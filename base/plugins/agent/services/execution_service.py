"""
M2 执行编排服务（ExecutionService）

溯源：
- docs/arch/04 F2 试跑（draft + kind=dry_run，单用户试跑并发=1）/ F3 运行（绑定发布版本快照）
- docs/arch/04 F5 协作式取消（当前节点完成或下一个调度点终止）/ F6 HITL 暂停恢复（72h）
- docs/arch/04 F7 配额拦截：预估 → Redis 原子预占 → 执行 → 每节点结算 → 释放差额（R-09）
- docs/arch/03 §2.5：全局信号量 50 + 用户信号量（经 T4 acquire_concurrency），看门狗心跳
- docs/arch/05 §1.4：引擎崩溃 → 实例 interrupted + 预占释放 + 审计 critical
- docs/arch/06 R-02：归属判断在接入层完成，引擎只消费 ExecutionContext

事件流：backend emit → TraceWriter（批量缓冲 R-11）→ asyncio.Queue → SSE 生成器；
node_completed 事件携带 usage 时按 (execution_id,node_id,seq) 幂等结算（R-09）。
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from loguru import logger

from base.common.authz.context import OwnerContext
from base.common.quota.errors import QuotaError
from base.common.quota.services.estimator import estimate_tokens
from base.common.quota.services.quota_service import QuotaService
from base.plugins.agent.models.workflow import WorkflowExecution
from base.plugins.agent.services.engine import events as evt
from base.plugins.agent.services.engine.backend import InProcessBackend, RunControl
from base.plugins.agent.services.engine.context import (
    KIND_DRY_RUN,
    KIND_RUN,
    ExecutionContext,
)
from base.plugins.agent.services.trace_service import TraceService, TraceWriter

# 执行状态
STATUS_RUNNING = "running"
STATUS_PAUSED = "paused"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
STATUS_INTERRUPTED = "interrupted"

# 心跳周期（conc: 看门狗 60s，03-§2.3）
HEARTBEAT_INTERVAL_S = 30
# 试跑并发（F2：单用户试跑并发=1）
DRY_RUN_CONCURRENCY = 1
# 缺省用户并发（套餐未配置 concurrency 项时）
DEFAULT_RUN_CONCURRENCY = 5


def estimate_graph_items(graph: Dict[str, Any]) -> Dict[str, float]:
    """
    配额预估（F7/R-09：先于一切外部调用）
    字符启发式（03-§2.9）：llm 节点 prompt 模板 + max_tokens 预留；rag 节点 kb_search 计数
    """
    token_estimate = 0
    kb_search = 0
    for node in graph.get("nodes") or []:
        ntype = node.get("type")
        config = (node.get("data") or {}).get("config") or {}
        if ntype == "llm":
            template = (config.get("prompt_template") or config.get("prompt") or "")
            system = config.get("system_prompt") or ""
            token_estimate += estimate_tokens(
                system + template, reserve_output=int(config.get("max_tokens", 2000))
            )
        elif ntype == "rag_retrieval":
            kb_search += 1
        elif ntype == "sub_workflow" or ntype == "loop":
            body = config.get("body")
            if isinstance(body, dict):
                sub = estimate_graph_items(body)
                token_estimate += int(sub.get("token", 0))
                kb_search += int(sub.get("kb_search", 0))
    items: Dict[str, float] = {}
    if token_estimate:
        items["token"] = float(token_estimate)
    if kb_search:
        items["kb_search"] = float(kb_search)
    return items


def sse_format(event: Dict[str, Any]) -> str:
    """SSE 帧（04-§5.1：event/data 两段）"""
    payload = dict(event.get("payload") or {})
    payload.setdefault("seq", event.get("seq"))
    return f"event: {event['event_type']}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class ExecutionService:
    """执行实例生命周期编排"""

    # 运行控制注册表（协作式取消 / HITL 恢复；进程内单实例，P0）
    _controls: Dict[int, RunControl] = {}

    # ============================================================
    # 准备（建实例 → 预估预占 → 并发槽）
    # ============================================================
    @classmethod
    async def prepare(
        cls,
        owner: OwnerContext,
        *,
        workflow,
        graph: Dict[str, Any],
        inputs: Dict[str, Any],
        kind: str = KIND_RUN,
        version_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> ExecutionContext:
        """
        创建执行实例并完成前置拦截（配额预估 + 并发槽）。

        Raises:
            QuotaError: 42901（预估超 / 并发超，不进入引擎，零模型调用）
        """
        execution = await WorkflowExecution.create(
            workflow_id=workflow.id,
            status=STATUS_RUNNING,
            input_data=inputs or {},
            owner_type=owner.owner_type,
            owner_id=owner.owner_id,
            version_id=version_id,
            kind=kind,
        )
        ctx: Optional[ExecutionContext] = None
        try:
            # 1. 配额预估预占（R-09：先于一切外部调用）
            hold_id = await QuotaService.quota_estimate(
                owner, estimate_graph_items(graph), execution_id=execution.id
            )
            # 2. 并发槽（全局 50 + 用户套餐；F2：试跑并发=1）
            if kind == KIND_DRY_RUN:
                limit = DRY_RUN_CONCURRENCY
            else:
                limit = await cls._concurrency_limit(owner)
            await QuotaService.acquire_concurrency(owner, limit)
            ctx = ExecutionContext(
                owner_type=owner.owner_type,
                owner_id=owner.owner_id,
                execution_id=execution.id,
                domain=owner.owner_type,
                quota_hold_id=hold_id,
                kind=kind,
                workflow_id=workflow.id,
                version_id=version_id,
                session_id=session_id,
                settings=graph.get("settings") or {},
                check_resource=cls._build_resource_checker(owner),
            )
            return ctx
        except Exception:
            # 前置失败：实例标记失败并释放已占资源（05-§1.4）
            execution.status = STATUS_FAILED
            execution.error_message = "前置拦截失败"
            execution.completed_at = datetime.now()
            await execution.save()
            if ctx is not None and ctx.quota_hold_id:
                await QuotaService.quota_release(ctx.quota_hold_id)
            raise

    @staticmethod
    async def _concurrency_limit(owner: OwnerContext) -> int:
        from base.common.quota.services.plan_service import PlanService

        plan = await PlanService.resolve_plan(owner.owner_type, owner.owner_id)
        items = (plan.quota_items if plan else {}) or {}
        try:
            return max(1, int(items.get("concurrency", DEFAULT_RUN_CONCURRENCY)))
        except (TypeError, ValueError):
            return DEFAULT_RUN_CONCURRENCY

    @staticmethod
    def _build_resource_checker(owner: OwnerContext):
        """M8 资源复核回调注入（R-02：引擎不直接做归属判断）"""
        from base.common.authz.service import ResourceGrantService

        async def check(resource_type: str, resource_id: Any) -> bool:
            return await ResourceGrantService.check_resource_access(
                owner, resource_type, resource_id
            )

        return check

    # ============================================================
    # 事件流执行（SSE 生成器）
    # ============================================================
    @classmethod
    async def stream_events(
        cls,
        ctx: ExecutionContext,
        graph: Dict[str, Any],
        inputs: Dict[str, Any],
    ) -> AsyncIterator[str]:
        """
        执行并产出 SSE 帧。无论正常/异常结束，最终都完成：
        状态落库、配额结算/释放、并发槽释放、Trace flush（05-§1.4）。
        """
        execution_id = ctx.execution_id
        queue: asyncio.Queue = asyncio.Queue()
        control = RunControl()
        cls._controls[execution_id] = control
        writer = await TraceService.create_writer(execution_id)
        heartbeat = asyncio.create_task(cls._heartbeat(ctx))

        async def emit(event_type: str, node_id: Optional[str], payload: Dict[str, Any]) -> None:
            event = await writer.emit(event_type, node_id, payload)
            await queue.put(event)
            if event_type == evt.EventType.NODE_COMPLETED:
                await cls._settle_node_usage(ctx, event)
            elif event_type == evt.EventType.RUN_PAUSED:
                await cls._update_status(execution_id, STATUS_PAUSED)

        async def runner() -> None:
            try:
                backend = InProcessBackend()
                result = await backend.execute(ctx, graph, inputs, emit, control)
                await queue.put({"__done__": True, "result": result})
            except Exception as e:  # 引擎崩溃兜底（05-§1.4）
                logger.critical(
                    f"[engine] 执行器崩溃 execution_id={execution_id}: {e}"
                )
                await queue.put({"__done__": True, "result": {
                    "status": STATUS_FAILED, "tokens": {"in": 0, "out": 0},
                    "error": {"code": "ENGINE_CRASH", "message": str(e)},
                }})

        task = asyncio.create_task(runner())
        final: Dict[str, Any] = {"status": STATUS_FAILED}
        try:
            while True:
                item = await queue.get()
                if item.get("__done__"):
                    final = item.get("result") or final
                    break
                yield sse_format(item)
        finally:
            heartbeat.cancel()
            if not task.done():
                control.request_cancel()
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                    pass
            await cls._finalize(ctx, final, writer)

    # ============================================================
    # 收尾（结算 / 释放 / 状态）
    # ============================================================
    @classmethod
    async def _finalize(cls, ctx: ExecutionContext, final: Dict[str, Any],
                        writer: TraceWriter) -> None:
        execution_id = ctx.execution_id
        status = final.get("status") or STATUS_FAILED
        if status == "success":
            status = STATUS_SUCCESS
        elif status not in (STATUS_CANCELLED, STATUS_INTERRUPTED):
            status = STATUS_FAILED
        try:
            await cls._update_status(
                execution_id, status,
                error=(final.get("error") or {}).get("message") or None,
                output=final.get("outputs") or None,
            )
        except Exception as e:
            logger.error(f"[engine] 执行状态落库失败 execution_id={execution_id}: {e}")
        # 释放剩余预占（已节点结算部分由 settle 转正式）
        try:
            if ctx.quota_hold_id:
                await QuotaService.quota_release(ctx.quota_hold_id)
        except Exception as e:
            logger.error(f"[engine] 配额预占释放失败 execution_id={execution_id}: {e}")
        # 并发槽释放
        try:
            await QuotaService.release_concurrency(ctx.owner)
        except Exception as e:
            logger.error(f"[engine] 并发槽释放失败 execution_id={execution_id}: {e}")
        cls._controls.pop(execution_id, None)
        await TraceService.close_writer(execution_id)
        logger.info(
            f"[engine] 执行结束 execution_id={execution_id} status={status} "
            f"tokens={final.get('tokens')}"
        )

    @staticmethod
    async def _update_status(execution_id: int, status: str, *,
                             error: Optional[str] = None,
                             output: Optional[Dict[str, Any]] = None) -> None:
        execution = await WorkflowExecution.get_or_none(id=execution_id)
        if execution is None:
            return
        execution.status = status
        if error is not None:
            execution.error_message = error[:2000]
        if output is not None:
            execution.output_data = output
        if status in (STATUS_SUCCESS, STATUS_FAILED, STATUS_CANCELLED, STATUS_INTERRUPTED):
            execution.completed_at = datetime.now()
        await execution.save()

    @classmethod
    async def _settle_node_usage(cls, ctx: ExecutionContext, event: Dict[str, Any]) -> None:
        """每节点结算（R-09：幂等键 execution_id+node_id+seq）"""
        usage = (event.get("payload") or {}).get("usage") or {}
        tokens_in = int(usage.get("tokens_in") or 0)
        tokens_out = int(usage.get("tokens_out") or 0)
        resource_type = usage.get("resource_type")
        amount = usage.get("amount")
        entries: List[Dict[str, Any]] = []
        if tokens_in or tokens_out:
            entries.append({
                "execution_id": ctx.execution_id,
                "node_id": event.get("node_id"),
                "seq": event.get("seq") or 0,
                "resource_type": "token",
                "amount": tokens_in + tokens_out,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "model": usage.get("model"),
            })
        elif resource_type and amount:
            entries.append({
                "execution_id": ctx.execution_id,
                "node_id": event.get("node_id"),
                "seq": event.get("seq") or 0,
                "resource_type": resource_type,
                "amount": amount,
            })
        if not entries:
            return
        try:
            await QuotaService.quota_settle(ctx.quota_hold_id or None, entries, owner=ctx.owner)
        except Exception as e:
            logger.error(f"[engine] 节点结算失败 execution_id={ctx.execution_id}: {e}")

    @staticmethod
    async def _heartbeat(ctx: ExecutionContext) -> None:
        """并发槽看门狗心跳（03-§2.3：60s 兜底，运行中周期续期）"""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL_S)
                await QuotaService.heartbeat_concurrency(ctx.owner)
        except asyncio.CancelledError:
            pass

    # ============================================================
    # 取消（F5 协作式）
    # ============================================================
    @classmethod
    async def cancel(cls, execution_id: int) -> str:
        """
        请求取消：置位取消标记；HITL 等待中的同步解除等待由引擎检测取消标志处理。
        返回当前状态（重复取消幂等）。
        """
        execution = await WorkflowExecution.get_or_none(id=execution_id)
        if execution is None:
            return "not_found"
        if execution.status not in (STATUS_RUNNING, STATUS_PAUSED):
            return execution.status
        control = cls._controls.get(execution_id)
        if control is not None:
            control.request_cancel()
            control.resume({"cancelled": True})  # 解除 HITL 等待，引擎下一个检查点抛 ExecutionCancelled
        else:
            # 无活动控制面（消费端已断开等）：直接标记取消
            await cls._update_status(execution_id, STATUS_CANCELLED,
                                     error="已被用户取消")
            await TraceWriter.mark_cancelled_state(execution_id)
        return STATUS_CANCELLED

    # ============================================================
    # HITL 恢复（F6：paused → running 状态机，幂等）
    # ============================================================
    @classmethod
    async def resume(cls, execution_id: int, *, approved: bool,
                     comment: str = "") -> Tuple[bool, str]:
        """
        注入审批结果并恢复执行。

        Returns:
            (accepted, status)：仅 paused → running 合法；重复提交返回当前状态（幂等）
        """
        execution = await WorkflowExecution.get_or_none(id=execution_id)
        if execution is None:
            return False, "not_found"
        if execution.status != STATUS_PAUSED:
            return False, execution.status
        control = cls._controls.get(execution_id)
        if control is None:
            return False, "no_active_control"
        await cls._update_status(execution_id, STATUS_RUNNING)
        control.resume({"approved": approved, "comment": comment})
        return True, STATUS_RUNNING

    # ============================================================
    # 断点标记（F5：进程重启后运行中实例标记 interrupted，P0 不自动恢复）
    # ============================================================
    @classmethod
    async def mark_interrupted_on_startup(cls) -> int:
        """启动任务：running/paused → interrupted；悬挂预占由 M9 清理任务兜底（AR-08）"""
        count = await WorkflowExecution.filter(
            status__in=[STATUS_RUNNING, STATUS_PAUSED]
        ).update(
            status=STATUS_INTERRUPTED,
            error_message="进程重启，执行实例标记中断（P0 不自动恢复）",
            completed_at=datetime.now(),
        )
        if count:
            logger.critical(
                f"[engine] 启动断点标记：{count} 个运行中实例标记 interrupted"
            )
        return count

    # ============================================================
    # 查询（用户侧列表/详情）
    # ============================================================
    @staticmethod
    async def list_executions(owner: OwnerContext, *, workflow_id: Optional[int] = None,
                              kind: Optional[str] = None, skip: int = 0,
                              limit: int = 50) -> List[WorkflowExecution]:
        query = WorkflowExecution.filter(
            owner_type=owner.owner_type, owner_id=owner.owner_id
        )
        if workflow_id:
            query = query.filter(workflow_id=workflow_id)
        if kind:
            query = query.filter(kind=kind)
        return await query.order_by("-created_at").offset(skip).limit(min(limit, 200))

    @staticmethod
    async def get_execution(owner: OwnerContext, execution_id: int) -> Optional[WorkflowExecution]:
        return await WorkflowExecution.get_or_none(
            id=execution_id, owner_type=owner.owner_type, owner_id=owner.owner_id
        )

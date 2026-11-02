"""
T6 / M2 引擎域化改造 单元测试

覆盖（对应任务验证要求）：
A. 信封契约：节点处理器返回 {status, outputs, usage?, error?}（start/template/end/llm）
B. SSE 事件序：run_started/node_started/token/node_completed/node_failed/run_paused/
   run_completed/run_failed 八类齐全；seq 全局单调（TraceWriter）；sse_format 帧结构
C. 配额四步：prepare 先 estimate 后 acquire_concurrency（dry_run limit=1）；
   QuotaError 超限不进引擎且实例标 failed；stream_events 结束 release + release_concurrency；
   node_completed 携带 usage 时按 (execution_id,node_id,seq) 幂等 settle
D. code/http 运行时拦截：用户域 code 拒绝（双保险）；http 白名单/DNS 内网二次校验/方法
E. M5 归属复核：owner 匹配/公共库/ResourceGrant 放行，缓存 60s 命中与
   invalidate_kb 版本递增后的缓存失效
F. RAG 白名单求交：自有∪授权∪公共求交、空交集拒绝、单节点 ≤5 KB、跨库按 score 合并
G. 取消协作式：RunControl 置位 → throw_if_cancelled；HITL 等待中 cancel → cancelled
H. HITL 状态机：paused→running 合法、重复提交幂等、无控制面拒绝、节点超时 skip/fail
I. 断点标记：running/paused → interrupted，终态不动
J. 缓冲 flush：满 20 条立即 flush、close 终 flush、seq 播种续接、cursor 分页

运行：.venv/Scripts/python.exe -m unittest tests.test_engine_m2 -v
"""
import asyncio
import json
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

from tortoise import Tortoise

from base.common.setting import get_model_list
from base.common.authz import OwnerContext
from base.common.quota.errors import QuotaError
from base.plugins.agent.models.trace_event import TraceEvent
from base.plugins.agent.models.workflow import Workflow, WorkflowExecution
from base.plugins.agent.services import execution_service as es_mod
from base.plugins.agent.services.engine import backend as backend_mod
from base.plugins.agent.services.engine import events as evt
from base.plugins.agent.services.engine import nodes as engine_nodes
from base.plugins.agent.services.engine import rag as rag_mod
from base.plugins.agent.services.engine.backend import InProcessBackend, RunControl
from base.plugins.agent.services.engine.context import ExecutionContext
from base.plugins.agent.services.engine.errors import (
    ExecutionCancelled,
    HitlTimeout,
    KBAccessDenied,
    NodeCapabilityDenied,
    NodeExecutionError,
)
from base.plugins.agent.services.engine.http_guard import (
    _domain_matches,
    assert_method_allowed,
    assert_url_allowed,
    is_private_ip,
)
from base.plugins.agent.services.engine.llm_gateway import classify_llm_error
from base.plugins.agent.services.execution_service import (
    ExecutionService,
    estimate_graph_items,
    sse_format,
)
from base.plugins.agent.services.trace_service import TraceService
from base.plugins.agent.services.vector_store import (
    KBAccessDeniedError,
    VectorStore,
)

TEST_MODULES = get_model_list()

FAKE_RESOURCE = {
    "provider_name": "openai",
    "api_key_str": "sk-test",
    "api_secret": None,
    "endpoint_url": "https://api.example.com/v1",
    "model_id_for_call": "gpt-test",
    "model_name": "gpt-test",
}


# ============================================================
# 辅助：图构造 / 运行时 / 收集器
# ============================================================
def _node(nid: str, ntype: str, *, inputs=None, outputs=None, config=None) -> Dict[str, Any]:
    data: Dict[str, Any] = {"label": nid, "config": config or {}}
    if inputs is not None:
        data["inputs"] = inputs
    if outputs is not None:
        data["outputs"] = outputs
    return {"id": nid, "type": ntype, "position": {"x": 0, "y": 0}, "data": data}


def _edge(eid: str, src: str, tgt: str, **kw) -> Dict[str, Any]:
    edge = {"id": eid, "source": src, "target": tgt,
            "sourceHandle": "out", "targetHandle": "in"}
    edge.update(kw)
    return edge


def minimal_graph() -> Dict[str, Any]:
    return {
        "nodes": [
            _node("s", "start", outputs=[{"name": "query", "type": "string"}]),
            _node("e", "end",
                  inputs=[{"name": "answer", "type": "any", "from": "s.query"}]),
        ],
        "edges": [_edge("e1", "s", "e")],
        "settings": {"timeout_s": 60},
    }


def llm_graph(*, stream: bool = False, on_error: Optional[str] = None,
              outputs=None, settings=None) -> Dict[str, Any]:
    config: Dict[str, Any] = {"model_id": 1, "prompt_template": "{{query}}",
                              "stream": stream, "max_tokens": 128}
    if on_error:
        config["on_error"] = on_error
    out = outputs if outputs is not None else [{"name": "answer", "type": "string"}]
    return {
        "nodes": [
            _node("s", "start", outputs=[{"name": "query", "type": "string"}]),
            _node("l", "llm", config=config, outputs=out),
            _node("e", "end",
                  inputs=[{"name": "answer", "type": "any", "from": "l.answer"}]),
        ],
        "edges": [_edge("e1", "s", "l"), _edge("e2", "l", "e")],
        "settings": settings or {"timeout_s": 60},
    }


def hitl_graph(*, timeout_s: int = 5, timeout_action: str = "fail") -> Dict[str, Any]:
    return {
        "nodes": [
            _node("s", "start", outputs=[{"name": "query", "type": "string"}]),
            _node("h", "hitl", config={"timeout_s": timeout_s,
                                       "timeout_action": timeout_action}),
            _node("e", "end", inputs=[{"name": "approved", "from": "h.approved"}]),
        ],
        "edges": [_edge("e1", "s", "h"), _edge("e2", "h", "e")],
        "settings": {"timeout_s": 60},
    }


def _ctx(*, domain: str = "cus", check_resource=None, settings=None,
         execution_id: int = 1) -> ExecutionContext:
    return ExecutionContext(
        owner_type="cus", owner_id=1, execution_id=execution_id,
        domain=domain, settings=settings or {},
        check_resource=check_resource,
    )


def _runtime(*, ctx=None, state=None, emit=None, control=None, depth=0) -> Dict[str, Any]:
    async def _noop_emit(*args, **kwargs):
        return None

    return {
        "emit": emit or _noop_emit,
        "control": control or RunControl(),
        "state": state or {"vars": {}, "nodes": {}},
        "ctx": ctx or _ctx(),
        "depth": depth,
        "run_subgraph": AsyncMock(return_value={"outputs": {}, "nodes": {}}),
    }


class EventCollector:
    """backend emit 收集器（event_type, node_id, payload）"""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    async def __call__(self, event_type, node_id, payload):
        self.events.append({"event_type": event_type, "node_id": node_id,
                            "payload": payload})

    def types(self) -> List[str]:
        return [e["event_type"] for e in self.events]


class FakeRedis:
    """M5 复核缓存用最小内存 Redis"""

    def __init__(self):
        self._data: Dict[str, Any] = {}

    async def get(self, key):
        return self._data.get(key)

    async def set(self, key, value, ex=None):
        self._data[key] = value
        return True

    async def incr(self, key):
        val = int(self._data.get(key) or 0) + 1
        self._data[key] = str(val)
        return val

    async def hset(self, key, mapping=None):
        h = self._data.setdefault(key, {})
        h.update({k: str(v) for k, v in (mapping or {}).items()})
        return len(mapping or {})

    async def expire(self, key, ttl):
        return True

    async def delete(self, *keys):
        n = 0
        for k in keys:
            if k in self._data:
                del self._data[k]
                n += 1
        return n


class FakeVectorStore:
    """RAG retrieve 注入用假向量库"""

    def __init__(self, hits_map: Dict[int, List[Dict[str, Any]]]):
        self.hits_map = hits_map
        self.calls: List[int] = []

    async def search(self, kb_id, vector, owner, *, top_k=5, score_threshold=None,
                     payload_filter=None):
        self.calls.append(kb_id)
        return list(self.hits_map.get(kb_id, []))


class DbTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TEST_MODULES})
        await Tortoise.generate_schemas()

    async def asyncTearDown(self):
        await Tortoise.close_connections()


# ============================================================
# A. 信封契约 / ExecutionContext
# ============================================================
class ContextEnvelopeTest(unittest.IsolatedAsyncioTestCase):

    async def test_envelope_contract(self):
        ctx = ExecutionContext(owner_type="cus", owner_id=7, execution_id=42,
                               quota_hold_id="h-1", kind="dry_run", session_id="sess-1")
        self.assertEqual(ctx.trace_id, 42)  # trace_id 默认 = execution_id
        self.assertEqual(ctx.owner, ("cus", 7))
        self.assertTrue(ctx.is_dry_run)
        env = ctx.envelope()
        self.assertEqual(env["owner"], {"owner_type": "cus", "owner_id": 7})
        self.assertEqual(env["quota"], {"hold_id": "h-1"})
        self.assertEqual(env["trace_id"], 42)
        self.assertEqual(env["session"], {"session_id": "sess-1"})
        self.assertEqual(env["domain"], "cus")
        self.assertEqual(env["kind"], "dry_run")

    async def test_require_resource_safe_side(self):
        # 无注入回调 → False（安全侧，R-02）
        ctx = _ctx(check_resource=None)
        self.assertFalse(await ctx.require_resource("model", 1))
        # 回调异常 → False（安全侧）
        ctx2 = _ctx(check_resource=AsyncMock(side_effect=RuntimeError("boom")))
        self.assertFalse(await ctx2.require_resource("model", 1))
        # 正常放行
        ctx3 = _ctx(check_resource=AsyncMock(return_value=True))
        self.assertTrue(await ctx3.require_resource("model", 1))


class NodeEnvelopeTest(unittest.IsolatedAsyncioTestCase):

    async def test_handle_start_envelope(self):
        node = _node("s", "start", outputs=[{"name": "query", "type": "string"}])
        runtime = _runtime(state={"vars": {"query": "你好"}, "nodes": {}})
        result = await engine_nodes.handle_start(node, {}, runtime)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["outputs"], {"query": "你好"})

    async def test_handle_template_envelope(self):
        node = _node("t", "template",
                     config={"template": "问题: {{query}}"})
        runtime = _runtime(state={"vars": {"query": "Q1"}, "nodes": {}})
        result = await engine_nodes.handle_template(node, {}, runtime)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["outputs"]["output"], "问题: Q1")

    async def test_handle_end_envelope(self):
        result = await engine_nodes.handle_end(
            _node("e", "end"), {"answer": "A"}, _runtime())
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["outputs"], {"answer": "A"})

    async def test_handle_llm_envelope_and_usage(self):
        node = _node("l", "llm",
                     config={"model_id": 1, "prompt_template": "{{query}}"})
        runtime = _runtime(
            ctx=_ctx(check_resource=AsyncMock(return_value=True)),
            state={"vars": {"query": "hi"}, "nodes": {}},
        )
        with patch.object(engine_nodes.LLMGateway, "resolve_model",
                          AsyncMock(return_value=FAKE_RESOURCE)), \
             patch.object(engine_nodes.LLMGateway, "call",
                          AsyncMock(return_value={
                              "content": "答案",
                              "usage": {"tokens_in": 11, "tokens_out": 7, "model": "gpt-test"},
                          })) as call_mock:
            result = await engine_nodes.handle_llm(node, {}, runtime)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["outputs"]["answer"], "答案")
        self.assertEqual(result["usage"]["tokens_in"], 11)
        self.assertEqual(result["usage"]["tokens_out"], 7)
        # messages 由模板渲染
        sent_messages = call_mock.await_args.args[1]
        self.assertEqual(sent_messages[-1]["content"], "hi")

    async def test_handle_llm_stream_emits_token(self):
        node = _node("l", "llm",
                     config={"model_id": 1, "prompt_template": "q", "stream": True})
        collector = EventCollector()
        control = RunControl()
        runtime = _runtime(ctx=_ctx(check_resource=AsyncMock(return_value=True)),
                           emit=collector, control=control,
                           state={"vars": {}, "nodes": {}})

        async def fake_call(resource, messages, *, stream=False, on_token=None, **kw):
            if on_token:
                await on_token("你")
                await on_token("好")
            return {"content": "你好",
                    "usage": {"tokens_in": 2, "tokens_out": 2, "model": "gpt-test"}}

        with patch.object(engine_nodes.LLMGateway, "resolve_model",
                          AsyncMock(return_value=FAKE_RESOURCE)), \
             patch.object(engine_nodes.LLMGateway, "call",
                          AsyncMock(side_effect=fake_call)):
            result = await engine_nodes.handle_llm(node, {}, runtime)
        self.assertEqual(result["status"], "success")
        token_events = [e for e in collector.events
                        if e["event_type"] == evt.EventType.TOKEN]
        self.assertEqual([e["payload"]["delta"] for e in token_events], ["你", "好"])

    async def test_handle_llm_unauthorized_model(self):
        node = _node("l", "llm", config={"model_id": 99, "prompt_template": "q"})
        runtime = _runtime(ctx=_ctx(check_resource=AsyncMock(return_value=False)))
        with self.assertRaises(NodeExecutionError) as cm:
            await engine_nodes.handle_llm(node, {}, runtime)
        self.assertEqual(cm.exception.code, "MODEL_UNAVAILABLE")
        self.assertFalse(cm.exception.retryable)


class ClassifyLlmErrorTest(unittest.TestCase):

    def test_429_with_retry_after(self):
        err = classify_llm_error(Exception("OpenAI API调用失败: 429 rate limit, retry after 5"))
        self.assertEqual(err.code, "LLM_RATE_LIMITED")
        self.assertTrue(err.retryable)
        self.assertEqual(err.retry_after, 5.0)

    def test_timeout(self):
        err = classify_llm_error(Exception("request timeout"))
        self.assertEqual(err.code, "LLM_TIMEOUT")
        self.assertTrue(err.retryable)

    def test_5xx_retryable(self):
        err = classify_llm_error(Exception("503 Service Unavailable"))
        self.assertEqual(err.code, "LLM_UPSTREAM_5XX")
        self.assertTrue(err.retryable)

    def test_4xx_not_retryable(self):
        err = classify_llm_error(Exception("401 unauthorized"))
        self.assertEqual(err.code, "LLM_CALL_FAILED")
        self.assertFalse(err.retryable)


# ============================================================
# D. code / http 运行时拦截（R-10）
# ============================================================
class CapabilityGuardTest(unittest.IsolatedAsyncioTestCase):

    async def test_code_denied_user_domain(self):
        node = _node("c", "code", config={"language": "python", "code": "1+1"})
        for domain in ("cus", "usr"):
            with self.assertRaises(NodeCapabilityDenied) as cm:
                await engine_nodes.handle_code(node, {}, _runtime(ctx=_ctx(domain=domain)))
            self.assertEqual(cm.exception.code, "NODE_CAPABILITY_DENIED")
            self.assertFalse(cm.exception.retryable)

    def test_method_guard(self):
        self.assertEqual(assert_method_allowed("get"), "GET")
        self.assertEqual(assert_method_allowed("post"), "POST")
        with self.assertRaises(NodeCapabilityDenied):
            assert_method_allowed("DELETE")

    def test_is_private_ip(self):
        for ip in ("10.1.2.3", "172.16.0.1", "192.168.1.1", "127.0.0.1",
                   "169.254.1.1", "::1", "fc00::1", "not-an-ip"):
            self.assertTrue(is_private_ip(ip), ip)
        self.assertFalse(is_private_ip("8.8.8.8"))

    def test_domain_wildcard(self):
        wl = {"*.example.com", "a.com"}
        self.assertTrue(_domain_matches("api.example.com", wl))
        self.assertTrue(_domain_matches("example.com", wl))
        self.assertTrue(_domain_matches("a.com", wl))
        self.assertFalse(_domain_matches("b.com", wl))
        self.assertFalse(_domain_matches("example.com.evil.com", wl))

    def _mock_dns(self, ips: List[str]):
        infos = [(2, 1, 6, "", (ip, 80)) for ip in ips]
        loop = AsyncMock()
        loop.getaddrinfo = AsyncMock(return_value=infos)
        return patch("base.plugins.agent.services.engine.http_guard.asyncio.get_event_loop",
                     return_value=loop)

    async def test_url_empty_whitelist_denied(self):
        with self.assertRaises(NodeCapabilityDenied):
            await assert_url_allowed("http://a.com", whitelist=set())

    async def test_url_not_in_whitelist_denied(self):
        with self.assertRaises(NodeCapabilityDenied):
            await assert_url_allowed("http://evil.com", whitelist={"a.com"})

    async def test_url_private_ip_blocked(self):
        with self._mock_dns(["10.0.0.5"]):
            with self.assertRaises(NodeCapabilityDenied) as cm:
                await assert_url_allowed("http://a.com", whitelist={"a.com"})
            self.assertIn("内网", cm.exception.message)

    async def test_url_public_allowed(self):
        with self._mock_dns(["8.8.8.8"]):
            url = await assert_url_allowed("https://a.com/x", whitelist={"a.com"})
        self.assertEqual(url, "https://a.com/x")

    async def test_url_bad_scheme_denied(self):
        with self.assertRaises(NodeCapabilityDenied):
            await assert_url_allowed("ftp://a.com", whitelist={"a.com"})


# ============================================================
# B. 引擎事件序（backend emit）+ 重试/失败策略
# ============================================================
class EngineEventSequenceTest(unittest.IsolatedAsyncioTestCase):

    async def _run(self, graph, inputs=None, *, ctx=None, control=None):
        collector = EventCollector()
        backend = InProcessBackend()
        result = await backend.execute(
            ctx or _ctx(check_resource=AsyncMock(return_value=True)),
            graph, inputs or {"query": "Q"}, collector, control or RunControl())
        return result, collector

    async def test_success_event_sequence(self):
        result, collector = await self._run(minimal_graph())
        self.assertEqual(result["status"], "success")
        types = collector.types()
        self.assertEqual(types[0], evt.EventType.RUN_STARTED)
        self.assertEqual(types[-1], evt.EventType.RUN_COMPLETED)
        self.assertEqual(types.count(evt.EventType.NODE_STARTED), 2)
        self.assertEqual(types.count(evt.EventType.NODE_COMPLETED), 2)
        # end 输出来自 start.query
        self.assertEqual(result["outputs"].get("answer"), "Q")

    async def test_llm_stream_full_event_sequence(self):
        async def fake_call(resource, messages, *, stream=False, on_token=None, **kw):
            if on_token:
                await on_token("A")
                await on_token("B")
            return {"content": "AB",
                    "usage": {"tokens_in": 3, "tokens_out": 2, "model": "gpt-test"}}

        with patch.object(engine_nodes.LLMGateway, "resolve_model",
                          AsyncMock(return_value=FAKE_RESOURCE)), \
             patch.object(engine_nodes.LLMGateway, "call",
                          AsyncMock(side_effect=fake_call)):
            result, collector = await self._run(llm_graph(stream=True))
        self.assertEqual(result["status"], "success")
        types = collector.types()
        # 八类中成功路径的六类：run_started/node_started/token/node_completed/run_completed
        self.assertEqual(types[0], evt.EventType.RUN_STARTED)
        self.assertEqual(types[-1], evt.EventType.RUN_COMPLETED)
        self.assertEqual(types.count(evt.EventType.TOKEN), 2)
        # token 事件位于 llm 的 node_started 与 node_completed 之间
        llm_start_idx = types.index(evt.EventType.NODE_STARTED, 1)  # start 节点之后
        llm_start_idx = types.index(evt.EventType.NODE_STARTED, llm_start_idx + 1)
        token_idx = types.index(evt.EventType.TOKEN)
        complete_idx = types.index(evt.EventType.NODE_COMPLETED, llm_start_idx)
        self.assertLess(llm_start_idx, token_idx)
        self.assertLess(token_idx, complete_idx)
        # token 汇总
        self.assertEqual(result["tokens"], {"in": 3, "out": 2})

    async def test_node_failure_fail_fast(self):
        with patch.object(engine_nodes.LLMGateway, "resolve_model",
                          AsyncMock(return_value=FAKE_RESOURCE)), \
             patch.object(engine_nodes.LLMGateway, "call",
                          AsyncMock(side_effect=NodeExecutionError(
                              "LLM_CALL_FAILED", "4xx", retryable=False))):
            result, collector = await self._run(llm_graph())
        self.assertEqual(result["status"], "failed")
        types = collector.types()
        self.assertIn(evt.EventType.NODE_FAILED, types)
        self.assertEqual(types[-1], evt.EventType.RUN_FAILED)
        failed_payload = next(e for e in collector.events
                              if e["event_type"] == evt.EventType.NODE_FAILED)
        self.assertEqual(failed_payload["payload"]["error"]["code"], "LLM_CALL_FAILED")

    async def test_retry_then_success(self):
        calls = {"n": 0}

        async def flaky(node, resolved_inputs, runtime):
            calls["n"] += 1
            if calls["n"] < 3:
                raise NodeExecutionError("LLM_TIMEOUT", "t", retryable=True)
            return {"status": "success", "outputs": {"answer": "ok"}}

        with patch.dict(backend_mod.NODE_HANDLERS, {"llm": flaky}), \
             patch.object(backend_mod, "RETRY_BACKOFF", (0.001, 0.001, 0.001)):
            result, _ = await self._run(llm_graph())
        self.assertEqual(result["status"], "success")
        self.assertEqual(calls["n"], 3)  # 1 次首发 + 2 次重试

    async def test_retry_max_capped_at_3(self):
        calls = {"n": 0}

        async def always_fail(node, resolved_inputs, runtime):
            calls["n"] += 1
            raise NodeExecutionError("LLM_TIMEOUT", "t", retryable=True)

        # settings.retry.max=10 不可上调（N4-4：上限 3）
        with patch.dict(backend_mod.NODE_HANDLERS, {"llm": always_fail}), \
             patch.object(backend_mod, "RETRY_BACKOFF", (0.001, 0.001, 0.001)):
            result, _ = await self._run(
                llm_graph(settings={"retry": {"max": 10}}))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(calls["n"], 4)  # 1 + 3 次重试封顶

    async def test_retry_after_respected(self):
        calls = {"n": 0}
        sleeps: List[float] = []

        async def rate_limited(node, resolved_inputs, runtime):
            calls["n"] += 1
            if calls["n"] == 1:
                raise NodeExecutionError("LLM_RATE_LIMITED", "429",
                                         retryable=True, retry_after=9.0)
            return {"status": "success", "outputs": {"answer": "ok"}}

        async def fake_sleep(delay):
            sleeps.append(delay)

        with patch.dict(backend_mod.NODE_HANDLERS, {"llm": rate_limited}), \
             patch("asyncio.sleep", side_effect=fake_sleep):
            result, _ = await self._run(llm_graph())
        self.assertEqual(result["status"], "success")
        self.assertEqual(sleeps[0], 9.0)  # max(退避 1s, Retry-After 9s)

    async def test_continue_with_default(self):
        outputs = [{"name": "answer", "type": "string", "default": "默认答案"}]

        async def always_fail(node, resolved_inputs, runtime):
            raise NodeExecutionError("LLM_CALL_FAILED", "4xx", retryable=False)

        with patch.dict(backend_mod.NODE_HANDLERS, {"llm": always_fail}):
            result, collector = await self._run(
                llm_graph(on_error="continue_with_default", outputs=outputs))
        self.assertEqual(result["status"], "success")
        # end 输入来自 l.answer 的默认值
        self.assertEqual(result["outputs"].get("answer"), "默认答案")

    async def test_condition_branch_routing(self):
        graph = {
            "nodes": [
                _node("s", "start", outputs=[{"name": "flag", "type": "number"}]),
                _node("c", "condition"),
                _node("t1", "template", config={"template": "分支一"}),
                _node("t2", "template", config={"template": "分支二"}),
                _node("e", "end",
                      inputs=[{"name": "x", "from": "t1.output"},
                              {"name": "y", "from": "t2.output"}]),
            ],
            "edges": [
                _edge("e1", "s", "c"),
                _edge("e2", "c", "t1", condition="{{flag}} == 1", priority=1),
                _edge("e3", "c", "t2"),  # 默认边
                _edge("e4", "t1", "e"),
                _edge("e5", "t2", "e"),
            ],
            "settings": {},
        }
        # flag=1 → 走 t1
        result, _ = await self._run(graph, inputs={"flag": 1})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["outputs"].get("x"), "分支一")
        self.assertIsNone(result["outputs"].get("y"))
        # flag=2 → 默认边 t2
        result2, _ = await self._run(graph, inputs={"flag": 2})
        self.assertEqual(result2["outputs"].get("y"), "分支二")


# ============================================================
# J. Trace 缓冲写入（R-11）+ seq + 分页 + SSE 帧
# ============================================================
class TraceWriterTest(DbTestCase):

    async def test_flush_at_20_and_close_flush(self):
        writer = await TraceService.create_writer(900001)
        events = []
        for i in range(25):
            events.append(await writer.emit(
                evt.EventType.NODE_STARTED, "n1", {"i": i}))
        # seq 全局单调 1..25
        self.assertEqual([e["seq"] for e in events], list(range(1, 26)))
        # 满 20 已触发 flush（R-11 批量缓冲）
        count = await TraceEvent.filter(execution_id=900001).count()
        self.assertEqual(count, 20)
        # close 终 flush 剩余 5 条
        await TraceService.close_writer(900001)
        count = await TraceEvent.filter(execution_id=900001).count()
        self.assertEqual(count, 25)

    async def test_seq_seeded_from_db(self):
        await TraceEvent.create(execution_id=900002, seq=7,
                                event_type="node_started", payload={})
        writer = await TraceService.create_writer(900002)
        event = await writer.emit(evt.EventType.NODE_COMPLETED, "n1", {})
        self.assertEqual(event["seq"], 8)  # 恢复执行续接单调
        await TraceService.close_writer(900002)

    async def test_cursor_pagination(self):
        writer = await TraceService.create_writer(900003)
        for i in range(15):
            await writer.emit(evt.EventType.TOKEN, "l", {"delta": str(i)})
        await TraceService.close_writer(900003)
        page1 = await TraceService.list_events(900003, cursor=0, limit=10)
        self.assertEqual(len(page1), 10)
        self.assertEqual(page1[0].seq, 1)
        page2 = await TraceService.list_events(900003, cursor=page1[-1].seq, limit=10)
        self.assertEqual([e.seq for e in page2], [11, 12, 13, 14, 15])

    def test_sse_format(self):
        frame = sse_format({"event_type": "token", "seq": 3,
                            "payload": {"node_id": "l", "delta": "x"}})
        self.assertTrue(frame.startswith("event: token\n"))
        self.assertTrue(frame.endswith("\n\n"))
        data = json.loads(frame.split("data: ", 1)[1])
        self.assertEqual(data["seq"], 3)  # seq 注入 data 段
        self.assertEqual(data["delta"], "x")


# ============================================================
# C. 配额四步接线（F7/R-09）
# ============================================================
class QuotaWiringTest(DbTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.workflow = await Workflow.create(
            name="wf-q", definition={}, owner_type="cus", owner_id=1)
        patcher = patch.object(es_mod, "QuotaService")
        self.qs = patcher.start()
        self.addCleanup(patcher.stop)
        self.qs.quota_estimate = AsyncMock(return_value="hold-1")
        self.qs.acquire_concurrency = AsyncMock(return_value=None)
        self.qs.quota_settle = AsyncMock(return_value={"settled": 1})
        self.qs.quota_release = AsyncMock(return_value=True)
        self.qs.release_concurrency = AsyncMock(return_value=None)
        self.qs.heartbeat_concurrency = AsyncMock(return_value=None)
        # 资源复核回调注入放行（M8 授权链路在 test_authz_m8 覆盖，此处聚焦配额接线）
        async def _allow_all(resource_type, resource_id):
            return True
        checker_patcher = patch.object(
            es_mod.ExecutionService, "_build_resource_checker",
            return_value=_allow_all)
        checker_patcher.start()
        self.addCleanup(checker_patcher.stop)
        self.owner = OwnerContext(owner_type="cus", owner_id=1)

    def test_estimate_graph_items(self):
        items = estimate_graph_items(llm_graph())
        self.assertGreater(items["token"], 0)  # llm 节点预估
        self.assertNotIn("kb_search", items)
        rag_graph = {
            "nodes": [_node("r", "rag_retrieval", config={"kb_ids": [1]})],
            "edges": [], "settings": {},
        }
        self.assertEqual(estimate_graph_items(rag_graph)["kb_search"], 1)

    async def test_prepare_estimate_then_acquire(self):
        ctx = await ExecutionService.prepare(
            self.owner, workflow=self.workflow, graph=llm_graph(),
            inputs={"query": "q"}, kind="dry_run")
        # 先预估后并发槽（R-09：先于一切外部调用）
        self.qs.quota_estimate.assert_awaited_once()
        estimate_args = self.qs.quota_estimate.await_args
        self.assertIn("token", estimate_args.args[1])
        self.assertEqual(estimate_args.kwargs.get("execution_id"), ctx.execution_id)
        # dry_run 并发=1（F2）
        self.qs.acquire_concurrency.assert_awaited_once()
        self.assertEqual(self.qs.acquire_concurrency.await_args.args[1], 1)
        self.assertEqual(ctx.quota_hold_id, "hold-1")
        self.assertEqual(ctx.kind, "dry_run")
        self.assertEqual(ctx.domain, "cus")
        exe = await WorkflowExecution.get(id=ctx.execution_id)
        self.assertEqual(exe.status, "running")
        self.assertEqual(exe.kind, "dry_run")

    async def test_prepare_quota_exceeded_never_enters_engine(self):
        self.qs.quota_estimate = AsyncMock(
            side_effect=QuotaError(item="token", remaining=0, estimated=100))
        with self.assertRaises(QuotaError) as cm:
            await ExecutionService.prepare(
                self.owner, workflow=self.workflow, graph=llm_graph(), inputs={})
        self.assertEqual(cm.exception.code, 42901)
        # 不进入引擎：并发槽未申请
        self.qs.acquire_concurrency.assert_not_called()
        # 实例标记 failed（05-§1.4）
        exe = await WorkflowExecution.filter(workflow_id=self.workflow.id).first()
        self.assertEqual(exe.status, "failed")

    async def test_stream_events_releases_and_settles(self):
        ctx = await ExecutionService.prepare(
            self.owner, workflow=self.workflow, graph=llm_graph(),
            inputs={"query": "q"}, kind="dry_run")
        with patch.object(engine_nodes.LLMGateway, "resolve_model",
                          AsyncMock(return_value=FAKE_RESOURCE)), \
             patch.object(engine_nodes.LLMGateway, "call",
                          AsyncMock(return_value={
                              "content": "ans",
                              "usage": {"tokens_in": 12, "tokens_out": 8, "model": "m1"},
                          })):
            frames = [f async for f in
                      ExecutionService.stream_events(ctx, llm_graph(), {"query": "q"})]
        types = [f.split("\n", 1)[0].replace("event: ", "") for f in frames]
        self.assertEqual(types[0], "run_started")
        self.assertEqual(types[-1], "run_completed")
        # 每节点结算（llm usage → token 条目，幂等键 execution_id+node_id+seq）
        self.qs.quota_settle.assert_awaited_once()
        settle_args = self.qs.quota_settle.await_args
        self.assertEqual(settle_args.args[0], "hold-1")
        entry = settle_args.args[1][0]
        self.assertEqual(entry["resource_type"], "token")
        self.assertEqual(entry["amount"], 20)
        self.assertEqual(entry["tokens_in"], 12)
        self.assertEqual(entry["tokens_out"], 8)
        self.assertEqual(entry["execution_id"], ctx.execution_id)
        self.assertEqual(entry["node_id"], "l")
        self.assertGreater(entry["seq"], 0)
        # 结束：释放剩余预占 + 并发槽
        self.qs.quota_release.assert_awaited_once_with("hold-1")
        self.qs.release_concurrency.assert_awaited_once()
        exe = await WorkflowExecution.get(id=ctx.execution_id)
        self.assertEqual(exe.status, "success")
        self.assertIsNotNone(exe.completed_at)

    async def test_stream_events_failure_releases(self):
        ctx = await ExecutionService.prepare(
            self.owner, workflow=self.workflow, graph=llm_graph(),
            inputs={"query": "q"}, kind="dry_run")
        with patch.object(engine_nodes.LLMGateway, "resolve_model",
                          AsyncMock(return_value=FAKE_RESOURCE)), \
             patch.object(engine_nodes.LLMGateway, "call",
                          AsyncMock(side_effect=NodeExecutionError(
                              "LLM_CALL_FAILED", "4xx", retryable=False))):
            frames = [f async for f in
                      ExecutionService.stream_events(ctx, llm_graph(), {"query": "q"})]
        types = [f.split("\n", 1)[0].replace("event: ", "") for f in frames]
        self.assertEqual(types[-1], "run_failed")
        self.qs.quota_release.assert_awaited_once_with("hold-1")
        self.qs.release_concurrency.assert_awaited_once()
        exe = await WorkflowExecution.get(id=ctx.execution_id)
        self.assertEqual(exe.status, "failed")


# ============================================================
# E. M5 归属复核（缓存 60s + 授权版本号失效）
# ============================================================
class VectorStoreAuthzTest(DbTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        from base.plugins.agent.models.rag import RAGKnowledgeBase
        self.kb_model = RAGKnowledgeBase
        self.store = VectorStore()
        self.fake = FakeRedis()
        patcher = patch.object(self.store, "_redis", AsyncMock(return_value=self.fake))
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_owner_match_allowed_and_cached(self):
        kb = await self.kb_model.create(name="kb1", owner_type="cus", owner_id=1)
        await self.store.verify_kb_access(kb.id, ("cus", 1))
        key = self.store._cache_key(kb.id, ("cus", 1), 0)
        self.assertEqual(await self.fake.get(key), "1")  # 放行结果已缓存

    async def test_stranger_denied_and_cached(self):
        kb = await self.kb_model.create(name="kb2", owner_type="cus", owner_id=1,
                                        is_public=False)
        with self.assertRaises(KBAccessDeniedError):
            await self.store.verify_kb_access(kb.id, ("cus", 2))
        key = self.store._cache_key(kb.id, ("cus", 2), 0)
        self.assertEqual(await self.fake.get(key), "0")  # 拒绝结果亦缓存

    async def test_public_kb_allowed(self):
        kb = await self.kb_model.create(name="kb3", owner_type="usr", owner_id=9,
                                        is_public=True)
        await self.store.verify_kb_access(kb.id, ("cus", 2))

    async def test_grant_allowed(self):
        kb = await self.kb_model.create(name="kb4", owner_type="usr", owner_id=9,
                                        is_public=False)
        with patch("base.common.authz.service.ResourceGrantService.check_resource_access",
                   AsyncMock(return_value=True)):
            await self.store.verify_kb_access(kb.id, ("cus", 2))

    async def test_cache_hit_and_invalidate(self):
        kb = await self.kb_model.create(name="kb5", owner_type="cus", owner_id=1)
        await self.store.verify_kb_access(kb.id, ("cus", 1))  # v0 缓存 "1"
        # PG 事实变化：归属转移
        kb.owner_id = 999
        await kb.save()
        # 命中旧缓存仍放行（60s 内）
        await self.store.verify_kb_access(kb.id, ("cus", 1))
        # 授权版本递增 → 旧键自然失效，新键触发 PG 复核
        await self.store.invalidate_kb(kb.id)
        self.assertEqual(await self.fake.get(self.store._ver_key(kb.id)), "1")
        with self.assertRaises(KBAccessDeniedError):
            await self.store.verify_kb_access(kb.id, ("cus", 1))


# ============================================================
# F. RAG 白名单求交（05-§2.2）
# ============================================================
class RagRetrieveTest(DbTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        from base.plugins.agent.models.rag import RAGKnowledgeBase
        self.kb_model = RAGKnowledgeBase

    async def _make_kbs(self):
        own = await self.kb_model.create(name="own", owner_type="cus", owner_id=1)
        pub = await self.kb_model.create(name="pub", owner_type="usr", owner_id=9,
                                         is_public=True)
        grant = await self.kb_model.create(name="grant", owner_type="usr", owner_id=9)
        other = await self.kb_model.create(name="other", owner_type="usr", owner_id=9)
        inactive = await self.kb_model.create(name="ina", owner_type="cus", owner_id=1,
                                              status="inactive")
        return own, pub, grant, other, inactive

    async def test_accessible_intersection(self):
        own, pub, grant, other, inactive = await self._make_kbs()
        with patch.object(rag_mod.ResourceGrantService, "check_many",
                          AsyncMock(return_value=[str(grant.id)])):
            allowed = await rag_mod.accessible_kb_ids(
                ("cus", 1), [own.id, pub.id, grant.id, other.id, inactive.id])
        # 自有 ∪ 公共 ∪ 授权；越权与 inactive 排除
        self.assertEqual(allowed, {own.id, pub.id, grant.id})

    async def test_retrieve_empty_intersection_denied(self):
        other = await self.kb_model.create(name="o2", owner_type="usr", owner_id=9)
        with patch.object(rag_mod.ResourceGrantService, "check_many",
                          AsyncMock(return_value=[])):
            with self.assertRaises(KBAccessDenied) as cm:
                await rag_mod.retrieve(("cus", 1), [other.id], "query")
            self.assertEqual(cm.exception.code, "KB_ACCESS_DENIED")

    async def test_retrieve_max_5_kb(self):
        with self.assertRaises(KBAccessDenied):
            await rag_mod.retrieve(("cus", 1), [1, 2, 3, 4, 5, 6], "query")

    async def test_retrieve_merge_and_truncate(self):
        kb1 = await self.kb_model.create(name="k1", owner_type="cus", owner_id=1)
        kb2 = await self.kb_model.create(name="k2", owner_type="cus", owner_id=1,
                                         is_public=True)
        hits = {
            kb1.id: [{"chunk_id": 1, "kb_id": kb1.id, "score": 0.7, "content": "A"}],
            kb2.id: [{"chunk_id": 2, "kb_id": kb2.id, "score": 0.9, "content": "B"},
                     {"chunk_id": 3, "kb_id": kb2.id, "score": 0.5, "content": "C"}],
        }
        store = FakeVectorStore(hits)
        with patch.object(rag_mod.ResourceGrantService, "check_many",
                          AsyncMock(return_value=[])), \
             patch.object(rag_mod, "_embed_query", AsyncMock(return_value=[0.1, 0.2])):
            result = await rag_mod.retrieve(
                ("cus", 1), [kb1.id, kb2.id], "query", top_k=2, store=store)
        # 按 score 合并截断 top_k
        self.assertEqual([h["content"] for h in result], ["B", "A"])
        self.assertEqual(sorted(store.calls), [kb1.id, kb2.id])


# ============================================================
# G/H. 取消协作式 + HITL 状态机
# ============================================================
class RunControlTest(unittest.IsolatedAsyncioTestCase):

    async def test_throw_if_cancelled(self):
        control = RunControl()
        control.throw_if_cancelled()  # 未置位不抛
        control.request_cancel()
        with self.assertRaises(ExecutionCancelled):
            control.throw_if_cancelled()

    async def test_hitl_resume_injects_outputs(self):
        node = _node("h", "hitl", config={"timeout_s": 5})
        control = RunControl()
        collector = EventCollector()
        runtime = _runtime(control=control, emit=collector)

        async def resume_later():
            await asyncio.sleep(0.05)
            control.resume({"approved": True, "comment": "同意"})

        task = asyncio.create_task(resume_later())
        result = await engine_nodes.handle_hitl(node, {}, runtime)
        await task
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["outputs"]["approved"], True)
        self.assertEqual(result["outputs"]["comment"], "同意")
        # run_paused 事件已发出（含 assignee/deadline）
        paused = [e for e in collector.events
                  if e["event_type"] == evt.EventType.RUN_PAUSED]
        self.assertEqual(len(paused), 1)
        self.assertIn("deadline", paused[0]["payload"])
        # 审批结果注入变量
        self.assertEqual(runtime["state"]["vars"]["hitl"]["approved"], True)

    async def test_hitl_timeout_skip(self):
        node = _node("h", "hitl",
                     config={"timeout_s": 0.05, "timeout_action": "skip"})
        result = await engine_nodes.handle_hitl(node, {}, _runtime())
        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["outputs"]["approved"])
        self.assertTrue(result["outputs"]["skipped"])

    async def test_hitl_timeout_fail(self):
        node = _node("h", "hitl",
                     config={"timeout_s": 0.05, "timeout_action": "fail"})
        with self.assertRaises(HitlTimeout) as cm:
            await engine_nodes.handle_hitl(node, {}, _runtime())
        self.assertEqual(cm.exception.code, "HITL_TIMEOUT")


class HitlAndCancelServiceTest(DbTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.workflow = await Workflow.create(
            name="wf-h", definition={}, owner_type="cus", owner_id=1)
        patcher = patch.object(es_mod, "QuotaService")
        self.qs = patcher.start()
        self.addCleanup(patcher.stop)
        self.qs.quota_estimate = AsyncMock(return_value="hold-h")
        self.qs.acquire_concurrency = AsyncMock(return_value=None)
        self.qs.quota_settle = AsyncMock(return_value={"settled": 0})
        self.qs.quota_release = AsyncMock(return_value=True)
        self.qs.release_concurrency = AsyncMock(return_value=None)
        self.qs.heartbeat_concurrency = AsyncMock(return_value=None)
        self.owner = OwnerContext(owner_type="cus", owner_id=1)

    async def asyncTearDown(self):
        ExecutionService._controls.clear()
        await super().asyncTearDown()

    async def test_resume_state_machine(self):
        exe = await WorkflowExecution.create(
            workflow_id=self.workflow.id, status="paused", input_data={},
            owner_type="cus", owner_id=1)
        # 无活动控制面 → 拒绝
        ok, st = await ExecutionService.resume(exe.id, approved=True)
        self.assertEqual((ok, st), (False, "no_active_control"))
        # 注册控制面 → paused → running
        control = RunControl()
        ExecutionService._controls[exe.id] = control
        ok, st = await ExecutionService.resume(exe.id, approved=True, comment="c")
        self.assertEqual((ok, st), (True, "running"))
        self.assertEqual(control.resume_payload, {"approved": True, "comment": "c"})
        await exe.refresh_from_db()
        self.assertEqual(exe.status, "running")
        # 重复提交幂等（已非 paused）
        ok, st = await ExecutionService.resume(exe.id, approved=False)
        self.assertEqual((ok, st), (False, "running"))
        # 不存在
        ok, st = await ExecutionService.resume(999999, approved=True)
        self.assertEqual((ok, st), (False, "not_found"))

    async def test_hitl_run_paused_then_resume_to_completed(self):
        graph = hitl_graph(timeout_s=5)
        ctx = await ExecutionService.prepare(
            self.owner, workflow=self.workflow, graph=graph,
            inputs={"query": "q"}, kind="dry_run")

        async def consume():
            return [f async for f in
                    ExecutionService.stream_events(ctx, graph, {"query": "q"})]

        task = asyncio.create_task(consume())
        # 等待 paused 状态落库
        for _ in range(100):
            await asyncio.sleep(0.05)
            exe = await WorkflowExecution.get_or_none(id=ctx.execution_id)
            if exe and exe.status == "paused":
                break
        self.assertEqual(exe.status, "paused")
        ok, st = await ExecutionService.resume(ctx.execution_id, approved=True)
        self.assertTrue(ok)
        frames = await asyncio.wait_for(task, timeout=5)
        types = [f.split("\n", 1)[0].replace("event: ", "") for f in frames]
        self.assertIn("run_paused", types)
        self.assertEqual(types[-1], "run_completed")
        await exe.refresh_from_db()
        self.assertEqual(exe.status, "success")

    async def test_cancel_hitl_run(self):
        graph = hitl_graph(timeout_s=30)
        ctx = await ExecutionService.prepare(
            self.owner, workflow=self.workflow, graph=graph,
            inputs={"query": "q"}, kind="dry_run")

        async def consume():
            return [f async for f in
                    ExecutionService.stream_events(ctx, graph, {"query": "q"})]

        task = asyncio.create_task(consume())
        for _ in range(100):
            await asyncio.sleep(0.05)
            exe = await WorkflowExecution.get_or_none(id=ctx.execution_id)
            if exe and exe.status == "paused":
                break
        status = await ExecutionService.cancel(ctx.execution_id)
        self.assertEqual(status, "cancelled")
        await asyncio.wait_for(task, timeout=5)
        await exe.refresh_from_db()
        self.assertEqual(exe.status, "cancelled")
        # 预占与并发槽仍被释放（05-§1.4）
        self.qs.quota_release.assert_awaited_with("hold-h")
        self.qs.release_concurrency.assert_awaited()

    async def test_cancel_terminal_state_idempotent(self):
        exe = await WorkflowExecution.create(
            workflow_id=self.workflow.id, status="success", input_data={},
            owner_type="cus", owner_id=1)
        # 终态重复取消幂等返回当前状态
        self.assertEqual(await ExecutionService.cancel(exe.id), "success")
        self.assertEqual(await ExecutionService.cancel(999999), "not_found")


# ============================================================
# I. 断点标记（F5：启动扫描 running/paused → interrupted）
# ============================================================
class InterruptMarkTest(DbTestCase):

    async def test_mark_interrupted_on_startup(self):
        w = await Workflow.create(name="wf-i", definition={},
                                  owner_type="cus", owner_id=1)
        running = await WorkflowExecution.create(
            workflow_id=w.id, status="running", input_data={},
            owner_type="cus", owner_id=1)
        paused = await WorkflowExecution.create(
            workflow_id=w.id, status="paused", input_data={},
            owner_type="cus", owner_id=1)
        success = await WorkflowExecution.create(
            workflow_id=w.id, status="success", input_data={},
            owner_type="cus", owner_id=1)
        cancelled = await WorkflowExecution.create(
            workflow_id=w.id, status="cancelled", input_data={},
            owner_type="cus", owner_id=1)

        count = await ExecutionService.mark_interrupted_on_startup()
        self.assertEqual(count, 2)
        await running.refresh_from_db()
        await paused.refresh_from_db()
        await success.refresh_from_db()
        await cancelled.refresh_from_db()
        self.assertEqual(running.status, "interrupted")
        self.assertEqual(paused.status, "interrupted")
        self.assertIsNotNone(running.completed_at)
        self.assertIn("中断", running.error_message)
        # 终态不动
        self.assertEqual(success.status, "success")
        self.assertEqual(cancelled.status, "cancelled")


if __name__ == "__main__":
    unittest.main()

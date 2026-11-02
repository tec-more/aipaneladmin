"""
J-2 配额对账（监控项 M-9，P1）

对账口径（R-09 预占/释放闭环校验）：
- Redis HOLD_INDEX_KEY 中未过期的 hold（hold_id 为 execution_id 字符串）
- 其对应 execution 已落库终态（success/failed/cancelled/interrupted）→ 预占未随终态释放，计为差异

差异 > 0 即告警（P1），人工处置：执行 QuotaService.quota_release 或等待 HOLD_TTL 过期兜底。

crontab 建议：0 2 * * *（每日 02:00）
Redis 未启用/不可达时：P1 报告「对账跳过」（进程内降级模式无对账面，本身是 H-2 违规信号）。

运行: python scripts/ops/quota_reconcile.py
"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ops._common import (  # noqa: E402
    CheckItem, Report, close_db, emit_report, get_redis, init_db,
)

TERMINAL_STATUS = ("success", "failed", "cancelled", "interrupted")


async def main() -> Report:
    report = Report(script="quota_reconcile")

    redis = await get_redis()
    if redis is None:
        report.add(CheckItem(
            name="M-9 配额对账",
            ok=False,
            level="P1",
            detail="Redis 未启用/不可达，对账跳过（进程内降级模式无 TTL 兜底，H-2 硬约束违规信号）",
        ))
        return report

    await init_db()
    try:
        from base.common.quota.services.quota_service import HOLD_INDEX_KEY
        from base.plugins.agent.models.workflow import WorkflowExecution

        # 未过期 hold（score=expire_at > now）
        hold_ids = await redis.zrangebyscore(HOLD_INDEX_KEY, time.time(), "+inf")
        # hold_id 即 execution_id 字符串（quota_estimate 传 execution_id）；qh_ 前缀为无实例预占，跳过
        exec_ids = [int(h) for h in hold_ids if str(h).isdigit()]
        diffs = []
        if exec_ids:
            rows = await WorkflowExecution.filter(id__in=exec_ids).all()
            status_map = {r.id: r.status for r in rows}
            for eid in exec_ids:
                st = status_map.get(eid)
                if st in TERMINAL_STATUS:
                    diffs.append(f"execution_id={eid} status={st} hold 未释放")
        report.add(CheckItem(
            name="M-9 配额对账",
            ok=not diffs,
            level="P1" if diffs else "OK",
            detail=(f"未过期 hold {len(exec_ids)} 个，无差异" if not diffs
                    else f"差异 {len(diffs)} 例: " + " | ".join(diffs[:20])),
        ))
    finally:
        await close_db()
    return report


if __name__ == "__main__":
    emit_report(asyncio.run(main()))

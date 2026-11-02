"""
J-4 Trace seq 单调性抽检（监控项 M-10 / AC-15 回归哨兵，P2）

抽检口径：最近 24h 内已完成的执行实例抽 10 个，校验其 TraceEvent：
- seq 从 1 开始严格递增（seq[i] == seq[i-1] + 1），无重复、无乱序、无断号
- 存在 run_completed / run_failed / run_paused 等运行级收束事件之外的缺失暂不判定（仅查 seq 单调性）

乱序即告警（P2）：TraceWriter 批量缓冲（R-11）或 shield 化收尾引入乱序的信号。

crontab 建议：0 3 * * *（每日 03:00）

运行: python scripts/ops/trace_check.py
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ops._common import (  # noqa: E402
    CheckItem, Report, close_db, emit_report, init_db, naive_utc,
)

SAMPLE_SIZE = 10


async def main() -> Report:
    report = Report(script="trace_check")
    await init_db()
    try:
        from base.plugins.agent.models.trace_event import TraceEvent
        from base.plugins.agent.models.workflow import WorkflowExecution

        since = datetime.utcnow() - timedelta(hours=24)
        rows = await WorkflowExecution.filter(
            status__in=["success", "failed", "cancelled", "interrupted"]
        ).order_by("-id").limit(200).all()
        exec_ids = [r.id for r in rows
                    if (naive_utc(r.completed_at) or datetime.min) >= since][:SAMPLE_SIZE]

        if not exec_ids:
            report.add(CheckItem(name="M-10 Trace seq 抽检", ok=True, level="OK",
                                 detail="近 24h 无已完成执行实例，跳过"))
            return report

        bad = []
        checked = 0
        for eid in exec_ids:
            events = await TraceEvent.filter(execution_id=eid).order_by("seq").all()
            if not events:
                bad.append(f"execution_id={eid} 无 trace 事件")
                continue
            checked += 1
            seqs = [e.seq for e in events]
            expected = list(range(seqs[0], seqs[0] + len(seqs)))
            if seqs != expected:
                bad.append(f"execution_id={eid} seq 非严格递增: {seqs[:10]}{'...' if len(seqs) > 10 else ''}")

        report.add(CheckItem(
            name="M-10 Trace seq 单调性",
            ok=not bad,
            level="P2" if bad else "OK",
            detail=(f"抽检 {checked}/{len(exec_ids)} 个执行实例，seq 全部严格递增" if not bad
                    else f"{len(bad)} 例异常: " + " | ".join(bad[:10])),
        ))
    finally:
        await close_db()
    return report


if __name__ == "__main__":
    emit_report(asyncio.run(main()))

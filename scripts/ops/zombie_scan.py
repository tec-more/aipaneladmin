"""
J-1 僵尸执行巡检（监控项 M-1，P0 兜底网）

判定：status ∈ (running, paused) 且 updated_at 停滞超阈值
- dry_run：30 分钟（试跑正常秒级完成，30min 停滞必为异常）
- run：24 小时（HITL 合法暂停可达 72h，保守阈值避免误报）

R-1 安全边界：只告警输出异常实例清单，不自动修改 DB、不调用 cancel 接口。
僵尸实例的人工处置路径：DB 直改终态 + 检查并发槽（或重启进程清槽）。

crontab 建议：*/5 * * * *（5 分钟/次）；退出码 2（P0）时触发告警。

运行: python scripts/ops/zombie_scan.py
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ops._common import (  # noqa: E402
    CheckItem, Report, close_db, emit_report, init_db, naive_utc,
)

DRY_RUN_TIMEOUT_MIN = 30
RUN_TIMEOUT_HOURS = 24


async def main() -> Report:
    report = Report(script="zombie_scan")
    await init_db()
    try:
        from base.plugins.agent.models.workflow import WorkflowExecution

        now = datetime.utcnow()
        rows = await WorkflowExecution.filter(status__in=["running", "paused"]).all()
        zombies = []
        for r in rows:
            updated = naive_utc(getattr(r, "updated_at", None)) or naive_utc(r.started_at)
            threshold = (timedelta(minutes=DRY_RUN_TIMEOUT_MIN) if r.kind == "dry_run"
                         else timedelta(hours=RUN_TIMEOUT_HOURS))
            if updated and (now - updated) > threshold:
                zombies.append(
                    f"id={r.id} kind={r.kind} status={r.status} "
                    f"owner={r.owner_type}:{r.owner_id} stalled={now - updated}"
                )
        report.add(CheckItem(
            name="M-1 僵尸执行实例",
            ok=not zombies,
            level="P0" if zombies else "OK",
            detail="无异常" if not zombies
                   else f"{len(zombies)} 例: " + " | ".join(zombies[:20]),
        ))
    finally:
        await close_db()
    return report


if __name__ == "__main__":
    emit_report(asyncio.run(main()))

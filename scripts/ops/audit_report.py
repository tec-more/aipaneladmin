"""
J-3 取消审计占比日报（监控项 M-5 / 遗留 R-1，P2 趋势项）

口径：最近 24h 内 status=cancelled 的执行中，output_data.tokens 为 null/缺失 的占比
- tokens 为 null → runner 被强杀路径（SSE 断开触发自愈，anyio cancel scope 连带 cancel，T15 已定性为传输层语义）
- tokens 为字典 → 协作式取消（ExecutionCancelled 正常路径，有「执行被取消」审计日志）

占比环比突增（监控平台按日对比，阈值建议 >20pp）说明断开场景协作唤醒退化面扩大，
需复查网关/代理层取消传播（BUG-T15-014 关联）。

crontab 建议：0 9 * * *（每日 09:00 出日报）；本脚本始终退出码 0（趋势项，不直接告警）。

运行: python scripts/ops/audit_report.py
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ops._common import (  # noqa: E402
    CheckItem, Report, close_db, emit_report, init_db, naive_utc,
)


async def main() -> Report:
    report = Report(script="audit_report")
    await init_db()
    try:
        from base.plugins.agent.models.workflow import WorkflowExecution

        since = datetime.utcnow() - timedelta(hours=24)
        rows = await WorkflowExecution.filter(status="cancelled").all()
        # updated_at 在部分 Tortoise 版本为只读 Python 侧时间，统一 Python 过滤保证跨驱动一致
        recent = [r for r in rows
                  if (naive_utc(getattr(r, "updated_at", None)) or naive_utc(r.started_at)
                      or datetime.min) >= since]

        total = len(recent)
        killed = []   # tokens 缺失/None → 强杀路径
        for r in recent:
            tokens = (r.output_data or {}).get("tokens") if isinstance(r.output_data, dict) else None
            if not tokens:
                killed.append(r.id)
        ratio = (len(killed) / total * 100.0) if total else 0.0

        report.add(CheckItem(
            name="M-5 取消审计占比（tokens=NULL 强杀路径）",
            ok=True,  # 趋势日报项，不直接告警；阈值判定由监控平台按日环比执行
            level="OK",
            detail=(f"近 24h cancelled={total} 例，强杀路径 {len(killed)} 例，占比 {ratio:.1f}%"
                    + (f"；强杀实例: {killed[:20]}" if killed else "")),
        ))
    finally:
        await close_db()
    return report


if __name__ == "__main__":
    emit_report(asyncio.run(main()))

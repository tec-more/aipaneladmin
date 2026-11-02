"""
运维巡检公共层：Tortoise 初始化 / Redis 连接 / 报告输出落盘

溯源：docs/ops/grayscale-monitoring-checklist.md 第四部分定时巡检任务（J-1~J-4）
边界红线：本包脚本只读 DB/Redis 并输出报告，不修改任何业务状态、不调用业务接口
运行方式：python scripts/ops/<script>.py（sys.path 自举，crontab 可直接调度）
退出码约定：worst_level=P0 → 2；P1 → 1；其余 → 0（供告警平台/crontab 接入判定）
"""
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 报告落盘目录（对齐 R-2 测试基建落盘规范精神：取证可追溯）
REPORT_DIR = ROOT / "reports" / "ops"

_LEVEL_ORDER = {"OK": 0, "P2": 1, "P1": 2, "P0": 3}


@dataclass
class CheckItem:
    """巡检项结果"""
    name: str      # 检查项名（对齐监控清单 M-x 编号）
    ok: bool       # 是否通过
    level: str     # OK/P0/P1/P2（对齐监控清单告警级别）
    detail: str    # 明细（异常实例 ID 列表、差异计数等）


@dataclass
class Report:
    """巡检报告：stdout 表格 + JSON 落盘"""
    script: str
    generated_at: str = ""
    items: List[CheckItem] = field(default_factory=list)

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat(timespec="seconds")

    def add(self, item: CheckItem) -> None:
        self.items.append(item)

    @property
    def worst_level(self) -> str:
        if not self.items:
            return "OK"
        return max(self.items, key=lambda i: _LEVEL_ORDER.get(i.level, 0)).level

    @property
    def exit_code(self) -> int:
        wl = self.worst_level
        return 2 if wl == "P0" else (1 if wl == "P1" else 0)

    def render(self) -> str:
        lines = [f"===== {self.script} 巡检报告 ({self.generated_at}) ====="]
        for i in self.items:
            mark = "OK " if i.ok else "!!!"
            lines.append(f"[{mark}] [{i.level}] {i.name}: {i.detail}")
        lines.append(f"汇总: worst_level={self.worst_level} exit_code={self.exit_code}")
        return "\n".join(lines)

    def save(self) -> Path:
        day = datetime.now().strftime("%Y%m%d")
        ts = datetime.now().strftime("%H%M%S")
        out_dir = REPORT_DIR / day
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.script}_{ts}.json"
        path.write_text(
            json.dumps({"script": self.script, "generated_at": self.generated_at,
                        "worst_level": self.worst_level, "exit_code": self.exit_code,
                        "items": [asdict(i) for i in self.items]},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path


async def init_db() -> None:
    """Tortoise 初始化（复用主应用 ORM 配置，tests 已验证模式）"""
    from tortoise import Tortoise
    from base.common.setting import TORTOISE_ORM
    await Tortoise.init(config=TORTOISE_ORM)


async def close_db() -> None:
    from tortoise import Tortoise
    await Tortoise.close_connections()


async def get_redis() -> Optional[object]:
    """
    获取原生 redis 客户端（quota 键操作需要 hgetall/zrangebyscore 等原生命令）。
    复用 RedisCache 单例连接；未启用/不可达返回 None。
    与 QuotaService._redis 保持同一访问路径（项目内既有先例）。
    """
    try:
        from base.common.cache import RedisCache
        cache = await RedisCache.get_instance()
        if RedisCache.is_enabled():
            return cache._client  # noqa: SLF001（同 quota_service._redis 先例）
    except Exception:
        pass
    return None


def emit_report(report: Report) -> None:
    """公共出口：stdout 渲染 + 落盘 + 退出码"""
    print(report.render(), flush=True)
    path = report.save()
    print(f"报告落盘: {path}", flush=True)
    sys.exit(report.exit_code)


def naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """统一转 naive UTC 比较（TimestampMixin 在不同驱动下可能带 tzinfo）"""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt

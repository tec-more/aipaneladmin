"""
AIF2F 插件钩子函数
"""

import logging
from fastapi import FastAPI

logger = logging.getLogger(__name__)


async def on_enable(app: FastAPI):
    """插件启用时的钩子"""
    logger.info("AIF2F插件启用")
    # TODO: 初始化数据
    # await init_default_membership_levels()


async def on_disable(app: FastAPI):
    """插件禁用时的钩子"""
    logger.info("AIF2F插件禁用")


async def on_startup(app: FastAPI):
    """应用启动时的钩子"""
    logger.info("AIF2F插件启动")
    # TODO: 启动定时任务
    # - 检查过期订单
    # - 检查过期会员
    # - 统计数据


async def on_shutdown(app: FastAPI):
    """应用关闭时的钩子"""
    logger.info("AIF2F插件关闭")


async def init_default_membership_levels():
    """初始化默认会员等级"""
    from base.plugins.aif2f.models import MembershipLevel, LevelType

    # 检查是否已存在
    existing = await MembershipLevel.filter(is_active=True).count()
    if existing > 0:
        return

    # 创建默认会员等级
    default_levels = [
        {
            "level_type": LevelType.TRIAL,
            "level": 0,
            "name": "体验会员",
            "description": "7天免费体验",
            "duration_days": 7,
            "duration_hours": 0,
            "price": 0,
            "original_price": None,
            "bonus_hours": 0,
            "features": ["基础翻译功能", "每日2小时限制"],
            "sort_order": 0
        },
        {
            "level_type": LevelType.MONTHLY,
            "level": 1,
            "name": "月度会员",
            "description": "30天会员",
            "duration_days": 30,
            "duration_hours": 0,
            "price": 29.9,
            "original_price": 39.9,
            "bonus_hours": 0,
            "features": ["无限翻译", "优先客服", "API访问"],
            "sort_order": 1
        },
        {
            "level_type": LevelType.QUARTERLY,
            "level": 2,
            "name": "季度会员",
            "description": "90天会员",
            "duration_days": 90,
            "duration_hours": 0,
            "price": 79.9,
            "original_price": 99.9,
            "bonus_hours": 0,
            "features": ["无限翻译", "优先客服", "API访问", "离线翻译"],
            "sort_order": 2
        },
        {
            "level_type": LevelType.FIBONACCI,
            "level": 1,
            "name": "1小时",
            "description": "充值1小时",
            "duration_days": 0,
            "duration_hours": 1,
            "price": 1.0,
            "original_price": None,
            "bonus_hours": 0,
            "features": ["按需付费"],
            "sort_order": 10
        },
        {
            "level_type": LevelType.FIBONACCI,
            "level": 5,
            "name": "5小时",
            "description": "充值5小时",
            "duration_days": 0,
            "duration_hours": 5,
            "price": 5.0,
            "original_price": None,
            "bonus_hours": 1,
            "features": ["按需付费", "赠送1小时"],
            "sort_order": 11
        },
        {
            "level_type": LevelType.FIBONACCI,
            "level": 20,
            "name": "20小时",
            "description": "充值20小时",
            "duration_days": 0,
            "duration_hours": 20,
            "price": 20.0,
            "original_price": None,
            "bonus_hours": 5,
            "features": ["按需付费", "赠送5小时"],
            "sort_order": 12
        },
        {
            "level_type": LevelType.FIBONACCI,
            "level": 50,
            "name": "50小时",
            "description": "充值50小时",
            "duration_days": 0,
            "duration_hours": 50,
            "price": 50.0,
            "original_price": None,
            "bonus_hours": 10,
            "features": ["按需付费", "赠送10小时", "优先客服"],
            "sort_order": 13
        }
    ]

    for level_data in default_levels:
        await MembershipLevel.create(**level_data)

    logger.info(f"初始化了 {len(default_levels)} 个默认会员等级")

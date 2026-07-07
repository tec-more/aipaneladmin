from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
from base.plugins.audit.models.audit_log import DataChangeLog
from base.plugins.audit.schemas.audit_log import DataChangeLogCreate
class DataChangeService:
    model = "data_change"
    """数据变更服务"""

    @staticmethod
    async def create_log(data: DataChangeLogCreate) -> DataChangeLog:
        """创建数据变更日志"""
        if isinstance(data, dict):
            log = await DataChangeLog.create(**data)
        else:
            log = await DataChangeLog.create(**data.model_dump(exclude_unset=True))
        return log

    @staticmethod
    async def get_log_by_id(log_id: int) -> Optional[DataChangeLog]:
        """根据ID获取数据变更日志"""
        return await DataChangeLog.get_or_none(id=log_id)

    @staticmethod
    async def get_log_list(
        page: int = 1,
        page_size: int = 20,
        table_name: Optional[str] = None,
        record_id: Optional[str] = None,
        change_type: Optional[str] = None,
        username: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Tuple[List[DataChangeLog], int]:
        """获取数据变更日志列表"""
        query = DataChangeLog.all()

        if table_name:
            query = query.filter(table_name=table_name)
        if record_id:
            query = query.filter(record_id=record_id)
        if change_type:
            query = query.filter(change_type=change_type)
        if username:
            query = query.filter(username__icontains=username)
        if start_time:
            query = query.filter(created_at__gte=start_time)
        if end_time:
            query = query.filter(created_at__lte=end_time)

        total = await query.count()
        offset = (page - 1) * page_size
        logs = await query.offset(offset).limit(page_size).order_by("-created_at")

        return logs, total

    @staticmethod
    async def get_changes_by_record(table_name: str, record_id: str) -> List[DataChangeLog]:
        """获取某条记录的所有变更历史"""
        logs = await DataChangeLog.filter(
            table_name=table_name,
            record_id=record_id
        ).order_by("-created_at")
        return logs

    @staticmethod
    async def delete_old_logs(days: int = 90) -> int:
        """删除旧日志"""
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = await DataChangeLog.filter(created_at__lt=cutoff_date).delete()
        return deleted_count

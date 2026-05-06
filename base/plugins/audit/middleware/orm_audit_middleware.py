from tortoise import signals
from tortoise.models import Model
from base.plugins.audit.services.data_change_service import DataChangeService
from base.common.context import current_user_id, current_username
from base.common.setting import settings


AUDIT_EXCLUDE_MODELS = [
    'AuditLog', 'InputLayerLog', 'DecisionLayerLog', 'ExecutionLayerLog',
    'OutputLayerLog', 'SystemLayerLog', 'DataChangeLog', 'LoginLog',
    'RiskAuditRecord', 'AuditReport', 'AuditConfig'
]


def is_audit_enabled() -> bool:
    return getattr(settings, 'AUDIT_ENABLED', True)


def is_data_change_log_enabled() -> bool:
    return getattr(settings, 'AUDIT_LOG_DATA_CHANGES', True)


def is_model_excluded(model_name: str) -> bool:
    return model_name in AUDIT_EXCLUDE_MODELS


def get_instance_dict(instance) -> dict:
    data = {}
    for field in instance._meta.fields:
        if field != 'id':
            value = getattr(instance, field, None)
            if not isinstance(value, Model):
                data[field] = value
    return data


@signals.pre_delete()
async def on_model_delete(sender, instance, using_db):
    if not is_audit_enabled() or not is_data_change_log_enabled():
        return
    
    model_name = sender.__name__
    if is_model_excluded(model_name):
        return
    
    user_id = current_user_id.get()
    username = current_username.get()
    table_name = sender._meta.table
    
    try:
        await DataChangeService.create_log({
            "table_name": table_name,
            "record_id": str(instance.id),
            "change_type": "DELETE",
            "before_data": get_instance_dict(instance),
            "user_id": user_id,
            "username": username,
        })
    except Exception as e:
        print(f"Failed to record delete audit: {e}")


@signals.post_save()
async def on_model_save(sender, instance, created, using_db, update_fields):
    if not is_audit_enabled() or not is_data_change_log_enabled():
        return
    
    model_name = sender.__name__
    if is_model_excluded(model_name):
        return
    
    user_id = current_user_id.get()
    username = current_username.get()
    table_name = sender._meta.table
    
    try:
        if created:
            await DataChangeService.create_log({
                "table_name": table_name,
                "record_id": str(instance.id),
                "change_type": "CREATE",
                "after_data": get_instance_dict(instance),
                "user_id": user_id,
                "username": username,
            })
        else:
            await DataChangeService.create_log({
                "table_name": table_name,
                "record_id": str(instance.id),
                "change_type": "UPDATE",
                "changed_fields": list(update_fields) if update_fields else [],
                "after_data": get_instance_dict(instance),
                "user_id": user_id,
                "username": username,
            })
    except Exception as e:
        print(f"Failed to record save audit: {e}")


def register_orm_audit_handlers():
    pass
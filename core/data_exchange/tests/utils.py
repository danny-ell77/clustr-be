from django.contrib.contenttypes.models import ContentType

from core.data_exchange.models import ExportTask, ImportTask


def create_test_export_task(
    owner_id: str, created_by: str, content_type: ContentType, **kwargs
) -> tuple[dict, ExportTask]:
    valid_data = {
        "owner_id": owner_id,
        "created_by": created_by,
        "status": ExportTask.TaskStatuses.IN_PROGRESS,
        "content_type": content_type,
        "sql_query": "test sql",
        "notify_on_success": True,
    }
    valid_data.update(kwargs)
    return valid_data, ExportTask.objects.create(**valid_data)


def create_test_import_task(
    owner_id: str, created_by: str, content_type: ContentType, **kwargs
) -> tuple[dict, ImportTask]:
    valid_data = {
        "owner_id": owner_id,
        "created_by": created_by,
        "status": ExportTask.TaskStatuses.IN_PROGRESS,
        "content_type": content_type,
        "notify_on_success": True,
    }
    valid_data.update(kwargs)
    return valid_data, ImportTask.objects.create(**valid_data)

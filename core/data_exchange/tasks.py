import logging
from datetime import timedelta
from typing import Type, Optional, Any
from uuid import UUID

from celery import shared_task
from django.db.models import Model

from core.data_exchange.exceptions import (
    DataExportException,
    DataImportException,
)


from core.data_exchange.includes.types import ExportOutput, ImportResult
from core.data_exchange.includes.types import StorageLocations, FileFormats
from core.data_exchange.models import ExportTask, ImportTask
from core.data_exchange.serializers import DynamicFieldsSerializer

logger = logging.getLogger(__name__)
EXPORT_TASK_TIME_LIMIT = timedelta(minutes=5).total_seconds()
IMPORT_TASK_TIME_LIMIT = timedelta(minutes=10).total_seconds()


@shared_task(
    ignore_result=False,
    name="export_records",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    serializer="pickle",
    time_limit=EXPORT_TASK_TIME_LIMIT,
)
def export_records(
    model_class: Type[Model],
    queryset_dict: dict,  # Queryset query string
    serializer_class: Type[DynamicFieldsSerializer],
    serializer_extra_fields: Optional[list[str]],
    task: ExportTask,
    output_format: FileFormats,
    storage_location: StorageLocations,
    owner_id: UUID,
    always_on_external=True,
) -> Optional[ExportOutput]:
    from core.data_exchange.includes.record_exporter import RecordExporter

    try:
        exporter = RecordExporter(
            model_class=model_class,
            queryset_dict=queryset_dict,
            serializer_class=serializer_class,
            serializer_extra_fields=serializer_extra_fields,
            output_format=output_format,
            storage_location=storage_location,
            owner_id=owner_id,
            always_on_external=always_on_external,
        )
        exported_record = exporter.export()
        task.mark_as_successful(exported_record.external_file_id)
        return exported_record
    except DataExportException as error:
        logger.error(
            f"Failed for export external file for model class - {model_class.__name__} "
            f"owner - {owner_id}",
            exc_info=error,
        )
        task.mark_as_failed()


@shared_task(
    ignore_result=True,  # We have no need for the result
    name="import_records",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    serializer="pickle",
    time_limit=IMPORT_TASK_TIME_LIMIT,
)
def import_records(
    import_data: dict[str, Any],
    import_serializer_class: Type[DynamicFieldsSerializer],
    serializer_context: Optional[dict],
    task: ImportTask,
) -> Optional[ImportResult]:
    from core.data_exchange.includes.record_importer import RecordImporter

    try:
        importer = RecordImporter(
            import_data=import_data,
            import_serializer_class=import_serializer_class,
            serializer_context=serializer_context,
        )
        import_result = importer.import_()
        if import_result.errors and not import_result.data:
            task.mark_as_failed(errors=import_result.serialized_errors())
        else:
            task.mark_as_successful(
                imported_object_ids=import_result.object_ids,
                errors=import_result.serialized_errors(),
                total_skipped=import_result.total_skipped,
            )
        return import_result
    except DataImportException as error:
        logger.error(
            f"An error occurred while attempting to import data with payload - {import_data}",
            exc_info=error,
        )
        task.mark_as_failed(errors=[])

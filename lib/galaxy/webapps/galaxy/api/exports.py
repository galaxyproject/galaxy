"""
API operations on user exports.
"""

import logging
from typing import (
    Annotated,
    Optional,
)

from fastapi import Query

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.export_tracker import StoreExportTracker
from galaxy.schema.schema import (
    ExportObjectMetadata,
    ExportObjectRequestMetadata,
    ExportObjectResultMetadata,
    ExportTaskListResponse,
    ObjectExportTaskResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["exports"])


@router.cbv
class FastAPIExports:
    export_tracker: StoreExportTracker = depends(StoreExportTracker)

    @router.get(
        "/api/exports",
        summary="Get recent exports for the current user.",
        response_model_exclude_unset=True,
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        limit: Annotated[
            Optional[int],
            Query(
                title="Limit",
                description="Maximum number of exports to return.",
            ),
        ] = 50,
        days: Annotated[
            int,
            Query(
                title="Days",
                description="Number of days to look back.",
            ),
        ] = 30,
    ) -> ExportTaskListResponse:
        """
        Returns a list of recent exports (to remote file sources) for the current user.
        """
        if trans.anonymous:
            return ExportTaskListResponse(root=[])

        user_id = trans.user.id
        exports = self.export_tracker.get_user_exports(user_id, limit=limit, days=days)

        results = []
        for export in exports:
            export_metadata = None
            if export.export_metadata:
                export_metadata = self._parse_export_metadata(export.export_metadata)

            # Determine if export is preparing or ready
            is_preparing = export_metadata is None or export_metadata.result_data is None
            is_ready = export_metadata is not None and export_metadata.is_ready()

            results.append(
                ObjectExportTaskResponse(
                    id=export.id,
                    ready=is_ready,
                    preparing=is_preparing,
                    up_to_date=is_ready,  # Remote exports are always "up to date" once complete
                    task_uuid=export.task_uuid,
                    create_time=export.create_time,
                    export_metadata=export_metadata,
                )
            )

        return ExportTaskListResponse(root=results)

    def _parse_export_metadata(self, metadata: dict) -> Optional[ExportObjectMetadata]:
        """Parse export metadata dict without double-encoding ID fields.

        We use model_construct() to skip Pydantic validation because the ID fields
        are stored as already-encoded strings, and the BeforeValidator on
        EncodedDatabaseIdField would encode them again.
        """
        request_data_raw = metadata.get("request_data", {})
        result_data_raw = metadata.get("result_data")

        request_data = ExportObjectRequestMetadata.model_construct(
            object_id=request_data_raw.get("object_id"),
            object_type=request_data_raw.get("object_type"),
            user_id=request_data_raw.get("user_id"),
            payload=request_data_raw.get("payload"),
        )

        result_data = None
        if result_data_raw:
            result_data = ExportObjectResultMetadata.model_construct(
                success=result_data_raw.get("success"),
                uri=result_data_raw.get("uri"),
                error=result_data_raw.get("error"),
            )

        return ExportObjectMetadata.model_construct(
            request_data=request_data,
            result_data=result_data,
        )

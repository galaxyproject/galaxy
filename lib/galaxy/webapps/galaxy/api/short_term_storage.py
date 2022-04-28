"""
API operations around galaxy.web.short_term_storage infrastructure.
"""
from starlette.responses import FileResponse

from galaxy.web.short_term_storage import (
    ShortTermStorageMonitor,
    ShortTermStorageServeCancelledInformation,
    ShortTermStorageServeCompletedInformation,
)
from . import (
    depends,
    Router,
)

router = Router(tags=["short_term_storage"])


@router.cbv
class FastAPIShortTermStorage:
    # typing here is not ideal, mypy is the issue xref https://github.com/python/mypy/issues/5374
    short_term_storage_monitor: ShortTermStorageMonitor = depends(ShortTermStorageMonitor)  # type: ignore[misc]

    @router.get(
        "/api/short_term_storage/{storage_request_id}/ready",
        summary="Determine if specified storage request ID is ready for download.",
        response_description="Boolean indicating if the storage is ready.",
    )
    def is_ready(self, storage_request_id: str) -> bool:
        storage_target = self.short_term_storage_monitor.recover_target(storage_request_id)
        return self.short_term_storage_monitor.is_ready(storage_target)

    @router.get(
        "/api/short_term_storage/{storage_request_id}",
        summary="Serve the staged download specified by request ID.",
        response_description="Raw contents of the file.",
        response_class=FileResponse,
        responses={
            200: {
                "description": "The archive file containing the History.",
            },
            204: {
                "description": "Request was cancelled without an exception condition recorded.",
            },
        },
    )
    def serve(self, storage_request_id: str):
        storage_target = self.short_term_storage_monitor.recover_target(storage_request_id)
        serve_info = self.short_term_storage_monitor.get_serve_info(storage_target)
        if isinstance(serve_info, ShortTermStorageServeCompletedInformation):
            return FileResponse(
                path=serve_info.target.path,
                media_type=serve_info.mime_type,
                filename=serve_info.filename,
            )

        assert isinstance(serve_info, ShortTermStorageServeCancelledInformation)
        raise serve_info.message_exception

import abc
import contextlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
    Union,
)
from uuid import (
    UUID,
    uuid4,
)

from galaxy.exceptions import (
    InternalServerError,
    MessageException,
    NoContentException,
    ObjectNotFound,
)
from galaxy.exceptions.error_codes import error_codes_by_int_code
from galaxy.schema.schema import OptionalNumberT
from galaxy.util import (
    directory_hash_id,
    is_uuid,
    safe_makedirs,
)
from galaxy.web.framework.decorators import api_error_message

now = datetime.utcnow
DEFAULT_STORAGE_DURATION = 24 * 60 * 60  # store for a day by default


@dataclass
class ShortTermStorageConfiguration:
    short_term_storage_directory: str
    default_storage_duration: OptionalNumberT = None
    maximum_storage_duration: OptionalNumberT = None


@dataclass
class ShortTermStorageTargetSecurity:
    user_id: Optional[int] = None
    session_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Optional[int]]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(self, as_dict: Dict[str, Optional[int]]) -> "ShortTermStorageTargetSecurity":
        return ShortTermStorageTargetSecurity(
            user_id=as_dict.get("user_id"),
            session_id=as_dict.get("session_id"),
        )


@dataclass
class ShortTermStorageTarget:
    request_id: UUID
    raw_path: str
    duration: OptionalNumberT = None

    @property
    def path(self):
        return Path(self.raw_path)


@dataclass
class ShortTermStorageServeCompletedInformation:
    target: ShortTermStorageTarget
    mime_type: str
    filename: str
    security: ShortTermStorageTargetSecurity


@dataclass
class ShortTermStorageServeCancelledInformation:
    target: ShortTermStorageTarget
    status_code: int
    exception: Optional[Dict[str, Any]]

    @property
    def message_exception(self) -> MessageException:
        serialized_exception = self.exception
        if not serialized_exception:
            raise NoContentException()
        exception_obj = MessageException()
        exception_obj.status_code = self.status_code
        exception_obj.err_code = error_codes_by_int_code[serialized_exception["err_code"]]
        exception_obj.err_msg = serialized_exception["err_msg"]
        return exception_obj


ShortTermStorageServeInformation = Union[
    ShortTermStorageServeCompletedInformation, ShortTermStorageServeCancelledInformation
]


class ShortTermStorageAllocator(metaclass=abc.ABCMeta):
    # TODO: Implement upstream_mod_zip=False, upstream_gzip=False - in initial request and serving...
    @abc.abstractmethod
    def new_target(
        self,
        filename: str,
        mime_type: str,
        duration: Optional[int] = None,
        security: Optional[ShortTermStorageTargetSecurity] = None,
    ) -> ShortTermStorageTarget:
        """Return a new ShortTermStorageTarget for this short term file request."""


class ShortTermStorageMonitor(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def is_ready(self, target: ShortTermStorageTarget) -> bool:
        """Check if storage is ready."""

    @abc.abstractmethod
    def get_serve_info(self, target: ShortTermStorageTarget) -> ShortTermStorageServeInformation:
        """Get information required to serve this short term storage target."""

    @abc.abstractmethod
    def finalize(self, target: ShortTermStorageTarget) -> None:
        """Indicate the file is ready to be served."""

    @abc.abstractmethod
    def cancel(self, target: ShortTermStorageTarget, exception: Optional[MessageException] = None) -> None:
        """Store metadata for failed task.

        Implementation is responsible for indicating target is finalized as well.
        """

    @abc.abstractmethod
    def target_path(self, target: ShortTermStorageTarget) -> Path:
        """Return fully qualified path on this server for specified target."""

    @abc.abstractmethod
    def cleanup(self) -> None:
        """Cleanup old requests."""

    @abc.abstractmethod
    def recover_target(self, request_id: UUID) -> ShortTermStorageTarget:
        """Return an existing ShortTermStorageTarget from a specified request_id."""


class ShortTermStorageManager(ShortTermStorageAllocator, ShortTermStorageMonitor):
    def __init__(self, config: ShortTermStorageConfiguration):
        self._config = config

    def new_target(
        self,
        filename: str,
        mime_type: str,
        duration: OptionalNumberT = None,
        security: Optional[ShortTermStorageTargetSecurity] = None,
    ) -> ShortTermStorageTarget:
        if security is None:
            security = ShortTermStorageTargetSecurity()
        request_id = uuid4()
        target_directory = self._directory(request_id)
        duration = duration or self._config.default_storage_duration or DEFAULT_STORAGE_DURATION
        maximum_storage_duration = self._config.maximum_storage_duration
        if duration and maximum_storage_duration and duration > maximum_storage_duration:
            duration = maximum_storage_duration
        target = ShortTermStorageTarget(
            request_id=request_id, raw_path=str(target_directory / "target"), duration=duration
        )
        safe_makedirs(target_directory)
        # optimize by placing the deletion time outside JSON as new file...
        request_info = {
            "filename": filename,
            "mime_type": mime_type,
            "duration": duration,
            "created": str(now()),
            "security": security.to_dict(),
        }
        self._store_metadata(target_directory, "request", request_info)
        return target

    def recover_target(self, request_id: UUID) -> ShortTermStorageTarget:
        target_directory = self._directory(request_id)
        target = ShortTermStorageTarget(request_id=request_id, raw_path=str(target_directory / "target"))
        return target

    def is_ready(self, target: ShortTermStorageTarget) -> bool:
        """Check if storage is ready."""
        return self._finalized_path(target).exists()

    def get_serve_info(self, target: ShortTermStorageTarget) -> ShortTermStorageServeInformation:
        """Get information required to serve this short term storage target."""
        cancelled = self._cancelled_path(target)
        serve_info: ShortTermStorageServeInformation
        target_directory = self._directory(target)
        if cancelled.exists():
            exception_metadata = self._load_metadata(target_directory, "cancelled")
            serve_info = ShortTermStorageServeCancelledInformation(
                target=target,
                status_code=exception_metadata["status_code"],
                exception=exception_metadata["exception"],
            )
        else:
            request_metadata = self._load_metadata(target_directory, "request")
            serve_info = ShortTermStorageServeCompletedInformation(
                target=target,
                filename=request_metadata["filename"],
                mime_type=request_metadata["mime_type"],
                security=ShortTermStorageTargetSecurity.from_dict(request_metadata["security"]),
            )
        return serve_info

    def cancel(self, target: ShortTermStorageTarget, exception: Optional[MessageException] = None):
        """Write metadata for failed task."""
        if exception:
            exception_json = {
                "status_code": exception.status_code,
                "exception": api_error_message(None, exception=exception),
            }
        else:
            exception_json = {"status_code": 204, "exception": None}  # NO CONTENT
        self._store_metadata(self._directory(target), "cancelled", exception_json)
        self.finalize(target)

    def finalize(self, target: ShortTermStorageTarget) -> None:
        """Indicate the file is ready to be served."""
        self._finalized_path(target).touch()

    def target_path(self, target: ShortTermStorageTarget) -> Path:
        return self._directory(target) / "target"

    def _cancelled_path(self, target: ShortTermStorageTarget) -> Path:
        return self._directory(target) / "cancelled.json"

    def _finalized_path(self, target: ShortTermStorageTarget) -> Path:
        return self._directory(target) / "finalized"

    def _store_metadata(self, target_directory: Path, meta_name: str, meta_value: Any):
        meta_path = target_directory / f"{meta_name}.json"
        with open(meta_path, "w") as f:
            json.dump(meta_value, f)

    def _load_metadata(self, target_directory: Path, meta_name: str):
        meta_path = target_directory / f"{meta_name}.json"
        if not meta_path.exists():
            raise ObjectNotFound
        with open(meta_path) as f:
            return json.load(f)

    def _directory(self, target: Union[UUID, ShortTermStorageTarget]) -> Path:
        if isinstance(target, ShortTermStorageTarget):
            request_id = target.request_id
        else:
            request_id = target
        relative_directory = directory_hash_id(request_id) + [str(request_id)]
        return self._root.joinpath(*relative_directory)

    def _cleanup_if_needed(self, request_id: UUID):
        request_metadata = self._load_metadata(self._directory(request_id), "request")
        duration = request_metadata["duration"]
        creation_datetime_str = request_metadata["created"]
        unprintStrptimeFmt = "%Y-%m-%d %H:%M:%S.%f"
        creation_datetime = datetime.strptime(creation_datetime_str, unprintStrptimeFmt)
        request_time = now() - creation_datetime
        request_seconds = request_time.total_seconds()
        if request_seconds > duration:
            self._delete(request_id)

    def _delete(self, request_id: UUID):
        shutil.rmtree(self._directory(request_id))

    def cleanup(self):
        for directory in self._root.glob("*/*/*/*"):
            request_id = os.path.basename(directory)
            if not is_uuid(request_id):
                continue
            self._cleanup_if_needed(UUID(request_id))

    @property
    def _root(self) -> Path:
        return Path(self._config.short_term_storage_directory)


@contextlib.contextmanager
def storage_context(short_term_storage_request_id: UUID, short_term_storage_monitor: ShortTermStorageMonitor):
    target = short_term_storage_monitor.recover_target(short_term_storage_request_id)
    try:
        yield target
    except MessageException as e:
        short_term_storage_monitor.cancel(target, exception=e)
        raise
    except Exception as e:
        short_term_storage_monitor.cancel(target, exception=InternalServerError(f"Unknown error: {e}"))
        raise
    short_term_storage_monitor.finalize(target)

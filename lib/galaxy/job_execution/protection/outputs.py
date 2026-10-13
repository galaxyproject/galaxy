"""Protect the outputs of protected jobs before Galaxy persists them.

Runs on the compute host while collecting outputs (``set_metadata``). Every output
file is encrypted in place right before it would be pushed to the object store,
whatever way the output was produced (declared, ``from_work_dir``, discovered,
collection element, extra files). The result for every output is recorded in a
sidecar file that Galaxy checks when finishing the job, and from which it creates
the grants to use the outputs in further jobs.
"""

import json
import logging
import os
import shutil
import threading
from concurrent.futures import (
    ThreadPoolExecutor,
    wait,
)
from typing import (
    Any,
    TYPE_CHECKING,
)

from galaxy.datatypes import sniff
from galaxy.util.crypt4gh import (
    CRYPT4GH_FILE_EXT,
    iter_relpaths,
    unwrap_crypt4gh_file_ext,
    wrap_crypt4gh_file_ext,
)
from . import (
    load_runtime,
    ProtectedFileResult,
    ProtectedJobRuntime,
    ProtectionError,
    ProtectionPlan,
    write_private_file,
)

if TYPE_CHECKING:
    from galaxy.datatypes.registry import Registry
    from galaxy.model import DatasetInstance

log = logging.getLogger(__name__)

SIDECAR_FILE = os.path.join("metadata", "outputs_populated", "protection.json")

OUTCOME_PROTECTED = "protected"
OUTCOME_PURGED = "purged"
OUTCOME_DEFERRED = "deferred"
OUTCOME_FAILED = "failed"
# Outputs without content, nothing to protect.
CONTENTLESS_OUTCOMES = (OUTCOME_PURGED, OUTCOME_DEFERRED)
# Each protected file takes a request to the key service.
MAX_CONCURRENT_FILES = 8


class OutputProtector:
    def __init__(self, runtime: ProtectedJobRuntime, datatypes_registry: "Registry"):
        self.runtime = runtime
        self.datatypes_registry = datatypes_registry
        self.records: dict[str, dict[str, Any]] = {}
        self.errors: list[str] = []
        # Every file of every output is protected through this pool, it caps the calls to the key service.
        self._file_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_FILES, thread_name_prefix="protect_file")

    @classmethod
    def for_job(cls, metadata_params: dict[str, Any], datatypes_registry: "Registry") -> "OutputProtector | None":
        plan_path = metadata_params.get("protection_plan")
        if not plan_path:
            return None
        if not os.path.exists(plan_path):
            raise ProtectionError("The protection plan of this job is missing, its outputs can't be protected.")
        return cls(load_runtime(ProtectionPlan.read(plan_path)), datatypes_registry)

    def protect(
        self,
        dataset_instance: "DatasetInstance",
        path: str,
        extra_files_path: str | None = None,
        link_data: bool = False,
    ) -> None:
        """Encrypt the files of an output in place and switch it to the matching Crypt4GH datatype.

        On failure the plaintext is removed, so nothing unprotected can be persisted afterwards.
        """
        uuid = self._uuid(dataset_instance)
        try:
            if link_data:
                # Linked files stay where they are, they can't be encrypted in place.
                raise ProtectionError("outputs of protected jobs can't be linked data")
            ext = self._protected_ext(dataset_instance.extension, path)
            result = self._protect_file(path)
            extra_files = self._protect_extra_files(extra_files_path)
        except Exception as e:
            if not link_data:
                self._discard(path, extra_files_path)
            raise self._failed(dataset_instance, e) from e
        dataset_instance.extension = ext
        self.records[uuid] = {
            "outcome": OUTCOME_PROTECTED,
            "ext": ext,
            "header_sha256": result.header_sha256,
            "compute_header": result.compute_header,
            "extra_files": extra_files,
        }

    def protect_extra_files(self, dataset_instance: "DatasetInstance", extra_files_path: str | None) -> None:
        """Encrypt the extra files of an output protected earlier without them, see :meth:`protect`.

        Outputs assigned a discovered file (assign_primary_output) are protected before their
        extra files are located.
        """
        record = self.records[self._uuid(dataset_instance)]
        if record["outcome"] != OUTCOME_PROTECTED or record["extra_files"]:
            return
        try:
            record["extra_files"] = self._protect_extra_files(extra_files_path)
        except Exception as e:
            self._discard_extra_files(extra_files_path)
            raise self._failed(dataset_instance, e) from e

    def _failed(self, dataset_instance: "DatasetInstance", error: Exception) -> ProtectionError:
        """Record that an output could not be protected, its plaintext must be discarded already."""
        if isinstance(error, ProtectionError):
            message = str(error)
        else:
            message = f"Unexpected error ({type(error).__name__})"
        self.records[self._uuid(dataset_instance)] = {"outcome": OUTCOME_FAILED}
        self.errors.append(f"Output '{dataset_instance.name}' could not be protected: {message}")
        return ProtectionError(message)

    def _protect_extra_files(self, extra_files_path: str | None) -> dict[str, str | None]:
        """Encrypt every extra file in place, return their compute headers by relative path."""
        if not extra_files_path or not os.path.isdir(extra_files_path):
            return {}
        futures = {
            relpath: self._file_executor.submit(self.runtime.protect_file, os.path.join(extra_files_path, relpath))
            for relpath in iter_relpaths(extra_files_path)
        }
        # Let every file finish before failing, the files are discarded then.
        wait(futures.values())
        return {relpath: future.result().compute_header for relpath, future in futures.items()}

    def protect_all(self, outputs: list[tuple["DatasetInstance", str, str | None, bool]]) -> None:
        """Protect several outputs concurrently, see :meth:`protect`: ``(dataset_instance, path, extra_files_path, link_data)``."""
        failed = threading.Event()

        def protect(output: tuple["DatasetInstance", str, str | None, bool]) -> None:
            if failed.is_set():
                # The job fails anyway, don't keep calling the key service. Galaxy purges what isn't protected,
                # remove the plaintext like for failed outputs.
                _, path, extra_files_path, link_data = output
                if not link_data:
                    self._discard(path, extra_files_path)
                return
            try:
                self.protect(*output)
            except Exception:
                failed.set()
                raise

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_FILES) as executor:
            # Not executor.map(): it cancels the outputs left after an error, their plaintext would stay.
            futures = [executor.submit(protect, output) for output in outputs]
            wait(futures)
        for future in futures:
            # Raises the first error once every output is protected or discarded.
            future.result()

    def _protect_file(self, path: str) -> ProtectedFileResult:
        return self._file_executor.submit(self.runtime.protect_file, path).result()

    def record_outcome(self, dataset_instance: "DatasetInstance", outcome: str) -> None:
        self.records.setdefault(self._uuid(dataset_instance), {"outcome": outcome})

    def record_deferred(self, dataset_instance: "DatasetInstance") -> None:
        self.record_outcome(dataset_instance, OUTCOME_DEFERRED)

    @staticmethod
    def without_tool_metadata(attributes: dict[str, Any] | None) -> dict[str, Any]:
        """Tool provided attributes of an output, without the metadata: that may be derived from the decrypted data."""
        return {key: value for key, value in (attributes or {}).items() if key != "metadata"}

    def protected_ext(self, dataset_instance: "DatasetInstance") -> str | None:
        """Extension of an output protected earlier, ``None`` for other datasets."""
        record = self.records.get(self._uuid(dataset_instance))
        return record["ext"] if record and record["outcome"] == OUTCOME_PROTECTED else None

    def check_complete(self, dataset_instances: list["DatasetInstance"]) -> None:
        """Record an error for every output that went around the protection."""
        for dataset_instance in dataset_instances:
            dataset = dataset_instance.dataset
            if dataset is not None and dataset.purged:
                self.record_outcome(dataset_instance, OUTCOME_PURGED)
                continue
            if self._uuid(dataset_instance) not in self.records:
                self.records[self._uuid(dataset_instance)] = {"outcome": OUTCOME_FAILED}
                self.errors.append(f"Output '{dataset_instance.name}' was not protected.")

    def write_sidecar(self, job_directory: str) -> None:
        path = os.path.join(job_directory, SIDECAR_FILE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sidecar: dict[str, Any] = {
            "key_ref": None,
            "key_expiration": None,
            "datasets": self.records,
            "errors": self.errors,
        }
        try:
            sidecar["key_ref"] = self.runtime.key_ref
            sidecar["key_expiration"] = self.runtime.key_expiration
        except ProtectionError:
            # The inputs were never staged, there are no outputs to use again.
            pass
        # Compute headers are bearer capabilities.
        write_private_file(path, json.dumps(sidecar))

    def _protected_ext(self, ext: str | None, path: str) -> str:
        inner_ext = unwrap_crypt4gh_file_ext(ext or "") or ext or "data"
        if inner_ext in ("auto", "_sniff_"):
            # Sniffing needs the plaintext, so it has to happen now.
            inner_ext = sniff.guess_ext(path, self.datatypes_registry.sniff_order)
        if inner_ext == CRYPT4GH_FILE_EXT:
            return CRYPT4GH_FILE_EXT
        protected_ext = wrap_crypt4gh_file_ext(inner_ext)
        if self.datatypes_registry.get_datatype_by_extension(protected_ext) is None:
            return CRYPT4GH_FILE_EXT
        return protected_ext

    @staticmethod
    def _uuid(dataset_instance: "DatasetInstance") -> str:
        assert dataset_instance.dataset
        return str(dataset_instance.dataset.uuid)

    @classmethod
    def _discard(cls, path: str, extra_files_path: str | None) -> None:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            log.exception("Could not remove an output that failed to be protected")
        cls._discard_extra_files(extra_files_path)

    @staticmethod
    def _discard_extra_files(extra_files_path: str | None) -> None:
        try:
            if extra_files_path and os.path.isdir(extra_files_path):
                shutil.rmtree(extra_files_path)
        except OSError:
            log.exception("Could not remove an output that failed to be protected")

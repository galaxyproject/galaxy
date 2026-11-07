"""Restartable local execution through EngageQueue's Python API.

Galaxy owns preparation, datasets, metadata and interactive entry points.
EngageQueue owns accepted executions and resource termination. Closing this
runner releases its client handles while the shared scheduler keeps running.
"""

from __future__ import annotations

import fcntl
import hashlib
import importlib
import inspect
import json
import logging
import math
import os
import shlex
import shutil
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import (
    Callable,
    Iterator,
)
from contextlib import contextmanager
from pathlib import Path
from typing import (
    Any,
    cast,
    TYPE_CHECKING,
)

from sqlalchemy import select

from galaxy import model
from galaxy.exceptions import ConfigurationError
from galaxy.job_execution.compute_environment import SharedComputeEnvironment
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
)
from galaxy.jobs.runners.local import LocalJobRunner
from galaxy.jobs.upload_finish import (
    UploadFinishCancelled,
    UploadFinishContext,
    UploadFinishError,
    validate_upload,
)
from galaxy.util import asbool
from galaxy.util.commands import new_clean_env

if TYPE_CHECKING:
    from galaxy.app import GalaxyManagerApplication
    from galaxy.job_execution.setup import JobIO

log = logging.getLogger(__name__)
__all__ = ("EngageQueueJobRunner",)

RECORD_FILE = ".engagequeue-job.json"
STOP_FILE = ".engagequeue-stop.json"
GRACEFUL_STOP_FILE = ".engagequeue-graceful-stop.json"
ATTEMPT_PARAM = "__engagequeue_attempt"
STATE_PARAM = "__engagequeue_state_dir"
POOL_PARAM = "__engagequeue_pool"
ATTACH_PARAM = "__engagequeue_attach_only"
CANCEL_STATES = (
    model.Job.states.STOPPING,
    model.Job.states.STOPPED,
    model.Job.states.DELETING,
    model.Job.states.DELETED,
)
ACTIVE_STATES = (model.Job.states.QUEUED, model.Job.states.RUNNING, model.Job.states.FINISHING)


def _normalize_interactive_exit_code(
    marker_path: str, hard_stop_path: str, expected: dict[str, object], return_code: int, timeout: float = 5
) -> int:
    """Standalone, standard-library-only guard copied into the accepted job."""
    import json
    import re
    import time
    from pathlib import Path

    if return_code not in (137, 143):
        return return_code
    deadline = time.monotonic() + timeout
    while True:
        try:
            if Path(hard_stop_path).exists():
                return return_code
            marker = json.loads(Path(marker_path).read_text())
            if any(marker.get(key) != value for key, value in expected.items()):
                return return_code
            if marker.get("requested_while_terminal") is True:
                return return_code
            if marker.get("requested_while_terminal") is not False:
                raise KeyError("Stop identity is still being resolved")
            cid = marker.get("container_id")
            if cid is not None and (not isinstance(cid, str) or not re.fullmatch("[a-f0-9]{64}", cid)):
                return return_code
            receipt = json.loads(Path(marker["receipt_path"]).read_text())
            receipt_cid = receipt.get("container_id")
            if not isinstance(receipt_cid, str) or not re.fullmatch("[a-f0-9]{64}", receipt_cid):
                return return_code
            matches = {
                "schema": 1,
                "job_id": marker["execution_id"],
                "key": expected["key"],
                "name": expected["name"],
                "container_id": cid or receipt_cid,
                "label_key": expected["label_key"],
                "label_value": expected["label_value"],
                "job_cancel_requested": False,
            }
            if (
                all(receipt.get(key) == value for key, value in matches.items())
                and receipt.get("job_cancel_requested") is False
            ):
                if receipt.get("status") in ("signal_issued", "stopped"):
                    if return_code == 143 and receipt.get("issued_signal") == "TERM":
                        if receipt.get("exit_code") in (None, 143) and receipt.get("oom_killed") is not True:
                            if not Path(hard_stop_path).exists():
                                return 0
                    if return_code == 137 and receipt.get("issued_signal") == "KILL":
                        if receipt.get("exit_code") == 137 and receipt.get("oom_killed") is False:
                            if not Path(hard_stop_path).exists():
                                return 0
        except (OSError, ValueError, KeyError, TypeError):
            pass
        if time.monotonic() >= deadline:
            return return_code
        time.sleep(0.05)


class _StagedInputComputeEnvironment(SharedComputeEnvironment):
    """Snapshot selected inputs on job storage through normal evaluator hooks."""

    def __init__(self, job_io: JobIO, job: model.Job) -> None:
        super().__init__(job_io, job)
        self.materialized_objects = {}
        self.directory = Path(job_io.working_directory) / "inputs"
        self.staged_paths: dict[str, None] = {}

    def _path(self, source: str, filename: str) -> Path:
        token = hashlib.sha256(os.fsencode(os.path.abspath(source))).hexdigest()
        return self.directory / token / filename

    def _copy_file(self, source: str, target: Path) -> str:
        if str(target) in self.staged_paths:
            return str(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".input-", delete=False) as output:
                temporary = Path(output.name)
                with open(source, "rb") as input_file:
                    shutil.copyfileobj(input_file, output)
                output.flush()
                os.fsync(output.fileno())
            shutil.copystat(source, temporary)
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.staged_paths[str(target)] = None
        return str(target)

    def input_path_rewrite(self, dataset: Any) -> str:
        source = dataset.get_file_name()
        target = self._copy_file(source, self._path(source, "dataset.dat"))
        underlying = getattr(dataset, "dataset", None)
        if underlying is not None and Path(underlying.extra_files_path).exists():
            # Some composite tools derive the paired directory from the
            # primary filename rather than rendering .extra_files_path.
            self.input_extra_files_rewrite(dataset)
        metadata_files: list[tuple[str, str]] = getattr(dataset, "get_metadata_file_paths_and_extensions", lambda: [])()
        for _, path in metadata_files:
            self.input_metadata_rewrite(dataset, path)
        return target

    def input_extra_files_rewrite(self, dataset: Any) -> str:
        target = self._path(dataset.get_file_name(), "dataset_files")
        if str(target) in self.staged_paths:
            return str(target)
        source = Path(dataset.dataset.extra_files_path)
        if not source.exists():
            return str(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(dir=target.parent, prefix=".input-"))
        try:
            shutil.copytree(source, temporary, dirs_exist_ok=True, symlinks=True)
            # Preserve internal symlinks without following them into unrelated
            # data. Rebase absolute internal links into the copied tree.
            source_root = source.resolve()
            for root, directories, files in os.walk(temporary, followlinks=False):
                for name in [*directories, *files]:
                    copied = Path(root) / name
                    if copied.is_symlink():
                        original = source / copied.relative_to(temporary)
                        try:
                            relative = original.resolve().relative_to(source_root)
                        except (ValueError, RuntimeError) as exc:
                            raise ConfigurationError(
                                "An input extra-files symlink escapes its selected directory"
                            ) from exc
                        copied.unlink()
                        copied.symlink_to(os.path.relpath(temporary / relative, copied.parent))
            if target.exists():
                shutil.rmtree(target)
            os.replace(temporary, target)
            self.staged_paths[str(target)] = None
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return str(target)

    def input_metadata_rewrite(self, dataset: Any, metadata_value: Any) -> str | None:
        if not metadata_value:
            return None
        source = str(metadata_value)
        return self._copy_file(source, self._path(source, Path(source).name))

    def input_collection_paths_and_metadata_files(self, collection: Any) -> list[list[Any]]:
        datasets = {dataset.get_file_name(): dataset for dataset in collection.dataset_instances}
        return [
            [
                identifiers,
                extension,
                self.input_path_rewrite(datasets[path]),
                [
                    (metadata_extension, self.input_metadata_rewrite(datasets[path], metadata_path))
                    for metadata_extension, metadata_path in metadata_files
                ],
            ]
            for identifiers, extension, path, metadata_files in collection.element_identifiers_extensions_paths_and_metadata_files
        ]


def _write_json(path: Path, value: Any) -> None:
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, prefix=f".{path.name}.", delete=False) as output:
            temporary = Path(output.name)
            json.dump(value, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        with Path(path).open() as source:
            return cast(dict[str, Any], json.load(source))
    except FileNotFoundError:
        return None


@contextmanager
def _job_lock(root: Path, name: str = "prepare") -> Iterator[None]:
    with (Path(root) / f".engagequeue-{name}.lock").open("a") as stream:
        os.fchmod(stream.fileno(), 0o600)
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        yield


@contextmanager
def _retain_job_files(wrapper: Any) -> Iterator[None]:
    destination = wrapper.job_destination
    original = destination.params
    destination.params = {**original, "cleanup_job": "never"}
    try:
        yield
    finally:
        updated = {**destination.params}
        if "cleanup_job" in original:
            updated["cleanup_job"] = original["cleanup_job"]
        else:
            updated.pop("cleanup_job", None)
        destination.params = updated


class EngageQueueJobState(AsynchronousJobState):
    def __init__(self, wrapper: Any, external_id: str | None) -> None:
        super().__init__(
            job_wrapper=wrapper,
            job_destination=wrapper.job_destination,
            files_dir=wrapper.working_directory,
            job_id=external_id,
        )
        self.output_file = str(Path(wrapper.working_directory) / ".engagequeue-stdout")
        self.error_file = str(Path(wrapper.working_directory) / ".engagequeue-stderr")
        self.retry_at = 0.0

    def cleanup(self) -> None:
        # Streams and the prepared script remain available until database
        # completion (including an upload receipt) has committed successfully.
        pass


class EngageQueueJobRunner(AsynchronousJobRunner[EngageQueueJobState]):
    """Use one native EngageQueue execution per durable Galaxy attempt."""

    runner_name = "EngageQueueRunner"
    recovers_finishing_jobs = True
    recovers_without_external_id = True
    DEFAULT_SPECS = {
        **AsynchronousJobRunner.DEFAULT_SPECS,
        "state_dir": {
            "map": lambda value: None if value is None else str(value),
            "valid": lambda value: value is None or Path(value).is_absolute(),
            "default": None,
        },
        "runtime_python": {
            "map": lambda value: None if value is None else str(value),
            "valid": lambda value: value is None or Path(value).is_absolute(),
            "default": None,
        },
        "pool": {"map": str, "valid": lambda value: bool(value), "default": "default"},
        "max_concurrent_jobs": {"map": lambda value: value, "valid": lambda value: True, "default": 1},
        "backend": {"map": str, "valid": lambda value: value in ("native", "systemd"), "default": "native"},
        "attach_only": {"map": asbool, "default": False},
        "stage_inputs": {"map": asbool, "default": False},
        "cancel_grace_seconds": {
            "map": float,
            "valid": lambda value: not isinstance(value, bool) and math.isfinite(float(value)) and float(value) >= 0,
            "default": 10.0,
        },
        "retry_delay_seconds": {
            "map": float,
            "valid": lambda value: not isinstance(value, bool) and math.isfinite(float(value)) and float(value) > 0,
            "default": 2.0,
        },
    }

    def __init__(self, app: GalaxyManagerApplication, nworkers: int, **kwargs: Any) -> None:
        # Import only when the runner is selected; discovery does not make the
        # optional package a dependency of unrelated Galaxy runners.
        self._library()
        self._clients: dict[tuple[str, str, str, bool], Any] = {}
        self._client_pid = os.getpid()
        self._client_lock = threading.RLock()
        super().__init__(app, nworkers, **kwargs)
        self._library().PoolConfig(
            max_jobs=self.runner_params["max_concurrent_jobs"],
            backend=self.runner_params["backend"],
            cancel_grace=self.runner_params["cancel_grace_seconds"],
        )

    @staticmethod
    def _library() -> Any:
        try:
            return importlib.import_module("engagequeue")
        except ImportError as exc:
            raise ConfigurationError("The EngageQueue runner requires the engagequeue Python package") from exc

    def _executor(self, wrapper: Any) -> tuple[Any, str, str]:
        params = wrapper.job_destination.params
        directory = params.get(STATE_PARAM) or params.get("state_dir") or self.runner_params["state_dir"]
        if directory is None:
            directory = str(Path(self.app.config.data_dir) / "engagequeue")
        if not Path(directory).is_absolute():
            raise ConfigurationError("EngageQueue state_dir must be an absolute local filesystem path")
        managed_profile = Path(directory) / "managed.json"
        if managed_profile.exists() or managed_profile.is_symlink():
            raise ConfigurationError(
                "EngageQueueJobRunner supports local execution only; state_dir selects a managed Docker profile. "
                "Configure a separate local state directory."
            )
        pool = params.get(POOL_PARAM) or params.get("pool", self.runner_params["pool"])
        library = self._library()
        configuration = library.PoolConfig(
            max_jobs=params.get("max_concurrent_jobs", self.runner_params["max_concurrent_jobs"]),
            backend=params.get("backend", self.runner_params["backend"]),
            cancel_grace=float(params.get("cancel_grace_seconds", self.runner_params["cancel_grace_seconds"])),
        )
        attach_only = asbool(params.get(ATTACH_PARAM, params.get("attach_only", self.runner_params["attach_only"])))
        key = (str(Path(directory).resolve()), pool, json.dumps(configuration.to_dict(), sort_keys=True), attach_only)
        if self._client_pid != os.getpid():
            # Gunicorn may preload this instance. Inherited locks/connections
            # belong to the parent; new handles attach to the same runtime.
            self._clients = {}
            self._client_lock = threading.RLock()
            self._client_pid = os.getpid()
        with self._client_lock:
            if key not in self._clients:
                self._clients[key] = library.Executor(
                    state_dir=key[0],
                    pools={pool: configuration},
                    runtime_python=self.runner_params["runtime_python"],
                    attach_only=attach_only,
                )
            return self._clients[key], key[0], pool

    @staticmethod
    def _is_upload(wrapper: Any) -> bool:
        return wrapper.get_job().tool_id in ("upload1", "__DATA_FETCH__")

    @staticmethod
    def _is_standalone_metadata(wrapper: Any) -> bool:
        return getattr(wrapper.tool, "tool_type", None) == "set_metadata"

    def _change_if_active(
        self, wrapper: Any, state: str, update_output_states: bool = False, allow_stopped: bool = False
    ) -> bool:
        active = ACTIVE_STATES + ((model.Job.states.STOPPING, model.Job.states.STOPPED) if allow_stopped else ())
        session = getattr(wrapper, "sa_session", None)
        if session is None:
            if wrapper.get_state() not in active:
                return False
            wrapper.change_state(state, update_output_states=update_output_states)
            return True
        job = session.scalars(
            select(model.Job)
            .where(model.Job.id == wrapper.job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one()
        if job.state not in active:
            session.commit()
            return False
        wrapper.change_state(state, job=job, update_output_states=update_output_states)
        return True

    def _retain_failure(self, wrapper: Any, message: Any) -> None:
        # Unknown execution ownership does not authorize moving files that a
        # surviving process may still be writing.
        if getattr(wrapper, "sa_session", None) is None:
            wrapper.fail(str(message))
        else:
            wrapper.change_state(model.Job.states.ERROR, info=str(message))
        self._fail_busy_metadata_inputs(wrapper)

    def _fail_busy_metadata_inputs(self, wrapper: Any) -> None:
        if not self._is_standalone_metadata(wrapper):
            return
        session = getattr(wrapper, "sa_session", None)
        job = wrapper.get_job()
        for association in [*job.input_datasets, *job.input_library_datasets]:
            dataset = association.dataset
            if (
                dataset.state == model.Dataset.states.SETTING_METADATA
                and not getattr(dataset, "deleted", False)
                and not getattr(dataset, "purged", False)
                and not getattr(dataset.dataset, "deleted", False)
                and not getattr(dataset.dataset, "purged", False)
            ):
                dataset.state = model.Dataset.states.FAILED_METADATA
                if session is not None:
                    session.add(dataset)
        if session is not None:
            session.commit()

    def _record(self, wrapper: Any) -> dict[str, Any] | None:
        record = _read_json(Path(wrapper.working_directory) / RECORD_FILE)
        if record and (record.get("schema") != 1 or record.get("job_id") != str(wrapper.job_id)):
            raise ValueError("EngageQueue execution record does not belong to this Galaxy job")
        return record

    def _persist_attempt(self, wrapper: Any, record: dict[str, Any]) -> None:
        destination = wrapper.job_destination
        destination.params = {
            **destination.params,
            ATTEMPT_PARAM: record["key"],
            STATE_PARAM: record["state_dir"],
            POOL_PARAM: record["pool"],
            ATTACH_PARAM: record.get("attach_only", False),
        }
        if persist := getattr(wrapper, "set_job_destination", None):
            persist(destination, external_id=wrapper.get_job().job_runner_external_id)

    def _label_container(self, wrapper: Any, container: Any) -> Any:
        if container is not None and container.container_type == "docker":
            token = wrapper._engagequeue_attempt_token
            existing = container.prop("run_extra_arguments", "") or ""
            container.destination_info = {
                **container.destination_info,
                "docker_run_extra_arguments": f"{existing} --label engagequeue.attempt={shlex.quote(token)}",
            }
            wrapper._engagequeue_containers.append(container)
        return container

    def _find_container(self, job_wrapper: Any, *args: Any, **kwargs: Any) -> Any:
        wrapper = job_wrapper
        container = super()._find_container(wrapper, *args, **kwargs)
        if container is not None and container.container_type == "docker" and wrapper.tool.produces_entry_points:
            wrapper._engagequeue_interactive_container = container.container_name
            # Keep final exit/OOM evidence until the independent supervisor has
            # recorded a verified Stop receipt. It removes only this owned,
            # stopped tool container after the full execution is quiescent.
            container.destination_info = {**container.destination_info, "docker_auto_rm": False}
            container._engagequeue_remove_on_exit = True
        if (
            container is not None
            and container.container_type == "docker"
            and (wrapper.tool.produces_entry_points or self._stage_inputs(wrapper))
        ):
            self._mount_interactive_inputs(wrapper, container)
        return self._label_container(wrapper, container)

    def get_return_code_capture_command(self, job_wrapper: Any) -> str | None:
        wrapper = job_wrapper
        name = getattr(wrapper, "_engagequeue_interactive_container", None)
        if not wrapper.tool.produces_entry_points or name is None:
            return None
        expected = {
            "schema": 1,
            "job_id": str(wrapper.job_id),
            "key": f"galaxy:{wrapper._engagequeue_attempt_token}",
            "name": name,
            "label_key": "engagequeue.attempt",
            "label_value": wrapper._engagequeue_attempt_token,
        }
        root = Path(wrapper.working_directory)
        script = root / ".engagequeue-normalize-stop.py"
        script.write_text(
            inspect.getsource(_normalize_interactive_exit_code)
            + "\nimport json, sys\nraise SystemExit(_normalize_interactive_exit_code(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), int(sys.argv[4])))\n"
        )
        script.chmod(0o600)
        command = " ".join(
            shlex.quote(str(value))
            for value in (
                Path(sys.prefix) / "bin/python",
                script,
                root / GRACEFUL_STOP_FILE,
                root / STOP_FILE,
                json.dumps(expected),
            )
        )
        return f'if [ "$return_code" = 143 ] || [ "$return_code" = 137 ]; then if {command} "$return_code"; then return_code=0; fi; fi'

    @staticmethod
    def _mount_interactive_inputs(wrapper: Any, container: Any) -> None:
        # Shared execution uses the original dataset paths rather than Pulsar's
        # per-job staging directory. Expose only the selected inputs, including
        # their metadata and extra files; mounting the object-store parent would
        # expose other users' datasets to arbitrary interactive code.
        environment = wrapper._engagequeue_compute_environment
        if isinstance(environment, _StagedInputComputeEnvironment):
            paths = environment.staged_paths
        else:
            paths = EngageQueueJobRunner._selected_input_paths(wrapper, environment.materialized_objects)
        for path in paths:
            if not Path(path).is_absolute() or "," in path or ":" in path:
                raise ConfigurationError(f"Cannot bind interactive input path {path!r}")
        volumes = container.destination_info.get("docker_volumes", "$defaults")
        container.destination_info = {
            **container.destination_info,
            "docker_volumes": ",".join([volumes, *(f"{path}:{path}:ro" for path in paths)]),
        }

    @staticmethod
    def _selected_input_paths(wrapper: Any, materialized: Any) -> dict[str, None]:
        job_io = wrapper.job_io
        datasets = list(job_io.get_input_datasets(materialized))
        for association in wrapper.get_job().input_dataset_collections:
            if association.name not in materialized:
                datasets.extend(association.dataset_collection.dataset_instances)
        for association in wrapper.get_job().input_dataset_collection_elements:
            if association.name not in materialized:
                datasets.extend(association.dataset_collection_element.dataset_instances)
        for value in materialized.values():
            for item in value if isinstance(value, list) else [value]:
                datasets.extend([item] if isinstance(item, model.DatasetInstance) else item.dataset_instances)
        return dict.fromkeys(path for dataset in datasets for path in job_io.get_input_dataset_fnames(dataset))

    def _stage_inputs(self, wrapper: Any) -> bool:
        return asbool(wrapper.job_destination.params.get("stage_inputs", self.runner_params["stage_inputs"]))

    def _get_metadata_container(self, job_wrapper: Any, *args: Any, **kwargs: Any) -> Any:
        return self._label_container(job_wrapper, super()._get_metadata_container(job_wrapper, *args, **kwargs))

    def _prepare_standalone_metadata(self, wrapper: Any) -> None:
        directory = Path(wrapper.working_directory) / "metadata"
        path = directory / "params.json"
        params = _read_json(path)
        if not isinstance(params, dict) or not params.get("outputs"):
            raise ValueError("Standalone metadata parameters must describe the existing input dataset")
        self.app.datatypes_registry.to_xml_file(path=str(directory / "registry.xml"))
        params["datatypes_config"] = "metadata/registry.xml"
        _write_json(path, params)
        library = shlex.quote(str(wrapper.galaxy_lib_dir))
        python = shlex.quote(str(Path(sys.prefix) / "bin/python"))
        wrapper.runner_command_line = (
            f"export GALAXY_PYTHON={python}; export PYTHONPATH={library}${{PYTHONPATH:+:$PYTHONPATH}}; "
            + wrapper.runner_command_line
        )

    def _specification(self, wrapper: Any, script: str, state: EngageQueueJobState, pool: str) -> Any:
        library = self._library()
        limits = self.app.job_config.limits
        walltimes = []
        if limits.walltime_delta is not None:
            walltimes.append(limits.walltime_delta.total_seconds())
        if wrapper.tool.timelimit and wrapper.tool.timelimit > 0:
            walltimes.append(wrapper.tool.timelimit)
        containers = []
        for container in wrapper._engagequeue_containers:
            connection = container.connection_configuration
            executable = connection.get("docker_cmd", "docker")
            if connection.get("sudo"):
                executable = f"{connection.get('sudo_cmd', 'sudo')} {executable}"
            retained = getattr(container, "_engagequeue_remove_on_exit", False)
            try:
                specification = library.ContainerSpec(
                    name=container.container_name,
                    label_key="engagequeue.attempt",
                    label_value=wrapper._engagequeue_attempt_token,
                    executable=executable,
                    host=connection.get("host"),
                    **({"remove_on_exit": True} if retained else {}),
                )
            except TypeError as exc:
                if retained:
                    raise ConfigurationError(
                        "Interactive tools require EngageQueue ContainerSpec.remove_on_exit support"
                    ) from exc
                raise
            containers.append(specification)
        return library.JobSpec(
            argv=[wrapper.shell or "/bin/bash", script],
            cwd=wrapper.working_directory,
            env=new_clean_env(),
            stdout=state.output_file,
            stderr=state.error_file,
            pool=pool,
            timeout=min(walltimes) if walltimes else None,
            output_limit=limits.output_size if limits.output_size and limits.output_size > 0 else None,
            output_paths=[str(path) for path in wrapper.job_io.get_output_fnames()],
            cpus=wrapper.job_destination.params.get("cpus"),
            memory_mb=wrapper.job_destination.params.get("memory_mb"),
            require_hard_limits=asbool(wrapper.job_destination.params.get("require_hard_limits", False)),
            containers=tuple(containers),
        )

    def queue_job(self, wrapper: Any) -> None:
        root = Path(wrapper.working_directory)
        root.mkdir(parents=True, exist_ok=True)
        try:
            with _job_lock(root):
                executor, directory, pool = self._executor(wrapper)
                record = self._record(wrapper)
                if record is None:
                    if (root / STOP_FILE).exists() or wrapper.get_state() in CANCEL_STATES:
                        self._change_if_active(wrapper, model.Job.states.STOPPED)
                        self._finish_cancelled_inputs(wrapper)
                        return
                    if wrapper.job_destination.params.get(ATTEMPT_PARAM):
                        raise ValueError(
                            "The frozen EngageQueue submission record is missing; files have been retained"
                        )
                    wrapper._engagequeue_attempt_token = uuid.uuid4().hex
                    wrapper._engagequeue_containers = []
                    wrapper._engagequeue_interactive_container = None
                    upload = self._is_upload(wrapper)
                    standalone = self._is_standalone_metadata(wrapper)
                    if upload:
                        validate_upload(wrapper)
                        if not asbool(wrapper.job_destination.params.get("embed_metadata_in_job", True)):
                            raise UploadFinishError(
                                "Recoverable uploads require metadata embedded in the accepted execution"
                            )
                    compute_environment = None
                    if self._stage_inputs(wrapper):
                        compute_environment = _StagedInputComputeEnvironment(wrapper.job_io, wrapper.get_job())
                    elif wrapper.tool.produces_entry_points:
                        compute_environment = wrapper.default_compute_environment()
                    if compute_environment is not None:
                        wrapper._engagequeue_compute_environment = compute_environment
                    with _retain_job_files(wrapper):
                        prepared = self.prepare_job(
                            wrapper, include_metadata=not standalone, compute_environment=compute_environment
                        )
                    if not prepared:
                        return
                    if standalone:
                        self._prepare_standalone_metadata(wrapper)
                    state = EngageQueueJobState(wrapper, None)
                    script, _ = LocalJobRunner._command_line(cast(Any, self), wrapper)
                    specification = self._specification(wrapper, script, state, pool)
                    record = {
                        "schema": 1,
                        "job_id": str(wrapper.job_id),
                        "key": f"galaxy:{wrapper._engagequeue_attempt_token}",
                        "state_dir": directory,
                        "pool": pool,
                        "attach_only": executor.attach_only,
                        "spec": specification.to_dict(),
                        "interactive_container": wrapper._engagequeue_interactive_container,
                    }
                    _write_json(root / RECORD_FILE, record)
                self._persist_attempt(wrapper, record)
                handle = executor.lookup(record["key"])
                if handle is None:
                    handle = executor.submit(self._library().JobSpec.from_dict(record["spec"]), key=record["key"])
                wrapper.set_external_id(handle.id)
                state = EngageQueueJobState(wrapper, handle.id)
                if (
                    (root / STOP_FILE).exists()
                    or (root / GRACEFUL_STOP_FILE).exists()
                    or wrapper.get_state() in CANCEL_STATES
                ):
                    self.stop_job(wrapper)
                self.monitor_job(state)
        except (ConfigurationError, UploadFinishError, ValueError) as exc:
            self._retain_failure(wrapper, exc)
        except Exception as exc:
            library = self._library()
            if isinstance(exc, (library.SubmissionConflict, library.UnsupportedBackend)):
                # A conflicting key may already identify another accepted
                # execution. Retain its receipt and files; never cancel it or
                # retry an unchanged specification that cannot be accepted.
                self._rollback()
                self._retain_failure(wrapper, exc)
                return
            # Submission may already be durable. Retain the frozen key/spec
            # and retry through lookup rather than repeating preparation.
            log.exception("(%s) EngageQueue submission deferred", wrapper.job_id)
            self._rollback()
            self._retry(self.queue_job, wrapper)

    def _retry(self, function: Callable[[Any], Any], value: Any) -> None:
        def enqueue() -> None:
            if not self._should_stop:
                self.work_queue.put((function, value))

        timer = threading.Timer(self.runner_params["retry_delay_seconds"], enqueue)
        timer.daemon = True
        timer.start()

    def _rollback(self) -> None:
        try:
            self.sa_session.rollback()
        except Exception:
            log.exception("Could not reset the EngageQueue completion session")

    def check_watched_item(self, state: EngageQueueJobState) -> EngageQueueJobState | None:
        if time.monotonic() < state.retry_at:
            return state
        wrapper = state.job_wrapper
        try:
            executor, _, _ = self._executor(wrapper)
            current = wrapper.get_state()
            if current in CANCEL_STATES or any(
                (Path(wrapper.working_directory) / name).exists() for name in (STOP_FILE, GRACEFUL_STOP_FILE)
            ):
                self.stop_job(wrapper)
            status = executor.status(state.job_id)
            if status.needs_reconciliation:
                self._retain_failure(wrapper, status.reason or "Execution ownership is uncertain; inspect EngageQueue")
                return None
            if status.state.value == "RUNNING" and not state.running:
                state.running = self._change_if_active(wrapper, model.Job.states.RUNNING, update_output_states=True)
            if state.running and current not in CANCEL_STATES:
                wrapper.check_for_entry_points()
            if status.terminal:
                if not status.writers_stopped:
                    raise ValueError("Terminal execution has no confirmed writer termination")
                self.mark_as_finished(state)
                return None
            return state
        except ConfigurationError as exc:
            self._rollback()
            self._retain_failure(wrapper, exc)
            return None
        except Exception:
            log.exception("(%s) EngageQueue status unavailable; keeping files", wrapper.job_id)
            self._rollback()
            state.retry_at = time.monotonic() + self.runner_params["retry_delay_seconds"]
            return state

    def _finish_cancelled_inputs(self, wrapper: Any) -> None:
        if self._is_standalone_metadata(wrapper):
            wrapper.tool.job_failed(wrapper)

    @staticmethod
    def _fail_execution(wrapper: Any, message: Any, **kwargs: Any) -> None:
        destination = wrapper.job_destination
        original = destination.params
        destination.params = {**original, "cleanup_job": "never"}
        try:
            wrapper.fail(message, **kwargs)
        finally:
            destination.params = original

    def _import_complete(self, wrapper: Any) -> bool:
        job = wrapper.get_job()
        if self._is_standalone_metadata(wrapper):
            associations = [*job.input_datasets, *job.input_library_datasets]
            return bool(associations) and all(item.dataset.state == model.Dataset.states.OK for item in associations)
        failed = (model.Dataset.states.ERROR, model.Dataset.states.FAILED_METADATA)
        return not any(item.dataset.state in failed for item in [*job.output_datasets, *job.output_library_datasets])

    def finish_job(self, state: EngageQueueJobState) -> None:
        wrapper: Any = state.job_wrapper
        root = Path(wrapper.working_directory)
        if not root.exists():
            return
        try:
            with _job_lock(root, "finish"):
                executor, _, _ = self._executor(wrapper)
                status = executor.status(state.job_id)
                if not status.terminal or not status.writers_stopped:
                    self.monitor_job(state)
                    return
                current = wrapper.get_state()
                if current in CANCEL_STATES or (root / STOP_FILE).exists() or (root / GRACEFUL_STOP_FILE).exists():
                    self.stop_job(wrapper)
                graceful = self._graceful_stop(wrapper)
                if (
                    (current in CANCEL_STATES and not graceful)
                    or (root / STOP_FILE).exists()
                    or status.state.value == "CANCELLED"
                ):
                    self._change_if_active(wrapper, model.Job.states.STOPPED)
                    self._finish_cancelled_inputs(wrapper)
                    return
                if current == model.Job.states.OK:
                    if self._import_complete(wrapper) and wrapper.cleanup_job in ("always", "onsuccess"):
                        wrapper.cleanup(delete_files=True)
                    return
                if current == model.Job.states.ERROR:
                    return
                if status.state.value == "FAILED":
                    streams = {}
                    for stream, path in (("job_stdout", state.output_file), ("job_stderr", state.error_file)):
                        try:
                            with open(path, "rb") as source:
                                streams[stream] = self._job_io_for_db(source)
                        except FileNotFoundError:
                            streams[stream] = ""
                    self._fail_execution(
                        wrapper, status.reason or "The execution failed", exit_code=status.returncode, **streams
                    )
                    self._fail_busy_metadata_inputs(wrapper)
                    return
                if not Path(state.exit_code_file).exists():
                    self._fail_execution(
                        wrapper,
                        status.reason or "Job exited before producing its native exit record",
                        exit_code=status.returncode,
                    )
                    return
                if not self._change_if_active(wrapper, model.Job.states.FINISHING, allow_stopped=bool(graceful)):
                    return
                if self._is_upload(wrapper):
                    record = self._record(wrapper)
                    if record is None:
                        raise ValueError("The frozen upload execution record is missing; files have been retained")
                    wrapper.finish_context = UploadFinishContext(wrapper, record["key"])
                destination = wrapper.job_destination
                original = destination.params
                cleanup = wrapper.cleanup_job
                destination.params = {**original, "cleanup_job": "never"}
                try:
                    self._finish_job(state)
                    imported = wrapper.get_state() == model.Job.states.OK and self._import_complete(wrapper)
                    if (
                        wrapper.get_state() == model.Job.states.OK
                        and self._is_standalone_metadata(wrapper)
                        and not imported
                    ):
                        wrapper.fail("Standalone metadata import failed; job files have been retained")
                finally:
                    destination.params = original
                if imported and cleanup in ("always", "onsuccess"):
                    wrapper.cleanup(delete_files=True)
        except UploadFinishCancelled:
            self._rollback()
        except (ConfigurationError, UploadFinishError) as exc:
            self._rollback()
            self._retain_failure(wrapper, exc)
        except Exception:
            log.exception("(%s) EngageQueue completion deferred; retaining execution receipts", wrapper.job_id)
            self._rollback()
            state.retry_at = time.monotonic() + self.runner_params["retry_delay_seconds"]
            self.monitor_job(state)

    def _graceful_stop(self, wrapper: Any, record: dict[str, Any] | None = None) -> dict[str, Any] | None:
        root = Path(wrapper.working_directory)
        if wrapper.get_state() in (model.Job.states.DELETING, model.Job.states.DELETED) or (root / STOP_FILE).exists():
            return None
        marker = _read_json(root / GRACEFUL_STOP_FILE)
        record = record or self._record(wrapper)
        if (
            marker
            and record
            and marker.get("schema") == 1
            and marker.get("job_id") == str(wrapper.job_id)
            and marker.get("key") == record["key"]
            and marker.get("name") == record.get("interactive_container")
            and wrapper.tool.produces_entry_points
        ):
            return marker
        return None

    @staticmethod
    def _publish_graceful_stop(
        root: Path, expected: dict[str, Any], updates: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        # Only file operations occur under this lock: the stop queue may own
        # the Galaxy SQL row, so no model access or executor calls belong here.
        with _job_lock(root, "stop-intent"):
            marker = _read_json(root / GRACEFUL_STOP_FILE)
            if marker and any(marker.get(key) != value for key, value in expected.items()):
                raise ConfigurationError("The interactive stop intent belongs to a different attempt")
            marker = marker or {
                **expected,
                "execution_id": None,
                "receipt_path": None,
                "requested_while_terminal": None,
                "container_id": None,
            }
            for key, value in (updates or {}).items():
                previous = marker.get(key)
                if key == "requested_while_terminal" and previous is not None:
                    continue
                if key in ("execution_id", "receipt_path", "container_id") and previous is not None:
                    if value is not None and previous != value:
                        raise ConfigurationError("The interactive stop identity changed")
                    continue
                marker[key] = value
            _write_json(root / GRACEFUL_STOP_FILE, marker)
            return marker

    def stop_job(self, wrapper: Any) -> None:
        root = Path(wrapper.working_directory)
        root.mkdir(parents=True, exist_ok=True)
        record = self._record(wrapper)
        previous_intent = self._graceful_stop(wrapper, record) if record else None
        normal_stop = (
            wrapper.tool.produces_entry_points
            and (wrapper.get_state() in (model.Job.states.STOPPING, model.Job.states.STOPPED) or previous_intent)
            and record
            and record.get("interactive_container")
            and not (root / STOP_FILE).exists()
        )
        if normal_stop and record is not None:
            name = record["interactive_container"]
            token = record["key"].removeprefix("galaxy:")
            expected = {
                "schema": 1,
                "job_id": str(wrapper.job_id),
                "key": record["key"],
                "name": name,
                "label_key": "engagequeue.attempt",
                "label_value": token,
            }
            self._publish_graceful_stop(root, expected)
            executor, _, _ = self._executor(wrapper)
            external_id = wrapper.get_job().job_runner_external_id
            if not external_id:
                handle = executor.lookup(record["key"])
                external_id = handle.id if handle else None
            if external_id:
                status = executor.status(external_id)
                snapshot = executor.inspect(external_id)
                containers = snapshot["spec"].get("containers", [])
                identities = snapshot.get("owned_container_ids", [])
                cid = None
                for index, container in enumerate(containers):
                    if container["name"] == name and index < len(identities):
                        cid = identities[index]
                self._publish_graceful_stop(
                    root,
                    expected,
                    {
                        "execution_id": external_id,
                        "receipt_path": executor.container_stop_receipt_path(external_id, name),
                        "requested_while_terminal": status.terminal,
                        "container_id": cid,
                    },
                )
                if (root / STOP_FILE).exists() or wrapper.get_state() in (
                    model.Job.states.DELETING,
                    model.Job.states.DELETED,
                ):
                    _write_json(root / STOP_FILE, {"job_id": str(wrapper.job_id), "requested_at": time.time()})
                    executor.cancel(external_id)
                elif not status.terminal:
                    executor.stop_container(external_id, name)
            # Submission may still be in flight. Its post-acceptance path will
            # redispatch this durable normal intent once the ID is known.
            return
        # The stop queue owns the SQL row lock. This marker must not take the
        # preparation/finish lock and invert that ordering.
        _write_json(root / STOP_FILE, {"job_id": str(wrapper.job_id), "requested_at": time.time()})
        executor, _, _ = self._executor(wrapper)
        external_id = wrapper.get_job().job_runner_external_id
        if not external_id and record:
            handle = executor.lookup(record["key"])
            external_id = handle.id if handle else None
        if external_id:
            executor.cancel(external_id)

    def recover(self, job: model.Job, wrapper: Any) -> None:
        if not job.job_runner_external_id:
            if job.state in CANCEL_STATES:
                self.stop_job(wrapper)
                record = self._record(wrapper)
                if record:
                    executor, _, _ = self._executor(wrapper)
                    handle = executor.lookup(record["key"])
                    if handle:
                        wrapper.set_external_id(handle.id)
                        self.monitor_job(EngageQueueJobState(wrapper, handle.id))
                return
            # This is an already assigned attempt. Its frozen key must resolve
            # acceptance before preparation; fresh admission only accepts NEW
            # jobs and would reject QUEUED/RUNNING recovery after a crash.
            if job.state in (model.Job.states.NEW, model.Job.states.RESUBMITTED):
                self.put(wrapper)
            else:
                self.work_queue.put((self.queue_job, wrapper))
            return
        try:
            self._record(wrapper)
            state = EngageQueueJobState(wrapper, job.job_runner_external_id)
            state.running = job.state != model.Job.states.QUEUED
            self.monitor_job(state)
        except (UploadFinishError, ValueError) as exc:
            self._retain_failure(wrapper, exc)

    def shutdown(self) -> None:
        super().shutdown()
        for client in self._clients.values():
            client.close()
        self._clients.clear()

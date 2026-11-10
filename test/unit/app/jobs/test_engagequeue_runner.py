"""Galaxy preparation/completion around real EngageQueue executions."""

import json
import os
import shlex
import shutil
import subprocess
import time
from contextlib import ExitStack
from decimal import Decimal
from pathlib import Path
from types import (
    MethodType,
    SimpleNamespace,
)
from typing import Any
from unittest.mock import (
    MagicMock,
    Mock,
    patch,
    PropertyMock,
)

import pytest

engagequeue = pytest.importorskip("engagequeue")

from galaxy import (
    job_metrics,
    model,
    tools as tools_module,
)
from galaxy.app_unittest_utils.job_runner_support import MockJobWrapper
from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.exceptions import ConfigurationError
from galaxy.job_execution.datasets import DatasetPath
from galaxy.job_execution.setup import JobIO
from galaxy.jobs import JobConfigurationLimits
from galaxy.jobs.runners.engagequeue import (
    _read_json,
    ATTEMPT_PARAM,
    EngageQueueJobRunner,
    EngageQueueJobState,
    GRACEFUL_STOP_FILE,
    RECORD_FILE,
    STATE_PARAM,
    STOP_FILE,
)
from galaxy.metadata import PortableDirectoryMetadataGenerator
from galaxy.model.unittest_utils import (
    GalaxyDataTestApp,
    GalaxyDataTestConfig,
)
from galaxy.tool_util.deps.container_classes import (
    DockerContainer,
    preprocess_volumes,
)
from galaxy.tool_util.deps.dependencies import (
    AppInfo,
    JobInfo,
    ToolInfo,
)
from galaxy.tools import SetMetadataTool
from galaxy.util.unittest import TestCase


def wait_for(read, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := read():
            return value
        time.sleep(0.03)
    pytest.fail("Timed out waiting for the execution checkpoint")


def required_json(path: Path) -> dict[str, Any]:
    value = _read_json(path)
    assert value is not None
    return value


def test_interactive_mounts_only_selected_inputs_and_keeps_output_mounts_writable(tmp_path):
    storage = tmp_path / "storage"
    selected, sidecar, extras, unrelated = [
        storage / name for name in ("selected.dat", "index.bai", "selected_files", "other.dat")
    ]
    collection_file, element_file, materialized_file = [
        storage / name for name in ("collection.dat", "element.dat", "materialized.dat")
    ]
    metadata = model.MetadataFile()

    def dataset(path, *, metadata=None, extra_path=None):
        return SimpleNamespace(
            get_file_name=lambda: str(path),
            metadata=metadata or {},
            dataset=SimpleNamespace(
                extra_files_path_exists=lambda: extra_path is not None, extra_files_path=str(extra_path)
            ),
        )

    primary = dataset(selected, metadata={"index": metadata}, extra_path=extras)
    deferred = dataset(unrelated)
    collection = dataset(collection_file)
    element = dataset(element_file)
    materialized = dataset(materialized_file)
    job = SimpleNamespace(
        input_datasets=[
            SimpleNamespace(name="primary", dataset=primary),
            SimpleNamespace(name="deferred", dataset=deferred),
        ],
        input_library_datasets=[],
        input_dataset_collections=[
            SimpleNamespace(name="collection", dataset_collection=SimpleNamespace(dataset_instances=[collection]))
        ],
        input_dataset_collection_elements=[
            SimpleNamespace(name="element", dataset_collection_element=SimpleNamespace(dataset_instances=[element]))
        ],
    )
    job_io = SimpleNamespace(job=job)
    job_io.get_input_datasets = MethodType(JobIO.get_input_datasets, job_io)
    job_io.get_input_dataset_fnames = MethodType(JobIO.get_input_dataset_fnames, job_io)
    wrapper = SimpleNamespace(
        job_io=job_io,
        get_job=lambda: job,
        _engagequeue_compute_environment=SimpleNamespace(
            materialized_objects={"deferred": SimpleNamespace(dataset_instances=[materialized])}
        ),
    )
    job_directory = tmp_path / "job"
    working = job_directory / "working"
    outputs = job_directory / "outputs"
    tmp = job_directory / "tmp"
    config = tmp_path / "config"
    destination = {
        "docker_volumes": "$job_directory:ro,$working_directory:rw,$job_directory/outputs:rw,$tmp_directory:rw"
    }
    container = DockerContainer(
        "test-image",
        AppInfo(galaxy_root_dir=str(config), outputs_to_working_directory=True),
        ToolInfo(profile=24.2),
        destination,
        JobInfo(str(working), None, str(job_directory), str(tmp), None, "galaxy", {str(storage)}),
        None,
    )
    with patch.object(metadata, "get_file_name", return_value=str(sidecar)):
        EngageQueueJobRunner._mount_interactive_inputs(wrapper, container)
    mounts = preprocess_volumes(container._expand_volume_str(container.destination_info["docker_volumes"]), "docker")
    for path in (selected, sidecar, extras, collection_file, element_file, materialized_file):
        assert f"{path}:ro" in mounts
    assert f"{working}:rw" in mounts
    assert f"{outputs}:rw" in mounts
    assert f"{tmp}:rw" in mounts
    assert all(str(path) not in mount.split(":")[:2] for path in (storage, unrelated, config) for mount in mounts)
    assert (
        destination["docker_volumes"]
        == "$job_directory:ro,$working_directory:rw,$job_directory/outputs:rw,$tmp_directory:rw"
    )


class TestEngageQueueRunner(TestCase, UsesTools):
    def setUp(self):
        self.setup_app()
        self._init_tool()
        self.app.job_metrics = job_metrics.JobMetrics()
        self.app.config.monitor_thread_join_timeout = 2
        self.app.config.job_runner_monitor_sleep = 0.03
        self.app.config.retry_job_output_collection = 0
        self.app.job_config.limits = JobConfigurationLimits()
        self.database_check = patch("galaxy.jobs.runners.check_database_connection", return_value=None)
        self.database_check.start()
        self.runners = []
        self.wrappers = []
        self.wrapper_patches = ExitStack()
        self.state_dir = str(Path(self.test_directory) / "runtime")
        self.runner = self.new_runner()

    def new_runner(self, **kwargs):
        runner = EngageQueueJobRunner(
            self.app, 1, state_dir=self.state_dir, max_concurrent_jobs=0, retry_delay_seconds=0.05, **kwargs
        )
        runner.sa_session = MagicMock()
        runner.start()
        self.runners.append(runner)
        return runner

    def tearDown(self):
        executor = engagequeue.Executor(state_dir=self.state_dir)
        try:
            for job in executor.list():
                if not job.terminal and not job.needs_reconciliation:
                    executor.cancel(job.id, wait=True, timeout=15)
            executor.shutdown(wait=True, timeout=15)
        finally:
            executor.close()
        for runner in self.runners:
            if not runner._should_stop:
                runner.shutdown()
        self.database_check.stop()
        self.wrapper_patches.close()
        self.tear_down_app()

    def wrapper(self, identifier=1, *, upload=False):
        wrapper = MockJobWrapper(
            self.app, self.test_directory, self.tool, job_id=identifier, use_unique_working_directory=True
        )
        self.wrapper_patches.enter_context(patch.object(wrapper, "_job_io", None, create=True))
        wrapper.job.tool_id = "__DATA_FETCH__" if upload else self.tool.id
        wrapper.job.state = wrapper.state
        wrapper.job.destination_params = wrapper.job_destination.params
        original_change, original_finish, original_fail = wrapper.change_state, wrapper.finish, wrapper.fail

        def change(state, **kwargs):
            wrapper.job.state = state
            return original_change(state, **kwargs)

        def finish(*args, **kwargs):
            result = original_finish(*args, **kwargs)
            change(model.Job.states.OK)
            return result

        def fail(*args, **kwargs):
            result = original_fail(*args, **kwargs)
            change(model.Job.states.ERROR)
            return result

        for name, value in (("change_state", change), ("finish", finish), ("fail", fail), ("cleanup", Mock())):
            self.wrapper_patches.enter_context(patch.object(wrapper, name, value))
        self.wrappers.append(wrapper)
        return wrapper

    def test_native_tool_and_metadata_run_in_accepted_execution(self):
        wrapper = self.wrapper()
        wrapper.job_destination.params.update(cpus=4, memory_mb=16384)
        wrapper.command_line = "printf 'expected output\\n'"
        self.runner.mark_as_queued(wrapper)
        wait_for(lambda: wrapper.get_state() == model.Job.states.OK)
        assert wrapper.exit_code == 0
        assert wrapper.stdout == "expected output\n"
        assert Path(wrapper.mock_metadata_path).exists()
        record = required_json(Path(wrapper.working_directory) / RECORD_FILE)
        assert record["spec"]["cpus"] == 4
        assert record["spec"]["memory_mb"] == 16384
        assert wrapper.job_destination.params[ATTEMPT_PARAM] == record["key"]
        executor, _, _ = self.runner._executor(wrapper)
        assert executor.lookup(record["key"]).id == wrapper.job.job_runner_external_id
        assert executor.status(wrapper.job.job_runner_external_id).writers_stopped

    def test_interactive_retention_applies_only_to_tool_container(self):
        for interactive in (False, True):
            wrapper = self.wrapper(identifier=10 + int(interactive))
            wrapper.tool.produces_entry_points = interactive
            wrapper._engagequeue_attempt_token = "retention-test"
            wrapper._engagequeue_containers = []

            def container(name):
                return SimpleNamespace(
                    container_type="docker",
                    container_name=name,
                    destination_info={"docker_auto_rm": True},
                    connection_configuration={"docker_cmd": "docker"},
                    prop=lambda name, default: default,
                )

            tool, metadata = container("tool"), container("metadata")
            with (
                patch("galaxy.jobs.runners.BaseJobRunner._find_container", return_value=tool),
                patch("galaxy.jobs.runners.BaseJobRunner._get_metadata_container", return_value=metadata),
                patch.object(self.runner, "_mount_interactive_inputs"),
            ):
                self.runner._find_container(wrapper)
                self.runner._get_metadata_container(wrapper)
            specification = self.runner._specification(
                wrapper, "script.sh", EngageQueueJobState(wrapper, None), "default"
            )
            assert tool.destination_info["docker_auto_rm"] is not interactive
            assert specification.containers[0].remove_on_exit is interactive
            assert metadata.destination_info["docker_auto_rm"] is True
            assert specification.containers[1].remove_on_exit is False

    def test_unsupported_interactive_cleanup_is_a_configuration_error(self):
        wrapper = self.wrapper()
        wrapper._engagequeue_attempt_token = "retention-test"
        wrapper._engagequeue_containers = [
            SimpleNamespace(
                container_name="tool",
                connection_configuration={},
                _engagequeue_remove_on_exit=True,
            )
        ]
        library = SimpleNamespace(ContainerSpec=Mock(side_effect=TypeError("unexpected remove_on_exit")))
        with patch.object(self.runner, "_library", return_value=library):
            with pytest.raises(ConfigurationError, match="ContainerSpec.remove_on_exit"):
                self.runner._specification(wrapper, "script.sh", EngageQueueJobState(wrapper, None), "default")

    def test_handler_shutdown_does_not_stop_execution_or_repeat_command(self):
        wrapper = self.wrapper()
        release = Path(self.test_directory) / "release"
        counter = Path(self.test_directory) / "executions"
        wrapper.command_line = (
            f"echo once >> {shlex.quote(str(counter))}; "
            f"while [ ! -f {shlex.quote(str(release))} ]; do sleep 0.05; done; echo recovered"
        )
        self.runner.mark_as_queued(wrapper)
        wait_for(counter.exists)
        attempt = wrapper.job.job_runner_external_id
        self.runner.shutdown()
        release.touch()
        detached = engagequeue.Executor(state_dir=self.state_dir)
        assert detached.wait(attempt, timeout=30).returncode == 0
        assert Path(wrapper.mock_metadata_path).exists()
        assert counter.read_text() == "once\n"
        recovered = self.new_runner()
        recovered.recover(wrapper.job, wrapper)
        wait_for(lambda: wrapper.get_state() == model.Job.states.OK)
        assert wrapper.job.job_runner_external_id == attempt
        assert wrapper.stdout == "recovered\n"
        assert counter.read_text() == "once\n"
        detached.close()

    def test_lost_submit_response_recovers_lookup_without_repreparing(self):
        wrapper = self.wrapper()
        release = Path(self.test_directory) / "release-submit"
        wrapper.command_line = f"while [ ! -f {shlex.quote(str(release))} ]; do sleep 0.05; done; echo accepted"
        executor, _, _ = self.runner._executor(wrapper)
        original = executor.submit
        calls = []

        def accepted_then_lost(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append(result.id)
            if len(calls) == 1:
                raise ConnectionError("Response lost after durable acceptance")
            return result

        executor.submit = accepted_then_lost
        self.runner.mark_as_queued(wrapper)
        wait_for(lambda: wrapper.job.job_runner_external_id)
        assert len(calls) == 1
        assert wrapper.prepare_called
        assert len(executor.list()) == 1
        release.touch()
        wait_for(lambda: wrapper.get_state() == model.Job.states.OK)
        assert wrapper.stdout == "accepted\n"

    def test_upload_pool_exceeds_dispatch_threads_and_adopts_completion_context(self):
        release = Path(self.test_directory) / "release-uploads"
        wrappers = [self.wrapper(identifier, upload=True) for identifier in range(1, 5)]
        contexts: list[tuple[int, str]] = []

        def completion_context(wrapper, key):
            contexts.append((wrapper.job_id, key))
            return SimpleNamespace(enabled=True)

        with (
            patch("galaxy.jobs.runners.engagequeue.validate_upload"),
            patch(
                "galaxy.jobs.runners.engagequeue.UploadFinishContext",
                side_effect=completion_context,
            ),
        ):
            for wrapper in wrappers:
                wrapper.command_line = f"while [ ! -f {shlex.quote(str(release))} ]; do sleep 0.05; done; echo upload"
                self.runner.mark_as_queued(wrapper)
            wait_for(lambda: all(wrapper.get_state() == model.Job.states.RUNNING for wrapper in wrappers))
            assert len(wrappers) > self.runner.nworkers
            release.touch()
            wait_for(lambda: all(wrapper.get_state() == model.Job.states.OK for wrapper in wrappers))
        assert len(contexts) == len(wrappers)
        assert {key for _, key in contexts} == {
            required_json(Path(wrapper.working_directory) / RECORD_FILE)["key"] for wrapper in wrappers
        }

    def test_confirmed_cancel_keeps_native_files_and_cannot_finish_successfully(self):
        wrapper = self.wrapper()
        wrapper.command_line = "echo started; sleep 120"
        self.runner.mark_as_queued(wrapper)
        wait_for(lambda: wrapper.get_state() == model.Job.states.RUNNING)
        wrapper.change_state(model.Job.states.STOPPED)
        self.runner.stop_job(wrapper)
        executor, _, _ = self.runner._executor(wrapper)
        status = executor.wait(wrapper.job.job_runner_external_id, timeout=30)
        assert status.state == engagequeue.JobState.CANCELLED and status.writers_stopped
        self.runner.finish_job(EngageQueueJobState(wrapper, status.id))
        assert wrapper.get_state() == model.Job.states.STOPPED
        assert not hasattr(wrapper, "stdout")
        wrapper.cleanup.assert_not_called()
        assert Path(wrapper.working_directory, STOP_FILE).is_file()

    def test_cancellation_before_submission_never_executes_or_prepares(self):
        wrapper = self.wrapper()
        self.runner.stop_job(wrapper)
        self.runner.queue_job(wrapper)
        assert not wrapper.prepare_called
        assert wrapper.get_state() == model.Job.states.STOPPED
        executor, _, _ = self.runner._executor(wrapper)
        assert executor.list() == []

    def test_explicit_attachment_uses_existing_runtime_and_close_leaves_it_alive(self):
        wrapper = self.wrapper()
        external, _, _ = self.runner._executor(wrapper)
        external.ensure_runtime()
        attached = self.new_runner(attach_only=True)
        client, _, _ = attached._executor(wrapper)
        assert client.attach_only is True
        attached.shutdown()
        assert external._runtime_running()

    def test_staged_input_snapshot_survives_restart_without_preparing_again(self):
        wrapper = self.wrapper()
        wrapper.job_destination.params["stage_inputs"] = True
        source = Path(self.test_directory) / "selected-input"
        source.write_text("prepared snapshot\n")
        release = Path(self.test_directory) / "release-staged"
        job_io = wrapper.job_io
        job_io.working_directory = wrapper.working_directory

        def prepare(compute_environment):
            staged = compute_environment.input_path_rewrite(SimpleNamespace(get_file_name=lambda: str(source)))
            wrapper.command_line = (
                f"while [ ! -f {shlex.quote(str(release))} ]; do sleep 0.05; done; cat {shlex.quote(staged)}"
            )

        wrapper.prepare = Mock(side_effect=prepare)
        with patch.object(type(wrapper), "job_io", new_callable=PropertyMock, return_value=job_io):
            self.runner.mark_as_queued(wrapper)
            wait_for(lambda: wrapper.job.job_runner_external_id)
            attempt = wrapper.job.job_runner_external_id
            self.runner.shutdown()
            source.write_text("changed after preparation\n")
            release.touch()
            recovered = self.new_runner()
            recovered.recover(wrapper.job, wrapper)
            wait_for(lambda: wrapper.get_state() == model.Job.states.OK)
        assert wrapper.job.job_runner_external_id == attempt
        assert wrapper.stdout == "prepared snapshot\n"
        wrapper.prepare.assert_called_once()

    def test_preparation_configuration_failure_is_terminal_and_retains_files(self):
        wrapper = self.wrapper()
        wrapper.job_destination.params["cleanup_job"] = "always"
        wrapper.prepare = Mock(side_effect=ConfigurationError("invalid staged input"))
        original_fail = wrapper.fail
        cleanup_during_failure = []

        def fail(*args, **kwargs):
            cleanup_during_failure.append(wrapper.job_destination.params["cleanup_job"])
            return original_fail(*args, **kwargs)

        wrapper.fail = fail
        self.runner.queue_job(wrapper)
        assert wrapper.get_state() == model.Job.states.ERROR
        assert cleanup_during_failure == ["never"]
        assert wrapper.job_destination.params["cleanup_job"] == "always"
        executor, _, _ = self.runner._executor(wrapper)
        assert not executor.list()

    def test_unsupported_hard_limits_fail_without_retry_or_workspace_cleanup(self):
        wrapper = self.wrapper()
        wrapper.job_destination.params.update(cpus=1, memory_mb=64, require_hard_limits=True, cleanup_job="always")
        self._assert_permanent_submission_error(wrapper)

    def test_managed_profile_is_a_terminal_configuration_error_without_starting_a_runtime(self):
        for identifier, (symlink, frozen) in enumerate(((False, False), (True, False), (False, True)), start=21):
            wrapper = self.wrapper(identifier=identifier)
            state = Path(self.test_directory) / f"managed-{identifier}"
            state.mkdir()
            profile = state / "managed.json"
            if symlink:
                profile.symlink_to(state / "missing-profile")
            else:
                profile.write_text('{"schema": 1}\n')
            wrapper.job_destination.params.update(state_dir=self.state_dir, cleanup_job="always")
            wrapper.job_destination.params[STATE_PARAM if frozen else "state_dir"] = str(state)
            evidence = Path(wrapper.working_directory) / "retained-evidence"
            evidence.write_text("diagnostics\n")
            with patch.object(engagequeue, "Executor") as executor, patch.object(self.runner, "_retry") as retry:
                with pytest.raises(ConfigurationError, match="local execution only.*managed Docker profile"):
                    self.runner._executor(wrapper)
                self.runner.queue_job(wrapper)
            assert wrapper.get_state() == model.Job.states.ERROR
            assert evidence.read_text() == "diagnostics\n"
            if symlink:
                assert profile.readlink() == state / "missing-profile"
            else:
                assert profile.read_text() == '{"schema": 1}\n'
            assert not wrapper.prepare_called
            wrapper.cleanup.assert_not_called()
            executor.assert_not_called()
            retry.assert_not_called()

    def test_managed_profile_does_not_retry_recovered_monitoring_or_finishing(self):
        for identifier, callback in enumerate((self.runner.check_watched_item, self.runner.finish_job), start=24):
            wrapper = self.wrapper(identifier=identifier)
            state = Path(self.test_directory) / f"managed-{identifier}"
            state.mkdir()
            (state / "managed.json").write_text('{"schema": 1}\n')
            wrapper.job_destination.params.update(state_dir=self.state_dir, cleanup_job="always")
            wrapper.job_destination.params[STATE_PARAM] = str(state)
            root = Path(wrapper.working_directory)
            record = {"schema": 1, "job_id": str(identifier), "state_dir": str(state), "key": "retained-attempt"}
            (root / RECORD_FILE).write_text(json.dumps(record))
            wrapper.set_external_id("retained-external-id")
            with patch.object(engagequeue, "Executor") as executor, patch.object(self.runner, "monitor_job") as monitor:
                assert callback(EngageQueueJobState(wrapper, "retained-external-id")) is None
            assert wrapper.get_state() == model.Job.states.ERROR
            assert json.loads((root / RECORD_FILE).read_text()) == record
            assert wrapper.job.job_runner_external_id == "retained-external-id"
            assert not wrapper.prepare_called
            wrapper.cleanup.assert_not_called()
            executor.assert_not_called()
            monitor.assert_not_called()

    def test_conflicting_submission_preserves_existing_accepted_execution(self):
        wrapper = self.wrapper()
        root = Path(wrapper.working_directory)
        executor, _, pool = self.runner._executor(wrapper)
        with (
            patch.object(
                executor, "submit", side_effect=engagequeue.RuntimeUnavailable("Unavailable before acceptance")
            ),
            patch.object(self.runner, "_retry"),
        ):
            self.runner.queue_job(wrapper)
        record = required_json(root / RECORD_FILE)
        release = root / "release-existing"
        original = executor.submit(
            engagequeue.JobSpec(
                argv=["/bin/sh", "-c", f"while [ ! -f {shlex.quote(str(release))} ]; do sleep .05; done"],
                cwd=str(root),
                pool=pool,
            ),
            key=record["key"],
        )
        # Another client can accept this key after lookup missed. The SDK must
        # preserve that execution when its specification differs from ours.
        with patch.object(executor, "lookup", return_value=None):
            self._assert_permanent_submission_error(wrapper)
        assert executor.status(original.id).state.value in {"QUEUED", "STARTING", "RUNNING"}
        release.touch()
        assert executor.wait(original.id, timeout=20).state.value == "SUCCEEDED"

    def _assert_permanent_submission_error(self, wrapper):
        root = Path(wrapper.working_directory)
        evidence = root / "retained-evidence"
        evidence.write_text("diagnostics\n")
        executor, _, _ = self.runner._executor(wrapper)
        with (
            patch.object(executor, "cancel", wraps=executor.cancel) as cancel,
            patch.object(self.runner, "_retry") as retry,
        ):
            self.runner.queue_job(wrapper)
        assert wrapper.get_state() == model.Job.states.ERROR
        assert evidence.read_text() == "diagnostics\n"
        assert (root / RECORD_FILE).is_file()
        assert wrapper.job.job_runner_external_id is None
        wrapper.cleanup.assert_not_called()
        cancel.assert_not_called()
        retry.assert_not_called()

    def test_unavailable_or_drained_runtime_keeps_submission_retryable(self):
        for index, error_type in enumerate((engagequeue.RuntimeUnavailable, engagequeue.AdmissionClosed), start=10):
            wrapper = self.wrapper(identifier=index)
            executor, _, _ = self.runner._executor(wrapper)
            with (
                patch.object(executor, "submit", side_effect=error_type("Temporarily unavailable")),
                patch.object(self.runner, "_retry") as retry,
            ):
                self.runner.queue_job(wrapper)
            assert wrapper.get_state() != model.Job.states.ERROR
            assert (Path(wrapper.working_directory) / RECORD_FILE).is_file()
            wrapper.cleanup.assert_not_called()
            retry.assert_called_once_with(self.runner.queue_job, wrapper)

    def test_interactive_container_stop_keeps_shell_metadata_alive_across_restart(self):
        self._assert_interactive_container_stop_keeps_metadata_alive(retained=False)

    def test_forced_interactive_stop_records_oom_evidence_before_owned_cleanup(self):
        self._assert_interactive_container_stop_keeps_metadata_alive(retained=True)

    def _assert_interactive_container_stop_keeps_metadata_alive(self, retained):
        docker = shutil.which("docker")
        image = os.environ.get("ENGAGEQUEUE_DOCKER_TEST_IMAGE", "alpine:latest")
        if not docker or subprocess.run([docker, "image", "inspect", image], capture_output=True).returncode:
            pytest.skip("Docker and a cached validation image are required")
        wrapper = self.wrapper()
        wrapper.job_destination.params["cancel_grace_seconds"] = 0.2
        wrapper.tool.produces_entry_points = True
        wrapper.default_compute_environment = lambda: SimpleNamespace(materialized_objects={})
        wrapper.prepare = lambda compute_environment: None
        root = Path(wrapper.working_directory)
        name = "galaxy-stop-test-" + root.name.replace("_", "-")
        observed = root / "metadata-exit-code"
        metadata_release = root / "release-metadata"
        wrapper.metadata_command = (
            f"while [ ! -f {shlex.quote(str(metadata_release))} ]; do sleep 0.05; done; "
            f"cat {shlex.quote(str(root / 'galaxy_1.ec'))} > {shlex.quote(str(observed))}; "
            f"touch {shlex.quote(wrapper.mock_metadata_path)}"
        )

        def container(job_wrapper, **kwargs):
            token = job_wrapper._engagequeue_attempt_token
            job_wrapper._engagequeue_interactive_container = name
            job_wrapper._engagequeue_containers.append(
                SimpleNamespace(
                    container_name=name,
                    connection_configuration={"docker_cmd": docker},
                    _engagequeue_remove_on_exit=retained,
                )
            )
            trap = "trap '' TERM" if retained else "trap 'exit 143' TERM"
            command = trap + "; echo saved-output > /work/saved; touch /work/started; while :; do sleep 0.1; done"
            job_wrapper.command_line = " ".join(
                shlex.quote(value)
                for value in [
                    docker,
                    "run",
                    *([] if retained else ["--rm"]),
                    "--name",
                    name,
                    "--label",
                    "engagequeue.attempt=" + token,
                    "--mount",
                    f"type=bind,src={wrapper.tool_working_directory},dst=/work",
                    image,
                    "sh",
                    "-c",
                    command,
                ]
            )
            return None

        self.runner._find_container = container
        self.runner.mark_as_queued(wrapper)
        wait_for(lambda: (Path(wrapper.tool_working_directory) / "started").exists())
        executor, _, _ = self.runner._executor(wrapper)
        attempt = wrapper.job.job_runner_external_id
        receipt_path = Path(executor.container_stop_receipt_path(attempt, name))
        wait_for(lambda: executor.inspect(attempt).get("owned_container_ids", [None])[0])
        wrapper.change_state(model.Job.states.STOPPING)
        # The monitor observes the API state before the handler's Stop queue
        # has called stop_job or published an intent file.
        with patch.object(executor, "cancel", wraps=executor.cancel) as cancel:
            self.runner.check_watched_item(EngageQueueJobState(wrapper, attempt))
            cancel.assert_not_called()
        assert (root / GRACEFUL_STOP_FILE).is_file()
        assert not (root / STOP_FILE).exists()
        wrapper.change_state(model.Job.states.STOPPED)
        self.runner.stop_job(wrapper)
        self.runner.shutdown()
        assert not observed.exists()
        if retained:
            receipt = wait_for(
                lambda: value if (value := _read_json(receipt_path)) and value.get("status") == "stopped" else None
            )
            assert receipt["issued_signal"] == "KILL" and receipt["exit_code"] == 137
            assert receipt["oom_killed"] is False
            stopped = json.loads(subprocess.check_output([docker, "inspect", name]))[0]
            assert stopped["State"]["Running"] is False
        metadata_release.touch()
        with engagequeue.Executor(self.state_dir) as independent:
            status = independent.wait(attempt, timeout=30)
            assert status.returncode == 0 and status.writers_stopped
        assert observed.read_text().strip() == "0"
        assert Path(wrapper.mock_metadata_path).exists()
        assert (Path(wrapper.tool_working_directory) / "saved").read_text() == "saved-output\n"
        if retained:
            assert subprocess.run([docker, "inspect", name], capture_output=True).returncode != 0
        recovered = self.new_runner()
        recovered.recover(wrapper.job, wrapper)
        wait_for(lambda: wrapper.get_state() == model.Job.states.OK)
        assert wrapper.exit_code == 0

    def test_sdk_failure_after_graceful_stop_is_not_imported_as_success(self):
        wrapper = self.wrapper()
        wrapper.tool.produces_entry_points = True
        root = Path(wrapper.working_directory)
        executor, _, pool = self.runner._executor(wrapper)
        key = "galaxy:failed-interactive"
        handle = executor.submit(
            engagequeue.JobSpec(argv=["/bin/sh", "-c", "exit 124"], cwd=str(root), pool=pool), key=key
        )
        status = executor.wait(handle.id, timeout=20)
        assert status.state.value == "FAILED" and status.writers_stopped
        (root / RECORD_FILE).write_text(
            json.dumps({"schema": 1, "job_id": str(wrapper.job_id), "key": key, "interactive_container": "tool"})
        )
        (root / GRACEFUL_STOP_FILE).write_text(
            json.dumps(
                {
                    "schema": 1,
                    "job_id": str(wrapper.job_id),
                    "key": key,
                    "name": "tool",
                    "label_key": "engagequeue.attempt",
                    "label_value": "failed-interactive",
                }
            )
        )
        wrapper.change_state(model.Job.states.STOPPED)
        with patch.object(executor, "container_stop_receipt_path", return_value=str(root / "unused-receipt")):
            self.runner.finish_job(EngageQueueJobState(wrapper, handle.id))
        assert wrapper.get_state() == model.Job.states.ERROR
        assert wrapper.exit_code == 124
        assert not Path(wrapper.mock_metadata_path).exists()
        wrapper.cleanup.assert_not_called()

    def test_late_interactive_stop_collects_completed_attempt_without_rewriting_tool_status(self):
        docker = shutil.which("docker")
        if not docker or subprocess.run([docker, "info"], capture_output=True).returncode:
            pytest.skip("Docker daemon is required to verify declared-container absence")
        wrapper = self.wrapper()
        wrapper.tool.produces_entry_points = True
        root = Path(wrapper.working_directory)
        executor, _, pool = self.runner._executor(wrapper)
        key, name = "galaxy:late-stop", "galaxy-late-stop-" + root.name.replace("_", "-")
        state = EngageQueueJobState(wrapper, None)
        handle = executor.submit(
            engagequeue.JobSpec(
                argv=[
                    "/bin/sh",
                    "-c",
                    f"echo 5 > {shlex.quote(state.exit_code_file)}; touch {shlex.quote(wrapper.mock_metadata_path)}",
                ],
                cwd=str(root),
                pool=pool,
                stdout=state.output_file,
                stderr=state.error_file,
                containers=(
                    engagequeue.ContainerSpec(
                        name=name, label_key="engagequeue.attempt", label_value="late-stop", executable=docker
                    ),
                ),
            ),
            key=key,
        )
        assert executor.wait(handle.id, timeout=20).state.value == "SUCCEEDED"
        wrapper.set_external_id(handle.id)
        (root / RECORD_FILE).write_text(
            json.dumps({"schema": 1, "job_id": str(wrapper.job_id), "key": key, "interactive_container": name})
        )
        wrapper.change_state(model.Job.states.STOPPED)
        with patch.object(executor, "stop_container", wraps=executor.stop_container) as stop:
            # Completion can see STOPPED before StopQueue has published the
            # late normal intent, even though execution already succeeded.
            self.runner.finish_job(EngageQueueJobState(wrapper, handle.id))
            stop.assert_not_called()
        marker = required_json(root / GRACEFUL_STOP_FILE)
        assert marker["requested_while_terminal"] is True
        assert not (root / STOP_FILE).exists()
        assert wrapper.exit_code == 5
        assert Path(state.exit_code_file).read_text().strip() == "5"
        assert Path(wrapper.mock_metadata_path).exists()


@pytest.mark.parametrize("library", [False, True])
@pytest.mark.parametrize("extension", ["fasta", "bam"])
def test_direct_standalone_metadata_uses_framework_and_imports_existing_inputs(
    tmp_path, monkeypatch, library, extension
):
    app = GalaxyDataTestApp(GalaxyDataTestConfig(root=str(tmp_path / "app")))
    app.config["metadata_strategy"] = "directory"
    session = app.model.session
    executor = engagequeue.Executor(state_dir=tmp_path / "runtime")
    try:
        history = model.History(name="Metadata input")
        job = model.Job()
        job.tool_id, job.tool_version, job.history = "__SET_METADATA__", "1.0.3", history
        session.add_all([history, job])
        session.commit()
        cls = model.LibraryDatasetDatasetAssociation if library else model.HistoryDatasetAssociation
        dataset = cls(sa_session=session, create_dataset=True, extension=extension)
        assert dataset.dataset is not None
        session.add(dataset)
        if not library:
            history.add_dataset(dataset)
        app.object_store.create(dataset.dataset)
        source = Path(__file__).resolve().parents[4] / "test-data" / f"1.{extension}"
        shutil.copyfile(source, dataset.dataset.get_file_name())
        original = Path(dataset.get_file_name()).read_bytes()
        dataset.dataset.state, dataset.dataset.file_size = model.Dataset.states.OK, Decimal(len(original))
        dataset.init_meta()
        if library:
            job.add_input_library_dataset("input1", dataset)
        else:
            job.add_input_dataset("input1", dataset)
        dataset.state = model.Dataset.states.SETTING_METADATA
        session.commit()
        identity = dataset.id, dataset.dataset.uuid
        root = tmp_path / "job"
        (root / "working").mkdir(parents=True)
        app.datatypes_registry.to_xml_file(path=str(root / "registry.xml"))
        PortableDirectoryMetadataGenerator(job.id).setup_external_metadata(
            {"input1": dataset},
            {},
            session,
            uses_tool_provided_metadata=False,
            allows_unnamed_outputs=False,
            allows_external_output_paths=False,
            tmp_dir=str(root),
            output_fnames=[DatasetPath(dataset.dataset.id, dataset.get_file_name())],
            datatypes_config=str(root / "registry.xml"),
            job_metadata=str(root / "working/galaxy.json"),
            include_command=False,
            job=job,
            groom_directory_content=False,
        )
        wrapper = SimpleNamespace(
            working_directory=str(root),
            galaxy_lib_dir=str(Path(__file__).resolve().parents[4] / "lib"),
            runner_command_line='cd working; cd ..; "${GALAXY_PYTHON:-python}" -c '
            + shlex.quote("from galaxy_ext.metadata.set_metadata import set_metadata; set_metadata()"),
        )
        runner = object.__new__(EngageQueueJobRunner)
        monkeypatch.setattr(runner, "app", app, raising=False)
        runner._prepare_standalone_metadata(wrapper)
        environment = {key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "GALAXY_PYTHON")}
        handle = executor.submit(
            engagequeue.JobSpec(argv=["/bin/bash", "-c", wrapper.runner_command_line], cwd=str(root), env=environment),
            key=f"metadata:{job.id}",
        )
        status = executor.wait(handle.id, timeout=30)
        assert status.returncode == 0, executor.inspect(handle.id)
        assert json.loads((root / "metadata/metadata_results_input1").read_text())[0] is True
        tool = object.__new__(SetMetadataTool)
        monkeypatch.setattr(tool, "app", app, raising=False)
        tool.id = "__SET_METADATA__"
        monkeypatch.setattr(tools_module, "JobWorkingDirectory", lambda *_: SimpleNamespace(resolve=lambda: str(root)))
        tool.exec_after_process(app, {"input1": dataset}, {}, {}, job)
        assert dataset.state == model.Dataset.states.OK
        assert (dataset.id, dataset.dataset.uuid) == identity
        assert Path(dataset.get_file_name()).read_bytes() == original
        if extension == "fasta":
            assert dataset.metadata.sequences > 0
        else:
            assert Path(dataset.metadata.bam_index.get_file_name()).exists()
    finally:
        executor.shutdown(wait=True, timeout=15)
        executor.close()
        session.remove()
        app.model.engine.dispose()

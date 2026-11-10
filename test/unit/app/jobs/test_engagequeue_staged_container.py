"""Optional real Docker validation of selected local input snapshots."""

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

engagequeue = pytest.importorskip("engagequeue")

from galaxy import model
from galaxy.job_execution.setup import JobIO
from galaxy.jobs.runners.engagequeue import _StagedInputComputeEnvironment


def test_native_docker_reads_only_staged_selected_inputs_and_keeps_them_read_only(tmp_path):
    docker = shutil.which("docker")
    image = os.environ.get("ENGAGEQUEUE_DOCKER_TEST_IMAGE", "alpine:latest")
    if docker is None:
        pytest.skip("Docker executable is unavailable")
    available = subprocess.run([docker, "image", "inspect", image], capture_output=True, timeout=15)
    if available.returncode:
        pytest.skip("Docker daemon and a cached validation image are required")

    storage = tmp_path / "permanent-store"
    storage.mkdir()
    primary, metadata, unrelated = [storage / name for name in ("selected.dat", "index.bai", "unrelated-secret.dat")]
    primary.write_text("selected-primary\n")
    metadata.write_text("selected-sidecar\n")
    unrelated.write_text("unrelated-secret\n")
    extras = storage / "selected_files"
    (extras / "nested").mkdir(parents=True)
    (extras / "nested/value.txt").write_text("selected-extra\n")

    job = tmp_path / "ssd-job"
    job.mkdir()
    outputs = job / "working"
    outputs.mkdir()
    dataset = SimpleNamespace(get_file_name=lambda: str(primary), dataset=SimpleNamespace(extra_files_path=str(extras)))
    environment = _StagedInputComputeEnvironment(Mock(spec=JobIO, working_directory=str(job)), model.Job())
    staged_primary = Path(environment.input_path_rewrite(dataset))
    metadata_path = environment.input_metadata_rewrite(dataset, str(metadata))
    assert metadata_path is not None
    staged_metadata = Path(metadata_path)
    staged_extras = Path(environment.input_extra_files_rewrite(dataset))
    assert set(environment.staged_paths) == {str(staged_primary), str(staged_metadata), str(staged_extras)}
    assert all(path.is_relative_to(job / "inputs") for path in (staged_primary, staged_metadata, staged_extras))

    # The snapshot is independent of later source edits. Only the selected
    # copies, not the broad permanent store, are visible inside the container.
    primary.write_text("changed-source\n")
    metadata.write_text("changed-sidecar-source\n")
    (extras / "nested/value.txt").write_text("changed-extra-source\n")
    attempt = uuid.uuid4().hex
    name = "engagequeue-staged-test-" + attempt
    argv = [
        docker,
        "run",
        "--rm",
        "--name",
        name,
        "--label",
        "engagequeue.attempt=" + attempt,
        "--network",
        "none",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--read-only",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
    ]
    for path in (staged_primary, staged_metadata, staged_extras):
        argv.extend(["--mount", f"type=bind,src={path},dst={path},readonly"])
    argv.extend(
        [
            "--mount",
            f"type=bind,src={outputs},dst=/results",
            "--workdir",
            "/results",
            image,
            "/bin/sh",
            "-ceu",
            r"""
test "$(cat "$1")" = selected-primary
test "$(cat "$2")" = selected-sidecar
test "$(cat "$3/nested/value.txt")" = selected-extra
test ! -e "$4"
test ! -e "$5"
if { printf forbidden >> "$1"; } 2>/dev/null; then exit 11; fi
if { printf forbidden >> "$2"; } 2>/dev/null; then exit 12; fi
if { printf forbidden >> "$3/nested/value.txt"; } 2>/dev/null; then exit 13; fi
if { printf forbidden > "$3/new-file"; } 2>/dev/null; then exit 14; fi
printf 'selected inputs read; writes denied; output writable\n' > /results/result.txt
""",
            "staged-input-check",
            str(staged_primary),
            str(staged_metadata),
            str(staged_extras),
            str(unrelated),
            str(storage),
        ]
    )
    executor = engagequeue.Executor(tmp_path / "executor", runtime_python=str(Path(sys.prefix) / "bin/python"))
    handle = None
    try:
        handle = executor.submit(
            engagequeue.JobSpec(
                argv=argv,
                cwd=str(job),
                stdout=str(job / "stdout"),
                stderr=str(job / "stderr"),
                container=engagequeue.ContainerSpec(name=name, label_value=attempt, executable=docker),
            ),
            key="staged-input-test:" + attempt,
        )
        status = executor.wait(handle.id, timeout=45)
        assert status.state == engagequeue.JobState.SUCCEEDED, (job / "stderr").read_text()
        assert status.returncode == 0
        assert executor.inspect(handle.id)["writers_stopped"] is True
        assert (outputs / "result.txt").read_text() == "selected inputs read; writes denied; output writable\n"
        assert staged_primary.read_text() == "selected-primary\n"
        assert staged_metadata.read_text() == "selected-sidecar\n"
        assert (staged_extras / "nested/value.txt").read_text() == "selected-extra\n"
        assert not (staged_extras / "new-file").exists()
        assert unrelated.read_text() == "unrelated-secret\n"
    finally:
        if handle is not None and not executor.status(handle.id).terminal:
            executor.cancel(handle.id, wait=True, timeout=20)
        executor.shutdown(wait=True, timeout=20)
        executor.close()

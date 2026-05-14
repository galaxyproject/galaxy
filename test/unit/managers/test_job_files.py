"""Unit tests for ``galaxy.managers.job_files.JobFilesManager``.

These exercise the auth and path-policy contracts in isolation via small
stub objects — no Galaxy app, no SQLAlchemy, no real object store.
"""

from __future__ import annotations

import os
from typing import (
    Any,
    Optional,
)

import pytest

from galaxy import exceptions
from galaxy.managers.job_files import JobFilesManager


class _StubSecurity:
    """Synthetic id-encoder. ``decode_id("ENC:N")`` returns ``N``;
    ``encode_id(N, kind="K")`` returns ``"EXPECTED[K]:N"``. Deterministic
    and self-explanatory so the kind selected by the manager is visible in
    the assertion failure message."""

    def decode_id(self, encoded: str) -> int:
        prefix, _, suffix = encoded.partition(":")
        if prefix != "ENC":
            raise ValueError(f"unexpected encoded id: {encoded!r}")
        return int(suffix)

    def encode_id(self, obj_id: int, kind: Optional[str] = None) -> str:
        return f"EXPECTED[{kind or ''}]:{obj_id}"


class _StubObjectStore:
    def __init__(self, working_directory: str) -> None:
        self._working_directory = working_directory

    def get_filename(self, *args: Any, **kwargs: Any) -> str:
        return self._working_directory


class _StubSession:
    def __init__(self, jobs_by_id: dict[int, Any]) -> None:
        self._jobs = jobs_by_id

    def get(self, model_cls: Any, pk: int) -> Any:
        # The manager only calls ``session.get(Job, pk)``; the stub returns
        # whatever Job-like object is registered without inspecting the
        # class. ``model_cls`` is monkey-patched to ``_StubJob`` (see the
        # ``_patch_job_class`` fixture) so a ``__name__`` dispatch would
        # have to match that anyway.
        return self._jobs.get(pk)


class _StubModel:
    def __init__(self, session: _StubSession) -> None:
        self.session = session


class _StubApp:
    def __init__(self, security: _StubSecurity, model: _StubModel, object_store: _StubObjectStore) -> None:
        self.security = security
        self.model = model
        self.object_store = object_store


class _StubDataset:
    """Stand-in for HistoryDatasetAssociation — just the methods the
    manager calls."""

    def __init__(self, *, file_path: str, extra_files_path: Optional[str] = None) -> None:
        self._file_path = file_path
        self.extra_files_path = extra_files_path

    def get_file_name(self) -> str:
        return self._file_path


class _StubAssoc:
    def __init__(self, dataset: _StubDataset) -> None:
        self.dataset = dataset


class _StubJob:
    """Just enough Job for the manager. ``destination_params`` carries the
    BYOC binding when set. ``state`` is one of ``Job.non_ready_states``
    for happy-path tests."""

    # Mirrors galaxy.model.Job.non_ready_states; redefining locally so
    # we don't drag the whole model module into a "manager unit test".
    non_ready_states = ["new", "resubmitted", "upload", "waiting", "queued", "running"]

    def __init__(
        self,
        *,
        id: int,
        state: str = "running",
        destination_params: Optional[dict[str, Any]] = None,
        input_datasets: Optional[list[_StubAssoc]] = None,
        output_datasets: Optional[list[_StubAssoc]] = None,
    ) -> None:
        self.id = id
        self.state = state
        self.destination_params = destination_params or {}
        self.input_datasets = input_datasets or []
        self.output_datasets = output_datasets or []
        self.input_library_datasets: list[_StubAssoc] = []
        self.output_library_datasets: list[_StubAssoc] = []


@pytest.fixture(autouse=True)
def _patch_job_class(monkeypatch):
    """Reroute the manager's ``session.get(Job, ...)`` and ``Job.non_ready_states``
    lookup to our stub class so we don't need the SQLAlchemy import chain."""
    # The manager imports Job from galaxy.model; substitute our stub class
    # in that module so `session.get(Job, pk)` resolves correctly and the
    # `job.state not in Job.non_ready_states` check uses the stub list.
    monkeypatch.setattr("galaxy.managers.job_files.Job", _StubJob, raising=True)


@pytest.fixture
def tmp_working_dir(tmp_path):
    """A real on-disk directory acting as the job's working_directory so
    ``in_directory`` / ``realpath`` checks are meaningful."""
    d = tmp_path / "job_work"
    d.mkdir()
    (d / "working").mkdir()
    return str(d)


def _make_manager(*, jobs: dict[int, _StubJob], working_directory: str = "/tmp/nonexistent") -> JobFilesManager:
    app = _StubApp(
        security=_StubSecurity(),
        model=_StubModel(_StubSession(jobs)),
        object_store=_StubObjectStore(working_directory),
    )
    return JobFilesManager(app)  # type: ignore[arg-type]


# ---- authorize_for_files / authorize_for_token --------------------------


class TestAuthorize:
    def test_files_happy_path_legacy_kind(self):
        job = _StubJob(id=5)
        mgr = _make_manager(jobs={5: job})
        returned = mgr.authorize_for_files("ENC:5", "EXPECTED[jobs_files]:5")
        assert returned is job

    def test_files_uses_compute_resource_kind_when_bound(self):
        job = _StubJob(id=5, destination_params={"compute_resource_id": 7})
        mgr = _make_manager(jobs={5: job})
        # The legacy key MUST NOT validate
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.authorize_for_files("ENC:5", "EXPECTED[jobs_files]:5")
        # The tenant-scoped key validates
        returned = mgr.authorize_for_files("ENC:5", "EXPECTED[jobs_files:compute_resource:7]:5")
        assert returned is job

    def test_files_missing_key_raises(self):
        mgr = _make_manager(jobs={5: _StubJob(id=5)})
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.authorize_for_files("ENC:5", None)
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.authorize_for_files("ENC:5", "")

    def test_files_unknown_job_raises(self):
        mgr = _make_manager(jobs={})
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.authorize_for_files("ENC:5", "anything")

    def test_files_terminal_job_raises(self):
        job = _StubJob(id=5, state="ok")
        mgr = _make_manager(jobs={5: job})
        with pytest.raises(exceptions.ItemAccessibilityException, match="already completed"):
            mgr.authorize_for_files("ENC:5", "EXPECTED[jobs_files]:5")

    def test_token_happy_path_raises_authentication_failed(self):
        job = _StubJob(id=5)
        mgr = _make_manager(jobs={5: job})
        returned = mgr.authorize_for_token("ENC:5", "EXPECTED[jobs_token]:5")
        assert returned is job
        with pytest.raises(exceptions.AuthenticationFailed):
            mgr.authorize_for_token("ENC:5", "wrong")

    def test_token_uses_compute_resource_kind_when_bound(self):
        job = _StubJob(id=5, destination_params={"compute_resource_id": 7})
        mgr = _make_manager(jobs={5: job})
        with pytest.raises(exceptions.AuthenticationFailed):
            mgr.authorize_for_token("ENC:5", "EXPECTED[jobs_token]:5")
        returned = mgr.authorize_for_token("ENC:5", "EXPECTED[jobs_token:compute_resource:7]:5")
        assert returned is job


# ---- assert_readable / assert_writable ----------------------------------


class TestPathPolicy:
    def test_read_in_working_dir_allowed(self, tmp_working_dir):
        job = _StubJob(id=5)
        path = os.path.join(tmp_working_dir, "working", "outputs", "discovered.txt")
        mgr = _make_manager(jobs={5: job}, working_directory=tmp_working_dir)
        # No raise.
        mgr.assert_readable(job, path)

    def test_read_input_dataset_allowed(self, tmp_path):
        input_file = tmp_path / "input.dat"
        input_file.write_bytes(b"x")
        job = _StubJob(id=5, input_datasets=[_StubAssoc(_StubDataset(file_path=str(input_file)))])
        mgr = _make_manager(jobs={5: job})
        mgr.assert_readable(job, str(input_file))

    def test_read_arbitrary_path_rejected(self, tmp_path):
        outside = tmp_path / "outside.txt"
        outside.write_bytes(b"x")
        job = _StubJob(id=5)
        mgr = _make_manager(jobs={5: job}, working_directory="/tmp/nonexistent")
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.assert_readable(job, str(outside))

    def test_read_symlink_rejected(self, tmp_path):
        target = tmp_path / "real.txt"
        target.write_bytes(b"x")
        link = tmp_path / "link"
        os.symlink(str(target), str(link))
        # Even if the symlink TARGET would be allowed, the symlink path itself
        # is refused outright.
        job = _StubJob(id=5, input_datasets=[_StubAssoc(_StubDataset(file_path=str(target)))])
        mgr = _make_manager(jobs={5: job})
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.assert_readable(job, str(link))

    def test_write_input_path_rejected(self, tmp_path):
        # Even when a path matches an input dataset, writes are not allowed —
        # the runner posts outputs, not inputs.
        input_file = tmp_path / "input.dat"
        input_file.write_bytes(b"x")
        job = _StubJob(id=5, input_datasets=[_StubAssoc(_StubDataset(file_path=str(input_file)))])
        mgr = _make_manager(jobs={5: job})
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.assert_writable(job, str(input_file))

    def test_write_output_path_allowed(self, tmp_path):
        out = tmp_path / "out.dat"
        out.write_bytes(b"")
        job = _StubJob(id=5, output_datasets=[_StubAssoc(_StubDataset(file_path=str(out)))])
        mgr = _make_manager(jobs={5: job})
        mgr.assert_writable(job, str(out))

    def test_write_compute_resource_blocks_outputs_populated(self, tmp_working_dir):
        # outputs_populated/** is denied for BYOC even though it's
        # inside the working directory.
        job = _StubJob(id=5, destination_params={"compute_resource_id": 7})
        mgr = _make_manager(jobs={5: job}, working_directory=tmp_working_dir)
        denied = os.path.join(tmp_working_dir, "metadata", "outputs_populated", "results.json")
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.assert_writable(job, denied)
        # While the non-BYOC variant of the same job WOULD permit it.
        legacy_job = _StubJob(id=6)
        mgr_legacy = _make_manager(jobs={6: legacy_job}, working_directory=tmp_working_dir)
        mgr_legacy.assert_writable(legacy_job, denied)  # No raise.

    def test_write_compute_resource_allows_working_subdir(self, tmp_working_dir):
        job = _StubJob(id=5, destination_params={"compute_resource_id": 7})
        mgr = _make_manager(jobs={5: job}, working_directory=tmp_working_dir)
        allowed = os.path.join(tmp_working_dir, "working", "outputs", "galaxy.json")
        mgr.assert_writable(job, allowed)  # No raise.

    def test_write_symlink_rejected(self, tmp_path):
        target = tmp_path / "real.out"
        target.write_bytes(b"")
        link = tmp_path / "link"
        os.symlink(str(target), str(link))
        job = _StubJob(id=5, output_datasets=[_StubAssoc(_StubDataset(file_path=str(target)))])
        mgr = _make_manager(jobs={5: job})
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.assert_writable(job, str(link))

"""Unit tests for ``galaxy.managers.job_files.JobFilesManager``.

These exercise the auth and path-policy contracts in isolation via small
stub objects — no Galaxy app, no SQLAlchemy, no real object store.
"""

from __future__ import annotations

import os
from typing import (
    Any,
    cast,
    Optional,
    TYPE_CHECKING,
)

import pytest

from galaxy import exceptions
from galaxy.managers.job_files import JobFilesManager

if TYPE_CHECKING:
    from galaxy.model import Job


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
    """Resolves a job's working directory strictly by ``extra_dir`` — the job
    id the manager passes to ``get_filename``. Keying on it (rather than
    returning one directory unconditionally) means a regression that drops
    ``extra_dir`` — and would alias one job's working dir onto a shared
    parent — surfaces as a lookup miss instead of silently passing."""

    def __init__(self, working_dirs: dict[str, str]) -> None:
        self._working_dirs = working_dirs

    def get_filename(self, job: Any, *, extra_dir: Optional[str] = None, **kwargs: Any) -> str:
        if extra_dir not in self._working_dirs:
            raise AssertionError(
                f"object store queried with extra_dir={extra_dir!r}; "
                f"known job working dirs: {sorted(self._working_dirs)}"
            )
        return self._working_dirs[extra_dir]


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


def _stub_job(**kwargs: Any) -> Job:
    """Build a ``_StubJob`` but type it as the real ``Job`` so call sites
    type-check against ``JobFilesManager``'s actual ``Job``-typed API. The
    autouse ``_patch_job_class`` fixture makes the manager treat the stub as a
    Job at runtime; this cast aligns the static view."""
    return cast("Job", _StubJob(**kwargs))


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


def _make_manager(
    *,
    jobs: dict[int, Any],
    working_directory: str = "/tmp/nonexistent",
    working_dirs: Optional[dict[str, str]] = None,
) -> JobFilesManager:
    # By default every job resolves to the same ``working_directory`` (most
    # tests use a single job). Pass ``working_dirs`` to give jobs distinct
    # directories keyed by ``str(job.id)``.
    if working_dirs is None:
        working_dirs = {str(job_id): working_directory for job_id in jobs}
    return JobFilesManager(
        _StubSecurity(),  # type: ignore[arg-type]
        _StubSession(jobs),  # type: ignore[arg-type]
        _StubObjectStore(working_dirs),  # type: ignore[arg-type]
    )


# ---- authorize_for_files / authorize_for_token --------------------------


class TestAuthorize:
    def test_files_happy_path_legacy_kind(self):
        job = _stub_job(id=5)
        mgr = _make_manager(jobs={5: job})
        returned = mgr.authorize_for_files("ENC:5", "EXPECTED[jobs_files]:5")
        assert returned is job

    def test_files_uses_compute_resource_kind_when_bound(self):
        job = _stub_job(id=5, destination_params={"compute_resource_id": 7})
        mgr = _make_manager(jobs={5: job})
        # The legacy key MUST NOT validate
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.authorize_for_files("ENC:5", "EXPECTED[jobs_files]:5")
        # The tenant-scoped key validates
        returned = mgr.authorize_for_files("ENC:5", "EXPECTED[jf:cr:7]:5")
        assert returned is job

    def test_files_missing_key_raises(self):
        mgr = _make_manager(jobs={5: _stub_job(id=5)})
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.authorize_for_files("ENC:5", None)
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.authorize_for_files("ENC:5", "")

    def test_files_unknown_job_raises(self):
        mgr = _make_manager(jobs={})
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.authorize_for_files("ENC:5", "anything")

    def test_files_terminal_job_raises(self):
        job = _stub_job(id=5, state="ok")
        mgr = _make_manager(jobs={5: job})
        with pytest.raises(exceptions.ItemAccessibilityException, match="already completed"):
            mgr.authorize_for_files("ENC:5", "EXPECTED[jobs_files]:5")

    def test_token_happy_path_raises_authentication_failed(self):
        job = _stub_job(id=5)
        mgr = _make_manager(jobs={5: job})
        returned = mgr.authorize_for_token("ENC:5", "EXPECTED[jobs_token]:5")
        assert returned is job
        with pytest.raises(exceptions.AuthenticationFailed):
            mgr.authorize_for_token("ENC:5", "wrong")

    def test_token_uses_compute_resource_kind_when_bound(self):
        job = _stub_job(id=5, destination_params={"compute_resource_id": 7})
        mgr = _make_manager(jobs={5: job})
        with pytest.raises(exceptions.AuthenticationFailed):
            mgr.authorize_for_token("ENC:5", "EXPECTED[jobs_token]:5")
        returned = mgr.authorize_for_token("ENC:5", "EXPECTED[jt:cr:7]:5")
        assert returned is job


# ---- assert_readable / assert_writable ----------------------------------


class TestPathPolicy:
    def test_read_in_working_dir_allowed(self, tmp_working_dir):
        job = _stub_job(id=5)
        path = os.path.join(tmp_working_dir, "working", "outputs", "discovered.txt")
        mgr = _make_manager(jobs={5: job}, working_directory=tmp_working_dir)
        # No raise.
        mgr.assert_readable(job, path)

    def test_read_input_dataset_allowed(self, tmp_path):
        input_file = tmp_path / "input.dat"
        input_file.write_bytes(b"x")
        job = _stub_job(id=5, input_datasets=[_StubAssoc(_StubDataset(file_path=str(input_file)))])
        mgr = _make_manager(jobs={5: job})
        mgr.assert_readable(job, str(input_file))

    def test_read_arbitrary_path_rejected(self, tmp_path):
        outside = tmp_path / "outside.txt"
        outside.write_bytes(b"x")
        job = _stub_job(id=5)
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
        job = _stub_job(id=5, input_datasets=[_StubAssoc(_StubDataset(file_path=str(target)))])
        mgr = _make_manager(jobs={5: job})
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.assert_readable(job, str(link))

    def test_write_input_path_rejected(self, tmp_path):
        # Even when a path matches an input dataset, writes are not allowed —
        # the runner posts outputs, not inputs.
        input_file = tmp_path / "input.dat"
        input_file.write_bytes(b"x")
        job = _stub_job(id=5, input_datasets=[_StubAssoc(_StubDataset(file_path=str(input_file)))])
        mgr = _make_manager(jobs={5: job})
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.assert_writable(job, str(input_file))

    def test_write_output_path_allowed(self, tmp_path):
        out = tmp_path / "out.dat"
        out.write_bytes(b"")
        job = _stub_job(id=5, output_datasets=[_StubAssoc(_StubDataset(file_path=str(out)))])
        mgr = _make_manager(jobs={5: job})
        mgr.assert_writable(job, str(out))

    def test_write_compute_resource_blocks_outputs_populated(self, tmp_working_dir):
        # outputs_populated/** is denied for BYOC even though it's
        # inside the working directory.
        job = _stub_job(id=5, destination_params={"compute_resource_id": 7})
        mgr = _make_manager(jobs={5: job}, working_directory=tmp_working_dir)
        denied = os.path.join(tmp_working_dir, "metadata", "outputs_populated", "results.json")
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.assert_writable(job, denied)
        # While the non-BYOC variant of the same job WOULD permit it.
        legacy_job = _stub_job(id=6)
        mgr_legacy = _make_manager(jobs={6: legacy_job}, working_directory=tmp_working_dir)
        mgr_legacy.assert_writable(legacy_job, denied)  # No raise.

    def test_write_compute_resource_allows_working_subdir(self, tmp_working_dir):
        job = _stub_job(id=5, destination_params={"compute_resource_id": 7})
        mgr = _make_manager(jobs={5: job}, working_directory=tmp_working_dir)
        allowed = os.path.join(tmp_working_dir, "working", "outputs", "galaxy.json")
        mgr.assert_writable(job, allowed)  # No raise.

    def test_write_resolves_this_jobs_working_dir(self, tmp_path):
        """The working-dir check must resolve *this* job's directory (via
        ``extra_dir``), not a shared parent: a key authorised for job A must
        not let a write land in job B's working directory. Regression guard
        for a manager that drops ``extra_dir`` and aliases jobs together."""
        work_a = tmp_path / "job_a" / "working"
        work_a.mkdir(parents=True)
        work_b = tmp_path / "job_b" / "working"
        work_b.mkdir(parents=True)
        job_a = _stub_job(id=5, destination_params={"compute_resource_id": 7})
        job_b = _stub_job(id=6, destination_params={"compute_resource_id": 7})
        mgr = _make_manager(
            jobs={5: job_a, 6: job_b},
            working_dirs={"5": str(work_a.parent), "6": str(work_b.parent)},
        )

        # job_a may write inside its own working directory...
        mgr.assert_writable(job_a, str(work_a / "out.txt"))  # No raise.
        # ...but not into job_b's, even though both are compute-resource jobs.
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.assert_writable(job_a, str(work_b / "out.txt"))

    def test_write_symlink_rejected(self, tmp_path):
        target = tmp_path / "real.out"
        target.write_bytes(b"")
        link = tmp_path / "link"
        os.symlink(str(target), str(link))
        job = _stub_job(id=5, output_datasets=[_StubAssoc(_StubDataset(file_path=str(target)))])
        mgr = _make_manager(jobs={5: job})
        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.assert_writable(job, str(link))


class TestStoreUploadedFile:
    def test_move_into_place(self, tmp_path):
        # Realistic setup: an output dataset path the runner is allowed to
        # write, and a NamedTemporaryFile-style ``source`` carrying content.
        target_file = tmp_path / "outputs" / "out.dat"
        job = _stub_job(id=5, output_datasets=[_StubAssoc(_StubDataset(file_path=str(target_file)))])
        mgr = _make_manager(jobs={5: job})

        source = tmp_path / "upload.tmp"
        source.write_bytes(b"hello")

        class _Src:
            name = str(source)

            def close(self):
                pass

        mgr.store_uploaded_file(job, str(target_file), _Src())  # type: ignore[arg-type]
        # Move semantics: source is gone, target has the bytes, intermediate
        # directories were created.
        assert target_file.read_bytes() == b"hello"
        assert not source.exists()

    def test_append_to_existing_tool_stdout(self, tmp_path):
        target = tmp_path / "outputs" / "tool_stdout"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"first ")
        job = _stub_job(id=5, output_datasets=[_StubAssoc(_StubDataset(file_path=str(target)))])
        mgr = _make_manager(jobs={5: job})

        source = tmp_path / "more.txt"
        source.write_bytes(b"second")

        class _Src:
            name = str(source)

        mgr.store_uploaded_file(job, str(target), _Src())  # type: ignore[arg-type]
        # Append semantics: existing bytes preserved, new bytes follow.
        # ``shutil.copyfileobj`` doesn't unlink the source — that's the
        # contract — so we don't assert source absence here.
        assert target.read_bytes() == b"first second"

    def test_reauthorises_writability(self, tmp_path):
        """The manager re-runs ``assert_writable`` itself; an unauthorised
        path raises even if the caller forgot to check."""
        job = _stub_job(id=5)  # no output datasets
        mgr = _make_manager(jobs={5: job})

        stray = tmp_path / "stray"
        stray.write_bytes(b"")

        class _Src:
            name = str(stray)

        with pytest.raises(exceptions.ItemAccessibilityException):
            mgr.store_uploaded_file(job, str(tmp_path / "anywhere.dat"), _Src())  # type: ignore[arg-type]

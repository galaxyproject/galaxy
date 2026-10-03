import shlex
import subprocess
from typing import cast

from galaxy.jobs import MinimalJobWrapper
from galaxy.jobs.command_factory import build_command
from galaxy.jobs.runners import BaseJobRunner
from galaxy.util.bunch import Bunch
from .test_command_factory import MockJobWrapper


def _job_dir(tmp_path):
    job_dir = tmp_path / "job dir"
    (job_dir / "working").mkdir(parents=True)
    (job_dir / "outputs").mkdir()
    return job_dir


def _run_job_command(job_dir, work_dir_outputs):
    job_wrapper = MockJobWrapper(str(job_dir))
    job_wrapper.command_line = "true"
    runner = Bunch(get_work_dir_outputs=lambda job_wrapper, **kwds: work_dir_outputs)
    command = build_command(runner=cast(BaseJobRunner, runner), job_wrapper=cast(MinimalJobWrapper, job_wrapper))
    subprocess.run(["sh", "-c", command], cwd=job_dir, check=True)
    return command


def test_copy_command_quotes_paths(tmp_path):
    job_dir = _job_dir(tmp_path)
    source = job_dir / "working" / "out $(touch injected) 'q'.txt"
    source.write_text("produced\n")
    destination = tmp_path / "data set.dat"
    destination.touch()

    command = _run_job_command(job_dir, [(str(source), str(destination))])

    assert destination.read_text() == "produced\n"
    assert not (job_dir / "working" / "injected").exists()
    assert shlex.quote(str(source)) in command
    assert shlex.quote(str(destination)) in command


def test_copy_command_expands_globs(tmp_path):
    job_dir = _job_dir(tmp_path)
    (job_dir / "working" / "output_1.txt").write_text("globbed\n")
    destination = tmp_path / "dataset.dat"
    destination.touch()

    _run_job_command(job_dir, [(str(job_dir / "working" / "output*"), str(destination))])

    assert destination.read_text() == "globbed\n"


def test_copy_command_quotes_directory_paths(tmp_path):
    job_dir = _job_dir(tmp_path)
    source = job_dir / "working" / "index $(touch injected)"
    source.mkdir()
    (source / "part.txt").write_text("part\n")
    destination = tmp_path / "extra files" / "dataset_1_files"
    destination.mkdir(parents=True)

    _run_job_command(job_dir, [(str(source), str(destination))])

    assert (destination / "part.txt").read_text() == "part\n"
    assert not (job_dir / "working" / "injected").exists()

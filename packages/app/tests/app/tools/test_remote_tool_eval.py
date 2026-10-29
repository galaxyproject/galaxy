import json

import pytest

from galaxy.tools import remote_tool_eval


@pytest.fixture
def job_directory(tmp_path, monkeypatch):
    (tmp_path / "working").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def error_file(job_directory):
    return job_directory / "metadata" / "outputs_populated" / "remote_tool_eval_error.json"


def test_failure_writes_error_with_cause(job_directory, monkeypatch):
    def evaluate_tool(*args):
        try:
            raise KeyError("out_file2")
        except KeyError as e:
            raise RuntimeError("Error occurred while building command line") from e

    monkeypatch.setattr(remote_tool_eval, "evaluate_tool", evaluate_tool)

    with pytest.raises(RuntimeError):
        remote_tool_eval.main()

    error = json.loads(error_file(job_directory).read_text())
    assert error["message"] == "Error occurred while building command line <- KeyError: 'out_file2'"
    assert "KeyError" in error["traceback"]
    assert (job_directory / "metadata" / "outputs_populated" / "traceback.txt").exists()


def test_success_removes_stale_error(job_directory, monkeypatch):
    error_file(job_directory).parent.mkdir(parents=True)
    error_file(job_directory).write_text("{}")
    monkeypatch.setattr(remote_tool_eval, "evaluate_tool", lambda *args: None)

    remote_tool_eval.main()

    assert not error_file(job_directory).exists()

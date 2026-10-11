import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / ".ci/check_ruff_exemptions.py"
spec = importlib.util.spec_from_file_location("check_ruff_exemptions", SCRIPT)
assert spec and spec.loader
pruner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pruner)


@pytest.fixture
def config(tmp_path):
    path = tmp_path / "ruff.toml"
    path.write_text(
        '[lint]\nselect = ["ANN"]\n[lint.per-file-ignores]\n'
        '"test/**" = ["ANN"]\n'
        f"{pruner.START}\n"
        '"legacy.py" = ["ANN001", "ANN201"]\n'
        '"deleted.py" = ["ANN201"]\n'
        f"{pruner.END}\n"
    )
    return path


def mock_ruff(monkeypatch, config, diagnostics, returncode=1):
    def run(command, **kwargs):
        temporary = Path(command[command.index("--config") + 1])
        # Policy exemptions survive, but the complete generated baseline is
        # removed, so a file/rule is retained only if Ruff still reports it.
        source = temporary.read_text()
        assert '"test/**" = ["ANN"]' in source
        assert '"legacy.py"' not in source
        assert kwargs["cwd"] == config.parent
        output = [{"filename": str(config.parent / filename), "code": code} for filename, code in diagnostics]
        return subprocess.CompletedProcess(command, returncode, json.dumps(output), "Ruff failed")

    monkeypatch.setattr(pruner.subprocess, "run", run)


def test_prunes_individual_rules_and_deleted_files(monkeypatch, config):
    mock_ruff(monkeypatch, config, [("legacy.py", "ANN001")])
    summary = config.parent / "summary.md"
    assert pruner.prune(config, "ruff", fix=True, summary=summary) == 0
    source = config.read_text()
    assert '"legacy.py" = ["ANN001"]' in source
    assert '"deleted.py"' not in source
    assert '"test/**" = ["ANN"]' in source
    assert "2 stale" in summary.read_text()
    # Repeating the operation leaves the configuration unchanged.
    assert pruner.prune(config, "ruff", fix=True) == 0
    assert config.read_text() == source


def test_report_only_does_not_modify_config(monkeypatch, config):
    mock_ruff(monkeypatch, config, [])
    original = config.read_text()
    assert pruner.prune(config, "ruff") == 1
    assert config.read_text() == original


def test_new_violations_prevent_writes(monkeypatch, config):
    mock_ruff(monkeypatch, config, [("new.py", "ANN201")])
    original = config.read_text()
    assert pruner.prune(config, "ruff", fix=True) == 1
    assert config.read_text() == original


@pytest.mark.parametrize("returncode", [2, 0])
def test_invalid_ruff_output_does_not_modify_config(monkeypatch, config, returncode):
    original = config.read_text()

    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode, "invalid JSON", "Ruff failed")

    monkeypatch.setattr(pruner.subprocess, "run", run)
    with pytest.raises((RuntimeError, json.JSONDecodeError)):
        pruner.prune(config, "ruff", fix=True)
    assert config.read_text() == original

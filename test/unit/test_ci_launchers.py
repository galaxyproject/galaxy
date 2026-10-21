"""Check CI launcher configuration and failure propagation without external services."""

import importlib.util
import subprocess
from contextlib import nullcontext
from pathlib import Path
from xml.etree import ElementTree

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_converter_selection_and_container_execution(monkeypatch, tmp_path):
    launcher = load_script("test_converters")
    converters = [tmp_path / "converter with spaces.xml", tmp_path / "other.xml"]
    tool_list = tmp_path / "tools.txt"
    tool_list.write_text("\n".join(map(str, converters)))
    monkeypatch.setattr(launcher.sys, "argv", ["test_converters.py", str(tool_list)])
    calls = []

    def run(args, *, cwd, env, check):
        calls.append(args)
        upload_conf, converter_conf = env["GALAXY_TEST_TOOL_CONF"].split(",")
        assert Path(upload_conf).name == "upload_tool_conf.xml"
        toolbox = ElementTree.parse(converter_conf)
        assert [tool.attrib["file"] for tool in toolbox.findall("tool")] == list(map(str, converters))
        job_config = yaml.safe_load(Path(env["GALAXY_TEST_JOB_CONFIG_FILE"]).read_text())
        destination = job_config["execution"]["environments"]["local"]
        assert destination["docker_enabled"] is True
        assert destination["container_resolvers"] == [{"type": "mulled"}]
        assert "--framework-tools" not in args  # That flag replaces the selected toolbox.
        assert "test/functional/test_toolbox_pytest.py" in args
        assert cwd == ROOT
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(launcher.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        launcher.main()
    assert len(calls) == 1


@pytest.mark.parametrize("fail_at", [None, "startup", "tests"])
def test_bioblend_stops_server_and_propagates_failure(monkeypatch, tmp_path, fail_at):
    launcher = load_script("test_bioblend")
    monkeypatch.setattr(launcher.sys, "argv", ["test_bioblend.py", str(tmp_path), "py314"])
    monkeypatch.setenv("DATABASE_CONNECTION", "postgresql+psycopg://localhost/galaxy")
    monkeypatch.setattr(launcher.urllib.request, "urlopen", lambda *args, **kwds: nullcontext())
    calls = []

    def run(args, *, cwd, env, check):
        calls.append(args)
        config = yaml.safe_load(Path(env["GALAXY_CONFIG_FILE"]).read_text())
        assert config["galaxy"]["master_api_key"] == env["BIOBLEND_GALAXY_MASTER_API_KEY"]
        assert config["galaxy"]["database_connection"] == "postgresql+psycopg://localhost/galaxy"
        if args[0] == "tox":
            assert cwd == tmp_path
            assert args == ["tox", "-e", "py314"]
        if (fail_at == "startup" and args == ["./run.sh", "--daemon"]) or (fail_at == "tests" and args[0] == "tox"):
            raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(launcher.subprocess, "run", run)
    if fail_at:
        with pytest.raises(subprocess.CalledProcessError):
            launcher.main()
    else:
        launcher.main()
    assert calls[-1] == ["./run.sh", "--daemon", "stop"]
    assert any(args[0] == "tox" for args in calls) == (fail_at != "startup")

"""Interactive runtime publication remains recoverable across server downtime."""

import json
import subprocess
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from galaxy.job_execution import container_monitor
from galaxy.util import requests


def configuration(tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/container_config.json").write_text(
        json.dumps(
            {
                "container_type": "docker",
                "container_name": "owned-container",
                "callback_url": "https://galaxy.invalid/callback",
                "connection_configuration": {},
            }
        )
    )


def test_callback_recovers_after_more_than_ten_retries_and_retains_atomic_runtime(tmp_path, monkeypatch):
    configuration(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(container_monitor, "parse_ports", lambda *_: "8888/tcp -> 127.0.0.1:12345")
    monkeypatch.setattr(container_monitor, "container_running", lambda *_: True)
    monkeypatch.setattr(container_monitor, "get_ip", lambda: "127.0.0.1")
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    calls: list[str] = []

    def post(*args, **kwargs):
        # The durable runtime exists before callback publication, so a
        # restarted Galaxy handler can also recover it independently.
        runtime = json.loads((tmp_path / "container_runtime.json").read_text())
        assert runtime["8888"]["port"] == 12345
        calls.append(args[0])
        if len(calls) <= 12:
            raise ConnectionError("Galaxy handler is down")
        return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(requests, "post", post)
    container_monitor.main()
    assert len(calls) == 13 and len(sleeps) == 12
    assert all(0 < interval <= 10 for interval in sleeps)
    assert not (tmp_path / "container_monitor_exception.txt").exists()
    assert not list(tmp_path.glob(".container-runtime-*"))


def test_revoked_or_exited_container_ends_callback_retry_with_diagnostics(tmp_path, monkeypatch):
    configuration(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(container_monitor, "parse_ports", lambda *_: "8888/tcp -> 127.0.0.1:12345")
    monkeypatch.setattr(container_monitor, "container_running", lambda *_: False)
    monkeypatch.setattr(container_monitor, "get_ip", lambda: "127.0.0.1")
    monkeypatch.setattr(time, "sleep", Mock(side_effect=AssertionError("Container is already gone")))
    monkeypatch.setattr(requests, "post", Mock(side_effect=ConnectionError("Galaxy is down")))
    container_monitor.main()
    assert (tmp_path / "container_runtime.json").exists()
    assert "Galaxy is down" in (tmp_path / "container_monitor_exception.txt").read_text()


def test_docker_port_probe_is_one_bounded_call_without_shell(tmp_path, monkeypatch):
    run = Mock(return_value=SimpleNamespace(returncode=1, stdout="", stderr="No such container"))
    monkeypatch.setattr(subprocess, "run", run)
    assert container_monitor.parse_ports("owned-container", {"docker_cmd": "docker", "host": "tcp://host:2375"}) is None
    assert run.call_args.args[0] == ["docker", "-H", "tcp://host:2375", "port", "owned-container"]
    assert run.call_args.kwargs["timeout"] == 30
    assert "shell" not in run.call_args.kwargs


def test_failed_command_without_container_stops_the_monitor(tmp_path, monkeypatch):
    configuration(tmp_path)
    path = tmp_path / "configs/container_config.json"
    data = json.loads(path.read_text())
    data["job_exit_code_file"] = "galaxy_42.ec"
    path.write_text(json.dumps(data))
    (tmp_path / "galaxy_42.ec").write_text("1")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(container_monitor, "parse_ports", lambda *_: None)
    monkeypatch.setattr(container_monitor, "container_running", lambda *_: False)
    monkeypatch.setattr(time, "sleep", Mock(side_effect=AssertionError("Command has finished")))
    container_monitor.main()
    assert "Failed to recover ports" in (tmp_path / "container_monitor_exception.txt").read_text()


@pytest.mark.parametrize("status,expected", [("true", True), ("false", False)])
def test_running_probe_uses_structured_docker_inspection(monkeypatch, status, expected):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout='[{"State":{"Running":' + status + "}}]",
            stderr="",
        ),
    )
    assert container_monitor.container_running("owned-container", {}) is expected

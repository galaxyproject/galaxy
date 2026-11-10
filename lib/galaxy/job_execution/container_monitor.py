import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
from functools import partial

from galaxy.tool_util.deps import docker_util
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
)
from galaxy.util.sockets import get_ip

GetIpCallable = Callable[[], str]


def parse_ports(container_name, connection_configuration):
    command = docker_util.command_list("port", [container_name], **connection_configuration)
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return result.stdout if result.returncode == 0 and result.stdout.strip() else None


def container_running(container_name, connection_configuration):
    """Return None for unavailable Docker, rather than treating it as exit."""
    command = docker_util.command_list("inspect", [container_name], **connection_configuration)
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode:
        if "no such" in result.stderr.lower():
            return False
        return None
    rows = json.loads(result.stdout)
    return bool(rows and rows[0].get("State", {}).get("Running"))


def write_runtime(ports):
    """Publish a complete runtime snapshot for recovery without a callback."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", prefix=".container-runtime-", dir=".", delete=False) as stream:
            temporary = stream.name
            json.dump(ports, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, "container_runtime.json")
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def get_ip_command(cmd) -> str:
    return subprocess.check_output(shlex.split(cmd), text=True).strip()


def main():
    if not os.path.exists("configs"):
        # on Pulsar and in tool working directory instead of job directory
        os.chdir("..")

    with open("configs/container_config.json") as f:
        container_config = json.load(f)

    container_type = container_config["container_type"]
    container_name = container_config["container_name"]
    callback_url = container_config.get("callback_url")
    get_ip_method = container_config.get("get_ip_method")
    connection_configuration = container_config["connection_configuration"]
    if container_type != "docker":
        raise Exception(f"Monitoring container type [{container_type}], not yet implemented.")

    _get_ip: GetIpCallable
    if get_ip_method is not None:
        method, arg = (e.strip() for e in get_ip_method.split(":", 1))
        if method == "command":
            _get_ip = partial(get_ip_command, arg)
        else:
            raise Exception(f"get_ip method [{get_ip_method}], not yet implemented.")
    else:
        _get_ip = get_ip

    exc_traceback = ""
    attempt = 0
    ports_found = False
    started = time.monotonic()
    exit_code_path = container_config.get("job_exit_code_file")
    startup_timeout = container_config.get("startup_timeout", None if exit_code_path else 300)
    if startup_timeout is not None:
        startup_timeout = float(startup_timeout)
    while True:
        try:
            ports_raw = parse_ports(container_name, connection_configuration)
            if ports_raw is not None:
                host_ip = _get_ip()
                ports = docker_util.parse_port_text(ports_raw)
                if host_ip is not None:
                    for key in ports:
                        if ports[key]["host"] == "0.0.0.0":
                            ports[key]["host"] = host_ip
                # Recovery can consume this even when callbacks are disabled or
                # Galaxy is down longer than the former ten-attempt window.
                write_runtime(ports)
                ports_found = True
                if callback_url:
                    r = requests.post(callback_url, json={"container_runtime": ports}, timeout=DEFAULT_SOCKET_TIMEOUT)
                    r.raise_for_status()
                exc_traceback = ""
                break
            else:
                raise Exception("Failed to recover ports...")
        except Exception:
            exc_info = sys.exc_info()
            exc_traceback = "".join(traceback.format_exception(*exc_info))
        try:
            running = container_running(container_name, connection_configuration)
        except Exception:
            running = None
        if exit_code_path and os.path.exists(exit_code_path):
            break
        expired = startup_timeout is not None and time.monotonic() - started >= startup_timeout
        if running is False and (ports_found or expired):
            break
        if not ports_found and expired:
            break
        attempt += 1
        time.sleep(min(10, attempt * 2))
    if exc_traceback:
        with open("container_monitor_exception.txt", "w") as stream:
            stream.write(exc_traceback)


if __name__ == "__main__":
    main()

import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import traceback
from functools import partial
from typing import Callable

import requests

from galaxy.tool_util.deps import docker_util
from galaxy.util import DEFAULT_SOCKET_TIMEOUT
from galaxy.util.sockets import get_ip

GetIpCallable = Callable[[], str]


def parse_ports(container_name, connection_configuration):
    while True:
        ports_command = docker_util.build_docker_simple_command(
            "port", container_name=container_name, **connection_configuration
        )
        with tempfile.TemporaryFile(prefix="docker_port_") as stdout_file:
            exit_code = subprocess.call(ports_command, shell=True, stdout=stdout_file, preexec_fn=os.setpgrp)
            if exit_code == 0:
                stdout_file.seek(0)
                ports_raw = stdout_file.read().decode("utf-8")
                return ports_raw


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

    ports_raw = None
    exc_traceback = ""
    for i in range(10):
        try:
            ports_raw = parse_ports(container_name, connection_configuration)
            if ports_raw is not None:
                host_ip = _get_ip()
                ports = docker_util.parse_port_text(ports_raw)
                if host_ip is not None:
                    for key in ports:
                        if ports[key]["host"] == "0.0.0.0":
                            ports[key]["host"] = host_ip
                if callback_url:
                    requests.post(callback_url, json={"container_runtime": ports}, timeout=DEFAULT_SOCKET_TIMEOUT)
                else:
                    with open("container_runtime.json", "w") as f:
                        json.dump(ports, f)
                break
            else:
                raise Exception("Failed to recover ports...")
        except Exception:
            exc_info = sys.exc_info()
            exc_traceback = "".join(traceback.format_exception(*exc_info))
        time.sleep(i * 2)
    else:
        with open("container_monitor_exception.txt", "w") as f:
            f.write(exc_traceback)


if __name__ == "__main__":
    main()

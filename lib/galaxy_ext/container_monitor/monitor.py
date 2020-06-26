import json
import os
import subprocess
import sys
import tempfile
import time

# insert *this* galaxy before all others on sys.path
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))

import requests

from galaxy.tool_util.deps import docker_util
from galaxy.util.sockets import get_ip


def parse_ports(container_name, connection_configuration):
    while True:
        ports_command = docker_util.build_docker_simple_command("port", container_name=container_name, **connection_configuration)
        with tempfile.TemporaryFile(prefix="docker_port_") as stdout_file:
            exit_code = subprocess.call(ports_command,
                                        shell=True,
                                        stdout=stdout_file,
                                        preexec_fn=os.setpgrp)
            if exit_code == 0:
                stdout_file.seek(0)
                ports_raw = stdout_file.read().decode('utf-8')
                return ports_raw


def main():
    if not os.path.exists("configs"):
        # on Pulsar and in tool working directory instead of job directory
        os.chdir("..")

    with open("configs/container_config.json") as f:
        container_config = json.load(f)

    container_type = container_config["container_type"]
    container_name = container_config["container_name"]
    callback_url = container_config.get("callback_url")
    connection_configuration = container_config["connection_configuration"]
    if container_type != "docker":
        raise Exception("Monitoring container type [%s], not yet implemented." % container_type)

    ports_raw = None
    for i in range(10):
        try:
            ports_raw = parse_ports(container_name, connection_configuration)
            if ports_raw is not None:
                host_ip = get_ip()
                ports = docker_util.parse_port_text(ports_raw)
                if host_ip is not None:
                    for key in ports:
                        if ports[key]['host'] == '0.0.0.0':
                            ports[key]['host'] = host_ip
                if callback_url:
                    requests.post(callback_url, json={"container_runtime": ports})
                else:
                    with open("container_runtime.json", "w") as f:
                        json.dump(ports, f)
                break
            else:
                raise Exception("Failed to recover ports...")
        except Exception as e:
            with open("container_monitor_exception.txt", "a") as f:
                f.write(str(e) + "\n\n\n")
        time.sleep(i * 2)


if __name__ == "__main__":
    main()

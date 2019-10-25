import json
import os
import socket
import subprocess
import sys
import tempfile
import time

# insert *this* galaxy before all others on sys.path
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))

from galaxy.tool_util.deps import docker_util


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
                ports_raw = stdout_file.read()
                return ports_raw


def main():
    with open("container_config.json", "r") as f:
        container_config = json.load(f)

    container_type = container_config["container_type"]
    container_name = container_config["container_name"]
    connection_configuration = container_config["connection_configuration"]
    if container_type != "docker":
        raise Exception("Monitoring container type [%s], not yet implemented." % container_type)

    ports_raw = None
    for i in range(10):
        try:
            ports_raw = parse_ports(container_name, connection_configuration)
            if ports_raw is not None:
                host_ip = socket.gethostbyname(socket.gethostname())
                with open("container_runtime.json", "w") as f:
                    # Override the IPs
                    ports = docker_util.parse_port_text(ports_raw)
                    for key in ports:
                        ports[key]['host'] = host_ip
                    json.dump(ports, f)
                break
            else:
                raise Exception("Failed to recover ports...")
        except Exception as e:
            with open("container_monitor_exception.txt", "a") as f:
                f.write(str(e))
        time.sleep(i * 2)


if __name__ == "__main__":
    main()

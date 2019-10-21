import json
import os
import subprocess
import sys
import tempfile

# insert *this* galaxy before all others on sys.path
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))

from galaxy.tool_util.deps import docker_util


def main():
    with open("container_config.json", "r") as f:
        container_config = json.load(f)

    container_type = container_config["container_type"]
    container_name = container_config["container_name"]
    connection_configuration = container_config["connection_configuration"]
    if container_type != "docker":
        raise Exception("Monitoring container type [%s], not yet implemented." % container_type)

    ports_raw = None
    try:
        while True:
            ports_command = docker_util.build_docker_simple_command("port", container_name=container_name, **connection_configuration)
            with tempfile.TemporaryFile() as stdout_file:
                exit_code = subprocess.call(ports_command,
                                            shell=True,
                                            stdout=stdout_file,
                                            preexec_fn=os.setpgrp)
                if exit_code == 0:
                    stdout_file.seek(0)
                    ports_raw = stdout_file.read()
                    break

        if ports_raw is not None:
            with open("container_runtime.json", "w") as f:
                json.dump(docker_util.parse_port_text(ports_raw), f)
        else:
            raise Exception("Failed to recover ports...")
    except Exception as e:
        with open("exception.txt", "w") as f:
            f.write(str(e))


if __name__ == "__main__":
    main()

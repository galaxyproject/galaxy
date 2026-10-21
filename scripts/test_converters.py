"""Run converter tool tests with Galaxy's own test driver."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree


def main():
    root = Path(__file__).resolve().parents[1]
    converters = [Path(line).resolve() for line in Path(sys.argv[1]).read_text().splitlines() if line.strip()]
    if not converters:
        raise ValueError("No converters selected")
    with tempfile.TemporaryDirectory(prefix="galaxy-converters-") as directory:
        config_dir = Path(directory)
        toolbox = ElementTree.Element("toolbox", tool_path=str(root))
        for converter in converters:
            ElementTree.SubElement(toolbox, "tool", file=str(converter))
        tool_conf = config_dir / "tool_conf.xml"
        ElementTree.ElementTree(toolbox).write(tool_conf)
        job_conf = config_dir / "job_conf.yml"
        job_conf.write_text(
            "runners:\n"
            "  local:\n"
            "    load: galaxy.jobs.runners.local:LocalJobRunner\n"
            "    workers: 4\n"
            "execution:\n"
            "  default: local\n"
            "  environments:\n"
            "    local:\n"
            "      runner: local\n"
            "      docker_enabled: true\n"
            "      docker_volumes: '$defaults'\n"
            "      container_resolvers:\n"
            "        - type: mulled\n"
        )
        env = dict(
            os.environ,
            GALAXY_TEST_TOOL_CONF=f"{root / 'test/functional/tools/upload_tool_conf.xml'},{tool_conf}",
            GALAXY_TEST_JOB_CONFIG_FILE=str(job_conf),
            GALAXY_TEST_FILE_DIR=str(root / "test-data"),
            GALAXY_TEST_TOOL_PATH=str(root),
            GALAXY_TEST_CONDA_AUTO_INIT="false",
            GALAXY_TEST_CONDA_AUTO_INSTALL="false",
        )
        subprocess.run(
            [
                str(root / "run_tests.sh"),
                "--report_file",
                "run_converter_tests.html",
                "test/functional/test_toolbox_pytest.py",
                "--",
                "-m",
                "tool",
                "-n",
                "4",
            ],
            cwd=root,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()

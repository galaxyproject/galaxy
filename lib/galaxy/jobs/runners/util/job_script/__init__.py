import logging
import os
import subprocess
import time
from dataclasses import dataclass
from string import Template
from typing import (
    Any,
    Dict,
    Optional,
)

from typing_extensions import Protocol

from galaxy.util import (
    RWXR_XR_X,
    unicodify,
)
from galaxy.util.resources import resource_string

log = logging.getLogger(__name__)
DEFAULT_SHELL = "/bin/bash"

DEFAULT_JOB_FILE_TEMPLATE = Template(resource_string(__name__, "DEFAULT_JOB_FILE_TEMPLATE.sh"))

SLOTS_STATEMENT_CLUSTER_DEFAULT = resource_string(__name__, "CLUSTER_SLOTS_STATEMENT.sh")

MEMORY_STATEMENT_DEFAULT_TEMPLATE = Template(resource_string(__name__, "MEMORY_STATEMENT_TEMPLATE.sh"))

SLOTS_STATEMENT_SINGLE = """
GALAXY_SLOTS="1"
"""

INTEGRITY_INJECTION = """
# The following block can be used by the job system
# to ensure this script is runnable before actually attempting
# to run it.
if [ -n "$ABC_TEST_JOB_SCRIPT_INTEGRITY_XYZ" ]; then
    exit 42
fi
"""

INTEGRITY_SYNC_COMMAND = "/bin/sync"
DEFAULT_INTEGRITY_CHECK = True
DEFAULT_INTEGRITY_COUNT = 35
DEFAULT_INTEGRITY_SLEEP = 0.25
REQUIRED_TEMPLATE_PARAMS = ["working_directory", "command"]
OPTIONAL_TEMPLATE_PARAMS: Dict[str, Any] = {
    "galaxy_lib": None,
    "galaxy_virtual_env": None,
    "headers": "",
    "env_setup_commands": [],
    "slots_statement": SLOTS_STATEMENT_CLUSTER_DEFAULT,
    "instrument_pre_commands": "",
    "instrument_post_commands": "",
    "integrity_injection": INTEGRITY_INJECTION,
    "shell": DEFAULT_SHELL,
    "preserve_python_environment": True,
    "tmp_dir_creation_statement": '""',
}


def job_script(template=DEFAULT_JOB_FILE_TEMPLATE, **kwds):
    """

    >>> has_exception = False
    >>> try: job_script()
    ... except Exception as e: has_exception = True
    >>> has_exception
    True
    >>> script = job_script(working_directory='wd', command='uptime', exit_code_path='ec')
    >>> '\\nuptime\\n' in script
    True
    >>> 'GALAXY_LIB="None"' in script
    True
    >>> script.startswith('#!/bin/sh\\n#PBS -test\\n')
    False
    >>> script = job_script(working_directory='wd', command='uptime', exit_code_path='ec', headers='#PBS -test')
    >>> script.startswith('#!/bin/bash\\n\\n#PBS -test\\n')
    True
    >>> script = job_script(working_directory='wd', command='uptime', exit_code_path='ec', slots_statement='GALAXY_SLOTS="$SLURM_JOB_NUM_NODES"')
    >>> script.find('GALAXY_SLOTS="$SLURM_JOB_NUM_NODES"\\n') > 0
    True
    >>> script = job_script(working_directory='wd', command='uptime', exit_code_path='ec', memory_statement='GALAXY_MEMORY_MB="32768"')
    >>> script.find('GALAXY_MEMORY_MB="32768"\\n') > 0
    True
    """
    if any(param not in kwds for param in REQUIRED_TEMPLATE_PARAMS):
        raise Exception("Failed to create job_script, a required parameter is missing.")
    job_instrumenter = kwds.get("job_instrumenter", None)
    metadata_directory = kwds.get("metadata_directory", kwds["working_directory"])
    if job_instrumenter:
        del kwds["job_instrumenter"]
        kwds["instrument_pre_commands"] = job_instrumenter.pre_execute_commands(metadata_directory) or ""
        kwds["instrument_post_commands"] = job_instrumenter.post_execute_commands(metadata_directory) or ""
    if "memory_statement" not in kwds:
        kwds["memory_statement"] = MEMORY_STATEMENT_DEFAULT_TEMPLATE.safe_substitute(
            metadata_directory=metadata_directory
        )

    # Setup home directory var
    kwds["home_directory"] = kwds.get("home_directory", os.path.join(kwds["working_directory"], "home"))

    template_params = OPTIONAL_TEMPLATE_PARAMS.copy()
    template_params.update(**kwds)
    env_setup_commands_str = "\n".join(template_params["env_setup_commands"])
    template_params["env_setup_commands"] = env_setup_commands_str
    for key, value in template_params.items():
        template_params[key] = unicodify(value)
    if not isinstance(template, Template):
        template = Template(template)
    return template.safe_substitute(template_params)


class DescribesScriptIntegrityChecks(Protocol):
    check_job_script_integrity: bool
    check_job_script_integrity_count: Optional[int]
    check_job_script_integrity_sleep: Optional[float]


@dataclass
class ScriptIntegrityChecks:
    """Minimal class implementing the DescribesScriptIntegrityChecks protocol"""

    check_job_script_integrity: bool
    check_job_script_integrity_count: Optional[int] = None
    check_job_script_integrity_sleep: Optional[float] = None


def write_script(path: str, contents, job_io: DescribesScriptIntegrityChecks, mode: int = RWXR_XR_X) -> None:
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)

    with open(path, "w", encoding="utf-8") as f:
        f.write(unicodify(contents))
    os.chmod(path, mode)
    if job_io.check_job_script_integrity:
        assert job_io.check_job_script_integrity_count is not None
        assert job_io.check_job_script_integrity_sleep is not None
        _handle_script_integrity(path, job_io.check_job_script_integrity_count, job_io.check_job_script_integrity_sleep)


def _handle_script_integrity(
    path: str, check_job_script_integrity_count: int, check_job_script_integrity_sleep: float
) -> None:
    script_integrity_verified = False
    for _ in range(check_job_script_integrity_count):
        try:
            returncode = subprocess.call([path], env={"ABC_TEST_JOB_SCRIPT_INTEGRITY_XYZ": "1"})
            if returncode == 42:
                script_integrity_verified = True
                break

            log.debug("Script integrity error for file '%s': returncode was %d", path, returncode)

            # Else we will sync and wait to see if the script becomes
            # executable.
            try:
                # sync file system to avoid "Text file busy" problems.
                # These have occurred both in Docker containers and on EC2 clusters
                # under high load.
                subprocess.check_call(INTEGRITY_SYNC_COMMAND)
            except Exception as e:
                log.debug("Error syncing the filesystem: %s", unicodify(e))

        except Exception as exc:
            log.debug("Script not available yet: %s", unicodify(exc))

        time.sleep(check_job_script_integrity_sleep)

    if not script_integrity_verified:
        raise Exception(f"Failed to write job script '{path}', could not verify job script integrity.")


__all__ = (
    "job_script",
    "write_script",
    "INTEGRITY_INJECTION",
)

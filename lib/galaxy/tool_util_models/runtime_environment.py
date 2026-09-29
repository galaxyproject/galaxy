"""Names of job environment variables consumed by trusted installed tools."""

import re

from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
)

ENVIRONMENT_VARIABLE_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
RESERVED_NAMES = frozenset(
    "PATH HOME USER LOGNAME SHELL PWD OLDPWD HOSTNAME TMPDIR TMP TEMP PYTHONPATH PYTHONHOME BASH_ENV ENV IFS PS4".split()
)
RESERVED_PREFIXES = ("LD_", "GALAXY_", "_GALAXY_", "SINGULARITY_", "SINGULARITYENV_", "APPTAINER_", "APPTAINERENV_")


def validate_environment_variable_name(name: str) -> str:
    if not re.fullmatch(ENVIRONMENT_VARIABLE_NAME, name):
        raise ValueError(f"Invalid environment variable name: {name}")
    return name


class RuntimeEnvironmentVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    required: bool = False
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        validate_environment_variable_name(name)
        if name in RESERVED_NAMES or name.startswith(RESERVED_PREFIXES):
            raise ValueError(f"Reserved runtime environment variable name: {name}")
        return name

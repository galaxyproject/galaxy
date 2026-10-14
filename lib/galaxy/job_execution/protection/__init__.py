"""Compute-side handling of jobs running on protected (encrypted) datasets.

Galaxy authorizes a protected job when preparing it and writes a
:class:`ProtectionPlan` into the job's configs directory. On the compute host,
outside of any tool container, the plan is used to decrypt the inputs into the
job's ``_protected`` directory before the tool runs, and to remove that plaintext
again afterwards.

Crypt4GH is the only protection scheme: the plan, :mod:`.crypt4gh` and the grants of
:mod:`galaxy.managers.dataset_protection` are Crypt4GH's. The scheme recorded on jobs
and grants leaves room for another one, which would bring its own plan, runtime and
grant validation; the interface between them is best extracted then.

This module must stay importable with the ``galaxy-job-execution`` package only,
so it can run on Pulsar and other remote compute hosts.
"""

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from typing import (
    Any,
    Final,
)

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.util import asbool

PROTECTED_DIRECTORY_NAME = "_protected"
PLAN_FILENAME = "protection_plan.json"
STATE_FILENAME = "state.json"
CRYPT4GH_SCHEME: Final = "crypt4gh"


class RecryptorSettings(BaseModel):
    url: str
    timeout: float = 30
    retries: int = 3
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None
    # Include the underlying errors, which may show the service's address, in messages users see.
    verbose_errors: bool = False

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> "RecryptorSettings | None":
        """Read the compute service of a job destination, ``None`` if it has none."""
        url = params.get("crypt4gh_recryptor_url")
        if not url:
            return None
        return cls(
            url=url,
            timeout=float(params.get("crypt4gh_recryptor_timeout", 30)),
            ca_cert=params.get("crypt4gh_recryptor_ca_cert"),
            client_cert=params.get("crypt4gh_recryptor_client_cert"),
            client_key=params.get("crypt4gh_recryptor_client_key"),
            verbose_errors=asbool(params.get("crypt4gh_recryptor_verbose_errors", False)),
        )


class ProtectedFile(BaseModel):
    source_path: str = Field(description="Path of the encrypted file on the compute host.")
    staged_path: str = Field(description="Path the decrypted file is written to.")
    compute_header: str = Field(description="Base64 header of the file, encrypted to the compute keypair.")
    key_ref: str | None = Field(
        default=None, description="Compute keypair of this header, when not the one of its input."
    )


class ProtectedInput(BaseModel):
    dataset_id: int
    key_ref: str = Field(description="Compute keypair the headers of this input are encrypted to.")
    primary: ProtectedFile
    staged_extra_files_path: str
    source_extra_files_path: str | None = None
    extra_files: dict[str, ProtectedFile] = Field(default_factory=dict)


class ProtectionPlan(BaseModel):
    job_directory: str
    output_key_ref: str = Field(description="Compute keypair outputs get encrypted to.")
    recryptor: RecryptorSettings
    inputs: list[ProtectedInput]
    encrypted_inputs: list[str] = Field(
        default_factory=list,
        description="Paths of protected inputs passed to the tool encrypted, outputs copying them are kept as they are.",
    )

    @property
    def protected_directory(self) -> str:
        return protected_directory(self.job_directory)

    @property
    def inputs_directory(self) -> str:
        return protected_inputs_directory(self.job_directory)

    @cached_property
    def inputs_by_dataset_id(self) -> dict[int, ProtectedInput]:
        # Paths of every input are rewritten while building the command line.
        return {protected_input.dataset_id: protected_input for protected_input in self.inputs}

    def staged_input(self, dataset_id: int) -> ProtectedInput | None:
        return self.inputs_by_dataset_id.get(dataset_id)

    def write(self, path: str) -> None:
        # The plan carries bearer capabilities (headers sealed to the compute key).
        write_private_file(path, self.model_dump_json())

    @classmethod
    def read(cls, path: str) -> "ProtectionPlan":
        with open(path) as f:
            return cls.model_validate(json.load(f))


def write_private_file(path: str, content: str) -> None:
    """Write a file only its owner can read, for files holding bearer capabilities."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        # The mode only applies to new files.
        os.fchmod(f.fileno(), 0o600)
        f.write(content)


def protected_directory(job_directory: str) -> str:
    # Next to working/ rather than inside it, so output discovery never sees decrypted inputs.
    return os.path.join(job_directory, PROTECTED_DIRECTORY_NAME)


def protected_inputs_directory(job_directory: str) -> str:
    """Where the inputs of a protected job are decrypted."""
    return os.path.join(protected_directory(job_directory), "inputs")


class ProtectionError(Exception):
    """A user-facing error preparing or finishing a protected job. Never contains key material."""


@dataclass
class ProtectionDestination:
    """What the job destination provides, as far as running protected jobs is concerned."""

    metadata_strategy: str
    has_tasks: bool
    is_pulsar: bool
    remote_metadata: bool
    rewrite_parameters: bool
    recryptor: RecryptorSettings | None
    walltime: timedelta | None = None
    live_tool_output_reporting: bool = False

    @classmethod
    def from_params(
        cls,
        params: Mapping[str, Any],
        *,
        metadata_strategy: str,
        has_tasks: bool,
        is_pulsar: bool,
        walltime: timedelta | None,
    ) -> "ProtectionDestination":
        """Read the parameters of a job destination, along with what Galaxy decided for the job."""
        return cls(
            metadata_strategy=metadata_strategy,
            has_tasks=has_tasks,
            is_pulsar=is_pulsar,
            remote_metadata=asbool(params.get("remote_metadata", False)),
            rewrite_parameters=asbool(params.get("rewrite_parameters", False)),
            recryptor=RecryptorSettings.from_params(params),
            walltime=walltime,
            live_tool_output_reporting=asbool(params.get("live_tool_output_reporting", False)),
        )

    def check(self, outputs_in_job_directory: bool) -> None:
        problems = []
        if self.metadata_strategy != "extended":
            problems.append("metadata_strategy must be 'extended'")
        if not outputs_in_job_directory:
            # Otherwise tools write decrypted data directly to the object store.
            problems.append(
                "tools must write outputs into the job directory (enable outputs_to_working_directory, "
                "or stage the outputs of Pulsar destinations)"
            )
        if self.has_tasks:
            problems.append("jobs can't be split into tasks")
        if self.is_pulsar and not self.remote_metadata:
            problems.append("Pulsar destinations must use remote_metadata")
        if self.is_pulsar and not self.rewrite_parameters:
            # Otherwise the protection plan would hold paths of the Galaxy server.
            problems.append("Pulsar destinations must use rewrite_parameters")
        if self.live_tool_output_reporting:
            # The API would serve the tool's live output, which may contain decrypted data.
            problems.append("live_tool_output_reporting must be disabled")
        if self.recryptor is None:
            problems.append("it has no Crypt4GH recryptor service (crypt4gh_recryptor_url) configured")
        if problems:
            raise ProtectionError(
                "This job uses encrypted datasets but its destination can't run it securely: "
                + "; ".join(problems)
                + ". Contact your Galaxy administrator."
            )


@dataclass
class ProtectedFileResult:
    """An output file that was encrypted in place for the job's user, or was encrypted already."""

    # SHA-256 of the header the file now starts with.
    header_sha256: str
    # Base64 header of the file encrypted to the compute keypair, i.e. the grant to compute on it again.
    # None for files that were encrypted already: users authorize them like uploads.
    compute_header: str | None

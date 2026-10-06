"""Compute-side handling of jobs running on protected (encrypted) datasets.

Galaxy authorizes a protected job when preparing it and writes a
:class:`ProtectionPlan` into the job's configs directory. On the compute host,
outside of any tool container, the plan is used to decrypt the inputs into the
job's ``_protected`` directory before the tool runs, and to remove that plaintext
again afterwards.

This module must stay importable with the ``galaxy-job-execution`` package only,
so it can run on Pulsar and other remote compute hosts.
"""

import json
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import (
    Literal,
    Protocol,
)

from pydantic import (
    BaseModel,
    Field,
)

PROTECTED_DIRECTORY_NAME = "_protected"
PLAN_FILENAME = "protection_plan.json"
STATE_FILENAME = "state.json"


class RecryptorSettings(BaseModel):
    url: str
    timeout: float = 30
    retries: int = 3
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None


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
    scheme: Literal["crypt4gh"]
    job_directory: str
    output_key_ref: str = Field(description="Compute keypair outputs get encrypted to.")
    recryptor: RecryptorSettings
    inputs: list[ProtectedInput]

    @property
    def protected_directory(self) -> str:
        return protected_directory(self.job_directory)

    def staged_input(self, dataset_id: int) -> ProtectedInput | None:
        for protected_input in self.inputs:
            if protected_input.dataset_id == dataset_id:
                return protected_input
        return None

    def write(self, path: str) -> None:
        # The plan carries bearer capabilities (headers sealed to the compute key).
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(self.model_dump_json())

    @classmethod
    def read(cls, path: str) -> "ProtectionPlan":
        with open(path) as f:
            return cls.model_validate(json.load(f))


def protected_directory(job_directory: str) -> str:
    # Next to working/ rather than inside it, so output discovery never sees decrypted inputs.
    return os.path.join(job_directory, PROTECTED_DIRECTORY_NAME)


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
        if self.recryptor is None:
            problems.append("no Crypt4GH recryptor service (crypt4gh_recryptor_url) is configured")
        if problems:
            raise ProtectionError(
                "This job uses encrypted datasets but its destination can't run it securely: "
                + "; ".join(problems)
                + ". Contact your Galaxy administrator."
            )


@dataclass
class ProtectedFileResult:
    """An output file that was encrypted in place for the job's user."""

    # SHA-256 of the header the file now starts with, encrypted to the user's key.
    header_sha256: str
    # Base64 header of the file encrypted to the compute keypair, i.e. the grant to compute on it again.
    compute_header: str


class ProtectedJobRuntime(Protocol):
    @property
    def key_ref(self) -> str: ...

    @property
    def key_expiration(self) -> str | None: ...

    def stage_inputs(self) -> None: ...

    def protect_file(self, path: str) -> ProtectedFileResult: ...

    def cleanup_inputs(self) -> None: ...

    def cleanup(self) -> None: ...


def load_runtime(plan: ProtectionPlan) -> ProtectedJobRuntime:
    if plan.scheme == "crypt4gh":
        from .crypt4gh import Crypt4GHJobRuntime

        return Crypt4GHJobRuntime(plan)
    raise ProtectionError(f"Unsupported protection scheme '{plan.scheme}'")

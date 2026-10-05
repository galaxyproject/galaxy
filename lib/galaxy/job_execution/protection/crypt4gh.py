"""Crypt4GH implementation of protected job execution.

Decrypting an input never needs a long-lived private key on the compute host:

1. A fresh X25519 *job key* is generated in memory.
2. The compute-side recryptor service (Service B of ``crypt4gh-recryptor-service``)
   re-encrypts the dataset header from the compute keypair to the job key.
3. The re-encrypted header is spliced in front of the unchanged encrypted body and
   the file is decrypted with the job key.

Only headers ever travel to the service, never the encrypted bodies or plaintext.
"""

import base64
import hashlib
import io
import json
import logging
import os
import shutil
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import (
    Any,
    BinaryIO,
)

import requests

from galaxy.util.crypt4gh import read_crypt4gh_header
from . import (
    ProtectedFile,
    ProtectedFileResult,
    ProtectionError,
    ProtectionPlan,
    RecryptorSettings,
    STATE_FILENAME,
)

log = logging.getLogger(__name__)

# The crypt4gh library logs private, shared and session keys at DEBUG level.
# Never let those reach job logs, whatever the logging configuration.
logging.getLogger("crypt4gh").setLevel(logging.WARNING)

MAX_CONCURRENT_REQUESTS = 8
RETRY_BACKOFF_SECONDS = 0.5

ERROR_MESSAGES = {
    404: "The key service does not know the compute key of this dataset, authorize the dataset again.",
    410: "The compute key of this dataset has expired, authorize the dataset again.",
    422: "The key service could not open the header of this dataset, authorize the dataset again.",
}


def format_public_key(public_key: bytes) -> str:
    encoded = base64.b64encode(public_key).decode()
    return f"-----BEGIN CRYPT4GH PUBLIC KEY-----\n{encoded}\n-----END CRYPT4GH PUBLIC KEY-----\n"


def parse_public_key(public_key: str) -> bytes:
    lines = [line.strip() for line in public_key.strip().splitlines() if line.strip()]
    if len(lines) < 3 or "CRYPT4GH PUBLIC KEY" not in lines[0]:
        raise ProtectionError("The key service returned an invalid compute public key.")
    return base64.b64decode("".join(lines[1:-1]))


class RecryptorClient:
    """Client for the compute-side recryptor service.

    Requests and responses carry headers, which are bearer capabilities: they are never logged.
    """

    def __init__(self, settings: RecryptorSettings):
        self.settings = settings

    def recrypt_header_to_job_key(self, header: str, key_ref: str, job_public_key: str) -> dict[str, Any]:
        return self._post(
            "recrypt_header_to_job_key",
            {
                "crypt4gh_header": header,
                "crypt4gh_compute_keypair_id": key_ref,
                "crypt4gh_job_public_key": job_public_key,
            },
        )

    def recrypt_header_to_user_key(self, header: str, key_ref: str) -> dict[str, Any]:
        return self._post(
            "recrypt_header_to_user_key",
            {"crypt4gh_header": header, "crypt4gh_compute_keypair_id": key_ref},
        )

    def _post(self, route: str, payload: dict[str, str]) -> dict[str, Any]:
        url = f"{self.settings.url.rstrip('/')}/{route}"
        verify: bool | str = self.settings.ca_cert or True
        cert: str | tuple[str, str] | None = self.settings.client_cert
        if self.settings.client_cert and self.settings.client_key:
            cert = (self.settings.client_cert, self.settings.client_key)
        attempts = self.settings.retries + 1
        for attempt in range(attempts):
            last_attempt = attempt == attempts - 1
            try:
                response = requests.post(url, json=payload, timeout=self.settings.timeout, verify=verify, cert=cert)
            except requests.RequestException as e:
                if last_attempt:
                    raise ProtectionError(f"Could not reach the key service ({type(e).__name__}).")
                log.warning("Key service request to %s failed (%s), retrying", route, type(e).__name__)
            else:
                if response.status_code == 200:
                    result: dict[str, Any] = response.json()
                    return result
                if response.status_code < 500 or last_attempt:
                    message = ERROR_MESSAGES.get(response.status_code, "The key service rejected the request")
                    raise ProtectionError(f"{message} (HTTP {response.status_code} from {route})")
                log.warning("Key service returned HTTP %s for %s, retrying", response.status_code, route)
            time.sleep(RETRY_BACKOFF_SECONDS * 2**attempt)
        raise AssertionError("unreachable")


class _HeaderThenBody(io.RawIOBase):
    """Read a replacement header followed by the body of an existing Crypt4GH file."""

    def __init__(self, header: bytes, body: BinaryIO):
        self._header = io.BytesIO(header)
        self._body = body

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:  # type: ignore[no-untyped-def]
        data = self._header.read(len(buffer)) or self._body.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)


@contextmanager
def _body_with_header(path: str, header: bytes) -> Iterator[BinaryIO]:
    with open(path, "rb") as encrypted:
        read_crypt4gh_header(encrypted)
        yield io.BufferedReader(_HeaderThenBody(header, encrypted))


class Crypt4GHJobRuntime:
    def __init__(self, plan: ProtectionPlan, client: RecryptorClient | None = None):
        self.plan = plan
        self.client = client or RecryptorClient(plan.recryptor)
        self._state: dict[str, Any] | None = None
        self._writer_secret_key: bytes | None = None

    @property
    def state(self) -> dict[str, Any]:
        """The compute key outputs get encrypted to, as found when staging the inputs."""
        if self._state is None:
            state_path = os.path.join(self.plan.protected_directory, STATE_FILENAME)
            if not os.path.exists(state_path):
                raise ProtectionError("The protected inputs of this job were not staged, outputs can't be protected.")
            with open(state_path) as f:
                self._state = json.load(f)
        return self._state

    @property
    def key_ref(self) -> str:
        key_ref: str = self.state["key_ref"]
        return key_ref

    @property
    def key_expiration(self) -> str | None:
        return self.state.get("compute_keypair_expiration_date")

    def protect_file(self, path: str) -> ProtectedFileResult:
        """Encrypt ``path`` in place for the job's user.

        The file is encrypted to the compute keypair, then the recryptor service re-encrypts
        that header to the user's key. The compute header is returned as the grant to use
        the file in further jobs.
        """
        from crypt4gh import lib as crypt4gh_lib

        if self._writer_secret_key is None:
            self._writer_secret_key = os.urandom(32)
        compute_public_key = parse_public_key(self.state["compute_public_key"])
        directory, name = os.path.split(path)
        body_path = os.path.join(directory, f".{name}.c4gh-body")
        protected_path = os.path.join(directory, f".{name}.c4gh")
        try:
            compute_header = io.BytesIO()
            with open(path, "rb") as plaintext, open(body_path, "wb") as body:
                crypt4gh_lib.encrypt(
                    [(0, self._writer_secret_key, compute_public_key)], plaintext, body, headerfile=compute_header
                )
            encoded_compute_header = base64.b64encode(compute_header.getvalue()).decode()
            response = self.client.recrypt_header_to_user_key(encoded_compute_header, self.key_ref)
            user_header = base64.b64decode(response["crypt4gh_header"])
            if read_crypt4gh_header(io.BytesIO(user_header)) != user_header:
                raise ProtectionError("The key service returned an invalid header.")
            with open(protected_path, "wb") as protected, open(body_path, "rb") as body:
                protected.write(user_header)
                shutil.copyfileobj(body, protected)
            # Replacing the file drops the plaintext.
            os.replace(protected_path, path)
        except ProtectionError:
            raise
        except Exception as e:
            raise ProtectionError(f"Failed to encrypt an output of this job ({type(e).__name__}).") from e
        finally:
            for temporary_path in (body_path, protected_path):
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
        return ProtectedFileResult(
            header_sha256=hashlib.sha256(user_header).hexdigest(),
            compute_header=encoded_compute_header,
        )

    @property
    def inputs_directory(self) -> str:
        return os.path.join(self.plan.protected_directory, "inputs")

    def stage_inputs(self) -> None:
        from crypt4gh import (
            lib as crypt4gh_lib,
            sodium,
        )

        os.umask(0o077)
        os.makedirs(self.inputs_directory, exist_ok=True)
        job_secret_key = os.urandom(32)
        job_public_key = format_public_key(sodium.derive_pk(job_secret_key))
        files = self._files_to_stage()
        try:
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
                responses = list(
                    executor.map(
                        lambda file_and_key: self.client.recrypt_header_to_job_key(
                            file_and_key[0].compute_header, file_and_key[1], job_public_key
                        ),
                        files,
                    )
                )
            output_response = self._check_responses(files, responses)
            for (protected_file, _), response in zip(files, responses):
                job_header = base64.b64decode(response["crypt4gh_header"])
                os.makedirs(os.path.dirname(protected_file.staged_path), exist_ok=True)
                with (
                    _body_with_header(protected_file.source_path, job_header) as stream,
                    open(protected_file.staged_path, "wb") as plaintext,
                ):
                    crypt4gh_lib.decrypt([(0, job_secret_key, None)], stream, plaintext)
            self._write_state(output_response)
        except ProtectionError:
            self.cleanup_inputs()
            raise
        except Exception as e:
            self.cleanup_inputs()
            # Errors from the crypt4gh library are generic, don't let them pass as-is.
            raise ProtectionError(f"Failed to decrypt a protected input ({type(e).__name__}).") from e

    def _files_to_stage(self) -> list[tuple[ProtectedFile, str]]:
        files: list[tuple[ProtectedFile, str]] = []
        for protected_input in self.plan.inputs:
            files.append((protected_input.primary, protected_input.key_ref))
            files.extend((extra_file, protected_input.key_ref) for extra_file in protected_input.extra_files.values())
            source_extra = protected_input.source_extra_files_path
            if source_extra and os.path.isdir(source_extra):
                for root, _, filenames in os.walk(source_extra):
                    for filename in filenames:
                        relpath = os.path.relpath(os.path.join(root, filename), source_extra)
                        if relpath not in protected_input.extra_files:
                            # Every file of a protected dataset must be protected, refuse to guess.
                            raise ProtectionError(
                                "A protected input has extra files that cannot be decrypted, authorize the dataset again."
                            )
        return files

    def _check_responses(
        self, files: list[tuple[ProtectedFile, str]], responses: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Check the service answered for the requested keypairs, return the response for the output keypair."""
        output_response = None
        for (_, key_ref), response in zip(files, responses):
            if response.get("crypt4gh_compute_keypair_id") != key_ref:
                raise ProtectionError("The key service answered with an unexpected compute key.")
            parse_public_key(response.get("crypt4gh_compute_public_key") or "")
            if key_ref == self.plan.output_key_ref:
                output_response = response
        if output_response is None:
            raise ProtectionError("No protected input uses the compute key selected for the outputs.")
        return output_response

    def _write_state(self, response: dict[str, Any]) -> None:
        state = {
            "key_ref": self.plan.output_key_ref,
            "compute_public_key": response["crypt4gh_compute_public_key"],
            "compute_keypair_expiration_date": response.get("crypt4gh_compute_keypair_expiration_date"),
        }
        with open(os.path.join(self.plan.protected_directory, STATE_FILENAME), "w") as f:
            json.dump(state, f)

    def cleanup_inputs(self) -> None:
        if os.path.exists(self.inputs_directory):
            shutil.rmtree(self.inputs_directory)

    def cleanup(self) -> None:
        if os.path.exists(self.plan.protected_directory):
            shutil.rmtree(self.plan.protected_directory)

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
import filecmp
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

from galaxy.util.crypt4gh import (
    check_crypt4gh,
    iter_relpaths,
    read_crypt4gh_header,
)
from galaxy.util.requests import Session
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
# Copies of decrypted inputs made for links to them, in the protected directory.
COPIES_FILENAME = "copied_inputs.json"
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


def describe_error(error: BaseException, verbose: bool) -> str:
    """The error's type, and its message only when the destination asks for verbose errors.

    Messages of underlying errors can show the key service's address, and job errors are shown to users.
    """
    return f"{type(error).__name__}: {error}" if verbose else type(error).__name__


class RecryptorClient:
    """Client for the compute-side recryptor service.

    Requests and responses carry headers, which are bearer capabilities: they are never logged.
    """

    def __init__(self, settings: RecryptorSettings):
        self.settings = settings
        # Reuses connections, every file of a job takes a request.
        self.session = Session()

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

    def _check_tls_files(self) -> None:
        # requests only reports these as a generic OSError.
        for setting, path in (
            ("crypt4gh_recryptor_ca_cert", self.settings.ca_cert),
            ("crypt4gh_recryptor_client_cert", self.settings.client_cert),
            ("crypt4gh_recryptor_client_key", self.settings.client_key),
        ):
            if path and not os.path.exists(path):
                location = f" ({path})" if self.settings.verbose_errors else ""
                raise ProtectionError(
                    f"The file configured as {setting} doesn't exist on the compute host{location}. "
                    "Contact your Galaxy administrator."
                )

    def _post(self, route: str, payload: dict[str, str]) -> dict[str, Any]:
        self._check_tls_files()
        url = f"{self.settings.url.rstrip('/')}/{route}"
        verify: bool | str = self.settings.ca_cert or True
        cert: str | tuple[str, str] | None = self.settings.client_cert
        if self.settings.client_cert and self.settings.client_key:
            cert = (self.settings.client_cert, self.settings.client_key)
        attempts = self.settings.retries + 1
        for attempt in range(attempts):
            last_attempt = attempt == attempts - 1
            try:
                response = self.session.post(url, json=payload, timeout=self.settings.timeout, verify=verify, cert=cert)
            except requests.RequestException as e:
                if last_attempt:
                    # Users can read job errors: don't chain the request error, it shows the service's address.
                    raise ProtectionError(
                        f"Could not reach the key service ({describe_error(e, self.settings.verbose_errors)})."
                    ) from None
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


def _remove_unless_encrypted(path: str) -> None:
    """Remove a copy of decrypted data, unless it was encrypted since, as an output."""
    if os.path.isdir(path):
        if not all(check_crypt4gh(os.path.join(path, relpath)) for relpath in iter_relpaths(path)):
            shutil.rmtree(path)
    elif os.path.exists(path) and not check_crypt4gh(path):
        os.remove(path)


def _encrypt_body(plaintext: io.BufferedReader, encrypted: BinaryIO, session_key: bytes) -> None:
    """Write the Crypt4GH segments of ``plaintext``, as ``crypt4gh.lib.encrypt()`` does."""
    from crypt4gh import (
        CIPHER_SEGMENT_SIZE,
        SEGMENT_SIZE,
        sodium,
    )

    segment = bytearray(SEGMENT_SIZE)
    cipher_segment = bytearray(CIPHER_SEGMENT_SIZE)
    while segment_length := plaintext.readinto(segment):
        cipher_length = sodium.chacha20poly1305_encrypt(cipher_segment, segment[:segment_length], session_key)
        encrypted.write(cipher_segment[:cipher_length])
        if segment_length < SEGMENT_SIZE:
            break


class Crypt4GHJobRuntime:
    def __init__(self, plan: ProtectionPlan, client: RecryptorClient | None = None):
        self.plan = plan
        self.client = client or RecryptorClient(plan.recryptor)
        self._state: dict[str, Any] | None = None
        # Created upfront, outputs may be protected concurrently.
        self._writer_secret_key = os.urandom(32)

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

        Copies of inputs passed to the tool encrypted are kept as they are: encrypting them
        again would take two decryptions to use them.
        """
        from crypt4gh import header as crypt4gh_header

        # Plaintext outputs can't be copies of encrypted inputs, don't compare them.
        if check_crypt4gh(path) and any(
            os.path.exists(source) and filecmp.cmp(path, source, shallow=False) for source in self.plan.encrypted_inputs
        ):
            with open(path, "rb") as f:
                existing_header = read_crypt4gh_header(f)
            return ProtectedFileResult(header_sha256=hashlib.sha256(existing_header).hexdigest(), compute_header=None)
        compute_public_key = parse_public_key(self.state["compute_public_key"])
        directory, name = os.path.split(path)
        protected_path = os.path.join(directory, f".{name}.c4gh")
        try:
            # As crypt4gh.lib.encrypt() does, but the header is recrypted for the user before encrypting
            # the body, so the body is written once, right behind it.
            session_key = os.urandom(32)
            compute_header = crypt4gh_header.serialize(
                crypt4gh_header.encrypt(
                    crypt4gh_header.make_packet_data_enc(0, session_key),
                    [(0, self._writer_secret_key, compute_public_key)],
                )
            )
            encoded_compute_header = base64.b64encode(compute_header).decode()
            response = self.client.recrypt_header_to_user_key(encoded_compute_header, self.key_ref)
            user_header = base64.b64decode(response["crypt4gh_header"])
            if read_crypt4gh_header(io.BytesIO(user_header)) != user_header:
                raise ProtectionError("The key service returned an invalid header.")
            with open(path, "rb") as plaintext, open(protected_path, "wb") as protected:
                protected.write(user_header)
                _encrypt_body(plaintext, protected, session_key)
            # Replacing the file drops the plaintext.
            os.replace(protected_path, path)
        except ProtectionError:
            raise
        except Exception as e:
            raise ProtectionError(
                f"Failed to encrypt an output of this job ({describe_error(e, self.plan.recryptor.verbose_errors)})."
            ) from e
        finally:
            if os.path.exists(protected_path):
                os.remove(protected_path)
        return ProtectedFileResult(
            header_sha256=hashlib.sha256(user_header).hexdigest(),
            compute_header=encoded_compute_header,
        )

    def stage_inputs(self) -> None:
        from crypt4gh import (
            lib as crypt4gh_lib,
            sodium,
        )

        os.umask(0o077)
        os.makedirs(self.plan.inputs_directory, exist_ok=True)
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
            raise ProtectionError(
                f"Failed to decrypt a protected input ({describe_error(e, self.plan.recryptor.verbose_errors)})."
            ) from e

    def _files_to_stage(self) -> list[tuple[ProtectedFile, str]]:
        files: list[tuple[ProtectedFile, str]] = []
        for protected_input in self.plan.inputs:
            files.append((protected_input.primary, protected_input.key_ref))
            files.extend(
                (extra_file, extra_file.key_ref or protected_input.key_ref)
                for extra_file in protected_input.extra_files.values()
            )
            source_extra = protected_input.source_extra_files_path
            if source_extra and os.path.isdir(source_extra):
                if any(relpath not in protected_input.extra_files for relpath in iter_relpaths(source_extra)):
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
        if os.path.exists(self.plan.inputs_directory):
            self._copy_linked_inputs()
            shutil.rmtree(self.plan.inputs_directory)

    def _copy_linked_inputs(self) -> None:
        """Replace links to decrypted inputs, e.g. outputs the tool linked to an input, by copies.

        Outputs are collected after the decrypted inputs are removed. The copies are recorded, so
        the ones that weren't encrypted as outputs are removed with the rest of the decrypted data.
        """
        inputs_directory = os.path.realpath(self.plan.inputs_directory)
        protected_directory = os.path.realpath(self.plan.protected_directory)
        copies: list[str] = []
        for root, dirnames, filenames in os.walk(self.plan.job_directory):
            if os.path.realpath(root) == protected_directory:
                dirnames.clear()
                continue
            for name in dirnames + filenames:
                path = os.path.join(root, name)
                if not os.path.islink(path):
                    continue
                target = os.path.realpath(path)
                if os.path.commonpath([target, inputs_directory]) != inputs_directory:
                    continue
                os.remove(path)
                if os.path.isdir(target):
                    shutil.copytree(target, path)
                else:
                    shutil.copy2(target, path)
                copies.append(path)
        if copies:
            with open(os.path.join(self.plan.protected_directory, COPIES_FILENAME), "w") as f:
                json.dump(copies, f)

    def cleanup(self) -> None:
        if not os.path.exists(self.plan.protected_directory):
            return
        copies_path = os.path.join(self.plan.protected_directory, COPIES_FILENAME)
        if os.path.exists(copies_path):
            with open(copies_path) as f:
                for path in json.load(f):
                    _remove_unless_encrypted(path)
        shutil.rmtree(self.plan.protected_directory)

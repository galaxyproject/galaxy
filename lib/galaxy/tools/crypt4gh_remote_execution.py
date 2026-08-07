"""Crypt4GH helpers for remote tool execution and output finalization."""

from __future__ import annotations

import asyncio
import base64
import errno
import importlib
import io
import ipaddress
import json
import os
import re
import shlex
import shutil
import ssl
from collections.abc import (
    Mapping,
    Sequence,
)
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from logging import getLogger
from pathlib import Path
from typing import (
    Any,
    BinaryIO,
    cast,
    Protocol,
    TYPE_CHECKING,
)
from urllib.parse import urlsplit

import aiohttp
import crypt4gh.header
import crypt4gh.lib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from dateutil.parser import isoparse

from galaxy.job_execution.compute_environment import (
    dataset_path_to_extra_path,
    SharedComputeEnvironment,
)
from galaxy.util.crypt4gh import (
    CRYPT4GH_CLEANUP_FAILED_MARKER,
    read_crypt4gh_header,
)

try:
    _optional_truststore: Any = importlib.import_module("truststore")
except Exception:
    _optional_truststore = None

if TYPE_CHECKING:
    from galaxy.job_execution.setup import JobIO
    from galaxy.model import (
        DatasetInstance,
        Job,
    )

log = getLogger(__name__)


@dataclass(frozen=True)
class _ReencryptionHttpResponse:
    status_code: int
    text: str
    json_payload: Any

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


def _is_dev_style_https_reencryption_url(*, reencryption_service_url: str) -> bool:
    parsed_url = urlsplit(reencryption_service_url)
    if parsed_url.scheme.lower() != "https":
        return False

    hostname = parsed_url.hostname
    if not hostname:
        return False

    if hostname == "localhost":
        return True

    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return "." not in hostname


def _ssl_context_for_reencryption_url(
    *,
    reencryption_service_url: str,
    truststore_module: Any,
) -> ssl.SSLContext | None:
    if not _is_dev_style_https_reencryption_url(reencryption_service_url=reencryption_service_url):
        return None

    if truststore_module is None:
        log.warning(
            "Crypt4GH re-encryption service URL %s matches local/dev HTTPS pattern, "
            "but truststore is unavailable; falling back to default TLS handling",
            reencryption_service_url,
        )
        return None

    try:
        ssl_context = truststore_module.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        log.warning(
            "Failed to initialize truststore SSL context for Crypt4GH re-encryption service URL %s; "
            "falling back to default TLS handling",
            reencryption_service_url,
            exc_info=True,
        )
        return None

    return ssl_context


async def _post_reencryption_json_async(
    *,
    endpoint: str,
    payload: dict[str, str],
    ssl_context: ssl.SSLContext | None,
) -> _ReencryptionHttpResponse:
    timeout = aiohttp.ClientTimeout(total=30)
    ssl_option: ssl.SSLContext | bool = ssl_context if ssl_context is not None else True
    async with aiohttp.ClientSession(timeout=timeout) as request_session:
        async with request_session.post(endpoint, json=payload, ssl=ssl_option) as response:
            response_text = await response.text()
            try:
                response_json: Any = json.loads(response_text) if response_text else None
            except ValueError:
                response_json = None

            return _ReencryptionHttpResponse(
                status_code=response.status,
                text=response_text,
                json_payload=response_json,
            )


async def _post_many_reencryption_json_async(
    *,
    endpoint: str,
    payloads: Sequence[dict[str, str]],
    ssl_context: ssl.SSLContext | None,
) -> list[_ReencryptionHttpResponse]:
    timeout = aiohttp.ClientTimeout(total=30)
    ssl_option: ssl.SSLContext | bool = ssl_context if ssl_context is not None else True
    async with aiohttp.ClientSession(timeout=timeout) as request_session:
        requests_to_send = [request_session.post(endpoint, json=payload, ssl=ssl_option) for payload in payloads]
        responses = await asyncio.gather(*requests_to_send)
        try:
            results: list[_ReencryptionHttpResponse] = []
            for response in responses:
                response_text = await response.text()
                try:
                    response_json: Any = json.loads(response_text) if response_text else None
                except ValueError:
                    response_json = None

                results.append(
                    _ReencryptionHttpResponse(
                        status_code=response.status,
                        text=response_text,
                        json_payload=response_json,
                    )
                )
            return results
        finally:
            for response in responses:
                response.release()


def _post_reencryption_json(
    *, reencryption_service_url: str, endpoint: str, payload: dict[str, str]
) -> _ReencryptionHttpResponse:
    ssl_context = _ssl_context_for_reencryption_url(
        reencryption_service_url=reencryption_service_url,
        truststore_module=_optional_truststore,
    )
    return asyncio.run(
        _post_reencryption_json_async(
            endpoint=endpoint,
            payload=payload,
            ssl_context=ssl_context,
        )
    )


def _post_many_reencryption_json(
    *,
    reencryption_service_url: str,
    endpoint: str,
    payloads: Sequence[dict[str, str]],
) -> list[_ReencryptionHttpResponse]:
    ssl_context = _ssl_context_for_reencryption_url(
        reencryption_service_url=reencryption_service_url,
        truststore_module=_optional_truststore,
    )
    return asyncio.run(
        _post_many_reencryption_json_async(
            endpoint=endpoint,
            payloads=payloads,
            ssl_context=ssl_context,
        )
    )


class _Crypt4GHAppConfig(Protocol):
    enable_crypt4gh_transparent_input_matching: bool
    enable_crypt4gh_remote_execution_staging: bool
    enable_crypt4gh_transparent_staging: bool
    outputs_to_working_directory: bool
    metadata_strategy: str
    crypt4gh_reencryption_service_url: str | None
    tool_evaluation_strategy: str | None


class Crypt4GHRemoteExecutionError(Exception):
    """Raised when execution-side Crypt4GH setup must fail closed."""


_DEFAULT_MINIMUM_TTL = timedelta(days=1)
_DESTINATION_WALLTIME_BUFFER = timedelta(hours=1)
_CRYPT4GH_FILE_SUFFIX = ".c4gh"


class _HeaderThenBodyStream:
    """Stream wrapper that prepends a replacement Crypt4GH header."""

    def __init__(self, *, header_bytes: bytes, body_stream: BinaryIO) -> None:
        self._header = memoryview(header_bytes)
        self._header_pos = 0
        self._body_stream = body_stream

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            header_remainder = self._header[self._header_pos :].tobytes()
            self._header_pos = len(self._header)
            body_remainder = self._body_stream.read()
            return header_remainder + body_remainder

        if size == 0:
            return b""

        chunks: list[bytes] = []
        header_remaining = len(self._header) - self._header_pos
        if header_remaining > 0:
            take = min(size, header_remaining)
            chunks.append(self._header[self._header_pos : self._header_pos + take].tobytes())
            self._header_pos += take

        body_remaining = size - sum(len(chunk) for chunk in chunks)
        if body_remaining > 0:
            chunks.append(self._body_stream.read(body_remaining))

        return b"".join(chunks)

    def readinto(self, buffer: bytearray) -> int:
        data = self.read(len(buffer))
        bytes_read = len(data)
        if bytes_read:
            buffer[:bytes_read] = data
        return bytes_read


@dataclass(frozen=True)
class _RecryptToJobKeyResult:
    crypt4gh_header: str
    crypt4gh_compute_public_key: str
    crypt4gh_compute_keypair_id: str
    crypt4gh_compute_keypair_expiration_date: str


@dataclass(frozen=True)
class _DeclaredCrypt4GHOutputTarget:
    association_name: str
    output_path: str
    dataset_output_path: str | None
    extra_files_output_path: str | None
    extra_files_manifest_path: str | None
    plaintext_path: str
    encrypted_marker_path: str
    encrypted_ext: str
    clear_compute_keypair: bool
    allowed_root_paths: tuple[str, ...] = ()
    plaintext_root_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ComputeKeyContext:
    """Compute-side key context inferred from recrypt responses."""

    public_key: str
    keypair_id: str
    keypair_expiration_date: str


class Crypt4GHRemoteComputeEnvironment(SharedComputeEnvironment):
    """Compute environment that rewrites remote input paths for Crypt4GH jobs."""

    def __init__(
        self,
        *,
        job_io: JobIO,
        job: Job,
        input_path_overrides_by_dataset_id: Mapping[int, str],
        compute_public_key: str | None,
        compute_keypair_id: str | None,
        compute_keypair_expiration_date: str | None,
    ) -> None:
        super().__init__(job_io=job_io, job=job)
        self._input_path_overrides_by_dataset_id = dict(input_path_overrides_by_dataset_id)
        self.compute_public_key = compute_public_key
        self.compute_keypair_id = compute_keypair_id
        self.compute_keypair_expiration_date = compute_keypair_expiration_date

    def input_path_rewrite(self, dataset: DatasetInstance) -> str:
        """Return plaintext override path for staged Crypt4GH input datasets."""

        dataset_object = getattr(dataset, "dataset", None)
        dataset_id = getattr(dataset_object, "id", None)
        if isinstance(dataset_id, int):
            rewritten_path = self._input_path_overrides_by_dataset_id.get(dataset_id)
            if rewritten_path:
                return rewritten_path
        return super().input_path_rewrite(dataset)


Crypt4GHComputeEnvironment = Crypt4GHRemoteComputeEnvironment


def _crypt4gh_staging_enabled(app_config: _Crypt4GHAppConfig) -> bool:
    return bool(
        getattr(app_config, "enable_crypt4gh_remote_execution_staging", False)
        or getattr(app_config, "enable_crypt4gh_transparent_staging", False)
    )


def build_crypt4gh_remote_compute_environment(
    *,
    job_io: JobIO,
    job: Job,
    working_directory: str,
    reencryption_service_url: str,
    minimum_ttl: timedelta | None = None,
    now: datetime | None = None,
) -> Crypt4GHRemoteComputeEnvironment:
    """Build remote compute environment with staged plaintext Crypt4GH inputs."""

    crypt4gh_inputs = _collect_crypt4gh_inputs(job_io)
    if not crypt4gh_inputs:
        raise Crypt4GHRemoteExecutionError("Crypt4GH remote execution requested but no Crypt4GH inputs were detected")

    destination_params = dict(getattr(job, "destination_params", {}) or {})
    effective_minimum_ttl = _minimum_ttl_for_destination(
        destination_params=destination_params,
        fallback_minimum_ttl=minimum_ttl or _DEFAULT_MINIMUM_TTL,
    )
    current_time = now or datetime.now(timezone.utc)
    _assert_minimum_ttl(datasets=crypt4gh_inputs, minimum_ttl=effective_minimum_ttl, now=current_time)

    crypt_inputs_workspace = _ensure_crypt4gh_inputs_workspace(working_directory)
    job_private_key, job_public_key = _generate_job_keypair()
    input_path_overrides_by_dataset_id, compute_context = _prepare_plaintext_inputs(
        datasets=crypt4gh_inputs,
        crypt_inputs_workspace=crypt_inputs_workspace,
        reencryption_service_url=reencryption_service_url,
        job_public_key=job_public_key,
        job_private_key=job_private_key,
    )

    return Crypt4GHRemoteComputeEnvironment(
        job_io=job_io,
        job=job,
        input_path_overrides_by_dataset_id=input_path_overrides_by_dataset_id,
        compute_public_key=compute_context.public_key,
        compute_keypair_id=compute_context.keypair_id,
        compute_keypair_expiration_date=compute_context.keypair_expiration_date,
    )


def _prepare_plaintext_inputs(
    *,
    datasets: Sequence[DatasetInstance],
    crypt_inputs_workspace: Path,
    reencryption_service_url: str,
    job_public_key: str,
    job_private_key: bytes,
) -> tuple[dict[int, str], _ComputeKeyContext]:
    endpoint = f"{reencryption_service_url.rstrip('/')}/recrypt_header_to_job_key"
    recrypt_payloads = _build_recrypt_payloads(datasets=datasets, job_public_key=job_public_key)
    responses = _post_many_reencryption_json(
        reencryption_service_url=reencryption_service_url,
        endpoint=endpoint,
        payloads=[payload["request_payload"] for payload in recrypt_payloads],
    )
    if len(responses) != len(recrypt_payloads):
        raise Crypt4GHRemoteExecutionError(
            "Compute-side recryptor B must return one response per dataset for /recrypt_header_to_job_key"
        )

    input_path_overrides_by_dataset_id: dict[int, str] = {}
    compute_context: _ComputeKeyContext | None = None

    for payload, response in zip(recrypt_payloads, responses):
        recrypt_result = _parse_recrypt_header_to_job_key_response(
            response=response,
            endpoint=endpoint,
        )
        dataset_id, plaintext_path = _prepare_plaintext_input_for_dataset(
            dataset=cast(Any, payload["dataset"]),
            source_header=cast(str, payload["source_header"]),
            recrypt_header=recrypt_result.crypt4gh_header,
            crypt_inputs_workspace=crypt_inputs_workspace,
            job_private_key=job_private_key,
        )
        input_path_overrides_by_dataset_id[dataset_id] = plaintext_path

        candidate_context = _ComputeKeyContext(
            public_key=recrypt_result.crypt4gh_compute_public_key,
            keypair_id=recrypt_result.crypt4gh_compute_keypair_id,
            keypair_expiration_date=recrypt_result.crypt4gh_compute_keypair_expiration_date,
        )
        if compute_context is None:
            compute_context = candidate_context
        else:
            _assert_consistent_compute_key_context(existing=compute_context, candidate=candidate_context)

    if compute_context is None:
        raise Crypt4GHRemoteExecutionError("Crypt4GH remote execution requested but no Crypt4GH inputs were detected")

    return input_path_overrides_by_dataset_id, compute_context


def _build_recrypt_payloads(
    *,
    datasets: Sequence[DatasetInstance],
    job_public_key: str,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for dataset in datasets:
        dataset_object = getattr(dataset, "dataset", None)
        dataset_id = getattr(dataset_object, "id", None)
        if not isinstance(dataset_id, int):
            raise Crypt4GHRemoteExecutionError("Crypt4GH input dataset is missing a persisted dataset id")

        metadata = getattr(dataset, "metadata", None)
        source_header = getattr(metadata, "crypt4gh_header", None)
        compute_header = getattr(metadata, "crypt4gh_compute_header", None)
        keypair_id = getattr(metadata, "crypt4gh_compute_keypair_id", None)
        if not source_header or not compute_header or not keypair_id:
            raise Crypt4GHRemoteExecutionError(
                "Crypt4GH input metadata must include crypt4gh_header, crypt4gh_compute_header, and crypt4gh_compute_keypair_id"
            )

        payloads.append(
            {
                "dataset": dataset,
                "dataset_id": dataset_id,
                "source_header": cast(str, source_header),
                "request_payload": {
                    "crypt4gh_header": cast(str, compute_header),
                    "crypt4gh_compute_keypair_id": cast(str, keypair_id),
                    "crypt4gh_job_public_key": job_public_key,
                },
            }
        )
    return payloads


def _parse_recrypt_header_to_job_key_response(
    *,
    response: _ReencryptionHttpResponse,
    endpoint: str,
) -> _RecryptToJobKeyResult:
    if not response.ok:
        raise Crypt4GHRemoteExecutionError(
            f"Compute-side recryptor B returned HTTP {response.status_code} for {endpoint}: "
            f"{_summarize_http_error_response(response)}"
        )

    try:
        response_json = response.json_payload
        if not isinstance(response_json, dict):
            raise ValueError("Response body is not a JSON object")

        return _RecryptToJobKeyResult(
            crypt4gh_header=cast(str, response_json["crypt4gh_header"]),
            crypt4gh_compute_public_key=cast(str, response_json["crypt4gh_compute_public_key"]),
            crypt4gh_compute_keypair_id=cast(str, response_json["crypt4gh_compute_keypair_id"]),
            crypt4gh_compute_keypair_expiration_date=cast(
                str, response_json["crypt4gh_compute_keypair_expiration_date"]
            ),
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise Crypt4GHRemoteExecutionError(
            "Compute-side recryptor B returned an invalid /recrypt_header_to_job_key payload"
        ) from exc


def _assert_consistent_compute_key_context(*, existing: _ComputeKeyContext, candidate: _ComputeKeyContext) -> None:
    if existing.public_key != candidate.public_key:
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH job inputs reference multiple compute public keys; mixed key contexts are unsupported"
        )
    if existing.keypair_id != candidate.keypair_id:
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH job inputs reference multiple compute keypair ids; mixed key contexts are unsupported"
        )
    if existing.keypair_expiration_date != candidate.keypair_expiration_date:
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH job inputs reference multiple compute key expiry timestamps; mixed key contexts are unsupported"
        )


def should_run_crypt4gh_remote_execution(
    *,
    job_io: JobIO,
    app_config: _Crypt4GHAppConfig,
    destination_params: dict[str, Any],
    provided_metadata_style: str | None = None,
    minimum_ttl: timedelta | None = None,
    now: datetime | None = None,
) -> bool:
    """Decide whether execution-side Crypt4GH setup is allowed for this job.

    The helper is intentionally small for the Task 3 contract:
    - top-level gate: ``enable_crypt4gh_remote_execution_staging``
    - execution path only when ``tool_evaluation_strategy == "remote"``
    - only if at least one Crypt4GH input dataset is present
    - setup failures must fail closed
    """

    if not _crypt4gh_staging_enabled(app_config):
        return False

    if _effective_tool_evaluation_strategy(destination_params=destination_params, app_config=app_config) != "remote":
        return False

    crypt4gh_inputs = _collect_crypt4gh_inputs(job_io)
    if not crypt4gh_inputs:
        return False

    if provided_metadata_style == "legacy":
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH remote execution is not supported for tools with legacy provided_metadata_style; "
            "use a tool with profile >= 17.09 or set provided_metadata_style to \"default\""
        )

    effective_minimum_ttl = _minimum_ttl_for_destination(
        destination_params=destination_params,
        fallback_minimum_ttl=minimum_ttl or _DEFAULT_MINIMUM_TTL,
    )
    current_time = now or datetime.now(timezone.utc)
    _assert_minimum_ttl(datasets=crypt4gh_inputs, minimum_ttl=effective_minimum_ttl, now=current_time)
    return True


def assert_crypt4gh_job_readiness(
    *,
    job_io: JobIO,
    tool: Any | None,
    app_config: _Crypt4GHAppConfig,
    destination_params: Mapping[str, Any],
    metadata_strategy: str,
    reencryption_service_url: str | None = None,
) -> None:
    """Fail closed when Crypt4GH transparent-adapted jobs are misconfigured.

    Transparent input matching and remote execution staging are intentionally split:
    transparent input matching may be enabled alone, but if a job depends on
    transparent adaptation (tool input does not explicitly accept ``.c4gh``),
    remote-execution prerequisites must be satisfied.
    """

    remote_execution_staging_enabled = bool(getattr(app_config, "enable_crypt4gh_remote_execution_staging", False))
    transparent_input_matching_enabled = bool(getattr(app_config, "enable_crypt4gh_transparent_input_matching", False))

    required_remote_settings = [
        "enable_crypt4gh_transparent_input_matching = true",
        "enable_crypt4gh_remote_execution_staging = true",
        "tool_evaluation_strategy = remote",
        "outputs_to_working_directory = true",
        "metadata_strategy = extended",
        "crypt4gh_reencryption_service_url",
    ]

    def _missing_remote_settings_summary() -> str:
        return "; required settings: " + ", ".join(required_remote_settings)

    if remote_execution_staging_enabled and not transparent_input_matching_enabled:
        raise Crypt4GHRemoteExecutionError(
            "Invalid Crypt4GH configuration: enable_crypt4gh_remote_execution_staging requires "
            "enable_crypt4gh_transparent_input_matching = true" + _missing_remote_settings_summary()
        )

    crypt4gh_input_names = _collect_crypt4gh_input_names(job_io=job_io)
    if not crypt4gh_input_names:
        return

    transparent_adapted_inputs = _collect_transparent_adapted_crypt4gh_input_names(job_io=job_io, tool=tool)

    if not remote_execution_staging_enabled:
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH input handling requires enable_crypt4gh_remote_execution_staging = true"
            + _missing_remote_settings_summary()
        )

    if _effective_tool_evaluation_strategy(destination_params=destination_params, app_config=app_config) != "remote":
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH input handling requires tool_evaluation_strategy = remote" + _missing_remote_settings_summary()
        )

    if not bool(getattr(app_config, "outputs_to_working_directory", False)):
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH input handling requires outputs_to_working_directory = true" + _missing_remote_settings_summary()
        )

    if metadata_strategy != "extended":
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH input handling requires metadata_strategy = extended" + _missing_remote_settings_summary()
        )

    effective_reencryption_service_url = str(
        reencryption_service_url or getattr(app_config, "crypt4gh_reencryption_service_url", "") or ""
    ).strip()
    if not effective_reencryption_service_url:
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH input handling requires crypt4gh_reencryption_service_url" + _missing_remote_settings_summary()
        )

    del transparent_adapted_inputs


def _collect_crypt4gh_input_names(*, job_io: JobIO) -> list[str]:
    job = getattr(job_io, "job", None)
    if not job:
        return []

    input_associations = [
        *list(getattr(job, "input_datasets", []) or []),
        *list(getattr(job, "input_library_datasets", []) or []),
    ]
    if not input_associations:
        return []

    crypt4gh_input_names: list[str] = []
    for input_association in input_associations:
        dataset = getattr(input_association, "dataset", None)
        if dataset is None or not _is_crypt4gh_dataset_instance(dataset):
            continue

        input_name = getattr(input_association, "name", "")
        if not isinstance(input_name, str) or not input_name:
            input_name = "<unnamed>"
        crypt4gh_input_names.append(input_name)

    return crypt4gh_input_names


def _effective_tool_evaluation_strategy(
    *, destination_params: Mapping[str, Any], app_config: _Crypt4GHAppConfig
) -> str:
    destination_strategy = destination_params.get("tool_evaluation_strategy")
    if isinstance(destination_strategy, str) and destination_strategy:
        return destination_strategy

    global_strategy = getattr(app_config, "tool_evaluation_strategy", None)
    if isinstance(global_strategy, str) and global_strategy:
        return global_strategy

    return ""


def _collect_transparent_adapted_crypt4gh_input_names(*, job_io: JobIO, tool: Any | None) -> list[str]:
    job = getattr(job_io, "job", None)
    if not job:
        return []

    input_associations = [
        *list(getattr(job, "input_datasets", []) or []),
        *list(getattr(job, "input_library_datasets", []) or []),
    ]
    if not input_associations:
        return []

    tool_inputs = getattr(tool, "inputs", {}) if tool is not None else {}
    adapted_names: list[str] = []
    for input_association in input_associations:
        dataset = getattr(input_association, "dataset", None)
        if dataset is None or not _is_crypt4gh_dataset_instance(dataset):
            continue

        input_name = getattr(input_association, "name", "")
        if not isinstance(input_name, str) or not input_name:
            adapted_names.append("<unnamed>")
            continue

        tool_input = tool_inputs.get(input_name) if isinstance(tool_inputs, Mapping) else None
        if _tool_input_explicitly_accepts_crypt4gh(tool_input):
            continue

        adapted_names.append(input_name)

    return adapted_names


def _is_crypt4gh_dataset_instance(dataset: Any) -> bool:
    metadata = getattr(dataset, "metadata", None)
    if metadata and getattr(metadata, "crypt4gh_header", None):
        return True

    return str(getattr(dataset, "ext", "") or "").endswith(".c4gh")


def _tool_input_explicitly_accepts_crypt4gh(tool_input: Any) -> bool:
    if tool_input is None:
        return False

    extensions = getattr(tool_input, "extensions", None)
    if not isinstance(extensions, Sequence):
        return False

    return any(isinstance(extension, str) and extension.endswith(".c4gh") for extension in extensions)


def _minimum_ttl_for_destination(
    *, destination_params: Mapping[str, Any], fallback_minimum_ttl: timedelta
) -> timedelta:
    walltime_value = destination_params.get("walltime")
    walltime_delta = _parse_destination_walltime(walltime_value)
    if walltime_delta is None:
        return fallback_minimum_ttl
    derived_minimum_ttl = walltime_delta + _DESTINATION_WALLTIME_BUFFER
    return max(fallback_minimum_ttl, derived_minimum_ttl)


def _parse_destination_walltime(walltime_value: Any) -> timedelta | None:
    if not isinstance(walltime_value, str):
        return None
    parts = walltime_value.strip().split(":")
    if len(parts) != 3:
        return None
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        return None
    if hours < 0 or minutes < 0 or seconds < 0:
        return None
    if minutes >= 60 or seconds >= 60:
        return None
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _collect_crypt4gh_inputs(job_io: JobIO) -> list[DatasetInstance]:
    datasets: list[DatasetInstance] = []
    for dataset in job_io.get_input_datasets():
        metadata = getattr(dataset, "metadata", None)
        if metadata and getattr(metadata, "crypt4gh_header", None):
            datasets.append(dataset)
    return datasets


def _ensure_crypt4gh_inputs_workspace(working_directory: str) -> Path:
    workspace = Path(working_directory) / "_crypt" / "inputs"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _format_crypt4gh_public_key(public_key: bytes) -> str:
    encoded_public_key = base64.b64encode(public_key).decode("ascii")
    return "\n".join(
        [
            "-----BEGIN CRYPT4GH PUBLIC KEY-----",
            encoded_public_key,
            "-----END CRYPT4GH PUBLIC KEY-----",
        ]
    )


def _generate_job_keypair() -> tuple[bytes, str]:
    private_key = X25519PrivateKey.generate()
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_key_bytes, _format_crypt4gh_public_key(public_key_bytes)


def _prepare_plaintext_input_for_dataset(
    *,
    dataset: DatasetInstance,
    source_header: str,
    recrypt_header: str,
    crypt_inputs_workspace: Path,
    job_private_key: bytes,
) -> tuple[int, str]:
    dataset_object = getattr(dataset, "dataset", None)
    dataset_id = getattr(dataset_object, "id", None)
    if not isinstance(dataset_id, int):
        raise Crypt4GHRemoteExecutionError("Crypt4GH input dataset is missing a persisted dataset id")

    dataset_workspace = crypt_inputs_workspace / f"ds_{dataset_id}"
    dataset_workspace.mkdir(parents=True, exist_ok=True)
    plaintext_path = dataset_workspace / "plaintext"

    source_dataset_path = Path(dataset.get_file_name())
    _decrypt_recrypted_input(
        source_dataset_path=source_dataset_path,
        source_header=source_header,
        recrypted_header=recrypt_header,
        plaintext_path=plaintext_path,
        job_private_key=job_private_key,
    )
    return dataset_id, str(plaintext_path)


def collect_declared_crypt4gh_output_targets(
    *,
    job_io: JobIO,
    tool_outputs: Mapping[str, Any],
    datatypes_registry: Any,
    working_directory: str,
) -> list[dict[str, Any]]:
    """Collect declared non-discovery outputs that require Crypt4GH finalization."""

    targets: list[dict[str, Any]] = []
    marker_dir = Path(working_directory) / "_c4gh_stage" / "outputs"
    plaintext_root = Path(working_directory) / "_crypt" / "outputs"
    tool_working_directory = Path(working_directory) / "working"

    for output_name, (dataset, dataset_path) in job_io.get_output_hdas_and_fnames().items():
        if output_name.startswith("__new_primary_file_"):
            continue

        output_name_for_tool_lookup = _resolve_output_name_for_tool_lookup(
            output_name=output_name,
            tool_outputs=tool_outputs,
        )
        if output_name_for_tool_lookup is None:
            raise Crypt4GHRemoteExecutionError(
                f"Crypt4GH output target '{output_name}' has no matching tool output declaration"
            )
        dataset_object = getattr(dataset, "dataset", None)
        dataset_id = getattr(dataset_object, "id", None)
        if not isinstance(dataset_id, int):
            raise Crypt4GHRemoteExecutionError(
                f"Crypt4GH output target '{output_name}' is missing a persisted dataset id"
            )

        tool_output = tool_outputs.get(output_name_for_tool_lookup)
        if _is_discovery_routed_output(tool_output):
            continue

        base_ext = _resolve_base_output_extension(dataset=dataset, tool_output=tool_output)
        if base_ext is None:
            if _has_output_collectors(tool_output):
                continue
            raise Crypt4GHRemoteExecutionError(
                f"Crypt4GH output target '{output_name}' could not resolve encrypted output extension"
            )

        encrypted_ext = _ensure_crypt4gh_output_datatype(
            datatypes_registry=datatypes_registry,
            base_ext=base_ext,
        )
        output_path, output_path_source = _resolve_output_path_with_source(
            dataset_path=dataset_path,
            tool_output=tool_output,
            tool_working_directory=tool_working_directory,
        )
        _assert_output_path_inside_job_working_directory(
            output_path=output_path,
            output_path_source=output_path_source,
            working_directory=working_directory,
            output_name=output_name,
        )
        _print_declared_output_target_debug(
            output_name=output_name,
            output_name_for_tool_lookup=output_name_for_tool_lookup,
            output_path=output_path,
            output_path_source=output_path_source,
            from_work_dir=getattr(tool_output, "from_work_dir", None),
            false_path=getattr(dataset_path, "false_path", None),
            real_path=getattr(dataset_path, "real_path", None),
            working_directory=working_directory,
        )

        target = _DeclaredCrypt4GHOutputTarget(
            association_name=output_name,
            output_path=output_path,
            dataset_output_path=cast(str | None, getattr(dataset_path, "real_path", None)),
            extra_files_output_path=cast(str | None, getattr(dataset_path, "false_extra_files_path", None))
            or dataset_path_to_extra_path(output_path),
            extra_files_manifest_path=str(marker_dir / f"ds_{dataset_id}.extra_files_manifest.json"),
            plaintext_path=str(plaintext_root / f"ds_{dataset_id}" / "plaintext"),
            encrypted_marker_path=str(marker_dir / f"ds_{dataset_id}.encrypted"),
            encrypted_ext=encrypted_ext,
            clear_compute_keypair=True,
            allowed_root_paths=_declared_output_allowed_root_paths(
                working_directory=working_directory,
                dataset_output_path=cast(str | None, getattr(dataset_path, "real_path", None)),
            ),
            plaintext_root_paths=(str(Path(working_directory).resolve()),),
        )
        targets.append(_declared_output_target_to_mapping(target))

    return targets


def collect_discovery_crypt4gh_output_specs(
    *,
    job_io: JobIO,
    tool_outputs: Mapping[str, Any],
    datatypes_registry: Any,
    working_directory: str,
) -> list[dict[str, Any]]:
    """Collect discovery-output specs for postrun encryption scanning.

    The resulting specs are intentionally serialization-friendly and can be
    passed to the postrun helper script.
    """

    discovery_specs: list[dict[str, Any]] = []
    tool_working_directory = Path(working_directory) / "working"
    discovered_marker_map_path = str(Path(working_directory) / "_c4gh_stage" / "outputs" / "discovered_designations.json")

    for output_name, tool_output in tool_outputs.items():
        collectors = list(getattr(tool_output, "dataset_collector_descriptions", []) or [])
        if not collectors:
            continue

        base_ext = getattr(tool_output, "format", None)
        if not base_ext or base_ext in ("auto", "data", "_sniff_", "input"):
            continue
        encrypted_ext = _ensure_crypt4gh_output_datatype(
            datatypes_registry=datatypes_registry,
            base_ext=cast(str, base_ext),
        )

        for collector in collectors:
            directory = str(getattr(collector, "directory", "") or "")
            if os.path.isabs(directory):
                scan_root = directory
            elif directory:
                scan_root = str(tool_working_directory / directory)
            else:
                scan_root = str(tool_working_directory)

            discover_via = str(getattr(collector, "discover_via", "pattern") or "pattern")
            pattern = str(getattr(collector, "pattern", "") or "")
            if not pattern:
                pattern = r"(?P<designation>.+)"

            discovery_specs.append(
                {
                    "output_name": output_name,
                    "discover_via": discover_via,
                    "pattern": pattern,
                    "scan_root": scan_root,
                    "encrypted_ext": encrypted_ext,
                    "assign_primary_output": bool(getattr(collector, "assign_primary_output", False)),
                    "recurse": bool(getattr(collector, "recurse", False)),
                    "match_relative_path": bool(getattr(collector, "match_relative_path", False)),
                    "discovered_marker_map_path": discovered_marker_map_path,
                    "allowed_root_paths": [str(Path(working_directory).resolve())],
                    "plaintext_root_paths": [str(Path(working_directory).resolve())],
                }
            )

    return discovery_specs


def finalize_discovered_crypt4gh_payloads(
    *,
    discovery_specs: Sequence[Mapping[str, Any]],
    working_directory: str,
    reencryption_service_url: str,
    compute_public_key: str,
    compute_keypair_id: str,
    compute_keypair_expiration_date: str | None = None,
) -> list[dict[str, Any]]:
    """Scan discovery roots and finalize discovered payloads in-place."""

    payload_metadata: list[dict[str, Any]] = []
    for spec in discovery_specs:
        if str(spec.get("discover_via", "pattern")) != "pattern":
            continue

        scan_root = Path(str(spec.get("scan_root", "") or ""))
        if not scan_root.exists() or not scan_root.is_dir():
            continue

        pattern_text = str(spec.get("pattern", "") or "")
        try:
            compiled_pattern = re.compile(pattern_text)
        except re.error:
            continue

        recurse = bool(spec.get("recurse", False))
        walk_iter = os.walk(scan_root) if recurse else [(str(scan_root), [], os.listdir(scan_root))]
        for root, _dirs, files in walk_iter:
            for file_name in files:
                source_path = Path(root) / file_name
                if source_path.name.endswith(".c4gh"):
                    continue

                candidate_text = str(source_path.relative_to(scan_root)) if bool(spec.get("match_relative_path", False)) else source_path.name
                match = compiled_pattern.match(candidate_text)
                if not match:
                    continue

                designation = match.groupdict().get("designation") if match.groupdict() else None
                designation = designation or source_path.stem
                encrypted_ext = str(spec["encrypted_ext"])
                # Encrypt the discovered plaintext file in place: the file keeps its
                # original name (so Galaxy's pattern discovery still matches it) while
                # its bytes become a Crypt4GH payload.  finalize_about_to_persist_crypt4gh_payload
                # -> _finalize_output_target copies output_path to the plaintext staging
                # area (_crypt/outputs/discovered/<designation>/plaintext, removed by
                # cleanup_crypt4gh_plaintext_artifacts) and os.replace-s the encrypted
                # result back onto output_path.  Pointing output_path at a non-existent
                # ``*.c4gh`` sidecar (the previous behaviour) made that copyfile fail.
                output_path = str(source_path)

                finalize_about_to_persist_crypt4gh_payload(
                    output_path=output_path,
                    plaintext_path=str(Path(working_directory) / "_crypt" / "outputs" / "discovered" / designation / "plaintext"),
                    encrypted_ext=encrypted_ext,
                    reencryption_service_url=reencryption_service_url,
                    compute_public_key=compute_public_key,
                    compute_keypair_id=compute_keypair_id,
                    compute_keypair_expiration_date=compute_keypair_expiration_date,
                    encrypted_marker_path="",
                    dataset_output_path="",
                    designation=designation,
                    discovered_marker_map_path=str(spec.get("discovered_marker_map_path", "") or ""),
                    allowed_root_paths=cast(Sequence[str], spec.get("allowed_root_paths", [])),
                    plaintext_root_paths=cast(Sequence[str], spec.get("plaintext_root_paths", [])),
                    clear_compute_keypair=False,
                )

                payload_metadata.append(
                    {
                        "output_name": str(spec.get("output_name", "")),
                        "designation": designation,
                        "filename": source_path.name,
                        "encrypted_ext": encrypted_ext,
                    }
                )

    return payload_metadata


def emit_crypt4gh_galaxy_metadata(
    *,
    output_targets: Sequence[Mapping[str, Any]],
    output_metadata: Sequence[Mapping[str, Any]],
    discovered_payload_metadata: Sequence[Mapping[str, Any]],
    compute_keypair_id: str,
    compute_keypair_expiration_date: str | None,
    galaxy_json_path: str,
) -> None:
    """Merge Crypt4GH metadata for declared and discovered outputs into galaxy.json."""

    existing: dict[str, Any] = {}
    galaxy_json = Path(galaxy_json_path)
    if galaxy_json.exists():
        try:
            loaded = json.loads(galaxy_json.read_text())
            if isinstance(loaded, dict):
                existing = loaded
        except Exception:
            existing = {}

    for metadata_entry in output_metadata:
        association_name = str(metadata_entry.get("association_name", "") or "")
        if not association_name:
            continue
        association_payload = existing.setdefault(association_name, {})
        if not isinstance(association_payload, dict):
            association_payload = {}
            existing[association_name] = association_payload
        encrypted_ext = str(metadata_entry.get("encrypted_ext", "") or "")
        if encrypted_ext:
            association_payload["ext"] = encrypted_ext
        metadata_payload = association_payload.setdefault("metadata", {})
        if not isinstance(metadata_payload, dict):
            metadata_payload = {}
            association_payload["metadata"] = metadata_payload
        payload_metadata = metadata_entry.get("metadata") if isinstance(metadata_entry.get("metadata"), dict) else {}
        metadata_payload.update(cast(dict[str, Any], payload_metadata))
        metadata_payload["crypt4gh_compute_keypair_id"] = compute_keypair_id
        metadata_payload["crypt4gh_compute_keypair_expiration_date"] = str(compute_keypair_expiration_date or "")
        if "crypt4gh_inner_ext" not in metadata_payload and encrypted_ext.endswith(".c4gh"):
            metadata_payload["crypt4gh_inner_ext"] = encrypted_ext[: -len(".c4gh")]

    for discovered_entry in discovered_payload_metadata:
        output_name = str(discovered_entry.get("output_name", "") or "")
        if not output_name:
            continue
        output_payload = existing.setdefault(output_name, {})
        if not isinstance(output_payload, dict):
            output_payload = {}
            existing[output_name] = output_payload
        datasets = output_payload.setdefault("datasets", [])
        if not isinstance(datasets, list):
            datasets = []
            output_payload["datasets"] = datasets
        encrypted_ext = str(discovered_entry.get("encrypted_ext", "") or "")
        designation = str(discovered_entry.get("designation", "") or "")
        filename = str(discovered_entry.get("filename", "") or "")
        metadata_payload = {
            "crypt4gh_compute_keypair_id": compute_keypair_id,
            "crypt4gh_compute_keypair_expiration_date": str(compute_keypair_expiration_date or ""),
        }
        if encrypted_ext.endswith(".c4gh"):
            metadata_payload["crypt4gh_inner_ext"] = encrypted_ext[: -len(".c4gh")]
        datasets.append(
            {
                "name": designation,
                "designation": designation,
                "filename": filename,
                "ext": encrypted_ext,
                "metadata": metadata_payload,
            }
        )

    galaxy_json.parent.mkdir(parents=True, exist_ok=True)
    galaxy_json.write_text(json.dumps(existing))


def build_crypt4gh_postrun_command(
    *,
    tool_command: str,
    output_targets: Sequence[Mapping[str, Any]],
    discovery_specs: Sequence[Mapping[str, Any]],
    galaxy_json_path: str,
    working_directory: str,
    reencryption_service_url: str,
    compute_public_key: str,
    compute_keypair_id: str,
    compute_keypair_expiration_date: str | None,
    python_executable: str,
) -> str:
    """Build a wrapped shell command that finalizes Crypt4GH outputs after tool success."""

    galaxy_lib_dir = str(Path(__file__).resolve().parents[2])

    postrun_script = (
        "import json\n"
        f"from galaxy.tools.crypt4gh_remote_execution import finalize_declared_crypt4gh_outputs, finalize_discovered_crypt4gh_payloads, emit_crypt4gh_galaxy_metadata\n"
        f"_OUTPUT_TARGETS = json.loads({json.dumps(json.dumps(list(output_targets)))})\n"
        f"_DISCOVERY_SPECS = json.loads({json.dumps(json.dumps(list(discovery_specs)))})\n"
        f"_DECLARED_METADATA = finalize_declared_crypt4gh_outputs(output_targets=_OUTPUT_TARGETS, reencryption_service_url={json.dumps(reencryption_service_url)}, compute_public_key={json.dumps(compute_public_key)}, compute_keypair_id={json.dumps(compute_keypair_id)}, compute_keypair_expiration_date={json.dumps(compute_keypair_expiration_date)})\n"
        f"_DISCOVERED_METADATA = finalize_discovered_crypt4gh_payloads(discovery_specs=_DISCOVERY_SPECS, working_directory={json.dumps(working_directory)}, reencryption_service_url={json.dumps(reencryption_service_url)}, compute_public_key={json.dumps(compute_public_key)}, compute_keypair_id={json.dumps(compute_keypair_id)}, compute_keypair_expiration_date={json.dumps(compute_keypair_expiration_date)})\n"
        f"emit_crypt4gh_galaxy_metadata(output_targets=_OUTPUT_TARGETS, output_metadata=_DECLARED_METADATA, discovered_payload_metadata=_DISCOVERED_METADATA, compute_keypair_id={json.dumps(compute_keypair_id)}, compute_keypair_expiration_date={json.dumps(compute_keypair_expiration_date)}, galaxy_json_path={json.dumps(galaxy_json_path)})\n"
    )
    postrun_command = (
        f"PYTHONPATH={shlex.quote(galaxy_lib_dir)}:$PYTHONPATH "
        f"{shlex.quote(python_executable)} -c {shlex.quote(postrun_script)}"
    )
    cleanup_script = f"from galaxy.util.crypt4gh import cleanup_crypt4gh_plaintext_artifacts; cleanup_crypt4gh_plaintext_artifacts(working_directory={json.dumps(working_directory)})"
    cleanup_command = (
        f"PYTHONPATH={shlex.quote(galaxy_lib_dir)}:$PYTHONPATH "
        f"{shlex.quote(python_executable)} -c {shlex.quote(cleanup_script)}"
    )
    return build_crypt4gh_cleanup_wrapped_command(
        tool_command=tool_command,
        postrun_command=postrun_command,
        cleanup_command=cleanup_command,
    )


def _is_discovery_routed_output(tool_output: Any) -> bool:
    if tool_output is None:
        return False
    collectors = list(getattr(tool_output, "dataset_collector_descriptions", []) or [])
    return any(bool(getattr(collector, "assign_primary_output", False)) for collector in collectors)


def _has_output_collectors(tool_output: Any) -> bool:
    if tool_output is None:
        return False
    collectors = list(getattr(tool_output, "dataset_collector_descriptions", []) or [])
    return len(collectors) > 0


def _resolve_output_name_for_tool_lookup(*, output_name: str, tool_outputs: Mapping[str, Any]) -> str | None:
    if output_name in tool_outputs:
        return output_name
    if output_name.startswith("__new_primary_file_"):
        return output_name[len("__new_primary_file_") :].split("|", 1)[0]
    return None


def _resolve_base_output_extension(*, dataset: Any, tool_output: Any) -> str | None:
    base_ext = cast(str, getattr(dataset, "ext", "") or "")
    if not base_ext:
        return None

    if base_ext.endswith(".c4gh"):
        base_ext = base_ext[: -len(".c4gh")]

    if base_ext in ("auto", "data", "_sniff_"):
        declared_ext = getattr(tool_output, "format", None) if tool_output else None
        if declared_ext and declared_ext not in ("auto", "data", "_sniff_", "input"):
            return cast(str, declared_ext)
        return None
    return base_ext


def _ensure_crypt4gh_output_datatype(*, datatypes_registry: Any, base_ext: str) -> str:
    encrypted_ext = f"{base_ext}.c4gh"
    if datatypes_registry.get_datatype_by_extension(encrypted_ext) is None:
        datatypes_registry.get_or_create_crypt4gh_datatype(base_ext)
    return encrypted_ext


def _resolve_output_path(*, dataset_path: Any, tool_output: Any, tool_working_directory: Path) -> str:
    output_path, _output_path_source = _resolve_output_path_with_source(
        dataset_path=dataset_path,
        tool_output=tool_output,
        tool_working_directory=tool_working_directory,
    )
    return output_path


def _resolve_output_path_with_source(
    *, dataset_path: Any, tool_output: Any, tool_working_directory: Path
) -> tuple[str, str]:
    from_work_dir = getattr(tool_output, "from_work_dir", None) if tool_output else None
    if from_work_dir:
        from_work_dir_path = Path(str(from_work_dir))
        if from_work_dir_path.is_absolute():
            return str(from_work_dir_path), "from_work_dir:absolute"
        return str(tool_working_directory / from_work_dir_path), "from_work_dir:relative"

    false_path = getattr(dataset_path, "false_path", None)
    if false_path:
        return cast(str, false_path), "false_path"

    real_path = getattr(dataset_path, "real_path", None)
    if real_path:
        return cast(str, real_path), "real_path"

    return str(dataset_path), "dataset_path:str"


def _print_declared_output_target_debug(
    *,
    output_name: str,
    output_name_for_tool_lookup: str,
    output_path: str,
    output_path_source: str,
    from_work_dir: Any,
    false_path: Any,
    real_path: Any,
    working_directory: str,
) -> None:
    if os.getenv("GALAXY_CRYPT4GH_DEBUG", "") != "1":
        return

    debug_payload = {
        "event": "crypt4gh_declared_output_target",
        "output_name": output_name,
        "tool_output_name": output_name_for_tool_lookup,
        "output_path": output_path,
        "output_path_source": output_path_source,
        "from_work_dir": str(from_work_dir or ""),
        "false_path": str(false_path or ""),
        "real_path": str(real_path or ""),
        "working_directory": working_directory,
    }
    print(f"CRYPT4GH_DEBUG {json.dumps(debug_payload, sort_keys=True)}", flush=True)


def _assert_output_path_inside_job_working_directory(
    *,
    output_path: str,
    output_path_source: str,
    working_directory: str,
    output_name: str,
) -> None:
    resolved_working_directory = Path(working_directory).resolve(strict=False)
    resolved_output_path = Path(output_path).resolve(strict=False)

    try:
        resolved_output_path.relative_to(resolved_working_directory)
    except ValueError as exc:
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH declared output target "
            f"'{output_name}' resolved {output_path_source} outside job working directory: {output_path}"
        ) from exc


def _declared_output_target_to_mapping(target: _DeclaredCrypt4GHOutputTarget) -> dict[str, Any]:
    mapping = {
        "association_name": target.association_name,
        "output_path": target.output_path,
        "plaintext_path": target.plaintext_path,
        "encrypted_marker_path": target.encrypted_marker_path,
        "encrypted_ext": target.encrypted_ext,
        "clear_compute_keypair": target.clear_compute_keypair,
    }
    if target.dataset_output_path:
        mapping["dataset_output_path"] = target.dataset_output_path
    if target.extra_files_output_path:
        mapping["extra_files_output_path"] = target.extra_files_output_path
    if target.extra_files_manifest_path:
        mapping["extra_files_manifest_path"] = target.extra_files_manifest_path
    if target.allowed_root_paths:
        mapping["allowed_root_paths"] = list(target.allowed_root_paths)
    if target.plaintext_root_paths:
        mapping["plaintext_root_paths"] = list(target.plaintext_root_paths)
    return mapping


def _declared_output_allowed_root_paths(*, working_directory: str, dataset_output_path: str | None) -> tuple[str, ...]:
    resolved_roots: list[str] = []
    seen_roots: set[str] = set()

    def _add_root(path_value: str) -> None:
        resolved_root = str(Path(path_value).resolve())
        if resolved_root in seen_roots:
            return
        seen_roots.add(resolved_root)
        resolved_roots.append(resolved_root)

    _add_root(working_directory)
    if dataset_output_path:
        _add_root(str(Path(dataset_output_path).resolve().parent))

    return tuple(resolved_roots)


def finalize_declared_crypt4gh_outputs(
    *,
    output_targets: Sequence[Mapping[str, Any]],
    reencryption_service_url: str,
    compute_public_key: str,
    compute_keypair_id: str,
    compute_keypair_expiration_date: str | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Encrypt declared outputs to user keys and persist extension markers."""

    current_time = now or datetime.now(timezone.utc)
    if compute_keypair_expiration_date:
        _assert_key_valid_for_output_finalization(
            compute_keypair_expiration_date=compute_keypair_expiration_date,
            now=current_time,
        )

    output_metadata: list[dict[str, Any]] = []
    resolved_targets = _iter_unique_existing_output_targets(output_targets)
    try:
        for concrete_target, output_path in resolved_targets:
            payload_metadata = _finalize_output_target(
                concrete_target=concrete_target,
                output_path=output_path,
                reencryption_service_url=reencryption_service_url,
                compute_public_key=compute_public_key,
                compute_keypair_id=compute_keypair_id,
            )
            output_metadata.append(payload_metadata)
            _finalize_extra_files_payloads(
                concrete_target=concrete_target,
                reencryption_service_url=reencryption_service_url,
                compute_public_key=compute_public_key,
                compute_keypair_id=compute_keypair_id,
            )
    except Exception:
        _purge_output_targets_after_finalization_failure(resolved_targets)
        raise
    return output_metadata


def finalize_about_to_persist_crypt4gh_payload(
    *,
    output_path: str,
    plaintext_path: str,
    encrypted_ext: str,
    reencryption_service_url: str,
    compute_public_key: str,
    compute_keypair_id: str,
    compute_keypair_expiration_date: str | None = None,
    encrypted_marker_path: str = "",
    dataset_output_path: str = "",
    designation: str = "",
    discovered_marker_map_path: str = "",
    extra_files_output_path: str = "",
    extra_files_manifest_path: str = "",
    allowed_root_paths: Sequence[str] = (),
    plaintext_root_paths: Sequence[str] = (),
    clear_compute_keypair: bool = True,
) -> None:
    resolved_allowed_root_paths = [str(path) for path in allowed_root_paths if str(path)]
    if not resolved_allowed_root_paths:
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH finalize_about_to_persist requires explicit allowed_root_paths provenance"
        )

    concrete_target: dict[str, Any] = {
        "output_path": output_path,
        "plaintext_path": plaintext_path,
        "encrypted_ext": encrypted_ext,
        "encrypted_marker_path": encrypted_marker_path,
        "clear_compute_keypair": clear_compute_keypair,
    }
    if dataset_output_path:
        concrete_target["dataset_output_path"] = dataset_output_path
    if designation:
        concrete_target["designation"] = designation
    if discovered_marker_map_path:
        concrete_target["discovered_marker_map_path"] = discovered_marker_map_path
    if extra_files_output_path:
        concrete_target["extra_files_output_path"] = extra_files_output_path
    if extra_files_manifest_path:
        concrete_target["extra_files_manifest_path"] = extra_files_manifest_path
    concrete_target["allowed_root_paths"] = resolved_allowed_root_paths
    resolved_plaintext_root_paths = [str(path) for path in plaintext_root_paths if str(path)]
    if resolved_plaintext_root_paths:
        concrete_target["plaintext_root_paths"] = resolved_plaintext_root_paths

    allowed_roots = _resolve_allowed_root_paths(concrete_target)
    plaintext_roots = _resolve_plaintext_root_paths(concrete_target, fallback_roots=allowed_roots)
    _assert_path_within_allowed_roots(
        Path(output_path),
        allowed_root_paths=allowed_roots,
        context="finalize output_path",
    )
    if dataset_output_path:
        _assert_path_within_allowed_roots(
            Path(dataset_output_path),
            allowed_root_paths=allowed_roots,
            context="finalize dataset_output_path",
        )
    if encrypted_marker_path:
        _assert_path_within_allowed_roots(
            Path(encrypted_marker_path),
            allowed_root_paths=allowed_roots,
            context="finalize encrypted_marker_path",
        )
    if extra_files_output_path:
        _assert_path_within_allowed_roots(
            Path(extra_files_output_path),
            allowed_root_paths=allowed_roots,
            context="finalize extra_files_output_path",
        )
    if extra_files_manifest_path:
        _assert_path_within_allowed_roots(
            Path(extra_files_manifest_path),
            allowed_root_paths=allowed_roots,
            context="finalize extra_files_manifest_path",
        )
    _assert_path_within_allowed_roots(
        Path(plaintext_path),
        allowed_root_paths=plaintext_roots,
        context="finalize plaintext_path",
    )

    if compute_keypair_expiration_date:
        _assert_key_valid_for_output_finalization(
            compute_keypair_expiration_date=compute_keypair_expiration_date,
            now=datetime.now(timezone.utc),
        )

    resolved_target = (concrete_target, Path(output_path))
    try:
        _finalize_output_target(
            concrete_target=concrete_target,
            output_path=Path(output_path),
            reencryption_service_url=reencryption_service_url,
            compute_public_key=compute_public_key,
            compute_keypair_id=compute_keypair_id,
        )
        _finalize_extra_files_payloads(
            concrete_target=concrete_target,
            reencryption_service_url=reencryption_service_url,
            compute_public_key=compute_public_key,
            compute_keypair_id=compute_keypair_id,
        )
    except Exception:
        _purge_output_targets_after_finalization_failure([resolved_target])
        raise


def _purge_output_targets_after_finalization_failure(
    resolved_targets: Sequence[tuple[dict[str, Any], Path]],
) -> None:
    for concrete_target, output_path in resolved_targets:
        allowed_roots = _resolve_allowed_root_paths(concrete_target)
        candidate_paths = [output_path]
        dataset_output_path_value = str(concrete_target.get("dataset_output_path", "") or "")
        if dataset_output_path_value:
            candidate_paths.append(Path(dataset_output_path_value))
        for candidate_path in candidate_paths:
            try:
                _assert_path_within_allowed_roots(
                    candidate_path,
                    allowed_root_paths=allowed_roots,
                    context="purge plaintext output candidate",
                )
                if candidate_path.exists():
                    candidate_path.unlink()
            except FileNotFoundError as exc:
                log.warning(
                    "Observed concurrent mutation while removing plaintext output candidate %s after Crypt4GH finalization failure (%s: %s)",
                    candidate_path,
                    exc.__class__.__name__,
                    exc,
                )
            except Exception as exc:
                log.exception(
                    "Failed to remove plaintext output candidate %s after Crypt4GH finalization failure (%s: %s)",
                    candidate_path,
                    exc.__class__.__name__,
                    exc,
                )

        marker_path_value = str(concrete_target.get("encrypted_marker_path", "") or "")
        if marker_path_value:
            marker_path = Path(marker_path_value)
            try:
                _assert_path_within_allowed_roots(
                    marker_path,
                    allowed_root_paths=allowed_roots,
                    context="purge encrypted marker",
                )
                if marker_path.exists():
                    marker_path.unlink()
            except FileNotFoundError as exc:
                log.warning(
                    "Observed concurrent mutation while removing encrypted marker %s after Crypt4GH finalization failure (%s: %s)",
                    marker_path,
                    exc.__class__.__name__,
                    exc,
                )
            except Exception as exc:
                log.exception(
                    "Failed to remove encrypted marker %s after Crypt4GH finalization failure (%s: %s)",
                    marker_path,
                    exc.__class__.__name__,
                    exc,
                )

        extra_files_output_path_value = str(concrete_target.get("extra_files_output_path", "") or "")
        if extra_files_output_path_value:
            extra_files_output_path = Path(extra_files_output_path_value)
            try:
                _assert_path_within_allowed_roots(
                    extra_files_output_path,
                    allowed_root_paths=allowed_roots,
                    context="purge plaintext extra_files candidate",
                )
                if extra_files_output_path.is_symlink():
                    extra_files_output_path.unlink()
                elif extra_files_output_path.exists() and extra_files_output_path.is_dir():
                    shutil.rmtree(extra_files_output_path)
                elif extra_files_output_path.exists():
                    extra_files_output_path.unlink()
            except FileNotFoundError as exc:
                log.warning(
                    "Observed concurrent mutation while removing plaintext extra_files candidate %s after Crypt4GH finalization failure (%s: %s)",
                    extra_files_output_path,
                    exc.__class__.__name__,
                    exc,
                )
            except OSError as exc:
                if isinstance(exc, (NotADirectoryError, IsADirectoryError, FileNotFoundError)) or exc.errno in (
                    errno.ENOTDIR,
                    errno.EISDIR,
                    errno.ENOENT,
                ):
                    log.warning(
                        "Observed concurrent mutation while removing plaintext extra_files candidate %s after Crypt4GH finalization failure (%s: %s)",
                        extra_files_output_path,
                        exc.__class__.__name__,
                        exc,
                    )
                    continue
                log.exception(
                    "Failed to remove plaintext extra_files candidate %s after Crypt4GH finalization failure (%s: %s)",
                    extra_files_output_path,
                    exc.__class__.__name__,
                    exc,
                )
            except Exception as exc:
                log.exception(
                    "Failed to remove plaintext extra_files candidate %s after Crypt4GH finalization failure (%s: %s)",
                    extra_files_output_path,
                    exc.__class__.__name__,
                    exc,
                )

        extra_files_manifest_path_value = str(concrete_target.get("extra_files_manifest_path", "") or "")
        if extra_files_manifest_path_value:
            extra_files_manifest_path = Path(extra_files_manifest_path_value)
            try:
                _assert_path_within_allowed_roots(
                    extra_files_manifest_path,
                    allowed_root_paths=allowed_roots,
                    context="purge extra_files manifest",
                )
                if extra_files_manifest_path.exists():
                    extra_files_manifest_path.unlink()
            except FileNotFoundError as exc:
                log.warning(
                    "Observed concurrent mutation while removing extra_files manifest %s after Crypt4GH finalization failure (%s: %s)",
                    extra_files_manifest_path,
                    exc.__class__.__name__,
                    exc,
                )
            except Exception as exc:
                log.exception(
                    "Failed to remove extra_files manifest %s after Crypt4GH finalization failure (%s: %s)",
                    extra_files_manifest_path,
                    exc.__class__.__name__,
                    exc,
                )


def _iter_unique_existing_output_targets(
    output_targets: Sequence[Mapping[str, Any]],
) -> list[tuple[dict[str, Any], Path]]:
    encrypted_paths: set[str] = set()
    resolved_targets: list[tuple[dict[str, Any], Path]] = []
    for target in output_targets:
        declared_output_path = target.get("output_path")
        if declared_output_path:
            declared_output = Path(str(declared_output_path))
            if not declared_output.exists():
                raise Crypt4GHRemoteExecutionError(f"Crypt4GH declared output path does not exist: {declared_output}")

        for concrete_target in _resolve_output_targets(target):
            allowed_roots = _resolve_allowed_root_paths(concrete_target)
            output_path = Path(concrete_target["output_path"])
            _assert_path_within_allowed_roots(
                output_path,
                allowed_root_paths=allowed_roots,
                context="finalize output_path",
            )

            dataset_output_path_value = str(concrete_target.get("dataset_output_path", "") or "")
            if dataset_output_path_value:
                _assert_path_within_allowed_roots(
                    Path(dataset_output_path_value),
                    allowed_root_paths=allowed_roots,
                    context="finalize dataset_output_path",
                )

            marker_path_value = str(concrete_target.get("encrypted_marker_path", "") or "")
            if marker_path_value:
                _assert_path_within_allowed_roots(
                    Path(marker_path_value),
                    allowed_root_paths=allowed_roots,
                    context="finalize encrypted_marker_path",
                )

            extra_files_output_path_value = str(concrete_target.get("extra_files_output_path", "") or "")
            if extra_files_output_path_value:
                _assert_path_within_allowed_roots(
                    Path(extra_files_output_path_value),
                    allowed_root_paths=allowed_roots,
                    context="finalize extra_files_output_path",
                )

            extra_files_manifest_path_value = str(concrete_target.get("extra_files_manifest_path", "") or "")
            if extra_files_manifest_path_value:
                _assert_path_within_allowed_roots(
                    Path(extra_files_manifest_path_value),
                    allowed_root_paths=allowed_roots,
                    context="finalize extra_files_manifest_path",
                )

            plaintext_path_value = str(concrete_target.get("plaintext_path", "") or "")
            if plaintext_path_value:
                plaintext_roots = _resolve_plaintext_root_paths(concrete_target, fallback_roots=allowed_roots)
                _assert_path_within_allowed_roots(
                    Path(plaintext_path_value),
                    allowed_root_paths=plaintext_roots,
                    context="finalize plaintext_path",
                )

            if not output_path.exists():
                association_name = str(concrete_target.get("association_name", "") or "<unknown>")
                raise Crypt4GHRemoteExecutionError(
                    "Crypt4GH declared output target path is missing before finalization: "
                    f"association={association_name} path={output_path}"
                )

            output_path_key = str(output_path)
            if output_path_key in encrypted_paths:
                continue

            encrypted_paths.add(output_path_key)
            resolved_targets.append((concrete_target, output_path))
    return resolved_targets


def _finalize_output_target(
    *,
    concrete_target: Mapping[str, Any],
    output_path: Path,
    reencryption_service_url: str,
    compute_public_key: str,
    compute_keypair_id: str,
) -> dict[str, Any]:
    plaintext_path = Path(concrete_target["plaintext_path"])
    plaintext_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output_path, plaintext_path)
    dataset_output_path_value = str(concrete_target.get("dataset_output_path", "") or "")
    dataset_output_path = Path(dataset_output_path_value) if dataset_output_path_value else None

    compute_encrypted_path = Path(f"{output_path}.compute.c4gh")
    final_tmp_path = Path(f"{output_path}.c4gh.tmp")
    output_replaced = False
    compute_encrypted_header = ""
    user_encrypted_header = ""
    try:
        _encrypt_plaintext_to_compute_key(
            plaintext_path=plaintext_path,
            compute_encrypted_path=compute_encrypted_path,
            compute_public_key=compute_public_key,
        )
        compute_encrypted_header = base64.b64encode(read_crypt4gh_header(str(compute_encrypted_path))).decode("ascii")
        _rewrite_output_header_to_user_key(
            compute_encrypted_path=compute_encrypted_path,
            final_output_tmp_path=final_tmp_path,
            reencryption_service_url=reencryption_service_url,
            compute_keypair_id=compute_keypair_id,
        )
        os.replace(final_tmp_path, output_path)
        output_replaced = True
        user_encrypted_header = base64.b64encode(read_crypt4gh_header(str(output_path))).decode("ascii")
        _write_output_markers(concrete_target)
    except Exception as exc:
        if not output_replaced and output_path.exists():
            output_path.unlink()
        if not output_replaced and dataset_output_path and dataset_output_path.exists():
            dataset_output_path.unlink()
        raise Crypt4GHRemoteExecutionError(
            f"Failed to finalize encrypted Crypt4GH output at {output_path}: {exc}"
        ) from exc
    finally:
        if compute_encrypted_path.exists():
            compute_encrypted_path.unlink()
        if final_tmp_path.exists():
            final_tmp_path.unlink()

    encrypted_ext = str(concrete_target["encrypted_ext"])
    inner_ext = encrypted_ext[: -len(".c4gh")] if encrypted_ext.endswith(".c4gh") else encrypted_ext
    return {
        "association_name": str(concrete_target.get("association_name", "")),
        "output_path": str(output_path),
        "encrypted_ext": encrypted_ext,
        "metadata": {
            "crypt4gh_header": user_encrypted_header,
            "crypt4gh_compute_header": compute_encrypted_header,
            "crypt4gh_inner_ext": inner_ext,
        },
    }


def _write_output_markers(concrete_target: Mapping[str, Any]) -> None:
    marker_path_value = concrete_target.get("encrypted_marker_path")
    if marker_path_value:
        marker_path = Path(marker_path_value)
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(f"{concrete_target['encrypted_ext']}\n")

    designation = str(concrete_target.get("designation", "") or "")
    discovered_marker_map_path = str(concrete_target.get("discovered_marker_map_path", "") or "")
    if designation and discovered_marker_map_path:
        _write_discovered_designation_marker(
            marker_map_path=Path(discovered_marker_map_path),
            designation=designation,
            encrypted_ext=concrete_target["encrypted_ext"],
        )


def _resolve_output_targets(target: Mapping[str, Any]) -> list[dict[str, Any]]:
    output_path = target.get("output_path")
    if output_path:
        concrete_target = {
            "output_path": str(output_path),
            "plaintext_path": str(target["plaintext_path"]),
            "encrypted_ext": str(target["encrypted_ext"]),
            "encrypted_marker_path": str(target.get("encrypted_marker_path", "")),
            "clear_compute_keypair": bool(target.get("clear_compute_keypair", False)),
            "association_name": str(target.get("association_name", "")),
        }
        dataset_output_path = target.get("dataset_output_path")
        if dataset_output_path:
            concrete_target["dataset_output_path"] = str(dataset_output_path)
        extra_files_output_path = target.get("extra_files_output_path")
        if extra_files_output_path:
            concrete_target["extra_files_output_path"] = str(extra_files_output_path)
        extra_files_manifest_path = target.get("extra_files_manifest_path")
        if extra_files_manifest_path:
            concrete_target["extra_files_manifest_path"] = str(extra_files_manifest_path)
        allowed_root_paths = target.get("allowed_root_paths")
        if isinstance(allowed_root_paths, (list, tuple)):
            concrete_target["allowed_root_paths"] = [str(path) for path in allowed_root_paths if str(path)]
        plaintext_root_paths = target.get("plaintext_root_paths")
        if isinstance(plaintext_root_paths, (list, tuple)):
            concrete_target["plaintext_root_paths"] = [str(path) for path in plaintext_root_paths if str(path)]
        return [concrete_target]

    if target.get("discover_pattern") is not None:
        raise Crypt4GHRemoteExecutionError(
            "Crypt4GH declared output finalization requires explicit output_path targets; "
            "discovered payloads must be finalized via discovery/persistence hooks"
        )

    return []


def _write_discovered_designation_marker(*, marker_map_path: Path, designation: str, encrypted_ext: str) -> None:
    marker_map_path.parent.mkdir(parents=True, exist_ok=True)
    marker_map: dict[str, str] = {}
    if marker_map_path.exists():
        try:
            loaded = json.loads(marker_map_path.read_text())
            if isinstance(loaded, dict):
                marker_map = {str(key): str(value) for key, value in loaded.items()}
        except Exception:
            marker_map = {}
    marker_map[designation] = encrypted_ext
    marker_map_path.write_text(json.dumps(marker_map))


def _finalize_extra_files_payloads(
    *,
    concrete_target: Mapping[str, Any],
    reencryption_service_url: str,
    compute_public_key: str,
    compute_keypair_id: str,
) -> None:
    extra_files_output_path_value = str(concrete_target.get("extra_files_output_path", "") or "")
    if not extra_files_output_path_value:
        return

    extra_files_output_path = Path(extra_files_output_path_value)
    if not extra_files_output_path.exists() or not extra_files_output_path.is_dir():
        return

    extra_files_manifest_path_value = str(concrete_target.get("extra_files_manifest_path", "") or "")
    if not extra_files_manifest_path_value:
        raise Crypt4GHRemoteExecutionError("Crypt4GH extra_files finalization requires an extra_files manifest path")

    extra_files_manifest_path = Path(extra_files_manifest_path_value)
    if extra_files_manifest_path.exists():
        extra_files_manifest_path.unlink()

    base_plaintext_path = Path(str(concrete_target["plaintext_path"]))
    expected_entries: set[str] = set()
    for root, _dirs, files in os.walk(extra_files_output_path):
        root_path = Path(root)
        for file_name in files:
            source_path = root_path / file_name
            relative_path = os.path.relpath(source_path, extra_files_output_path)
            normalized_relative_path = relative_path.replace(os.sep, "/")
            encrypted_relative_path = _encrypted_extra_files_relative_path(relative_path=normalized_relative_path)

            extra_file_target = dict(concrete_target)
            extra_file_target["output_path"] = str(source_path)
            extra_file_target["plaintext_path"] = str(
                base_plaintext_path.parent / "extra_files" / encrypted_relative_path / "plaintext"
            )
            extra_file_target["encrypted_marker_path"] = ""
            extra_file_target.pop("dataset_output_path", None)
            allowed_roots = _resolve_allowed_root_paths(extra_file_target)
            _assert_path_within_allowed_roots(
                source_path,
                allowed_root_paths=allowed_roots,
                context="finalize extra_files payload",
            )

            payload_path = _rename_extra_files_payload_with_suffix_if_needed(
                source_path=source_path,
                extra_files_root=extra_files_output_path,
                encrypted_relative_path=encrypted_relative_path,
                allowed_root_paths=allowed_roots,
            )
            expected_entries.add(encrypted_relative_path)

            extra_file_target["output_path"] = str(payload_path)

            _finalize_output_target(
                concrete_target=extra_file_target,
                output_path=payload_path,
                reencryption_service_url=reencryption_service_url,
                compute_public_key=compute_public_key,
                compute_keypair_id=compute_keypair_id,
            )
            _write_extra_files_manifest_entry(
                manifest_path=extra_files_manifest_path,
                relative_path=encrypted_relative_path,
                encrypted_ext=str(concrete_target["encrypted_ext"]),
            )
            _assert_crypt4gh_payload_header(path=payload_path)

    _assert_extra_files_manifest_complete(
        manifest_path=extra_files_manifest_path,
        expected_entries=expected_entries,
    )


def _write_extra_files_manifest_entry(*, manifest_path: Path, relative_path: str, encrypted_ext: str) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_payload: dict[str, Any] = {"files": {}}
    if manifest_path.exists():
        try:
            loaded_payload = json.loads(manifest_path.read_text())
            if isinstance(loaded_payload, dict):
                manifest_payload = loaded_payload
        except Exception:
            manifest_payload = {"files": {}}

    files_payload = manifest_payload.get("files")
    if not isinstance(files_payload, dict):
        files_payload = {}
        manifest_payload["files"] = files_payload

    files_payload[relative_path] = encrypted_ext
    manifest_path.write_text(json.dumps(manifest_payload))


def _encrypted_extra_files_relative_path(*, relative_path: str) -> str:
    if relative_path.endswith(_CRYPT4GH_FILE_SUFFIX):
        return relative_path
    return f"{relative_path}{_CRYPT4GH_FILE_SUFFIX}"


def _rename_extra_files_payload_with_suffix_if_needed(
    *,
    source_path: Path,
    extra_files_root: Path,
    encrypted_relative_path: str,
    allowed_root_paths: Sequence[Path],
) -> Path:
    encrypted_path = extra_files_root / encrypted_relative_path
    if encrypted_path == source_path:
        return source_path

    _assert_path_within_allowed_roots(
        encrypted_path,
        allowed_root_paths=allowed_root_paths,
        context="finalize extra_files encrypted payload",
    )
    if encrypted_path.exists():
        raise Crypt4GHRemoteExecutionError(
            f"Crypt4GH extra_files encrypted payload already exists: {encrypted_path}"
        )

    encrypted_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.rename(encrypted_path)
    return encrypted_path


def _assert_extra_files_manifest_complete(*, manifest_path: Path, expected_entries: set[str]) -> None:
    if not expected_entries:
        return

    if not manifest_path.exists():
        raise Crypt4GHRemoteExecutionError("Crypt4GH extra_files manifest missing entries")

    try:
        manifest_payload = json.loads(manifest_path.read_text())
    except Exception as exc:
        raise Crypt4GHRemoteExecutionError(f"Crypt4GH extra_files manifest is unreadable: {manifest_path}") from exc

    files_payload = manifest_payload.get("files") if isinstance(manifest_payload, dict) else None
    if not isinstance(files_payload, dict):
        raise Crypt4GHRemoteExecutionError(f"Crypt4GH extra_files manifest has invalid structure: {manifest_path}")

    missing_entries = expected_entries - set(files_payload.keys())
    if missing_entries:
        raise Crypt4GHRemoteExecutionError("Crypt4GH extra_files manifest missing entries")


def _assert_crypt4gh_payload_header(*, path: Path) -> None:
    with path.open("rb") as payload_stream:
        if payload_stream.read(8) != b"crypt4gh":
            raise Crypt4GHRemoteExecutionError(f"Crypt4GH extra_files payload remained plaintext: {path}")


def verify_crypt4gh_pre_success_output_evidence(
    *,
    working_directory: str,
    output_dataset_associations: Sequence[Any],
) -> None:
    marker_dirs = _resolve_pre_success_marker_directories(working_directory=working_directory)
    if not marker_dirs:
        return

    discovered_designations: set[str] = set()
    discovered_parent_output_names: set[str] = set()
    for output_dataset_assoc in output_dataset_associations:
        association_name = getattr(output_dataset_assoc, "name", "")
        designation = _resolve_discovered_designation(association_name)
        if designation:
            discovered_designations.add(designation)

        discovered_parent_output_name = _resolve_discovered_parent_output_name(association_name)
        if discovered_parent_output_name:
            discovered_parent_output_names.add(discovered_parent_output_name)

    dataset_candidates: dict[int, dict[str, Any]] = {}
    for output_dataset_assoc in output_dataset_associations:
        association_name = getattr(output_dataset_assoc, "name", "")
        designation = _resolve_discovered_designation(association_name)
        if not designation and association_name in discovered_parent_output_names:
            continue

        dataset_instance = getattr(output_dataset_assoc, "dataset", None)
        dataset = getattr(dataset_instance, "dataset", None)
        dataset_id = getattr(dataset, "id", None)
        if not isinstance(dataset_id, int):
            continue

        dataset_payload_path = _dataset_payload_path(dataset)
        if not dataset_payload_path:
            continue

        require_payload_marker = not bool(designation)
        candidate = dataset_candidates.get(dataset_id)
        if candidate is None:
            dataset_candidates[dataset_id] = {
                "dataset": dataset,
                "require_payload_marker": require_payload_marker,
                "discovered_designation": designation,
            }
        else:
            candidate["require_payload_marker"] = (
                bool(candidate.get("require_payload_marker", False)) or require_payload_marker
            )
            if designation and not candidate.get("discovered_designation"):
                candidate["discovered_designation"] = designation

    diagnostics: list[str] = []
    for dataset_id in sorted(dataset_candidates):
        candidate = dataset_candidates[dataset_id]
        _verify_payload_header_evidence(
            dataset_id=dataset_id,
            dataset=candidate.get("dataset"),
            diagnostics=diagnostics,
        )
        if bool(candidate.get("require_payload_marker", False)):
            _verify_payload_marker_evidence(marker_dirs=marker_dirs, dataset_id=dataset_id, diagnostics=diagnostics)
        _verify_extra_files_manifest_evidence(
            marker_dirs=marker_dirs,
            dataset_id=dataset_id,
            dataset=candidate.get("dataset"),
            discovered_designation=str(candidate.get("discovered_designation", "") or ""),
            diagnostics=diagnostics,
        )

    _verify_no_residual_plaintext_staging_artifacts(
        working_directory=working_directory,
        diagnostics=diagnostics,
    )

    if discovered_designations:
        _verify_discovered_mapping_evidence(
            marker_dirs=marker_dirs,
            discovered_designations=discovered_designations,
            diagnostics=diagnostics,
        )

    if diagnostics:
        diagnostics_text = "; ".join(diagnostics)
        log.error("Crypt4GH pre-success verifier failed in %s: %s", working_directory, diagnostics_text)
        raise Crypt4GHRemoteExecutionError(f"Crypt4GH pre-success verifier failed: {diagnostics_text}")


def _resolve_pre_success_marker_directories(*, working_directory: str) -> list[Path]:
    working_directory_path = Path(working_directory)
    candidates = [
        working_directory_path / "_c4gh_stage" / "outputs",
        working_directory_path / "working" / "_c4gh_stage" / "outputs",
    ]
    parent_directory = working_directory_path.parent
    if parent_directory != working_directory_path:
        candidates.append(parent_directory / "_c4gh_stage" / "outputs")

    marker_dirs: list[Path] = []
    seen_dirs: set[str] = set()
    for candidate in candidates:
        candidate_key = str(candidate)
        if candidate_key in seen_dirs:
            continue
        seen_dirs.add(candidate_key)
        if candidate.is_dir():
            marker_dirs.append(candidate)
    return marker_dirs


def _resolve_discovered_designation(association_name: Any) -> str:
    if not isinstance(association_name, str) or not association_name.startswith("__new_primary_file_"):
        return ""

    split_name = association_name[len("__new_primary_file_") :].split("|", 1)
    if len(split_name) != 2:
        return ""

    designation = split_name[1]
    if designation.endswith("__"):
        designation = designation[:-2]
    return designation


def _resolve_discovered_parent_output_name(association_name: Any) -> str:
    if not isinstance(association_name, str) or not association_name.startswith("__new_primary_file_"):
        return ""

    split_name = association_name[len("__new_primary_file_") :].split("|", 1)
    if len(split_name) != 2:
        return ""

    return split_name[0]


def _verify_payload_marker_evidence(*, marker_dirs: Sequence[Path], dataset_id: int, diagnostics: list[str]) -> None:
    found_marker = False
    saw_unreadable_marker = False
    saw_invalid_marker = False

    for marker_dir in marker_dirs:
        marker_path = marker_dir / f"ds_{dataset_id}.encrypted"
        if not marker_path.exists():
            continue

        found_marker = True
        try:
            marker_ext = marker_path.read_text().strip()
        except Exception:
            saw_unreadable_marker = True
            continue

        if marker_ext:
            return
        saw_invalid_marker = True

    if not found_marker:
        diagnostics.append(f"payload marker missing for dataset_id={dataset_id}")
    elif saw_invalid_marker:
        diagnostics.append(f"payload marker invalid for dataset_id={dataset_id}")
    elif saw_unreadable_marker:
        diagnostics.append(f"payload marker unreadable for dataset_id={dataset_id}")


def _verify_payload_header_evidence(*, dataset_id: int, dataset: Any, diagnostics: list[str]) -> None:
    dataset_path = _dataset_payload_path(dataset)
    if not dataset_path:
        return

    payload_path = Path(dataset_path)
    if not payload_path.exists():
        diagnostics.append(f"payload path missing for dataset_id={dataset_id}")
        return

    try:
        with payload_path.open("rb") as payload_stream:
            payload_prefix = payload_stream.read(8)
    except Exception:
        diagnostics.append(f"payload unreadable for dataset_id={dataset_id}")
        return

    if payload_prefix != b"crypt4gh":
        diagnostics.append(f"payload remained plaintext for dataset_id={dataset_id}")


def _verify_discovered_mapping_evidence(
    *, marker_dirs: Sequence[Path], discovered_designations: set[str], diagnostics: list[str]
) -> None:
    mapping_paths = [marker_dir / "discovered_designations.json" for marker_dir in marker_dirs]
    existing_paths = [mapping_path for mapping_path in mapping_paths if mapping_path.exists()]
    if not existing_paths:
        for designation in sorted(discovered_designations):
            diagnostics.append(f"discovered-output mapping missing for designation={designation}")
        return

    merged_mapping: dict[str, str] = {}
    saw_unreadable_mapping = False
    saw_invalid_mapping = False
    for mapping_path in existing_paths:
        try:
            loaded_mapping = json.loads(mapping_path.read_text())
        except Exception:
            saw_unreadable_mapping = True
            continue

        if not isinstance(loaded_mapping, dict):
            saw_invalid_mapping = True
            continue

        for key, value in loaded_mapping.items():
            merged_mapping[str(key)] = str(value)

    if not merged_mapping:
        if saw_invalid_mapping:
            diagnostics.append("discovered-output mapping invalid")
            return
        if saw_unreadable_mapping:
            diagnostics.append("discovered-output mapping unreadable")
            return
        for designation in sorted(discovered_designations):
            diagnostics.append(f"discovered-output mapping missing for designation={designation}")
        return

    for designation in sorted(discovered_designations):
        if not any(bool(value) and key == designation for key, value in merged_mapping.items()):
            diagnostics.append(f"discovered-output mapping missing for designation={designation}")


def _verify_extra_files_manifest_evidence(
    *,
    marker_dirs: Sequence[Path],
    dataset_id: int,
    dataset: Any,
    discovered_designation: str,
    diagnostics: list[str],
) -> None:
    dataset_path = _dataset_payload_path(dataset)
    if not dataset_path:
        return

    extra_files_path = Path(dataset_path_to_extra_path(dataset_path))
    if not extra_files_path.exists() or not extra_files_path.is_dir():
        return

    observed_entries: set[str] = set()
    for root, _dirs, files in os.walk(extra_files_path):
        root_path = Path(root)
        for file_name in files:
            source_path = root_path / file_name
            relative_path = os.path.relpath(source_path, extra_files_path)
            observed_entries.add(relative_path.replace(os.sep, "/"))

    manifest_paths = [marker_dir / f"ds_{dataset_id}.extra_files_manifest.json" for marker_dir in marker_dirs]
    discovered_designation = discovered_designation or _resolve_discovered_designation(
        getattr(dataset, "designation", "")
    )
    if discovered_designation:
        designation_token = _safe_discovered_designation_token(discovered_designation)
        manifest_paths.extend(
            marker_dir / f"designation_{designation_token}.extra_files_manifest.json" for marker_dir in marker_dirs
        )

    existing_paths: list[Path] = []
    seen_manifest_paths: set[str] = set()
    for manifest_path in manifest_paths:
        manifest_path_key = str(manifest_path)
        if manifest_path_key in seen_manifest_paths:
            continue
        seen_manifest_paths.add(manifest_path_key)
        if manifest_path.exists():
            existing_paths.append(manifest_path)
    if not existing_paths:
        diagnostics.append(f"extra_files manifest missing for dataset_id={dataset_id}")
        return

    saw_unreadable_manifest = False
    saw_invalid_manifest = False
    saw_missing_entries = False
    complete_manifest_found = False
    expected_payload_entries: set[str] = set()
    for manifest_path in existing_paths:
        try:
            manifest_payload = json.loads(manifest_path.read_text())
        except Exception:
            saw_unreadable_manifest = True
            continue

        files_payload = manifest_payload.get("files") if isinstance(manifest_payload, dict) else None
        if not isinstance(files_payload, dict):
            saw_invalid_manifest = True
            continue

        manifest_entries = set(files_payload.keys())
        if not observed_entries:
            if manifest_entries:
                complete_manifest_found = True
                expected_payload_entries = manifest_entries
                break
            continue

        missing_entries = observed_entries - manifest_entries
        if not missing_entries:
            complete_manifest_found = True
            expected_payload_entries = manifest_entries
            break
        saw_missing_entries = True

    if complete_manifest_found:
        _verify_extra_files_payload_header_evidence(
            dataset_id=dataset_id,
            extra_files_path=extra_files_path,
            expected_entries=expected_payload_entries,
            diagnostics=diagnostics,
        )
        return

    if saw_missing_entries:
        diagnostics.append(f"extra_files manifest missing entries for dataset_id={dataset_id}")
    elif saw_invalid_manifest:
        diagnostics.append(f"extra_files manifest invalid for dataset_id={dataset_id}")
    elif saw_unreadable_manifest:
        diagnostics.append(f"extra_files manifest unreadable for dataset_id={dataset_id}")


def _verify_no_residual_plaintext_staging_artifacts(*, working_directory: str, diagnostics: list[str]) -> None:
    crypt_root = Path(working_directory) / "_crypt"
    plaintext_roots = (crypt_root / "outputs", crypt_root / "inputs")

    for plaintext_root in plaintext_roots:
        if not plaintext_root.exists() or not plaintext_root.is_dir():
            continue

        for root, _dirs, files in os.walk(plaintext_root):
            root_path = Path(root)
            for file_name in files:
                if file_name != "plaintext":
                    continue

                leaked_path = root_path / file_name
                diagnostics.append(f"plaintext staging artifact remained at path={leaked_path}")


def _verify_extra_files_payload_header_evidence(
    *,
    dataset_id: int,
    extra_files_path: Path,
    expected_entries: set[str],
    diagnostics: list[str],
) -> None:
    for relative_path in sorted(expected_entries):
        payload_path = extra_files_path / relative_path
        if payload_path.is_symlink():
            diagnostics.append(f"extra_files payload symlink for dataset_id={dataset_id} path={relative_path}")
            continue

        if not payload_path.exists():
            diagnostics.append(f"extra_files payload missing for dataset_id={dataset_id} path={relative_path}")
            continue

        try:
            with payload_path.open("rb") as payload_stream:
                payload_prefix = payload_stream.read(8)
        except Exception:
            diagnostics.append(f"extra_files payload unreadable for dataset_id={dataset_id} path={relative_path}")
            continue

        if payload_prefix != b"crypt4gh":
            diagnostics.append(f"extra_files payload remained plaintext for dataset_id={dataset_id} path={relative_path}")


def _safe_discovered_designation_token(designation: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", designation).strip("._-")
    return sanitized or "designation"


def _resolve_allowed_root_paths(concrete_target: Mapping[str, Any]) -> tuple[Path, ...]:
    configured_paths = concrete_target.get("allowed_root_paths")
    resolved_paths: list[Path] = []

    if isinstance(configured_paths, (list, tuple)):
        for path_value in configured_paths:
            try:
                candidate = Path(str(path_value)).resolve(strict=False)
            except Exception:
                continue
            resolved_paths.append(candidate)

    if not resolved_paths:
        default_paths = [
            concrete_target.get("output_path"),
            concrete_target.get("dataset_output_path"),
            concrete_target.get("extra_files_output_path"),
            concrete_target.get("extra_files_manifest_path"),
            concrete_target.get("encrypted_marker_path"),
            concrete_target.get("plaintext_path"),
        ]
        for path_value in default_paths:
            if not path_value:
                continue
            try:
                resolved_paths.append(Path(str(path_value)).resolve(strict=False).parent)
            except Exception:
                continue

    deduped_paths: list[Path] = []
    seen: set[str] = set()
    for resolved_path in resolved_paths:
        key = str(resolved_path)
        if key in seen:
            continue
        seen.add(key)
        deduped_paths.append(resolved_path)

    return tuple(deduped_paths)


def _resolve_plaintext_root_paths(
    concrete_target: Mapping[str, Any], *, fallback_roots: Sequence[Path]
) -> tuple[Path, ...]:
    configured_paths = concrete_target.get("plaintext_root_paths")
    resolved_paths: list[Path] = []

    if isinstance(configured_paths, (list, tuple)):
        for path_value in configured_paths:
            try:
                candidate = Path(str(path_value)).resolve(strict=False)
            except Exception:
                continue
            resolved_paths.append(candidate)

    if not resolved_paths:
        resolved_paths = list(fallback_roots)

    deduped_paths: list[Path] = []
    seen: set[str] = set()
    for resolved_path in resolved_paths:
        key = str(resolved_path)
        if key in seen:
            continue
        seen.add(key)
        deduped_paths.append(resolved_path)

    return tuple(deduped_paths)


def _assert_path_within_allowed_roots(path: Path, *, allowed_root_paths: Sequence[Path], context: str) -> None:
    if not allowed_root_paths:
        return

    resolved_path = path.resolve(strict=False)
    for root_path in allowed_root_paths:
        try:
            resolved_path.relative_to(root_path)
            return
        except ValueError:
            continue

    raise Crypt4GHRemoteExecutionError(f"Crypt4GH {context} path is outside allowed roots: {path}")


def _dataset_payload_path(dataset: Any) -> str:
    get_file_name = getattr(dataset, "get_file_name", None)
    if not callable(get_file_name):
        return ""

    try:
        return str(get_file_name(sync_cache=False) or "")
    except TypeError:
        return str(get_file_name() or "")


def build_crypt4gh_cleanup_wrapped_command(
    *, tool_command: str, cleanup_command: str, postrun_command: str = ""
) -> str:
    """Wrap tool command with postrun and cleanup steps that preserve failures."""

    postrun_command = postrun_command.strip()
    cleanup_command = cleanup_command.strip()
    if not cleanup_command:
        if not postrun_command:
            return tool_command
        lines = _build_tool_and_postrun_shell_lines(
            tool_command=tool_command,
            postrun_command=postrun_command,
            include_exit_checks=True,
        )
        return "\n".join(lines)

    lines = _build_tool_and_postrun_shell_lines(
        tool_command=tool_command,
        postrun_command=postrun_command,
        include_exit_checks=False,
    )
    marker_line = (
        f'    echo "{CRYPT4GH_CLEANUP_FAILED_MARKER}: cleanup failed with exit code '
        '${_CRYPT4GH_CLEANUP_EXIT}" >&2'
    )
    lines.extend(
        [
            "if (",
            cleanup_command,
            "); then",
            "    _CRYPT4GH_CLEANUP_EXIT=0",
            "else",
            "    _CRYPT4GH_CLEANUP_EXIT=$?",
            marker_line,
            "fi",
            "if [ $_CRYPT4GH_TOOL_EXIT -ne 0 ]; then",
            "    exit $_CRYPT4GH_TOOL_EXIT",
            "fi",
            "if [ $_CRYPT4GH_POSTRUN_EXIT -ne 0 ]; then",
            "    exit $_CRYPT4GH_POSTRUN_EXIT",
            "fi",
        ]
    )
    return "\n".join(lines)


def _build_tool_and_postrun_shell_lines(
    *, tool_command: str, postrun_command: str, include_exit_checks: bool
) -> list[str]:
    lines = [
        "if (",
        tool_command,
        "); then",
        "    _CRYPT4GH_TOOL_EXIT=0",
        "else",
        "    _CRYPT4GH_TOOL_EXIT=$?",
        "fi",
    ]
    if postrun_command:
        lines.extend(
            [
                "if [ $_CRYPT4GH_TOOL_EXIT -eq 0 ]; then",
                "    if (",
                postrun_command,
                "    ); then",
                "        _CRYPT4GH_POSTRUN_EXIT=0",
                "    else",
                "        _CRYPT4GH_POSTRUN_EXIT=$?",
                "    fi",
                "else",
                "    _CRYPT4GH_POSTRUN_EXIT=0",
                "fi",
            ]
        )
    else:
        lines.append("_CRYPT4GH_POSTRUN_EXIT=0")

    if include_exit_checks:
        lines.extend(
            [
                "if [ $_CRYPT4GH_TOOL_EXIT -ne 0 ]; then",
                "    exit $_CRYPT4GH_TOOL_EXIT",
                "fi",
                "if [ $_CRYPT4GH_POSTRUN_EXIT -ne 0 ]; then",
                "    exit $_CRYPT4GH_POSTRUN_EXIT",
                "fi",
            ]
        )
    return lines


def _encrypt_plaintext_to_compute_key(
    *,
    plaintext_path: Path,
    compute_encrypted_path: Path,
    compute_public_key: str,
) -> None:
    recipient_key = _parse_crypt4gh_public_key(compute_public_key)
    ephemeral_private_key = X25519PrivateKey.generate().private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with plaintext_path.open("rb") as plaintext_stream, compute_encrypted_path.open("wb") as encrypted_stream:
        crypt4gh.lib.encrypt([(0, ephemeral_private_key, recipient_key)], plaintext_stream, encrypted_stream)


def _rewrite_output_header_to_user_key(
    *,
    compute_encrypted_path: Path,
    final_output_tmp_path: Path,
    reencryption_service_url: str,
    compute_keypair_id: str,
) -> None:
    with compute_encrypted_path.open("rb") as encrypted_stream:
        list(crypt4gh.header.parse(encrypted_stream))
        header_length = encrypted_stream.tell()
        encrypted_stream.seek(0)
        encrypted_header = encrypted_stream.read(header_length)

    recrypted_header = _recrypt_header_to_user_key(
        reencryption_service_url=reencryption_service_url,
        crypt4gh_header=base64.b64encode(encrypted_header).decode("ascii"),
        compute_keypair_id=compute_keypair_id,
    )
    recrypted_header_bytes = _decode_header(recrypted_header)
    _header_length(recrypted_header_bytes)

    with compute_encrypted_path.open("rb") as encrypted_stream, final_output_tmp_path.open("wb") as final_stream:
        encrypted_stream.seek(header_length)
        final_stream.write(recrypted_header_bytes)
        shutil.copyfileobj(encrypted_stream, final_stream)


def _recrypt_header_to_user_key(
    *,
    reencryption_service_url: str,
    crypt4gh_header: str,
    compute_keypair_id: str,
) -> str:
    endpoint = f"{reencryption_service_url.rstrip('/')}/recrypt_header_to_user_key"
    payload = {
        "crypt4gh_header": crypt4gh_header,
        "crypt4gh_compute_keypair_id": compute_keypair_id,
    }
    try:
        response = _post_reencryption_json(
            reencryption_service_url=reencryption_service_url,
            endpoint=endpoint,
            payload=payload,
        )
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise Crypt4GHRemoteExecutionError(f"Failed to contact compute-side recryptor B at {endpoint}: {exc}") from exc

    if not response.ok:
        raise Crypt4GHRemoteExecutionError(
            f"Compute-side recryptor B returned HTTP {response.status_code} for {endpoint}: "
            f"{_summarize_http_error_response(response)}"
        )

    try:
        response_json = response.json_payload
        if not isinstance(response_json, dict):
            raise ValueError("Response body is not a JSON object")
        return cast(str, response_json["crypt4gh_header"])
    except (ValueError, KeyError, TypeError) as exc:
        raise Crypt4GHRemoteExecutionError(
            "Compute-side recryptor B returned an invalid /recrypt_header_to_user_key payload"
        ) from exc


def _parse_crypt4gh_public_key(public_key_pem: str) -> bytes:
    lines = [line.strip() for line in public_key_pem.splitlines() if line.strip()]
    if len(lines) < 3:
        raise Crypt4GHRemoteExecutionError("Invalid CRYPT4GH public key payload")
    try:
        return base64.b64decode("".join(lines[1:-1]))
    except ValueError as exc:
        raise Crypt4GHRemoteExecutionError("Invalid CRYPT4GH public key payload") from exc


def _summarize_http_error_response(response: _ReencryptionHttpResponse) -> str:
    detail: Any = None
    payload = response.json_payload

    if isinstance(payload, dict):
        for key in ("detail", "message", "error"):
            candidate = payload.get(key)
            if candidate:
                detail = candidate
                break
        if detail is None and payload:
            detail = payload
    elif isinstance(payload, list):
        detail = payload
    elif isinstance(payload, str):
        detail = payload
    else:
        detail = response.text

    summary = re.sub(r"\s+", " ", str(detail or "")).strip()
    if not summary:
        return "no error details provided"
    if len(summary) > 200:
        return f"{summary[:200]}..."
    return summary


def _decrypt_recrypted_input(
    *,
    source_dataset_path: Path,
    source_header: str,
    recrypted_header: str,
    plaintext_path: Path,
    job_private_key: bytes,
) -> None:
    source_header_bytes = _decode_header(source_header)
    recrypted_header_bytes = _decode_header(recrypted_header)
    source_header_length = _header_length(source_header_bytes)
    try:
        with source_dataset_path.open("rb") as source_stream, plaintext_path.open("wb") as plaintext_stream:
            source_stream.seek(source_header_length)
            staged_stream = _HeaderThenBodyStream(header_bytes=recrypted_header_bytes, body_stream=source_stream)
            crypt4gh.lib.decrypt([(0, job_private_key, None)], staged_stream, plaintext_stream)
    except OSError as exc:
        raise Crypt4GHRemoteExecutionError(
            f"Failed to read or materialize Crypt4GH input for source dataset {source_dataset_path}: {exc}"
        ) from exc
    except Exception as exc:
        raise Crypt4GHRemoteExecutionError(f"Failed to decrypt staged Crypt4GH input {source_dataset_path}") from exc


def _decode_header(encoded_header: str) -> bytes:
    try:
        return base64.b64decode(encoded_header)
    except (ValueError, TypeError) as exc:
        raise Crypt4GHRemoteExecutionError("Invalid base64-encoded Crypt4GH header") from exc


def _header_length(header_bytes: bytes) -> int:
    try:
        stream = io.BytesIO(header_bytes)
        list(crypt4gh.header.parse(stream))
        return stream.tell()
    except Exception as exc:
        raise Crypt4GHRemoteExecutionError("Invalid Crypt4GH header payload") from exc


def _assert_minimum_ttl(*, datasets: Sequence[DatasetInstance], minimum_ttl: timedelta, now: datetime) -> None:
    for dataset in datasets:
        metadata = getattr(dataset, "metadata", None)
        expires_raw = getattr(metadata, "crypt4gh_compute_keypair_expiration_date", None)
        if not expires_raw:
            raise Crypt4GHRemoteExecutionError(
                "Crypt4GH key metadata missing; minimum TTL cannot be validated before remote call"
            )

        expires_at = _parse_expiration(expires_raw)
        ttl_left = expires_at - now
        if ttl_left <= minimum_ttl:
            raise Crypt4GHRemoteExecutionError(
                "Crypt4GH compute key violates minimum TTL requirement before remote call"
            )


def _parse_expiration(expires_raw: datetime | str) -> datetime:
    if isinstance(expires_raw, datetime):
        expires_at = expires_raw
    elif isinstance(expires_raw, str):
        try:
            expires_at = isoparse(expires_raw)
        except ValueError as exc:
            raise Crypt4GHRemoteExecutionError("Invalid Crypt4GH compute key expiration timestamp") from exc
    else:
        raise Crypt4GHRemoteExecutionError("Invalid Crypt4GH compute key expiration timestamp")

    if expires_at.tzinfo is None:
        raise Crypt4GHRemoteExecutionError("Invalid Crypt4GH compute key expiration timestamp - timezone is lacking")

    return expires_at


def _assert_key_valid_for_output_finalization(*, compute_keypair_expiration_date: str, now: datetime) -> None:
    expires_at = _parse_expiration(compute_keypair_expiration_date)
    if expires_at <= now:
        raise Crypt4GHRemoteExecutionError("Crypt4GH compute key expired before output finalization; failing closed")

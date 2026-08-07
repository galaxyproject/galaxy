"""Crypt4GH header parsing, file-extension helpers, and validation.

This module provides utilities for detecting Crypt4GH files, validating
their binary headers, managing the ``inner_ext.c4gh`` wrapper-extension
convention used by the Galaxy datatype registry, and validating compute
metadata / job readiness for Crypt4GH-wrapped datasets.

Security invariants
-------------------
* Functions in this module **never** decrypt payload data or handle
  private keys.  They only read and validate the *public* header
  portion of a Crypt4GH file.
* Header bytes returned by :func:`read_crypt4gh_header` are the raw
  public header; callers are responsible for redacting them before
  logging.
* Error messages are crafted to be actionable without leaking header
  bytes or other sensitive material.
"""

from __future__ import annotations

import os
import shutil
import struct
from datetime import datetime
from pathlib import Path
from re import fullmatch
from typing import (
    IO,
    TYPE_CHECKING,
)

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.job_execution.compute_environment import dataset_path_to_extra_path

if TYPE_CHECKING:
    from galaxy.model import (
        DatasetInstance,
        Job,
    )

# --- Constants -------------------------------------------------------------

CRYPT4GH_MAGIC = b"crypt4gh"
CRYPT4GH_VERSION = 1
CRYPT4GH_FILE_EXT = "c4gh"
CRYPT4GH_SUFFIX = f".{CRYPT4GH_FILE_EXT}"

#: Sentinel emitted to stderr by the compute-side shell wrapper when
#: plaintext cleanup fails.  Scanned by the host-side job finisher.
CRYPT4GH_CLEANUP_FAILED_MARKER = "CRYPT4GH_PLAINTEXT_CLEANUP_FAILED"

# Struct format for the 16-byte prelude: magic (8s) + version (I) + packet_count (I)
_PRELUDE_FORMAT = "<8sII"
_PRELUDE_SIZE = struct.calcsize(_PRELUDE_FORMAT)


# --- Extension helpers ------------------------------------------------------


def _is_generic_crypt4gh_file_ext(file_ext: str) -> bool:
    """Return True for bare wrapper extensions like ``c4gh``, ``crypt4gh``."""
    return fullmatch(r"c[^.]*4gh", file_ext) is not None


def _unwrap_crypt4gh_suffix(value: str) -> str | None:
    """Strip a trailing ``.c4gh`` (or similar) suffix and return the inner stem."""
    if not value:
        return None
    stem, sep, suffix = value.rpartition(".")
    if not sep:
        return None
    if _is_generic_crypt4gh_file_ext(suffix):
        return stem
    return None


def is_crypt4gh_file_ext(file_ext: str) -> bool:
    """Return True if *file_ext* is a Crypt4GH wrapper (generic or typed)."""
    return _is_generic_crypt4gh_file_ext(file_ext) or _unwrap_crypt4gh_suffix(file_ext) is not None


def wrap_crypt4gh_file_ext(file_ext: str) -> str:
    """Append the Crypt4GH suffix to *file_ext* unless it is already wrapped."""
    if is_crypt4gh_file_ext(file_ext):
        return file_ext
    return f"{file_ext}{CRYPT4GH_SUFFIX}"


def unwrap_crypt4gh_file_ext(file_ext: str) -> str | None:
    """Return the inner extension of a typed wrapper, or None for generic/invalid."""
    if _is_generic_crypt4gh_file_ext(file_ext):
        return None
    return _unwrap_crypt4gh_suffix(file_ext)


def infer_crypt4gh_inner_file_ext(filename: str, registry) -> str | None:
    """Try to infer the inner datatype extension from *filename* via the registry."""
    inner_filename = _unwrap_crypt4gh_suffix(filename) or filename
    datatype = registry.get_datatype_from_filename(inner_filename)
    if datatype and datatype.file_ext not in ("data", "auto"):
        return datatype.file_ext
    return None


def infer_crypt4gh_file_ext(filename: str, registry, requested_ext: str = "auto") -> str:
    """Determine the best Crypt4GH wrapper extension for *filename*.

    Priority:
    1. Inner type inferred from filename via the registry.
    2. Wrap the user-requested extension (if not ``auto``).
    3. Fall back to the generic ``c4gh``.
    """
    inner_file_ext = infer_crypt4gh_inner_file_ext(filename, registry)
    if inner_file_ext is not None:
        return wrap_crypt4gh_file_ext(inner_file_ext)
    if requested_ext != "auto":
        return wrap_crypt4gh_file_ext(requested_ext)
    return CRYPT4GH_FILE_EXT


def preserve_crypt4gh_inner_file_ext(
    guessed_ext: str,
    current_ext: str | None = None,
    metadata_inner_ext: str | None = None,
) -> str:
    """Preserve a known wrapper extension during datatype re-detection.

    Re-detection from object-store paths often loses the original filename
    suffix and can only sniff a generic ``c*4gh`` wrapper.  When that
    happens, keep the more specific wrapper if we already know it from the
    dataset extension or from computed ``crypt4gh_inner_ext`` metadata.
    """
    if not _is_generic_crypt4gh_file_ext(guessed_ext):
        return guessed_ext

    if current_ext and not _is_generic_crypt4gh_file_ext(current_ext) and is_crypt4gh_file_ext(current_ext):
        return current_ext

    if (
        metadata_inner_ext
        and metadata_inner_ext
        not in (
            "auto",
            "data",
            "binary",
            "txt",
        )
        and not _is_generic_crypt4gh_file_ext(metadata_inner_ext)
    ):
        return wrap_crypt4gh_file_ext(metadata_inner_ext)

    return guessed_ext


# --- Header reading / validation -------------------------------------------


def read_crypt4gh_header(stream_or_path: str | IO[bytes]) -> bytes:
    """Read and validate the Crypt4GH header from a file path or stream.

    Returns the raw header bytes (prelude + all header packets).

    Raises :class:`ValueError` if the file is not a valid Crypt4GH file
    or if the header is truncated.
    """
    close_stream = False
    stream: IO[bytes]
    if isinstance(stream_or_path, str):
        stream = open(stream_or_path, "rb")
        close_stream = True
    else:
        stream = stream_or_path

    try:
        prelude = stream.read(_PRELUDE_SIZE)
        if len(prelude) != _PRELUDE_SIZE:
            raise ValueError("Header too small")

        magic, version, packet_count = struct.unpack(_PRELUDE_FORMAT, prelude)
        if magic != CRYPT4GH_MAGIC:
            raise ValueError("Not a Crypt4GH file")
        if version != CRYPT4GH_VERSION:
            raise ValueError(f"Unsupported Crypt4GH version {version}")

        header = bytearray(prelude)
        for _ in range(packet_count):
            packet_len_bytes = stream.read(4)
            if len(packet_len_bytes) != 4:
                raise ValueError("Truncated header packet length")
            packet_len = int.from_bytes(packet_len_bytes, byteorder="little")
            if packet_len < 4:
                raise ValueError(f"Invalid packet length {packet_len}")
            packet_data = stream.read(packet_len - 4)
            if len(packet_data) != packet_len - 4:
                raise ValueError("Truncated header packet data")
            header.extend(packet_len_bytes)
            header.extend(packet_data)

        return bytes(header)
    finally:
        if close_stream:
            stream.close()


def check_crypt4gh(file_path: str) -> bool:
    """Return True if *file_path* is a valid Crypt4GH file (header check only)."""
    try:
        read_crypt4gh_header(file_path)
        return True
    except Exception:
        return False


def cleanup_crypt4gh_plaintext_artifacts(*, working_directory: str) -> None:
    """Delete staged Crypt4GH plaintext input and output directories.

    Removes ``_crypt/inputs`` and ``_crypt/outputs`` under *working_directory*.
    """
    crypt_root = Path(working_directory) / "_crypt"
    for child_name in ("inputs", "outputs"):
        child_path = crypt_root / child_name
        if child_path.exists():
            shutil.rmtree(child_path)


def cleanup_crypt4gh_plaintext_outputs(*, output_paths: list[str]) -> None:
    """Remove plaintext (un-encrypted) output files left by a failed postrun.

    For each path in *output_paths*, if the file exists and does **not** begin
    with the Crypt4GH magic bytes, it is deleted.  If a sibling ``_files``
    directory exists (extra-files), its non-``.c4gh`` contents are also removed.

    This ensures that no unencrypted dataset remains on the compute node when
    the tool or postrun script fails.
    """
    for output_path_str in output_paths:
        output_path = Path(output_path_str)
        if not output_path.exists():
            continue

        # Remove the primary output file if it is not encrypted.
        if output_path.is_file():
            try:
                with output_path.open("rb") as fh:
                    magic = fh.read(len(CRYPT4GH_MAGIC))
                if magic != CRYPT4GH_MAGIC:
                    output_path.unlink()
            except OSError:
                pass

        # Remove plaintext files in the sibling extra-files directory.
        extra_files_path = Path(dataset_path_to_extra_path(str(output_path)))
        if extra_files_path.exists() and extra_files_path.is_dir():
            for root, _dirs, files in os.walk(extra_files_path):
                root_path = Path(root)
                for file_name in files:
                    if file_name.endswith(CRYPT4GH_SUFFIX):
                        continue
                    file_path = root_path / file_name
                    try:
                        with file_path.open("rb") as fh:
                            magic = fh.read(len(CRYPT4GH_MAGIC))
                        if magic != CRYPT4GH_MAGIC:
                            file_path.unlink()
                    except OSError:
                        pass


__all__ = (
    "assert_crypt4gh_job_readiness",
    "check_crypt4gh",
    "cleanup_crypt4gh_plaintext_artifacts",
    "cleanup_crypt4gh_plaintext_outputs",
    "CRYPT4GH_CLEANUP_FAILED_MARKER",
    "CRYPT4GH_COMPUTE_METADATA_KEYS",
    "CRYPT4GH_FILE_EXT",
    "CRYPT4GH_MAGIC",
    "CRYPT4GH_SUFFIX",
    "CRYPT4GH_VERSION",
    "infer_crypt4gh_file_ext",
    "infer_crypt4gh_inner_file_ext",
    "is_crypt4gh_file_ext",
    "preserve_crypt4gh_inner_file_ext",
    "read_crypt4gh_header",
    "unwrap_crypt4gh_file_ext",
    "validate_crypt4gh_compute_metadata",
    "validate_crypt4gh_keypair_expiration",
    "wrap_crypt4gh_file_ext",
)


# --- Compute metadata validation (dataset-level) ---------------------------

#: Metadata field names that can be set by the recrypt action.
CRYPT4GH_COMPUTE_METADATA_KEYS = frozenset(
    {
        "crypt4gh_compute_header",
        "crypt4gh_compute_keypair_id",
        "crypt4gh_compute_keypair_expiration_date",
    }
)


def validate_crypt4gh_compute_metadata(
    dataset_assoc: DatasetInstance,
    key: str,
    val: object,
) -> None:
    """Validate a single Crypt4GH compute metadata update.

    Called from :class:`DatasetAssociationDeserializer.deserialize_metadatum`
    before the value is persisted.

    Only Crypt4GH-wrapped datasets may receive compute metadata.  The
    keypair expiration date must be a valid ISO 8601 string that is in
    the future.

    :raises RequestParameterInvalidException: if the dataset is not
        Crypt4GH-wrapped, is in an active job, or the expiration date
        is invalid or expired.
    """
    if key not in CRYPT4GH_COMPUTE_METADATA_KEYS:
        return

    ext = dataset_assoc.ext or ""
    if not is_crypt4gh_file_ext(ext):
        raise RequestParameterInvalidException(
            f"Crypt4GH compute metadata '{key}' can only be set on Crypt4GH-wrapped datasets, not '{ext}'."
        )

    if not dataset_assoc.ok_to_edit_metadata():
        raise RequestParameterInvalidException(
            "Dataset metadata could not be updated because it is used as input or output of a running job."
        )

    if key == "crypt4gh_compute_keypair_expiration_date" and val:
        validate_crypt4gh_keypair_expiration(str(val))


def validate_crypt4gh_keypair_expiration(val: str) -> None:
    """Ensure the keypair expiration date is valid ISO 8601 and in the future.

    :raises RequestParameterInvalidException: if the value is not
        parseable as ISO 8601 or is not in the future.
    """
    try:
        expiration = datetime.fromisoformat(val)
    except (ValueError, TypeError):
        raise RequestParameterInvalidException(
            f"Invalid Crypt4GH keypair expiration date '{val}': expected ISO 8601 format."
        )
    if expiration.tzinfo is not None:
        now = datetime.now(expiration.tzinfo)
    else:
        now = datetime.now()
    if expiration <= now:
        raise RequestParameterInvalidException("Crypt4GH keypair expiration date must be in the future.")


# --- Job readiness guard (job-level) ---------------------------------------


def assert_crypt4gh_job_readiness(job: Job) -> list[str]:
    """Validate that every Crypt4GH input dataset is ready for compute.

    Returns a list of human-readable error messages (empty if all
    Crypt4GH inputs are ready).  Each error message is actionable and
    tells the user to use the recrypt action to fix the problem.

    This function does **not** raise; the caller is responsible for
    failing the job when errors are returned.
    """
    input_associations = [
        *list(job.input_datasets or []),
        *list(job.input_library_datasets or []),
    ]
    if not input_associations:
        return []

    errors: list[str] = []
    for assoc in input_associations:
        dataset = getattr(assoc, "dataset", None)
        if dataset is None:
            continue
        ext = getattr(dataset, "ext", "") or ""
        if not is_crypt4gh_file_ext(ext):
            continue

        input_name = getattr(assoc, "name", "") or "<unnamed>"
        errors.extend(_validate_single_crypt4gh_input(input_name, dataset))

    return errors


def _validate_single_crypt4gh_input(input_name: str, dataset: DatasetInstance) -> list[str]:
    """Validate one Crypt4GH input dataset and return a list of errors."""
    metadata = dataset.metadata
    compute_header = getattr(metadata, "crypt4gh_compute_header", None)
    keypair_id = getattr(metadata, "crypt4gh_compute_keypair_id", None)
    expiration_str = getattr(metadata, "crypt4gh_compute_keypair_expiration_date", None)

    if not compute_header:
        return [
            f"Input '{input_name}': missing crypt4gh_compute_header metadata. ",
            "Use the recrypt action to prepare this dataset for compute.",
        ]
    if not keypair_id:
        return [
            f"Input '{input_name}': missing crypt4gh_compute_keypair_id metadata. ",
            "Use the recrypt action to prepare this dataset for compute.",
        ]
    if not expiration_str:
        return [
            f"Input '{input_name}': missing crypt4gh_compute_keypair_expiration_date metadata. ",
            "Use the recrypt action to prepare this dataset for compute.",
        ]

    return _validate_keypair_not_expired(input_name, str(expiration_str))


def _validate_keypair_not_expired(input_name: str, expiration_str: str) -> list[str]:
    """Validate that the keypair expiration date is valid and not expired."""
    try:
        expiration = datetime.fromisoformat(expiration_str)
    except (ValueError, TypeError):
        return [
            f"Input '{input_name}': invalid crypt4gh_compute_keypair_expiration_date ",
            f"'{expiration_str}': expected ISO 8601 format.",
        ]

    if expiration.tzinfo is not None:
        now = datetime.now(expiration.tzinfo)
    else:
        now = datetime.now()

    if expiration <= now:
        return [
            f"Input '{input_name}': Crypt4GH keypair has expired ",
            f"(expiration: {expiration_str}). Use the recrypt action to renew.",
        ]

    return []

"""Crypt4GH header parsing and file-extension helpers.

This module provides strict, dependency-free utilities for detecting
Crypt4GH files, validating their binary headers, and managing the
``inner_ext.c4gh`` wrapper-extension convention used by the Galaxy
datatype registry.

Security invariants
-------------------
* Functions in this module **never** decrypt payload data or handle
  private keys.  They only read and validate the *public* header
  portion of a Crypt4GH file.
* Header bytes returned by :func:`read_crypt4gh_header` are the raw
  public header; callers are responsible for redacting them before
  logging.
"""

import struct
from re import fullmatch
from typing import IO

# --- Constants -------------------------------------------------------------

CRYPT4GH_MAGIC = b"crypt4gh"
CRYPT4GH_VERSION = 1
CRYPT4GH_FILE_EXT = "c4gh"
CRYPT4GH_SUFFIX = f".{CRYPT4GH_FILE_EXT}"

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
    if datatype and datatype.file_ext not in ("data", "binary", "txt", "auto"):
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


__all__ = (
    "check_crypt4gh",
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
    "wrap_crypt4gh_file_ext",
)

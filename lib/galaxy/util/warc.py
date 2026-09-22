"""WARC (Web ARChive) record header check.

Single home for WARC byte-level knowledge, shared by the upload content
gate (:mod:`galaxy.util.checkers`) and the ``warc.gz`` datatype sniffer.
"""

WARC_VERSION_PREFIXES = (b"WARC/1.0", b"WARC/1.1")
WARC_REQUIRED_FIELDS = (b"WARC-Type:", b"WARC-Record-ID:", b"Content-Length:")
WARC_HEADER_LIMIT = 8192


def is_warc_chunk(chunk: bytes | None) -> bool:
    """True if chunk opens with a WARC record header.

    The version line must be at byte 0 and every required field must start
    a line of the first header block (up to the first blank line, max 8K,
    so payload bytes past the blank line never match). Truncated headers
    and indented fields do not match.
    """
    if not chunk:
        return False
    header = chunk[:WARC_HEADER_LIMIT]
    if not header.startswith(WARC_VERSION_PREFIXES):
        return False
    header_block = header.split(b"\r\n\r\n", 1)[0].split(b"\n\n", 1)[0]
    lines = header_block.splitlines()
    if len(lines) < 2:
        return False
    seen = set()
    for line in lines[1:]:
        for field in WARC_REQUIRED_FIELDS:
            if line.startswith(field):
                seen.add(field)
    return len(seen) == len(WARC_REQUIRED_FIELDS)


__all__ = (
    "WARC_HEADER_LIMIT",
    "WARC_REQUIRED_FIELDS",
    "WARC_VERSION_PREFIXES",
    "is_warc_chunk",
)

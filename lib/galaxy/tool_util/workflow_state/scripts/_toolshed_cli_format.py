"""Shared table formatting helpers for the Tool Shed gxwf subcommands."""

import re
from typing import (
    List,
    Sequence,
)

_WS_RE = re.compile(r"\s+")


def truncate(text: str, max_len: int) -> str:
    flat = _WS_RE.sub(" ", text).strip()
    return f"{flat[: max_len - 1]}…" if len(flat) > max_len else flat


def format_table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [max(len(col), *(len(r[i]) for r in rows)) if rows else len(col) for i, col in enumerate(header)]

    def fmt(cells: Sequence[str]) -> str:
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells)).rstrip()

    lines: List[str] = [fmt(header), fmt(["-" * w for w in widths])]
    lines.extend(fmt(r) for r in rows)
    return "\n".join(lines)

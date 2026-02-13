"""File I/O utilities for agent evaluation tests."""
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

log = logging.getLogger(__name__)


def atomic_json_write(path: Path, data: Dict[str, Any]) -> None:
    """Atomically write JSON to file.

    Uses temp file + atomic rename pattern to prevent partial writes
    that could corrupt data if disk fills or process is interrupted.

    Args:
        path: Target file path
        data: Dictionary to serialize as JSON

    Raises:
        OSError: If unable to write file
        ValueError: If data cannot be serialized to JSON
    """
    path = Path(path)  # Ensure it's a Path object

    # Write to temp file in same directory (ensures same filesystem for atomic rename)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )

    try:
        # Write JSON to temp file
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic rename (POSIX guarantee)
        os.replace(temp_path, path)
        log.debug(f"Atomically wrote JSON to {path}")

    except Exception as e:
        # Clean up temp file on failure
        try:
            os.unlink(temp_path)
        except OSError:
            pass  # Already deleted or doesn't exist
        log.exception(f"Failed to write JSON to {path}: {e}")
        raise

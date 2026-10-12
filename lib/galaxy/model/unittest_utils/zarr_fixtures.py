"""Small Zarr stores written to disk, e.g. to serve as remote stores for deferred datasets."""

import json
from pathlib import Path
from typing import Any

ZARR_V3_ARRAY_METADATA: dict[str, Any] = {
    "zarr_format": 3,
    "node_type": "array",
    "shape": [3],
    "data_type": "uint8",
    "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": [2]}},
    "chunk_key_encoding": {"name": "default", "configuration": {"separator": "/"}},
    "fill_value": 0,
    "codecs": [{"name": "bytes"}],
}
ZARR_V2_ARRAY_METADATA: dict[str, Any] = {
    "zarr_format": 2,
    "shape": [3],
    "chunks": [2],
    "dtype": "|u1",
    "fill_value": 0,
    "compressor": None,
}


def _write_json(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content))


def write_zarr_v3_store(root: Path, consolidated: bool = True, array_name: str = "arr") -> list[str]:
    """Write a group holding an array named ``array_name`` with two chunks, of which only the first is stored.

    Return the paths of the files written, relative to ``root``.
    """
    group: dict[str, Any] = {"zarr_format": 3, "node_type": "group", "attributes": {}}
    if consolidated:
        group["consolidated_metadata"] = {
            "kind": "inline",
            "must_understand": False,
            "metadata": {array_name: ZARR_V3_ARRAY_METADATA},
        }
    _write_json(root / "zarr.json", group)
    _write_json(root / array_name / "zarr.json", ZARR_V3_ARRAY_METADATA)
    # The second chunk only holds the fill value, so it is not stored.
    (root / array_name / "c").mkdir()
    (root / array_name / "c" / "0").write_bytes(b"\x01\x02")
    return [f"{array_name}/c/0", f"{array_name}/zarr.json", "zarr.json"]


def write_zarr_v2_store(root: Path, array_name: str = "arr") -> list[str]:
    """Write a consolidated group holding an array named ``array_name`` with two chunks, only the first stored.

    Return the paths of the files written, relative to ``root``.
    """
    _write_json(root / ".zgroup", {"zarr_format": 2})
    _write_json(root / array_name / ".zarray", ZARR_V2_ARRAY_METADATA)
    _write_json(
        root / ".zmetadata",
        {
            "zarr_consolidated_format": 1,
            "metadata": {".zgroup": {"zarr_format": 2}, f"{array_name}/.zarray": ZARR_V2_ARRAY_METADATA},
        },
    )
    # The second chunk only holds the fill value, so it is not stored.
    (root / array_name / "0").write_bytes(b"\x01\x02")
    return [".zgroup", ".zmetadata", f"{array_name}/.zarray", f"{array_name}/0"]

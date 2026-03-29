#!/usr/bin/env python3
"""Generate the cache_golden/ directory by fetching real tools from the ToolShed.

Fetches ParsedTool data from the ToolShed API for each entry in cache_golden.yaml,
writes the JSON files and index to cache_golden/. Run this when the manifest
changes or when you want to refresh against the current ToolShed API.

Usage:
    PYTHONPATH=lib python generate_golden_cache.py
"""

import hashlib
import json
import os
import shutil

import yaml

from galaxy.tool_util.workflow_state.toolshed_tool_info import (
    _cache_key,
    parse_toolshed_tool_id,
    ToolShedGetToolInfo,
)

SUPPORTED_FORMAT_VERSION = 1

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(SCRIPT_DIR, "cache_golden.yaml")
GOLDEN_DIR = os.path.join(SCRIPT_DIR, "cache_golden")


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_checksums(golden_dir, manifest_path):
    checksums = {
        "manifest_sha256": _sha256_file(manifest_path),
        "files": {},
    }
    for fname in sorted(os.listdir(golden_dir)):
        if not fname.endswith(".json") or fname == "checksums.json":
            continue
        checksums["files"][fname] = _sha256_file(os.path.join(golden_dir, fname))
    out_path = os.path.join(golden_dir, "checksums.json")
    with open(out_path, "w") as f:
        json.dump(checksums, f, indent=2)
        f.write("\n")
    return out_path


def main():
    with open(MANIFEST_PATH) as f:
        manifest = yaml.safe_load(f)

    version = manifest.get("format_version")
    assert (
        version == SUPPORTED_FORMAT_VERSION
    ), f"Manifest format_version {version} != expected {SUPPORTED_FORMAT_VERSION}"

    # Clean and recreate
    if os.path.exists(GOLDEN_DIR):
        shutil.rmtree(GOLDEN_DIR)
    os.makedirs(GOLDEN_DIR)

    # Fetch into golden dir — ToolShedGetToolInfo will cache API responses as JSON files
    tool_info = ToolShedGetToolInfo(cache_dir=GOLDEN_DIR)

    # Toolshed tools — fetched via TRS API
    for entry in manifest.get("toolshed_tools", []):
        tool_id = entry["tool_id"]
        version = entry["expected_version"]
        result = tool_info.get_tool_info(tool_id, version)
        assert result is not None, f"Fetch failed: {tool_id}"

        parsed = parse_toolshed_tool_id(tool_id)
        key = _cache_key(parsed[0], parsed[1], version)
        print(f"  {tool_id}")
        print(f"    name={result.name!r}, inputs={len(result.inputs)}, outputs={len(result.outputs)}")
        print(f"    cache_key={key}")

        if "expected_cache_key" in entry:
            assert key == entry["expected_cache_key"], f"Key mismatch: {key} != {entry['expected_cache_key']}"

    # Stock tools — fetched via stock tool resolution (tool_id as TRS ID)
    for entry in manifest.get("stock_tools", []):
        tool_id = entry["tool_id"]
        version = entry["tool_version"]
        result = tool_info.get_tool_info(tool_id, version)
        assert result is not None, f"Fetch failed: {tool_id}"

        key = _cache_key(entry["default_toolshed_url"], tool_id, version)
        print(f"  {tool_id}")
        print(f"    name={result.name!r}, inputs={len(result.inputs)}, outputs={len(result.outputs)}")
        print(f"    cache_key={key}")

        if "expected_cache_key" in entry:
            assert key == entry["expected_cache_key"], f"Key mismatch: {key} != {entry['expected_cache_key']}"

    # Emit checksums for cross-language sync validation
    checksums_path = _write_checksums(GOLDEN_DIR, MANIFEST_PATH)

    n_files = len([f for f in os.listdir(GOLDEN_DIR) if f.endswith(".json") and f != "checksums.json"])
    print(f"\nGolden cache written to {GOLDEN_DIR}/")
    print(f"  {n_files} JSON files (including index.json)")
    print(f"  checksums: {checksums_path}")


if __name__ == "__main__":
    main()

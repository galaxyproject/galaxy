"""Shared fixtures for tool source store unit tests."""

import os
import subprocess
import sys
import time
from types import SimpleNamespace
from typing import cast

import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.search import ToolSearchTuning


@pytest.fixture
def index_entry():
    def _make(id, version=None, **kwargs):
        return ToolIndexEntry(id=id, version=version, **kwargs)

    return _make


@pytest.fixture
def tool_index(index_entry):
    def _make(*entries):
        index = ToolIndex()
        for entry in entries:
            index.add_entry(entry)
        return index

    return _make


@pytest.fixture
def search_config():
    """Build a real tuning-compatible config without patching from_config."""

    def _make(tuning: ToolSearchTuning, index_dir: str | None = None) -> GalaxyAppConfiguration:
        return cast(
            GalaxyAppConfiguration,
            SimpleNamespace(
                tool_id_boost=tuning.id_boost,
                tool_name_boost=tuning.name_boost,
                tool_name_exact_multiplier=tuning.name_exact_multiplier,
                tool_stub_boost=tuning.stub_boost,
                tool_section_boost=tuning.section_boost,
                tool_description_boost=tuning.description_boost,
                tool_label_boost=tuning.label_boost,
                tool_ngram_minsize=tuning.ngram_minsize,
                tool_ngram_maxsize=tuning.ngram_maxsize,
                tool_enable_ngram_search=tuning.enable_ngram_search,
                tool_ngram_factor=tuning.ngram_factor,
                tool_help_boost=tuning.help_boost,
                index_tool_help=tuning.index_tool_help,
                tool_help_bm25f_k1=tuning.help_bm25f_k1,
                tool_search_index_dir=index_dir,
            ),
        )

    return _make


@pytest.fixture
def run_processes_together(tmp_path):
    """Run ``script`` once per argument list, releasing all processes at once.

    ``script`` gets ``ready go *args``: it creates ``ready`` once set up, then
    waits for ``go`` to exist. Fails unless every process exits 0.
    """

    def _run(script: str, args_per_process: list[list[str]]) -> None:
        go = tmp_path / "go"
        ready_files = [tmp_path / f"ready-{i}" for i in range(len(args_per_process))]
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
        processes = [
            subprocess.Popen(
                [sys.executable, "-c", script, str(ready), str(go), *args],
                env=env,
                stderr=subprocess.PIPE,
                text=True,
            )
            for ready, args in zip(ready_files, args_per_process)
        ]
        try:
            deadline = time.monotonic() + 120
            while not all(ready.exists() for ready in ready_files):
                assert all(p.poll() is None for p in processes), "a process exited before the start signal"
                assert time.monotonic() < deadline, "processes did not start"
                time.sleep(0.01)
            go.touch()
            errors = [p.communicate(timeout=120)[1] for p in processes]
        finally:
            for p in processes:
                p.kill()
        assert [p.returncode for p in processes] == [0] * len(processes), "\n".join(errors)

    return _run

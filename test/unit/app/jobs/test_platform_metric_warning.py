"""The warning of the job wrapper when a job ran on another platform than its destination requests."""

import logging
from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

from galaxy.jobs import MinimalJobWrapper


def _collect(metrics, requested, caplog):
    wrapper = SimpleNamespace(
        job_id=7,
        platform=requested,
        working_directory="/nonexistent",
        app=SimpleNamespace(job_metrics=SimpleNamespace(collect_properties=lambda *a: metrics)),
    )
    has_metrics = SimpleNamespace(
        get_job=lambda: SimpleNamespace(destination_id="aarch64_dest"), add_metric=lambda *a: None
    )
    with caplog.at_level(logging.WARNING, logger="galaxy.jobs"):
        MinimalJobWrapper._collect_metrics(cast(Any, wrapper), has_metrics)


def test_platform_mismatch_warns(caplog):
    _collect({"core": {"platform": "linux-64"}}, "linux-aarch64", caplog)
    assert "Job 7 ran on platform linux-64" in caplog.text
    assert "aarch64_dest" in caplog.text and "linux-aarch64" in caplog.text


def test_platform_match_or_unset_is_quiet(caplog):
    _collect({"core": {"platform": "linux-64"}}, "linux-64", caplog)
    _collect({"core": {"platform": "linux-64"}}, None, caplog)
    _collect({"core": {}}, "linux-64", caplog)
    assert caplog.text == ""

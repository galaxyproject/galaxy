"""Distribute tests across CI shards without splitting up test classes.

An integration test class boots a Galaxy instance in ``setUpClass``, so a class split
across shards makes every one of them pay that startup. Whole classes are kept together
and packed into shards longest-first, weighted by recorded durations, which balances
shards by cost rather than by name.
"""

import json
import os
from collections import defaultdict
from typing import (
    Any,
    NamedTuple,
)

import pytest

DURATIONS_ENV_VAR = "GALAXY_TEST_SHARD_DURATIONS"
# Per-group seconds measured from a CI run, as {"module::Class": seconds}. Only affects
# balance, never correctness: unknown groups get DEFAULT_GROUP_SECONDS. Regenerate from a
# full unsharded run with --structured_data_report_file, summing each test's setup, call
# and teardown into its group_key(). GALAXY_TEST_SHARD_DURATIONS overrides the path.
DEFAULT_DURATIONS_FILE = os.path.join(os.path.dirname(__file__), "shard_durations.json")
# What to assume a group costs when we have no measurement for it. Integration classes
# are startup-dominated, so an unknown group is much closer to one startup than to zero.
DEFAULT_GROUP_SECONDS = 40.0


class ShardGroup(NamedTuple):
    """Tests that share a Galaxy instance, and therefore must share a shard."""

    key: str
    items: list[Any]
    seconds: float


def group_key(item) -> str:
    """Identify the instance an item belongs to.

    Class for class-based tests, module for those taking a module-scoped instance
    fixture, and the file for items with no module at all.
    """
    module = getattr(item, "module", None)
    if module is None:
        return item.nodeid.split("::")[0]
    cls = getattr(item, "cls", None)
    if cls is not None:
        return f"{module.__name__}::{cls.__name__}"
    return module.__name__


def load_durations(path: str | None = None) -> dict[str, float]:
    """Load recorded per-group durations, falling back to an empty mapping."""
    path = path or os.environ.get(DURATIONS_ENV_VAR) or DEFAULT_DURATIONS_FILE
    try:
        with open(path) as fh:
            return {key: float(seconds) for key, seconds in json.load(fh).items()}
    except (OSError, ValueError):
        return {}


def build_groups(items: list[Any], durations: dict[str, float]) -> list[ShardGroup]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for item in items:
        grouped[group_key(item)].append(item)
    return [
        ShardGroup(key, group_items, durations.get(key, DEFAULT_GROUP_SECONDS)) for key, group_items in grouped.items()
    ]


def assign_groups_to_shards(groups: list[ShardGroup], num_shards: int) -> list[list[ShardGroup]]:
    """Pack groups into shards longest-first, always onto the shard with the least work.

    Greedy bin-packing. Ties break on group key: every shard runs this independently and
    the assignments must agree, or tests get dropped or duplicated.
    """
    shards: list[list[ShardGroup]] = [[] for _ in range(num_shards)]
    loads = [0.0] * num_shards
    for group in sorted(groups, key=lambda g: (-g.seconds, g.key)):
        target = min(range(num_shards), key=lambda index: (loads[index], index))
        shards[target].append(group)
        loads[target] += group.seconds
    return shards


def select_shard(items: list[Any], shard_id: int, num_shards: int, durations: dict[str, float]) -> list[Any]:
    groups = build_groups(items, durations)
    assigned = assign_groups_to_shards(groups, num_shards)[shard_id]
    selected = []
    for group in sorted(assigned, key=lambda g: g.key):
        selected.extend(group.items)
    return selected


def pytest_configure(config) -> None:
    """Take over sharding from pytest-shard, reusing its command line options."""
    shard_plugin = config.pluginmanager.get_plugin("pytest-shard")
    if shard_plugin is not None:
        config.pluginmanager.unregister(shard_plugin)


def pytest_report_collectionfinish(config, items) -> str | None:
    """Report which groups this shard runs."""
    num_shards = config.getoption("num_shards", default=1)
    if num_shards <= 1:
        return None
    groups = sorted({group_key(item) for item in items})
    shard_id = config.getoption("shard_id", default=0)
    return f"Running {len(items)} items from {len(groups)} groups in shard {shard_id}: {', '.join(groups)}"


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items: list[Any]) -> None:
    num_shards = config.getoption("num_shards", default=1)
    shard_id = config.getoption("shard_id", default=0)
    if num_shards <= 1:
        return
    if shard_id >= num_shards:
        raise ValueError(f"shard_id = {shard_id} must be less than num_shards = {num_shards}")
    items[:] = select_shard(items, shard_id, num_shards, load_durations())

import sys
from pathlib import Path

galaxy_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(galaxy_root / "lib"))

from galaxy.tools.source_store.populator import (
    DEFAULT_STORE_NAME,
    whoosh_dir_for_store,
)


def test_default_store_maps_to_store_default_subdir():
    # Backwards-compat: LazyToolBox._get_search_index has been reading from
    assert (
        whoosh_dir_for_store("/var/galaxy/tool_search", DEFAULT_STORE_NAME) == "/var/galaxy/tool_search/_store_default"
    )


def test_named_store_gets_named_subdir():
    assert whoosh_dir_for_store("/var/galaxy/tool_search", "cvmfs_mirror") == "/var/galaxy/tool_search/cvmfs_mirror"


def test_none_or_empty_base_yields_none():
    assert whoosh_dir_for_store(None, DEFAULT_STORE_NAME) is None
    assert whoosh_dir_for_store("", DEFAULT_STORE_NAME) is None

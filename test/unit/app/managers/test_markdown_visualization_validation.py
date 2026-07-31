"""Warn-only validation of visualization blocks in Galaxy markdown (save path)."""

import logging
import os
from typing import cast

from galaxy.exceptions import ObjectNotFound
from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.markdown_util import validate_visualization_blocks
from galaxy.visualization.plugins import config_parser
from galaxy.visualization.plugins.registry import VisualizationsRegistry

GALAXY_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *([os.pardir] * 4)))
IGV_DIR = os.path.join(GALAXY_ROOT, "config", "plugins", "visualizations", "igv")


def _igv_plugin():
    registry = VisualizationsRegistry.__new__(VisualizationsRegistry)
    registry.config_parser = config_parser.PluginConfigParser()
    return registry._load_plugin(IGV_DIR)


class _Registry:
    def __init__(self, plugins):
        self._plugins = plugins

    def get_plugin(self, name):
        if name not in self._plugins:
            raise ObjectNotFound(name)
        return self._plugins[name]


class _Trans:
    def __init__(self, registry):
        self.app = type("App", (), {"visualizations_registry": registry})()


def _as_trans(registry) -> ProvidesAppContext:
    # validate_visualization_blocks only reaches trans.app.visualizations_registry.
    return cast(ProvidesAppContext, _Trans(registry))


def _trans() -> ProvidesAppContext:
    return _as_trans(_Registry({"igv": _igv_plugin()}))


def _block(config: str) -> str:
    return f"intro\n\n```visualization\n{config}\n```\n\noutro\n"


def _warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def test_valid_config_produces_no_warning(caplog):
    with caplog.at_level(logging.WARNING):
        validate_visualization_blocks(
            _trans(), _block("visualization_name: igv\ndataset_id: abc\nsettings:\n  locus: chr1\n")
        )
    assert _warnings(caplog) == []


def test_json_block_also_validates(caplog):
    with caplog.at_level(logging.WARNING):
        validate_visualization_blocks(_trans(), _block('{"visualization_name": "igv", "settings": {"locus": "x"}}'))
    assert _warnings(caplog) == []


def test_bad_select_value_warns(caplog):
    with caplog.at_level(logging.WARNING):
        validate_visualization_blocks(
            _trans(), _block("visualization_name: igv\ntracks:\n  - type: not-a-track-type\n")
        )
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert "igv" in warnings[0]


def test_unknown_setting_key_warns(caplog):
    with caplog.at_level(logging.WARNING):
        validate_visualization_blocks(_trans(), _block("visualization_name: igv\nsettings:\n  bogus: 1\n"))
    assert len(_warnings(caplog)) == 1


def test_unknown_visualization_warns(caplog):
    with caplog.at_level(logging.WARNING):
        validate_visualization_blocks(_trans(), _block("visualization_name: does_not_exist\n"))
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert "does_not_exist" in warnings[0]


def test_block_without_name_is_ignored(caplog):
    with caplog.at_level(logging.WARNING):
        validate_visualization_blocks(_trans(), _block("settings:\n  locus: chr1\n"))
    assert _warnings(caplog) == []


def test_no_registry_is_a_noop(caplog):
    with caplog.at_level(logging.WARNING):
        validate_visualization_blocks(_as_trans(None), _block("visualization_name: igv\nsettings:\n  bogus: 1\n"))
    assert _warnings(caplog) == []

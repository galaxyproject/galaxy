"""Warn-only validation of visualization blocks in Galaxy markdown (save path)."""

import logging
from types import SimpleNamespace
from typing import cast
from xml.etree.ElementTree import fromstring

from galaxy.exceptions import ObjectNotFound
from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.markdown_util import validate_visualization_blocks
from galaxy.visualization.parameters import input_models_for_visualization

# An IGV-shaped plugin declaration, inlined so the test does not depend on the
# shipped igv plugin (installed at build time, absent from the unit-test checkout).
IGV_XML = """
<visualization name="igv">
    <settings>
        <input><name>locus</name><type>text</type><value>all</value></input>
    </settings>
    <tracks>
        <input><name>type</name><type>select</type><value>auto</value>
            <data>
                <data><label>Auto</label><value>auto</value></data>
                <data><label>Annotation</label><value>annotation</value></data>
            </data>
        </input>
    </tracks>
</visualization>
"""


def _igv_plugin():
    bundle = input_models_for_visualization(fromstring(IGV_XML))
    return SimpleNamespace(parameter_bundle=bundle)


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

"""Tests for :mod:`galaxy.visualization.parameters`."""

import os
from xml.etree.ElementTree import fromstring

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.visualization.parameters import (
    BooleanParameterModel,
    ConditionalParameterModel,
    create_request_model,
    DataColumnParameterModel,
    DataParameterModel,
    input_models_for_visualization,
    input_models_for_visualization_path,
    IntegerParameterModel,
    SelectParameterModel,
    TextParameterModel,
    VisualizationState,
)
from galaxy.visualization.parameters.factory import VisualizationParameterParsingException

GALAXY_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir))
IGV_XML = os.path.join(GALAXY_ROOT, "config", "plugins", "visualizations", "igv", "static", "igv.xml")


def bundle_from(settings="", tracks=""):
    xml = f"<visualization name='t'><settings>{settings}</settings><tracks>{tracks}</tracks></visualization>"
    return input_models_for_visualization(fromstring(xml))


def validate(bundle, state):
    VisualizationState(state).validate(bundle)


# --- parsing -----------------------------------------------------------------


def test_parses_leaf_types():
    bundle = bundle_from(settings="""
        <input><name>a</name><type>text</type><value>x</value></input>
        <input><name>b</name><type>integer</type><min>1</min><max>9</max></input>
        <input><name>c</name><type>boolean</type><value>true</value></input>
        <input><name>d</name><type>color</type></input>
        <input><name>e</name><type>data</type><extension>bam,bed</extension></input>
        <input><name>f</name><type>data_column</type><is_number>true</is_number></input>
        """)
    by_name = {p.name: p for p in bundle.settings}
    assert isinstance(by_name["a"], TextParameterModel) and by_name["a"].value == "x"
    assert isinstance(by_name["b"], IntegerParameterModel) and (by_name["b"].min, by_name["b"].max) == (1, 9)
    assert isinstance(by_name["c"], BooleanParameterModel) and by_name["c"].value is True
    assert isinstance(by_name["e"], DataParameterModel) and by_name["e"].extension == "bam,bed"
    assert isinstance(by_name["f"], DataColumnParameterModel) and by_name["f"].is_number is True


def test_select_options_and_default():
    bundle = bundle_from(settings="""
        <input><name>mode</name><type>select</type><value>b</value>
            <data>
                <data><label>A</label><value>a</value></data>
                <data><label>B</label><value>b</value></data>
            </data>
        </input>
        """)
    select = bundle.settings[0]
    assert isinstance(select, SelectParameterModel)
    assert [o.value for o in select.options] == ["a", "b"]
    assert select.value == "b"


def test_string_type_is_alias_for_text():
    bundle = bundle_from(settings="<input><name>s</name><type>string</type><value>1</value></input>")
    assert isinstance(bundle.settings[0], TextParameterModel)


def test_unknown_type_raises():
    with pytest.raises(VisualizationParameterParsingException):
        bundle_from(settings="<input><name>x</name><type>nonsense</type></input>")


def test_missing_name_raises():
    with pytest.raises(VisualizationParameterParsingException):
        bundle_from(settings="<input><type>text</type></input>")


def test_requires_value_metadata():
    bundle = bundle_from(settings="""
        <input><name>needs</name><type>data</type></input>
        <input><name>has_default</name><type>text</type><value>x</value></input>
        <input><name>opt</name><type>data</type><optional>true</optional></input>
        <input><name>empty_default</name><type>text</type><value></value></input>
        """)
    by_name = {p.name: p for p in bundle.settings}
    assert by_name["needs"].requires_value is True
    assert by_name["has_default"].requires_value is False
    assert by_name["opt"].requires_value is False
    # a present-but-empty <value> is a real default, so not required
    assert by_name["empty_default"].requires_value is False


# --- validation --------------------------------------------------------------


def test_type_and_choice_validation():
    bundle = bundle_from(settings="""
        <input><name>label</name><type>text</type></input>
        <input><name>count</name><type>integer</type><min>0</min><max>10</max></input>
        <input><name>mode</name><type>select</type>
            <data><data><label>A</label><value>a</value></data>
                  <data><label>B</label><value>b</value></data></data>
        </input>
        """)
    validate(bundle, {"settings": {"label": "hi", "count": 5, "mode": "a"}})
    with pytest.raises(RequestParameterInvalidException):
        validate(bundle, {"settings": {"label": 123}})  # wrong type
    with pytest.raises(RequestParameterInvalidException):
        validate(bundle, {"settings": {"count": 99}})  # out of range
    with pytest.raises(RequestParameterInvalidException):
        validate(bundle, {"settings": {"mode": "z"}})  # bad choice


def test_presence_is_lenient():
    bundle = bundle_from(settings="<input><name>required_looking</name><type>data</type></input>")
    # no default, not optional, yet omission is allowed (client fills defaults, binding elsewhere)
    validate(bundle, {})
    validate(bundle, {"settings": {}})


def test_settings_closed_tracks_open_meta_allowed():
    bundle = bundle_from(
        settings="<input><name>known</name><type>text</type></input>",
        tracks="<input><name>color</name><type>color</type></input>",
    )
    with pytest.raises(RequestParameterInvalidException):
        validate(bundle, {"settings": {"unknown": 1}})  # settings is closed
    validate(bundle, {"tracks": [{"color": "#fff", "binding_meta": "ok"}]})  # tracks stays open
    validate(bundle, {"height": 400, "visualization_name": "t", "dataset_id": "x"})  # top-level extras


def test_tracks_is_a_repeat():
    bundle = bundle_from(tracks="<input><name>label</name><type>text</type></input>")
    validate(bundle, {"tracks": [{"label": "one"}, {"label": "two"}]})
    with pytest.raises(RequestParameterInvalidException):
        validate(bundle, {"tracks": [{"label": 5}]})  # wrong type inside a track


# --- conditionals ------------------------------------------------------------

CONDITIONAL = """
<input><name>source</name><type>conditional</type>
    <test_param><name>origin</name><type>select</type><value>remote</value>
        <data><data><label>Remote</label><value>remote</value></data>
              <data><label>History</label><value>history</value></data></data>
    </test_param>
    <cases>
        <cases><value>remote</value><inputs>
            <inputs><name>url</name><type>text</type></inputs>
        </inputs></cases>
        <cases><value>history</value><inputs>
            <inputs><name>dataset</name><type>data</type></inputs>
        </inputs></cases>
    </cases>
</input>
"""


def test_conditional_parsing():
    bundle = bundle_from(settings=CONDITIONAL)
    cond = bundle.settings[0]
    assert isinstance(cond, ConditionalParameterModel)
    assert isinstance(cond.test_parameter, SelectParameterModel)
    assert [w.value for w in cond.whens] == ["remote", "history"]


def test_conditional_validation():
    bundle = bundle_from(settings=CONDITIONAL)
    validate(bundle, {"settings": {"source": {"origin": "remote", "url": "http://x"}}})
    validate(bundle, {"settings": {"source": {"origin": "history", "dataset": "d1"}}})
    with pytest.raises(RequestParameterInvalidException):
        validate(bundle, {"settings": {"source": {"origin": "bogus"}}})  # bad discriminator


def test_nested_conditional_rejected():
    nested = """
    <input><name>outer</name><type>conditional</type>
        <test_param><name>t</name><type>select</type>
            <data><data><label>X</label><value>x</value></data></data>
        </test_param>
        <cases><cases><value>x</value><inputs>
            <inputs><name>inner</name><type>conditional</type>
                <test_param><name>t2</name><type>select</type>
                    <data><data><label>Y</label><value>y</value></data></data>
                </test_param>
                <cases><cases><value>y</value><inputs></inputs></cases></cases>
            </inputs>
        </inputs></cases></cases>
    </input>
    """
    with pytest.raises(VisualizationParameterParsingException):
        bundle_from(settings=nested)


# --- real plugin integration -------------------------------------------------


def test_real_igv_plugin():
    bundle = input_models_for_visualization_path(IGV_XML)
    assert [p.name for p in bundle.settings] == ["locus", "source"]
    assert isinstance(bundle.settings[1], ConditionalParameterModel)
    track_names = [p.name for p in bundle.tracks]
    assert "urlDataset" in track_names and "type" in track_names
    # a realistic embed config validates
    validate(
        bundle,
        {
            "visualization_name": "igv",
            "dataset_id": "abc",
            "settings": {"locus": "chr1:1-100", "source": {"origin": "igv", "genome": "hg38"}},
            "tracks": [{"urlDataset": "d1", "type": "annotation", "displayMode": "EXPANDED", "color": "#ff0000"}],
        },
    )
    # a bad track select choice is rejected
    with pytest.raises(RequestParameterInvalidException):
        validate(bundle, {"tracks": [{"type": "not-a-track-type"}]})


def test_create_request_model_is_stable():
    bundle = bundle_from(settings="<input><name>a</name><type>text</type></input>")
    model = create_request_model(bundle)
    assert set(model.model_fields) == {"settings", "tracks"}

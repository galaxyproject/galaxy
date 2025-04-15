import sys
from string import Template

import lxml.etree as ET
import pytest
from pydantic import ValidationError

from galaxy.tool_util.verify.codegen import galaxy_xsd_path
from galaxy.tool_util.verify.parse import assertion_xml_els_to_models
from galaxy.tool_util_models.assertions import assertion_list
from galaxy.util.commands import shell
from galaxy.util.unittest_utils import skip_unless_executable

valid_assertions = [
    {"that": "has_size", "size": "5G"},
    {"that": "has_size", "size": 1},
    {"that": "has_size", "size": "5Mi"},
    {"that": "has_text", "text": "JBrowseDefaultMainPage"},
    {"that": "has_line", "line": "'>Wildtype Staphylococcus aureus strain WT.'"},
    {"that": "has_n_columns", "n": 2},
    {"that": "is_valid_xml"},
    {"that": "has_element_with_path", "path": "//el"},
    {"that": "has_n_elements_with_path", "path": "//el", "n": 4},
    {"that": "element_text_matches", "expression": "foob[a]r", "path": "//el"},
    {"that": "element_text_is", "text": "foobar", "path": "//el"},
    {
        "that": "xml_element",
        "path": "./elem/more[2]",
        "children": [{"that": "has_text_matching", "expression": "foo$"}],
    },
    {"that": "xml_element", "path": "./elem/more[2]"},
    {"that": "element_text", "path": "./elem/more[2]", "children": [{"that": "has_text", "text": "foo"}]},
    {"that": "has_json_property_with_value", "property": "foobar", "value": "'6'"},
    {"that": "has_json_property_with_text", "property": "foobar", "text": "cowdog"},
    {"that": "has_archive_member", "path": ".*/my-file.txt"},
    {"that": "has_archive_member", "path": ".*/my-file.txt", "children": [{"that": "has_text", "text": "1235abc"}]},
    {"that": "has_image_width", "width": 560},
    {"that": "has_image_width", "width": 560, "delta": 490},
    {"that": "has_image_height", "height": 560, "delta": 490},
    {"that": "has_image_height", "min": 45, "max": 90},
    {"that": "has_image_channels", "channels": 3},
    {"that": "has_image_channels", "channels": 3, "delta": 1},
    {"that": "has_image_channels", "min": 1, "max": 4},
    {"that": "has_image_channels", "min": 1, "max": 4, "negate": True},
    {"that": "has_image_mean_intensity", "mean_intensity": 3.4},
    {"that": "has_image_mean_intensity", "mean_intensity": 3.4, "eps": 0.2},
    {"that": "has_image_mean_intensity", "mean_intensity": 3.4, "eps": 0.2, "channel": 1},
    {"that": "has_image_mean_intensity", "min": 0.4, "max": 0.6, "channel": 1},
    {"that": "has_image_center_of_mass", "center_of_mass": "511.07, 223.34"},
    {"that": "has_image_center_of_mass", "center_of_mass": "511.07, 223.34", "channel": 1},
    {"that": "has_image_center_of_mass", "center_of_mass": "511.07, 223.34", "channel": 1, "eps": 0.2},
    {"that": "has_image_n_labels", "n": 85},
    {"that": "has_image_n_labels", "labels": [1, 3, 4]},
    {"that": "has_image_n_labels", "n": 9, "exclude_labels": [1, 3, 4]},
    {"that": "has_image_n_labels", "n": 9, "exclude_labels": [1, 3, 4], "negate": True},
    {"that": "has_image_mean_object_size", "mean_object_size": 9, "exclude_labels": [1, 3, 4]},
    {"that": "has_image_mean_object_size", "mean_object_size": 9, "labels": [1, 3, 4]},
    {"that": "has_image_mean_object_size", "mean_object_size": 9, "channel": 1, "eps": 0.2},
    {"that": "has_json_property_with_value", "property": "skipped_columns", "value": "[1, 3, 5]"},
    {"that": "has_json_property_with_text", "property": "color", "text": "red"},
    {"that": "has_n_columns", "n": 30},
    {"that": "has_n_columns", "n": 30, "delta": 4},
    {"that": "has_n_columns", "n": 30, "delta": 4, "sep": " ", "comment": "####"},
]

valid_xml_assertions = [
    """<has_size value="5G" />""",
    """<has_size size="5G" />""",
    """<has_size size="5G" />""",
    """<has_text text="JBrowseDefaultMainPage" />""",
    """<has_line line="'>Wildtype Staphylococcus aureus strain WT.'" />""",
    """<xml_element path="./elem/more[2]" attribute="name"><has_text_matching expression="foo$"/></xml_element>""",
    """<xml_element path="./elem/more[2]" attribute="name"></xml_element>""",
    """<element_text path="./elem/more[2]"><has_text text="foo" /></element_text>""",
    """<has_element_with_path path="BlastOutput_param/Parameters/Parameters_matrix" />""",
    r"""<element_text_matches path="BlastOutput_version" expression="BLASTP\s+2\.2.*"/>""",
    """<element_text_is path="BlastOutput_program" text="blastp" />""",
    r"""<attribute_matches path="outerElement/innerElement2" attribute="foo2" expression="bar\d+" />""",
    """<element_text path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_def"><not_has_text text="EDK72998.1" /></element_text>""",
    """<has_archive_member path=".*/my-file.txt"><not_has_text text="EDK72998.1"/></has_archive_member>""",
    """<has_archive_member path=".*/my-file.txt"></has_archive_member>""",
    """<has_image_n_labels n="85" />""",
    """<has_image_center_of_mass center_of_mass="511.07, 223.34" />""",
    """<has_image_center_of_mass center_of_mass="511.07, 223.34" eps=".2" />""",
    """<has_image_mean_intensity mean_intensity="0.83" />""",
    """<has_image_height height="512" delta="2" />""",
    """<has_image_width width="512" delta="2" />""",
    """<has_image_channels channels="3" />""",
    """<has_image_channels channels="3" delta="1" />""",
    """<has_image_channels min="3" max="5" />""",
    """<has_image_channels min="3" max="5" negate="true" />""",
    """<has_json_property_with_value property="skipped_columns" value="[1, 3, 5]" />""",
    """<has_json_property_with_text property="color" text="red" />""",
    """<has_n_columns n="30" />""",
    """<has_n_columns n="30" delta="4" />""",
    """<has_n_columns n="30" delta="4" sep=" " comment="###" />""",
    """<has_image_width min="500" />""",
    """<has_image_height min="500" />""",
]

invalid_assertions = [
    {"that": "has_size", "size": "5Gigabytes"},
    # negative sizes not allowed
    {"that": "has_size", "size": -1},
    {"that": "has_n_columns", "n": [2]},
    {"that": "has_n_columns", "n": -2},
    {"that": "is_valid_xml_foo"},
    {"that": "has_element_with_path", "path": 45},
    {"that": "has_n_elements_with_path", "n": 4},
    {"that": "has_n_elements_with_path", "n": -4},
    {"that": "element_text_matches", "expression": 12, "path": "//el"},
    # unclosed regex group
    {"that": "element_text_matches", "expression": "[12", "path": "//el"},
    {"that": "xml_element", "path": "./elem/more[2]", "children": [{"that": "foobar"}]},
    {
        "that": "xml_element",
        "path": "./elem/more[2]",
        "children": [{"that": "has_text_matching", "line": "invalidprop"}],
    },
    # must specify children for element_text
    {"that": "element_text", "path": "./elem/more[2]"},
    {"that": "has_json_property_with_value", "property": 42, "value": "cowdog"},
    {"that": "has_json_property_with_text", "property": "foobar", "text": 6},
    {"that": "has_archive_member", "path": ".*/my-file.txt", "extra": "param"},
    {"that": "has_archive_member", "path": ".*/my-file.txt", "children": [{"that": "invalid"}]},
    {"that": "has_image_width", "width": "560"},
    {"that": "has_image_width", "width": -560},
    {"that": "has_image_width", "width": 560, "delta": "wrong"},
    {"that": "has_image_height", "height": -560},
    {"that": "has_image_center_of_mass", "center_of_mass": "511.07, 223.34, foobar"},
    {"that": "has_image_center_of_mass", "center_of_mass": "511.07"},
    {"that": "has_image_center_of_mass", "center_of_mass": "511.07, cow"},
    # negative mean object sizes are not allowed
    {"that": "has_image_n_labels", "n": -85},
    {"that": "has_image_n_labels", "n": 85, "delta": -3},
    # negative mean object sizes are not allowed
    {"that": "has_image_mean_object_size", "mean_object_size": -9, "exclude_labels": [1, 3, 4]},
    {"that": "has_image_mean_object_size", "mean_object_size": -9.0, "exclude_labels": [1, 3, 4]},
    {"that": "has_image_mean_object_size", "mean_object_size": 9, "exclude_labels": [1, 3, 4], "eps": -0.2},
    # looks a little odd in JSON but value is JSON loaded so must be a string
    {"that": "has_json_property_with_value", "property": "skipped_columns", "value": [1, 3, 5]},
    # missing property
    {"that": "has_json_property_with_value", "property": "skipped_columns"},
    {"that": "has_json_property_with_text", "property": "color"},
    {"that": "has_n_columns", "n": 30, "delta": "wrongtype"},
    {"that": "has_n_columns", "n": 30, "delta": -2},
    {"that": "has_n_columns", "n": 30, "delta": 4, "sep": " ", "comment": "####", "extra": "param"},
]

invalid_xml_assertions = [
    """<has_n_columns n="cow" />""",
    """<has_text line="JBrowseDefaultMainPage" />""",
    """<has_line text="JBrowseDefaultMainPage" />""",
    # at least one child assertion is required here...
    """<element_text path="./elem/more[2]"></element_text>""",
    """<has_archive_member path=".*/my-file.txt"><not_has_text line="EDK72998.1"/></has_archive_member>""",
    """<has_archive_member path=".*/my-file.txt"><foobar /></has_archive_member>""",
    """<has_image_center_of_mass center_of_mass="511.07, 223.34" extra="param" />""",
    """<has_image_center_of_mass center_of_mass="511.07, 223.34" eps="foobar" />""",
    # negative numbers not allowed
    """<has_image_n_labels n="-85" />""",
    """<has_image_n_labels n="85" delta="-3" />""",
    """<has_image_mean_intensity mean_intensity="not_a_number" />""",
    """<has_image_mean_intensity mean_intensity=".83" extra="param" />""",
    """<has_image_height height="512" delta="notanumber" />""",
    """<has_image_width width="512" delta="2" extra="param" />""",
    """<has_image_height height="512" delta="-2" />""",
    """<has_image_width width="512" delta="-2" />""",
    """<has_image_height height="-512" />""",
    """<has_image_width width="-512" />""",
    """<has_image_channels channels="3" exclude="wrong" />""",
    """<has_image_channels channels="3" delta="not_a_number"  />""",
    """<has_image_channels min="3" max="5" foo="bar" />""",
    """<has_image_channels min="3" max="5" negate="NOTABOOLEAN" />""",
    # missing required arguments...
    """<has_json_property_with_value property="skipped_columns" />""",
    """<has_json_property_with_text property="color" />""",
    """<has_n_columns n="30" delta="wrong_type" />""",
    """<has_n_columns n="30" delta="4" sep=" " comment="###" extra="param"/>""",
]


TOOL_TEMPLATE = Template(
    """
<tool id="gx_test" name="gx_test" version="1.0.0">
    <command><![CDATA[
echo '$parameter' >> '$output'
    ]]></command>
    <inputs>
        <param name="parameter" value="1" type="integer" />
    </inputs>
    <outputs>
        <data name="output" format="txt" />
    </outputs>
    <tests>
        <test>
            <param name="parameter" value_json="12456" />
            <output name="output">
                <assert_contents>
                    $assertion_xml
                </assert_contents>
            </output>
        </test>
    </tests>
</tool>
"""
)


if sys.version_info < (3, 8):  # noqa: UP036
    pytest.skip(reason="Pydantic assertion models require python3.8 or higher", allow_module_level=True)


def test_valid_json_models_validate():
    assertion_list.model_validate(valid_assertions)


def test_invalid_json_models_do_not_validate():
    for invalid_assertion in invalid_assertions:
        with pytest.raises(ValidationError):
            assertion_list.model_validate([invalid_assertion])


@skip_unless_executable("xmllint")
def test_valid_xsd(tmp_path):
    for assertion_xml in valid_xml_assertions:
        tool_xml = TOOL_TEMPLATE.safe_substitute(assertion_xml=assertion_xml)
        tool_path = tmp_path / "tool.xml"
        tool_path.write_text(tool_xml)
        ret = shell(["xmllint", "--nowarning", "--noout", "--schema", galaxy_xsd_path, str(tool_path)])
        assert ret == 0, f"{assertion_xml} failed to validate"


@skip_unless_executable("xmllint")
def test_invalid_xsd(tmp_path):
    for assertion_xml in invalid_xml_assertions:
        tool_xml = TOOL_TEMPLATE.safe_substitute(assertion_xml=assertion_xml)
        tool_path = tmp_path / "tool.xml"
        tool_path.write_text(tool_xml)
        ret = shell(["xmllint", "--nowarning", "--noout", "--schema", galaxy_xsd_path, str(tool_path)])
        assert ret != 0, f"{assertion_xml} validated when error expected"


def test_valid_xml_models_validate_after_json_transform():
    for assertion_xml in valid_xml_assertions:
        assertion_xml_els_to_models([ET.fromstring(assertion_xml)])

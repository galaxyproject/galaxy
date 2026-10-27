# Not yet tested:
# - 23_0_consider_optional_text
import os

import pytest

from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.tool_util.upgrade import (
    Advice,
    advise_on_upgrade,
    TARGET_TOO_NEW,
)

FUTURE_GALAXY_VERSION = "29.6"
UNQUALIFIED_STRUCTURED_LIKE = "26_0_fix_unqualified_structured_like"
SECTION_INPUT = """<tool id="nested_collection_reference" name="nested_collection_reference" version="1.0">
  <command>cat '$sect.input1.forward' > '$output.forward'</command>
  <inputs>
    <section name="sect" title="Section">
      <param name="input1" type="data_collection" collection_type="paired" format="txt" />
    </section>
  </inputs>
  <outputs>
    <collection name="output" type="paired" {reference} />
  </outputs>
</tool>
"""
NESTED_CONDITIONAL_INPUT = """<tool id="nested_collection_reference" name="nested_collection_reference" version="1.0">
  <command>cat '$outer.inner.input1.forward' > '$output.forward'</command>
  <inputs>
    <conditional name="outer">
      <param name="outer_select" type="select"><option value="a">A</option></param>
      <when value="a">
        <conditional name="inner">
          <param name="inner_select" type="select"><option value="b">B</option></param>
          <when value="b">
            <param name="input1" type="data_collection" collection_type="paired" format="txt" />
          </when>
        </conditional>
      </when>
    </conditional>
  </inputs>
  <outputs>
    <collection name="output" type="paired" {reference} />
  </outputs>
</tool>
"""
FROM_WORK_DIR_TOOL = """<tool id="from_work_dir" name="from_work_dir" version="1.0" profile="21.01">
  <command>echo hi > out.txt</command>
  <inputs />
  <outputs>
    <data name="output" format="txt" from_work_dir="{reference}" />
  </outputs>
</tool>
"""
CITATION_TOOL = """<tool id="citation_tool" name="citation_tool" version="1.0" profile="26.0">
  <command>echo hi > '$output'</command>
  <inputs />
  <outputs>
    <data name="output" format="txt" />
  </outputs>
  <citations>
    <citation type="doi">{reference}</citation>
  </citations>
</tool>
"""
EMPTY_MULTIPLE_TEST_TOOL = """<tool id="empty_multiple" name="empty_multiple" version="1.0" profile="26.0">
  <command>echo '$parameter' > '$output'</command>
  <inputs>
    <param name="parameter" type="select" multiple="true" optional="true">
      <option value="a">A</option>
      <option value="b">B</option>
    </param>
  </inputs>
  <outputs>
    <data name="output" format="txt" />
  </outputs>
  <tests>
    <test>
      <param name="parameter" {reference} />
      <output name="output"><assert_contents><has_text text="a" /></assert_contents></output>
    </test>
  </tests>
</tool>
"""
N_COLUMNS_TOOL = """<tool id="n_columns" name="n_columns" version="1.0" profile="26.1">
  <command>echo 'a,b' > '$output'</command>
  <inputs />
  <outputs>
    <data name="output" format="txt" />
  </outputs>
  <tests>
    <test>
      <output name="output"><assert_contents><has_n_columns n="2" {reference} /></assert_contents></output>
    </test>
  </tests>
</tool>
"""


def test_does_not_work_on_non_xml_tools():
    simple_constructs = _tool_path("simple_constructs.yml")
    with pytest.raises(Exception) as e:
        advise_on_upgrade(simple_constructs, "16.04")
    assert "XML tools" in str(e)


def test_does_not_work_on_versions_too_new():
    simple_constructs = _tool_path("simple_constructs.xml")
    with pytest.raises(Exception) as e:
        advise_on_upgrade(simple_constructs, FUTURE_GALAXY_VERSION)
    assert TARGET_TOO_NEW in str(e)


def test_old_advice_does_not_appear_when_upgrading_past_it():
    a_16_01_tool = _tool_path("tool_provided_metadata_1.xml")
    advice = advise_on_upgrade(a_16_01_tool)
    assert_has_advice(advice, "16_04_consider_implicit_extra_file_collection")

    a_17_09_tool = _tool_path("tool_provided_metadata_6.xml")
    advice = advise_on_upgrade(a_17_09_tool)
    assert_not_has_advice(advice, "16_04_consider_implicit_extra_file_collection")


def test_advice_skipped_for_tool_already_at_profile(tmp_path):
    tool = SECTION_INPUT.replace('version="1.0"', 'version="1.0" profile="26.0"')
    advice = advise_on_upgrade(_write_tool(tmp_path, tool, 'structured_like="input1"'))
    assert_not_has_advice(advice, UNQUALIFIED_STRUCTURED_LIKE)


def test_interpreter_advice_positive():
    legacy_interpreter = _tool_path("legacy_interpreter.xml")
    advice = advise_on_upgrade(legacy_interpreter, "16.04")
    assert_has_advice(advice, "16_04_fix_interpreter")
    assert_not_has_advice(advice, "16_04_ready_interpreter")


def test_interpreter_advice_negative():
    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs, "16.04")
    assert_not_has_advice(advice, "16_04_fix_interpreter")
    assert_has_advice(advice, "16_04_ready_interpreter")


def test_output_format_advice_positive():
    output_format = _tool_path("output_format.xml")
    advice = advise_on_upgrade(output_format, "16.04")
    assert_has_advice(advice, "16_04_fix_output_format")


def test_20_05_inputs_changes():
    inputs_as_json = _tool_path("inputs_as_json.xml")
    advice = advise_on_upgrade(inputs_as_json)
    assert_has_advice(advice, "20_05_consider_inputs_as_json_changes")

    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs)
    assert_not_has_advice(advice, "20_05_consider_inputs_as_json_changes")


def test_output_format_advice_negative():
    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs, "16.04")
    assert_not_has_advice(advice, "16_04_fix_output_format")


def test_consider_implicit_extra_file_collection():
    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs, "16.04")
    assert_has_advice(advice, "16_04_consider_implicit_extra_file_collection")


def test_consider_stdio():
    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs, "16.04")
    assert_has_advice(advice, "16_04_exit_code")

    a_17_09_tool = _tool_path("tool_provided_metadata_6.xml")
    advice = advise_on_upgrade(a_17_09_tool)
    assert_not_has_advice(advice, "16_04_exit_code")


def test_2009_output_collection_advice_positive():
    collection_creates_list = _tool_path("collection_creates_list.xml")
    advice = advise_on_upgrade(collection_creates_list)
    assert_has_advice(advice, "20_09_consider_output_collection_order")


def test_2009_output_collection_advice_negative():
    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs)
    assert_not_has_advice(advice, "20_09_consider_output_collection_order")


def test_2009_consider_strict_shell_positive():
    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs)
    assert_has_advice(advice, "20_09_consider_set_e")


def test_1801_consider_home_directory():
    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs)
    assert_has_advice(advice, "18_01_consider_home_directory")


def test_26_0_unqualified_structured_like():
    nested_unqualified = _tool_path("collection_paired_conditional_structured_like.xml")
    advice = advise_on_upgrade(nested_unqualified)
    assert "'cond|input1'" in _advice_message(advice, UNQUALIFIED_STRUCTURED_LIKE)

    advice = advise_on_upgrade(nested_unqualified, "24.2")
    assert_not_has_advice(advice, UNQUALIFIED_STRUCTURED_LIKE)

    top_level_unqualified = _tool_path("collection_paired_structured_like.xml")
    advice = advise_on_upgrade(top_level_unqualified)
    assert_not_has_advice(advice, UNQUALIFIED_STRUCTURED_LIKE)


def test_26_0_unqualified_reference_in_section(tmp_path):
    tool = _write_tool(tmp_path, SECTION_INPUT, 'structured_like="input1"')
    advice = advise_on_upgrade(tool)
    assert "'sect|input1'" in _advice_message(advice, UNQUALIFIED_STRUCTURED_LIKE)


def test_26_0_qualified_reference(tmp_path):
    tool = _write_tool(tmp_path, SECTION_INPUT, 'structured_like="sect|input1"')
    advice = advise_on_upgrade(tool)
    assert_not_has_advice(advice, UNQUALIFIED_STRUCTURED_LIKE)


def test_26_0_partially_qualified_reference(tmp_path):
    tool = _write_tool(tmp_path, NESTED_CONDITIONAL_INPUT, 'structured_like="outer|input1"')
    advice = advise_on_upgrade(tool)
    assert "'outer|inner|input1'" in _advice_message(advice, UNQUALIFIED_STRUCTURED_LIKE)


def test_26_0_reference_in_repeat_not_advised(tmp_path):
    tool = _write_tool(
        tmp_path,
        SECTION_INPUT.replace(
            '<section name="sect" title="Section">',
            '<repeat name="queries" title="Q"><section name="sect" title="Section">',
        ).replace("</section>", "</section></repeat>"),
        'structured_like="queries_0|input1"',
    )
    advice = advise_on_upgrade(tool)
    assert_not_has_advice(advice, UNQUALIFIED_STRUCTURED_LIKE)


def test_21_09_from_work_dir_whitespace(tmp_path):
    advice = advise_on_upgrade(_write_tool(tmp_path, FROM_WORK_DIR_TOOL, " out.txt "))
    assert_has_advice(advice, "21_09_fix_from_work_dir_whitespace")

    advice = advise_on_upgrade(_write_tool(tmp_path, FROM_WORK_DIR_TOOL, "out.txt"))
    assert_not_has_advice(advice, "21_09_fix_from_work_dir_whitespace")


def test_21_09_data_source_advice():
    test_data_source = _tool_path("test_data_source.xml")
    advice = advise_on_upgrade(test_data_source)
    assert_has_advice(advice, "21_09_consider_python_environment")

    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs)
    assert_not_has_advice(advice, "21_09_consider_python_environment")


def test_24_0_request_cleaning():
    test_data_source = _tool_path("test_data_source.xml")
    advice = advise_on_upgrade(test_data_source)
    assert_has_advice(advice, "24_0_request_cleaning")

    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs)
    assert_not_has_advice(advice, "24_0_request_cleaning")


def test_24_2_test_case_validation():
    test_data_source = _tool_path("column_param.xml")
    advice = advise_on_upgrade(test_data_source)
    assert_has_advice(advice, "24_2_fix_test_case_validation")

    int_param = _tool_path("parameters/gx_int.xml")
    advice = advise_on_upgrade(int_param)
    assert_not_has_advice(advice, "24_2_fix_test_case_validation")


def test_24_2_validates_at_target_profile(tmp_path):
    tool = _write_tool(tmp_path, EMPTY_MULTIPLE_TEST_TOOL.replace('profile="26.0"', 'profile="24.0"'), 'value=""')
    advice = advise_on_upgrade(tool, "24.2")
    assert_not_has_advice(advice, "24_2_fix_test_case_validation")

    advice = advise_on_upgrade(tool)
    assert_not_has_advice(advice, "24_2_fix_test_case_validation")
    assert_has_advice(advice, "26_1_fix_empty_multiple_test_value")


def test_26_1_invalid_citation(tmp_path):
    advice = advise_on_upgrade(_write_tool(tmp_path, CITATION_TOOL, "not a doi"))
    assert "not a doi" in _advice_message(advice, "26_1_fix_invalid_citation")


def test_26_1_valid_citation(tmp_path):
    advice = advise_on_upgrade(_write_tool(tmp_path, CITATION_TOOL, "10.1093/bioinformatics/bts252"))
    assert_not_has_advice(advice, "26_1_fix_invalid_citation")


def test_26_1_empty_multiple_test_value(tmp_path):
    advice = advise_on_upgrade(_write_tool(tmp_path, EMPTY_MULTIPLE_TEST_TOOL, 'value=""'))
    assert_has_advice(advice, "26_1_fix_empty_multiple_test_value")


def test_26_1_empty_multiple_value_json(tmp_path):
    advice = advise_on_upgrade(_write_tool(tmp_path, EMPTY_MULTIPLE_TEST_TOOL, 'value_json="[]"'))
    assert_not_has_advice(advice, "26_1_fix_empty_multiple_test_value")


def test_26_1_advice_skipped_when_targeting_26_0(tmp_path):
    advice = advise_on_upgrade(_write_tool(tmp_path, CITATION_TOOL, "not a doi"), "26.0")
    assert_not_has_advice(advice, "26_1_fix_invalid_citation")


def test_26_2_optional_boolean():
    advice = advise_on_upgrade(_tool_path("parameters/gx_boolean_optional.xml"))
    assert_has_advice(advice, "26_2_consider_optional_boolean_unset")

    advice = advise_on_upgrade(_tool_path("parameters/gx_boolean_optional_checked.xml"))
    assert_not_has_advice(advice, "26_2_consider_optional_boolean_unset")


def test_26_2_tool_provided_metadata():
    advice = advise_on_upgrade(_tool_path("tool_provided_metadata_6.xml"))
    assert_has_advice(advice, "26_2_consider_tool_provided_metadata")

    # writes galaxy.json but has a format="auto" output
    advice = advise_on_upgrade(_tool_path("all_output_types.xml"))
    assert_not_has_advice(advice, "26_2_consider_tool_provided_metadata")

    advice = advise_on_upgrade(_tool_path("simple_constructs.xml"))
    assert_not_has_advice(advice, "26_2_consider_tool_provided_metadata")


def test_26_2_tool_provided_metadata_configfile(tmp_path):
    tool = _write_tool(
        tmp_path,
        CITATION_TOOL.replace('profile="26.0"', 'profile="26.1"').replace(
            "<inputs />",
            '<configfiles><configfile filename="galaxy.json">{reference}</configfile></configfiles><inputs />',
        ),
        "{}",
    )
    advice = advise_on_upgrade(tool)
    assert_has_advice(advice, "26_2_consider_tool_provided_metadata")


def test_26_2_tabular_assertion_separator():
    advice = advise_on_upgrade(_tool_path("column_assertion_delimiter_legacy.xml"))
    assert_has_advice(advice, "26_2_consider_tabular_assertion_separator")

    advice = advise_on_upgrade(_tool_path("simple_constructs.xml"))
    assert_not_has_advice(advice, "26_2_consider_tabular_assertion_separator")


def test_26_2_tabular_assertion_with_separator(tmp_path):
    advice = advise_on_upgrade(_write_tool(tmp_path, N_COLUMNS_TOOL, 'sep=","'))
    assert_not_has_advice(advice, "26_2_consider_tabular_assertion_separator")

    advice = advise_on_upgrade(_write_tool(tmp_path, N_COLUMNS_TOOL, ""))
    assert_has_advice(advice, "26_2_consider_tabular_assertion_separator")


def _write_tool(tmp_path, template: str, reference: str) -> str:
    tool_path = tmp_path / "tool.xml"
    tool_path.write_text(template.format(reference=reference))
    return str(tool_path)


def _advice_message(advice_list: list[Advice], advice_code: str) -> str:
    assert_has_advice(advice_list, advice_code)
    return "\n".join(a.message or "" for a in advice_list if a.advice_code["name"] == advice_code)


def _tool_path(tool_name: str):
    return os.path.join(functional_test_tool_path(tool_name))


def assert_has_advice(advice_list: list[Advice], advice_code: str):
    for advice in advice_list:
        if advice.advice_code["name"] == advice_code:
            return

    raise AssertionError(f"Was expecting advice {advice_code} in list of upgrade advice {advice_list}")


def assert_not_has_advice(advice_list: list[Advice], advice_code: str):
    for advice in advice_list:
        if advice.advice_code["name"] == advice_code:
            raise AssertionError(f"Was not expecting advice {advice_code} in list of upgrade advice {advice_list}")

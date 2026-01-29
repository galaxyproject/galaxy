# Not yet tested:
# - 21_09_fix_from_work_dir_whitespace
# - 23_0_consider_optional_text
import os
from typing import List

import pytest

from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.tool_util.upgrade import (
    Advice,
    advise_on_upgrade,
    TARGET_TOO_NEW,
)

FUTURE_GALAXY_VERSION = "29.6"


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


def test_1801_consider_structured_like():
    simple_constructs = _tool_path("collection_paired_conditional_structured_like.xml")
    advice = advise_on_upgrade(simple_constructs)
    assert_has_advice(advice, "18_01_consider_structured_like")

    simple_constructs = _tool_path("simple_constructs.xml")
    advice = advise_on_upgrade(simple_constructs)
    assert_not_has_advice(advice, "18_01_consider_structured_like")


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


def _tool_path(tool_name: str):
    return os.path.join(functional_test_tool_path(tool_name))


def assert_has_advice(advice_list: List[Advice], advice_code: str):
    for advice in advice_list:
        if advice.advice_code["name"] == advice_code:
            return

    raise AssertionError(f"Was expecting advice {advice_code} in list of upgrade advice {advice_list}")


def assert_not_has_advice(advice_list: List[Advice], advice_code: str):
    for advice in advice_list:
        if advice.advice_code["name"] == advice_code:
            raise AssertionError(f"Was not expecting advice {advice_code} in list of upgrade advice {advice_list}")

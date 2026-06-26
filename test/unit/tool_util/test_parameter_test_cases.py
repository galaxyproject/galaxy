import os
import re
from typing import (
    Any,
)

import pytest

from galaxy.tool_util.model_factory import parse_tool
from galaxy.tool_util.parameters import (
    DataCollectionRequest,
    DataRequestHda,
    encode_test,
    input_models_for_tool_source,
)
from galaxy.tool_util.parameters.case import (
    test_case_state as case_state,
    TestCaseStateAndWarnings,
    TestCaseStateValidationResult,
    validate_test_cases_for_tool_source,
)
from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.parser.interface import (
    ToolSource,
    ToolSourceTest,
)
from galaxy.tool_util.unittest_utils import (
    functional_test_tool_directory,
    functional_test_tool_source,
)
from galaxy.tool_util.verify.parse import parse_tool_test_descriptions
from galaxy.tool_util_models.tool_source import (
    JsonTestCollectionDefDict,
    JsonTestDatasetDefDict,
)
from galaxy.util.permutations import (
    is_in_state,
    state_set_value,
)
from .util import dict_verify_each

# legacy tools allows specifying parameter and repeat parameters without
# qualification. This was problematic and could result in ambigious specifications.
TOOLS_THAT_USE_UNQUALIFIED_PARAMETER_ACCESS = [
    "boolean_conditional.xml",
    "simple_constructs.xml",
    "disambiguate_cond.xml",
    "multi_repeats.xml",
    "implicit_default_conds.xml",
]

TOOLS_THAT_USE_SELECT_BY_VALUE = [
    "multi_select.xml",
]

# Figure out the problem and resolve.
TOOLS_THAT_ARE_OUTSTANDING_ISSUES = [
    "gx_conditional_boolean_optional.xml",
    "gx_conditional_boolean_discriminate_on_string_value.xml",
]

TEST_TOOL_THAT_DO_NOT_VALIDATE = (
    TOOLS_THAT_USE_UNQUALIFIED_PARAMETER_ACCESS
    + TOOLS_THAT_USE_SELECT_BY_VALUE
    + TOOLS_THAT_ARE_OUTSTANDING_ISSUES
    + [
        # will never handle upload_dataset
        "upload.xml",
    ]
)

MOCK_ID = "thisisafakeid"


def test_parameter_test_cases_validate():
    validation_result = validate_test_cases_for("column_param")
    assert len(validation_result[0].warnings) == 0
    assert len(validation_result[1].warnings) == 0
    assert len(validation_result[2].warnings) == 1

    validation_result = validate_test_cases_for("column_param", use_latest_profile=True)
    assert validation_result[2].validation_error


def test_legacy_features_fail_validation_with_24_2(tmp_path):
    for filename in TOOLS_THAT_USE_UNQUALIFIED_PARAMETER_ACCESS:
        _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, filename, index=None)

    # column parameters need to be indexes
    _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, "column_param.xml", index=2)

    # selection by value only
    _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, "multi_select.xml", index=1)


def _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, filename: str, index: int | None = 0):
    test_tool_directory = functional_test_tool_directory()
    original_path = os.path.join(test_tool_directory, filename)
    new_path = tmp_path / filename
    with open(original_path) as rf:
        tool_contents = rf.read()
        tool_contents = re.sub(r'profile="[\d\.]*"', r"", tool_contents)
        new_profile_contents = tool_contents.replace("<tool ", '<tool profile="24.2" ', 1)
    with open(new_path, "w") as wf:
        wf.write(new_profile_contents)
    test_cases = list(parse_tool_test_descriptions(get_tool_source(original_path)))
    if index is not None:
        assert test_cases[index].to_dict()["error"] is False
    else:
        # just make sure there is at least one failure...
        assert not any(c.to_dict()["error"] is True for c in test_cases)

    test_cases = list(parse_tool_test_descriptions(get_tool_source(new_path)))
    if index is not None:
        assert (
            test_cases[index].to_dict()["error"] is True
        ), f"expected {filename} to have validation failure preventing loading of tools"
    else:
        assert any(c.to_dict()["error"] is True for c in test_cases)


def test_validate_framework_test_tools():
    test_tool_directory = functional_test_tool_directory()
    parameter_tool_directory = os.path.join(test_tool_directory, "parameters")
    for test_directory in [test_tool_directory, parameter_tool_directory]:
        for tool_name in os.listdir(test_directory):
            if tool_name in TEST_TOOL_THAT_DO_NOT_VALIDATE:
                continue
            if tool_name.endswith("_conf.xml") or tool_name == "macros.xml":
                # tool conf (toolbox) files or sample datatypes
                continue
            tool_path = os.path.join(test_directory, tool_name)
            if not (tool_path.endswith(".xml") or tool_path.endswith(".yml")) or os.path.isdir(tool_path):
                continue

            try:
                _validate_path(tool_path)
            except Exception as e:
                raise Exception(f"Failed to validate {tool_path}: {str(e)}")


def test_test_case_state_conversion():
    tool_source = tool_source_for("collection_nested_test")
    test_cases: list[ToolSourceTest] = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations: list[tuple[list[Any], Any | None]]
    expectations = [
        (["f1", "collection_type"], "list:paired"),
        (["f1", "class"], "Collection"),
        (["f1", "elements", 0, "class"], "Collection"),
        (["f1", "elements", 0, "collection_type"], "paired"),
        (["f1", "elements", 0, "elements", 0, "class"], "File"),
        (["f1", "elements", 0, "elements", 0, "path"], "simple_line.txt"),
        (["f1", "elements", 0, "elements", 0, "identifier"], "forward"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    tool_source = tool_source_for("dbkey_filter_input")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["inputs", "class"], "File"),
        (["inputs", "dbkey"], "hg19"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    tool_source = tool_source_for("discover_metadata_files")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["input_bam", "class"], "File"),
        (["input_bam", "filetype"], "bam"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    tool_source = tool_source_for("remote_test_data_location")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["input", "class"], "File"),
        (
            ["input", "location"],
            "https://raw.githubusercontent.com/galaxyproject/planemo/7be1bf5b3971a43eaa73f483125bfb8cabf1c440/tests/data/hello.txt",
        ),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    tool_source = tool_source_for("composite")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["input", "class"], "File"),
        (["input", "filetype"], "velvet"),
        (["input", "composite_data", 0], "velveth_test1/Sequences"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    tool_source = tool_source_for("parameters/gx_group_tag")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["ref_parameter", "class"], "Collection"),
        (["ref_parameter", "collection_type"], "paired"),
        (["ref_parameter", "elements", 0, "identifier"], "forward"),
        (["ref_parameter", "elements", 0, "tags", 0], "group:type:single"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    index = 2
    tool_source = tool_source_for("filter_param_value_ref_attribute")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[index])
    expectations = [
        (["data_mult", 0, "path"], "1.bed"),
        (["data_mult", 0, "dbkey"], "hg19"),
        (["data_mult", 1, "path"], "2.bed"),
        (["data_mult", 0, "dbkey"], "hg19"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    index = 1
    tool_source = tool_source_for("expression_pick_larger_file")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[index])
    expectations = [
        (["input1", "path"], "simple_line_alternative.txt"),
        (["input2"], None),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    index = 2
    state = case_state_for(tool_source, test_cases[index])
    expectations = [
        (["input1"], None),
        (["input2", "path"], "simple_line.txt"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    index = 0
    tool_source = tool_source_for("composite_shapefile")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[index])
    expectations = [
        (["input", "filetype"], "shp"),
        (["input", "composite_data", 0], "shapefile/shapefile.shp"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    index = 0
    tool_source = tool_source_for("simple_constructs_y")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[index])
    expectations = [
        (["booltest"], True),
        (["simp_file", "path"], "simple_line.txt"),
        (["more_files", 0, "nestinput", "path"], "simple_line_alternative.txt"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)


def test_is_in_state_supports_nested_keys():
    state = {
        "section": {
            "parameter": "value",
        },
    }

    assert is_in_state(state, "section|parameter", nested=True)
    assert not is_in_state(state, "section|missing", nested=True)


def test_state_set_value_creates_nested_parent_state():
    state: dict[str, Any] = {}

    state_set_value(state, "p1|p1use", True, nested=True)
    state_set_value(state, "files_0|file", "dataset", nested=True)

    assert state == {
        "p1": {
            "p1use": True,
        },
        "files": [
            {
                "file": "dataset",
            }
        ],
    }


def test_state_set_value_does_not_misidentify_conditional_names_with_digit_suffix():
    # Conditional parameter names ending in _N (e.g. "inner_options_1") must not be
    # treated as flattened repeat indices when no repeat list has been started yet.
    state: dict[str, Any] = {}

    state_set_value(state, "outer|inner_options_1|mode", "by_index", nested=True)
    state_set_value(state, "outer|inner_options_1|col", 1, nested=True)
    state_set_value(state, "outer|inner_options_2|mode", "by_name", nested=True)
    state_set_value(state, "outer|inner_options_2|label", "foo", nested=True)

    assert state == {
        "outer": {
            "inner_options_1": {"mode": "by_index", "col": 1},
            "inner_options_2": {"mode": "by_name", "label": "foo"},
        }
    }


def test_test_case_request_conversion_preserves_non_default_select_and_booleans():
    tool_source = raw_xml_tool_source("""
<tool id="async_request_regression" name="async_request_regression" version="1.0.0">
    <command>echo</command>
    <inputs>
        <param name="output_type" type="select">
            <option value="meta" selected="true">MetaBAT2</option>
            <option value="semi">SemiBin2</option>
        </param>
        <param name="full_contig_name" type="boolean" truevalue="--full-contig-name" falsevalue="" />
        <section name="advanced_settings" expanded="false">
            <param name="method" type="select">
                <option value="hybrid" selected="true">Hybrid</option>
                <option value="wgs">WGS</option>
            </param>
            <param name="remove_identical_sequences" type="boolean" truevalue="-d" falsevalue="" />
        </section>
    </inputs>
    <outputs />
    <tests>
        <test>
            <param name="output_type" value="semi" />
            <param name="full_contig_name" value="true" />
            <section name="advanced_settings">
                <param name="method" value="wgs" />
                <param name="remove_identical_sequences" value="true" />
            </section>
        </test>
    </tests>
</tool>
        """)
    parameters = input_models_for_tool_source(tool_source)
    parsed_tool = parse_tool(tool_source)
    test_case = tool_source.parse_tests_to_dict()["tests"][0]
    test_case_state = case_state(test_case, parsed_tool.inputs, tool_source.parse_profile()).tool_state

    request_state = encode_test(test_case_state, parameters, mock_adapt_datasets, mock_adapt_collections)

    expectations = [
        (["output_type"], "semi"),
        (["full_contig_name"], True),
        (["advanced_settings", "method"], "wgs"),
        (["advanced_settings", "remove_identical_sequences"], True),
    ]
    dict_verify_each(request_state.input_state, expectations)


def test_nested_conditional_duplicate_short_names_are_distinct_when_qualified():
    tool_source = raw_xml_tool_source("""
<tool id="duplicate_use_regression" name="duplicate_use_regression" version="1.0.0">
    <command>echo</command>
    <inputs>
        <conditional name="operation">
            <param name="use" type="select">
                <option value="droplets" selected="true">Droplets</option>
                <option value="other">Other</option>
            </param>
            <when value="droplets">
                <conditional name="method">
                    <param name="use" type="select">
                        <option value="default" selected="true">Default</option>
                        <option value="expected">Expected</option>
                    </param>
                    <when value="default" />
                    <when value="expected">
                        <param name="expected" type="integer" value="1000" />
                    </when>
                </conditional>
            </when>
            <when value="other" />
        </conditional>
    </inputs>
    <outputs />
    <tests>
        <test>
            <conditional name="operation">
                <param name="use" value="droplets" />
                <conditional name="method">
                    <param name="use" value="expected" />
                    <param name="expected" value="2000" />
                </conditional>
            </conditional>
        </test>
    </tests>
</tool>
        """)
    parsed_tool = parse_tool(tool_source)
    test_case = tool_source.parse_tests_to_dict()["tests"][0]

    tool_state = case_state(test_case, parsed_tool.inputs, tool_source.parse_profile()).tool_state

    expectations = [
        (["operation", "use"], "droplets"),
        (["operation", "method", "use"], "expected"),
        (["operation", "method", "expected"], 2000),
    ]
    dict_verify_each(tool_state.input_state, expectations)


def test_legacy_partial_conditional_paths_are_resolved_for_request_state():
    tool_source = tool_source_for("disambiguate_cond")
    test_case = tool_source.parse_tests_to_dict()["tests"][1]

    tool_state = case_state_for(tool_source, test_case).tool_state

    expectations = [
        (["p1", "use"], True),
        (["p2", "use"], False),
        (["p3", "use"], True),
        (["files", "p4", "use"], True),
        (["files", "p4", "file", "path"], "simple_line.txt"),
    ]
    dict_verify_each(tool_state.input_state, expectations)


def test_legacy_unqualified_repeat_inputs_are_expanded_for_request_state():
    tool_source = tool_source_for("multi_repeats")
    test_cases = tool_source.parse_tests_to_dict()["tests"]

    test_case_state = case_state_for(tool_source, test_cases[2]).tool_state

    expectations = [
        (["queries", 0, "input2", "path"], "simple_line.txt"),
        (["queries", 1, "input2", "path"], "simple_line.txt"),
        (["more_queries", 0, "more_queries_input", "path"], "simple_line.txt"),
        (["more_queries", 1, "more_queries_input", "path"], "simple_line.txt"),
    ]
    dict_verify_each(test_case_state.input_state, expectations)


def test_legacy_unqualified_repeat_inside_conditional_is_resolved():
    # A repeat that lives inside a conditional may be specified unqualified (at the top
    # level of the test, without the enclosing <conditional> wrapper). Its nested params
    # must still resolve - including across two levels of repeat nesting - matching the
    # synchronous /api/tools path. Regression for the deseq2 async submission failure:
    #   select_data.__absent__.rep_factorName.0.rep_factorLevel.0.countsFile - Field required
    tool_source = raw_xml_tool_source("""
<tool id="unqualified_repeat_in_conditional" name="unqualified_repeat_in_conditional" version="1.0.0" profile="22.01">
    <command>echo</command>
    <inputs>
        <conditional name="select_data">
            <param name="how" type="select">
                <option value="datasets_per_level">Datasets per level</option>
                <option value="group_tags">Group tags</option>
            </param>
            <when value="datasets_per_level">
                <repeat name="rep_factorName" min="1">
                    <param name="factorName" type="text" value="" />
                    <repeat name="rep_factorLevel" min="1">
                        <param name="factorLevel" type="text" value="" />
                        <param name="countsFile" type="data" format="txt" />
                    </repeat>
                </repeat>
            </when>
            <when value="group_tags">
                <param name="countsFile" type="data" format="txt" />
            </when>
        </conditional>
    </inputs>
    <outputs />
    <tests>
        <test>
            <repeat name="rep_factorName">
                <param name="factorName" value="Treatment" />
                <repeat name="rep_factorLevel">
                    <param name="factorLevel" value="Treated" />
                    <param name="countsFile" value="simple_line.txt" />
                </repeat>
            </repeat>
        </test>
    </tests>
</tool>
        """)
    parsed_tool = parse_tool(tool_source)
    test_case = tool_source.parse_tests_to_dict()["tests"][0]

    tool_state = case_state(test_case, parsed_tool.inputs, tool_source.parse_profile()).tool_state

    expectations = [
        (["select_data", "rep_factorName", 0, "factorName"], "Treatment"),
        (["select_data", "rep_factorName", 0, "rep_factorLevel", 0, "factorLevel"], "Treated"),
        (["select_data", "rep_factorName", 0, "rep_factorLevel", 0, "countsFile", "path"], "simple_line.txt"),
    ]
    dict_verify_each(tool_state.input_state, expectations)


def test_omitted_conditional_discriminator_inferred_from_provided_params():
    # When a conditional's discriminator is omitted, the active when must be inferred from
    # the parameters the test actually supplies (matching the synchronous tool API) rather
    # than defaulting to the selected="true" branch. Regression for the quast async failure
    # where `inputs` is a repeat in the non-default when but a data param in the default:
    #   mode.co.in.__absent__.inputs.0.class - ...
    tool_source = raw_xml_tool_source("""
<tool id="infer_when" name="infer_when" version="1.0.0" profile="22.01">
    <command>echo</command>
    <inputs>
        <conditional name="in">
            <param name="custom" type="select">
                <option value="true">Custom names</option>
                <option value="false" selected="true">Dataset names</option>
            </param>
            <when value="true">
                <repeat name="inputs" min="1">
                    <param name="input" type="data" format="txt" />
                    <param name="labels" type="text" value="" />
                </repeat>
            </when>
            <when value="false">
                <param name="inputs" type="data" format="txt" multiple="true" />
            </when>
        </conditional>
    </inputs>
    <outputs />
    <tests>
        <test>
            <conditional name="in">
                <repeat name="inputs">
                    <param name="input" value="simple_line.txt" />
                    <param name="labels" value="c1" />
                </repeat>
            </conditional>
        </test>
    </tests>
</tool>
        """)
    parsed_tool = parse_tool(tool_source)
    test_case = tool_source.parse_tests_to_dict()["tests"][0]

    tool_state = case_state(test_case, parsed_tool.inputs, tool_source.parse_profile()).tool_state

    expectations = [
        (["in", "custom"], "true"),
        (["in", "inputs", 0, "input", "path"], "simple_line.txt"),
        (["in", "inputs", 0, "labels"], "c1"),
    ]
    dict_verify_each(tool_state.input_state, expectations)


def test_duplicate_identical_unqualified_test_param_is_tolerated():
    # A test may list the same unqualified conditional param twice (a common authoring
    # slip). When the duplicate values are identical it is tolerated - matching the
    # synchronous tool API - rather than aborting the request build. Regression for the
    # gatk4 mutect2 / hisat2 async failure:
    #   could not build request: Ambiguous unqualified test parameter name (...)
    tool_template = """
<tool id="duplicate_unqualified" name="duplicate_unqualified" version="1.0.0" profile="22.01">
    <command>echo</command>
    <inputs>
        <conditional name="reference_source">
            <param name="selector" type="select">
                <option value="history" selected="true">History</option>
                <option value="cached">Cached</option>
            </param>
            <when value="history">
                <param name="ref" type="text" value="" />
            </when>
            <when value="cached">
                <param name="ref" type="text" value="" />
            </when>
        </conditional>
    </inputs>
    <outputs />
    <tests>
        <test>
            <param name="selector" value="history" />
            <param name="ref" value="{first}" />
            <param name="ref" value="{second}" />
        </test>
    </tests>
</tool>
        """

    # identical duplicate -> tolerated
    tool_source = raw_xml_tool_source(tool_template.format(first="hg38", second="hg38"))
    parsed_tool = parse_tool(tool_source)
    test_case = tool_source.parse_tests_to_dict()["tests"][0]
    tool_state = case_state(test_case, parsed_tool.inputs, tool_source.parse_profile()).tool_state
    dict_verify_each(tool_state.input_state, [(["reference_source", "ref"], "hg38")])

    # conflicting duplicate -> still ambiguous
    tool_source = raw_xml_tool_source(tool_template.format(first="hg38", second="hg19"))
    parsed_tool = parse_tool(tool_source)
    test_case = tool_source.parse_tests_to_dict()["tests"][0]
    with pytest.raises(Exception, match="[Aa]mbiguous"):
        case_state(test_case, parsed_tool.inputs, tool_source.parse_profile())


def test_legacy_boolean_test_values_are_coerced_to_booleans():
    # The test-case builder must submit a real boolean for a boolean param. A test may
    # supply the param's truevalue/falsevalue command-line string, a plain true/false,
    # or (for legacy tools) a non-boolean placeholder such as "-" that the synchronous
    # tool API coerces via string_as_bool. Regression for the quast async failure:
    #   advanced.skip_unaligned_mis_contigs - Input should be a valid boolean, input_value='-'
    tool_template = """
<tool id="boolean_legacy_values" name="boolean_legacy_values" version="1.0.0" profile="{profile}">
    <command>echo</command>
    <inputs>
        <param name="flag" type="boolean" truevalue="" falsevalue="--skip" checked="true" />
    </inputs>
    <outputs />
    <tests>
        <test><param name="flag" value="{value}" /></test>
    </tests>
</tool>
        """

    def flag_value_for(value: str, profile: str = "23.02"):
        tool_source = raw_xml_tool_source(tool_template.format(value=value, profile=profile))
        parsed_tool = parse_tool(tool_source)
        test_case = tool_source.parse_tests_to_dict()["tests"][0]
        tool_state = case_state(test_case, parsed_tool.inputs, tool_source.parse_profile()).tool_state
        return tool_state.input_state["flag"]

    # plain booleans
    assert flag_value_for("true") is True
    assert flag_value_for("false") is False
    # truevalue / falsevalue command-line strings mapped back to booleans
    assert flag_value_for("") is True
    assert flag_value_for("--skip") is False
    # legacy non-boolean placeholder coerced to False (matches synchronous string_as_bool)
    assert flag_value_for("-") is False


def test_legacy_unqualified_conditional_discriminator_in_section_is_resolved():
    # A conditional inside a section may have its name elided in the test, with the
    # discriminator given directly under the section (e.g. <section name="adv">
    # <param name="esf" value="user"/> rather than wrapping it in <conditional
    # name="esf_cond">). The section prefix is kept but the conditional name is dropped.
    # Regression for the deseq2 async submission failure:
    #   Invalid parameter name found advanced_options|esf
    tool_source = raw_xml_tool_source("""
<tool id="elided_conditional_in_section" name="elided_conditional_in_section" version="1.0.0" profile="22.01">
    <command>echo</command>
    <inputs>
        <section name="advanced_options" title="Advanced">
            <conditional name="esf_cond">
                <param name="esf" type="select">
                    <option value="default" selected="true">Default</option>
                    <option value="user">User supplied</option>
                </param>
                <when value="default" />
                <when value="user">
                    <param name="size_factor_input" type="data" format="txt" />
                </when>
            </conditional>
        </section>
    </inputs>
    <outputs />
    <tests>
        <test>
            <section name="advanced_options">
                <param name="esf" value="user" />
                <param name="size_factor_input" value="simple_line.txt" />
            </section>
        </test>
    </tests>
</tool>
        """)
    parsed_tool = parse_tool(tool_source)
    test_case = tool_source.parse_tests_to_dict()["tests"][0]

    tool_state = case_state(test_case, parsed_tool.inputs, tool_source.parse_profile()).tool_state

    expectations = [
        (["advanced_options", "esf_cond", "esf"], "user"),
        (["advanced_options", "esf_cond", "size_factor_input", "path"], "simple_line.txt"),
    ]
    dict_verify_each(tool_state.input_state, expectations)


def test_legacy_select_labels_are_converted_to_values_for_request_state():
    tool_source = tool_source_for("multi_select")
    test_case = tool_source.parse_tests_to_dict()["tests"][1]

    test_case_state = case_state_for(tool_source, test_case).tool_state

    expectations = [
        (["select_ex", 0], "--ex1"),
    ]
    dict_verify_each(test_case_state.input_state, expectations)


def test_convert_to_requests():
    tools = [
        "parameters/gx_drill_down_recurse_multiple",
        "parameters/gx_conditional_select",
        "expression_pick_larger_file",
        "identifier_in_conditional",
        "column_param_list",
        "composite_shapefile",
    ]
    for tool_path in tools:
        tool_source = tool_source_for(tool_path)
        parameters = input_models_for_tool_source(tool_source)
        parsed_tool = parse_tool(tool_source)
        profile = tool_source.parse_profile()
        test_cases: list[ToolSourceTest] = tool_source.parse_tests_to_dict()["tests"]

        def mock_adapt_datasets(input: JsonTestDatasetDefDict) -> DataRequestHda:
            return DataRequestHda(src="hda", id=MOCK_ID)

        def mock_adapt_collections(input: JsonTestCollectionDefDict) -> DataCollectionRequest:
            return DataCollectionRequest(src="hdca", id=MOCK_ID)

        for test_case in test_cases:
            if test_case.get("expect_failure"):
                continue
            test_case_state_and_warnings = case_state(test_case, parsed_tool.inputs, profile)
            test_case_state = test_case_state_and_warnings.tool_state

            encode_test(test_case_state, parameters, mock_adapt_datasets, mock_adapt_collections)


def _validate_path(tool_path: str):
    tool_source = get_tool_source(tool_path)

    tool_source_class = type(tool_source).__name__
    raw_tool_source = tool_source.to_string()
    tool_source = get_tool_source(tool_source_class=tool_source_class, raw_tool_source=raw_tool_source)

    tool_id = tool_source.parse_id()
    model_name = f"{tool_id} (test case model)"
    parsed_tool = parse_tool(tool_source)
    profile = tool_source.parse_profile()
    test_cases: list[ToolSourceTest] = tool_source.parse_tests_to_dict()["tests"]
    for test_case in test_cases:
        if test_case.get("expect_failure"):
            continue
        test_case_state_and_warnings = case_state(test_case, parsed_tool.inputs, profile, name=model_name)
        tool_state = test_case_state_and_warnings.tool_state
        assert tool_state.state_representation == "test_case_xml"


def validate_test_cases_for(tool_name: str, **kwd) -> list[TestCaseStateValidationResult]:
    return validate_test_cases_for_tool_source(tool_source_for(tool_name), **kwd)


def case_state_for(tool_source: ToolSource, test_case: ToolSourceTest) -> TestCaseStateAndWarnings:
    parsed_tool = parse_tool(tool_source)
    profile = tool_source.parse_profile()
    return case_state(test_case, parsed_tool.inputs, profile)


def raw_xml_tool_source(raw_tool_source: str) -> ToolSource:
    return get_tool_source(tool_source_class="XmlToolSource", raw_tool_source=raw_tool_source)


def mock_adapt_datasets(input: JsonTestDatasetDefDict) -> DataRequestHda:
    return DataRequestHda(src="hda", id=MOCK_ID)


def mock_adapt_collections(input: JsonTestCollectionDefDict) -> DataCollectionRequest:
    return DataCollectionRequest(src="hdca", id=MOCK_ID)


tool_source_for = functional_test_tool_source


def test_build_xml_tool_source_preserves_validator_whitespace():
    """Regex validators may rely on significant leading/trailing whitespace (e.g. a leading
    `" *"` meaning "optional spaces"). Parsing a tool from its raw string source (as the async
    tool-request path does when re-parsing the stored source) must preserve it, exactly like
    parsing from a file does - otherwise " *(\\d+, *)*\\d+ *$" becomes the invalid "*(\\d+..."
    and statically validating the request 500s.
    """
    from galaxy.tool_util.parser.factory import build_xml_tool_source

    tool_xml = (
        '<tool id="ws_validator" name="ws_validator" version="1.0" profile="24.2">'
        "<command>echo</command><inputs>"
        '<param name="ints" type="text" value="1, 2, 3">'
        '<validator type="regex" message="comma separated ints"> *(\\d+, *)*\\d+ *$</validator>'
        "</param></inputs><outputs/></tool>"
    )
    tool_source = build_xml_tool_source(tool_xml)
    bundle = input_models_for_tool_source(tool_source)
    regex_validators = [
        v
        for p in bundle.parameters
        for v in (getattr(p, "validators", None) or [])
        if getattr(v, "type", "") == "regex"
    ]
    assert regex_validators, "expected a regex validator in the parsed model"
    assert regex_validators[0].expression == " *(\\d+, *)*\\d+ *$"


def test_infer_when_from_bare_unqualified_branch_param():
    """A legacy test may supply a non-default branch's param by its bare short name (without
    the enclosing conditional prefix) and omit the discriminator. The async builder must infer
    the active when from that bare param, as the sync API does - otherwise it defaults to the
    (empty) default branch and rejects the param as unhandled. Models novoplasty reference_cond
    / hisat2 adv|spliced_options.
    """
    from galaxy.tool_util.parser.factory import build_xml_tool_source

    tool_xml = (
        '<tool id="bare_branch" name="bare_branch" version="1.0" profile="20.01">'
        "<command>echo</command><inputs>"
        '<conditional name="use_ref">'
        '<param name="enabled" type="select"><option value="no" selected="true">No</option>'
        '<option value="yes">Yes</option></param>'
        '<when value="no"/>'
        '<when value="yes"><param name="reference" type="text" value="" /></when>'
        "</conditional></inputs><outputs/>"
        "<tests><test>"
        '<param name="reference" value="ref.fa"/>'  # bare, non-default branch, discriminator omitted
        "</test></tests></tool>"
    )
    ts = build_xml_tool_source(tool_xml)
    bundle = input_models_for_tool_source(ts)
    test = ts.parse_tests_to_dict()["tests"][0]
    # should not raise - the 'yes' branch is inferred from the bare 'reference'
    state = case_state(test, bundle.parameters, ts.parse_profile(), validate=True)
    assert state.tool_state.input_state["use_ref"]["enabled"] == "yes"


def test_omitted_conditional_records_first_option_default():
    """For a legacy conditional with no explicit selected="true", the first option is the
    default (is_default_when). When a test omits the discriminator entirely, the builder must
    record that default discriminator in the state - mirroring how the synchronous runtime
    (fill_static_defaults) fills an incomplete payload - so the state validates against the
    default branch instead of the phantom __absent__ branch. Models multigsea's
    proteomics/metabolomics conditionals.
    """
    from galaxy.tool_util.parser.factory import build_xml_tool_source

    tool_xml = (
        '<tool id="first_opt" name="first_opt" version="1.0" profile="20.05">'
        "<command>echo</command><inputs>"
        '<conditional name="opt">'
        '<param name="selector" type="select">'
        '<option value="a">A</option><option value="b">B</option></param>'  # no selected="true"
        '<when value="a"><param name="x" type="text" value="dx"/></when>'
        '<when value="b"/></conditional>'
        "</inputs><outputs/><tests><test/></tests></tool>"  # discriminator omitted entirely
    )
    ts = build_xml_tool_source(tool_xml)
    bundle = input_models_for_tool_source(ts)
    state = case_state(ts.parse_tests_to_dict()["tests"][0], bundle.parameters, ts.parse_profile(), validate=True)
    assert state.tool_state.input_state["opt"]["selector"] == "a"  # first option recorded, not __absent__

import pytest
from pydantic import ValidationError

from galaxy.tool_util.model_factory import (
    parse_tool,
)
from galaxy.tool_util.parser.factory import (
    build_xml_tool_source,
    get_tool_source,
)
from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.tool_util_models.tool_outputs import (
    IncomingUserToolOutputCollection,
    IncomingUserToolOutputDataset,
)


def tool_source_for(tool_name: str):
    return get_tool_source(functional_test_tool_path(tool_name))


def parsed_tool_for(tool_name: str):
    return parse_tool(tool_source_for(tool_name))


def test_parsed_tool_exposes_package_requirements():
    tool = parsed_tool_for("mulled_example_explicit.xml")

    assert len(tool.requirements) == 1
    requirement = tool.requirements[0]
    assert requirement.type == "package"
    assert requirement.name == "bwa"
    assert requirement.version == "0.7.15"


def test_parsed_tool_exposes_containers():
    tool = parsed_tool_for("mulled_example_explicit.xml")

    assert len(tool.containers) == 1
    container = tool.containers[0]
    assert container.type == "docker"
    assert container.container_id == "quay.io/biocontainers/bwa:0.7.15--0"


def test_parsed_tool_exposes_resource_requirements():
    tool = parsed_tool_for("resource_requirements.xml")

    assert len(tool.requirements) == 1
    requirement = tool.requirements[0]
    assert requirement.type == "resource"
    assert requirement.cores_min == "1.1"
    assert requirement.cores_max == "2"
    assert requirement.ram_min == "1.1"
    assert requirement.ram_max == "2>"
    assert requirement.tmpdir_min == "$(inputs.input1.size)"
    assert requirement.tmpdir_max == "$(inputs.input1.size * 2)"
    assert requirement.timelimit == "60"


def test_parsed_tool_exposes_versionless_package_requirements():
    tool = parsed_tool_for("mulled_example_multi_versionless.xml")

    assert len(tool.requirements) == 2
    requirements_by_name = {requirement.name: requirement for requirement in tool.requirements}
    assert requirements_by_name["samtools"].version is None
    assert requirements_by_name["bedtools"].version is None


def test_parsed_tool_exposes_stdio_exit_code_rules():
    tool = parsed_tool_for("mulled_example_explicit.xml")

    assert len(tool.stdio.exit_codes) == 1
    exit_code = tool.stdio.exit_codes[0]
    assert exit_code.range_start == 2.0
    assert exit_code.range_end == "inf"
    assert exit_code.error_level == 3


def test_parsed_tool_exposes_stdio_regex_rules():
    tool = parsed_tool_for("detect_errors.xml")

    assert len(tool.stdio.exit_codes) == 3
    assert len(tool.stdio.regexes) == 6
    regex = tool.stdio.regexes[0]
    assert regex.match == "message"
    assert regex.stdout_match is True
    assert regex.stderr_match is False
    assert regex.error_level == 1
    assert regex.desc == "some program message of interest"


def test_parsed_tool_serializes():
    tool_source = tool_source_for("mulled_example_explicit.xml")

    parsed_tool = parse_tool(tool_source)

    assert parsed_tool.model_dump(mode="json")["requirements"][0]["name"] == "bwa"
    assert parsed_tool.model_dump(mode="json")["containers"][0]["type"] == "docker"
    assert parsed_tool.model_dump_json()


@pytest.mark.parametrize(
    "model_class, output_type",
    [
        (IncomingUserToolOutputDataset, "data"),
        (IncomingUserToolOutputCollection, "collection"),
    ],
)
def test_user_tool_outputs_reject_filters(model_class, output_type):
    with pytest.raises(ValidationError) as exc:
        model_class.model_validate({"name": "out", "type": output_type, "filters": ["flag is True"]})
    assert any(error["loc"] == ("filters",) and error["type"] == "extra_forbidden" for error in exc.value.errors())


def test_parsed_tool_serializes_output_filters():
    tool = parsed_tool_for("output_filter.xml")
    outputs = {output["name"]: output for output in tool.model_dump(mode="json")["outputs"]}
    assert outputs["out_1"]["filters"] == ["produce_out_1 is True"]
    assert outputs["out_2"]["filters"] == ['filter_text_1 in ["foo", "bar"]', 'filter_text_1 == "foo"']
    assert outputs["list_output"]["filters"] == ["produce_collection is True"]
    assert outputs["paired_list_output"]["filters"] == ["produce_paired_collection is True"]


@pytest.mark.parametrize("output_type", ["integer", "float", "boolean", "text"])
def test_parsed_tool_serializes_scalar_output_filters(output_type):
    tool_source = build_xml_tool_source(f"""
        <tool id="filtered_scalar" name="Filtered scalar" version="1.0">
            <outputs>
                <output name="value" type="{output_type}" from="1">
                    <filter> True </filter>
                    <filter>False</filter>
                </output>
            </outputs>
        </tool>
    """)
    tool = parse_tool(tool_source)
    assert tool.model_dump(mode="json")["outputs"][0]["filters"] == ["True", "False"]


@pytest.mark.parametrize(
    "tool_name", ["mulled_example_explicit.xml", "collection_creates_pair.xml", "collection_creates_pair_y.yml"]
)
def test_parsed_tool_unfiltered_outputs(tool_name):
    tool = parsed_tool_for(tool_name)
    assert tool.outputs
    assert all(output["filters"] == [] for output in tool.model_dump(mode="json")["outputs"])

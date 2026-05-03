from galaxy.tool_util.model_factory import (
    parse_tool,
    parse_tool_custom,
)
from galaxy.tool_util.parser.factory import build_xml_tool_source
from galaxy.tool_util_models.tool_source import PackageRequirement
from tool_shed_client.schema import ShedParsedTool


def test_parsed_tool_exposes_package_requirements():
    tool = parse_tool(build_xml_tool_source("""
<tool id="parsed_req" name="Parsed Requirement" version="1.0" profile="22.05">
    <requirements>
        <requirement type="package" version="1.17">samtools</requirement>
    </requirements>
</tool>
"""))

    assert len(tool.requirements) == 1
    requirement = tool.requirements[0]
    assert requirement.type == "package"
    assert requirement.name == "samtools"
    assert requirement.version == "1.17"


def test_parsed_tool_exposes_containers():
    tool = parse_tool(build_xml_tool_source("""
<tool id="parsed_container" name="Parsed Container" version="1.0" profile="22.05">
    <requirements>
        <container type="docker">quay.io/biocontainers/samtools:1.17--h00cdaf9_0</container>
    </requirements>
</tool>
"""))

    assert len(tool.containers) == 1
    container = tool.containers[0]
    assert container.type == "docker"
    assert container.container_id == "quay.io/biocontainers/samtools:1.17--h00cdaf9_0"


def test_parsed_tool_exposes_resource_requirements_without_defaults():
    tool = parse_tool(build_xml_tool_source("""
<tool id="parsed_resource" name="Parsed Resource" version="1.0" profile="22.05">
    <requirements>
        <resource type="cores_min">4</resource>
    </requirements>
</tool>
"""))

    assert len(tool.requirements) == 1
    requirement = tool.requirements[0]
    assert requirement.type == "resource"
    assert requirement.cores_min == "4"
    assert requirement.ram_min is None


def test_package_requirement_version_is_optional():
    requirement = PackageRequirement.model_validate({"type": "package", "name": "bwa"})

    assert requirement.version is None


def test_parsed_tool_exposes_stdio_rules():
    tool = parse_tool(build_xml_tool_source("""
<tool id="parsed_stdio" name="Parsed Stdio" version="1.0" profile="22.05">
    <stdio>
        <exit_code range="2:4" level="fatal" description="bad exit" />
        <regex match="WARNING" source="stdout" level="warning" description="warn text" />
    </stdio>
</tool>
"""))

    assert len(tool.stdio.exit_codes) == 1
    exit_code = tool.stdio.exit_codes[0]
    assert exit_code.range_start == 2
    assert exit_code.range_end == 4
    assert exit_code.error_level == 3
    assert exit_code.desc == "bad exit"

    assert len(tool.stdio.regexes) == 1
    regex = tool.stdio.regexes[0]
    assert regex.match == "WARNING"
    assert regex.stdout_match is True
    assert regex.stderr_match is False
    assert regex.error_level == 2
    assert regex.desc == "warn text"


def test_parsed_tool_and_shed_parsed_tool_serialize():
    tool_source = build_xml_tool_source("""
<tool id="parsed_serialized" name="Parsed Serialized" version="1.0" profile="22.05">
    <requirements>
        <requirement type="package" version="1.17">samtools</requirement>
        <container type="docker">quay.io/biocontainers/samtools:1.17--h00cdaf9_0</container>
    </requirements>
</tool>
""")

    parsed_tool = parse_tool(tool_source)
    shed_parsed_tool = parse_tool_custom(tool_source, ShedParsedTool)

    assert parsed_tool.model_dump(mode="json")["requirements"][0]["name"] == "samtools"
    assert shed_parsed_tool.model_dump(mode="json")["containers"][0]["type"] == "docker"
    assert parsed_tool.model_dump_json()
    assert shed_parsed_tool.model_dump_json()

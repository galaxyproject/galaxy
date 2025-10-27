import json
import os
from uuid import uuid4

import pytest
import yaml

from galaxy.tool_util.cwl import (
    tool_proxy,
    workflow_proxy,
)
from galaxy.tool_util.cwl.cwltool_deps import schema_salad
from galaxy.tool_util.cwl.parser import (
    _to_cwl_tool_object,
    tool_proxy_from_persistent_representation,
)
from galaxy.tool_util.cwl.representation import USE_FIELD_TYPES
from galaxy.tool_util.parser.cwl import (
    CWL_DEFAULT_FILE_OUTPUT,
    CwlToolSource,
)
from galaxy.tool_util.parser.factory import get_tool_source as _get_tool_source
from galaxy.util import galaxy_directory

CWL_TOOLS_DIRECTORY = os.path.abspath(os.path.join(galaxy_directory(), "test/functional/tools/cwl_tools"))


def get_tool_source(*args, **kwargs):
    tool_source = _get_tool_source(*args, **kwargs)
    if not isinstance(tool_source, CwlToolSource):
        raise Exception(f"Returned ToolSource class '{type(tool_source)}' was not expected class 'CwlToolSource'")
    return tool_source


def _cwl_tool_path(path: str):
    return os.path.join(CWL_TOOLS_DIRECTORY, path)


def test_tool_proxy():
    """Test that tool proxies load some valid tools correctly."""
    tool_proxy(_cwl_tool_path("v1.0/v1.0/cat1-testcli.cwl"))
    tool_proxy(_cwl_tool_path("v1.0/v1.0/cat3-tool.cwl"))
    tool_proxy(_cwl_tool_path("v1.0/v1.0/env-tool1.cwl"))
    tool_proxy(_cwl_tool_path("v1.0/v1.0/sorttool.cwl"))
    tool_proxy(_cwl_tool_path("v1.0/v1.0/bwa-mem-tool.cwl"))
    tool_proxy(_cwl_tool_path("v1.0/v1.0/parseInt-tool.cwl"))


def test_tool_source_records():
    record_output_path = _cwl_tool_path("v1.0/v1.0/record-output.cwl")
    tool_source = get_tool_source(record_output_path)
    inputs = _inputs(tool_source)
    assert len(inputs) == 1, inputs

    output_data, output_collections = _outputs(tool_source)
    assert len(output_data) == 1
    assert len(output_collections) == 1


def test_serialize_deserialize():
    path = _cwl_tool_path("v1.0/v1.0/cat5-tool.cwl")
    tool = tool_proxy(path)
    expected_uuid = tool.uuid
    rep = tool.to_persistent_representation()
    tool = tool_proxy_from_persistent_representation(rep)
    assert tool.uuid == expected_uuid
    tool.job_proxy({"file1": "/moo"}, {})
    with open(path) as f:
        tool_object = yaml.safe_load(f)
    tool_object = json.loads(json.dumps(tool_object))
    tool = _to_cwl_tool_object(tool_object=tool_object, uuid=expected_uuid)
    assert tool.uuid == expected_uuid


def test_job_proxy():
    bwa_parser = get_tool_source(_cwl_tool_path("v1.0/v1.0/bwa-mem-tool.cwl"))
    bwa_inputs = {
        "reference": {
            "class": "File",
            "location": _cwl_tool_path("v1.0/v1.0/chr20.fa"),
            "size": 123,
            "checksum": "sha1$hash",
        },
        "reads": [
            {"class": "File", "location": _cwl_tool_path("v1.0/v1.0/example_human_Illumina.pe_1.fastq")},
            {"class": "File", "location": _cwl_tool_path("v1.0/v1.0/example_human_Illumina.pe_2.fastq")},
        ],
        "min_std_max_min": [1, 2, 3, 4],
        "minimum_seed_length": 3,
    }
    bwa_proxy = bwa_parser.tool_proxy
    bwa_id = bwa_parser.parse_id()

    job_proxy = bwa_proxy.job_proxy(
        bwa_inputs,
        {},
        "/",
    )

    cmd = job_proxy.command_line
    print(cmd)

    bind_parser = get_tool_source(_cwl_tool_path("v1.0/v1.0/binding-test.cwl"))
    binding_proxy = bind_parser.tool_proxy
    binding_id = bind_parser.parse_id()

    job_proxy = binding_proxy.job_proxy(
        bwa_inputs,
        {},
        "/",
    )

    cmd = job_proxy.command_line
    assert bwa_id != binding_id, bwa_id


def test_cores_min():
    sort_parser = get_tool_source(_cwl_tool_path("v1.0/v1.0/sorttool.cwl"))
    bwa_parser = get_tool_source(_cwl_tool_path("v1.0/v1.0/bwa-mem-tool.cwl"))

    assert sort_parser.parse_cores_min() == 1
    assert bwa_parser.parse_cores_min() == 2


def test_success_codes():
    exit_success_parser = get_tool_source(_cwl_tool_path("v1.0/v1.0/exit-success.cwl"))

    stdio, _ = exit_success_parser.parse_stdio()
    assert len(stdio) == 2
    stdio_0 = stdio[0]
    assert stdio_0.range_start == float("-inf")
    assert stdio_0.range_end == 0

    stdio_1 = stdio[1]
    assert stdio_1.range_start == 2
    assert stdio_1.range_end == float("inf")

    bwa_parser = get_tool_source(_cwl_tool_path("v1.0/v1.0/bwa-mem-tool.cwl"))
    stdio, _ = bwa_parser.parse_stdio()

    assert len(stdio) == 2
    stdio_0 = stdio[0]
    assert stdio_0.range_start == float("-inf")
    assert stdio_0.range_end == -1

    stdio_1 = stdio[1]
    assert stdio_1.range_start == 1
    assert stdio_1.range_end == float("inf")


def test_serialize_deserialize_workflow_embed():
    # Test inherited hints and requirements from workflow -> tool
    # work here.
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/count-lines2-wf.cwl"))
    step_proxies = proxy.step_proxies()
    tool_proxy = step_proxies[0].tool_proxy
    assert tool_proxy.requirements, tool_proxy.requirements


def test_reference_proxies():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/count-lines1-wf.cwl"))
    assert len(proxy.tool_reference_proxies()) == 2


def test_subworkflow_parsing():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/count-lines10-wf.cwl"))
    assert len(proxy.tool_reference_proxies()) == 2

    assert len(proxy.output_labels) == 1
    assert "count_output" in proxy.output_labels, proxy.output_labels

    galaxy_workflow_dict = proxy.to_dict()
    steps = galaxy_workflow_dict["steps"]
    assert len(steps) == 2  # One input, one subworkflow

    subworkflow_step = steps[1]
    assert subworkflow_step["type"] == "subworkflow"


def test_checks_is_a_tool():
    """Test that tool proxy cannot be created for a workflow."""
    exception = None
    try:
        tool_proxy(_cwl_tool_path("v1.0/v1.0/count-lines1-wf.cwl"))
    except Exception as e:
        exception = e

    assert exception is not None
    assert "CommandLineTool" in str(exception), str(exception)


def test_workflow_of_files_proxy():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/count-lines1-wf.cwl"))
    step_proxies = proxy.step_proxies()
    assert len(step_proxies) == 2

    galaxy_workflow_dict = proxy.to_dict()

    assert len(proxy.runnables) == 2

    assert len(galaxy_workflow_dict["steps"]) == 3
    wc_step = galaxy_workflow_dict["steps"][1]
    exp_step = galaxy_workflow_dict["steps"][2]
    assert wc_step["input_connections"]
    assert exp_step["input_connections"]


def test_workflow_embedded_tools_proxy():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/count-lines2-wf.cwl"))
    step_proxies = proxy.step_proxies()
    assert len(step_proxies) == 2
    galaxy_workflow_dict = proxy.to_dict()

    assert len(proxy.runnables) == 2

    assert len(galaxy_workflow_dict["steps"]) == 3
    wc_step = galaxy_workflow_dict["steps"][1]
    exp_step = galaxy_workflow_dict["steps"][2]
    assert wc_step["input_connections"]
    assert exp_step["input_connections"]


def test_workflow_scatter():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/count-lines3-wf.cwl"))

    step_proxies = proxy.step_proxies()
    assert len(step_proxies) == 1

    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 2

    # TODO: For CWL - deactivate implicit scattering Galaxy does
    # and force annotation in the workflow of scattering? Maybe?
    wc_step = galaxy_workflow_dict["steps"][1]
    assert wc_step["input_connections"]

    assert "inputs" in wc_step
    wc_inputs = wc_step["inputs"]
    assert len(wc_inputs) == 1
    file_input = wc_inputs[0]
    assert file_input["scatter_type"] == "dotproduct", wc_step

    assert len(wc_step["workflow_outputs"]) == 1


def test_workflow_outputs_of_inputs():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/any-type-compat.cwl"))

    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 3
    input_step = galaxy_workflow_dict["steps"][0]

    assert len(input_step["workflow_outputs"]) == 1


def test_workflow_scatter_multiple_input():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/count-lines4-wf.cwl"))

    step_proxies = proxy.step_proxies()
    assert len(step_proxies) == 1

    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 3


def test_workflow_multiple_input_merge_flattened():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/count-lines7-wf.cwl"))

    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 3

    tool_step = galaxy_workflow_dict["steps"][2]
    assert "inputs" in tool_step
    inputs = tool_step["inputs"]
    assert len(inputs) == 1
    input = inputs[0]
    assert input["merge_type"] == "merge_flattened"


def test_workflow_step_value_from():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/step-valuefrom-wf.cwl"))

    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 3

    tool_step = [s for s in galaxy_workflow_dict["steps"].values() if s["label"] == "step1"][0]
    assert "inputs" in tool_step
    inputs = tool_step["inputs"]
    assert len(inputs) == 1
    assert "value_from" in inputs[0], inputs


def test_workflow_input_without_source():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/step-valuefrom3-wf.cwl"))

    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 3

    tool_step = galaxy_workflow_dict["steps"][2]
    assert "inputs" in tool_step
    inputs = tool_step["inputs"]
    assert len(inputs) == 3, inputs
    assert inputs[2].get("value_from")


def test_workflow_input_default():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/pass-unconnected.cwl"))
    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 3

    tool_step = galaxy_workflow_dict["steps"][2]

    assert "inputs" in tool_step
    inputs = tool_step["inputs"]
    assert len(inputs) == 2, inputs
    assert inputs[1]


def test_search_workflow():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/search.cwl#main"))
    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 5


def test_workflow_simple_optional_input():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/io-int-optional-wf.cwl"))

    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 2

    input_step = galaxy_workflow_dict["steps"][0]
    assert input_step["type"] == "parameter_input", input_step
    assert input_step["tool_state"]["parameter_type"] == "field", input_step


def test_boolean_defaults():
    proxy = workflow_proxy(_cwl_tool_path("v1.2/tests/conditionals/cond-wf-002_nojs.cwl"))
    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 3
    bool_input = galaxy_workflow_dict["steps"][0]
    assert bool_input["label"] == "test", bool_input
    bool_tool_state = bool_input["tool_state"]
    assert bool_tool_state["optional"]
    assert bool_tool_state["default"]["value"] is False


def test_workflow_file_optional_input():
    proxy = workflow_proxy(_cwl_tool_path("v1.0/v1.0/count-lines11-wf.cwl"))

    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 3

    input_step = galaxy_workflow_dict["steps"][0]
    # TODO: make this File? - implemented in Galaxy now
    assert input_step["type"] == "parameter_input", input_step
    assert input_step["tool_state"]["optional"] is True, input_step


def test_load_proxy_simple():
    cat3 = _cwl_tool_path("v1.0/v1.0/cat3-tool.cwl")
    tool_source = get_tool_source(cat3)

    # Behavior was changed - too verbose?
    # description = tool_source.parse_description()
    # assert description == "Print the contents of a file to stdout using 'cat' running in a docker container.", description

    input_sources = _inputs(tool_source)
    assert len(input_sources) == 1

    input_source = input_sources[0]
    assert input_source.parse_help() == "The file that will be copied using 'cat'"
    assert input_source.parse_label() == "Input File"

    outputs, output_collections = tool_source.parse_outputs(None)
    assert len(outputs) == 1

    output1 = outputs["output_file"]
    assert output1.format == CWL_DEFAULT_FILE_OUTPUT, output1.format  # Have Galaxy auto-detect

    software_requirements, containers, resource_requirements, _, credentials = tool_source.parse_requirements()
    assert software_requirements.to_dict() == []
    assert len(containers) == 1
    assert containers[0].to_dict() == {
        "identifier": "debian:stretch-slim",
        "type": "docker",
        "resolve_dependencies": False,
        "shell": "/bin/sh",
    }
    assert len(resource_requirements) == 1
    assert resource_requirements[0].to_dict() == {"resource_type": "ram_min", "value_or_expression": 8}
    assert len(credentials) == 0


def test_cwl_strict_parsing():
    md5sum_non_strict_path = _cwl_tool_path("v1.0_custom/md5sum_non_strict.cwl")
    with pytest.raises(schema_salad.exceptions.ValidationException):
        get_tool_source(md5sum_non_strict_path).tool_proxy  # noqa: B018

    get_tool_source(md5sum_non_strict_path, strict_cwl_validation=False).tool_proxy  # noqa: B018


def test_load_proxy_bwa_mem():
    bwa_mem = _cwl_tool_path("v1.0/v1.0/bwa-mem-tool.cwl")
    tool_source = get_tool_source(bwa_mem)
    tool_id = tool_source.parse_id()
    assert tool_id == "bwa-mem-tool.cwl", tool_id
    _inputs(tool_source)
    # TODO: test repeat generated...


def test_representation_id():
    cat3 = _cwl_tool_path("v1.0/v1.0/cat3-tool.cwl")
    with open(cat3) as f:
        representation = yaml.safe_load(f)
        representation["id"] = "my-cool-id"

        uuid = str(uuid4())
        proxy = tool_proxy(tool_object=representation, uuid=uuid)
        tool_id = proxy.galaxy_id()
        assert tool_id == uuid, tool_id
        id_proxy = tool_proxy_from_persistent_representation(proxy.to_persistent_representation())
        tool_id = id_proxy.galaxy_id()
        assert tool_id == uuid, tool_id
        assert proxy.uuid == id_proxy.uuid


def test_env_tool1():
    env_tool1 = _cwl_tool_path("v1.0/v1.0/env-tool1.cwl")
    tool_source = get_tool_source(env_tool1)
    _inputs(tool_source)


def test_wc2_tool():
    env_tool1 = _cwl_tool_path("v1.0/v1.0/wc2-tool.cwl")
    tool_source = get_tool_source(env_tool1)
    _inputs(tool_source)
    datasets, collections = _outputs(tool_source)
    assert len(datasets) == 1, datasets
    output = datasets["output"]
    assert output.format == "expression.json", output.format


def test_optional_output():
    optional_output2_tool1 = _cwl_tool_path("v1.0/v1.0/optional-output.cwl")
    tool_source = get_tool_source(optional_output2_tool1)
    datasets, collections = _outputs(tool_source)
    assert len(datasets) == 2, datasets
    output = datasets["optional_file"]
    assert output.format == "expression.json", output.format


def test_sorttool():
    env_tool1 = _cwl_tool_path("v1.0/v1.0/sorttool.cwl")
    tool_source = get_tool_source(env_tool1)

    assert tool_source.parse_id() == "sorttool.cwl"

    inputs = _inputs(tool_source)
    assert len(inputs) == 2
    bool_input = inputs[0]
    file_input = inputs[1]
    assert bool_input.parse_input_type() == "param"
    assert bool_input.get("type") == "boolean"

    assert file_input.parse_input_type() == "param"
    assert file_input.get("type") == "data", file_input.get("type")

    output_data, output_collections = _outputs(tool_source)
    assert len(output_data) == 1
    assert len(output_collections) == 0


def test_schemadef_tool():
    tool_path = _cwl_tool_path("v1.0/v1.0/schemadef-tool.cwl")
    tool_source = get_tool_source(tool_path)
    _inputs(tool_source)


def test_params_tool():
    tool_path = _cwl_tool_path("v1.0/v1.0/params.cwl")
    tool_source = get_tool_source(tool_path)
    _inputs(tool_source)


def test_cat1():
    cat1_tool = _cwl_tool_path("v1.0/v1.0/cat1-testcli.cwl")
    tool_source = get_tool_source(cat1_tool)
    inputs = _inputs(tool_source)

    assert len(inputs) == 3, inputs
    file_input = inputs[0]

    assert file_input.parse_input_type() == "param"
    assert file_input.get("type") == "data", file_input.get("type")

    # User needs to specify if want to select boolean or not.
    if not USE_FIELD_TYPES:
        null_or_bool_input = inputs[1]
        assert null_or_bool_input.parse_input_type() == "conditional"
    else:
        field_input = inputs[1]
        assert field_input.parse_input_type() == "param"
        assert field_input.get("type") == "field", field_input.get("type")

    output_data, output_collections = _outputs(tool_source)
    assert len(output_data) == 1
    assert len(output_collections) == 1


def test_tool_reload():
    cat1_tool = _cwl_tool_path("v1.0/v1.0/cat1-testcli.cwl")
    tool_source = get_tool_source(cat1_tool)
    _inputs(tool_source)

    # Test reloading - had a regression where this broke down.
    cat1_tool_again = _cwl_tool_path("v1.0/v1.0/cat1-testcli.cwl")
    tool_source = get_tool_source(cat1_tool_again)
    _inputs(tool_source)


def _outputs(tool_source: CwlToolSource):
    return tool_source.parse_outputs(None)


def _inputs(tool_source=None, path=None):
    if tool_source is None:
        path = _cwl_tool_path(path)
        tool_source = get_tool_source(path)

    input_pages = tool_source.parse_input_pages()
    assert input_pages.inputs_defined
    page_sources = input_pages.page_sources
    assert len(page_sources) == 1
    page_source = page_sources[0]
    input_sources = page_source.parse_input_sources()
    return input_sources


import os

from galaxy.tools.cwl import tool_proxy
from galaxy.tools.cwl import workflow_proxy

from galaxy.tools.parser.factory import get_tool_source


TESTS_DIRECTORY = os.path.dirname(__file__)
CWL_TOOLS_DIRECTORY = os.path.join(TESTS_DIRECTORY, "cwl_tools")


def test_tool_proxy():
    """Test that tool proxies load some valid tools correctly."""
    tool_proxy(_cwl_tool_path("draft3/cat1-tool.cwl"))
    tool_proxy(_cwl_tool_path("draft3/cat3-tool.cwl"))
    tool_proxy(_cwl_tool_path("draft3/env-tool1.cwl"))
    tool_proxy(_cwl_tool_path("draft3/sorttool.cwl"))
    tool_proxy(_cwl_tool_path("draft3/bwa-mem-tool.cwl"))

    tool_proxy(_cwl_tool_path("draft3/parseInt-tool.cwl"))


def test_checks_requirements():
    """Test that tool proxy will not load unmet requirements."""
    exception = None
    try:
        tool_proxy(_cwl_tool_path("draft3_custom/unmet-requirement.cwl"))
    except Exception as e:
        exception = e

    assert exception is not None
    assert "Unsupported requirement SubworkflowFeatureRequirement" in str(exception), str(exception)


def test_checks_is_a_tool():
    """Test that tool proxy cannot be created for a workflow."""
    exception = None
    try:
        tool_proxy(_cwl_tool_path("draft3/count-lines1-wf.cwl"))
    except Exception as e:
        exception = e

    assert exception is not None
    assert "CommandLineTool" in str(exception), str(exception)


def test_checks_cwl_version():
    """Test that tool proxy verifies supported version."""
    exception = None
    try:
        tool_proxy(_cwl_tool_path("draft3_custom/version345.cwl"))
    except Exception as e:
        exception = e

    assert exception is not None


def test_workflow_of_files_proxy():
    proxy = workflow_proxy(_cwl_tool_path("draft3/count-lines1-wf.cwl"))
    step_proxies = proxy.step_proxies()
    assert len(step_proxies) == 2

    galaxy_workflow_dict = proxy.to_dict()

    assert len(proxy.runnables) == 2

    first_runnable = proxy.runnables[0]
    print first_runnable

    assert len(galaxy_workflow_dict["steps"]) == 3
    print proxy._workflow
    print dir(proxy._workflow)
    print proxy._workflow.tool
    print dir(proxy._workflow.tool)


def test_workflow_embedded_tools_proxy():
    proxy = workflow_proxy(_cwl_tool_path("draft3/count-lines2-wf.cwl"))
    step_proxies = proxy.step_proxies()
    assert len(step_proxies) == 2
    assert len(proxy.runnables) == 2
    first_runnable = proxy.runnables[0]
    print first_runnable

    galaxy_workflow_dict = proxy.to_dict()
    assert len(galaxy_workflow_dict["steps"]) == 3
    print proxy._workflow
    print dir(proxy._workflow)
    print proxy._workflow.tool
    print dir(proxy._workflow.tool)


def test_load_proxy_simple():
    cat3 = _cwl_tool_path("draft3/cat3-tool.cwl")
    tool_source = get_tool_source(cat3)

    description = tool_source.parse_description()
    assert description == "Print the contents of a file to stdout using 'cat' running in a docker container.", description

    input_sources = _inputs(tool_source)
    assert len(input_sources) == 1

    input_source = input_sources[0]
    assert input_source.parse_help() == "The file that will be copied using 'cat'"
    assert input_source.parse_label() == "Input File"

    outputs, output_collections = tool_source.parse_outputs(None)
    assert len(outputs) == 1

    output1 = outputs['output_file']
    assert output1.format == "_sniff_"  # Have Galaxy auto-detect

    _, containers = tool_source.parse_requirements_and_containers()
    assert len(containers) == 1


def test_load_proxy_bwa_mem():
    bwa_mem = _cwl_tool_path("draft3/bwa-mem-tool.cwl")
    tool_source = get_tool_source(bwa_mem)
    _inputs(tool_source)
    # TODO: test repeat generated...


def test_env_tool1():
    env_tool1 = _cwl_tool_path("draft3/env-tool1.cwl")
    tool_source = get_tool_source(env_tool1)
    _inputs(tool_source)


def test_wc2_tool():
    env_tool1 = _cwl_tool_path("draft3/wc2-tool.cwl")
    tool_source = get_tool_source(env_tool1)
    _inputs(tool_source)
    datasets, collections = _outputs(tool_source)
    assert len(datasets) == 1, datasets
    output = datasets["output"]
    assert output.format == "expression.json", output.format


def test_optionial_output2():
    optional_output2_tool1 = _cwl_tool_path("draft3_custom/optional-output2.cwl")
    tool_source = get_tool_source(optional_output2_tool1)
    datasets, collections = _outputs(tool_source)
    assert len(datasets) == 1, datasets
    output = datasets["optional_file"]
    assert output.format == "_sniff_", output.format


def test_sorttool():
    env_tool1 = _cwl_tool_path("draft3/sorttool.cwl")
    tool_source = get_tool_source(env_tool1)
    _inputs(tool_source)


def test_cat1():
    cat1_tool = _cwl_tool_path("draft3/cat1-tool.cwl")
    tool_source = get_tool_source(cat1_tool)
    _inputs(tool_source)

    # Test reloading - had a regression where this broke down.
    cat1_tool_again = _cwl_tool_path("draft3/cat1-tool.cwl")
    tool_source = get_tool_source(cat1_tool_again)
    _inputs(tool_source)


def _outputs(tool_source):
    return tool_source.parse_outputs(object())


def _inputs(tool_source):
    input_pages = tool_source.parse_input_pages()
    assert input_pages.inputs_defined
    page_sources = input_pages.page_sources
    assert len(page_sources) == 1
    page_source = page_sources[0]
    input_sources = page_source.parse_input_sources()
    return input_sources


def _cwl_tool_path(path):
    return os.path.join(CWL_TOOLS_DIRECTORY, path)

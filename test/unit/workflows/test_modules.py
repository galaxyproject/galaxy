import json
from typing import (
    Any,
    NamedTuple,
)
from unittest import mock

import pytest

from galaxy import model
from galaxy.managers.workflows import WorkflowContentsManager
from galaxy.tool_util.parser.output_objects import ToolOutput
from galaxy.tools.parameters.meta import to_decoded_json
from galaxy.tools.parameters.workflow_utils import (
    ConnectedValue,
    NO_REPLACEMENT,
    RuntimeValue,
)
from galaxy.util import bunch
from galaxy.workflow import modules
from .workflow_support import (
    MockTrans,
    yaml_to_model,
)


def test_input_has_no_errors():
    trans = MockTrans()
    input_step_module = modules.module_factory.from_dict(trans, {"type": "data_input"})
    assert not input_step_module.get_errors()


def test_valid_new_tool_has_no_errors():
    trans = MockTrans()
    mock_tool = __mock_tool()
    trans.app.toolbox.tools["cat1"] = mock_tool
    tool_module = modules.module_factory.from_dict(trans, {"type": "tool", "tool_id": "cat1"})
    assert not tool_module.get_errors()


def test_data_input_default_state():
    trans = MockTrans()
    module = modules.module_factory.from_dict(trans, {"type": "data_input", "label": "Input Dataset"})
    __assert_has_runtime_input(module, label="Input Dataset")


def test_data_input_modified_state():
    module = __from_state({"type": "data_input", "label": "Cool Input"})
    __assert_has_runtime_input(module, label="Cool Input")


def test_data_input_step_modified_state():
    module = __from_step(type="data_input", label="Cool Input")
    __assert_has_runtime_input(module, label="Cool Input")


def test_data_input_compute_runtime_state_default():
    module = __from_step(type="data_input")
    state, errors = module.compute_runtime_state(module.trans, module.test_step)
    assert not errors
    assert "input" in state.inputs
    assert state.inputs["input"] is NO_REPLACEMENT


def test_data_input_compute_runtime_state_args():
    module = __from_step(type="data_input")
    tool_state = module.get_state()
    hda = model.HistoryDatasetAssociation()
    with mock.patch("galaxy.workflow.modules.check_param") as check_method:
        check_method.return_value = (hda, None)
        state, errors = module.compute_runtime_state(
            module.trans, module.test_step, {"input": 4, "tool_state": tool_state}
        )
    assert not errors
    assert "input" in state.inputs
    assert state.inputs["input"] is hda


def test_data_input_connections():
    module = __from_step(type="data_input")
    assert len(module.get_data_inputs()) == 0
    outputs = module.get_data_outputs()
    assert len(outputs) == 1
    output = outputs[0]
    assert output["name"] == "output"
    assert output["extensions"] == ["input"]


def test_data_collection_input_default_state():
    trans = MockTrans()
    module = modules.module_factory.from_dict(
        trans, {"type": "data_collection_input", "label": "Input Dataset Collection"}
    )
    __assert_has_runtime_input(module, label="Input Dataset Collection", collection_type="list")


def test_data_input_collection_modified_state():
    module = __from_state(
        {
            "type": "data_collection_input",
            "label": "Cool Input Collection",
            "tool_state": json.dumps({"collection_type": "list:paired"}),
        }
    )
    __assert_has_runtime_input(module, label="Cool Input Collection", collection_type="list:paired")


def test_data_input_collection_step_modified_state():
    module = __from_step(
        type="data_collection_input",
        label="Cool Input Collection",
        tool_inputs={
            "collection_type": "list:paired",
        },
    )
    __assert_has_runtime_input(module, label="Cool Input Collection", collection_type="list:paired")


def test_data_collection_input_connections():
    module = __from_step(type="data_collection_input", tool_inputs={"collection_type": "list:paired"})
    assert len(module.get_data_inputs()) == 0
    outputs = module.get_data_outputs()
    assert len(outputs) == 1
    output = outputs[0]
    assert output["name"] == "output"
    assert output["extensions"] == ["input"]
    assert output["collection_type"] == "list:paired"


def test_cannot_create_tool_modules_for_missing_tools():
    trans = MockTrans()
    module = modules.module_factory.from_dict(trans, {"type": "tool", "tool_id": "cat1"})
    assert not module.tool


def test_tool_version_latest_resolves_toolshed_guid():
    # Toolshed GUIDs embed the version as the last segment. When tool_version="latest"
    # is requested (as the WF editor does on insert), from_dict should strip the version
    # from the GUID and resolve to the latest installed version via the versionless key.
    trans = MockTrans()
    old_guid = "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.68+galaxy1"
    versionless_guid = "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc"
    latest_tool = __mock_tool(
        id="toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy1", version="0.74+galaxy1"
    )
    trans.app.toolbox.tools[versionless_guid] = latest_tool
    module = modules.module_factory.from_dict(trans, {"type": "tool", "content_id": old_guid, "tool_version": "latest"})
    assert module.tool is not None
    assert module.tool.version == "0.74+galaxy1"


def test_tool_version_latest_resolves_builtin_tool():
    # Built-in tool IDs have no version segment; remove_version_from_guid returns None
    # so the ID is unchanged. tool_version="latest" should still resolve correctly.
    trans = MockTrans()
    latest_tool = __mock_tool(id="cat1", version="2.0")
    trans.app.toolbox.tools["cat1"] = latest_tool
    module = modules.module_factory.from_dict(trans, {"type": "tool", "content_id": "cat1", "tool_version": "latest"})
    assert module.tool is not None
    assert module.tool.version == "2.0"


def test_updated_tool_version():
    trans = MockTrans()
    mock_tool = __mock_tool(id="cat1", version="0.9")
    trans.app.toolbox.tools["cat1"] = mock_tool
    module = __from_step(
        trans=trans,
        type="tool",
        tool_id="cat1",
        tool_version="0.7",
        config=None,
    )
    # Make sure there is a warnin with tool id, old version,
    # and new version.
    for val in "cat1", "0.7", "0.9":
        assert val in module.version_changes[0]


def test_tool_version_same():
    trans = MockTrans()
    mock_tool = __mock_tool(id="cat1", version="1.0")
    trans.app.toolbox.tools["cat1"] = mock_tool
    module = __from_step(
        trans=trans,
        type="tool",
        tool_id="cat1",
        tool_version="1.0",
        config=None,
    )
    assert not module.version_changes


TEST_WORKFLOW_YAML = """
steps:
  - type: "data_input"
    label: "input1"
  - type: "data_collection_input"
    label: "input2"
  - type: "tool"
    tool_id: "cat1"
    inputs:
      input1:
        connections:
        - "@output_step": 0
          output_name: "output"
  - type: "tool"
    tool_id: "cat1"
    inputs:
      input1:
        connections:
        - "@output_step": 0
          output_name: "output"
    workflow_outputs:
    -   output_name: "out_file1"
        label: "out1"
  - type: "tool"
    tool_id: "cat1"
    inputs:
      input1:
        connections:
        - "@output_step": 2
          output_name: "out_file1"
    workflow_outputs:
    -   output_name: "out_file1"
"""

COLLECTION_TYPE_WORKFLOW_YAML = """
steps:
  - type: "data_collection_input"
    label: "input1"
    collection_type: "list:list"
  - type: "tool"
    tool_id: "cat1"
    inputs:
      input1:
        connections:
        - "@output_step": 0
          output_name: "output"
"""


def test_subworkflow_new_inputs():
    subworkflow_module = __new_subworkflow_module()
    inputs = subworkflow_module.get_data_inputs()
    assert len(inputs) == 2, len(inputs)
    input1, input2 = inputs
    assert input1["input_type"] == "dataset"
    assert input1["name"] == "input1"
    assert input2["input_type"] == "dataset_collection"
    assert input2["name"] == "input2", input2["name"]


def test_subworkflow_new_inputs_collection_type():
    subworkflow_module = __new_subworkflow_module(COLLECTION_TYPE_WORKFLOW_YAML)
    inputs = subworkflow_module.get_data_inputs()
    assert inputs[0]["collection_type"] == "list:list"


def test_subworkflow_new_outputs():
    subworkflow_module = __new_subworkflow_module()
    outputs = subworkflow_module.get_data_outputs()
    assert len(outputs) == 2, len(outputs)
    output1, output2 = outputs
    assert output1["name"] == "out1"
    assert output1["extensions"] == ["input"]
    assert output2["name"] == "4:out_file1", output2["name"]


def test_to_cwl():
    hda = model.HistoryDatasetAssociation(create_dataset=True, flush=False)
    hda.dataset.state = model.Dataset.states.OK
    hdas = [hda]
    hda_references = []
    result = modules.to_cwl(hdas, hda_references, model.WorkflowStep())
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["class"] == "File"
    assert hda_references == hdas


def test_to_cwl_purged_dataset():
    hda = model.HistoryDatasetAssociation(create_dataset=True, flush=False)
    hda.id = 1
    hda.dataset.state = model.Dataset.states.OK
    hda.dataset.purged = True
    step = model.WorkflowStep()
    step.id = 1
    with pytest.raises(modules.FailWorkflowEvaluation):
        modules.to_cwl(hda, [], step)


def test_to_cwl_nested_collection():
    hda = model.HistoryDatasetAssociation(create_dataset=True, flush=False)
    hda.dataset.state = model.Dataset.states.OK
    dc_inner = model.DatasetCollection(collection_type="list")
    model.DatasetCollectionElement(collection=dc_inner, element_identifier="inner", element=hda)
    dc_outer = model.DatasetCollection(collection_type="list:list")
    model.DatasetCollectionElement(collection=dc_outer, element_identifier="outer", element=dc_inner)
    hdca = model.HistoryDatasetCollectionAssociation(name="the collection", collection=dc_outer)
    result = modules.to_cwl(hdca, [], model.WorkflowStep())
    assert result["outer"][0]["class"] == "File"
    assert result["outer"][0]["basename"] == "inner"


def test_to_cwl_dataset_collection_element():
    hda = model.HistoryDatasetAssociation(create_dataset=True, flush=False)
    hda.dataset.state = model.Dataset.states.OK
    dc_inner = model.DatasetCollection(collection_type="list")
    model.DatasetCollectionElement(collection=dc_inner, element_identifier="inner", element=hda)
    dc_outer = model.DatasetCollection(collection_type="list:list")
    dce_outer = model.DatasetCollectionElement(collection=dc_outer, element_identifier="outer", element=dc_inner)
    result = modules.to_cwl(dce_outer, [], model.WorkflowStep())
    assert result[0]["class"] == "File"
    assert result[0]["basename"] == "inner"


class MapOverTestCase(NamedTuple):
    data_input: str
    step_input_def: str | list[str]
    step_output_def: str
    expected_collection_type: str | None
    steps: dict[int, Any]


def _construct_steps_for_map_over() -> list[MapOverTestCase]:
    test_case = MapOverTestCase
    # these are the cartesian product of
    # data_input = ['dataset', 'list', 'list:pair', 'list:list']
    # step_input_definition = ['dataset', 'dataset_multiple', 'list', ['list', 'pair']]
    # step_output_definition = ['dataset', 'list', 'list:list']
    # list(itertools.product(data_input, step_input_definition, step_output_definition, [None])),
    # with the last item filled in manually
    test_case_args: list[tuple[str, str | list[str], str, str | None]] = [
        ("dataset", "dataset", "dataset", None),
        ("dataset", "dataset", "list", "list"),
        ("dataset", "dataset", "list:list", "list:list"),
        ("dataset", "dataset_multiple", "dataset", None),
        ("dataset", "dataset_multiple", "list", "list"),
        ("dataset", "dataset_multiple", "list:list", "list:list"),
        # Can't feed a dataset into a list or pair input
        # ('dataset', 'list', 'dataset', None),
        # ('dataset', 'list', 'list', None),
        # ('dataset', 'list', 'list:list', None),
        # ('dataset', ['list', 'pair'], 'dataset', None),
        # ('dataset', ['list', 'pair'], 'list', None),
        # ('dataset', ['list', 'pair'], 'list:list', None),
        ("list", "dataset", "dataset", "list"),
        ("list", "dataset", "list", "list:list"),
        ("list", "dataset", "list:list", "list:list:list"),
        ("list", "dataset_multiple", "dataset", None),
        ("list", "dataset_multiple", "list", "list"),
        ("list", "dataset_multiple", "list:list", "list:list"),
        ("list", "list", "dataset", None),
        ("list", "list", "list", "list"),
        ("list", "list", "list:list", "list:list"),
        ("list", ["list", "pair"], "dataset", None),
        ("list", ["list", "pair"], "list", "list"),
        ("list", ["list", "pair"], "list:list", "list:list"),
        ("list:pair", "dataset", "dataset", "list:pair"),
        ("list:pair", "dataset", "list", "list:pair:list"),
        ("list:pair", "dataset", "list:list", "list:pair:list:list"),
        # Pair into multiple="True" is not allowed
        # ('list:pair', 'dataset_multiple', 'dataset', None),
        # ('list:pair', 'dataset_multiple', 'list', None),
        # ('list:pair', 'dataset_multiple', 'list:list', None),
        # list:pair into list is not allowed
        # ('list:pair', 'list', 'dataset', None),
        # ('list:pair', 'list', 'list', None),
        # ('list:pair', 'list', 'list:list', None),
        ("list:pair", ["list", "pair"], "dataset", "list"),
        ("list:pair", ["list", "pair"], "list", "list:list"),
        ("list:pair", ["list", "pair"], "list:list", "list:list:list"),
        ("list:list", "dataset", "dataset", "list:list"),
        ("list:list", "dataset", "list", "list:list:list"),
        ("list:list", "dataset", "list:list", "list:list:list:list"),
        ("list:list", "dataset_multiple", "dataset", "list"),
        ("list:list", "dataset_multiple", "list", "list:list"),
        ("list:list", "dataset_multiple", "list:list", "list:list:list"),
        ("list:list", "list", "dataset", "list"),
        ("list:list", "list", "list", "list:list"),
        ("list:list", "list", "list:list", "list:list:list"),
        ("list:list", ["list", "pair"], "dataset", "list"),
        ("list:list", ["list", "pair"], "list", "list:list"),
        ("list:list", ["list", "pair"], "list:list", "list:list:list"),
    ]
    test_cases = []
    for data_input, step_input_def, step_output_def, expected_collection_type in test_case_args:
        steps: dict[int, dict[str, Any]] = {
            0: _input_step(collection_type=data_input),
            1: _output_step(step_input_def=step_input_def, step_output_def=step_output_def),
        }
        test_cases.append(
            test_case(
                data_input=data_input,
                step_input_def=step_input_def,
                step_output_def=step_output_def,
                expected_collection_type=expected_collection_type,
                steps=steps,
            )
        )
    return test_cases


def _input_step(collection_type) -> dict[str, Any]:
    output: dict[str, Any] = {"name": "output", "extensions": ["input_collection"]}
    if collection_type != "dataset":
        output["collection"] = True
        output["collection_type"] = collection_type
    step_type = "data_colletion_input" if collection_type == "dataset" else "data_input"
    return {
        "id": 0,
        "type": step_type,
        "inputs": [],
        "outputs": [output],
        "workflow_outputs": [],
        "input_connections": {},
    }


def _output_step(step_input_def, step_output_def) -> dict[str, Any]:
    multiple = False
    if step_input_def in ["dataset", "dataset_multiple"]:
        input_type = "dataset"
        collection_types = None
        if step_input_def == "dataset_multiple":
            multiple = True
    else:
        input_type = "dataset_collection"
        collection_types = step_input_def if isinstance(step_input_def, list) else [step_input_def]
    output: dict[str, Any] = {"name": "output", "extensions": ["data"]}
    if step_output_def != "dataset":
        output["collection"] = True
        output["collection_type"] = step_output_def
    input_connection_input: Any = [{"id": 0, "output_name": "output", "input_type": input_type}]
    if step_input_def == "dataset":
        # For whatever reason multiple = False inputs are not wrapped in a list.
        input_connection_input = input_connection_input[0]
    return {
        "id": 1,
        "type": "tool",
        "inputs": [
            {
                "name": "input",
                "multiple": multiple,
                "input_type": input_type,
                "collection_types": collection_types,
                "extensions": ["data"],
            }
        ],
        "input_connections": {"input": input_connection_input},
        "outputs": [output],
        "workflow_outputs": [{"output_name": "output"}],
    }


@pytest.mark.parametrize("test_case", _construct_steps_for_map_over())
def test_subworkflow_map_over_type(test_case):
    trans = MockTrans()
    new_steps = WorkflowContentsManager(app=trans.app, trs_proxy=trans.app.trs_proxy)._resolve_collection_type(
        test_case.steps
    )
    assert (
        new_steps[1]["outputs"][0].get("collection_type") == test_case.expected_collection_type
    ), "Expected collection_type '{}' for a '{}' input module, a '{}' input and a '{}' output, got collection_type '{}' instead".format(
        test_case.expected_collection_type,
        test_case.data_input,
        test_case.step_input_def,
        test_case.step_output_def,
        new_steps[1]["outputs"][0].get("collection_type"),
    )


def __new_subworkflow_module(workflow=TEST_WORKFLOW_YAML):
    trans = MockTrans()
    mock_tool = __mock_tool(id="cat1", version="1.0")
    trans.app.toolbox.tools["cat1"] = mock_tool
    workflow = yaml_to_model(workflow)
    stored_workflow = trans.save_workflow(workflow)
    workflow_id = trans.app.security.encode_id(stored_workflow.id)
    subworkflow_module = modules.module_factory.from_dict(trans, {"type": "subworkflow", "content_id": workflow_id})
    return subworkflow_module


def __assert_has_runtime_input(module, label=None, collection_type=None):
    test_step = getattr(module, "test_step", None)
    if test_step is None:
        test_step = mock.MagicMock()
    inputs = module.get_runtime_inputs(test_step)
    assert len(inputs) == 1
    assert "input" in inputs
    input_param = inputs["input"]
    if label is not None:
        assert input_param.get_label() == label, input_param.get_label()
    if collection_type is not None:
        assert input_param.collection_types == [collection_type]
    return input_param


def __from_state(state):
    trans = MockTrans()
    module = modules.module_factory.from_dict(trans, state)
    return module


def __from_step(**kwds):
    if "trans" in kwds:
        trans = kwds["trans"]
        del kwds["trans"]
    else:
        trans = MockTrans()
    step = __step(**kwds)
    injector = modules.WorkflowModuleInjector(trans)
    injector.inject(step, exact_tools=False)
    injector.compute_runtime_state(step)
    module = step.module
    module.test_step = step
    return module


def __step(**kwds):
    step = model.WorkflowStep()
    for key, value in kwds.items():
        setattr(step, key, value)
    return step


def __mock_tool(
    id="cat1",
    version="1.0",
):
    # For now ignoring inputs, params_from_strings, and
    # check_and_update_param_values since only have unit tests for version
    # handling - but need to write tests for all of this longer term.
    tool = bunch.Bunch(
        id=id,
        version=version,
        name=id,
        inputs={},
        outputs={
            "out_file1": mock.Mock(
                collection=None,
                format="input",
                format_source=None,
                change_format=[],
                filters=[],
                label=None,
                output_type="data",
                spec=ToolOutput,
            )
        },
        params_from_strings=mock.Mock(),
        check_and_update_param_values=mock.Mock(),
        to_json=_to_json,
    )

    return tool


def _to_json(*args, **kwargs):
    return "{}"


# _mapped_inputs_from_collection_info: reduce a MatchingCollections to
# source-neutral per-input map-over descriptors. Workflow path is always
# linked=True.


def test_mapped_inputs_from_collection_info_none_or_empty():
    assert modules._mapped_inputs_from_collection_info(None) == {}
    assert modules._mapped_inputs_from_collection_info(bunch.Bunch(collections={})) == {}


def test_mapped_inputs_from_collection_info_hdca_no_subcollection():
    collection_info = bunch.Bunch(collections={"a": bunch.Bunch(id=7)}, subcollection_types={})

    mapped = modules._mapped_inputs_from_collection_info(collection_info)

    assert set(mapped) == {"a"}
    descriptor = mapped["a"]
    assert descriptor.src == "hdca"
    assert descriptor.id == 7
    assert descriptor.map_over_type is None
    assert descriptor.linked is True


def test_mapped_inputs_from_collection_info_subcollection_map_over_type():
    collection_info = bunch.Bunch(
        collections={"a": bunch.Bunch(id=7)},
        subcollection_types={"a": bunch.Bunch(collection_type="paired")},
    )

    mapped = modules._mapped_inputs_from_collection_info(collection_info)

    assert mapped["a"].map_over_type == "paired"


def test_mapped_inputs_from_collection_info_dce_src():
    dce = mock.MagicMock(spec=model.DatasetCollectionElement)
    dce.id = 9
    collection_info = bunch.Bunch(collections={"a": dce}, subcollection_types={})

    mapped = modules._mapped_inputs_from_collection_info(collection_info)

    assert mapped["a"].src == "dce"
    assert mapped["a"].id == 9


# _capture_workflow_tool_request_state outcome taxonomy: the function
# returns (template, combinations, tool_request). Skipped steps and
# unexpected capture-code defects return (None, None, None) — no
# ToolRequest minted. Real meta-model rejections after the converter has
# produced a structural payload mint a ToolRequest with
# request_state == "validation_failed". trans/step are unused here;
# collection_info=None -> no mapped inputs; resolve raises before any
# downstream is reached.


class _CaptureFakeTool:
    id = "test_tool"
    profile = "21.09"
    parameters: list = []


def _capture(resolve):
    # history=None means the mint path is unreachable in these unit cases;
    # every exercised branch returns before touching it.
    return modules._capture_workflow_tool_request_state(None, _CaptureFakeTool(), None, None, None, resolve, [])


def test_capture_skipped_conditional_step_returns_none():
    """A falsy `when` raises SkipWorkflowStepEvaluation: nothing to capture."""

    def resolve(iteration_elements):
        raise modules.SkipWorkflowStepEvaluation

    assert _capture(resolve) == (None, None, None)


def test_capture_converter_guard_returns_none_quietly():
    """Converter raised before request_internal was built: no ToolRequest, quiet."""

    def resolve(iteration_elements):
        raise modules.RequestInternalToWorkflowStateError("cross-product")

    with mock.patch.object(modules, "log") as log:
        assert _capture(resolve) == (None, None, None)

    log.debug.assert_called_once()
    log.warning.assert_not_called()


def test_capture_invalid_state_returns_none_quietly():
    """Meta-model rejection at resolve-time: no payload to record, quiet."""

    def resolve(iteration_elements):
        raise modules.exceptions.RequestParameterInvalidException("bad state")

    with mock.patch.object(modules, "log") as log:
        assert _capture(resolve) == (None, None, None)

    log.debug.assert_called_once()
    log.warning.assert_not_called()


def test_capture_unexpected_error_returns_none_loudly():
    """Capture-code defect: drop the partial payload, surface at warning."""

    def resolve(iteration_elements):
        raise RuntimeError("capture bug")

    with mock.patch.object(modules, "log") as log:
        assert _capture(resolve) == (None, None, None)

    log.warning.assert_called_once()


def test_to_decoded_json_lowers_connected_value_in_repeat():
    """ConnectedValue inside a repeat lowers to its JSON marker.

    Regression: an unresolved connection inside a `repeat` survived to the
    tool_request flush as a raw ``ConnectedValue()`` and broke JSON encode
    with a TypeError. ``to_decoded_json`` recurses and lowers it to a marker.
    """
    payload = {
        "datasets": [
            {"input": {"src": "hda", "id": 1}},
            {"input": ConnectedValue()},
        ],
    }

    result = to_decoded_json(payload)

    assert result["datasets"][0]["input"] == {"src": "hda", "id": 1}
    assert result["datasets"][1]["input"] == {"__class__": "ConnectedValue"}
    json.dumps(result)


def test_to_decoded_json_lowers_bare_runtime_value():
    """Bare RuntimeValue tokens lower to their JSON marker form too."""
    result = to_decoded_json({"foo": RuntimeValue()})
    assert result == {"foo": {"__class__": "RuntimeValue"}}
    json.dumps(result)

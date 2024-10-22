import json
from typing import (
    Any,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)
from unittest import mock

import pytest

from galaxy import model
from galaxy.managers.workflows import WorkflowContentsManager
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
    assert state.inputs["input"] is None


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


def test_data_collection_input_config_form():
    module = __from_step(
        type="data_collection_input",
        tool_inputs={
            "collection_type": "list:paired",
        },
    )
    result = module.get_config_form()
    assert result["inputs"][0]["value"], "list:paired"


def test_cannot_create_tool_modules_for_missing_tools():
    trans = MockTrans()
    module = modules.module_factory.from_dict(trans, {"type": "tool", "tool_id": "cat1"})
    assert not module.tool


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
    step_input_def: Union[str, List[str]]
    step_output_def: str
    expected_collection_type: Optional[str]
    steps: Dict[int, Any]


def _construct_steps_for_map_over() -> List[MapOverTestCase]:
    test_case = MapOverTestCase
    # these are the cartesian product of
    # data_input = ['dataset', 'list', 'list:pair', 'list:list']
    # step_input_definition = ['dataset', 'dataset_multiple', 'list', ['list', 'pair']]
    # step_output_definition = ['dataset', 'list', 'list:list']
    # list(itertools.product(data_input, step_input_definition, step_output_definition, [None])),
    # with the last item filled in manually
    test_case_args: List[Tuple[str, Union[str, List[str]], str, Optional[str]]] = [
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
        steps: Dict[int, Dict[str, Any]] = {
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


def _input_step(collection_type) -> Dict[str, Any]:
    output: Dict[str, Any] = {"name": "output", "extensions": ["input_collection"]}
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


def _output_step(step_input_def, step_output_def) -> Dict[str, Any]:
    multiple = False
    if step_input_def in ["dataset", "dataset_multiple"]:
        input_type = "dataset"
        collection_types = None
        if step_input_def == "dataset_multiple":
            multiple = True
    else:
        input_type = "dataset_collection"
        collection_types = step_input_def if isinstance(step_input_def, list) else [step_input_def]
    output: Dict[str, Any] = {"name": "output", "extensions": ["data"]}
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
    new_steps = WorkflowContentsManager(app=trans.app)._resolve_collection_type(test_case.steps)
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
            "out_file1": bunch.Bunch(
                collection=None,
                format="input",
                format_source=None,
                change_format=[],
                filters=[],
                label=None,
                output_type="data",
            )
        },
        params_from_strings=mock.Mock(),
        check_and_update_param_values=mock.Mock(),
        to_json=_to_json,
    )

    return tool


def _to_json(*args, **kwargs):
    return "{}"

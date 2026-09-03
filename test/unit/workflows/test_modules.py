import json
from datetime import timedelta
from typing import (
    Any,
    NamedTuple,
)
from unittest import mock

import pytest

from galaxy import model
from galaxy.managers.workflows import WorkflowContentsManager
from galaxy.model.dataset_collections import matching
from galaxy.model.dataset_collections.structure import Tree
from galaxy.schema.invocation import FailureReason
from galaxy.tool_util.parser.output_objects import ToolOutput
from galaxy.tools.parameters.meta import to_decoded_json
from galaxy.tools.parameters.workflow_utils import (
    ConnectedValue,
    NO_REPLACEMENT,
    RuntimeValue,
)
from galaxy.util import (
    bunch,
    now,
)
from galaxy.workflow import (
    map_over,
    modules,
)
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


def _expression_json_hda(path, content: str | None, seconds_since_updated: int = 0):
    hda = model.HistoryDatasetAssociation(extension="expression.json", create_dataset=True, flush=False)
    hda.id = 1
    assert hda.dataset is not None
    hda.dataset.state = model.Dataset.states.OK
    if content is not None:
        path.write_text(content)
    hda.dataset.external_filename = str(path)
    hda.update_time = now() - timedelta(seconds=seconds_since_updated)
    return hda


def _workflow_step():
    step = model.WorkflowStep()
    step.id = 1
    return step


def test_to_cwl_expression_json(tmp_path):
    hda = _expression_json_hda(tmp_path / "expression.json", '"abs(c3)>0.5"')
    assert modules.to_cwl(hda, [], _workflow_step()) == "abs(c3)>0.5"


def test_to_cwl_expression_json_empty_file_recently_updated_delays(tmp_path):
    hda = _expression_json_hda(tmp_path / "expression.json", "")
    with pytest.raises(modules.DelayedWorkflowEvaluation) as exc_info:
        modules.to_cwl(hda, [], _workflow_step())
    assert "could not be read" in exc_info.value.why


def test_to_cwl_expression_json_malformed_fails_after_grace_period(tmp_path):
    hda = _expression_json_hda(
        tmp_path / "expression.json",
        "{not json",
        seconds_since_updated=modules.EXPRESSION_JSON_GRACE_PERIOD_SECONDS + 1,
    )
    step = _workflow_step()
    with pytest.raises(modules.FailWorkflowEvaluation) as exc_info:
        modules.to_cwl(hda, [], step)
    why = exc_info.value.why
    assert why.reason == FailureReason.unexpected_failure
    assert why.workflow_step_id == step.id
    assert "dataset 1" in why.details


def test_to_cwl_expression_json_missing_file_fails_after_grace_period(tmp_path):
    hda = _expression_json_hda(
        tmp_path / "expression.json", None, seconds_since_updated=modules.EXPRESSION_JSON_GRACE_PERIOD_SECONDS + 1
    )
    with pytest.raises(modules.FailWorkflowEvaluation) as exc_info:
        modules.to_cwl(hda, [], _workflow_step())
    why = exc_info.value.why
    assert why.reason == FailureReason.unexpected_failure
    # Invocation details must not expose the dataset path.
    assert str(tmp_path) not in why.details


def test_read_expression_json_without_update_time_fails_immediately(tmp_path):
    hda = _expression_json_hda(tmp_path / "expression.json", "")
    hda.update_time = None
    with pytest.raises(modules.FailWorkflowEvaluation) as exc_info:
        modules.read_expression_json(hda, _workflow_step())
    assert exc_info.value.why.reason == FailureReason.unexpected_failure


def test_read_expression_json_does_not_swallow_other_os_errors(tmp_path):
    a_directory = tmp_path / "expression.json"
    a_directory.mkdir()
    hda = _expression_json_hda(a_directory, None)
    with pytest.raises(IsADirectoryError):
        modules.read_expression_json(hda, _workflow_step())


def test_read_expression_json_without_step_reraises_read_error(tmp_path):
    hda = _expression_json_hda(tmp_path / "expression.json", "")
    with pytest.raises(json.JSONDecodeError):
        modules.read_expression_json(hda)


def test_replace_expression_json_dataset(tmp_path):
    hda = _expression_json_hda(tmp_path / "expression.json", "0.5")
    assert modules.replace_expression_json_dataset(hda, _workflow_step()) == 0.5


def test_replace_expression_json_dataset_collection_element(tmp_path):
    hda = _expression_json_hda(tmp_path / "expression.json", "true")
    collection = model.DatasetCollection(collection_type="list")
    element = model.DatasetCollectionElement(collection=collection, element_identifier="true", element=hda)
    assert modules.replace_expression_json_dataset(element, _workflow_step()) is True


def test_replace_expression_json_dataset_leaves_other_replacements_unchanged():
    hda = model.HistoryDatasetAssociation(extension="txt", create_dataset=True, flush=False)
    assert modules.replace_expression_json_dataset(hda, _workflow_step()) is hda
    assert modules.replace_expression_json_dataset("a string", _workflow_step()) == "a string"


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


def test_pick_value_mapped_false_coordinate_is_skipped():
    pick_value_module = object.__new__(modules.PickValueModule)
    picked = object()
    skipped = object()
    pick_value_module._pick_from_replacements = mock.Mock(return_value=picked)
    pick_value_module._create_skipped_output = mock.Mock(return_value=skipped)
    pick_value_module._create_mapped_output_collection = mock.Mock(return_value="mapped-output")
    first = bunch.Bunch(element_identifier="X", hda=object(), child_collection=None)
    second = bunch.Bunch(element_identifier="Y", hda=object(), child_collection=None)
    collection_info = bunch.Bunch(
        slice_collections=lambda: iter([({"input_0": first}, True), ({"input_0": second}, False)]),
        structure=object(),
    )
    invocation_step = bunch.Bunch(workflow_invocation=bunch.Bunch(history=object()))

    output = pick_value_module._execute_mapped(
        None,
        invocation_step,
        "first_non_null",
        [{"name": "input_0"}],
        collection_info,
    )

    assert output == "mapped-output"
    pick_value_module._pick_from_replacements.assert_called_once_with(
        None,
        invocation_step,
        "first_non_null",
        [first.hda],
    )
    pick_value_module._create_skipped_output.assert_called_once_with(None, invocation_step)
    assert pick_value_module._create_mapped_output_collection.call_args.args[3] == [("X", picked), ("Y", skipped)]


def test_residual_linked_axis_validates_later_direct_candidate():
    residual_structure = mock_structure("list")
    direct_structure = mock_structure("list")
    collection_info = matching.MatchingCollections.from_axes(
        [matching.MatchingCollectionAxis(direct_structure, "linked")]
    )
    collection_info.linked_structure = direct_structure
    inherited_bindings = {
        "a_residual": (
            bunch.Bunch(),
            (),
            (matching.MatchingCollectionAxis(residual_structure, "residual"),),
            (),
        )
    }

    def compatible_shape(left, right):
        return left.structure is right.structure

    with mock.patch.object(
        matching.MatchingCollections,
        "_axes_have_compatible_or_refined_shape",
        side_effect=compatible_shape,
    ):
        with pytest.raises(modules.exceptions.MessageException, match=matching.CANNOT_MATCH_ERROR_MESSAGE):
            map_over.MapOverPlanner._add_residual_linked_axis(
                collection_info,
                inherited_bindings,
                "linked",
                ["z_direct"],
            )


def test_missing_suffix_with_direct_linked_peer_remains_in_linked_group():
    outer_structure = mock_structure("list")
    full_structure = mock_structure("list:paired")
    suffix_structure = mock_structure("paired")
    outer_axis = matching.MatchingCollectionAxis(outer_structure, "outer")
    inherited = matching.MatchingCollections.from_axes([outer_axis])
    progress = bunch.Bunch(subworkflow_collection_info=inherited)
    collections = matching.CollectionsToMatch()
    collections.add("mapped_output", object())
    collections.add("direct_peer", object())
    workflow_module = map_over.MapOverPlanner(None)
    workflow_module._source_mapping_axes = mock.Mock(
        side_effect=lambda _progress, _step, input_name: (outer_axis,) if input_name == "mapped_output" else ()
    )
    workflow_module._mapping_structure = mock.Mock(return_value=full_structure)
    workflow_module._structure_suffix = mock.Mock(return_value=suffix_structure)

    bindings, refinements = workflow_module._extract_inherited_axis_bindings(progress, object(), collections)

    assert not refinements
    assert bindings["mapped_output"][2][0].structure is suffix_structure
    assert [name for name, _to_match in collections.items()] == ["direct_peer"]


def test_ragged_missing_suffix_promotes_direct_linked_peer_into_refined_axis():
    outer_structure = mock_structure("list")
    local_structure = mock_structure("list")
    ragged_structure = mock_structure("list:list:paired")
    outer_axis = matching.MatchingCollectionAxis(outer_structure, "outer")
    local_axis = matching.MatchingCollectionAxis(local_structure, "local")
    inherited = matching.MatchingCollections.from_axes([outer_axis])
    progress = bunch.Bunch(subworkflow_collection_info=inherited)
    collections = matching.CollectionsToMatch()
    collections.add("ragged", object())
    collections.add("direct_peer", object())
    ragged_to_match = collections.collections["ragged"]
    workflow_module = map_over.MapOverPlanner(None)
    workflow_module._source_mapping_axes = mock.Mock(
        side_effect=lambda _progress, _step, input_name: (outer_axis, local_axis) if input_name == "ragged" else ()
    )
    workflow_module._mapping_structure = mock.Mock(
        side_effect=lambda to_match: ragged_structure if to_match is ragged_to_match else local_structure
    )
    workflow_module._structure_suffix = mock.Mock(side_effect=modules.exceptions.MessageException("ragged"))

    bindings, refinements = workflow_module._extract_inherited_axis_bindings(progress, object(), collections)

    assert not collections.has_collections()
    assert refinements["outer"].structure is ragged_structure
    assert bindings["ragged"][2] == ()
    assert bindings["direct_peer"][1] == (outer_axis,)
    assert bindings["direct_peer"][2] == ()
    assert bindings["direct_peer"][3] == ((1, 2),)


def test_equal_shape_suffix_with_different_identifiers_is_not_reusable():
    first = mock_identifier_tree([("P", mock_identifier_tree([("one", matching.leaf), ("two", matching.leaf)]))])
    second = mock_identifier_tree([("P", mock_identifier_tree([("alpha", matching.leaf), ("beta", matching.leaf)]))])

    assert first.compatible_shape(second)
    assert not map_over.MapOverPlanner._structures_have_same_identifiers(first, second)


def test_direct_linked_peer_deeper_than_embedded_component_is_rejected():
    outer_structure = mock_structure("list")
    residual_structure = mock_structure("list")
    direct_structure = mock_structure("list:paired")
    refined_structure = mock_structure("list:list:paired")
    outer_axis = matching.MatchingCollectionAxis(outer_structure, "outer")
    residual_axis = matching.MatchingCollectionAxis(residual_structure, "local")
    refinements = {
        "outer": matching.MatchingCollectionAxis(
            refined_structure,
            "outer",
            (("outer", 0, 1), ("local", 1, 2)),
        )
    }
    collections = matching.CollectionsToMatch()
    collections.add("direct_peer", object())
    workflow_module = map_over.MapOverPlanner(None)
    workflow_module._mapping_structure = mock.Mock(return_value=direct_structure)

    with pytest.raises(modules.exceptions.MessageException, match=matching.CANNOT_MATCH_ERROR_MESSAGE):
        workflow_module._promote_direct_linked_bindings(
            collections,
            {},
            refinements,
            [(outer_axis, (residual_axis,))],
        )


def test_mapped_parameter_passthrough_is_explicitly_unsupported():
    with pytest.raises(modules.exceptions.MessageException, match="parameter pass-through"):
        map_over.passthrough_value_collection_type("not collection-backed")


def test_absent_optional_passthrough_is_not_materialized():
    output_step = bunch.Bunch(is_input_type=True)
    workflow_output = bunch.Bunch(workflow_step=output_step)

    replacement = map_over.shape_passthrough_output(
        None,
        None,
        workflow_output,
        "optional_output",
        modules.NO_REPLACEMENT,
        bunch.Bunch(),
    )

    assert replacement is modules.NO_REPLACEMENT


@pytest.mark.parametrize(
    ("axis_indices", "path_slices", "expected"),
    [
        ((0,), None, True),
        ((0,), ((0, 1),), False),
        ((0,), ((1, 2),), False),
        ((0, 0), ((0, 1), (1, 2)), True),
        ((0, 0), ((1, 2), (0, 1)), False),
    ],
)
def test_passthrough_binding_requires_complete_ordered_axis_paths(axis_indices, path_slices, expected):
    axis = matching.MatchingCollectionAxis(mock_structure("list:list"), "refined")
    binding = matching.MatchingCollectionBinding(
        collection=object(),
        axis_indices=axis_indices,
        axis_path_slices=path_slices,
    )

    assert map_over.binding_covers_mapping_axes(binding, [axis]) is expected


def test_partial_refined_axis_passthrough_is_broadcast_over_missing_suffix():
    list_description = bunch.Bunch(collection_type="list")
    refined_description = bunch.Bunch(collection_type="list:list")
    inner_x = Tree([("P", matching.leaf), ("Q", matching.leaf)], list_description)
    inner_y = Tree([("P", matching.leaf), ("Q", matching.leaf)], list_description)
    structure = Tree([("X", inner_x), ("Y", inner_y)], refined_description)
    axis = matching.MatchingCollectionAxis(structure, "refined")
    binding = matching.MatchingCollectionBinding(
        collection=object(),
        axis_indices=(0,),
        axis_path_slices=((0, 1),),
    )
    x_hda = model.HistoryDatasetAssociation()
    y_hda = model.HistoryDatasetAssociation()
    slices = [
        ({"source": bunch.Bunch(hda=x_hda, child_collection=None)}, None),
        ({"source": bunch.Bunch(hda=x_hda, child_collection=None)}, None),
        ({"source": bunch.Bunch(hda=y_hda, child_collection=None)}, None),
        ({"source": bunch.Bunch(hda=y_hda, child_collection=None)}, None),
    ]
    collection_info = bunch.Bunch(
        mapping_axes=[axis],
        conditions=[],
        bindings={"source": binding},
        structure=structure,
        slice_collections=lambda: iter(slices),
    )
    collection_manager = mock.Mock()
    child_collections = [object(), object()]
    collection_manager.create_dataset_collection.side_effect = child_collections
    shaped = object()
    collection_manager.create.return_value = shaped
    trans = bunch.Bunch(app=bunch.Bunch(dataset_collection_manager=collection_manager))
    output_step = bunch.Bunch(id=1, is_input_type=True)
    workflow_output = bunch.Bunch(workflow_step=output_step)
    parent_step = bunch.Bunch(
        label="sub",
        input_connections=[bunch.Bunch(input_subworkflow_step_id=1, input_name="source")],
    )
    invocation_step = bunch.Bunch(
        workflow_step=parent_step,
        workflow_invocation=bunch.Bunch(history=object()),
    )

    result = map_over.shape_passthrough_output(
        trans,
        invocation_step,
        workflow_output,
        "output",
        x_hda,
        collection_info,
    )

    assert result is shaped
    first_elements = collection_manager.create_dataset_collection.call_args_list[0].kwargs["elements"]
    second_elements = collection_manager.create_dataset_collection.call_args_list[1].kwargs["elements"]
    assert first_elements == {"P": x_hda, "Q": x_hda}
    assert second_elements == {"P": y_hda, "Q": y_hda}
    assert collection_manager.create.call_args.kwargs["elements"] == {
        "X": child_collections[0],
        "Y": child_collections[1],
    }


def test_absent_optional_passthrough_is_reconstructed_during_recovery():
    workflow_output = bunch.Bunch(
        label="optional_output",
        output_name="output",
        workflow_step=bunch.Bunch(order_index=0),
    )
    subworkflow_progress = mock.Mock()
    subworkflow_progress.get_replacement_workflow_output.return_value = {"__class__": "NoReplacement"}
    subworkflow_invoker = bunch.Bunch(
        workflow=bunch.Bunch(workflow_outputs=[workflow_output]),
        progress=subworkflow_progress,
    )
    progress = mock.Mock()
    progress.subworkflow_invoker.return_value = subworkflow_invoker
    invocation_step = bunch.Bunch(
        output_datasets=[],
        output_dataset_collections=[],
        workflow_step=object(),
    )
    subworkflow_module = object.__new__(modules.SubWorkflowModule)
    subworkflow_module.trans = object()
    subworkflow_module.get_all_inputs = mock.Mock(return_value=[])
    subworkflow_module.plan_map_over = mock.Mock(return_value=None)
    subworkflow_module._collect_output_mapping_axes = mock.Mock(return_value={})

    subworkflow_module.recover_mapping(invocation_step, progress)

    progress.set_step_outputs.assert_called_once_with(
        invocation_step,
        {"optional_output": modules.NO_REPLACEMENT},
        already_persisted=True,
        output_mapping_axes={},
    )


def test_missing_suffix_refines_existing_residual_axis_without_peer():
    outer_structure = mock_structure("list")
    local_structure = mock_structure("list")
    full_structure = mock_structure("list:list:paired")
    residual_structure = mock_structure("list:paired")
    outer_axis = matching.MatchingCollectionAxis(outer_structure, "outer")
    local_axis = matching.MatchingCollectionAxis(local_structure, "local")
    inherited = matching.MatchingCollections.from_axes([outer_axis])
    progress = bunch.Bunch(subworkflow_collection_info=inherited)
    collections = matching.CollectionsToMatch()
    collections.add("mapped_output", object())
    workflow_module = map_over.MapOverPlanner(None)
    workflow_module._source_mapping_axes = mock.Mock(return_value=(outer_axis, local_axis))
    workflow_module._mapping_structure = mock.Mock(return_value=full_structure)
    workflow_module._structure_suffix = mock.Mock(return_value=residual_structure)

    bindings, refinements = workflow_module._extract_inherited_axis_bindings(progress, object(), collections)

    assert not refinements
    assert bindings["mapped_output"][2][0].structure is residual_structure
    assert bindings["mapped_output"][3] == ((0, 1),)


def test_two_inherited_prefix_outputs_do_not_masquerade_as_direct_peers():
    outer_structure = mock_structure("list")
    full_structure = mock_structure("list:paired")
    outer_axis = matching.MatchingCollectionAxis(outer_structure, "outer")
    inherited = matching.MatchingCollections.from_axes([outer_axis])
    progress = bunch.Bunch(subworkflow_collection_info=inherited)
    collections = matching.CollectionsToMatch()
    collections.add("left", object())
    collections.add("right", object())
    workflow_module = map_over.MapOverPlanner(None)
    workflow_module._source_mapping_axes = mock.Mock(return_value=(outer_axis,))
    workflow_module._mapping_structure = mock.Mock(return_value=full_structure)

    bindings, refinements = workflow_module._extract_inherited_axis_bindings(progress, object(), collections)

    assert refinements["outer"].structure is full_structure
    assert bindings["left"][2] == ()
    assert bindings["right"][2] == ()


def test_ragged_refinement_preserves_and_promotes_embedded_residual_axis():
    outer_structure = mock_structure("list")
    local_structure = mock_structure("list")
    peer_structure = mock_structure("list:list")
    ragged_structure = mock_structure("list:list:paired")
    outer_axis = matching.MatchingCollectionAxis(outer_structure, "outer")
    local_axis = matching.MatchingCollectionAxis(local_structure, "local")
    inherited = matching.MatchingCollections.from_axes([outer_axis])
    progress = bunch.Bunch(subworkflow_collection_info=inherited)
    collections = matching.CollectionsToMatch()
    collections.add("ragged", object())
    collections.add("peer", object())
    ragged_to_match = collections.collections["ragged"]
    workflow_module = map_over.MapOverPlanner(None)
    workflow_module._source_mapping_axes = mock.Mock(return_value=(outer_axis, local_axis))
    workflow_module._mapping_structure = mock.Mock(
        side_effect=lambda to_match: ragged_structure if to_match is ragged_to_match else peer_structure
    )
    workflow_module._structure_suffix = mock.Mock(side_effect=modules.exceptions.MessageException("ragged"))

    bindings, refinements = workflow_module._extract_inherited_axis_bindings(progress, object(), collections)

    refined_axis = refinements["outer"]
    assert refined_axis.structure is ragged_structure
    assert refined_axis.component_path_slice("local") == (1, 2)
    assert bindings["ragged"][2] == ()
    assert bindings["peer"][1] == (outer_axis, outer_axis)
    assert bindings["peer"][2] == ()
    assert bindings["peer"][3] == ((0, 1), (1, 2))


def test_residual_linked_axis_can_refine_direct_binding_as_prefix():
    shallow = mock_structure("list")
    deep = mock_structure("list:paired")
    collection_info = matching.MatchingCollections.from_axes(
        [matching.MatchingCollectionAxis(shallow, "linked")],
        bindings={
            "peer": matching.MatchingCollectionBinding(
                collection=object(),
                axis_indices=(0,),
            )
        },
    )
    collection_info.linked_structure = shallow
    inherited_bindings = {
        "nested": (
            bunch.Bunch(),
            (),
            (matching.MatchingCollectionAxis(deep, "source-local"),),
            (),
        )
    }

    combined = map_over.MapOverPlanner._add_residual_linked_axis(
        collection_info,
        inherited_bindings,
        "linked",
        ["peer"],
    )

    assert combined.mapping_axes[0].structure is deep
    assert combined.bindings["peer"].axis_path_slices == ((0, 1),)


def test_two_inherited_bindings_share_deepest_residual_axis():
    shallow = mock_structure("list")
    deep = mock_structure("list:paired")
    inherited_bindings = {
        "chained": (
            bunch.Bunch(),
            (),
            (matching.MatchingCollectionAxis(deep, "chained-local"),),
            (),
        ),
        "peer": (
            bunch.Bunch(),
            (),
            (matching.MatchingCollectionAxis(shallow, "peer-local"),),
            (),
        ),
    }

    combined = map_over.MapOverPlanner._add_residual_linked_axis(
        None,
        inherited_bindings,
        "linked",
        [],
    )

    assert combined.mapping_axes[0].structure is deep
    assert combined.linked_structure is deep


def mock_structure(collection_type, children_known=False):
    description = bunch.Bunch(collection_type=collection_type)
    description.compatible = lambda other: other.collection_type == collection_type
    structure = bunch.Bunch(
        collection_type_description=description,
        children_known=children_known,
    )
    structure.clone = lambda: structure
    return structure


def mock_identifier_tree(children):
    description = bunch.Bunch(collection_type="list")
    description.compatible = lambda other: other.collection_type == "list"
    return Tree(children, description)

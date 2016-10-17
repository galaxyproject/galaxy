import json

import mock

from galaxy import model
from galaxy.util import bunch
from galaxy.workflow import modules

from .workflow_support import MockTrans, yaml_to_model


def test_input_has_no_errors():
    trans = MockTrans()
    input_step_module = modules.module_factory.new( trans, "data_input" )
    assert not input_step_module.get_errors()


def test_valid_new_tool_has_no_errors():
    trans = MockTrans()
    mock_tool = mock.Mock()
    trans.app.toolbox.tools[ "cat1" ] = mock_tool
    tool_module = modules.module_factory.new( trans, "tool", content_id="cat1" )
    assert not tool_module.get_errors()


def test_data_input_default_state():
    trans = MockTrans()
    module = modules.module_factory.new( trans, "data_input" )
    __assert_has_runtime_input( module, label="Input Dataset" )


def test_data_input_modified_state():
    module = __from_state( {
        "type": "data_input",
        "tool_state": json.dumps({ "name": "Cool Input" }),
    } )
    __assert_has_runtime_input( module, label="Cool Input" )


def test_data_input_step_modified_state():
    module = __from_step(
        type="data_input",
        tool_inputs={
            "name": "Cool Input",
        },
    )
    __assert_has_runtime_input( module, label="Cool Input" )


def test_data_input_compute_runtime_state_default():
    module = __from_step(
        type="data_input",
    )
    state, errors = module.compute_runtime_state( module.trans )
    assert not errors
    assert 'input' in state.inputs
    assert state.inputs[ 'input' ] is None


def test_data_input_compute_runtime_state_args():
    module = __from_step(
        type="data_input",
    )
    tool_state = module.get_state()

    hda = model.HistoryDatasetAssociation()
    with mock.patch('galaxy.workflow.modules.check_param') as check_method:
        check_method.return_value = ( hda, None )
        state, errors = module.compute_runtime_state( module.trans, { 'input': 4, 'tool_state': tool_state } )

    assert not errors
    assert 'input' in state.inputs
    assert state.inputs[ 'input' ] is hda


def test_data_input_connections():
    module = __from_step(
        type="data_input",
    )
    assert len( module.get_data_inputs() ) == 0

    outputs = module.get_data_outputs()
    assert len( outputs ) == 1
    output = outputs[ 0 ]
    assert output[ 'name' ] == 'output'
    assert output[ 'extensions' ] == [ 'input' ]


def test_data_input_update():
    module = __from_step(
        type="data_input",
        tool_inputs={
            "name": "Cool Input",
        },
    )
    module.update_state( dict( name="Awesome New Name" ) )
    assert module.state[ 'name' ] == "Awesome New Name"


def test_data_input_get_form():
    module = __from_step(
        type="data_input",
        tool_inputs={
            "name": "Cool Input",
        },
    )

    def test_form(template, **kwds ):
        assert template == "workflow/editor_generic_form.mako"
        assert "form" in kwds
        assert len( kwds[ "form" ].inputs ) == 1
        return "TEMPLATE"

    fill_mock = mock.Mock( side_effect=test_form )
    module.trans.fill_template = fill_mock
    assert module.get_config_form() == "TEMPLATE"


def test_data_collection_input_default_state():
    trans = MockTrans()
    module = modules.module_factory.new( trans, "data_collection_input" )
    __assert_has_runtime_input( module, label="Input Dataset Collection", collection_type="list" )


def test_data_input_collection_modified_state():
    module = __from_state( {
        "type": "data_collection_input",
        "tool_state": json.dumps({ "name": "Cool Input Collection", "collection_type": "list:paired" }),
    } )
    __assert_has_runtime_input( module, label="Cool Input Collection", collection_type="list:paired" )


def test_data_input_collection_step_modified_state():
    module = __from_step(
        type="data_collection_input",
        tool_inputs={
            "name": "Cool Input Collection",
            "collection_type": "list:paired",
        },
    )
    __assert_has_runtime_input( module, label="Cool Input Collection", collection_type="list:paired" )


def test_data_collection_input_connections():
    module = __from_step(
        type="data_collection_input",
        tool_inputs={
            'collection_type': 'list:paired'
        }
    )
    assert len( module.get_data_inputs() ) == 0

    outputs = module.get_data_outputs()
    assert len( outputs ) == 1
    output = outputs[ 0 ]
    assert output[ 'name' ] == 'output'
    assert output[ 'extensions' ] == [ 'input_collection' ]
    assert output[ 'collection_type' ] == 'list:paired'


def test_data_collection_input_update():
    module = __from_step(
        type="data_collection_input",
        tool_inputs={
            'name': 'Cool Collection',
            'collection_type': 'list:paired',
        }
    )
    module.update_state( dict( name="New Collection", collection_type="list" ) )
    assert module.state[ 'name' ] == "New Collection"


def test_data_collection_input_config_form():
    module = __from_step(
        type="data_collection_input",
        tool_inputs={
            'name': 'Cool Collection',
            'collection_type': 'list:paired',
        }
    )

    def test_form(template, **kwds ):
        assert template == "workflow/editor_generic_form.mako"
        assert "form" in kwds
        assert len( kwds[ "form" ].inputs ) == 2
        return "TEMPLATE"

    fill_mock = mock.Mock( side_effect=test_form )
    module.trans.fill_template = fill_mock
    assert module.get_config_form() == "TEMPLATE"


def test_cannot_create_tool_modules_for_missing_tools():
    trans = MockTrans()
    exception = False
    try:
        modules.module_factory.new( trans, "tool", content_id="cat1" )
    except Exception:
        exception = True
    assert exception


def test_updated_tool_version():
    trans = MockTrans()
    mock_tool = __mock_tool(id="cat1", version="0.9")
    trans.app.toolbox.tools[ "cat1" ] = mock_tool
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
    trans.app.toolbox.tools[ "cat1" ] = mock_tool
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
    tool_inputs: {"name": "input1"}
  - type: "data_collection_input"
    tool_inputs: {"name": "input2"}
  - type: "tool"
    tool_id: "cat1"
    input_connections:
    -  input_name: "input1"
       "@output_step": 0
       output_name: "output"
  - type: "tool"
    tool_id: "cat1"
    input_connections:
    -  input_name: "input1"
       "@output_step": 0
       output_name: "output"
    workflow_outputs:
    -   output_name: "out_file1"
        label: "out1"
  - type: "tool"
    tool_id: "cat1"
    input_connections:
    -  input_name: "input1"
       "@output_step": 2
       output_name: "out_file1"
    workflow_outputs:
    -   output_name: "out_file1"
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


def test_subworkflow_new_outputs():
    subworkflow_module = __new_subworkflow_module()
    outputs = subworkflow_module.get_data_outputs()
    assert len(outputs) == 2, len(outputs)
    output1, output2 = outputs
    assert output1["name"] == "out1"
    assert output1["label"] == "out1"
    assert output1["extensions"] == ["input"]

    assert output2["name"] == "4:out_file1", output2["name"]
    assert output2["label"] == "4:out_file1", output2["label"]


def __new_subworkflow_module():
    trans = MockTrans()
    workflow = yaml_to_model(TEST_WORKFLOW_YAML)
    stored_workflow = trans.save_workflow(workflow)
    workflow_id = trans.app.security.encode_id(stored_workflow.id)
    subworkflow_module = modules.module_factory.new( trans, "subworkflow", workflow_id )
    return subworkflow_module


def __assert_has_runtime_input( module, label=None, collection_type=None ):
    inputs = module.get_runtime_inputs()
    assert len( inputs ) == 1
    assert "input" in inputs

    input_param = inputs[ "input" ]
    if label is not None:
        assert input_param.get_label() == label, input_param.get_label()
    if collection_type is not None:
        assert input_param.collection_types == [collection_type]
    return input_param


def __from_state( state ):
    trans = MockTrans()
    module = modules.module_factory.from_dict( trans, state )
    return module


def __from_step( **kwds ):
    if "trans" in kwds:
        trans = kwds["trans"]
        del kwds["trans"]
    else:
        trans = MockTrans()
    step = __step(
        **kwds
    )
    injector = modules.WorkflowModuleInjector( trans )
    injector.inject( step )
    module = step.module
    module.test_step = step
    return module


def __step( **kwds ):
    step = model.WorkflowStep()
    for key, value in kwds.items():
        setattr( step, key, value )

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
        inputs={},
        params_from_strings=mock.Mock(),
        check_and_update_param_values=mock.Mock(),
    )
    return tool

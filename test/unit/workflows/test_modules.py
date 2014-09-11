from galaxy import eggs
eggs.require( "mock" )

import json
import mock

from galaxy import model

from galaxy.workflow import modules
from galaxy.tools import parameters
from .workflow_support import MockTrans


def test_input_has_no_errors():
    trans = MockTrans()
    input_step_module = modules.module_factory.new( trans, "data_input" )
    assert not input_step_module.get_errors()


def test_valid_new_tool_has_no_errors():
    trans = MockTrans()
    mock_tool = mock.Mock()
    trans.app.toolbox.tools[ "cat1" ] = mock_tool
    tool_module = modules.module_factory.new( trans, "tool", tool_id="cat1" )
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


def test_data_input_compute_state_default():
    module = __from_step(
        type="data_input",
    )
    state, errors = module.compute_state( module.trans )
    assert not errors
    assert 'input' in state.inputs
    assert state.inputs[ 'input' ] is None


def test_data_input_compute_state_args():
    module = __from_step(
        type="data_input",
    )
    tool_state = module.encode_runtime_state( module.trans, module.test_step.state )

    hda = model.HistoryDatasetAssociation()
    with mock.patch('galaxy.workflow.modules.check_param') as check_method:
        check_method.return_value = ( hda, None )
        state, errors = module.compute_state( module.trans, { 'input': 4, 'tool_state': tool_state } )

    assert not errors
    assert 'input' in state.inputs
    assert state.inputs[ 'input' ] is hda


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


def test_cannot_create_tool_modules_for_missing_tools():
    trans = MockTrans()
    exception = False
    try:
        modules.module_factory.new( trans, "tool", tool_id="cat1" )
    except Exception:
        exception = True
    assert exception


def __assert_has_runtime_input( module, label=None, collection_type=None ):
    inputs = module.get_runtime_inputs()
    assert len( inputs ) == 1
    assert "input" in inputs

    input_param = inputs[ "input" ]
    if label is not None:
        assert input_param.get_label() == label, input_param.get_label()
    if collection_type is not None:
        assert input_param.collection_type == collection_type
    return input_param


def __from_state( state ):
    trans = MockTrans()
    module = modules.module_factory.from_dict( trans, state )
    return module


def __from_step( **kwds ):
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
    for key, value in kwds.iteritems():
        setattr( step, key, value )

    return step

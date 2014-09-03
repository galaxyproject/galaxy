from galaxy import eggs
eggs.require( "mock" )


import mock

from galaxy.workflow import modules
from .workflow_support import MockTrans


def test_input_has_no_errors():
    trans = MockTrans()
    input_step_module = modules.module_factory.new( trans, 'data_input' )
    assert not input_step_module.get_errors()


def test_valid_new_tool_has_no_errors():
    trans = MockTrans()
    mock_tool = mock.Mock()
    trans.app.toolbox.tools[ "cat1" ] = mock_tool
    tool_module = modules.module_factory.new( trans, 'tool', tool_id="cat1" )
    assert not tool_module.get_errors()


def test_cannot_create_tool_modules_for_missing_tools():
    trans = MockTrans()
    exception = False
    try:
        modules.module_factory.new( trans, 'tool', tool_id="cat1" )
    except Exception:
        exception = True
    assert exception

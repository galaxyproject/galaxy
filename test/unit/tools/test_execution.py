""" Test Tool execution and state handling logic.
"""

from unittest import TestCase

import galaxy.model
from galaxy.tools import DefaultToolState
from galaxy.tools.parameters import params_to_incoming
from galaxy.util.bunch import Bunch
from galaxy.util import string_to_object
from galaxy.util import object_to_string
from galaxy.util.odict import odict
import tools_support

from galaxy import eggs
eggs.require( "Paste" )
from paste import httpexceptions

# Tool with a repeat parameter, to test state update.
REPEAT_TOOL_CONTENTS = '''<tool id="test_tool" name="Test Tool">
    <command>echo "$param1" #for $r in $repeat# "$r.param2" #end for# &lt; $out1</command>
    <inputs>
        <param type="text" name="param1" value="" />
        <repeat name="repeat1" label="Repeat 1">
            <param type="text" name="param2" value="" />
        </repeat>
    </inputs>
    <outputs>
        <data name="out1" format="data" />
    </outputs>
</tool>
'''


class ToolExecutionTestCase( TestCase, tools_support.UsesApp, tools_support.UsesTools ):

    def setUp(self):
        self.setup_app()
        self.history = galaxy.model.History()
        self.trans = MockTrans( self.app, self.history )
        self.tool_action = MockAction( self.trans )

    def tearDown(self):
        self.tear_down_app()

    def test_state_new( self ):
        self._init_tool( tools_support.SIMPLE_TOOL_CONTENTS )
        template, template_vars = self.__handle_with_incoming(
            param1="moo",
            # no runtool_btn, just rerenders the form mako with tool
            # state populated.
        )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert state.inputs[ "param1" ] == "moo"

    def test_execute( self ):
        self._init_tool( tools_support.SIMPLE_TOOL_CONTENTS )
        template, template_vars = self.__handle_with_incoming(
            param1="moo",
            runtool_btn="dummy",
        )
        self.__assert_exeuted( template, template_vars )
        # Didn't specify a rerun_remap_id so this should be None
        assert self.tool_action.execution_call_args[ 0 ][ "rerun_remap_job_id" ] is None

    def test_execute_exception( self ):
        self._init_tool( tools_support.SIMPLE_TOOL_CONTENTS )
        self.tool_action.raise_exception( )
        template, template_vars = self.__handle_with_incoming(
            param1="moo",
            runtool_btn="dummy",
        )
        assert template == "message.mako"
        assert template_vars[ "status" ] == "error"
        assert "Error executing tool" in template_vars[ "message" ]

    def test_execute_errors( self ):
        self._init_tool( tools_support.SIMPLE_TOOL_CONTENTS )
        self.tool_action.return_error( )
        template, template_vars = self.__handle_with_incoming(
            param1="moo",
            runtool_btn="dummy",
        )
        assert template == "message.mako"
        assert template_vars[ "status" ] == "error"
        assert "Test Error Message" in template_vars[ "message" ], template_vars

    def test_redirect( self ):
        self._init_tool( tools_support.SIMPLE_TOOL_CONTENTS )
        self.tool_action.expect_redirect = True
        redirect_raised = False
        try:
            template, template_vars = self.__handle_with_incoming(
                param1="moo",
                runtool_btn="dummy",
            )
        except httpexceptions.HTTPFound:
            redirect_raised = True
        assert redirect_raised

    def test_remap_job( self ):
        self._init_tool( tools_support.SIMPLE_TOOL_CONTENTS )
        template, template_vars = self.__handle_with_incoming(
            param1="moo",
            rerun_remap_job_id=self.app.security.encode_id(123),
            runtool_btn="dummy",
        )
        self.__assert_exeuted( template, template_vars )
        assert self.tool_action.execution_call_args[ 0 ][ "rerun_remap_job_id" ] == 123

    def test_invalid_remap_job( self ):
        self._init_tool( tools_support.SIMPLE_TOOL_CONTENTS )
        template, template_vars = self.__handle_with_incoming(
            param1="moo",
            rerun_remap_job_id='123',  # Not encoded
            runtool_btn="dummy",
        )
        assert template == "message.mako"
        assert template_vars[ "status" ] == "error"
        assert "invalid job" in template_vars[ "message" ]

    def test_repeat_state_updates( self ):
        self._init_tool( REPEAT_TOOL_CONTENTS )

        # Fresh state contains no repeat elements
        template, template_vars = self.__handle_with_incoming()
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert len( state.inputs[ "repeat1" ] ) == 0

        # Hitting add button adds repeat element
        template, template_vars = self.__handle_with_incoming(
            repeat1_add="dummy",
        )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert len( state.inputs[ "repeat1" ] ) == 1

        # Hitting add button again adds another repeat element
        template, template_vars = self.__handle_with_incoming( state, **{
            "repeat1_add": "dummy",
            "repeat1_0|param2": "moo2",
        } )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert len( state.inputs[ "repeat1" ] ) == 2
        assert state.inputs[ "repeat1" ][ 0 ][ "param2" ] == "moo2"

        # Hitting remove drops a repeat element
        template, template_vars = self.__handle_with_incoming( state, repeat1_1_remove="dummy" )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert len( state.inputs[ "repeat1" ] ) == 1

    def test_data_param_execute( self ):
        self._init_tool( tools_support.SIMPLE_CAT_TOOL_CONTENTS )
        hda = self.__add_dataset(1)
        # Execute tool action
        template, template_vars = self.__handle_with_incoming(
            param1=1,
            runtool_btn="dummy",
        )
        self.__assert_exeuted( template, template_vars )
        # Tool 'executed' once, with hda as param1
        assert len( self.tool_action.execution_call_args ) == 1
        assert self.tool_action.execution_call_args[ 0 ][ "incoming" ][ "param1" ] == hda

    def test_data_param_state_update( self ):
        self._init_tool( tools_support.SIMPLE_CAT_TOOL_CONTENTS )
        hda = self.__add_dataset( 1 )
        # Update state
        template, template_vars = self.__handle_with_incoming(
            param1=1,
        )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert hda == state.inputs[ "param1" ]

    def __handle_with_incoming( self, previous_state=None, **kwds ):
        """ Execute tool.handle_input with incoming specified by kwds
        (optionally extending a previous state).
        """
        if previous_state:
            incoming = self.__to_incoming( previous_state, **kwds)
        else:
            incoming = kwds
        return self.tool.handle_input(
            trans=self.trans,
            incoming=incoming,
        )

    def __to_incoming( self, state, **kwds ):
        new_incoming = {}
        params_to_incoming( new_incoming, self.tool.inputs, state.inputs, self.app )
        new_incoming[ "tool_state" ] = self.__state_to_string( state )
        new_incoming.update( kwds )
        return new_incoming

    def __add_dataset( self, id, state='ok' ):
        hda = galaxy.model.HistoryDatasetAssociation()
        hda.id = id
        hda.dataset = galaxy.model.Dataset()
        hda.dataset.state = 'ok'

        self.trans.sa_session.model_objects[ galaxy.model.HistoryDatasetAssociation ][ id ] = hda
        self.history.datasets.append( hda )
        return hda

    def __assert_rerenders_tool_without_errors( self, template, template_vars ):
        assert template == "tool_form.mako"
        self.__assert_no_errors( template_vars )
        state = template_vars[ "tool_state" ]
        return state

    def __assert_exeuted( self, template, template_vars ):
        if template == "tool_form.mako":
            self.__assert_no_errors( template_vars )
        self.assertEquals(template, "tool_executed.mako")

    def __assert_no_errors( self, template_vars ):
        assert "errors" in template_vars, "tool_form.mako rendered without errors defintion."
        errors = template_vars[ "errors" ]
        assert not errors, "Template rendered unexpected errors - %s" % errors

    def __string_to_state( self, state_string ):
        encoded_state = string_to_object( state_string )
        state = DefaultToolState()
        state.decode( encoded_state, self.tool, self.app )
        return state

    def __inputs_to_state( self, inputs ):
        tool_state = DefaultToolState()
        tool_state.inputs = inputs
        return tool_state

    def __state_to_string( self, tool_state ):
        return object_to_string( tool_state.encode( self.tool, self.app ) )

    def __inputs_to_state_string( self, inputs ):
        tool_state = self.__inputs_to_state( inputs )
        return self.__state_to_string( tool_state )


class MockAction( object ):

    def __init__( self, expected_trans ):
        self.expected_trans = expected_trans
        self.execution_call_args = []
        self.expect_redirect = False
        self.exception_after_exection = None
        self.error_message_after_excution = None

    def execute( self, tool, trans, **kwds ):
        assert self.expected_trans == trans
        self.execution_call_args.append( kwds )
        num_calls = len( self.execution_call_args )
        if self.expect_redirect:
            raise httpexceptions.HTTPFound( "http://google.com" )
        if self.exception_after_exection is not None:
            if num_calls > self.exception_after_exection:
                raise Exception( "Test Exception" )
        if self.error_message_after_excution is not None:
            if num_calls > self.error_message_after_excution:
                return None, "Test Error Message"

        return None, odict(dict(out1="1"))

    def raise_exception( self, after_execution=0 ):
        self.exception_after_exection = after_execution

    def return_error( self, after_execution=0 ):
        self.error_message_after_excution = after_execution


class MockTrans( object ):

    def __init__( self, app, history ):
        self.app = app
        self.history = history
        self.history = galaxy.model.History()
        self.workflow_building_mode = False
        self.webapp = Bunch( name="galaxy" )
        self.sa_session = self.app.model.context

    def get_history( self ):
        return self.history

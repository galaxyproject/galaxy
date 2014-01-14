""" Test Tool execution and state handling logic.
"""
import os

from unittest import TestCase

import galaxy.model
from galaxy.tools import Tool
from galaxy.tools import DefaultToolState
from galaxy.tools.parameters import params_to_incoming
from galaxy.util import parse_xml
from galaxy.util.bunch import Bunch
from galaxy.util import string_to_object
from galaxy.util import object_to_string
from galaxy.util.odict import odict
from tools_support import UsesApp

# Simple tool with just one text parameter and output.
SIMPLE_TOOL_CONTENTS = '''<tool id="test_tool" name="Test Tool">
    <command>echo "$param1" &lt; $out1</command>
    <inputs>
        <param type="text" name="param1" value="" />
    </inputs>
    <outputs>
        <output name="out1" format="data" />
    </outputs>
</tool>'''

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
        <output name="out1" format="data" />
    </outputs>
</tool>
'''

# A tool with data parameters (kind of like cat1) my favorite test tool :)
SIMPLE_CAT_TOOL_CONTENTS = '''<tool id="test_tool" name="Test Tool">
    <command>cat "$param1" #for $r in $repeat# "$r.param2" #end for# &lt; $out1</command>
    <inputs>
        <param type="data" format="tabular" name="param1" value="" />
        <repeat name="repeat1" label="Repeat 1">
            <param type="data" format="tabular" name="param2" value="" />
        </repeat>
    </inputs>
    <outputs>
        <output name="out1" format="data" />
    </outputs>
</tool>
'''


class ToolExecutionTestCase( TestCase, UsesApp ):

    def setUp(self):
        self.setup_app()
        self.history = galaxy.model.History()
        self.app.job_config["get_job_tool_configurations"] = lambda ids: None
        self.app.config.drmaa_external_runjob_script = ""
        self.app.config.tool_secret = "testsecret"
        self.trans = MockTrans( self.app, self.history )
        self.tool_action = MockAction( self.trans )
        self.tool_file = os.path.join( self.test_directory, "tool.xml" )

    def tearDown(self):
        self.tear_down_app()

    def test_state_new( self ):
        self.__init_tool( SIMPLE_TOOL_CONTENTS )
        template, template_vars = self.__handle_with_incoming(
            param1="moo",
            # no runtool_btn, just rerenders the form mako with tool
            # state populated.
        )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert state.inputs[ "param1" ] == "moo"

    def test_execute( self ):
        self.__init_tool( SIMPLE_TOOL_CONTENTS )
        template, template_vars = self.__handle_with_incoming(
            param1="moo",
            runtool_btn="dummy",
        )
        assert template == "tool_executed.mako"
        # Didn't specify a rerun_remap_id so this should be None
        assert self.tool_action.execution_call_args[ 0 ][ "rerun_remap_job_id" ] is None

    def test_remap_job( self ):
        self.__init_tool( SIMPLE_TOOL_CONTENTS )
        template, template_vars = self.__handle_with_incoming(
            param1="moo",
            rerun_remap_job_id=self.app.security.encode_id(123),
            runtool_btn="dummy",
        )
        assert template == "tool_executed.mako"
        assert self.tool_action.execution_call_args[ 0 ][ "rerun_remap_job_id" ] == 123

    def test_invalid_remap_job( self ):
        self.__init_tool( SIMPLE_TOOL_CONTENTS )
        template, template_vars = self.__handle_with_incoming(
            param1="moo",
            rerun_remap_job_id='123',  # Not encoded
            runtool_btn="dummy",
        )
        assert template == "message.mako"
        assert template_vars[ "status" ] == "error"
        assert "invalid job" in template_vars[ "message" ]

    def test_repeat_state_updates( self ):
        self.__init_tool( REPEAT_TOOL_CONTENTS )

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
        self.__init_tool( SIMPLE_CAT_TOOL_CONTENTS )
        hda = self.__add_dataset(1)
        # Execute tool action
        template, template_vars = self.__handle_with_incoming(
            param1=1,
            runtool_btn="dummy",
        )
        assert template == "tool_executed.mako"
        # Tool 'executed' once, with hda as param1
        assert len( self.tool_action.execution_call_args ) == 1
        assert self.tool_action.execution_call_args[ 0 ][ "incoming" ][ "param1" ] == hda

    def test_data_param_state_update( self ):
        self.__init_tool( SIMPLE_CAT_TOOL_CONTENTS )
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
        assert not template_vars[ "errors" ]
        state = template_vars[ "tool_state" ]
        return state

    def __init_tool( self, tool_contents ):
        self.__write_tool( tool_contents )
        self.__setup_tool( )

    def __setup_tool( self ):
        tree = parse_xml( self.tool_file )
        self.tool = Tool( self.tool_file, tree.getroot(), self.app )
        self.tool.tool_action = self.tool_action

    def __write_tool( self, contents ):
        open( self.tool_file, "w" ).write( contents )

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

    def execute( self, tool, trans, **kwds ):
        assert self.expected_trans == trans
        self.execution_call_args.append( kwds )
        return None, odict(dict(out1="1"))


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

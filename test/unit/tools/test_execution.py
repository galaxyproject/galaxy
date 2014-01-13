""" Test Tool execution and state handling logic.
"""
import os

from unittest import TestCase

import galaxy.model
from galaxy.tools import Tool
from galaxy.tools import DefaultToolState
from galaxy.util import parse_xml
from galaxy.util import string_to_object
from galaxy.util import object_to_string
from galaxy.util.odict import odict
from tools_support import UsesApp

EXAMPLE_TOOL_CONTENTS = '''<tool id="test_tool" name="Test Tool">
    <command>echo "$text" &lt; $out1</command>
    <inputs>
        <param type="text" name="param1" value="" />
    </inputs>
    <outputs>
        <output name="out1" format="data" />
    </outputs>
</tool>'''


class ToolExecutionTestCase( TestCase, UsesApp ):

    def setUp(self):
        self.setup_app()
        self.app.job_config["get_job_tool_configurations"] = lambda ids: None
        self.app.config.drmaa_external_runjob_script = ""
        self.app.config.tool_secret = "testsecret"
        self.trans = MockTrans( self.app )
        self.tool_action = MockAction( self.trans )
        self.tool_file = os.path.join( self.test_directory, "tool.xml" )

    def tearDown(self):
        self.tear_down_app()

    def test_state_new( self ):
        self.__write_tool( EXAMPLE_TOOL_CONTENTS )
        self.__setup_tool( )
        template, template_vars = self.tool.handle_input(
            trans=self.trans,
            incoming=dict( param1="moo" )
            # no runtool_btn, just rerenders the form mako with tool
            # state populated.
        )
        assert template == "tool_form.mako"
        assert not template_vars[ "errors" ]
        state = template_vars[ "tool_state" ]
        assert state.inputs[ "param1" ] == "moo"

    def test_execute( self ):
        self.__write_tool( EXAMPLE_TOOL_CONTENTS )
        self.__setup_tool( )
        template, template_vars = self.tool.handle_input(
            trans=self.trans,
            incoming=dict( param1="moo", runtool_btn="dummy" )
        )
        assert template == "tool_executed.mako"

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

    def __inputs_to_state_string( self, inputs ):
        tool_state = self.__inputs_to_state( inputs )
        return object_to_string( tool_state.encode( self.tool, self.app ) )


class MockAction( object ):

    def __init__( self, expected_trans ):
        self.expected_trans = expected_trans
        self.execution_call_args = []

    def execute( self, tool, trans, **kwds ):
        assert self.expected_trans == trans
        self.execution_call_args.append( kwds )
        return None, odict(dict(out1="1"))


class MockTrans( object ):

    def __init__( self, app ):
        self.app = app
        self.history = galaxy.model.History()

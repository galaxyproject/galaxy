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

BASE_REPEAT_TOOL_CONTENTS = '''<tool id="test_tool" name="Test Tool">
    <command>echo "$param1" #for $r in $repeat# "$r.param2" #end for# &lt; $out1</command>
    <inputs>
        <param type="text" name="param1" value="" />
        <repeat name="repeat1" label="Repeat 1">
          %s
        </repeat>
    </inputs>
    <outputs>
        <data name="out1" format="data" />
    </outputs>
</tool>
'''

# Tool with a repeat parameter, to test state update.
REPEAT_TOOL_CONTENTS = BASE_REPEAT_TOOL_CONTENTS % '''<param type="text" name="param2" value="" />'''
REPEAT_COLLECTION_PARAM_CONTENTS = BASE_REPEAT_TOOL_CONTENTS % '''<param type="data_collection" name="param2" collection_type="paired" />'''


class ToolExecutionTestCase( TestCase, tools_support.UsesApp, tools_support.UsesTools ):

    def setUp(self):
        self.setup_app()
        self.history = galaxy.model.History()
        self.trans = MockTrans( self.app, self.history )
        self.app.dataset_collections_service = MockCollectionService()
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

    def test_simple_multirun_state_update( self ):
        hda1, hda2 = self.__setup_multirun_job()
        template, template_vars = self.__handle_with_incoming( **{
            "param1|__multirun__": [ 1, 2 ],
        } )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        self.__assert_state_serializable( state )
        self.assertEquals( state.inputs[ "param1|__multirun__" ], [ 1, 2 ] )

    def test_simple_collection_multirun_state_update( self ):
        hdca = self.__setup_collection_multirun_job()
        encoded_id = self.app.security.encode_id(hdca.id)
        template, template_vars = self.__handle_with_incoming( **{
            "param1|__collection_multirun__": encoded_id,
        } )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        self.__assert_state_serializable( state )
        self.assertEquals( state.inputs[ "param1|__collection_multirun__" ], encoded_id )

    def test_repeat_multirun_state_updates( self ):
        self._init_tool( REPEAT_TOOL_CONTENTS )

        # Fresh state contains no repeat elements
        self.__handle_with_incoming()
        # Hitting add button adds repeat element
        template, template_vars = self.__handle_with_incoming(**{
            "param1|__multirun__": [ 1, 2 ],
            "repeat1_add": "dummy",
        })
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        self.assertEquals( state.inputs[ "param1|__multirun__" ], [ 1, 2 ] )
        assert len( state.inputs[ "repeat1" ] ) == 1

        # Hitting add button again adds another repeat element
        template, template_vars = self.__handle_with_incoming( state, **{
            "repeat1_0|param2|__multirun__": [ 1, 2 ],
            "repeat1_add": "dummy",
        } )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        self.assertEquals( state.inputs[ "param1|__multirun__" ], [ 1, 2 ] )
        self.assertEquals( state.inputs[ "repeat1" ][0][ "param2|__multirun__" ], [ 1, 2 ] )

    def test_simple_multirun_execution( self ):
        hda1, hda2 = self.__setup_multirun_job()
        template, template_vars = self.__handle_with_incoming( **{
            "param1|__multirun__": [ 1, 2 ],
            "runtool_btn": "dummy",
        } )
        self.__assert_exeuted( template, template_vars )
        # Tool 'executed' twice, with param1 as hda1 and hda2 respectively.
        assert len( self.tool_action.execution_call_args ) == 2
        self.assertEquals( self.tool_action.execution_call_args[ 0 ][ "incoming" ][ "param1" ], hda1 )
        self.assertEquals( self.tool_action.execution_call_args[ 1 ][ "incoming" ][ "param1" ], hda2 )
        self.assertEquals( len( template_vars[ "jobs" ] ), 2 )

    def test_cannot_multirun_and_remap( self ):
        hda1, hda2 = self.__setup_multirun_job()
        template, template_vars = self.__handle_with_incoming( **{
            "param1|__multirun__": [ 1, 2 ],
            "rerun_remap_job_id": self.app.security.encode_id(123),  # Not encoded
            "runtool_btn": "dummy",
        } )
        self.assertEquals( template, "message.mako" )
        assert template_vars[ "status" ] == "error"
        assert "multiple jobs" in template_vars[ "message" ]

    def test_multirun_with_state_updates( self ):
        hda1, hda2 = self.__setup_multirun_job()

        # Fresh state contains no repeat elements
        template, template_vars = self.__handle_with_incoming()
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert len( state.inputs[ "repeat1" ] ) == 0
        self.__assert_state_serializable( state )

        # Hitting add button adds repeat element
        template, template_vars = self.__handle_with_incoming( **{
            "param1|__multirun__": [ 1, 2 ],
            "repeat1_add": "dummy",
        } )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert len( state.inputs[ "repeat1" ] ) == 1
        self.assertEquals( state.inputs[ "param1|__multirun__" ], [ 1, 2 ] )
        self.__assert_state_serializable( state )

        # Hitting add button again adds another repeat element
        template, template_vars = self.__handle_with_incoming( state, **{
            "repeat1_add": "dummy",
            "repeat1_0|param2": 1,
        } )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        self.assertEquals( state.inputs[ "param1|__multirun__" ], [ 1, 2 ] )
        assert len( state.inputs[ "repeat1" ] ) == 2
        assert state.inputs[ "repeat1" ][ 0 ][ "param2" ] == hda1
        self.__assert_state_serializable( state )

        # Hitting remove drops a repeat element
        template, template_vars = self.__handle_with_incoming( state, repeat1_1_remove="dummy" )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert len( state.inputs[ "repeat1" ] ) == 1
        self.__assert_state_serializable( state )

    def test_collection_multirun_with_state_updates( self ):
        hda1, hda2 = self.__setup_multirun_job()
        collection = self.__history_dataset_collection_for( [ hda1, hda2 ] )
        collection_id = self.app.security.encode_id( collection.id )
        self.app.dataset_collections_service = Bunch(
            match_collections=lambda collections: None
        )
        template, template_vars = self.__handle_with_incoming( **{
            "param1|__collection_multirun__": collection_id,
            "runtool_btn": "dummy",
        } )
        self.__assert_exeuted( template, template_vars )

    def test_subcollection_multirun_with_state_updates( self ):
        self._init_tool( REPEAT_COLLECTION_PARAM_CONTENTS )
        hda1, hda2 = self.__add_dataset( 1 ), self.__add_dataset( 2 )
        collection = self.__history_dataset_collection_for( [ hda1, hda2 ], collection_type="list:paired" )
        collection_id = self.app.security.encode_id( collection.id )
        self.app.dataset_collections_service = Bunch(
            match_collections=lambda collections: None
        )
        template, template_vars = self.__handle_with_incoming(
            repeat1_add="dummy",
        )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert len( state.inputs[ "repeat1" ] ) == 1
        template, template_vars = self.__handle_with_incoming( state, **{
            "repeat1_0|param2|__collection_multirun__": "%s|paired" % collection_id,
            "repeat1_add": "dummy",
        } )
        state = self.__assert_rerenders_tool_without_errors( template, template_vars )
        assert state.inputs[ "repeat1" ][ 0 ][ "param2|__collection_multirun__" ] == "%s|paired" % collection_id

    def __history_dataset_collection_for( self, hdas, collection_type="list", id=1234 ):
        collection = galaxy.model.DatasetCollection(
            collection_type=collection_type,
        )
        to_element = lambda hda: galaxy.model.DatasetCollectionElement(
            collection=collection,
            element=hda,
        )
        elements = map(to_element, hdas)
        if collection_type == "list:paired":
            paired_collection = galaxy.model.DatasetCollection(
                collection_type="paired",
            )
            paired_collection.elements = elements
            list_dce = galaxy.model.DatasetCollectionElement(
                collection=collection,
                element=paired_collection,
            )
            elements = [ list_dce ]

        collection.elements = elements

        history_dataset_collection_association = galaxy.model.HistoryDatasetCollectionAssociation(
            id=id,
            collection=collection,
        )
        hdcas = self.trans.sa_session.model_objects[ galaxy.model.HistoryDatasetCollectionAssociation ]
        hdcas[ id ] = history_dataset_collection_association
        return history_dataset_collection_association

    def __assert_state_serializable( self, state ):
        self.__state_to_string( state )  # Will thrown exception if there is a problem...

    def __setup_multirun_job( self ):
        self._init_tool( tools_support.SIMPLE_CAT_TOOL_CONTENTS )
        hda1, hda2 = self.__add_dataset( 1 ), self.__add_dataset( 2 )
        return hda1, hda2

    def __setup_collection_multirun_job( self ):
        self._init_tool( tools_support.SIMPLE_CAT_TOOL_CONTENTS )
        hdca = self.__add_collection_dataset( 1 )
        return hdca

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
        # Copy meta parameters over lost by params_to_incoming...
        for key, value in state.inputs.iteritems():
            if key.endswith( "|__multirun__" ):
                new_incoming[ key ] = value
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

    def __add_collection_dataset( self, id, collection_type="paired", *hdas ):
        hdca = galaxy.model.HistoryDatasetCollectionAssociation()
        hdca.id = id
        collection = galaxy.model.DatasetCollection()
        hdca.collection = collection
        collection.elements = [ galaxy.model.DatasetCollectionElement(element=self.__add_dataset( 1 )) ]
        collection.type = collection_type
        self.trans.sa_session.model_objects[ galaxy.model.HistoryDatasetCollectionAssociation ][ id ] = hdca
        self.history.dataset_collections.append( hdca )
        return hdca

    def __assert_rerenders_tool_without_errors( self, template, template_vars ):
        assert template == "tool_form.mako"
        self.__assert_no_errors( template_vars )
        state = template_vars[ "tool_state" ]
        return state

    def __assert_exeuted( self, template, template_vars ):
        if template == "tool_form.mako":
            self.__assert_no_errors( template_vars )
        self.assertEquals(
            template,
            "tool_executed.mako",
            "Expected tools_execute template - got template %s with vars %s" % ( template, template_vars)
        )

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

        return galaxy.model.Job(), odict(dict(out1="1"))

    def raise_exception( self, after_execution=0 ):
        self.exception_after_exection = after_execution

    def return_error( self, after_execution=0 ):
        self.error_message_after_excution = after_execution


class MockTrans( object ):

    def __init__( self, app, history ):
        self.app = app
        self.history = history
        self.history._active_datasets_children_and_roles = filter( lambda hda: hda.active and hda.history == history, self.app.model.context.model_objects[ galaxy.model.HistoryDatasetAssociation ] )
        self.workflow_building_mode = False
        self.webapp = Bunch( name="galaxy" )
        self.sa_session = self.app.model.context

    def get_history( self ):
        return self.history


class MockCollectionService( object ):

    def __init__( self ):
        self.collection_info = object()

    def match_collections( self, collections_to_match ):
        return self.collection_info

import unittest

from galaxy import model
from galaxy.tools.actions import DefaultToolAction

import tools_support

TEST_HANDLER_NAME = "test_handler_1"


# I cannot think of a saner way to test if data is being wrapped than use a
# data param in the output label - though you would probably never want to do
# this.
DATA_IN_LABEL_TOOL_CONTENTS = '''<tool id="test_tool" name="Test Tool">
    <command>echo "$param1" &lt; $out1</command>
    <inputs>
        <repeat name="repeat1" label="The Repeat">
            <param type="data" name="param1" value="" />
        </repeat>
    </inputs>
    <outputs>
        <data name="out1" format="data" label="Output (${repeat1[0].param1})" />
    </outputs>
</tool>
'''


class DefaultToolActionTestCase( unittest.TestCase, tools_support.UsesApp, tools_support.UsesTools ):

    def setUp( self ):
        self.setup_app( mock_model=False )
        history = model.History()
        self.history = history
        self.trans = MockTrans(
            self.app,
            self.history
        )
        self.app.model.context.add( history )
        self.app.model.context.flush()
        self.action = DefaultToolAction()
        self.app.config.len_file_path = "moocow"
        self.app.job_config[ "get_handler" ] = lambda h: TEST_HANDLER_NAME
        self.app.object_store = MockObjectStore()

    def test_output_created( self ):
        _, output = self._simple_execute()
        assert len( output ) == 1
        assert "out1" in output

    def test_output_label( self ):
        _, output = self._simple_execute()
        self.assertEquals( output[ "out1" ].name, "Output (moo)" )

    def test_output_label_data( self ):
        hda1 = self.__add_dataset()
        hda2 = self.__add_dataset()
        incoming = {
            "param1": hda1,
            "repeat1": [
                {"param2": hda2},
            ]
        }
        job, output = self._simple_execute(
            tools_support.SIMPLE_CAT_TOOL_CONTENTS,
            incoming,
        )
        self.assertEquals( output[ "out1" ].name, "Test Tool on data 2 and data 1" )

    def test_params_wrapped( self ):
        hda1 = self.__add_dataset()
        _, output = self._simple_execute(
            contents=DATA_IN_LABEL_TOOL_CONTENTS,
            incoming=dict( repeat1=[ dict( param1=hda1 ) ] ),
        )
        # Again this is a stupid way to ensure data parameters are wrapped.
        self.assertEquals( output[ "out1" ].name, "Output (%s)" % hda1.dataset.get_file_name() )

    def test_handler_set( self ):
        job, _ = self._simple_execute()
        assert job.handler == TEST_HANDLER_NAME

    def __add_dataset( self, state='ok' ):
        hda = model.HistoryDatasetAssociation()
        hda.dataset = model.Dataset()
        hda.dataset.state = 'ok'
        hda.dataset.external_filename = "/tmp/datasets/dataset_001.dat"
        self.history.add_dataset( hda )
        self.app.model.context.flush()
        return hda

    def _simple_execute( self, contents=None, incoming=None ):
        if contents is None:
            contents = tools_support.SIMPLE_TOOL_CONTENTS
        if incoming is None:
            incoming = dict(param1="moo")
        self._init_tool( contents )
        return self.action.execute(
            tool=self.tool,
            trans=self.trans,
            history=self.history,
            incoming=incoming,
        )


class MockTrans( object ):

    def __init__( self, app, history, user=None ):
        self.app = app
        self.history = history
        self.user = user
        self.sa_session = self.app.model.context
        self.model = app.model

    def db_dataset_for( self, input_db_key ):
        return None

    def get_galaxy_session( self ):
        return model.GalaxySession()

    def get_current_user_roles( self ):
        return []

    def log_event( self, *args, **kwargs ):
        pass


class MockObjectStore( object ):

    def __init__( self ):
        self.created_datasets = []

    def create( self, dataset ):
        self.created_datasets.append( dataset )

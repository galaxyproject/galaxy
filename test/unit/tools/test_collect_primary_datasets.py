import os
import json
import unittest

import tools_support

from galaxy import model

DEFAULT_TOOL_OUTPUT = "out1"
DEFAULT_EXTRA_NAME = "test1"


class CollectPrimaryDatasetsTestCase( unittest.TestCase, tools_support.UsesApp, tools_support.UsesTools ):

    def setUp( self ):
        self.setup_app( mock_model=False )
        object_store = MockObjectStore()
        self.app.object_store = object_store
        self._init_tool( tools_support.SIMPLE_TOOL_CONTENTS )
        self._setup_test_output( )
        self.app.config.collect_outputs_from = "job_working_directory"

        self.app.model.Dataset.object_store = object_store

    def tearDown( self ):
        if self.app.model.Dataset.object_store is self.app.object_store:
            self.app.model.Dataset.object_store = None

    def test_empty_collect( self ):
        assert len( self._collect() ) == 0

    def test_collect_multiple( self ):
        path1 = self._setup_extra_file( name="test1" )
        path2 = self._setup_extra_file( name="test2" )

        datasets = self._collect()
        assert DEFAULT_TOOL_OUTPUT in datasets
        self.assertEquals( len( datasets[ DEFAULT_TOOL_OUTPUT ] ), 2 )

        created_hda_1 = datasets[ DEFAULT_TOOL_OUTPUT ][ "test1" ]
        self.app.object_store.assert_created_with_path( created_hda_1.dataset, path1 )

        created_hda_2 = datasets[ DEFAULT_TOOL_OUTPUT ][ "test2" ]
        self.app.object_store.assert_created_with_path( created_hda_2.dataset, path2 )

        # Test default metadata stuff
        assert created_hda_1.visible
        assert created_hda_1.dbkey == "?"

    def test_collect_hidden( self ):
        self._setup_extra_file( visible="hidden" )
        created_hda = self._collect_default_extra()
        assert not created_hda.visible

    def test_collect_ext( self ):
        self._setup_extra_file( ext="txt" )
        created_hda = self._collect_default_extra()
        assert created_hda.ext == "txt"

    def test_copied_to_imported_histories( self ):
        self._setup_extra_file( )
        cloned_hda = self.hda.copy()
        history_2 = self._new_history( hdas=[ cloned_hda ])
        assert len( history_2.datasets ) == 1

        self._collect()

        # Make sure extra primary was copied to cloned history with
        # cloned output.
        assert len( history_2.datasets ) == 2

    def test_dbkey_from_filename( self ):
        self._setup_extra_file( dbkey="hg19" )
        created_hda = self._collect_default_extra()
        assert created_hda.dbkey == "hg19"

    def test_dbkey_from_galaxy_json( self ):
        path = self._setup_extra_file( )
        self._append_job_json( dict( dbkey="hg19" ), output_path=path )
        created_hda = self._collect_default_extra()
        assert created_hda.dbkey == "hg19"

    def test_name_from_galaxy_json( self ):
        path = self._setup_extra_file( )
        self._append_job_json( dict( name="test_from_json" ), output_path=path )
        created_hda = self._collect_default_extra()
        assert "test_from_json" in created_hda.name

    def test_info_from_galaxy_json( self ):
        path = self._setup_extra_file( )
        self._append_job_json( dict( info="extra output info" ), output_path=path )
        created_hda = self._collect_default_extra()
        assert created_hda.info == "extra output info"

    def test_extension_from_galaxy_json( self ):
        path = self._setup_extra_file( )
        self._append_job_json( dict( ext="txt" ), output_path=path )
        created_hda = self._collect_default_extra()
        assert created_hda.ext == "txt"

    def test_new_file_path_collection( self ):
        self.app.config.collect_outputs_from = "new_file_path"
        self.app.config.new_file_path = self.test_directory

        self._setup_extra_file( )
        created_hda = self._collect_default_extra( job_working_directory="/tmp" )
        assert created_hda

    def test_job_param( self ):
        self._setup_extra_file( )
        assert len( self.job.output_datasets ) == 1
        self._collect_default_extra()
        assert len( self.job.output_datasets ) == 2
        extra_job_assoc = filter( lambda job_assoc: job_assoc.name.startswith( "__" ), self.job.output_datasets )[ 0 ]
        assert extra_job_assoc.name == "__new_primary_file_out1|test1__"

    def _collect_default_extra( self, **kwargs ):
        return self._collect( **kwargs )[ DEFAULT_TOOL_OUTPUT ][ DEFAULT_EXTRA_NAME ]

    def _collect( self, job_working_directory=None ):
        if not job_working_directory:
            job_working_directory = self.test_directory
        return self.tool.collect_primary_datasets( self.outputs, job_working_directory )

    def _append_job_json( self, object, output_path=None, line_type="new_primary_dataset" ):
        object[ "type" ] = line_type
        if output_path:
            name = os.path.basename( output_path )
            object[ "filename" ] = name
        line = json.dumps( object )
        with open( os.path.join( self.test_directory, "galaxy.json" ), "a" ) as f:
            f.write( "%s\n" % line )

    def _setup_extra_file( self, **kwargs ):
        path = kwargs.get( "path", None )
        if not path:
            name = kwargs.get( "name", DEFAULT_EXTRA_NAME )
            visible = kwargs.get( "visible", "visible" )
            ext = kwargs.get( "ext", "data" )
            template_args = ( self.hda.id, name, visible, ext )
            directory = kwargs.get( "directory", self.test_directory )
            path = os.path.join( directory, "primary_%s_%s_%s_%s" % template_args )
            if "dbkey" in kwargs:
                path = "%s_%s" % ( path, kwargs[ "dbkey" ] )
        contents = kwargs.get( "contents", "test contents" )
        open( path, "w" ).write( contents )
        return path

    def _setup_test_output( self ):
        dataset = model.Dataset()
        dataset.external_filename = "example_output"  # This way object store isn't asked about size...
        self.hda = model.HistoryDatasetAssociation( name="test", dataset=dataset )
        job = model.Job()
        job.add_output_dataset( DEFAULT_TOOL_OUTPUT, self.hda )
        self.app.model.context.add( job )
        self.job = job
        self.history = self._new_history( hdas=[ self.hda ] )
        self.outputs = { DEFAULT_TOOL_OUTPUT: self.hda }

    def _new_history( self, hdas=[], flush=True ):
        history = model.History()
        self.app.model.context.add( history )
        for hda in hdas:
            history.add_dataset( hda, set_hid=False )
        self.app.model.context.flush( )
        return history


class MockObjectStore( object ):

    def __init__( self ):
        self.created_datasets = {}

    def update_from_file( self, dataset, file_name, create ):
        if create:
            self.created_datasets[ dataset ] = file_name

    def size( self, dataset ):
        path = self.created_datasets[ dataset ]
        return os.stat( path ).st_size

    def get_filename( self, dataset ):
        return self.created_datasets[ dataset ]

    def assert_created_with_path( self, dataset, file_name ):
        assert self.created_datasets[ dataset ] == file_name

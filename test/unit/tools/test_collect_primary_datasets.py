import os
import json
import unittest

import tools_support

from galaxy import model
from galaxy import util
from galaxy.tools.parameters import output_collect

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

    def test_pattern_override_designation( self ):
        self._replace_output_collectors( '''<output><discover_datasets pattern="__designation__" directory="subdir" ext="txt" /></output>''' )
        self._setup_extra_file( subdir="subdir", filename="foo.txt" )
        primary_outputs = self._collect( )[ DEFAULT_TOOL_OUTPUT ]
        assert len( primary_outputs ) == 1
        created_hda = primary_outputs.values()[ 0 ]
        assert "foo.txt" in created_hda.name
        assert created_hda.ext == "txt"

    def test_name_and_ext_pattern( self ):
        self._replace_output_collectors( '''<output><discover_datasets pattern="__name_and_ext__" directory="subdir" /></output>''' )
        self._setup_extra_file( subdir="subdir", filename="foo1.txt" )
        self._setup_extra_file( subdir="subdir", filename="foo2.tabular" )
        primary_outputs = self._collect( )[ DEFAULT_TOOL_OUTPUT ]
        assert len( primary_outputs ) == 2
        assert primary_outputs[ "foo1" ].ext == "txt"
        assert primary_outputs[ "foo2" ].ext == "tabular"

    def test_custom_pattern( self ):
        # Hypothetical oral metagenomic classifier that populates a directory
        # of files based on name and genome. Use custom regex pattern to grab
        # and classify these files.
        self._replace_output_collectors( '''<output><discover_datasets pattern="(?P&lt;designation&gt;.*)__(?P&lt;dbkey&gt;.*).fasta" directory="genome_breakdown" ext="fasta" /></output>''' )
        self._setup_extra_file( subdir="genome_breakdown", filename="samp1__hg19.fasta" )
        self._setup_extra_file( subdir="genome_breakdown", filename="samp2__lactLact.fasta" )
        self._setup_extra_file( subdir="genome_breakdown", filename="samp3__hg19.fasta" )
        self._setup_extra_file( subdir="genome_breakdown", filename="samp4__lactPlan.fasta" )
        self._setup_extra_file( subdir="genome_breakdown", filename="samp5__fusoNucl.fasta" )

        # Put a file in directory we don't care about, just to make sure
        # it doesn't get picked up by pattern.
        self._setup_extra_file( subdir="genome_breakdown", filename="overview.txt" )

        primary_outputs = self._collect( )[ DEFAULT_TOOL_OUTPUT ]
        assert len( primary_outputs ) == 5
        genomes = dict( samp1="hg19", samp2="lactLact", samp3="hg19", samp4="lactPlan", samp5="fusoNucl" )
        for key, hda in primary_outputs.iteritems():
            assert hda.dbkey == genomes[ key ]

    def test_name_versus_designation( self ):
        """ This test demonstrates the difference between name and desgination
        in grouping patterns and named patterns such as __designation__,
        __name__, __designation_and_ext__, and __name_and_ext__.
        """
        self._replace_output_collectors( '''<output>
            <discover_datasets pattern="__name_and_ext__" directory="subdir_for_name_discovery" />
            <discover_datasets pattern="__designation_and_ext__" directory="subdir_for_designation_discovery" />
        </output>''')
        self._setup_extra_file( subdir="subdir_for_name_discovery", filename="example1.txt" )
        self._setup_extra_file( subdir="subdir_for_designation_discovery", filename="example2.txt" )
        primary_outputs = self._collect( )[ DEFAULT_TOOL_OUTPUT ]
        name_output = primary_outputs[ "example1" ]
        designation_output = primary_outputs[ "example2" ]
        # While name is also used for designation, designation is not the name -
        # it is used in the calculation of the name however...
        assert name_output.name == "example1"
        assert designation_output.name == "%s (%s)" % ( self.hda.name, "example2" )

    def test_cannot_read_files_outside_job_directory( self ):
        self._replace_output_collectors( '''<output>
            <discover_datasets pattern="__name_and_ext__" directory="../../secrets" />
        </output>''')
        exception_thrown = False
        try:
            self._collect( )
        except Exception:
            exception_thrown = True
        assert exception_thrown

    def _collect_default_extra( self, **kwargs ):
        return self._collect( **kwargs )[ DEFAULT_TOOL_OUTPUT ][ DEFAULT_EXTRA_NAME ]

    def _collect( self, job_working_directory=None ):
        if not job_working_directory:
            job_working_directory = self.test_directory
        return self.tool.collect_primary_datasets( self.outputs, job_working_directory, "txt" )

    def _replace_output_collectors( self, xml_str ):
        # Rewrite tool as if it had been created with output containing
        # supplied dataset_collector elem.
        elem = util.parse_xml_string( xml_str )
        self.tool.outputs[ DEFAULT_TOOL_OUTPUT ].dataset_collectors = output_collect.dataset_collectors_from_elem( elem )

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
        filename = kwargs.get( "filename", None )
        if not path and not filename:
            name = kwargs.get( "name", DEFAULT_EXTRA_NAME )
            visible = kwargs.get( "visible", "visible" )
            ext = kwargs.get( "ext", "data" )
            template_args = ( self.hda.id, name, visible, ext )
            directory = kwargs.get( "directory", self.test_directory )
            path = os.path.join( directory, "primary_%s_%s_%s_%s" % template_args )
            if "dbkey" in kwargs:
                path = "%s_%s" % ( path, kwargs[ "dbkey" ] )
        if not path:
            assert filename
            subdir = kwargs.get( "subdir", "." )
            path = os.path.join( self.test_directory, subdir, filename )
        directory = os.path.dirname( path )
        if not os.path.exists( directory ):
            os.makedirs( directory )
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

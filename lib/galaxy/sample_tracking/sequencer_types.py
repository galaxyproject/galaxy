import logging, os, sys
from galaxy.util.odict import odict
from galaxy.util.bunch import Bunch
from galaxy import util, jobs, model
from galaxy.forms.forms import form_factory
from elementtree.ElementTree import XML
from galaxy.sample_tracking.data_transfer import data_transfer_factories
log = logging.getLogger( __name__ )

class SequencerTypeNotFoundException( Exception ):
    pass

class SequencerTypesCollection( object ):

    def __init__( self, config_filename, root_dir, app ):
        self.all_sequencer_types = odict()
        self.root_dir = root_dir
        self.app = app
        try:
            self.load_all( config_filename )
        except:
            log.exception( "SequencerTypesCollection error reading %s", config_filename )

    def load_all( self, config_filename ):
        tree = util.parse_xml( config_filename )
        root = tree.getroot()
        for elem in root:
            try:
                if elem.tag == 'sequencer_type':
                    file_path = elem.get( "file" )
                    visible = util.string_as_bool( elem.get( "visible" ) )
                    sequencer_type = self.load_sequencer_type( os.path.join( self.root_dir, file_path ), visible )
                    self.all_sequencer_types[ sequencer_type.id ] = sequencer_type
                    log.debug( "Loaded sequencer_type: %s %s" % ( sequencer_type.name, sequencer_type.config_version ) )
            except:
                log.exception( "error reading sequencer_type from path: %s" % file_path )        
    def load_sequencer_type( self, config_file, visible=True ):
        # Parse XML configuration file and get the root element
        tree = util.parse_xml( config_file )
        root = tree.getroot()
        return SequencerType( config_file, root, visible )
    
    def reload( self, sequencer_type_id ):
        """
        Attempt to reload the sequencer_type identified by 'sequencer_type_id', if successful
        replace the old sequencer_type.
        """
        if sequencer_type_id not in self.all_sequencer_types.keys():
            raise SequencerTypeNotFoundException( "No sequencer_type with id %s" % sequencer_type_id )
        old_sequencer_type = self.all_sequencer_types[ sequencer_type_id ]
        new_sequencer_type = self.load_sequencer_type( old_sequencer_type.config_file )
        self.all_sequencer_types[ sequencer_type_id ] = new_sequencer_type
        log.debug( "Reloaded sequencer_type %s" %( sequencer_type_id ) )
        return new_sequencer_type

class SequencerType( object ):
    def __init__( self, sequencer_type_xml_config, root, visible=True ):
        self.config_file = sequencer_type_xml_config
        self.parse( root )
        self.visible = visible
    def parse( self, root ):
        # Get the name 
        self.name = root.get( "name" )
        if not self.name: 
            raise Exception, "Missing sequencer_type 'name'"
        # Get the UNIQUE id for the tool 
        self.id = root.get( "id" )
        if not self.id: 
            raise Exception, "Missing sequencer_type 'id'"
        self.config_version = root.get( "version" )
        if not self.config_version: 
            self.config_version = '1.0.0'
        self.description = util.xml_text(root, "description")
        self.version = util.xml_text( root.find( "version" ) )
        # parse the form
        self.form_definition = form_factory.from_elem( root.find( 'form' ) )
        self.parse_data_transfer_settings( root )
        self.parse_run_details( root )
    def parse_data_transfer_settings( self, root ):
        self.data_transfer = {}
        data_transfer_settings_elem = root.find( 'data_transfer_settings' )
        # till now only data transfer using scp is supported.
        for data_transfer_elem in data_transfer_settings_elem.findall( "data_transfer" ):
            if data_transfer_elem.get( 'type' ) == model.Sequencer.data_transfer_types.SCP:
                scp_data_transfer = data_transfer_factories[ model.Sequencer.data_transfer_types.SCP ]
                scp_data_transfer.parse( self.config_file, data_transfer_elem  )
                self.data_transfer[ model.Sequencer.data_transfer_types.SCP ] = scp_data_transfer
    def parse_run_details( self, root ):
        self.run_details = {}
        run_details_elem = root.find( 'run_details' )
        if run_details_elem:
            results_elem = run_details_elem.find( 'results' )
            if results_elem:
                # get the list of resulting datatypes
                self.run_details[ 'results' ] = self.parse_run_details_results( results_elem )
    def parse_run_details_results( self, root ):
        datatypes_dict = {}
        for datatype_elem in root.findall( "dataset" ):
            name = datatype_elem.get( 'name' )
            datatypes_dict[ name ] = datatype_elem.get( 'datatype' )
        return datatypes_dict

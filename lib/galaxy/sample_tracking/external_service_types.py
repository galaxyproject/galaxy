import logging, os, sys
from galaxy.util.odict import odict
from galaxy.util.bunch import Bunch
from galaxy import util, jobs, model
from galaxy.forms.forms import form_factory
from galaxy.external_services.service import ExternalServiceActionsGroup
from elementtree.ElementTree import XML
from galaxy.sample_tracking.data_transfer import data_transfer_factories
log = logging.getLogger( __name__ )

class ExternalServiceTypeNotFoundException( Exception ):
    pass

class ExternalServiceTypesCollection( object ):

    def __init__( self, config_filename, root_dir, app ):
        self.all_external_service_types = odict()
        self.root_dir = root_dir
        self.app = app
        try:
            self.load_all( config_filename )
        except:
            log.exception( "ExternalServiceTypesCollection error reading %s", config_filename )
    def load_all( self, config_filename ):
        self.visible_external_service_types = []
        tree = util.parse_xml( config_filename )
        root = tree.getroot()
        for elem in root:
            try:
                if elem.tag == 'external_service_type':
                    file_path = elem.get( "file" )
                    visible = util.string_as_bool( elem.get( "visible" ) )
                    external_service_type = self.load_external_service_type( os.path.join( self.root_dir, file_path ), visible )
                    self.all_external_service_types[ external_service_type.id ] = external_service_type
                    log.debug( "Loaded external_service_type: %s %s" % ( external_service_type.name, external_service_type.config_version ) )
                    if visible:
                        self.visible_external_service_types.append( external_service_type.id )
            except:
                log.exception( "error reading external_service_type from path: %s" % file_path )
    def load_external_service_type( self, config_file, visible=True ):
        # Parse XML configuration file and get the root element
        tree = util.parse_xml( config_file )
        root = tree.getroot()
        return ExternalServiceType( config_file, root, visible )
    def reload( self, external_service_type_id ):
        """
        Attempt to reload the external_service_type identified by 'external_service_type_id', if successful
        replace the old external_service_type.
        """
        if external_service_type_id not in self.all_external_service_types.keys():
            raise ExternalServiceTypeNotFoundException( "No external_service_type with id %s" % external_service_type_id )
        old_external_service_type = self.all_external_service_types[ external_service_type_id ]
        new_external_service_type = self.load_external_service_type( old_external_service_type.config_file )
        self.all_external_service_types[ external_service_type_id ] = new_external_service_type
        log.debug( "Reloaded external_service_type %s" %( external_service_type_id ) )
        return new_external_service_type

class ExternalServiceType( object ):
    def __init__( self, external_service_type_xml_config, root, visible=True ):
        self.config_file = external_service_type_xml_config
        self.parse( root )
        self.visible = visible
        root.clear()
    def parse( self, root ):
        # Get the name 
        self.name = root.get( "name" )
        if not self.name: 
            raise Exception, "Missing external_service_type 'name'"
        # Get the UNIQUE id for the tool 
        self.id = root.get( "id" )
        if not self.id: 
            raise Exception, "Missing external_service_type 'id'"
        self.config_version = root.get( "version" )
        if not self.config_version: 
            self.config_version = '1.0.0'
        self.description = util.xml_text(root, "description")
        self.version = util.xml_text( root.find( "version" ) )
        # parse the form
        self.form_definition = form_factory.from_elem( root.find( 'form' ) )
        self.parse_data_transfer_settings( root )
        self.parse_run_details( root )
        #external services actions
        self.actions = ExternalServiceActionsGroup.from_elem( root.find( 'actions' ), parent=self )
    def parse_data_transfer_settings( self, root ):
        self.data_transfer = {}
        data_transfer_settings_elem = root.find( 'data_transfer_settings' )
        # Currently only data transfer using scp or http is supported.
        for data_transfer_elem in data_transfer_settings_elem.findall( "data_transfer" ):
            if data_transfer_elem.get( 'protocol' ) == model.ExternalService.data_transfer_protocol.SCP:
                scp_data_transfer = data_transfer_factories[ model.ExternalService.data_transfer_protocol.SCP ]
                scp_data_transfer.parse( self.config_file, data_transfer_elem  )
                self.data_transfer[ model.ExternalService.data_transfer_protocol.SCP ] = scp_data_transfer
            if data_transfer_elem.get( 'protocol' ) == model.ExternalService.data_transfer_protocol.HTTP:
                http_data_transfer = data_transfer_factories[ model.ExternalService.data_transfer_protocol.HTTP ]
                http_data_transfer.parse( self.config_file, data_transfer_elem  )
                self.data_transfer[ model.ExternalService.data_transfer_protocol.HTTP ] = http_data_transfer
    def parse_run_details( self, root ):
        self.run_details = {}
        run_details_elem = root.find( 'run_details' )
        if run_details_elem:
            results_elem = run_details_elem.find( 'results' )
            if results_elem:
                # Get the list of resulting datatypes
                # TODO: the 'results_urls' attribute is only useful if the transfer protocol is http(s), so check if that is the case.
                self.run_details[ 'results' ], self.run_details[ 'results_urls' ] = self.parse_run_details_results( results_elem )
    def parse_run_details_results( self, root ):
        datatypes_dict = {}
        urls_dict = {}
        for datatype_elem in root.findall( "dataset" ):
            name = datatype_elem.get( 'name' )
            datatypes_dict[ name ] = datatype_elem.get( 'datatype' )
            urls_dict[ name ] = datatype_elem.get( 'url', None )
        return datatypes_dict, urls_dict

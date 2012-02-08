"""
Execute an external process to set_meta() on a provided list of pickled datasets.

This should not be called directly!  Use the set_metadata.sh script in Galaxy's
top level directly.

"""

import logging
logging.basicConfig()
log = logging.getLogger( __name__ )

import os, sys, cPickle
assert sys.version_info[:2] >= ( 2, 4 )

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
import pkg_resources
pkg_resources.require("simplejson")
import simplejson
import galaxy.model.mapping #need to load this before we unpickle, in order to setup properties assigned by the mappers
galaxy.model.Job() #this looks REAL stupid, but it is REQUIRED in order for SA to insert parameters into the classes defined by the mappers --> it appears that instantiating ANY mapper'ed class would suffice here
galaxy.datatypes.metadata.DATABASE_CONNECTION_AVAILABLE = False #Let metadata know that there is no database connection, and to just assume object ids are valid
from galaxy.util import stringify_dictionary_keys
from galaxy.util.json import from_json_string
from sqlalchemy.orm import clear_mappers
from galaxy.objectstore import build_object_store_from_config
from galaxy import config
import ConfigParser

def __main__():
    file_path = sys.argv.pop( 1 )
    tmp_dir = sys.argv.pop( 1 )
    galaxy.model.Dataset.file_path = file_path
    galaxy.datatypes.metadata.MetadataTempFile.tmp_dir = tmp_dir

    config_root = sys.argv.pop( 1 )
    config_file_name = sys.argv.pop( 1 )
    if not os.path.isabs( config_file_name ):
        config_file_name = os.path.join( config_root, config_file_name )
    
    # Set up reference to object store
    # First, read in the main config file for Galaxy; this is required because
    # the object store configuration is stored there
    conf = ConfigParser.ConfigParser()
    conf.read(config_file_name)
    conf_dict = {}
    for section in conf.sections():
        for option in conf.options(section):
            try:
                conf_dict[option] = conf.get(section, option)
            except ConfigParser.InterpolationMissingOptionError:
                # Because this is not called from Paste Script, %(here)s variable
                # is not initialized in the config file so skip those fields -
                # just need not to use any such fields for the object store conf...
                log.debug("Did not load option %s from %s" % (option, config_file_name))
    # config object is required by ObjectStore class so create it now
    universe_config = config.Configuration(**conf_dict)
    object_store = build_object_store_from_config(universe_config)
    galaxy.model.Dataset.object_store = object_store
    
    # Set up datatypes registry
    datatypes_config = sys.argv.pop( 1 )
    datatypes_registry = galaxy.datatypes.registry.Registry()
    datatypes_registry.load_datatypes( root_dir=config_root, config=datatypes_config )
    galaxy.model.set_datatypes_registry( datatypes_registry )

    job_metadata = sys.argv.pop( 1 )
    ext_override = dict()
    if job_metadata != "None" and os.path.exists( job_metadata ):
        for line in open( job_metadata, 'r' ):
            try:
                line = stringify_dictionary_keys( from_json_string( line ) )
                assert line['type'] == 'dataset'
                ext_override[line['dataset_id']] = line['ext']
            except:
                continue
    for filenames in sys.argv[1:]:
        fields = filenames.split( ',' )
        filename_in = fields.pop( 0 )
        filename_kwds = fields.pop( 0 )
        filename_out = fields.pop( 0 )
        filename_results_code = fields.pop( 0 )
        dataset_filename_override = fields.pop( 0 )
        #Need to be careful with the way that these parameters are populated from the filename splitting, 
        #because if a job is running when the server is updated, any existing external metadata command-lines 
        #will not have info about the newly added override_metadata file
        if fields:
            override_metadata = fields.pop( 0 )
        else:
            override_metadata = None
        try:
            dataset = cPickle.load( open( filename_in ) ) #load DatasetInstance
            if dataset_filename_override:
                dataset.dataset.external_filename = dataset_filename_override
            if ext_override.get( dataset.dataset.id, None ):
                dataset.extension = ext_override[ dataset.dataset.id ]
            #Metadata FileParameter types may not be writable on a cluster node, and are therefore temporarily substituted with MetadataTempFiles
            if override_metadata:
                override_metadata = simplejson.load( open( override_metadata ) )
                for metadata_name, metadata_file_override in override_metadata:
                    if galaxy.datatypes.metadata.MetadataTempFile.is_JSONified_value( metadata_file_override ):
                        metadata_file_override = galaxy.datatypes.metadata.MetadataTempFile.from_JSON( metadata_file_override )
                    setattr( dataset.metadata, metadata_name, metadata_file_override )
            kwds = stringify_dictionary_keys( simplejson.load( open( filename_kwds ) ) )#load kwds; need to ensure our keywords are not unicode
            dataset.datatype.set_meta( dataset, **kwds )
            dataset.metadata.to_JSON_dict( filename_out ) # write out results of set_meta
            simplejson.dump( ( True, 'Metadata has been set successfully' ), open( filename_results_code, 'wb+' ) ) #setting metadata has succeeded
        except Exception, e:
            simplejson.dump( ( False, str( e ) ), open( filename_results_code, 'wb+' ) ) #setting metadata has failed somehow
    clear_mappers()
    # Shut down any additional threads that might have been created via the ObjectStore
    object_store.shutdown()

__main__()

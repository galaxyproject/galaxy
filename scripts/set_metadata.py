"""
Execute an external process to set_meta() on a provided list of pickled datasets.

This should not be called directly!  Use the set_metadata.sh script in Galaxy's
top level directly.

"""

import logging
logging.basicConfig()
log = logging.getLogger( __name__ )

import cPickle
import json
import os
import sys

# ensure supported version
from check_python import check_python
try:
    check_python()
except:
    sys.exit(1)

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[ 1: ] )  # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
import pkg_resources
import galaxy.model.mapping  # need to load this before we unpickle, in order to setup properties assigned by the mappers
galaxy.model.Job()  # this looks REAL stupid, but it is REQUIRED in order for SA to insert parameters into the classes defined by the mappers --> it appears that instantiating ANY mapper'ed class would suffice here
from galaxy.util import stringify_dictionary_keys
from sqlalchemy.orm import clear_mappers
from galaxy.objectstore import build_object_store_from_config
from galaxy import config
import ConfigParser


def set_meta_with_tool_provided( dataset_instance, file_dict, set_meta_kwds ):
    # This method is somewhat odd, in that we set the metadata attributes from tool,
    # then call set_meta, then set metadata attributes from tool again.
    # This is intentional due to interplay of overwrite kwd, the fact that some metadata
    # parameters may rely on the values of others, and that we are accepting the
    # values provided by the tool as Truth. 
    for metadata_name, metadata_value in file_dict.get( 'metadata', {} ).iteritems():
        setattr( dataset_instance.metadata, metadata_name, metadata_value )
    dataset_instance.datatype.set_meta( dataset_instance, **set_meta_kwds )
    for metadata_name, metadata_value in file_dict.get( 'metadata', {} ).iteritems():
        setattr( dataset_instance.metadata, metadata_name, metadata_value )

def __main__():
    file_path = sys.argv.pop( 1 )
    tool_job_working_directory = tmp_dir = sys.argv.pop( 1 ) #this is also the job_working_directory now
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
    universe_config.ensure_tempdir()
    object_store = build_object_store_from_config(universe_config)
    galaxy.model.Dataset.object_store = object_store

    # Set up datatypes registry
    datatypes_config = sys.argv.pop( 1 )
    datatypes_registry = galaxy.datatypes.registry.Registry()
    datatypes_registry.load_datatypes( root_dir=config_root, config=datatypes_config )
    galaxy.model.set_datatypes_registry( datatypes_registry )

    job_metadata = sys.argv.pop( 1 )
    existing_job_metadata_dict = {}
    new_job_metadata_dict = {}
    if job_metadata != "None" and os.path.exists( job_metadata ):
        for line in open( job_metadata, 'r' ):
            try:
                line = stringify_dictionary_keys( json.loads( line ) )
                if line['type'] == 'dataset':
                    existing_job_metadata_dict[ line['dataset_id'] ] = line
                elif line['type'] == 'new_primary_dataset':
                    new_job_metadata_dict[ line[ 'filename' ] ] = line
            except:
                continue

    for filenames in sys.argv[1:]:
        fields = filenames.split( ',' )
        filename_in = fields.pop( 0 )
        filename_kwds = fields.pop( 0 )
        filename_out = fields.pop( 0 )
        filename_results_code = fields.pop( 0 )
        dataset_filename_override = fields.pop( 0 )
        # Need to be careful with the way that these parameters are populated from the filename splitting,
        # because if a job is running when the server is updated, any existing external metadata command-lines
        #will not have info about the newly added override_metadata file
        if fields:
            override_metadata = fields.pop( 0 )
        else:
            override_metadata = None
        set_meta_kwds = stringify_dictionary_keys( json.load( open( filename_kwds ) ) )  # load kwds; need to ensure our keywords are not unicode
        try:
            dataset = cPickle.load( open( filename_in ) )  # load DatasetInstance
            if dataset_filename_override:
                dataset.dataset.external_filename = dataset_filename_override
            if dataset.dataset.id in existing_job_metadata_dict:
                dataset.extension = existing_job_metadata_dict[ dataset.dataset.id ].get( 'ext', dataset.extension )
            # Metadata FileParameter types may not be writable on a cluster node, and are therefore temporarily substituted with MetadataTempFiles
            if override_metadata:
                override_metadata = json.load( open( override_metadata ) )
                for metadata_name, metadata_file_override in override_metadata:
                    if galaxy.datatypes.metadata.MetadataTempFile.is_JSONified_value( metadata_file_override ):
                        metadata_file_override = galaxy.datatypes.metadata.MetadataTempFile.from_JSON( metadata_file_override )
                    setattr( dataset.metadata, metadata_name, metadata_file_override )
            file_dict = existing_job_metadata_dict.get( dataset.dataset.id, {} )
            set_meta_with_tool_provided( dataset, file_dict, set_meta_kwds )
            dataset.metadata.to_JSON_dict( filename_out )  # write out results of set_meta
            json.dump( ( True, 'Metadata has been set successfully' ), open( filename_results_code, 'wb+' ) )  # setting metadata has succeeded
        except Exception, e:
            json.dump( ( False, str( e ) ), open( filename_results_code, 'wb+' ) )  # setting metadata has failed somehow

    for i, ( filename, file_dict ) in enumerate( new_job_metadata_dict.iteritems(), start=1 ):
        new_dataset = galaxy.model.Dataset( id=-i, external_filename=os.path.join( tool_job_working_directory, file_dict[ 'filename' ] ) )
        extra_files = file_dict.get( 'extra_files', None )
        if extra_files is not None:
            new_dataset._extra_files_path = os.path.join( tool_job_working_directory, extra_files )
        new_dataset.state = new_dataset.states.OK
        new_dataset_instance = galaxy.model.HistoryDatasetAssociation( id=-i, dataset=new_dataset, extension=file_dict.get( 'ext', 'data' ) )
        set_meta_with_tool_provided( new_dataset_instance, file_dict, set_meta_kwds )
        file_dict[ 'metadata' ] = json.loads( new_dataset_instance.metadata.to_JSON_dict() ) #storing metadata in external form, need to turn back into dict, then later jsonify
    if existing_job_metadata_dict or new_job_metadata_dict:
        with open( job_metadata, 'wb' ) as job_metadata_fh:
            for value in existing_job_metadata_dict.values() + new_job_metadata_dict.values():
                job_metadata_fh.write( "%s\n" % ( json.dumps( value ) ) )

    clear_mappers()
    # Shut down any additional threads that might have been created via the ObjectStore
    object_store.shutdown()

__main__()

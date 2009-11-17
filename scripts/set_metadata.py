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

def __main__():
    file_path = sys.argv.pop( 1 )
    tmp_dir = sys.argv.pop( 1 )
    galaxy.model.Dataset.file_path = file_path
    galaxy.datatypes.metadata.MetadataTempFile.tmp_dir = tmp_dir
    
    # Set up datatypes registry
    config_root = sys.argv.pop( 1 )
    datatypes_config = sys.argv.pop( 1 )
    galaxy.model.set_datatypes_registry( galaxy.datatypes.registry.Registry( config_root, datatypes_config ) )

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
        filename_in, filename_kwds, filename_out, filename_results_code, dataset_filename_override = filenames.split( ',' )
        try:
            dataset = cPickle.load( open( filename_in ) ) #load DatasetInstance
            if dataset_filename_override:
                dataset.dataset.external_filename = dataset_filename_override
            if ext_override.get( dataset.dataset.id, None ):
                dataset.extension = ext_override[ dataset.dataset.id ]
            kwds = stringify_dictionary_keys( simplejson.load( open( filename_kwds ) ) )#load kwds; need to ensure our keywords are not unicode
            dataset.datatype.set_meta( dataset, **kwds )
            dataset.metadata.to_JSON_dict( filename_out ) # write out results of set_meta
            simplejson.dump( ( True, 'Metadata has been set successfully' ), open( filename_results_code, 'wb+' ) ) #setting metadata has suceeded
        except Exception, e:
            simplejson.dump( ( False, str( e ) ), open( filename_results_code, 'wb+' ) ) #setting metadata has failed somehow
    clear_mappers()

__main__()

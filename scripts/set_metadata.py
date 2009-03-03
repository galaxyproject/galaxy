"""
Execute an external process to set_meta() on a provided list of pickled datasets.

This should not be called directly!  Use the set_metadata.sh script in Galaxy's
top level directly.

"""

import os, sys, cPickle
assert sys.version_info[:2] >= ( 2, 4 )

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
import pkg_resources
import galaxy.model.mapping #need to load this before we unpickle, in order to setup properties assigned by the mappers
galaxy.model.Job() #this looks REAL stupid, but it is REQUIRED in order for SA to insert parameters into the classes defined by the mappers --> it appears that instantiating ANY mapper'ed class would suffice here
galaxy.datatypes.metadata.DATABASE_CONNECTION_AVAILABLE = False #Let metadata know that there is no database connection, and to just assume object ids are valid

def __main__():
    file_path = sys.argv.pop( 1 )
    tmp_dir = sys.argv.pop( 1 )
    galaxy.model.Dataset.file_path = file_path
    galaxy.datatypes.metadata.MetadataTempFile.tmp_dir = tmp_dir
    for pickled_filenames in sys.argv[1:]:
        pickled_filename_in, pickled_filename_kwds, pickled_filename_out, pickled_filename_results_code = pickled_filenames.split( ',' )
        try:
            data = cPickle.load( open( pickled_filename_in ) )#unpickle DatasetInstance
            kwds = cPickle.load( open( pickled_filename_kwds ) )#unpickle kwds
            data.datatype.set_meta( data, **kwds )
            data.metadata.to_pickled_dict( pickled_filename_out ) # write out results of set_meta
            cPickle.dump( ( True, 'Metadata has been set successfully' ), open( pickled_filename_results_code, 'wb+' ) ) #setting metadata has suceeded
        except Exception, e:
            cPickle.dump( ( False, e ), open( pickled_filename_results_code, 'wb+' ) ) #setting metadata has failed somehow

__main__()
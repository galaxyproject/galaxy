#!/usr/bin/env python
# Retrieves data from external data source applications and stores in a dataset file.
# Data source application parameters are temporarily stored in the dataset file.
import socket, urllib, sys, os
from galaxy import eggs #eggs needs to be imported so that galaxy.util can find docutils egg...
from galaxy.util.json import loads, dumps
from galaxy.util import get_charset_from_http_headers
import galaxy.model # need to import model before sniff to resolve a circular import dependency
from galaxy.datatypes import sniff
from galaxy.datatypes.registry import Registry
from galaxy.jobs import TOOL_PROVIDED_JOB_METADATA_FILE

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

GALAXY_PARAM_PREFIX = 'GALAXY'
GALAXY_ROOT_DIR = os.path.realpath( os.path.join( os.path.split( os.path.realpath( __file__ ) )[0], '..', '..' ) )
GALAXY_DATATYPES_CONF_FILE = os.path.join( GALAXY_ROOT_DIR, 'datatypes_conf.xml' )

def load_input_parameters( filename, erase_file = True ):
    datasource_params = {}
    try:
        json_params = loads( open( filename, 'r' ).read() )
        datasource_params = json_params.get( 'param_dict' )
    except:
        json_params = None
        for line in open( filename, 'r' ):
            try:
                line = line.strip()
                fields = line.split( '\t' )
                datasource_params[ fields[0] ] = fields[1]
            except:
                continue
    if erase_file:
        open( filename, 'w' ).close() #open file for writing, then close, removes params from file
    return json_params, datasource_params

def __main__():
    filename = sys.argv[1]
    try:
        max_file_size = int( sys.argv[2] )
    except:
        max_file_size = 0

    job_params, params = load_input_parameters( filename )
    if job_params is None: #using an older tabular file
        enhanced_handling = False
        job_params = dict( param_dict = params )
        job_params[ 'output_data' ] =  [ dict( out_data_name = 'output',
                                               ext = 'data',
                                               file_name = filename,
                                               extra_files_path = None ) ]
        job_params[ 'job_config' ] = dict( GALAXY_ROOT_DIR=GALAXY_ROOT_DIR, GALAXY_DATATYPES_CONF_FILE=GALAXY_DATATYPES_CONF_FILE, TOOL_PROVIDED_JOB_METADATA_FILE = TOOL_PROVIDED_JOB_METADATA_FILE )
    else:
        enhanced_handling = True
        json_file = open( job_params[ 'job_config' ][ 'TOOL_PROVIDED_JOB_METADATA_FILE' ], 'w' ) #specially named file for output junk to pass onto set metadata

    datatypes_registry = Registry()
    datatypes_registry.load_datatypes( root_dir = job_params[ 'job_config' ][ 'GALAXY_ROOT_DIR' ], config = job_params[ 'job_config' ][ 'GALAXY_DATATYPES_CONF_FILE' ] )

    URL = params.get( 'URL', None ) #using exactly URL indicates that only one dataset is being downloaded
    URL_method = params.get( 'URL_method', None )

    # The Python support for fetching resources from the web is layered. urllib uses the httplib
    # library, which in turn uses the socket library.  As of Python 2.3 you can specify how long
    # a socket should wait for a response before timing out. By default the socket module has no
    # timeout and can hang. Currently, the socket timeout is not exposed at the httplib or urllib2
    # levels. However, you can set the default timeout ( in seconds ) globally for all sockets by
    # doing the following.
    socket.setdefaulttimeout( 600 )

    for data_dict in job_params[ 'output_data' ]:
        cur_filename =  data_dict.get( 'file_name', filename )
        cur_URL =  params.get( '%s|%s|URL' % ( GALAXY_PARAM_PREFIX, data_dict[ 'out_data_name' ] ), URL )
        if not cur_URL:
            open( cur_filename, 'w' ).write( "" )
            stop_err( 'The remote data source application has not sent back a URL parameter in the request.' )

        # The following calls to urllib.urlopen() will use the above default timeout
        try:
            if not URL_method or URL_method == 'get':
                page = urllib.urlopen( cur_URL )
            elif URL_method == 'post':
                page = urllib.urlopen( cur_URL, urllib.urlencode( params ) )
        except Exception, e:
            stop_err( 'The remote data source application may be off line, please try again later. Error: %s' % str( e ) )
        if max_file_size:
            file_size = int( page.info().get( 'Content-Length', 0 ) )
            if file_size > max_file_size:
                stop_err( 'The size of the data (%d bytes) you have requested exceeds the maximum allowed (%d bytes) on this server.' % ( file_size, max_file_size ) )
        #do sniff stream for multi_byte
        try:
            cur_filename, is_multi_byte = sniff.stream_to_open_named_file( page, os.open( cur_filename, os.O_WRONLY | os.O_CREAT ), cur_filename, source_encoding=get_charset_from_http_headers( page.headers ) )
        except Exception, e:
            stop_err( 'Unable to fetch %s:\n%s' % ( cur_URL, e ) )

        #here import checks that upload tool performs
        if enhanced_handling:
            try:
                ext = sniff.handle_uploaded_dataset_file( filename, datatypes_registry, ext = data_dict[ 'ext' ], is_multi_byte = is_multi_byte )
            except Exception, e:
                stop_err( str( e ) )
            info = dict( type = 'dataset',
                         dataset_id = data_dict[ 'dataset_id' ],
                         ext = ext)

            json_file.write( "%s\n" % dumps( info ) )

if __name__ == "__main__": __main__()

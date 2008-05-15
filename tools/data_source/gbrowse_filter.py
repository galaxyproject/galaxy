import urllib

from galaxy import datatypes, config
from galaxy.datatypes import sniff
import tempfile, shutil

import logging
log = logging.getLogger( __name__ )

def exec_before_job( app, inp_data, out_data, param_dict, tool=None ):
    """Sets the name of the data"""
    data_name = urllib.unquote( param_dict.get( 't', 'GBrowse query' ) ).replace( '+', ' ' )
    data_region = param_dict.get( 'q', '' )
    data_type = param_dict.get( 'type', 'txt' )
    name, data = out_data.items()[0]
    if data_type == 'txt': 
        data_type = sniff.guess_ext( data.file_name )
    data = app.datatypes_registry.change_datatype( data, data_type )
    data.name = '%s %s' % ( data_name, data_region )
    out_data[name] = data

def exec_after_process( app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None ):
    """Verifies the data after the run"""
    URL = param_dict.pop( 'URL', None )
    if not URL:
        raise Exception( 'Datasource has not sent back a URL parameter' )
    for i, param in enumerate( param_dict.keys() ):
        if i == 0:
            sep = '?'
        else:
            sep = '&'
        if param != '__collected_datasets__':
            URL += "%s%s=%s" %( sep, param, param_dict.get( param ) )

    CHUNK_SIZE = 2**20 # 1Mb 
    try:
        page = urllib.urlopen( URL )
    except Exception, exc:
        raise Exception( 'Problems connecting to %s (%s)' % ( URL, exc ) )
        sys.exit( 1 )

    name, data = out_data.items()[0]

    fp = open( data.file_name, 'wb' )
    while 1:
        chunk = page.read( CHUNK_SIZE )
        if not chunk:
            break
        fp.write( chunk )
    fp.close()

    data.info = data.name
    data_type = sniff.guess_ext( data.file_name )
    data = app.datatypes_registry.change_datatype( data, data_type )
    data.set_peek()
    data.flush()

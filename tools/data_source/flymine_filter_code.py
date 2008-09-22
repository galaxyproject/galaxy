# Code for direct connection to flymine
from galaxy.datatypes import sniff
import urllib

import logging
log = logging.getLogger( __name__ )

def exec_before_job( app, inp_data, out_data, param_dict, tool=None ):
    """Sets the attributes of the data"""
    items = out_data.items()
    for name, data in items:
        data.dbkey = param_dict.get( 'dbkey', '?' )    
        # Store flymine parameters temporarily in output file
        out = open( data.file_name, 'w' )
        for key, value in param_dict.items():
            out.write( "%s\t%s\n" % ( key, value ) )
        out.close()
        out_data[ name ] = data

def exec_after_process( app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None ):
    """Verifies the data after the run"""
    name, data = out_data.items()[0]
    if data.state == data.states.OK:
        data.info = data.name
    if data.extension == 'txt':
        data_type = sniff.guess_ext( data.file_name, sniff_order=app.datatypes_registry.sniff_order )
        data = app.datatypes_registry.change_datatype( data, data_type ) 
    data.set_peek()
    data.set_size()
    data.flush()


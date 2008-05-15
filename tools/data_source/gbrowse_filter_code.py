# Code for direct connection to GMOD
from galaxy.datatypes import sniff
import urllib

import logging
log = logging.getLogger( __name__ )

def exec_before_job( app, inp_data, out_data, param_dict, tool=None ):
    """Sets the attributes of the data"""
    gb_settings = urllib.unquote( param_dict.get( 't', None ) ) # t=CG+TS+ESTB+SAGE+EXPR+EXPR_PATTERN+SNPs+PolyA+BLASTX+LINK+ETILE
    gb_landmark_region = urllib.unquote( param_dict.get( 'q' ) ) # q=IV:6070000..6100000&
    gb_land_mark, gb_region = gb_landmark_region.split( ':' )
    items = out_data.items()
    for name, data in items:
        data.name = "%s on %s" % ( data.name, gb_landmark_region )
        data.dbkey = param_dict.get( 'dbkey', '?' )    
        # Store GMOD / GBrowse parameters temporarily in output file
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
        data_type = sniff.guess_ext( data.file_name )
        data = app.datatypes_registry.change_datatype( data, data_type ) 
    data.set_peek()
    data.set_size()
    data.flush()

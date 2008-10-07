#Code for direct connection to EpiGRAPH
from galaxy.datatypes import sniff
import urllib

def exec_before_job( app, inp_data, out_data, param_dict, tool=None ):
    """
    EpiGRAPH sends data to Galaxy by passing the following parameters in the request:
    1. URL - the url to which Galaxy should post a request to retrieve the data
    2. GENOME - the name of the UCSC genome assembly (e.g. hg18), dbkey in Galaxy
    3. NAME - data.name in Galaxy
    4. INFO - data.info in Galaxy
    """
    items = out_data.items()
    for name, data in items:
        NAME = urllib.unquote( param_dict.get( 'NAME', None ) )
        if NAME is not None:
            data.name = NAME
        INFO = urllib.unquote( param_dict.get( 'INFO', None ) )
        if INFO is not None:
            data.info = INFO
        GENOME = urllib.unquote( param_dict.get( 'GENOME', None ) )
        if GENOME is not None:
            data.dbkey = GENOME
        else:
            data.dbkey = '?'
        # Store EpiGRAPH request parameters temporarily in output file
        out = open( data.file_name, 'w' )
        for key, value in param_dict.items():
            print >> out, "%s\t%s" % ( key, value )
        out.close()
        out_data[ name ] = data

def exec_after_process( app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None ):
    """Verifies the datatype after the run"""
    name, data = out_data.items()[0]
    if data.extension == 'txt':
        data_type = sniff.guess_ext( data.file_name, sniff_order=app.datatypes_registry.sniff_order )
        data = app.datatypes_registry.change_datatype( data, data_type ) 
    data.set_peek()
    data.set_size()
    data.flush()

import urllib

from galaxy import datatypes, config

def exec_before_job( trans, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    data_name = param_dict.get( 'name', 'Biomart query' )
    data_type = param_dict.get( 'type', 'text' )
    
    name, data = out_data.items()[0]
    data = datatypes.change_datatype(data, data_type)
    data.name = data_name
    out_data[name] = data

def exec_after_process(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    """Verifies the data after the run"""

    URL = param_dict.get( 'URL', None )
    URL = URL + '&_export=1&GALAXY_URL=0'
    if not URL:
        raise Exception('Datasource has not sent back a URL parameter')

    CHUNK_SIZE = 2**20 # 1Mb 
    MAX_SIZE   = CHUNK_SIZE * 100
    
    try:
        # damn you stupid sanitizer!
        URL = URL.replace('martX', 'mart&')
        URL = URL.replace('0X_', '0&_')
        page = urllib.urlopen(URL)
    except Exception, exc:
        raise Exception('Problems connecting to %s (%s)' % (URL, exc) )

    name, data = out_data.items()[0]
    
    fp = open(data.file_name, 'wb')
    size = 0
    while 1:
        chunk = page.read(CHUNK_SIZE)
        if not chunk:
            break
        if size > MAX_SIZE:
            raise Exception('----- maximum datasize exceeded ---')
        size += len(chunk)
        fp.write(chunk)

    fp.close()
    data.set_peek()

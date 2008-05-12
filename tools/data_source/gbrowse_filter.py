#TODO: Set dbkey to proper UCSC build, if known
import urllib

from galaxy import datatypes, config
from galaxy.datatypes import sniff
import tempfile, shutil

import logging
log = logging.getLogger( __name__ )

def exec_before_job( app, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    data_name = param_dict.get( 'name', 'GBrowse query' )
    data_type = param_dict.get( 'type', 'txt' )
    name, data = out_data.items()[0]
    if data_type == 'txt': 
        data_type = sniff.guess_ext(data.file_name)
    data = app.datatypes_registry.change_datatype(data, data_type)
    data.name = data_name
    out_data[name] = data

def exec_after_process(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    """Verifies the data after the run"""

    URL = param_dict.pop( 'URL', None )
    if not URL:
        raise Exception('Datasource has not sent back a URL parameter')

    for param in param_dict.keys():
        """
         TODO: FIXME - Sent tracks back in case they might be needed for GBrowse custom tracks in the future
        """
        if param != 'tracks' and param != '__collected_datasets__':
            URL += "&%s=%s" %(param, param_dict.get(param))

    #log.debug("In exec_after_process, URL: %s" %URL)

    CHUNK_SIZE = 2**20 # 1Mb 
    MAX_SIZE   = CHUNK_SIZE * 100
    
    try:
        page = urllib.urlopen(URL)
    except Exception, exc:
        raise Exception('Problems connecting to %s (%s)' % (URL, exc) )

    name, data = out_data.items()[0]
    
    fp = open(data.file_name, 'wb')
    size = 0
    max_size_exceeded = False
    while 1:
        chunk = page.read(CHUNK_SIZE)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_SIZE:
            max_size_exceeded = True
            break
        fp.write(chunk)

    fp.close()
    
    if max_size_exceeded:
        data.info = 'Maximum data size of 100 MB exceeded, incomplete data retrieval.'
    else:
        data.info = data.name
    #Set meta data, format file to be valid interval type
    if isinstance(data.datatype, datatypes.interval.Interval):
        data.set_meta(first_line_is_header=True)
        #check for missing meta data, if all there, comment first line and process file
        if not data.missing_meta():
            line_ctr = -1
            temp = tempfile.NamedTemporaryFile('w')
            temp_filename = temp.name
            temp.close()
            temp = open(temp_filename,'w')
            chromCol = int(data.metadata.chromCol) - 1
            startCol = int(data.metadata.startCol) - 1
            strandCol = int(data.metadata.strandCol) - 1
            
            for line in open(data.file_name, 'r'):
                line_ctr += 1
                
                #First line is a non-commented header line, lets comment it out here
                if line_ctr == 0:
                    temp.write("#%s" % line)
                    continue
                
                fields = line.strip().split('\t')
                
                #If chrom col is an int, make it chrInt
                try:
                    int(fields[chromCol])
                    fields[chromCol] = "chr%s" % fields[chromCol]
                except:
                    try:
                        if fields[chromCol].upper()== "X" or fields[chromCol].upper()== "Y":
                            fields[chromCol] = "chr%s" % fields[chromCol].upper()
                    except:
                        pass
                    
                #change to BED coordinate system
                try:
                    fields[startCol] = str(int(fields[startCol]) - 1)
                except:
                    pass
                
                #set strand to +/-, instead of +1/-1
                try:
                    if strandCol > 0:
                        if int(fields[strandCol]) > 0:
                            fields[strandCol] = "+"
                        else:
                            fields[strandCol] = "-"
                except:
                    pass
                
                temp.write("%s\n" % '\t'.join(fields))
            
            temp.close()
            shutil.move(temp_filename,data.file_name)
            
        else:
            data_type = sniff.guess_ext(data.file_name)
            data = app.datatypes_registry.change_datatype(data, data_type)
    else:
        data_type = sniff.guess_ext(data.file_name)
        data = app.datatypes_registry.change_datatype(data, data_type)
    data.set_peek()
    data.flush()

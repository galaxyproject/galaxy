#Code for direct connection to UCSC
from galaxy import datatypes

def exec_before_job( trans, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    outputType = param_dict.get( 'hgta_outputType', "interval" ) #assume all data is interval, we will fix later if not the case
    #list for converting ucsc to galaxy exts, if not in here, use raw reported value
    outputType_to_ext = {'wigData':'wig','tab':'interval'}
    items = out_data.items()
    description = param_dict.get('hgta_regionType',"")
    organism = param_dict.get('org',"unkown species")
    table = param_dict.get('hgta_track',"")
    if description == 'range':
        try:
            description = param_dict.get('position',"")
        except:
            description = "unkown position"
    for name, data in items:
        data.name  = "%s on %s: %s (%s)" % (data.name, organism, table, description)
        data.dbkey = param_dict.get('db', '?')
        ext = outputType
        try: ext = outputType_to_ext[outputType]
        except: pass
        if ext not in datatypes.datatypes_by_extension: ext = 'interval'
        
        data = datatypes.change_datatype(data, ext)
        
        #store ucsc parameters temporarily in output file
        out = open(data.file_name,'w')
        for key, value in param_dict.items():
            print >> out, "%s\t%s" % (key,value)
        out.close()
        
        out_data[name] = data

def exec_after_process(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    """Verifies the datatype after the run"""
    name, data = out_data.items()[0]
    if data.state == data.states.OK: data.info = data.name
    
    if not isinstance(data.datatype, datatypes.interval.Bed) and isinstance(data.datatype, datatypes.interval.Interval):
        data.set_meta()
        if data.missing_meta(): data = datatypes.change_datatype(data, 'tabular')
    data.set_peek()
    data.flush()

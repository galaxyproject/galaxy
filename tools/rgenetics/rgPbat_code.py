# before running the qc, need to rename various output files

from galaxy import datatypes

def get_out_formats():
    """return options for formats"""
    dat = [['ucsc track','wig'],['ucsc genome graphs','gg'],['tab delimited','xls']]
    dat = [(x[0],x[1],False) for x in dat]
    dat.reverse()
    return dat


def exec_before_job(app, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    job_name = param_dict.get( 'name', 'PlinkQC' )
    outxls = ['tabular','%s_TDT.xls' % job_name]
    logtxt = ['txt','%s_TDT.log' % job_name]
    lookup={}
    lookup['out_file1'] = outxls
    lookup['logf'] = logtxt
    for name in lookup.keys():
        data = out_data[name]
        data_type,newname = lookup[name]
        data = app.datatypes_registry.change_datatype(data, data_type)
        data.name = newname
        out_data[name] = data



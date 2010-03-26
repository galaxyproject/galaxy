# for GTOOL linkage ped to marchini snptest format
from galaxy import datatypes


def exec_before_job(app, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    job_name = param_dict.get( 'o', 'Marchini' )
    log = ['txt','%s_rgGTOOL_report.log' % job_name,'txt']
    lookup={}
    lookup['logf'] = log
    for name in lookup.keys():
        data = out_data[name]
        data_type,newname,ext = lookup[name]
        data = app.datatypes_registry.change_datatype(data, data_type)
        data.name = newname
        out_data[name] = data




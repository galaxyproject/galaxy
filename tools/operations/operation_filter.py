# runs after the job (and after the default post-filter)
import sets, os
from galaxy import jobs

def exec_before_process(app, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    dbkeys = sets.Set( [data.dbkey for data in inp_data.values() ] ) 
    if len(dbkeys) != 1:
        raise Exception, '<p><font color="yellow">Both Queries must be from the same genome build</font></p>'

def exec_after_process(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    """Verify the output data after each run"""
    items = out_data.items()

    for name, data in items:
        try:
            err_msg, err_flag = '', False
            if data.info and data.info[0] != 'M':
                data.peek = 'no peek'
                os.remove( data.file_name )
                err_flag = True
            if err_flag:
                raise Exception(err_msg)

        except Exception, exc:
            data.blurb = jobs.JOB_ERROR
            data.state = jobs.JOB_ERROR


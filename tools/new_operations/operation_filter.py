# runs after the job (and after the default post-filter)
import sets, os
from galaxy import jobs
from galaxy.tools.parameters import DataToolParameter

#def exec_before_process(app, inp_data, out_data, param_dict, tool=None):
#    """Sets the name of the data"""
#    dbkeys = sets.Set( [data.dbkey for data in inp_data.values() ] ) 
#    if len(dbkeys) != 1:
#        raise Exception, '<p><font color="yellow">Both Queries must be from the same genome build</font></p>'

def validate_input( trans, error_map, param_values, page_param_map ):
    dbkeys = sets.Set()
    data_param_names = sets.Set()
    data_params = 0
    for name, param in page_param_map.iteritems():
        if isinstance( param, DataToolParameter ):
            # for each dataset parameter
            if param_values.get(name, None) != None:
                dbkeys.add( param_values[name].dbkey )
                data_params += 1
                # check meta data
                try:
                    param = param_values[name]
                    startCol = int( param.metadata.startCol )
                    endCol = int( param.metadata.endCol )
                    chromCol = int( param.metadata.chromCol )
                    strandCol = int ( param.metadata.strandCol )
                except:
                    error_map[name] = "The attributes of this dataset are not the correct format."
            data_param_names.add( name )
    if len( dbkeys ) > 1:
        for name in data_param_names:
            error_map[name] = "All datasets must belong to same genomic build, " \
                "this dataset is linked to build '%s'" % param_values[name].dbkey
    if data_params != len(data_param_names):
        for name in data_param_names:
            error_map[name] = "A dataset of the appropriate type is required"


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

def exec_after_merge(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    exec_after_process(
        app, inp_data, out_data, param_dict, tool=tool, stdout=stdout, stderr=stderr)

    # strip strand column if clusters were merged
    items = out_data.items()
    for name, data in items:
        if param_dict['returntype'] == True:
            data.metadata.chromCol = 1
            data.metadata.startCol = 2
            data.metadata.endCol = 3
        # merge always clobbers strand
        data.metadata.strandCol = None
            

def exec_after_cluster(app, inp_data, out_data, param_dict, tool=None, stdout=None, stderr=None):
    exec_after_process(
        app, inp_data, out_data, param_dict, tool=tool, stdout=stdout, stderr=stderr)

    # strip strand column if clusters were merged
    if param_dict["returntype"] == '1':
        items = out_data.items()
        for name, data in items:
            data.metadata.strandCol = None

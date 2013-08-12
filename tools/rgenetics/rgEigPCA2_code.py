from galaxy import datatypes,model
import sys


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the html output file
    """
    job_name = param_dict.get( 'title', 'Eigenstrat run' )
    ofname = 'out_file1'
    data = out_data[ofname]
    newname = job_name
    data.name = newname
    out_data[ofname] = data


#Change format from Interval to tabular if needed
def exec_before_job(app, inp_data, out_data, param_dict, tool):
    if param_dict['summary']:
        out_data['out_file1'].change_datatype('tabular')
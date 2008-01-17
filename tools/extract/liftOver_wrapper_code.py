def exec_before_job(app, inp_data, out_data, param_dict, tool):
    out_data['out_file1'].set_dbkey(param_dict['to_dbkey'])
    out_data['out_file2'].set_dbkey(param_dict['to_dbkey'])
    out_data['out_file1'].name = out_data['out_file1'].name + " [ MAPPED COORDINATES ]"
    out_data['out_file2'].name = out_data['out_file2'].name + " [ UNMAPPED COORDINATES ]"
    

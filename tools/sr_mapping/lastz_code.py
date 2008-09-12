# by dan
#Change format from tabular to maf if needed; use metadata from input file
def exec_before_job(app, inp_data, out_data, param_dict, tool):
    if param_dict['out_format'] == "maf":
        out_data['output1'].change_datatype('maf')
#        out_data['output1'].init_meta( copy_from=inp_data['input1'] )

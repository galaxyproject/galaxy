# by dan
#Change format from FASTA to Interval if needed; use metadata from input file
def exec_before_job(app, inp_data, out_data, param_dict, tool):
    if param_dict['out_format'] == "1":
        out_data['out_file1'].change_datatype('interval')
        out_data['out_file1'].init_meta( copy_from=inp_data['input'] )

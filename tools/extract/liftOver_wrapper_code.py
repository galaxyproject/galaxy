def exec_before_job(app, inp_data, out_data, param_dict, tool):
    #Assuming the path of the form liftOverDirectory/hg18ToHg17.over.chain (This is how the mapping chain files from UCSC look.)
    to_dbkey = param_dict['to_dbkey'].split('.')[0].split('To')[1]
    to_dbkey = to_dbkey[0].lower()+to_dbkey[1:]
    out_data['out_file1'].set_dbkey(to_dbkey)
    out_data['out_file1'].name = out_data['out_file1'].name + " [ MAPPED COORDINATES ]"
    out_data['out_file2'].name = out_data['out_file2'].name + " [ UNMAPPED COORDINATES ]"
    

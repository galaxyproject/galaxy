import os

def exec_before_job(app, inp_data, out_data, param_dict, tool):
    try:
        refFile = param_dict['solidOrSolexa']['solidRefGenomeSource']['indices'].value
        out_data['output'].set_dbkey(os.path.split(refFile)[1].split('.')[0])
    except:
        try:
            refFile = param_dict['solidOrSolexa']['solidRefGenomeSource']['ownFile'].dbkey
        except:
            out_data['output'].set_dbkey('?')     

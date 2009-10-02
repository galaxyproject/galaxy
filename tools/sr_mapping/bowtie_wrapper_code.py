import os

def exec_before_job(app, inp_data, out_data, param_dict, tool):
    try:
        refFile = param_dict['refGenomeSource']['indices'].value
    except:
        try:
            refFile = param_dict['refGenomeSource']['ownFile'].dbkey
        except:
            out_data['output'].set_dbkey('?')
            return
    dbkey = os.path.split(refFile)[1].split('.')[0]
    # deal with the one odd case
    if dbkey.find('chrM') >= 0:
        dbkey = 'equCab2'
    out_data['output'].set_dbkey(dbkey)

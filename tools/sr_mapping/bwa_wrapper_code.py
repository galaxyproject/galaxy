import os

def exec_before_job(app, inp_data, out_data, param_dict, tool):
    try:
        refFile = param_dict[ 'genomeSource' ][ 'indices' ].value
    except:
        try:
            refFile = param_dict[ 'genomeSource' ][ 'ownFile' ].dbkey
        except:
            refFile = '?'
    out_data[ 'output' ].set_dbkey( os.path.split( refFile )[1].split( '.' )[0] )

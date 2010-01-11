import os

def exec_before_job(app, inp_data, out_data, param_dict, tool):
    try:
        try:
            refFile = param_dict[ 'solidOrSolexa' ][ 'cRefGenomeSource' ][ 'cIndex' ].value
        except:
            refFile = param_dict[ 'solidOrSolexa' ][ 'xRefGenomeSource' ][ 'xIndex' ].value
    except:
        try:
            try:
                refFile = param_dict[ 'solidOrSolexa' ][ 'cRefGenomeSource' ][ 'cOwnFile' ].dbkey
            except:
                refFile = param_dict[ 'solidOrSolexa' ][ 'xRefGenomeSource' ][ 'xOwnFile' ].dbkey
        except:
            out_data[ 'output' ].set_dbkey( '?' )
            return
    dbkey = os.path.split( refFile )[1].split( '.' )[0]
    # deal with the one odd case
    if dbkey.find( 'chrM' ) >= 0 or dbkey.find( 'chr_m' ) >= 0:
        dbkey = 'equCab2'
    out_data[ 'output' ].set_dbkey(dbkey)

import os

def load_maf_data( sep='\t' ):
    # FIXME: this function is duplicated in the DynamicOptions class.  It is used here only to
    # set data.name in exec_before_job(). 
    maf_sets = {}
    filename = "%s/maf_index.loc" % os.environ.get( 'GALAXY_DATA_INDEX_DIR' )
    for i, line in enumerate( file( filename ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ):
            fields = line.split( sep )
            #read each line, if not enough fields, go to next line
            try:
                maf_desc = fields[0]
                maf_uid = fields[1]
                builds = fields[2]
                build_list =[]
                split_builds = builds.split( "," )
                for build in split_builds:
                    this_build = build.split( "=" )[0]
                    build_list.append( this_build )
                paths = fields[3]
                maf_sets[ maf_uid ] = {}
                maf_sets[ maf_uid ][ 'description' ] = maf_desc
                maf_sets[ maf_uid ][ 'builds' ] = build_list
            except:
                continue
    return maf_sets
def exec_before_job(app, inp_data, out_data, param_dict, tool):
    maf_sets = load_maf_data()
    if param_dict[ 'maf_source_type' ][ 'maf_source' ] == "cached":
        for name, data in out_data.items():
            try:
                data.name = data.name + " [" + maf_sets[ str( param_dict[ 'maf_source_type' ][ 'mafType' ] ) ][ 'description' ] + "]"
            except KeyError:
                data.name = data.name + " [unknown MAF source specified]"
    if param_dict[ 'summary' ].lower() == "true":
        for name, data in out_data.items():
            data.change_datatype( 'tabular' )

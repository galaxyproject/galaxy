# before running the qc, need to rename various output files

builds = []
#Read build names and keys from galaxy.util
for dbkey, build_name in galaxy.util.dbnames:
    builds.append((build_name,dbkey,False))

#Return available builds
def get_available_builds(defval='hg18'):
    for i,x in enumerate(builds):
        if x[1] == defval:
           x = list(x)
           x[2] = True
           builds[i] = tuple(x)
    return builds


def get_out_formats():
    """return options for formats"""
    dat = [['ucsc genome graphs','gg',True],['ucsc track','wig',False],['tab delimited','xls',False]]
    dat = [(x[0],x[1],x[2]) for x in dat]
    return dat


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the data
   <command interpreter="python2.4">
        rgTDT.py -i $i.extra_files_path/$i.metadata.base_name -o $title -f $outformat -r $out_file1 -l $logf
    </command>
    
    """
    dbk = param_dict.get('dbkey','hg18')
    job_name = param_dict.get( 'title', 'rgTDT_run' )
    outext = param_dict.get('outformat','gg')
    outxls = [outext,'%s_TDT.%s' % (job_name,outext)]
    logtxt = ['txt','%s_TDTlog.txt' % job_name]
    lookup={}
    lookup['out_file1'] = outxls
    lookup['logf'] = logtxt
    for name in lookup.keys():
        data = out_data[name]
        data_type,newname = lookup[name]
        print >> sys.stdout, '###tdt exec_before_job name=%s, newname=%s, data_type=%s' % (name,newname,data_type)
        data.name = newname
        data.dbkey = dbk
        data = app.datatypes_registry.change_datatype(data, data_type)
        out_data[name] = data
        data.flush()

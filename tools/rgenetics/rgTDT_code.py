# before running the qc, need to rename various output files
import time,string

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

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
    job_name = param_dict.get( 'title1', 'rgTDTtest1' )
    killme=string.punctuation+string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    job_name = job_name.encode().translate(trantab)
    outxls = ['tabular','%s_TDT.xls' % job_name]
    logtxt = ['txt','%s_TDT_log.txt' % job_name]
    ggout = ['gg','%s_TDT_topTable.gff' % job_name]
    lookup={}
    lookup['out_file1'] = outxls
    lookup['logf'] = logtxt
    lookup['gffout'] = ggout
    info = 'rgTDT run at %s' % timenow()
    for name in lookup.keys():
        data = out_data[name]
        data_type,newname = lookup[name]
        data.name = newname
        data.info = info
        data.dbkey = dbk
        out_data[name] = data
    app.model.context.flush()

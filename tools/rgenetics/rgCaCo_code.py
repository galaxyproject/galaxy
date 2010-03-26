# for caco
# called as  plinkCaCo.py $i $name $test $outformat $out_file1 $logf $map
from galaxy import datatypes
import time,string,sys

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the data"""
    job_name = param_dict.get( 'name', 'RgCaCo' ).encode()
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    title = job_name.translate(trantab)
    indatname = inp_data['i'].name
    outxls = ['tabular','%s_CaCo.xls' % job_name]
    logtxt = ['txt','%s_CaCo_log.txt' % job_name]
    ggout = ['gff','%s_CaCo_topTable.gff' % job_name]
    lookup={}
    lookup['out_file1'] = outxls
    lookup['logf'] = logtxt
    lookup['gffout'] = ggout
    info = '%s rgCaCo from %s at %s' % (job_name,indatname,timenow())
    for name in lookup.keys():
        data = out_data[name]
        data_type,newname = lookup[name]
        data.name = newname
        data.info = info
        out_data[name] = data
    app.model.context.flush()
    

def get_test_opts():
    """return test options"""
    dat = [('Armitage test for trend chisq. Does NOT assume HWE!','TREND',True),
           ('Allelic (A vs a) chisq. assumes HWE','ALLELIC',False),
           ('Genotype (AA vs Aa vs aa)chisq. assumes HWE','GENO',False),
           ('Dominant model (AA/Aa vs aa) chisq. assumesWE','DOM',False),
           ('Recessive (AA vs Aa/aa) chisq. assumes HWE','REC',False)]
    dat.reverse()
    return dat



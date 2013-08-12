# for caco
# called as  plinkCaCo.py $i $name $test $outformat $out_file1 $logf $map
from galaxy import datatypes


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the data"""
    job_name = param_dict.get( 'name', 'PlinkCaCo' )
    format_name = param_dict.get( 'outformat', 'gg' )
    exte = 'xls'
    dt = 'tabular'
    if format_name == 'gg':
         dt = 'gg'
    elif format_name == 'wig':
         dt = 'interval'
    log = ['txt','%s_CaCo_report.log' % job_name]
    outf = [dt,'%s_CaCo_%s.track' % (job_name, format_name)]
    lookup={}
    lookup['logf'] = log
    lookup['out_file1'] = outf
    for name in lookup.keys():
        data = out_data[name]
        data_type,newname = lookup[name]
        data = app.datatypes_registry.change_datatype(data, data_type)
        data.name = newname
        out_data[name] = data
        data.flush()

def get_out_formats():
    """return options for formats"""
    dat = [('ucsc genome graphs','gg',True),('ucsc track','wig',False),('tab delimited','xls',False)]
    dat = [(x[0],x[1],x[2]) for x in dat]
    return dat

def get_test_opts():
    """return test options"""
    dat = [('test for trend','armitage',True),('allele chisq','allele',False),('dominant model','dom',False),('genotype chisq','geno',False)]
    dat = [(x[0],x[1],False) for x in dat]
    dat.reverse()
    return dat



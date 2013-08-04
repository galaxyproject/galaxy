# before running the qc, need to rename various output files
import os,string
from galaxy import datatypes
from galaxy import app
import galaxy.util

#Provides Upload tool with access to list of available builds

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
    dat = [['ucsc track','wig'],['ucsc genome graphs','gg'],['tab delimited','xls']]
    dat = [(x[0],x[1],False) for x in dat]
    dat.reverse()
    return dat

def get_phecols(phef):
   """return column names """
   phefile = os.path.join(phef.extra_files_path,'%s.phe' % (phef.metadata.base_name))
   head = open(phefile,'r').next()
   c = head.strip().split()
   res = [(cname,cname,False) for cname in c]
   x,y,z = res[2] # 0,1 = fid,iid
   res[2] = (x,y,True) # set second selected
   return res

def donotexec_before_job(app, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    job_name = param_dict.get( 'name', 'GLM' )
    outxls = ['gg','%s_GLM.gg' % job_name]
    logtxt = ['txt','%s_GLM.log' % job_name]
    lookup={}
    lookup['out_file1'] = outxls
    lookup['logf'] = logtxt
    for name in lookup.keys():
        data = out_data[name]
        data_type,newname = lookup[name]
        data = app.datatypes_registry.change_datatype(data, data_type)
        data.name = newname
        out_data[name] = data


def notexec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the data"""
    trantab = string.maketrans(string.punctuation,'_'*len(string.punctuation))
    job_name = param_dict.get( 'title1', 'fakePheno' ).translate(trantab)
    logtxt = ['txt','%s_fakePhe.log' % job_name]
    outtxt = ['pphe','%s_fakePhe.txt' % job_name]
    lookup={}
    lookup['out_file1'] = outtxt
    lookup['log_file1'] = logtxt
    for name in lookup.keys():
        data = out_data[name]
        data_type,newname = lookup[name]
        data = app.datatypes_registry.change_datatype(data, data_type)
        data.name = newname
        out_data[name] = data


# Create links to files here from rgenetics_import - a pointer to a file folder full of related things
# want to include all common formats - at import or on demand conversion?
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    i = inp_data['i']
    base_name = i.metadata.base_name
    ftd = i.extra_files_path
    data = out_data.values()[0]
    data.change_datatype(os.path.split(ftd)[-1])
    data.file_name = data.file_name
    data.metadata.base_name = base_name
    data.name = base_name
    data.flush()
    data.dataset_file.extra_files_path = ftd
    data.dataset_file.readonly = True
    data.flush()
    app.model.flush()


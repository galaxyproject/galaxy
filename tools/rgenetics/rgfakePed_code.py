import os, string, time
from galaxy import datatypes
from galaxy import app
import galaxy.util

#Provides Upload tool with access to list of available builds
repospath = '/usr/local/galaxy/data/rg'
builds = []
#Read build names and keys from galaxy.util
for dbkey, build_name in galaxy.util.dbnames:
    builds.append((build_name,dbkey,False))

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

#Return available builds
def get_available_builds(defval='hg18'):
    for i,x in enumerate(builds):
        if x[1] == defval:
           x = list(x)
           x[2] = True
           builds[i] = tuple(x)
    return builds

# Create link to files here
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    base_name = param_dict.get( 'title1', 'Null_Genotypes' )
    base_name = base_name.encode()
    outFormat = param_dict.get('outFormat','P')
    s = string.whitespace + string.punctuation
    ptran =  string.maketrans(s,'_'*len(s))
    base_name = base_name.translate(ptran)
    pname = "out_file1"
    lookup = {'L':('linkped','lped'),'F':('FBAT','fped')}
    # /usr/local/galaxy/data/rg/1/lped/
    info = 'Null phenotypes created by rgfakePhe at %s' % timenow()
    data = out_data[pname]
    ftype,pext = lookup[outFormat]
    data.name = '%s.%s' % (base_name,pext) # that's how they've been named in rgfakePhe.py
    data.change_datatype(pext)
    #data.file_name = data.file_name
    data.metadata.base_name = base_name
    data.readonly = True
    out_data[pname] = data
    app.model.context.flush()







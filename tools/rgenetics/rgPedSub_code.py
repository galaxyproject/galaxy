from galaxy import app
import galaxy.util,string,os,glob,time

#Provides Upload tool with access to list of available builds

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

#return available datasets for build
def get_available_data( file_type_dir, build='hg18' ):
    #we need to allow switching of builds, and properly set in post run hook
    import_files = [] # [('Use the History file chosen below','',False),]
    flist = glob.glob(os.path.join(librepos,file_type_dir,'*.ped'))  
    flist = [os.path.splitext(x)[0] for x in flist] # get unique filenames
    flist = list(set(flist)) # remove dupes  
    flist.sort()
    for i, data in enumerate( flist ):
        #import_files.append( (os.path.split(data)[-1], os.path.split(data)[-1], False) )
        import_files.append((os.path.split(data)[-1],data, False) )
    if len(import_files) < 1:
        import_files.append(('No %s data available - please choose a History file instead'
                             % file_type_dir,'',True))
    return import_files

def get_available_outexts(uid):
    userId = uid
    print 'userId=',userId
    flib = os.path.join(librepos,userId,'fped')
    plib = os.path.join(librepos,userId,'lped')
    e = [('Fbat style (header row has marker names)',flib,False),('Linkage style (separate .map file)',plib,True)]
    return e

def getcols(fname="/usr/local/galaxy/data/camp2007/camp2007.xls"):
   """return column names other than chr offset as a select list"""
   head = open(fname,'r').next()
   c = head.strip().split()
   res = [(cname,'%d' % n,False) for n,cname in enumerate(c)]
   for i in range(4):
     x,y,z = res[i]
     res[i] = (x,y,True) # set first couple as selected
   return res


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """from rgConvert_code
    """
    name,data = out_data.items()[0]
    iname,idata = inp_data.items()[0]
    basename = idata.metadata.base_name
    title = param_dict.get( 'title', 'Lped Subset' )
    title = title.encode() # make str - unicode is evil here
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    title = title.translate(trantab)
    info = '%s filtered by rgPedSub.py at %s' % (title,timenow())
    #data.file_name = data.file_name
    data.metadata.base_name = basename
    data.name = '%s.lped' % title
    data.info = info
    app.model.context.flush()


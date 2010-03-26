#Provides Upload tool with access to list of available files
import glob,sys
import galaxy.app as thisapp
import galaxy.util

from elementtree.ElementTree import XML

librepos = '/usr/local/galaxy/data/rg'
myrepos = '/home/rerla/galaxy'
marchinirepos = '/usr/local/galaxy/data/rg/snptest'

from galaxy.tools.parameters import DataToolParameter

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



def get_tabular_cols( input, outformat='gg' ):
    """numeric only other than rs for strict genome graphs
    otherwise tabular. Derived from galaxy tool source around August 2007 by Ross"""
    columns = []
    seenCnames = {}
    elems = []
    colnames = ['Col%d' % x for x in range(input.metadata.columns+1)]
    strict = (outformat=='gg')
    for i, line in enumerate( file ( input.file_name ) ):
        if line and not line.startswith( '#' ): 
            line = line.rstrip('\r\n')
            elems = line.split( '\t' )
    
            """
            Strict gg note:
            Since this tool requires users to select only those columns
            that contain numerical values, we'll restrict the column select
            list appropriately other than the first column which must be a marker
            """
            if len(elems) > 0:
                for col in range(1, input.metadata.columns+1):
		    isFloat = False # short circuit common result
                    try:
                        val = float(elems[col-1])
                        isFloat = True
                    except:
                        val = elems[col-1]
                        if val:
                            if i == 0: # header row
                               colnames[col] = val
                    if isFloat or (not strict) or (col == 1): # all in if not GG
                        option = colnames[col]
                        if not seenCnames.get(option,None): # new
                              columns.append((option,str(col),False))
                              seenCnames[option] = option
            #print 'get_tab: %d=%s. Columns=%s' % (i,line,str(columns))
            if len(columns) > 0 and i > 10:
                """
                We have our select list built, so we can break out of the outer most for loop
                """
                break 
        if i == 30:
            break # Hopefully we never get here...
    for option in range(min(5,len(columns))):
      (x,y,z) = columns[option]
      columns[option] = (x,y,True)
    return columns # sorted select options

def get_marchini_dir():
    """return the filesystem directory for snptest style files"""
    return marchinirepos


def get_lib_SNPTESTCaCofiles():
    """return a list of file names - without extensions - available for caco studies
    These have a common file name with both _1 and _2 suffixes"""
    d = get_marchini_dir()
    testsuffix = '.gen_1' # glob these
    flist = glob.glob('%s/*%s' % (d,testsuffix))
    flist = [x.split(testsuffix)[0] for x in flist] # leaves with a list of file set names
    if len(flist) > 0:
        dat = [(flist[0],flist[0],True),]
	dat += [(x,x,False) for x in flist[1:]]
    else:
        dat = [('No Marchini CaCo files found in %s - convert some using the Marchini converter tool' % d,'None',True),]
    return dat

def getChropt():
    """return dynamic chromosome select options
    """
    c = ['X','Y']
    c += ['%d' % x for x in range(1,23)]
    dat = [(x,x,False) for x in c]
    x,y,z = dat[3]
    dat[3] = (x,y,True)
    return dat


def get_phecols(fname=''):
   """ return a list of phenotype columns for a multi-select list
   prototype:
   foo = ('fake - not yet implemented','not implemented','False')
   dat = [foo for x in range(5)]
   return dat
   """
   try:
   	header = file(fname,'r').next().split()
   except:
        return [('get_phecols unable to open file %s' % fname,'None',False),]
   dat = [(x,x,False) for x in header]
   return dat

#Return various kinds of files

def get_lib_pedfiles():
    dat = glob.glob('%s/ped/*.ped' % librepos)
    dat += glob.glob('%s/ped/*.ped' % myrepos)
    dat.sort()
    if len(dat) > 0:
        dat = [x.split('.ped')[0] for x in dat]
    	dat = [(x,x,'True') for x in dat]
    else:
        dat = [('No ped files - add some to %s/ped or %s/ped' % (librepos,myrepos),'None',True),]
    return dat

def get_lib_phefiles():
    ext = 'phe'
    dat = glob.glob('%s/pheno/*.%s' % (librepos,ext))
    dat += glob.glob('%s/pheno/*.%s' % (myrepos,ext))
    dat.sort()
    if len(dat) > 0:
    	dat = [(x,x,'False') for x in dat]
    else:
        dat = [('No %s files - add some to %s/pheno or %s/pheno' % (ext,librepos,myrepos),'None',True),]
    return dat

def get_lib_bedfiles():
    dat = glob.glob('%s/plinkbed/*.bed' % librepos)
    dat += glob.glob('%s/plinkbed/*.bed' % myrepos)
    dat.sort()
    if len(dat) > 0:
        dat = [x.split('.bed')[0] for x in dat]
    	dat = [(x,x,False) for x in dat]
    else:
        dat = [('No bed files - Please import some to %s/plinkbed or %s/plinkbed' % (librepos,myrepos),'None',True),]
    return dat

def get_lib_fbatfiles():
    dat = glob.glob('%s/plinkfbat/*.ped' % librepos)
    dat += glob.glob('%s/plinkfbat/*.ped' % myrepos)
    dat.sort()
    if len(dat) > 0:
    	dat = [(x,x,False) for x in dat]
    else:
        dat = [('No fbat bed files - Please import some to %s/plinkfbat or %s/plinkfbat' % (librepos,myrepos),'None',True),]
    return dat

def get_lib_mapfiles():
    dat = glob.glob('%s/ped/*.map' % librepos)
    dat += glob.glob('%s/ped/*.map' % myrepos)
    dat.sort()
    if len(dat) > 0:
    	dat = [(x,x,False) for x in dat]
    else:
        dat = [('No map files - add some to %s/ped' % librepos,'None',True),]
    return dat

def get_my_pedfiles():
    dat = glob.glob('%s/*.ped' % myrepos)
    if len(dat) > 0:
    	dat = [(x,x,False) for x in dat]
    else:
        dat = [('No ped files - add some to %s' % librepos,'None',True),]
    return dat

def get_my_mapfiles():
    dat = glob.glob('%s/*.map' % myrepos)
    if len(dat) > 0:
    	dat = [(x,x,'True') for x in dat]
    else:
        dat = [('No ped files - add some to %s' % librepos,'None',True),]
    return dat

def get_lib_xlsfiles():
    dat = glob.glob('%s/*.xls' % librepos)
    if len(dat) > 0:
    	dat = [(x,x,False) for x in dat]
    else:
        dat = [('No ped files - add some to %s' % librepos,'None',True),]
    return dat

def get_lib_htmlfiles():
    dat = glob.glob('%s/*.html' % librepos)
    if len(dat) > 0:
    	dat = [(x,x,False) for x in dat]
    else:
        dat = [('No ped files - add some to %s' % librepos,'None',True),]
    return dat

def get_my_xlsfiles():
    dat = glob.glob('%s/*.xls' %  myrepos)
    if len(dat) > 0:
    	dat = [(x,x,False) for x in dat]
    else:
        dat = [('No ped files - add some to %s' % librepos,'None',True),]
    return dat

def get_my_htmlfiles():
    dat = glob.glob('%s/*.html' % myrepos)
    if len(dat) > 0:
    	dat = [(x,x,False) for x in dat]
    else:
        dat = [('No ped files - add some to %s' % librepos,'None',True),]
    return dat



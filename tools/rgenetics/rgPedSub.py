"""
July 1 2009 added relatedness filter - fo/oo or all
released under the terms of the LGPL
copyright ross lazarus August 2007 
for the rgenetics project

Special galaxy tool for the camp2007 data
Allows grabbing genotypes from an arbitrary region

Needs a mongo results file in the location hardwired below or could be passed in as
a library parameter - but this file must have a very specific structure
rs chrom offset float1...floatn

called as

    <command interpreter="python2.4">
        campRGeno2.py $region "$rslist" "$title" $output1 $log_file $userId "$lpedIn" "$lhistIn"
    </command>


"""


import sys, array, os, string
from rgutils import galhtmlprefix,plinke,readMap

progname = os.path.split(sys.argv[0])[1]


atrandic = {'A':'1','C':'2','G':'3','T':'4','N':'0','-':'0','1':'1','2':'2','3':'3','4':'4','0':'0'}

def doImport(outfile='test',flist=[]):
    """ import into one of the new html composite data types for Rgenetics
        Dan Blankenberg with mods by Ross Lazarus 
        October 2007
    """
    out = open(outfile,'w')
    out.write(galhtmlprefix % progname)

    if len(flist) > 0:
        out.write('<ol>\n')
        for i, data in enumerate( flist ):
           out.write('<li><a href="%s">%s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1]))
        out.write('</ol>\n')
    else:
           out.write('No files found')
    out.write("</div></body></html>")
    out.close()

def setupPedFilter(relfilter='oo',dfile=None):
    """ figure out who to drop to satisfy relative filtering
    note single offspring only from each family id
    ordering of pdict keys makes this 'random' as the first one only is
    kept if there are multiple sibs from same familyid.
    """
    dropId = {}
    keepoff = (relfilter == 'oo')
    keepfounder = (relfilter == 'fo')
    pdict = {}
    for row in dfile:
        rowl = row.strip().split()
        if len(rowl) > 6:
            idk = (rowl[0],rowl[1])
            pa =  (rowl[0],rowl[2]) # key for father
            ma = (rowl[0],rowl[3]) # and mother
            pdict[idk] = (pa,ma)
    dfile.seek(0) # rewind
    pk = pdict.keys()
    for p in pk:
        parents = pdict[p]
        if pdict.get(parents[0],None) or pdict.get(parents[1],None): # parents are in this file
            if keepfounder:
                dropId[p] = 1 # flag for removal
        elif keepoff:
            dropId[p] = 1 # flag for removal 
    if keepoff: # TODO keep only a random offspring if many - rely on pdict keys being randomly ordered...!   
        famseen = {}
        for p in pk: # look for multiples from same family - drop all but first
             famid = p[0]
             if famseen.get(famid,None):
                 dropId[p] = 1 # already got one from this family
             famseen.setdefault(famid,1)
    return dropId
   
def writeFped(rslist=[],outdir=None,title='Title',basename='',dfile=None,wewant=[],dropId={},outfile=None,logfile=None):
    """ fbat format version
    """
    outname = os.path.join(outdir,basename)
    pedfname = '%s.ped' % outname
    ofile = file(pedfname, 'w')
    rsl = ' '.join(rslist) # rslist for fbat
    ofile.write(rsl)
    s = 'wrote %d marker header to %s - %s\n' % (len(rslist),pedfname,rsl[:50])
    lf.write(s)
    ofile.write('\n')
    nrows = 0
    for line in dfile:
        line = line.strip()
        if not line:
            continue
        line = line.replace('D','N')
        fields = line.split()
        preamble = fields[:6]
        idk = (preamble[0],preamble[1])
        dropme = dropId.get(idk,None)
        if not dropme:
            g = ['%s %s' % (fields[snpcol], fields[snpcol+1]) for snpcol in wewant]
            g = ' '.join(g)
            g = g.split() # we'll get there
            g = [atrandic.get(x,'0') for x in g] # numeric alleles...
            # hack for framingham ND
            ofile.write('%s %s\n' % (' '.join(preamble), ' '.join(g)))
            nrows += 1
    ofile.close()
    loglist = open(logfile,'r').readlines() # retrieve log to add to html file
    doImport(outfile,[pedfname,],loglist=loglist)
    return nrows,pedfname

def writePed(markers=[],outdir=None,title='Title',basename='',dfile=None,wewant=[],dropId={},outfile=None,logfile=None):
    """ split out
    """
    outname = os.path.join(outdir,basename)
    mapfname = '%s.map' % outname
    pedfname = '%s.ped' % outname
    ofile = file(pedfname, 'w')
    # make a map file in the lped library
    mf = file(mapfname,'w')
    map = ['%s\t%s\t0\t%d' % (x[0],x[2],x[1]) for x in markers] # chrom,abspos,snp in genomic order
    mf.write('%s\n' % '\n'.join(map))
    mf.close()
    nrows = 0
    for line in dfile:
        line = line.strip()
        if not line:
            continue
        #line = line.replace('D','N')
        fields = line.split()
        preamble = fields[:6]
        idk = (preamble[0],preamble[1])
        dropme = dropId.get(idk,None)
        if not dropme:
            g = ['%s %s' % (fields[snpcol], fields[snpcol+1]) for snpcol in wewant]
            g = ' '.join(g)
            g = g.split() # we'll get there
            g = [atrandic.get(x,'0') for x in g] # numeric alleles...
            # hack for framingham ND
            ofile.write('%s %s\n' % (' '.join(preamble), ' '.join(g)))
            nrows += 1
    ofile.close()
    loglist = open(logfile,'r').readlines() # retrieve log to add to html file
    doImport(outfile,[mapfname,pedfname,logfile])
    return nrows,pedfname
    
def subset():
    """  ### Sanity check the arguments
    now passed in as 
    <command interpreter="python">
        rgPedSub.py $script_file
    </command>

    with
    <configfiles>
    <configfile name="script_file">
    title~~~~$title
    output1~~~~$output1
    log_file~~~~$log_file
    userId~~~~$userId
    outformat~~~~$outformat
    outdir~~~~$output1.extra_files_path
    relfilter~~~~$relfilter
    #if $d.source=='library'
    inped~~~~$d.lpedIn
    #else 
    inped~~~~$d.lhistIn.extra_files_path/$d.lhistIn.metadata.base_name
    #end if
    #if $m.mtype=='grslist'
    rslist~~~~$m.rslist
    region~~~~	
    #else 
    rslist~~~~	
    region~~~~$m.region
    #end if
    </configfile>
    </configfiles>    
    """
    sep = '~~~~' # arbitrary choice
    conf = {}
    if len(sys.argv) < 2:
        print >> sys.stderr, "No configuration file passed as a parameter - cannot run"
        sys.exit(1)
    configf = sys.argv[1]
    config = file(configf,'r').readlines()
    for row in config:
        row = row.strip()
        if len(row) > 0:
            try:
                key,valu = row.split(sep)
                conf[key] = valu
            except:
                pass
    ss = '%s%s' % (string.punctuation,string.whitespace)
    ptran =  string.maketrans(ss,'_'*len(ss))
    ### Figure out what genomic region we are interested in
    region = conf.get('region','')
    orslist = conf.get('rslist','').replace('X',' ').lower()
    orslist = orslist.replace(',',' ').lower()
    # galaxy replaces newlines with XX - go figure
    title = conf.get('title','').translate(ptran) # for outputs
    outfile = conf.get('output1','')
    outdir = conf.get('outdir','')
    try:
        os.makedirs(outdir)
    except:
        pass
    outformat = conf.get('outformat','lped')
    basename = conf.get('basename',title)
    logfile = os.path.join(outdir,'%s.log' % title) 
    userId = conf.get('userId','') # for library
    pedFileBase = conf.get('inped','')
    relfilter = conf.get('relfilter','')
    MAP_FILE = '%s.map' % pedFileBase
    DATA_FILE = '%s.ped' % pedFileBase    
    title = conf.get('title','lped subset')
    lf = file(logfile,'w')
    lf.write('config file %s = \n' % configf)
    lf.write(''.join(config))
    c = ''
    spos = epos = 0
    rslist = []
    rsdict = {}
    if region > '':
        try: # TODO make a regexp?
            c,rest = region.split(':')
            c = c.replace('chr','')
            rest = rest.replace(',','') # remove commas
            spos,epos = rest.split('-')
            spos = int(spos)
            epos = int(epos)
            s = '## %s parsing chrom %s from %d to %d\n' % (progname,c,spos,epos)
            lf.write(s)
        except:
            s = '##! %s unable to parse region %s - MUST look like "chr8:10,000-100,000\n' % (progname,region)
            lf.write(s)
            lf.close()
            sys.exit(1)
    else:
        rslist = orslist.split() # galaxy replaces newlines with XX - go figure
        rsdict = dict(zip(rslist,rslist))
    allmarkers = False
    if len(rslist) == 0 and epos == 0: # must be a full extract - presumably remove relateds or something
        allmarkers = True
    ### Figure out which markers are in this region
    markers,snpcols,rslist,rsdict = readMap(mapfile=MAP_FILE,allmarkers=allmarkers,rsdict=rsdict,c=c,spos=spos,epos=epos)
    if len(rslist) == 0:
            s = '##! %s found no rs numbers in %s\n' % (progname,sys.argv[1:3])
            lf.write(s)
            lf.write('\n')
            lf.close()
            sys.exit(1)
    s = '## %s looking for %d rs (%s....etc)\n' % (progname,len(rslist),rslist[:5])
    lf.write(s)
    try:
        dfile = open(DATA_FILE, 'r')
    except: # bad input file name?
        s = '##! rgPedSub unable to open file %s\n' % (DATA_FILE)
        lf.write(s)
        lf.write('\n')
        lf.close()
        print >> sys.stdout, s
        raise
        sys.exit(1)
    if relfilter <> 'all': # must read pedigree and figure out who to drop
        dropId = setupPedFilter(relfilter=relfilter,dfile=dfile)
    else:
        dropId = {}
    wewant = [(6+(2*snpcols[x])) for x in rslist] # 
    # column indices of first geno of each marker pair to get the markers into genomic
    ### ... and then parse the rest of the ped file to pull out
    ### the genotypes for all subjects for those markers
    # /usr/local/galaxy/data/rg/1/lped/
    if len(dropId.keys()) > 0:
        s = '## dropped the following subjects to satisfy requirement that relfilter = %s\n' % relfilter
        lf.write(s)
        if relfilter == 'oo':
            s = '## note that one random offspring from each family was kept if there were multiple offspring\n'
            lf.write(s)
        s = 'FamilyId\tSubjectId\n'
        lf.write(s)
        dk = dropId.keys()
        dk.sort()
        for k in dk:
            s = '%s\t%s\n' % (k[0],k[1])
            lf.write(s)
    lf.write('\n')
    lf.close()
    if outformat == 'lped':
        nrows,pedfname=writePed(markers=markers,outdir=outdir,title=title,basename=basename,dfile=dfile,
                 wewant=wewant,dropId=dropId,outfile=outfile,logfile=logfile)
    elif outformat == 'fped':
        nrows,pedfname=writeFped(rslist=rslist,outdir=outdir,title=title,basename=basename,dfile=dfile,
                  wewant=wewant,dropId=dropId,outfile=outfile,logfile=logfile)
    dfile.close()    

if __name__ == "__main__":
    subset()

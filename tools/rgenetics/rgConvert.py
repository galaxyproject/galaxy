"""
## changed to use a generator to create single output lines
## one at a time - the framingham data easily outstrips the size of
## a python string if I use the usual lazy everything at once approach
## autoconvert - run everything that's not there
## TODO make more selective and configurable
## class oct 2007 ross lazarus
## changed to use arrays rather than lists
## for snp vectors to save some space and maybe some time
## this is slow compared to convertf but doesn't require
## a whole slew of configuration parameters in a text file :)
## linkage format ped file to eigenstrat
## ross lazarus me fecit august 14 2007
## convertf seems to want a 7 column pedigree
## eigenstrat format is transposed with 1 line per snp and
## number of ref alleles for each marker for each subject
## subjects are in indiv file as sampleid gender label
## markers are in a linkage pedigree map file format
## how to avoid holding entire ped file in ram?
## read a line,
## need an allele count
## start by assuming first seen allele is major, then reverse if wrong
"""

import sys,os,shutil,array,time,subprocess,tempfile,glob
from optparse import OptionParser

thisprog = os.path.basename(sys.argv[0])

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


def readMap(fprefix="example"):
    """
    """
    map = []
    f = file('%s.map' % fprefix,'r')
    for l in f:
        ll = l.strip().split()
        if len(ll) >= 4:
            map.append((ll[:4]))
    return map

def majAllele(adict={'A':20,'C':100}):
    """return commonest allele
    """
    ak = adict.keys()
    if len(ak) == 1: # mono
        return ak[0] # is major allele
    m = None
    maxn = -9
    for k,n in adict.iteritems():
        if n > maxn:
            maxn = n
            m = k
    return m

                
class GtoolConverter:
    """ for marchini tools"""
    def __init__(self, destdir='',sourcedir='',basename='',logf='',missval='0'):
        """
        """
        self.sourcedir = sourcedir
        self.sourcepath = os.path.join(self.sourcedir,basename)
        self.destdir = destdir
        self.destpath = os.path.join(self.destdir,basename)
        self.logf = logf
        self.missval = missval
        self.basename = basename
        (tlf,self.lfname) = tempfile.mkstemp()
        
    def writeOut(self):
        """
        """
        mapname = os.path.join(self.sourcedir,'%s.%s' % (self.basename,'map'))
        cl = 'cp %s %s' % (mapname,self.destdir)
        p = subprocess.Popen(cl,shell=True)
        retval = p.wait() # copy map to lped
        print 'cp cl=',cl
        cl = 'plink --file %s --make-bed --out %s --missing-genotype %s > %s' % \
             (self.sourcepath,self.destpath,self.missval,self.lfname)
        print 'plink cl=',cl
        p = subprocess.Popen(cl,shell=True)
        retval = p.wait() # run plink
        plog = file(self.lfname,'r').read()
        os.unlink(self.lfname)
        self.logf.write(plog)
        print 'Rgenetics %s http://rgenetics.org SNPTEST Tools, rgGTOOL.py starting at %s' % (myversion,timenow())
        pname = sys.argv[1]
        lpedname = pname.split('.ped')[0] # get file name part
        outname = sys.argv[2]
        discrete = sys.argv[3]
        logf = sys.argv[4]
        outdir = sys.argv[5]
        cdir = os.getcwd()
        me = sys.argv[0]
        mypath = abspath(os.path.join(cdir,me)) # get abs path to this python script
        shpath = abspath(os.path.sep.join(mypath.split(os.path.sep)[:-1]))
        alogf = abspath(os.path.join(cdir,logf)) # absolute paths
        apedf = abspath(os.path.join(cdir,'%s.ped' % lpedname)) # absolute paths
        amapf = abspath(os.path.join(cdir,'%s.map' % lpedname)) # absolute paths
        outg = abspath(os.path.join(outdir,'%s.gen' % outname)) # absolute paths
        outs = abspath(os.path.join(outdir,'%s.sample' % outname)) # absolute paths
        workdir = abspath(os.path.sep.join(mypath.split(os.path.sep)[:-1])) # trim end off './database/files/foo.dat' 
        os.chdir(workdir)
        tlogname = '%s.logtemp' % outname
        sto = file(tlogname,'w')
        sto.write('rgGTOOL.py: called with %s\n' % (sys.argv)) 
        exme = '/usr/local/bin/gtool'
        vcl = [exme,'-P','--ped',apedf,'--map',amapf,'--discrete_phenotype',discrete,'--og',outg,'--os',outs]
        #'/usr/local/bin/plink','/usr/local/bin/plink',pc1,pc2,pc3)
        #os.spawnv(os.P_WAIT,plink,vcl)
        p=subprocess.Popen(' '.join(vcl),shell=True,stdout=sto)
        retval = p.wait()
        sto.write('rgGTOOL.py after calling %s: vcl=%s\n' % (exme,vcl)) 
        sto.close()
        shutil.move(tlogname,alogf)
        os.chdir(cdir)



class pedPlinkConverter:
    
    def __init__(self, destdir='',lpedpath='',basename='',logf='',missval='0'):
        """
        """
        """
        shell script was:
        echo 'Rgenetics http://rgenetics.org Galaxy Tools ped file importer'
        echo "CL = $1 $2 $3 $4 $5"
        echo 'called as importPed.sh $i $filelib_library_path $o $logfile $m $userId $userEmail'
        echo "Calling Plink to import $1"
        mkdir $4
        echo 'Rgenetics http://rgenetics.org Galaxy Tools ped file importer'
        echo "CL = $1 $2 $3 $4 $5"
        echo 'called as importPed.sh $i $filelib_library_path $o $logfile $m $userId $userEmail'
        echo "Calling Plink to import $1"
        mkdir $4
        cp $1/$2.map $4/
        plink --file $1/$2 --make-bed --out $4/$2 --missing-genotype $5 > $3[rerla@hg rgenetics]$
        """
        try:
            os.makedirs(destdir)
            print '### pedPlinkConverter made destdir %s' % destdir
        except:
            pass
        self.sourcepath = lpedpath
        self.destdir = destdir
        self.destpath = os.path.join(destdir,basename)
        self.logf = logf
        self.missval = missval
        self.basename = basename
        (tlf,self.lfname) = tempfile.mkstemp()
        
    def writeOut(self):
        """
        """
        mapname = '%s.%s' % (self.sourcepath,'map')
        cl = 'cp %s %s' % (mapname,self.destdir)
        p = subprocess.Popen(cl,shell=True)
        retval = p.wait() # copy map to lped
        print 'cp cl=',cl
        cl = 'plink --file %s --make-bed --out %s --missing-genotype %s > %s' % \
             (self.sourcepath,self.destpath,self.missval,self.lfname)
        print 'plink cl=',cl
        p = subprocess.Popen(cl,shell=True)
        retval = p.wait() # run plink
        plog = file(self.lfname,'r').read()
        os.unlink(self.lfname)
        self.logf.write(plog)

class pedFbatConverter:
    
    def __init__(self, destdir='',lpedpath='',basename='',logf='',missval='0'):
        """
        """
        try:
            os.makedirs(destdir)
            print '### pedFbatConverter made destdir %s' % destdir
        except:
            pass
        self.sourcepath = lpedpath
        self.destdir = destdir
        self.destpath = os.path.join(destdir,basename)
        self.logf = logf
        self.missval = missval
        self.basename = basename
        (tlf,self.lfname) = tempfile.mkstemp()
        
    def oldwriteOut(self):
        """
        """
        basename = self.basename
        mappath = '%s.map' % self.sourcepath
        mf = file(mappath,'r')
        pedpath = '%s.ped' % self.sourcepath
        pedf = file(pedpath,'r')
        outpath = os.path.join(self.destdir,'%sfbat.ped' % basename)
        outf = file(outpath,'w')
        rsl = [x.strip().split()[1] for x in mf]
        head = ' '.join(rsl) # list of rs numbers for fbat as first line
        outf.write(head)
        outf.write('\n')
        for l in pedf:
          outf.write(l)
        outf.close()

    def writeOut(self):
        recode={'A':'1','C':'2','G':'3','T':'4','N':'0','0':'0','1':'1','2':'2','3':'3','4':'4'}  
        basename = self.basename
        mappath = '%s.map' % self.sourcepath
        mf = file(mappath,'r')
        pedpath = '%s.ped' % self.sourcepath
        pedf = file(pedpath,'r',2**24)
        outpath = os.path.join(self.destdir,'%sfbat.ped' % basename)
        outf = file(outpath,'w',2**24)
        try:
            mf = file(mappath,'r')
        except:
            sys.stderr.write('%s cannot open mappath file %s - do you have permission?\n' % (progname,mappath))
            sys.exit(1)
        try:
            rsl = [x.strip().split()[1] for x in mf]
        except:
            sys.stderr.write('## cannot parse %s' % mappath)
            sys.exit(1)   
        head = ' '.join(rsl) # list of rs numbers
        # TODO add anno to rs but fbat will prolly barf?
        outf.write(head)
        outf.write('\n')
        dorecode = 0
        for i,row in enumerate(pedf):
            if (i+1) % 1000 == 0:
                print '%s:#%d' % (pedpath,i+1)
            if i == 0:
               lrow = row.split()
               try:
                    x = [int(x) for x in lrow[10:20]] # look for non numeric codes
               except:
                    dorecode = 1
               print 'dorecode=',dorecode,'lrow=',lrow[:80]
            if dorecode:
                lrow = row.split()
                p = lrow[:6]
                g = lrow[6:]
                gc = [recode.get(x,'0') for x in g]
                lrow = p+gc
                row = '%s\n' % ' '.join(lrow)
                if i < 5:
                     print '%d: lrow=%s' % (i,lrow[:50])
            outf.write(row)
        outf.close()
            
        

    
"""
DOCUMENTATION OF convertf program:

The syntax of convertf is "../bin/convertf -p parfile".  We illustrate how 
parfile works via a toy example: (see example.perl in this directory)

DESCRIPTION OF EACH PARAMETER in parfile for convertf:

genotypename: input genotype file
snpname:      input snp file
indivname:    input indiv file 
outputformat:    ANCESTRYMAP,  EIGENSTRAT, PED, PACKEDPED or PACKEDANCESTRYMAP
genotypeoutname: output genotype file
snpoutname:      output snp file
indivoutname:    output indiv file

OPTIONAL PARAMETERS:
familynames: only relevant if input format is PED or PACKEDPED. 
            If set to YES, then family ID will be concatenated to sample ID.
            This supports different individuals with different family ID but
            same sample ID.  The convertf default for this parameter is YES.
noxdata:    if set to YES, all SNPs on X chr are removed from the data set.
            The convertf default for this parameter is NO.
nomalexhet: if set to YES, any het genotypes on X chr for males are changed
            to missing data.  The convertf default for this parameter is NO.
badsnpname: specifies a list of SNPs which should be removed from the data set.
            Same format as example.snp.  Cannot be used if input is in
            PACKEDPED or PACKEDANCESTRYMAP format.
outputgroup: Only relevant if outputformat is PED or PACKEDPED.
             This parameter specifies what the 6th column of information
             about each individual should be in the output.
             If outputgroup is set to NO (the default), the 6th column will
               be set to 1 for each Control and 2 for each Case, as specified
               in the input indiv file.  [Individuals specified with some
               other label, such as a population group label, will be
               assumed to be controls and the 6th column will be set to 1.]
             If outputgroup is set to YES, the 6th column will be set to
               the exact label specified in the input indiv file.
               [This functionality preserves population group labels.]

CONVERTF in eigensoft wants a configuration file like this:

[rerla@hg ~]$ cat /usr/local/src/eigenstrat/CONVERTF/par.PED.EIGENSTRAT 
genotypename:    example.ped
snpname:         example.pedsnp # or example.map, either works 
indivname:       example.pedind # or example.ped, either works
outputformat:    EIGENSTRAT
genotypeoutname: example.eigenstratgeno
snpoutname:      example.snp
indivoutname:    example.ind
"   ""

"""

"""
class newpedEigenConverter:

    def __init__(self,pedf = None, basename="example",destdir="/foo/bar", sourcdir="/bar/foo", \
                 linkage=True, logf = None, mappath='', \
                 labels=['FounderNonAff','FounderAff','OffspringNonAff','OffspringAff']):

     def convertPedEigen(fprefix="example",outfroot="example", linkage=True, logf = None, fo=True,oo=False, \
      labels=['FounderNonAff','FounderAff','OffspringNonAff,OffspringAff']):           
        pass
"""

class pedEigenConverter:
    
    def __init__(self,pedf = None, basename="example",destdir="/foo/bar", sourcdir="/bar/foo", \
                 linkage=True, logf = None, mappath='', \
                 labels=['FounderNonAff','FounderAff','OffspringNonAff','OffspringAff']):
        """
     def convertPedEigen(fprefix="example",outfroot="example", linkage=True, logf = None, fo=True,oo=False, \
      labels=['FounderNonAff','FounderAff','OffspringNonAff,OffspringAff']):
        """
        missing = ['N','0','.','-']
        # eigenstrat codes
        emissval = '9'
        ehet = '1'
        ehom1 = '0'
        ehom2 = '2'
        swapdict = {ehom1:ehom2,ehom2:ehom1,ehet:ehet,emissval:emissval} # if initial ref allele was wrong, use these to swap
        mdict = dict(zip(missing,missing))
        pedroot = os.path.join(sourcedir,basename)
        pedf = '%s.ped' % pedroot
        f = file(pedf,'r')
        if linkage: # read map file
            map = readMap(pedroot)
            rslist = [x[1] for x in map] # get rs numbers
##            outmap = file(mappath,'w')
##            maps = ['\t'.join(x) for x in map]
##            maps.append('')
##            logf.write('%s %s: Writing map file\n' % (thisprog,timenow()))
##            outmap.write('\n'.join(maps))
        else:
            head = f.next().strip()
            rslist = head.split()
        nrs = len(rslist) # number of markers
        elen = 2*nrs + 6 # expected # elements on each line
        logf.write('%s %s: found %d for nrs\n' % (thisprog,timenow(),nrs))
        eig = {}
        eig['founders'] = [array.array('c',[]) for x in xrange(nrs)] # marker rows, subject cols
        eig['offspring'] = [array.array('c',[]) for x in xrange(nrs)] # marker rows, subject cols
        adicts = [{} for x in xrange(nrs)] # count of alleles in a dict for each marker
        refallele = [None for x in xrange(nrs)] # list of first observed alleles
        nsubj = 0
        indiv = {'founders':[],'offspring':[]}
        for lnum,l in enumerate(f):
            ll = l.strip().split()
            if (lnum+1) % 200 == 0:
                logf.write('%s %s: Processing line %d\n' % (thisprog, timenow(),lnum+1))
            if len(ll) < elen: # ? short ?
                logf.write('%s %s: Line %d is %d long, expected %d\n' % (thisprog, timenow(),lnum,len(ll),elen))
            else:
                nsubj += 1
                sid = '%s_%s' % (ll[0],ll[1])
		if sid == '1_1': # eesh
		   sid = '%d_%d' % (nsubj,nsubj)
                isFounder = isOff = False
                status = labels[0] # founder unaff
                if ll[2] <> '0' and ll[3] <> '0': # has parent ids
                   iclass = 'offspring'
                   status = labels[2] # unaffected offspring
                   if ll[5] == '2':
                        status = labels[3] # affected offspring
                else:
                   iclass = 'founders'
                   if ll[5] == '2':
                       status = labels[1] #change from unaff to aff founder label
                gender = 'M'
                if ll[4] == '2':
                    gender = 'F'
                indiv[iclass].append('%s %s %s' % (sid,gender,status)) # for the ind file
                for snp in xrange(nrs):
                    g1,g2 = ll[2*snp + 6],ll[2*snp + 7] # pair of genos
                    if mdict.get(g1,None) or mdict.get(g2,None): # one or both missing
                        esnp = emissval # missing value
                    else:
                        if not refallele[snp]:
                            refallele[snp] = g1 # first one we saw!
                        for g in (g1,g2):
                            if adicts[snp].get(g,None): # bump
                                adicts[snp][g] += 1
                            else:
                                adicts[snp][g] = 1 # first time
                        if g1 == g2: # hom
                            if g1 == refallele[snp]:
                                esnp = ehom2 # 2 copies of current reference allele
                            else:
                                esnp = ehom1 # no copies
                        else:
                            esnp = ehet # het - always has one copy of reference allele
                    eig[iclass][snp].append(esnp) # append the eigenstrat geno code for this new subject
        for ek in eig.keys():
            lek = len(eig[ek])
            if len(eig[ek]) > 0:
                lek0 = len(eig[ek][0])
                s = 'for %s, have %d snp of len %d' % (ek,lek,lek0)
                print s
                logf.write(s)
                for x in range(lek):
                        if len(eig[ek][x]) <> lek0:
                            s = 'for row %d, len = %d, not %d' % (x, len(eig[ek][x]),lek0)
                            print s
                            logf.write(s)
        logf.write('%s %s: Now checking major allele assignment and fixing as needed\n' % (thisprog,timenow()))
        for snp in xrange(nrs): # now check to see if reference = major allele
            major = majAllele(adicts[snp])
            if major <> refallele[snp]: # either None or we need to change all the codes
                if major <> None:
                  for iclass in eig.keys():
                    for i in range(len(eig[iclass][snp])):
                        if eig[iclass][snp][i] <> emissval:
                                eig[iclass][snp][i] = swapdict[eig[iclass][snp][i]]
        self.eig = eig
        self.indiv = indiv
        self.nrs = nrs
        self.sourcedir = sourcedir
        self.logf = logf
        self.basename = basename
        self.destdir = destdir
        self.pedroot = pedroot
        self.mappath = mappath

    def eigenRowGenerator(self,destname=None,outclass=None):
        """
        res = []
        res = [''.join(x) for x in self.eig[outclass[0]]]
        if len(outclass) > 1: # must append cases to rows snpwise
            for row in range(len(res)):
                for aclass in outclass[1:]: # rest
                    newstuff = ''.join(self.eig[aclass][row])
                    res[row] = '%s%s' % (res[row],newstuff)
        lres = len(res)
        llres = len(res[0])
        s = 'writeOut %s: Now writing %d rows of %d columns of genotype output to %s\n' % (timenow(),lres,llres,outfname)
        print s
        self.logf.write(s)

        """
        for n,row in enumerate(self.eig[outclass[0]]): # have to write fully row wise
            s = ''.join(row)
            if len(outclass) > 1: # must append cases to rows snpwise
                for aclass in outclass[1:]: # rest
                    appendme = ''.join(self.eig[aclass][n]) # take the nth row
                    s = '%s%s' % (s,appendme)
            yield s # we're a generator so iterable. Neat.
        

    def writeOut(self,fo=True,oo=False,):
        """Write the converted file remember to append cases to each snp row
        """
        s = 'writeOut fo = %s,oo = %s' % (fo,oo)
        print s
        self.logf.write(s)
        nfound = len(self.indiv['founders'])
        noff = len(self.indiv['offspring'])
        destname = '%s_all' % basename
        outclass = ['offspring','founders'] # do everyone if not one or other
        if fo or noff == 0: # do founders
            outclass = ['founders',]
            destname = '%s_fo' % basename
        if oo or nfound == 0: # do offspring only
                outclass = ['offspring',]
                destname = '%s_oo' % basename
        if oo and fo: # do both
                outclass = ['offspring','founders']
                destname = '%s' % basename
        outfname = os.path.join(self.destdir,'%s.eigenstratgeno' % destname)
        outf = file(outfname,'w')
        res = self.eigenRowGenerator(destname=destname,outclass=outclass)
        for x in res: 
            # yes, this is slower than outf.write('\n'.join(res)) but that fails with framingham 
            # because the file is bigger than a python string allows!
            outf.write('%s\n' % x)
        outf.close()
        res = []
        for iclass in outclass:
                res += self.indiv[iclass] # the eigenstrat individual file
        outfname = os.path.join(self.destdir,'%s.ind' % destname)
        # '%s.ind' % self.outfroot
        outf = file(outfname,'w')
        s = 'writeOut %s: Now writing %d rows to individual file %s\n' % (timenow(),len(res),outfname)
        print s
        self.logf.write(s)
        for indiv in res:
            outf.write('%s\n' % indiv)
        outf.close()
        outfname = os.path.join(self.destdir,'%s.map' % destname)
        # '%s.map' % self.outfroot
        mapf = file('%s.map' % self.pedroot,'r')
        res = mapf.readlines()
        outf = file(outfname,'w')
        s = 'writeOut %s: Now writing %d rows to mapfile %s\n' % (timenow(),len(res),outfname)
        print s
        self.logf.write(s)
        outf.write(''.join(res))
        outf.close()
    


def makeEig(lf=None,basename='',repository='',lpedpath='',force=0):
    """wrapper for the class to make all the eigenstrat input files automagically
    or on demand. get auto working first
    """
    outsubdir = 'eigenstratgeno'
    eigrepos = os.path.join(repository,outsubdir)
    try:
        os.makedirs(eigrepos)
    except:
        pass
    neweig = os.path.join(eigrepos,basename)
    if not force:
        if os.path.isfile('%s.eigenstratgeno' % neweig):
            print '## makeEig - file %s exists but force option not set, so not remaking' % neweig
            return
        else:
            print '## makeEig - file %s.eigenstratgeno not found - making' % neweig
    pedpath = '%s.ped' % lpedpath
    mappath = '%s.map' % lpedpath
    pedf = file(pedpath,'r')
    l1 = pedf.next().strip().split()
    l2 = pedf.next().strip().split()
    pedf.close()
    pedf = file(pedpath,'r')
    if len(l1) <> len(l2): # must be fbat
        linkage = False
    else:
        linkage = True
    s = '## makeEig: basename=%s, repository=%s, lpedpath=%s,cl=%s\n' % (basename,repository, lpedpath,sys.argv)
    print >> sys.stdout, s # so will appear as blurb for file
    lf.write(s)
    # (self,pedf = None, basename="example",destdir="/foo/bar", sourcdir="/bar/foo", \
    #            linkage=True, logf = None, fo=True, oo=False, \
    #           labels=['FounderNonAff','FounderAff','OffspringNonAff','OffspringAff']):
    c = pedEigenConverter(pedf=pedf,basename=basename,destdir=eigrepos,linkage=linkage,logf = lf,mappath=mappath)
    nfound = len(c.indiv['founders'])
    noff = len(c.indiv['offspring'])
    if nfound > 0:
        c.writeOut(fo = True, oo = False)
    if noff > 0:
        c.writeOut(fo = False, oo = True)
        if nfound > 0:
            c.writeOut(fo = True, oo = True)

def makePlink(lf=None,basename='',repository='',lpedpath='',missval='',force=0):
    """ wrapper for the plink maker class
    """
    outsubdir = 'pbed' # plink binary files
    destdir = os.path.join(repository,outsubdir)
    destfile = os.path.join(destdir,basename)

    if not force:
        if os.path.isfile('%s.bed' % destfile):
            print '## makePlink - file %s.bed exists but force option not set' % destfile
            return
        else:
            print '## makePlink - file %s.bed not found - making' % destfile
    c = pedPlinkConverter(destdir=destdir,lpedpath=lpedpath,basename=basename,logf=lf,missval=missval)
    c.writeOut()
    
def makeFbat(lf=None,basename='',repository='',lpedpath='',missval='',force=0):
    """ fbatmaker
    """
    outsubdir = 'fped' # 
    destdir = os.path.join(repository,outsubdir)
    destfile = os.path.join(destdir,basename)

    if not force:
        if os.path.isfile('%s.ped' % destfile):
            print '## makeFbat - file %s.ped exists but force option not set' % destfile
            return
        else:
            print '## makeFbat - file %s.ped not found - making' % destfile
    c = pedFbatConverter(destdir=destdir,lpedpath=lpedpath,basename=basename,logf=lf,missval=missval)
    c.writeOut()
    
u = """rgConvert -g 'fram*.ped' -p /usr/local/galaxy/data/rg/library/lped -m N -f """


if __name__ == "__main__":
    """ 
    Updated oct 4 - converters now need to clone the behaviour of creating a new
    rgenetics data file which is really an html file
      

    <command interpreter="python2.4">
    rgPedEigConv.py $i.extra_files_path/$i.metadata.base_name $i.metadata.base_name
    "$title" $outfile.files_path $outfile $founders $offspring "$uf" "$af" "$uo" "$ao"
    </command>

    Pass a path to lped and an optional force rebuild flag 
    glob and make everything if force else only if missing

    """
    progname = os.path.split(sys.argv[0])[1]
    parser = OptionParser(usage=u, version="%s 1.2" % progname)
    a = parser.add_option
    a("-f","--force",action="store_true",dest="force",
      help="force - rebuild even if output already exists",default=False)
    a("-p","--path",type="str",dest="sourcepath",
      help="directory containing linkage format ped files to be converted",default=None)
    a("-s","--singlefilename",type="str",dest="onefile",
      help="Full path to the single linkage ped (with map) file to be converted - use either -p or -s, not both!",default=None)
    a("-g","--glob",type="str",dest="globme",
      help="optional glob to match ped files to be converted",default='*.ped')
    a("-m","--missing-genotype",type="str",dest="missgeno",
      help="Missing genotype code in input files - use N or 0 usually",default='N')    
    (options,args) = parser.parse_args()
    if options.onefile and options.sourcepath:
        print 'Cannot use both -p and -s options at the same time'
        print u
        sys.exit(1)
    if options.onefile or options.sourcepath:
        logfile = '%s.log' % progname
        lf = file(logfile,'w')
        if options.sourcepath <> None:
            if os.path.isdir(options.sourcepath):
                repository = os.path.split(options.sourcepath)[0] # eg foo/lped is foo 
                print 'sourcepath = %s, repository = %s' % (options.sourcepath,repository)
                flist = glob.glob(os.path.join(options.sourcepath,options.globme)) # get all ped files
                for fname in flist:
                    lpedpath = os.path.splitext(fname)[0] # get rid of ped
                    sourcedir,basename = os.path.split(lpedpath)
                    print 'multifile, fname=%s,repository=%s,sourcepath=%s, lpedpath=%s, sourcedir=%s' % \
                          (fname,repository,options.sourcepath,lpedpath,sourcedir)
                    makeFbat(lf=lf,basename=basename,repository=repository,lpedpath=lpedpath,force=options.force)
                    makeEig(lf=lf,basename=basename,repository=repository,lpedpath=lpedpath,force=options.force)
                    makePlink(lf=lf,basename=basename,repository=repository,lpedpath=lpedpath,missval = options.missgeno,force=options.force)
            else:
                print 'Is %s a directory path? Must have a directory for the -p sourcepath parameter' % options.sourcepath
                print u
                sys.exit(1)
        else:
            sourcedir,basename = os.path.split(options.onefile) # still has lped
            repository = os.path.split(sourcedir)[0] # eg foo/lped is foo
            print 'single file - repository=%s,onefile=%s, sourcedir=%s' % (repository,options.onefile,sourcedir)
            makeFbat(lf=lf,basename=basename,repository=repository,lpedpath=options.onefile,force=options.force)
            makeEig(lf=lf,basename=basename,repository=repository,lpedpath=options.onefile, force=options.force)
            makePlink(lf=lf,basename=basename,repository=repository,lpedpath=options.onefile,missval = options.missgeno,force=options.force)
        
    else:
        print 'No path or single file specified - cannot run'
        print u    
    try:
        lf.close()
    except:
        pass




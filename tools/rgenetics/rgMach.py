#! env python
"""
26 July 2010
for sensitivity analysis on mach stage 1 params the only sane option seems to be to rerun 
mach stage 1 each time at present - because all output and intermediate stage 1 files are 
named according to the run name plus the basename. 
This is fine if Could add rounds to name?

But for stage 2 changes only, stage 1 doesn't 
need to be rerun so the outputs from stage 2 might be the only ones
uniquely named according to params - eg to compare stage 2 on fo and oo after a uniform stage 1 on fo

24 July 2010
Added drmaa interface and sgeMwait job runner. individual chromosomes split into separate sge jobs and
all run syncronized so the final clean up stage waits until they're all done.

22 July 2010
mach runner 
copyright July 2010 Ross Lazarus
All rights reserved 
For the Rgenetics project
Released under the LGPL

Can create and test a random subset of markers for testing effects of density on snp imputation accuracy
ie play hide the snp.

Mach stages:

preparation:
1. If family data, can write the to_be_imputed ped as pure trios - use 'to' flag
2. If family data, filter to_be_imputed to make training ped as founders only and subset to nsamp
3. If not family data subset to_be_imputed to nsamp training set
4. If >1 chrom, split into single chrom jobs

stage 1:
if crossover and erate not available
1. Make a haps/snps set for region if is subset - otherwise use original hap/snps chrom set
2. Run mach stage 1     
otherwise recycle

stage 2:
 1. run mach stage2
 2. filter on rsq to create final ped



 many complications

 python machtest.py -b tinywga -c 22 -s 21784722 -l 123000 -r 1 -o temp -p ./test -1 fo -2 fo -a /share/shared/data/1000g/2010_06 --greedy
 seems to work pretty much as expected.

 Need a training set from main to-be-inferred dataset 
 can be 300 subjects - ?founders only if family data?
 need to see what works best. What happens if trios in training data?

 Optionally subset the incoming ped file and fix alleles/affection for mach

 has a machRun class to hide some details
 and keep to a single chromosome or region - control for a WGA input file not yet tested but done
 includes code to obtain cut down hap/snps files if region and a
 generic way to cut down a ped file
 including optionally taking a random sample of markers over an inteval
 also includes a new super clumsy plink runner - still not sure it isn't easier to just bang command lines together 
 and run them...
 started out life as a
 script to make some small MACH samples
 both family and independent to test differences in quality
 need slice of /udd/relli/1000G_Sanger_0908/0908_CEU_NoSingleton/hap/0908_CEU_NoSingleton_chr22.hap eg
 actually, updated to q:/share/shared/data/1000g
 to match a full slice from /mnt/memefs/GWAS/CAMP_610/CAMP_610.ped
 then a random subset from the camp slice to run mach and compare the imputed with genotyped markers

 use with runme.sh to generate some frq, hwe etc from subsets - founders, non-founders, all
"""
import sys,os,random,copy,tempfile,subprocess,string,time,logging,datetime,gzip,shutil
from optparse import OptionParser

try:
    import drmaa
    wecanhasSGE = True
except:
    wecanhasSGE = False

prog = os.path.split(sys.argv[0])[1]

g1000 = '/share/shared/data/1000g/2010_06' # 2010_06 or 2010_03 or 2009_08 ?

htmlheader="""<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta name="generator" content="Galaxy %s tool output - see http://g2.trac.bx.psu.edu/" />
<title></title>
<link rel="stylesheet" href="/static/style/base.css" type="text/css" />
</head>
<body>
<div class="document">
"""
htmlattr = """<h3><a href="http://rgenetics.org">Rgenetics</a> tool %s run at %s</h3>"""
htmlfooter = """</div></body></html>\n"""


class NullDevice:
    """ """      
    def write(self, s):  
        pass

def getfSize(fpath,outpath):
    """
    format a nice file size string
    """
    size = ''
    fp = os.path.join(outpath,fpath)
    if os.path.isfile(fp):
        n = float(os.path.getsize(fp))
        if n > 2**20:
            size = ' (%1.1f MB)' % (n/2**20)
        elif n > 2**10:
            size = ' (%1.1f KB)' % (n/2**10)
        elif n > 0:
            size = ' (%d B)' % (int(n))
    return size


def setLogging(appname=prog,outdir='.'):
    """setup a logger
    """
    logdir = outdir
    if not os.path.isdir(logdir):
        os.makedirs(logdir)
    today=datetime.datetime.now().strftime('%Y%m%d')
    logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename=os.path.join(logdir,'%s_%s.log' % (appname,today)),
                filemode='a')
    
def setHtmlLogging(outname='foo.html'):
    """setup a logger
    """
    logdir = os.path.split(outname)[0]
    if not os.path.isdir(logdir):
        os.makedirs(logdir)
    today=datetime.datetime.now().strftime('%Y%m%d')
    logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename=outname,
                filemode='a')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-4s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

def mtest():
    """test drmaa interface
    """
    workdir = '/tmp/foo'
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    setLogging(appname='sgeMruntest',outdir=workdir)
    s = sgeMwait(clists=[],workdir=workdir)
    s.test()
 

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

def fTranspose(inf='',ofname='',insep=' ',outsep=' '):
    """quick and dirty transpose - not needed if we only use mlgeno but for mlinfo dose munging
    all in ram - can't use column = file trickery
    """
    assert os.path.isfile(inf),'# Error - fTranspose cannot open supplied infile = %s' % inf
    f = open(inf,'r')
    d = []
    rowlen = None
    logging.info('## fTranspose reading %s' % inf)
    for i,s in enumerate(f):
        row = s.strip().split(insep)
        if i == 0: # first row
           rowlen = len(row)
        else:
            assert rowlen == len(row),'# Error - fTranspose inf %s mixed rows %d; at %d, %d' % (inf,rowlen,i,len(row)) 
        d.append(row)
    logging.info('## fTranspose transposing')
    d = zip(*d)
    logging.info( 'writing %s' % ofname)
    fo = open(ofname,'w')
    for row in d:
      fo.write(outsep.join(row))
      fo.write('\n')
    fo.close()
   
 
class sgeMwait():
    """ 
    got DRMAA and a Sun Grid Engine cluster ? 
    If not, this SGE submission code is about as useful as a chocolate teapot. Yum.
    Takes a list of command lines, submits them to SGE and waits for the last one to finish
    If any member of the list is itself a list, these are run as a batch, assuming that they need to finish
    serially - eg phase 1 then phase 2 of MACH all have to finish for each distinct chromosome before the
    final cleanup of low rsq alleles and pbed creation
    Useage:
    create a list of command lines for sge to run as clists - if any of the list entries are
    themselves lists, the command lines will be run in a single job as a batch script -  call as eg:
        sge = sgeMwait(clists=clists,workdir=options.outpath,outname=options.outname)
        alogname = sge.mRun() # this will return when all the jobs which may themselves be serial are done
        allog = open(alogname,'r').readlines()
    stolen brazenly from http://code.google.com/p/drmaa-python/wiki/Tutorial
    and tinkered. 
    """
    def __init__(self,clists=[],workdir=None,outname=None,scriptbase=['#!/bin/sh','#$ -cwd','#$ -V','#$ -S /bin/sh'],**kwd):
        self.clists = clists   
        self.scriptbase = scriptbase
        if workdir == None:
            workdir = os.getcwd()
        self.cd = os.path.abspath(workdir) 
        self.workdir = workdir 
        self.outname = None
        opf = 'drmaa.log'
        if outname:
            self.outname = outname
            opf = '%s_drmaa.log' % outname
        self.opath=":%s" % os.path.join(workdir,opf)   
        self.opf = os.path.join(workdir,opf)    
 
    def init_job_template(self,jt, exe, args, as_bulk):
        jt.workingDirectory = self.workdir
        jt.remoteCommand = exe
        jt.args = args
        jt.joinFiles=True
        jt.errorPath = ":%s" % self.opath
        if as_bulk:
            jt.outputPath = '%s.%s' % (self.opath,drmaa.JobTemplate.PARAMETRIC_INDEX)
        else:
            jt.outputPath = self.opath
        return jt
    
        
    def mRun(self,timeOut=drmaa.Session.TIMEOUT_WAIT_FOREVER):
        """ can we chain 2 jobs in a runJob without a script - no.
        this writes a shell script if there are multiple 
        command lines in a clists element, then runs an sge submit on that.
        Simple CL are run as simple jobs
        All jobs must finish before this will return - be warned 
        Obviously this is crucial for apps like MACH where each chromosome needs a series of steps before
        subject dosage or best guess files can be built.
        """
        assert len(self.clists) > 0,'sgemWait class mRun called with empty clists - not much use?!'
        s=drmaa.Session()
        s.initialize()
        alljids = []
        alljts = []
        oldcd = os.getcwd()
        if self.cd > '':
            try:
            	os.makedirs(self.cd) 
            except:
                pass
            os.chdir(self.cd)
            logging.info('## mRun cd to %s' % (self.cd))
        for clist in self.clists:
            if type(clist) == type('  '): # simple case     
                c = clist.split()
                logging.info('# mRun single clist = %s' % clist)
                jt = self.init_job_template(jt=s.createJobTemplate(), exe=c[0], args=c[1:], as_bulk=False)
            else: # serial tasks for a single sge thread that must run in order...
                script = self.scriptbase[:] # lazy copy
                submitme=datetime.datetime.now().strftime('SGE_machtest_%Y_%m_%d_%H_%M_%S.sh')
                if self.cd <> None:
                    submitme = os.path.join(self.cd,submitme)
                batchf = open(submitme,'w')
                script += clist
                batchf.write('\n'.join(script))
                batchf.write('\n')
                batchf.close()
                logging.info('# mRun making script = %s as %s' % (str(script),submitme))
                jt = self.init_job_template(jt=s.createJobTemplate(), exe='/bin/sh', args=[submitme,], as_bulk=False)                 
            jobid = s.runJob(jt)
            alljids.append(jobid)
            alljts.append(jt)
            time.sleep(1)
        logging.info('# submitted jobids: %s' % alljids)
        s.synchronize(alljids,timeOut,False) # await the last one
        for i,jid in enumerate(alljids):
            logging.info('jid %s:' % str(jid))
            jinfo=s.wait(jid, drmaa.Session.TIMEOUT_WAIT_FOREVER)
            logging.info("id: %s resourceUsage: %s" % (jid,jinfo._asdict()['resourceUsage']))
            s.deleteJobTemplate(alljts[i])
        s.exit()
        if self.cd <> None:
            os.chdir(oldcd)
        return self.opf # so we can check mask stuff if needed
            
    def addCl(self,cl=None):
        """ append another command in preparation for an mRun call
        """
        if cl:
            self.clists.append(cl)
    
    def test(self):
        """
        """
        self.clists = []
        skel = 'ls -lt >> foo'
        skel2 = [skel,skel]
        skel3 = [skel,skel,skel]
        self.addCl('ls -lt > foo')
        self.addCl(skel3)
        self.addCl(skel2)
        logging.info('## sgeMwait test clists=%s' % (str(self.clists)))
        self.mRun()
            
class pedFile():
    """ here we go again
    specialised slicer - plink cannot currently autoprune a file to give optimal complete trios
    Much stuffing around to create an 'optimal' puretrio pedfile if multiple offspring - an affected one
    is chosen in preference to any unaffected ones and only one is ever put out.
    Alternatively, founders only or offspring only can be chosen
    TODO make sure only one offspring per family for oo - code not yet tested
    eg to slice a random 50% fraction from chr22 only and write founders only
    p = pedFile(basename='/opt/galaxy/test-data/tinywga')
    p.subsetPed(chrom='22',offset=0,length=999999999,randFrac=0.5,putOut='fo',outPath='/tmp/foo')    
    """
    def __init__(self,basename=None,**kwd):
        """
        """
        self.basename = basename
        self.mapname = '%s.map' % basename
        self.pedname = '%s.ped' % basename
        assert os.path.isfile(self.mapname),'## error pedfile instantiated but no map available at %s' % mapfile
        assert os.path.isfile(self.pedname),'## error pedfile instantiated but no ped available at %s' % pedfile
        self.pfile = open(self.pedname,'r')
        self.mapf = open(self.mapname,'r') 
        self.initMap()
        self.initPed()

    def refreshIndices(self,useme=self.lmap):
        """ do this at init and before slicing
        """
        self.rslist = [x[1] for x in useme]
        self.clist = [x[0] for x in useme]
        self.cset = set(self.clist)
        self.olist = [x[3] for x in useme]

        
    def initMap(self):
        """prepare for slice"""
        mapl = self.mapf.readlines()
        self.lmap = [x.strip().split() for x in mapl if len(x.split()) >=4]
        self.refreshIndices(useme=self.lmap)
        self.mslice = range(len(self.rslist)) # index for each active marker - can be changed by slice
        self.lenmap = len(self.lmap)
        mins = dict(zip(self.cset,[sys.maxint for x in self.cset]))
        maxs = dict(zip(self.cset,[-9 for x in self.cset]))
        for i,x in enumerate(self.clist):
            ofs = self.olist[i]
            if ofs < mins[x]:
                mins[x] = ofs
            if ofs > maxs[x]:
                maxs[x] = ofs  
        self.mapf.seek(0)
        self.mapl = mapl
        self.cmaxs = maxs
        self.cmins = mins # these are useful for slicing
        
    def sliceMap(self,chrom=None,offset=0,length=sys.maxint,randFrac=None):
        """ destructive slice - can be undone by calling sliceMap again
        """
        assert chrom in self.cset,'# error sliceMap called with chrom %s not found in cset %s' % (chrom,self.cset)
        end = offset + length
        # refresh all indices
        self.refreshIndices()
        mslice = [i for i,x in enumerate(self.lmap) if (x[0]==chrom and int(x[3]) >= offset and int(x[3]) <= (end))] 
        if randFrac > 0 and randFrac < 1.0: # random subset of all markers for testing eg
            n = int(len(mslice)*randFrac)
            assert n > 0,'sliceMap error %f of %d < 1' % (randFrac,len(mslice))
            randm = random.sample(mslice,n) # subset of marker indices
            randm.sort() # sample should retain order but..doesn't seem to?
            mslice = randm
        assert len(self.mslice) > 0,'# error sliceMap created an empty new map!'
        self.mslice = mslice
        self.lenmap = len(mslice)
        self.refreshIndices(useme=mslice) # now perverted until next call to initMap
    
    def initPed(self):
        """ prepare pedigree structures needed for setupPed which
        may need to be run multiple times per pedFile
        """       
        peds = {}
        offspring = {}
        trioped = {}
        noffs = {}
        affofs = {}
        for row in self.pfile: # need > 1 pass to find best (one of the affected offspring) choices for strict trios
            srow = row.split()
            assert len(srow) == 6+2*self.lenmap,'setupPed error - short row len %d expected %d' % (len(srow),6+2*self.lenmap)
            ped = srow[:6]
            fid = ped[0]
            iid = ped[1]
            k = '%s_%s' % (fid,iid)
            peds.setdefault(k,copy.copy(ped))
            if ped[2] <> '0' or ped[3] <> '0': # non founder
                offspring.setdefault(k,copy.copy(ped))
                noffs.setdefault(fid,0)
                noffs[fid] += 1 # record each offspring
               # optimise choice - select affected offspring if possible
                if ped[5] == '2': # affected
                    affofs.setdefault(fid,[])
                    affofs[fid].append(iid)
        self.pfile.seek(0)
        self.hastrios = False
        if len(offspring) > 0:
            self.hastrios = True
        self.peds = peds
        self.offspring = offspring
        self.trioped = trioped
        self.noffs = noffs
        self.affofs = affofs
        self.lenped = len(peds)

    def setupPed(self,putOut='all'):
        """prepare for subset"""
        pureTrios = False
        if putOut == 'to':
            pureTrios = True
        fidDone = {}  
        self.putOut = putOut          
        for ped in self.offspring.values(): # flag offspring for inclusion or not
            fid,iid,pid,mid = ped[:4]
            dadk = '%s_%s' % (fid,pid)
            mumk = '%s_%s' % (fid,mid)
            kidk = '%s_%s' % (fid,iid)
            dad = self.peds.get(dadk,None)
            mum = self.peds.get(mumk,None)
            kid = self.peds.get(kidk,None)        
            if ((dad != None) or (mum != None)) and (kid != None):
                saveme = 1 # save all offspring if non onlyOne
                if pureTrios:
                    if ((dad == None) or (mum == None)):
                        saveme = 0 # don't save non nuclear trios
                    if fidDone.get(fid,None):
                        saveme = 0 # only one per family
                    else:
                        a = self.affofs.get(fid,None) # see if there are any
                        if a <> None:
                            if iid not in a: # there are affected and this is not one don't write
                                saveme = 0
                if saveme:
                    fidDone.setdefault(fid,1) # flag no more
                    self.trioped.setdefault(dadk,1) # include this complete trio in _trio file
                    self.trioped.setdefault(mumk,1)
                    self.trioped.setdefault(kidk,1)
        

    def writePed(self,outPath=None,subsetn=None):
        """write out a potentially filtered ped and map 
        remember to call sliceMap to set up the markers to be written out
        and setupPed to set up the pedigree - eg for fo or puretrios to be imputed
        Take care of number to letter alleles and set -9 affection to 0 to placate mach1.06a
        """
        putOutVals = ['all','fo','oo','to']
        assert outPath <> None,'## error writePed called without outpath'
        assert self.putOut in putOutVals,\
          '# error pedfile writePed called with putOut = %s not in %s - remember to call setupPed first?' % (self.putOut,putOutVals)
        frac = None
        if subsetn:
            assert self.putOut in ['oo','fo'],'# error in writePed - frac = %f but putOut = %s - odd?' % (frac,self.putOut)
            if self.lenped > subsetn:
                frac = float(subsetn)/self.lenped # don't subset if too few to start with
        alleledict = {'0':'0','1':'A','2':'C','3':'G','4':'T','A':'A','C':'C','G':'G','T':'T','-9':'0','N':'0','-':'0'}
        outpedf = open('%s.ped' % outPath,'w')
        outmapf = open('%s.map' % outPath,'w')
        newmap = [self.mapl[x] for x in self.mslice] # haha
        outmapf.write(''.join(newmap))
        outmapf.write('\n')
        outmapf.close()
        cols = [6+2*x for x in self.mslice]
        cols += [7+2*x for x in self.mslice]
        cols.sort()
        self.pfile.seek(0)
        recode = None
        fiddone = {}
        for row in self.pfile: # finally can write out what we are looking for
            srow = row.split()
            ped = srow[:6]
            fid,iid,pid,mid,gender,aff = ped
            k = '%s_%s' % (fid,iid)
            writeme = False
            if self.putOut == 'fo':
                if (pid == '0') and (mid == '0'):
                    writeme = True
            elif self.putOut == 'oo':
                if (pid <> '0') or (mid <> '0'): 
                    if not fiddone.get(fid,None): # only one per fid so independent
                        writeme = True
                        fiddone[fid] = fid
            elif self.putOut == 'to': # trios only
                if self.trioped.get(k,None): # a nuclear trio to put out to triofile
                    writeme = True
            elif self.putOut == 'all':
                writeme = True
            else:
                assert False, 'Odd, putOut=%s in writePed? Nothing will be written!' % self.putOut
            if writeme and frac <> None: # random sample to density
                writeme = (random.random() > frac)
            if writeme:
                g = [srow[x] for x in cols]
                if recode == None:
                    try:
                        test = [int(x) for x in g[:100]] # are there number alleles?
                    except:
                        test = []
                    if len(test) > 0:
                        recode = True
                    else:
                        recode = False
                if recode:
                    g = [alleledict.get(x.upper(),'?') for x in g]  
                if ped[5] == '-9':
                    ped[5] = '0' # mach does not like -9 for affection
                ped += g                
                outpedf.write(' '.join(ped))
                outpedf.write('\n')
        outpedf.close()

class machRun():
    """
    mach run container - inputs, intermediates, outputs, settings for a chromosome or part thereof
    has code to deal with the reference haplotypes in 1000g format to ensure that a specific run has
    the input files it needs - by chr region if necessary - then can generate a command line for
    sge submission or direct execution with subprocess if no sge available
    """  
    def __init__(self, basename=None, stage1name=None, snpsource=None, hapsource=None, outname=None,
                stage2inname=None,rounds=None,inseed=0,machexe='mach1',cd=None,nmax=300,mask=None,
                chrom=None,offset=None,length=None,outpath=None,noSGE=True,reusePhase1=False,**kwd):
        """
        all basenames include full paths
        basename is ped file basename
        snpsource and hapsource point to the set of reference haplotypes - hap/snps pair or if None, these will be sorted out 
        including checking to see if a subset of chrom is required
        stage1name is the name for the crossover and erate files from mach stage 1 - made if not exists
        outname is used as stage2 output name
        """
        self.outpath = os.path.abspath(outpath)
        self.mask = mask
        self.stage2inname = stage2inname
        self.hapsource=hapsource
        self.chrom = chrom
        self.offset = offset
        if self.offset == None or self.offset < 0:
            self.offset = 0
        self.length = length
        if self.length == None or self.length < 0: # negative means all
            self.length = sys.maxint
        self.cd = cd
        self.nmax = nmax
        self.machexe = machexe
        self.basename = basename     
        self.hapsource = hapsource # reference haps for imputation
        self.snpsource = snpsource # reference snp names for imputation
        self.rounds = rounds
        self.inseed = inseed
        self.stage1name = stage1name
        self.outname = outname
        self.crossratename = '%s.rec' % stage1name
        self.eratename = '%s.erate' % stage1name 
        self.greedy = kwd.get('greedy',False)
        self.compact = kwd.get('compact',False)
        self.noSGE = noSGE
        self.reusePhase1 = reusePhase1
        assert rounds > 0,'## error %s machRun class instance initiated with rounds not > 0' % self.outname
        assert self.basename <> None,'## error %s machRun class instance initiated with missing basename'  % self.outname
        assert os.path.exists('%s.ped' % self.basename),'## error  %s no ped file found for machRun class instance basename %s' % (self.outname, basename)
        self.chroms,self.starts,self.ends = self.getExtent()
        assert self.chrom in self.chroms,'## error %s requested chromosome %s not in %s.map chroms (=%s) in machRun' % (self.outname,self.chrom,self.basename,self.chroms)  

        
    def slicehaps(self,newPrefix=None,mapPrefix=None):
        """ specific to mach hap format - take a slice from 1000g data corresponding to our slice
        or link to source haps if the slice is the entire chromosome
        note up to 2 fields may preceed the haplotype string !
        Sun,Jul 18 at 12:13am head /share/shared/data/1000g/map/chr22.map
        22	chr22:14431249	14431249
        22	rs6518413	14432239
        22	chr22:14433730	14433730
        Sun,Jul 18 at 12:13am head /share/shared/data/1000g/snps/chr22.snps
        chr22:14431249
        rs6518413
        chr22:14433730
        rs2844885
        chr22:14435122
        """
        assert newPrefix <> None, '# error - slicehaps needs a prefix for output'
        snpf = '%s/snps/chr%s.snps' % (self.hapsource,self.chrom)
        assert os.path.isfile(snpf),'# error - slicehaps cannot open snp file %s' % snpf
        hapf = '%s/hap/chr%s.hap' % (self.hapsource,self.chrom)
        assert os.path.isfile(hapf),'# error - slicehaps cannot open hap file %s' % hapf
        mapf = '%s/map/chr%s.map' % (self.hapsource,self.chrom)
        assert os.path.isfile(mapf),'# error - slicehaps cannot open map file %s' % mapf
        mapl = open(mapf,'r').readlines() # chr name offs
        mapls = [x.split() for x in mapl]
        lastone = self.offset + self.length
        outhapf = '%s_ref.hap' % newPrefix
        outsnpf = '%s_ref.snps' % newPrefix
        outmapf = '%s_ref.map' % mapPrefix
        mapi = [i for i,x in enumerate(mapls) if (int(x[2]) >= self.offset and int(x[2]) <= (lastone))] # use indices
        assert len(mapi) > 0, '# error slicehaps %s has zero length from %d to %d in %s' % (mapf,self.offset,lastone,snpf)
        if len(mapi) == len(mapl): # not a subset - return path to whole chromosome of data
            if os.path.exists(outhapf):
                os.system('rm -rf %s' % outhapf)
            if os.path.exists(outmapf):
                os.system('rm -rf %s' % outmapf)
            if os.path.exists(outsnpf):
                os.system('rm -rf %s' % outsnpf)
            shutil.copyfile(snpf,outsnpf)
            shutil.copyfile(hapf,outhapf)
            shutil.copyfile(mapf,outmapf) 
        else:
            maps = open(mapf,'r').readlines()
            outmaps = [maps[i] for i in mapi]
            outmap = open(outmapf,'w')
            outmap.write(''.join(outmaps)) # create new mach haplo map
            snps = open(snpf,'r').readlines()
            outsnps = [snps[i] for i in mapi] # subset	x
            outsnp = open(outsnpf,'w')
            outsnp.write(''.join(outsnps))
            outsnp.close()
            outhap = open(outhapf,'w')
            h = open(hapf,'r')
            for row in h: # this is not as simple as you might think
                r = row.strip().split() # may be up to 3 - take last
                rh = r[-1] # hap
                rb = r[:-1] # start
                subh = [rh[i] for i in mapi] # ugh - but that's the format - optional row id(s)
                subh.append('\n')
                outhap.write('\t'.join(rb)) # preferred by mach - note MUST be tab
                outhap.write('\t')
                outhap.write(''.join(subh)) 
            outhap.close()
            h.close()
        return outsnpf,outhapf,outmapf
    
    def makeClines(self):
        """
        constructs all needed files plus command lines that will run mach stage 1 if needed then stage 2
        these commands can be run using SGE or directly if no sge available
         
        need basename=None,refname=None, eratename=None, crossratename=None, outname=None,haps=None,snps=None,rounds=None,seed=0
        stage2
        mach1 -d ${MF}.dat -p ${MF}.ped -s ${FNAME}.snps -h ${FNAME}.hap --errorMap ${MF}.erate 
        --crossoverMap ${MF}.rec --greedy --autoFlip --seed $RND --mle --mldetails -o $MF >& ${MF}.impute.log 
        if no erate/crossrate files exist, make them - this could take a long time
        """
        datname = '%s.dat' % self.stage1name
        if not os.path.exists(datname):
            self.makeDat(self.stage1name)
        datname = '%s.dat' % self.basename
        if not os.path.exists(datname):
            self.makeDat(self.basename)
        datname = '%s.dat' % self.stage2inname
        if not os.path.exists(datname):
            self.makeDat(self.stage2inname)
        if self.snpsource == None or (not os.path.exists(self.snpsource) or not os.path.exists(self.hapsource)):
            outsnpf,outhapf,outmapf = self.slicehaps(newPrefix=self.stage1name,mapPrefix=self.outname) 
            # reference haplotypes - eg 1000g project for mach
            self.snpsource = outsnpf
            self.hapsource = outhapf
            self.mapsource = outmapf
        assert os.path.exists(self.snpsource),'## error no ref snps file found for machRun compute refname %s' % self.stage1name
        assert os.path.exists(self.hapsource),'## error no ref hap file found for machRun compute refname %s' % self.stage1name
        assert os.path.exists(self.mapsource),'## error no ref map file found for machRun compute refname %s' % self.stage1name
        lcl = []
        if not self.reusePhase1 or not (os.path.exists(self.eratename) and os.path.exists(self.crossratename)): # make
            seed = self.nextSeed()
            cl = 'mach1 -d %s.dat -p %s.ped -s %s -h %s -o %s --seed %d -r %d --autoflip' % (self.stage1name,self.stage1name,
                self.snpsource,self.hapsource,self.stage1name,seed,self.rounds) 
            if self.compact:
                cl = '%s --compact' % cl
            if self.greedy:
                cl = '%s --greedy' % cl
            lcl.append(cl)
        datname = '%s.dat' % self.stage2inname
        seed = self.nextSeed()
        cl = """mach1 -d %s.dat -p %s.ped -h %s -s %s --errorMap %s.erate --crossoverMap %s.rec --autoflip --seed %d --mle --mldetails -o %s""" % \
          (self.stage2inname,self.stage2inname,self.hapsource,self.snpsource,self.stage1name,self.stage1name,seed,self.outname)
        if self.compact:
            cl = '%s --compact' % cl
        if self.greedy:
            cl = '%s --greedy' % cl
        if self.mask:
            cl = '%s --mask %f' % (cl,self.mask)
        cl
        lcl.append(cl)
        return lcl

        
    def run(self,cl=[]):
        """ direct runner for commands if SGE not available       
        """
        if self.cd > '':
            cd = self.cd
        else:
            cd = os.getcwd()
        alog = []
        alog.append('## Rgenetics: http://rgenetics.org Galaxy Tools MACH runner\n')
        for cmd in list(cl):
            fplog,plog = tempfile.mkstemp()
            sto = file(plog,'w')
            if self.cd:
                x = subprocess.Popen(cmd,shell=True,stdout=sto,stderr=sto,cwd=cd)
            else:
                x = subprocess.Popen(cmd,shell=True,stdout=sto,stderr=sto)
            retval = x.wait()
            sto.close()
            try:
                lplog = file(plog,'r').readlines()
                alog += lplog
                alog.append('\n')
            except:
                alog.append('### %s Strange - no std out from MACH when running command line\n%s\n' % (timenow(),cmd))
            os.unlink(plog) # no longer needed
        return alog
        
    def nextSeed(self):
        if self.inseed <> 0:
            return self.inseed
        else:
            return random.randint(1,32767)
            
    def makeDat(self,fname=None):
        """ make a dumb old .dat file for mach to match the map - note 
        additional affection pheno field so mach can read plink style 6 column pedigrees
        """
        assert fname <> None, '# error makeDat called with None as fname'
        mapname = '%s.map' % fname
        assert os.path.isfile(mapname) or os.path.islink(mapname)
        m = open(mapname,'r').readlines()
        mlist = [x.strip().split() for x in m if len(x.strip().split()) >=3]
        rslist = ['M %s' % x[1] for x in mlist]
        datname = '%s.dat' % fname
        os.system('rm -rf %s' % datname)
        outf = file(datname,'w')
        outf.write('A Affection\n')
        outf.write('\n'.join(rslist))
        outf.write('\n')
        outf.close()        
        
    def cleanAff(self,fname=None):
        """remove all -9 from ped.clean
        now deprecated and now done inside the pedFile class along with numeric 
        allele translation as the MACH reference chromosomes are all letter alleles
        and mach barfs if they're different (!)
        """
        assert fname <> None, '# error cleanAff called with None as fname'
        cl = "sed 's/-9/0/g' %s.ped > %s.ped.clean" % (fname,fname)
        os.system(cl)
        os.unlink('%s.ped' % fname)
        os.rename('%s.ped.clean' % fname,'%s.ped' % fname)
        
    def truncTrain(self,fname=None):
        """and truncate to (say) 200 rows
        """
        cl = 'head -%d %s.ped > %s.ped.short' % (self.nmax,fname,fname)
        os.system(cl)

    def getExtent(self):
        """ find bounds of mapfile"""
        mapname = '%s.map' % self.basename
        maps = open(mapname,'r').readlines()
        m = [x.strip().split() for x in maps if len(x.strip().split()) >= 4]
        o = [int(x[3]) for x in m] # all offsets
        c = [x[0] for x in m] # all chroms
        cs = set(c)
        mins = dict(zip(cs,[sys.maxint for x in cs]))
        maxs = dict(zip(cs,[0 for x in cs]))
        for i,x in enumerate(c):
            ofs = o[i]
            if ofs < mins[x]:
                mins[x] = ofs
            if ofs > maxs[x]:
                maxs[x] = ofs          
        return cs, [mins[x] for x in cs], [maxs[x] for x in cs]

        

def machToPlink(chroms=[],inbase=None,plinke='plink',outpath=None,r2thresh=0.3,qualthresh=0.0,dped={},useSGE=wecanhasSGE):
    """
    some code to finalize mach imputation outputs
    filters each existing mlinfo file on an rsq threshold then creates a plink binary 'clean' version

    Should probably add QC autofilter on hwe, frequency and missingness
    
    note given current design, cannot be part of the machRun class which is single chromosome specific
    could wrap machrun into a bigger mach class in which case it makes sense for this to be moved there
    """ 
        
    def mlinfoConv(inmachfilepath=None,outpath=None,r2thresh=0.3,qualthresh=0.0,dped={}):
        """ 
        simplest approach - use mlinfo to filter reasonable rsq values for the 'best guess' alleles
        probably easier to do it ourselves than futz with gengen perl crap
        Thu,Jul 22 at 12:04am head /share/shared/data/1000g/2010_06/map/chr22.map 
        22      chr22:14431249  14431249
        22      rs6518413       14432239
        22      chr22:14433730  14433730
        Sat,May 22 at 12:12pm head *chr22.mlinfo
        SNP     Al1     Al2     Freq1   MAF     Quality Rsq
        rs11089130      C       G       0.2653  0.2653  0.5410  0.0176
        rs738829        A       G       0.4705  0.4705  0.5037  0.0549
        rs915674        A       G       0.0736  0.0736  0.8583  0.0050
        """
        assert inmachfilepath <> None,'# error mlinfoConv given None as inmachfilepath'
        logging.info('## mlinfoConv doing %s' % inmachfilepath)
        base_name = os.path.basename(inmachfilepath)
        inmap = open('%s_ref.map' % inmachfilepath,'r').readlines()
        mlinfo = open('%s.mlinfo' % inmachfilepath,'r')
        outroot = os.path.join(outpath,base_name)
        outpedfroot = '%s_clean' % outroot
        outped = open('%s.ped' % outpedfroot,'w')
        outmap = open('%s.map' % outpedfroot,'w')
        passing = []
        failing = []
        useme = [] # indices
        for n,row in mlinfo.readlines():
            mli = row.split()
            if n == 0:
                mlih = mli[0]
                mlih = [x.lower() for x in mlih]
                rsqpos = mlih.index('rsq')
                qualpos = mlih.index('quality')
            else:
                if float(row[rsqpos]) >= r2thresh and float(row[qualpos]) >= qualthresh:
                    passing.append(row)
                    useme.append(n) # index into map for passing rows
                else:
                    failing.append(row)
        logging.info('## mlinfoconv len(useme)=%d len(inmap)=%d' % (len(useme),len(inmap)))
        logging.info('len dped = %d; len map = %d; len mlinfo = %d' % (len(dped),len(inmap),len(mli)))
        if len(useme) == 0:
            logging.warn('### NO imputed markers passed the RSQ filter! No output!!')
        for j in useme:
            row = inmap[j].split() # use this one
            row.insert(2,'0') # fake a genetic map 0 to make this plink map style
            outmap.write('\t'.join(row))
            outmap.write('\n')
        outmap.close()
        ingeno = '%s.mlgeno' % inmachfilepath
        ingenogz = '%s.mlgeno.gz' % inmachfilepath
        if os.path.exists(ingenogz):
            mlg = gzip.open(ingenogz)
        else:
            mlg = open(ingeno,'r') # big
        for pedi,row in enumerate(mlg): # 500003->20100003 ML_GENO G/G A/G G/G C/C
            row = row.split()
            if len(row) > 0:
               genos = []
               iid,fid = row[0].split('->')
               k = '%s_%s' % (iid,fid)
               thisped = dped.get(k,None) # 
               assert thisped <> None, '# error - ID %s not found in dped' % k
               assert row[1] == 'ML_GENO','## file %s row %d col 2 %s <> ML_GENO' % ('%s.mlgeno' % base_name,i,row[1])
               row = row[2:]
               for j in useme:
                    g = row[j] # keep indices in useme
                    g1,g2 = g.split('/')
                    genos.append(g1)
                    genos.append(g2)
               s = ' '.join(thisped)
               outped.write('%s %s\n' % (s,' '.join(genos)))
        outped.close()
        return outpedfroot
        
    
    
    # machToPlink starts here
    fp,basename = os.path.split(inbase) # get basename
    outpedroots = []
    for chrom in chroms:
        inname = '%s_chr%s' % (basename,chrom)
        inbasepath = os.path.join(outpath,inname)
        outpedfroot = mlinfoConv(inmachfilepath=inbasepath,outpath=outpath,r2thresh=r2thresh,
                 qualthresh=qualthresh,dped=dped)
        outpedroots.append(os.path.abspath(outpedfroot))
    # now amalgamate
    paf = 'plinkmerge_%s.txt' % basename
    plinklist = ['%s.ped %s.map' % (x,x) for x in outpedroots[1:]] 
    # leave the first one out - this is what the merge-list option wants
    f = open(os.path.join(outpath,paf),'w')
    f.write('\n'.join(plinklist))
    f.write('\n')
    f.close()
    cl = '%s --noweb --file %s --make-bed --merge-list %s --out %s_clean' % (plinke,outpedroots[0],paf,inbase)
    logging.info( '## machtoplink calling %s' % cl)
    allog = []
    if not useSGE or not wecanhasSGE:
        p = subprocess.Popen(cl,shell=True,cwd=outpath)
        retval = p.wait() # run plink
        logging.info('## machtoplink done. retval = %d ' % (retval))
        alogf = os.path.join(outpath,'%s_clean.log' % inbase)
        allog = open(alogf,'r').readlines()
    else:
        sge = sgeMwait(clists=[cl,],workdir=outpath,outname=inbase)
        alogname = sge.mRun() # this will return when all the jobs which may themselves be serial are done
        allog = open(alogname,'r').readlines()
    return allog

        
def mrun():
    """mach runner    
    """
    
    def runOneChrom(clists=[],allog=[],chrom=None,p=None,mask=None):
        """ broken out to make iterating over multiple chromosomes simpler
        if no sge, use the mach run function, otherwise accumulate all the
        sge command lines since they must all complete before the final steps 
        to filter on rsq and create an amalgamated plink binary file.
        """
        stage1outname = os.path.join(options.outpath,'%s_chr%s_%s' % (options.outname,chrom,'stage1_in'))
        stage2outname = os.path.join(options.outpath,'%s_chr%s' % (options.outname,chrom))
        p.setupPed(putOut=options.stage1) 
        p.writePed(outPath=stage1outname,subsetn=options.nstage1)
        # ready for stage 1 - compute will take care of reference haplotypes
        p.setupPed(putOut=options.stage2)
        p.writePed(outPath=stage2outname)
        # ready for stage 2
        m = machRun(basename=options.basefile, stage1name=stage1outname, outname=stage2outname,
            rounds=options.rounds,inseed=int(options.seed),mask=mask,
            machexe=options.machexe,cd=None,nmax=options.nstage1,chrom=chrom,offset=options.offset,
            length=options.length,hapsource=options.happath,useSGE=useSGE,
            stage2inname=stage2outname,outpath=options.outpath,reusePhase1=options.reusePhase1)
        c = m.makeClines() # this generates intermediate files and a command line or lines
        if not useSGE:
            alog = m.run(c)
            allog += alog
        else: # append commands for a coordinated SGE splatter
            clists.append(c)

    def parseArgs(argv=None):
        """
        """
        helptext="""This is a wrapper for MACH - see http://genome.sph.umich.edu/wiki/MaCH
Purposes: impute WGA or a specific region using MACH
Optional: generate random subsets from a region and impute 

Takes an input ped/map, mach settings, source for reference haplotypes and optionally, 
subset chromosome start and length

Can evaluate imputation of masked snp using the mask parameter but need to keep the
masked fraction small so as to leave sufficient information for the mcmc.
allows compact option although to be avoided according to recent docs"""
        parser = OptionParser(usage=helptext, version="%prog 0.01")
        if len(sys.argv) == 1:
            sys.argv.append('-h')
        a = parser.add_option
        a("-1","--stage1",dest="stage1",default='fo',
          help='Stage 1 use founders only (fo) or independent offspring only (oo) for training')
        a("-2","--stage2",dest="stage2",default='all',
          help='Stage 2 use all (all), founders (fo), puretrios, or offspring only (oo) for imputation')
        a("-b","--basefile",dest="basefile", default=None,help='Ped/Map file input')
        a("-c","--chrom",dest="chrom", default=None,help='Subset to chromosome')
        a("--compact",dest="compact",default=False,action='store_true',
          help='Add MACH compact parameter (not recommended)')
        a("-e","--seed",dest="seed",default=0,type="int",
          help='Seed for all mach operations (default 0 - reseed and record seeds at each step)')    
        a("--greedy",dest="greedy",default=False,action='store_true',help='Add MACH greedy parameter')
        a("-a","--happath",dest="happath",default=None,
          help='Path to home of 1000 genomes or hapmap MACH compatible haplotypes to impute')
        a("-l","--length",dest="length",type="int",default=-1,help='Subset length')
        a("-x","--machexe",dest="machexe", default='mach1',help='MACH executable name - default is mach1')
        a("-m","--mask",dest="mask", default=None,type='float',help='MACH mask parameter for testing accuracy')
        a("-o","--outname",dest="outname", default='mymachjob',help='Title for output files')
        a("-p","--outpath",dest="outpath", default='.',help='Path for all output and intermediate files')    
        a("-q","--rsq",dest="rsq", default=0.3, type='float',help='Cutoff for simple RSQ filter when creating final output')    
        a("-r","--rounds",dest="rounds",type="int",default=50,help='MACH stage 1 rounds - eg 50')
        a("-t","--outhtml",dest="outhtml",default=None,help='Path to output html file')
        a("-f","--randfrac",dest="randfrac",type="float",default=1.0,help='Subset a random proportion of markers')
        a("-s","--start",dest="offset",type="int",default=-1,help='Subset start offset')
        a("-n","--nstage1",dest="nstage1",type="int",default=300,help='Stage 1 number of subjects')
        a("--noSGE",dest="noSGE",default=False,action='store_true',help='Ignore SGE even if available')
        a("-d","--reusePhase1",dest="reusePhase1",default=False,action='store_true',
          help='Reuse matching mach phase 1 files if rec and erate files (DO NOT set this flag for stage 1 sensitivity analyses eg!)')
        (options,args) = parser.parse_args()
        options.outpath = os.path.abspath(options.outpath)
        if not os.path.exists(options.outpath):
            os.makedirs(options.outpath)
        assert options.basefile <> None,'# error: %s must have an input ped/map basename supplied %s' % (prog,options.basefile)
        assert os.path.isfile('%s.ped' % options.basefile),'# error: %s needs a ped/map at %s' % (prog,options.basefile)
        assert os.path.isfile('%s.map' % options.basefile),'# error: %s needs a ped/map at %s' % (prog,options.basefile)
        return options
    
 
    # mrun starts here       
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    options=parseArgs(argv=sys.argv)
    options.outname = options.outname.translate(trantab)
    useSGE = wecanhasSGE and (not options.noSGE)
    scriptbase = ['#!/bin/sh','#$ -cwd','#$ -V','#$ -S /bin/sh'] # this may not always suit...
    setLogging(appname=prog,outdir=options.outpath)
    startt = time.time()
    logging.info('%s starting at %s' % (prog,timenow()))
    basepath,basename = os.path.split(options.basefile) # 
    p = pedFile(basename=options.basefile) # can now create slices
    logging.info('## finished setting up genotype data structures for %s' % options.basefile)
    if len(p.cset) == 1 and options.chrom == None: # input has only one
        options.chrom = p.cset[0]
    clists = []
    allog = []
    # set up job structures with mach command lines in case using sge
    if options.chrom <> None:
        logging.info('Single chromosome parameter %s supplied so slicing' % str(options.chrom))
        p.sliceMap(chrom=options.chrom,offset=options.offset,length=options.length,randFrac=options.randfrac)
        runOneChrom(clists=clists,allog=allog,chrom=options.chrom,p=p,mask=options.mask)
    else:
        logging.warn('# chromosome splitting - this will take a while')
        for c in p.cset: # for each chrom we found in the pedfile - assume all are full chromosomes?
            p.sliceMap(chrom=c,randFrac=options.randfrac) # use default offset/length = all
            runOneChrom(clists=clists,allog=allog,chrom=c,p=p,mask=options.mask)
    if len(clists) > 0: # must be using sge - these jobs all have to finish before we move on
        if useSGE:
            sge = sgeMwait(clists=clists,workdir=options.outpath,outname=options.outname,scriptbase=scriptbase)
            alogname = sge.mRun() # this will return when all the jobs which may themselves be serial are done
            allog = open(alogname,'r').readlines()
        else:
            logging.error('## Strange, no sge but clists=%s' % str(clists))
    # all files now ready for mach to plink conversion. Currently jsut using crude rsq threshold
    # TODO: add hwe/missingness and allele frequency filters
    if options.chrom == None: # do all available
        alog = machToPlink(chroms=p.cset,inbase=options.outname,plinke='plink',outpath=options.outpath,
           r2thresh=options.rsq,qualthresh=0.0,dped=p.peds,useSGE=useSGE)
    else:
        alog = machToPlink(chroms=[options.chrom,],inbase=options.outname,plinke='plink',outpath=options.outpath,
           r2thresh=options.rsq,qualthresh=0.0,dped=p.peds,useSGE=useSGE)
    # one way or another, alog should now contain the mach log
    allog += alog
    maskresstarts = []
    if allog:
        logging.debug('# machrun logs follow')
        logging.debug(''.join(allog))
        if options.mask > 0.0: # check for masked error estimates - ?bug in mach 106a .info file is empty
            for i,row in enumerate(allog):
                if row.lower().find('masked genotypes with mle') <> -1:
                    maskresstarts.append(i) # remember where these are - need this and next 2 lines
    if len(maskresstarts) > 0:
        maskres = [''.join(allog[i:i+3]) for i in maskresstarts] # 3 rows for each eg chrom
        maskresn = '\n'.join(maskres)
        logging.info('## Results of masking %f of %s for %s' % (options.mask,options.basefile,options.outname))
        logging.info(maskresn)
    endt = time.time()
    logging.info('# duration=%f secs' % (endt - startt))
    logging.shutdown()
    if options.outhtml:
        oh = open(options.outhtml,'w')
        oh.write(htmlheader)
        oh.write('<b>%s run at %s<br/><b>\n' % (prog,timenow()))
        if len(maskresstarts) > 0:
            oh.write('<B>## Results of masking %f of %s for %s</B>\n' % (options.mask,options.basefile,options.outname))
            oh.write('<br />\n'.join(maskres))
            oh.write('<hr />\n')
        oh.write('<b>The following output files were created. Click the name to view locally</b><br/>\n')
        flist = os.listdir(options.outpath)
        flist.sort()
        Html = []
        Html.append('<table cellpadding="5" border="0">')
        for f in flist:
            fsize = getfSize(f,options.outpath)
            Html.append('<tr><td><a href="%s">%s</a>%s</td></tr>' % (f,f,fsize))
        oh.write('\n'.join(Html))
        oh.write('\n')
        oh.close()

if __name__ == "__main__":    
    """
    python sgemach.py -b tinywga -c 22 -s 21784722 -l 123000 -r 1 -o temp -p ./test -1 fo -2 fo -a /share/shared/data/1000g/2010_06 --greedy 
    or
    python sgemach.py -b plink_wgas1_example -c 7 -s 52000000 -l 1000000 -r 5 -o plink7_1mb -p ./plinktest -1 fo -2 fo -a /share/shared/data/1000g/2010_06 --greedy --mask 0.02
    python sgemach.py -b plink_wgas1_example -c 22 -r 5 -o plink22 -p ./plink22 -1 fo -2 fo -a /share/shared/data/1000g/2010_06 --greedy --mask 0.02
    """
    std = sys.stderr
    foo = tempfile.mktemp()
    sys.stderr = foo
    mrun()
    sys.stderr = std



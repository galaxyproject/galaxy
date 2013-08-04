#!/ilocal/bin/python

""" pbvisualgeno.py """

import whrandom, time, os, stat, sys, string, glob, piddle, math, copy, random, iipgalib
import piddlePIL as pil

import util

# file name = gene_reporttype.formatextension
# report types
maxrandomtests = 0 # random snp resorts to be tested
# these run about 1000/minute on a sun ultra10 for medium sized genes
showmess = 0
myname = sys.argv[0]
genogram = 'genog'
prettybase = 'pb'
# file format extensions
htmlext = '.html'
pbfileext = 'prettybase.txt'
relpbfileext = 'relpb.txt'
tranhead = {'A':'Asthmatic', 'D':'African American', 'E':'European', 'H':'Hispanic'} # col. heading trans
testing = 0
missing = ['N','-','+']
missgeno = '0'
novalue = 0 # flags for the data display
commonhomozyg = 1
heterozyg = 2
rarehomozyg = 3
flagtran = {0:'Missing',1:'Homozygous (Common)',2:'Heterozygous',3:'Homozygous (Rare)'}
piximage = {0:'pixelgrey.jpg',1:'pixeldarkblue.jpg',2:'pixelred.jpg',3:'pixelyellow.jpg'}
missingval = 'Z' # so sorts last
pixheight = 14
pixwidth = 14
totpop = 'totpop' # fake population used for totpop snp/geno entries
alleledic = 'alleles'
genodic = 'genotypes'


def reorder(s='',sequence=[]):
    if len(sequence) == 0: # default if new sort order not provided
        return s
    else:
        news = ''
        for i in sequence:
            news += s[i]
        return news

def findsmallestkey(haps,rafsortlist,testsorts,pop,errlog):
    '''
    search the large space randomly using preshuffled lists 
    smallest number of snp to uniquely distinguish all the nonunique haps
    found by creating a tree and finding which nodes have more than 1 child
    if no search wanted, pass an empty list for testsorts
    '''
    shortest = 99999
    bestlist = []
    bestcn = []
    if len(testsorts) > 0:
        ts = copy.copy(testsorts)
    else:
        ts = []
    ts.insert(0,rafsortlist)
    i = 0
    for alist in ts:
        htree = iipgalib.genotree()
        for hap in haps:
            hap = reorder(hap,alist) # if keylist is short (eg 10% snp) will give short haps
            htree.parse(hap) # build haptree
        cn = htree.critnodes()
        if i == 0: # raf
            raflen = len(cn)
        if len(cn) < shortest:
            shortest = len(cn)
            bestlist = alist
            bestcn = cn
            besti = i
        i += 1
    rcn = []
    for acn in bestcn:
            rcn.append(bestlist[acn])
    if len(testsorts) > 0:
        if besti == 0:
            mess = '%s RAF' % pop
        else:
            mess = '%s Random #%d (RAF-%d)' % (pop,(besti-1),(raflen-shortest))
        errlog.append('%s best of %d trials, ncritsnp=%d %s' % (mess,len(ts),len(rcn),str(rcn)))
    return rcn
            
def genocomp(a,b):
    '''
    sort function which treats missing values as equivalent
    '''
    for i in range(len(a)):
        x = a[i]
        y = b[i]
        if (x == missgeno) or (y == missgeno):
            pass
            # keep looking
        elif x > y:
            return 1
        elif x < y:
            return -1
    return 0


def graphcommonalleles(genename='',sites={},pbdata={},commonsites=[],allpops={},minraf=0.0,errlog=[]):
    '''
    this needs a special print routine combined - cannot work with
    the standard output routine
    the pixel images live in /images
    note complication to print the allele loci vertically...
    '''

    loci = {}
    rafsort = {}
    rafsort10 = {}
    locilen = 0
    outfileext = htmlext
    sitekeys = sites.keys()
    sitekeys.sort()
    hapindex = 0
    for sk in sitekeys:
        sitealleles = [] # collect alleles here
        s = sites[sk]
        adic = s[alleledic]
        for a in adic.keys(): # collect all alleles for all pops at site
            if a <> totpop: # other than total
                if not a in sitealleles:
                        sitealleles.append(a)
        a1 = adic[sitealleles[0]][totpop].count
        a2 = adic[sitealleles[1]][totpop].count
        if a1 < a2 :
            sitealleles[0],sitealleles[1] = sitealleles[1],sitealleles[0] # swap so most common is first
        raf = float(min(a1,a2))/float(a1+a2) # get smallest allele freq
        headerstring = '%d[%s/%s]' % (sk,sitealleles[0],sitealleles[1])
        rafs = '%02d_' % int(100.0*raf)
        rafsort[rafs+str(sk)] = hapindex
        if sk in commonsites:
            rafsort10[rafs+str(sk)] = hapindex
        hapindex += 1 # this becomes the index for resorting haplotypes
        loci[sk] = headerstring
        if len(headerstring) > locilen:
            locilen = len(headerstring) # find longest locus
    for sk in sitekeys:
        if len(loci[sk]) < locilen:
            extra = locilen - len(loci[sk]) 
            loci[sk] = extra*' ' + loci[sk]
    sidk = pbdata.keys()
    sidk.sort()
    # sort in either id or flag order
    flagsort = {}
    for sid in sidk: # normal genogram - id order
        flagsort[sid] = sid
    fsk = flagsort.keys()
    fsk.sort()
    gcaprint(genename,'id','Sorted by subject ID',loci,pbdata,fsk,flagsort,sitekeys,locilen,{},allpops,minraf)
    haps = iipgalib.haplist() # pretend genotypes are haplotypes (!)
    haps10 = iipgalib.haplist()
    sidhaps = {}
    sidhaps10 = {}
    uhaps = {}
    u10haps = {}
    flagsort = {}
    csnp = {}
    for sid in sidk: # create a resorted version
        myhap=''
        myhap10 = '' # 10pc snp haps for sorting
        for sk in sitekeys:
            try:
                a1,a2,pop,flag = pbdata[sid][sk]
                myhap = myhap + str(flag)
                if sk in commonsites:
                    myhap10 = myhap10 + str(flag)
            except:
                myhap = myhap + '0'
                if sk in commonsites:
                    myhap10 = myhap10 + '0'
        pop = sid[0]
        if not pop in uhaps.keys():
            uhaps[pop] = {}
            u10haps[pop] = {}
        sidhaps[sid] = myhap # stow for later key generation
        sidhaps10[sid] = myhap10
        if not u10haps[pop].has_key(myhap10):
            u10haps[pop][myhap10] = myhap10
        if not uhaps[pop].has_key(myhap):
            uhaps[pop][myhap] = myhap
    rk = rafsort10.keys() # these are raf percentages
    rkr = rafsort10.keys()
    rk.sort()
    rkr.sort()
    rk.reverse()
    rafsortlist = []
    rrafsortlist = []
    for rafkey in rk:
            rafsortlist.append(rafsort[rafkey]) # hap indices now in raf order for reordering
    testsorts = []
    r = range(len(rafsort))
    for i in range(maxrandomtests):
        random.shuffle(r)
        testsorts.append(copy.copy(r))
    for pop in uhaps.keys():
        npop = 0
        freqhaps = uhaps[pop] # get haps seen more than once in count order
        critsnp = findsmallestkey(freqhaps.values(),rafsortlist,testsorts,pop,errlog)
        for sid in sidk:
            if sid[0] == pop:
                npop+=1
                myhap = sidhaps[sid]
                mycritkey = ''
                for locus in critsnp: # these are snp numbers in order
                    mycritkey = mycritkey + myhap[locus]
                flagsort[pop+mycritkey+string.replace(sid,'0',' ')] = sid # need to make ALL keys unique - bug took a while to find!
        csnp[tranhead[pop]] = critsnp # for flagging genogram
        print 'pop=%s, n=%d, ncrit = %d, %s' % (pop,npop,len(critsnp),str(critsnp))
    fsk = flagsort.keys()
    fsk.sort()
    fsk.reverse()
    fsk.sort(genocomp)
    gcaprint(genename,'gt','Sorted by Genotype',loci,pbdata,fsk,flagsort,sitekeys,locilen,csnp,allpops,minraf)


def gcaprint(genename='',oftype='',title='title',loci = [], pbdata = {},fsk=[],flagsort={},\
             sitekeys = [],locilen=0, pcritsnp={},allpops={},minraf=0.0):
    '''
    Visual genotype with piddle/PIL
    '''
    numgroups = len(allpops.keys())
    numcols = len(loci)
    plotheight = len(fsk) / numgroups # mean 
    plotwidth = max(600,10*numcols)
    if numcols > 40:
        plotwidth += min(800,(numcols-40)*10) # set max plotsize to 1000pixels wide.
    vg = iipgalib.VisualGenotypePlot(plotwidth,plotheight,sitekeys,genename,numgroups,loci,pcritsnp,minraf)    
    cpop = fsk[0][0] # first char of key is pop
    thisdata=[]
    for k in fsk:
        thisid = flagsort[k]
        thispop = thisid[0]
        if thispop <> cpop:
            vg.newdata(thisdata,tranhead[cpop])
            thisdata=[]
            cpop = thispop
        thisrow = []
        thisrow.append(thisid)
        for site in sitekeys:
            try:
                a1,a2,pop,flag = pbdata[thisid][site]
                thisrow.append(flag)
            except:
                thisrow.append(0) # missing
        thisdata.append(thisrow)
    vg.newdata(thisdata,tranhead[cpop]) # for last group        
    jpgname = genename + '_' + genogram + oftype + '.jpg'
    vg.writeimage(jpgname,'')
 





def cleanpb(fl=[]):
    '''
    '''
    indel = ['+','-']
    cleanfl = []
    badloci = []
    for l in fl: # for each line
        opbl,osid,oa1,oa2 = string.split(l)
        if (len(string.strip(oa1))<> 1) or (len(string.strip(oa2)) <> 1) \
          or (oa1 in indel) or (oa2 in indel) or (opbl in badloci):
            if not opbl in badloci:
                badloci.append(opbl) # in case - bad alleles
                print 'indel at locus %s' % opbl
    for l in fl:
        opbl,osid,oa1,oa2 = string.split(l)
        if not opbl in badloci:
            cleanfl.append(l) 
    return cleanfl

def checkrelpb(gene=''):
    '''
    read both rel and original pb file
    make a translation table and check all snp
    '''
    reltopb = {}
    rpb = gene + '.' + relpbfileext
    pb = gene + '.' + pbfileext
    rpbf = open(rpb,'r')
    rpbfl = rpbf.readlines()
    rpbf.close()
    pbf = open(pb,'r')
    pbfl = pbf.readlines()
    pbf.close()
    rpbfl = cleanpb(rpbfl)
    pbfl = cleanpb(pbfl)
    if len(rpbfl) == 0:
        print 'Empty relpb file. Cannot proceed'
        return reltopb
    if len(pbfl) <> len(rpbfl):
        print 'Houston, we have a problem: Original pb has %d lines, relpb has %d' % (len(pbfl),len(rpbfl))
        return reltopb
    for i in range(len(pbfl)): # for each line
        opbl,osid,oa1,oa2 = string.split(pbfl[i])
        rpbl,rsid,ra1,ra2 = string.split(rpbfl[i])
        if osid==rsid and oa1==ra1 and oa2==ra2:
            irpbl = int(rpbl)
            iopbl = int(opbl)
            if not (reltopb.has_key(irpbl)):
                reltopb[irpbl] = iopbl
    return reltopb



def pbvg(pbfilename,gene,minraf,errlog):
    '''
    creates a visual genotype for this prettybase file
    '''
    groups = ['A','D','E','H']
    format='html'
    fbase = os.path.basename(pbfilename)    
    gene = string.upper(gene)
    errlog.append('Parsing %s' % pbfilename)
    sites,pbdata,allpops,errlog = iipgalib.parseprettybase(pbfilename,errlog,groups)
    if not pbfilename or len(sites) <= 1 :
        pbfilename = string.replace(pbfilename,'relpb','prettybase')
        sites,pbdata,errlog = parseprettybase(pbfilename,groups,{},{},errlog)
        if len(sites) <= 1:
            rs = 'Unable to open/parse a prettybase or relpb file at %s' % pbfilename
            print (rs)
            errlog.append(rs)
            return errlog
    sites,errlog = iipgalib.padgenotypes(sites,allpops,errlog) 
    sites,errlog = iipgalib.calchz(sites,allpops,errlog)
    sites,pbdata,errlog = iipgalib.calccommonalleles(sites,pbdata,allpops,errlog)
    commonsites = iipgalib.selminraf(sites,pbdata,minraf)
    graphcommonalleles(gene,sites,pbdata,commonsites,allpops,minraf,errlog)
    return errlog




if __name__ == '__main__':
    global  _v_indels, _v_allpops, minraf,  _v_reltopb, minraf
    minraf = 0.1
    errlog=[]
    _v_reltopb = {} # for translation checking
    _v_indels = {}
    _v_allpops = {} # keeps every pop group encountered just in case
    errlog.append('Error Log for %s, started at %s' % (myname, util.timenow()))
    pyname = sys.argv[0]
    myname = string.split(pyname,'.py')[0]
    if len(sys.argv) > 1:
        onegene = sys.argv[1]
        try:
            minraf = float(sys.argv[2])
            print 'minraf = %5.4f' % minraf
        except:
            minraf = 0.1
    else:
        onegene = ''
    cwd = os.getcwd()
    mydlist = os.listdir(cwd)
    fname = '%s.log' % myname
    fname = os.path.join(cwd,fname)
    elogf = open(fname,'w')
    print 'opened %s' % fname
    done = []
    for pathname in mydlist:
      if (onegene == '') or (onegene == pathname):
        fpath = os.path.join(cwd,pathname)
        mode = os.stat(fpath)[stat.ST_MODE]
        if stat.S_ISDIR(mode):
                os.chdir(fpath) # so files appear here
                # It's a directory, recurse into it
                flist = glob.glob('*.relpb.txt') # might be wildcard
                for arpf in flist:
                    if not arpf in done:
                        done.append(arpf)
                        _v_reltopb = {} # for translation checking
                        _v_indels = {}
                        _v_allpops = {} # keeps every pop group encountered just in case
                        print 'trying %s' % arpf
                        errlog = pbvg(arpf,pathname,minraf,errlog)
                os.chdir(cwd) # return to top
    errlog.append('Error Log for %s, ended at %s' % (myname, util.timenow()))
    elogf.write(string.join(errlog,'\n'))
    print string.join(errlog,'\n')
    elogf.close()





"""
$Log: pbvisualgeno.py,v $
Revision 1.1.1.1  2004/03/24 21:44:46  rerla
Import of ross stuff

Revision 1.10  2002/11/05 23:21:14  rejpz
Fixed any non-portable (using /ilocal) shebangs; Chucked mycomment variable and moved content into Log keyword


March 28 - moved classes and reuseable functions out to iipgalib

March 21 - added alternative prettybase.txt use if relpb.txt not available

Lots of testing for better orderings. The "optimal" minimal set of critical snp often produces
what appear to be less helpful plots. Generally only small gains over RAF order.
Best is probably to display the entire string and also a provide 10% genogram separately?

rml march 10 2002:
fixed some bugs to do with handling of missing values. Now ignores these in critical snp detection and in
genotype string sorting - sort compare function must deal with strings! Haptree recast as genotree to ensure that
the specific missing genotype flag was handled correctly.
added minraf and appropriate deletion of sites

rml started early march 2002:

Makes visual genotype images using PIL from pb files
Designed for use as a zope external method


Derived from arlequinldplot march 4 2002

"""

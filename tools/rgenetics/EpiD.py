"""
feb 28
genesets in regions seem to come up roses with null (shuffled) data and the z scores are too symmetrical to be believed.
Added a distance cutoff 50k and fisher's exact test and use that for the fdr


feb 27
Major makeover - 7000 gene sets in <8 mins cf > 90mins for previous version running on omics

R is now not required - dependencies are python with scipy/numpy and closestBed binary from Aaron Quinlan's BEDtools project

Changes include:

1) Uses scipy.stats ranksums (the scipy.stats.wilcoxon implementation insists one equal sample sizes.
Note that this does not handle ties properly or do a continuity correction but since distances
are down to a single basepair resolution this should not be a major problem - would be possible to
also do the scipy.stats.mannwhitneyu test which does these things but may not be valid.

2) Remove the test gene distances from the comparison set of all gene distances to avoid bias to the null

3) Reports FDR accept/reject the null and the FDR cutoff. Uses a method for correlated p values from
Benjamini-Liu Behav.brain.res 125:2001;279-284 - this is conservative but robust for correlated tests - since a gene distance
can appear in multiple tests, the tests are not independent.

4) Reports counts and medians of distances in and out for each test - the ranksums test is robust for as long as there are (eg) 20 or more
distances in each group.

"""

import tempfile, os, sys, subprocess
from scipy.stats import ranksums,fisher_exact # could perhaps use mannwhitneyu
from numpy import median 
COMMENT = '#'
ourALL = '000ALL'

def benjliu(pvec=[],Q=0.05):
     """method of Benjamini and Liu for correlated tests - see Behav.brain.res 125:2001;279-284
        takes a vector of sorted p values; start at smallest p, reject while p <= q*m/(m-k)**2
        Benjamini Y, Liu W. A distribution-free multiple test procedure that controls the false discovery rate. Tel Aviv. RP-SOR-99-3:
        Department of Statistics and O.R., Tel Aviv University, 1999.
        http://www.math.tau.ac.il/~ybenja/BL2.pdf
        note that the paper has min(1.0,Q*m/((m-i+1)**2)) which makes no sense to me...surely Q rather than 1.0 is the smallest possible cutoff
        in any FDR correction. Also our i is offset by 1 more

     """
     m = len(pvec)
     cutoffs = []
     decisions = []
     for i in range(m):
          cutoff = min(Q,Q*m/((m-i+2)**2)) # our i ranges 0 to m-1
          cutoffs.append(cutoff)
          if pvec[i] < cutoff:
               decisions.append('reject')
          else:
               decisions.append('accept')
     return cutoffs,decisions

def fixGene(gin = []):
    """ kludge to take care of aliases expressed as gene1 /// gene2
        sometimes gene1 // or gene1 /// gene2 // and other unpredictable variations so attempt to be robust
    """
    glist = []
    for g in gin:
        g = g.strip()
        if len(g) > 0:
            if g.find('/') <> -1:
                gs = g.split('/') # lots of empty strings - may be 2 or 3 of these...
                if len(gs) > 1:
                    gs = [x.strip() for x in gs if len(x.strip()) > 1] # strip spaces
                    glist += gs
            else:
                glist.append(g)
    return glist


def getGS(genesetFilename=None,distdict={}):
    """
    make a dict with genesets as keys and their gene lists as the value
    ignore any genes with no corresponding distance measure since they did not match a peak
    add an 000ALL gene set containing every gene
    """
    allgenes = []
    allgs = {}
    gs = open(genesetFname,'r').readlines()
    gs = [x.strip() for x in gs]
    gsl = [x.split('\t') for x in gs]
    bad = [x for x in gsl if len(x) < 3]
    gsdict = {}
    if len(bad) > 0:
        print >> sys.stdout,'##bad %s' % bad
        gsl = [x for x in gsl if len(x) >= 3]
    for irow, srow in enumerate(gsl):
        gset = srow[0] or 'none'
        if allgs.get(gset,None):
            print >> sys.stdout, 'Input problem - geneset %s appears again at row %d as %s' % (gset,irow)
            continue
        gsetanno = srow[1] or 'none'
        gsnames = [x.strip() for x in srow[2:] if len(x.strip()) > 0]
        if len(gsnames) == 0:
            print '## bad srow = ',srow
        else:
            glist = fixGene(gsnames) # split /// genes
            glist = [x for x in glist if distdict.get(x,None)]
            mia = [x for x in glist if distdict.get(x,None) == None] # check that no genes are missing distances
            if len(mia) > 0:
                print >> sys.stdout, '# odd. %s missing from distance dict' % str(mia)
            if len(glist) > 0: # could be none with a distance...
                allgenes += glist
                gsdict.setdefault(gset,glist) # will fail if already seen
    ugenes = set(allgenes) # unique
    list(ugenes).sort()
    gsdict[ourALL] = ugenes # add all geneset
    return gsdict



def fixDistances(annoFname=None,regionFname=None):
    """ use closestBed to find distance to nearest feature of interest (eg TSS)
        supplied in annoFname. Massage output into the columns we need
        March 2 2011: if we want a measure of how many detected features were involved, we need a unique feature name
        If we get a 3 col bed (legal but unhelpful) from (eg) an intersect, we need to add one
    """
    tbed = open(regionFname,'r').readlines()
    tbeds = [x.strip().split('\t') for x in tbed if len(x.strip() > 0)]
    lens = [len(x) for x in tbeds]
    if min(lens) < 4 and max(lens) < 4: # ah. Maybe no feature name
        tbed = ['%s\tregion%d' % (x,i) for i,x in enumerate(tbeds)]
        f,namedFname = tempfile.mkstemp(prefix='epid_nameadded',suffix='.bed')
        tf = open(namedFname,'w')
        tf.write('\n'.join(tbed))
        tf.write('\n')
        tf.close()
        useregionFname = namedFname 
    else:
        useregionFname = regionFname   
    f,tdistFname = tempfile.mkstemp(prefix='epid_distances')
    # we want gene distance for closest so bed columns 4 (name) and col8 - col2
    cl = """closestBed  -tfirst -a  %s -b %s > %s""" % (annoFname,useregionFname,tdistFname)
    x = subprocess.Popen(cl,shell=True)
    ret = x.wait()
    tdist = open(tdistFname,'r').readlines()
    tdists = [x.split('\t') for x in tdist]
    lens = [len(x) for x in tdists]
    os.unlink(tdistFname)
    distvals = [abs(int(x[7]) - int(x[1])) for x in tdists]
    distkeys = [x[3] for i,x in enumerate(tdists)]
    distdict = dict(zip(distkeys,distvals)) # for fast lookup
    if min(lens) < 9: # ah. still no feature name - wtf?
        featlist = None
        featdict = None
    else:
        featlist = [x[9] for x in tdists]        
        featdict = dict(zip(distkeys,featlist)) # which feature for which gene
    return distdict,featdict


def runEpiD(genesetFname=None, annoFname=None, regionFname=None, outFname=None, fdr=0.05, maxDist=50000):
    """
    """
    # make distFname R input
    distFname = 'distances.txt'
    msigFname = 'geneSets.txt'
    distdict,featdict = fixDistances(annoFname,regionFname)
    gsdict = getGS(genesetFname,distdict)
    allgenes = gsdict[ourALL] # where we stowed unique gene names
    res = []
    pvec = []
    for gset in gsdict.keys():
        if gset == ourALL:
            continue
        gsl = gsdict[gset]
        gsldict = dict(zip(gsl,gsl)) # to speed search for all other gene distances
        allother = [x for x in allgenes if gsldict.get(x,None) == None] # distances NOT included in gsl
        indist = [distdict[x] for x in gsl ]
        outdist = [distdict[x] for x in allother] 
        maxDistnin = len([x for x in indist if x <= maxDist ]) # number close
        maxDistnout = len([x for x in outdist if x <= maxDist ]) # number close
        z,p = ranksums(indist,outdist)
        p = p/2.0 # one sided
        if z > 0.0: # reverse p for one sided test
            p = 1.0 - p # 
        nin = len(indist)
        nout = len(outdist)
        medin = median(indist)
        medout = median(outdist)
        prioror,fisherp = fisher_exact([[nout,maxDistnout],[nin,maxDistnin]])
        if featdict:
            outfeatn = len(set([featdict.get(x) for x in allother])) # features for compliment
            infeatn = len(set([featdict.get(x) for x in gsl])) # features for gene set
        else:
            outfeatn = -9
            infeatn = -9
        row = [gset,fisherp,z,nin,nout,medin,medout,maxDistnin,maxDistnout,prioror,p,infeatn,outfeatn]
        res.append(row) 
    pvec = [x[1] for x in res]
    cutoffs,decisions = benjliu(pvec,fdr)
    res = [x + [cutoffs[i],decisions[i]] for i,x in enumerate(res)] # add fdr to end
    res = [(x[1],x) for x in res] # decorate
    res.sort() # on p value
    res = [x[1] for x in res] # undecorate
    head = ['#geneset','fisherexactp','z','nin','nout','medin','medout','inDistin','inDistout','priorOR','ranksump','indepmarkersin','indepmarkersout','blcutoff','fisherfdrdecision']
    return res,head


if __name__ == "__main__":
    assert len(sys.argv) == 5, "Usage EpiD.py <gene set file.gmt> <annotation file.bed> <regions file .bed> <out file.txt>"
    fdr = 0.05
    myName,genesetFname, annoFname, regionFname, outFname = sys.argv[:5]
    for fname in [genesetFname, annoFname, regionFname]:
        assert os.path.isfile(fname),'## Error: %s Cannot open input path %s' % (myName,fname)
    res,head = runEpiD(genesetFname, annoFname, regionFname, outFname)
    res = ['%s\t%g\t%f\t%d\t%d\t%f\t%f\t%d\t%d\t%g\t%g\t%d\t%d\t%g\t%s' % tuple(x) for x in res]
    outf = open(outFname,'w')
    outf.write('\t'.join(head))
    outf.write('\n')
    outf.write('\n'.join(res))
    outf.write('\n')
    outf.close()
    


# modified may 2011 to name components (map/ped) as RgeneticsData to align with default base_name
# otherwise downstream tools fail
# modified march  2011 to remove post execution hook  
# pedigree data faker
# specifically designed for scalability testing of
# Shaun Purcel's PLINK package
# derived from John Ziniti's original suggestion
# allele frequency spectrum and random mating added
# ross lazarus me fecit january 13 2007
# copyright ross lazarus 2007
# without psyco
# generates about 10k snp genotypes in 2k subjects (666 trios) per minute or so.
# so 500k (a billion genotypes), at about 4 trios/min will a couple of hours to generate
# psyco makes it literally twice as quick!!
# all rights reserved except as granted under the terms of the LGPL
# see http://www.gnu.org/licenses/lgpl.html 
# for a copy of the license you receive with this software
# and for your rights and obligations
# especially if you wish to modify or redistribute this code
# january 19 added random missingness inducer
# currently about 15M genos/minute without psyco, 30M/minute with
# so a billion genos should take about 40 minutes with psyco or 80 without...
# added mendel error generator jan 23 rml


import random,sys,time,os,string

from optparse import OptionParser

defbasename="RgeneticsData"    
width = 500000
ALLELES = ['1','2','3','4']
prog = os.path.split(sys.argv[0])[-1]
debug = 0

"""Natural-order sorting, supporting embedded numbers.
# found at http://lists.canonical.org/pipermail/kragen-hacks/2005-October/000419.html
note test code there removed to conserve brain space
foo9bar2 < foo10bar2 < foo10bar10

"""
import random, re, sys

def natsort_key(item): 
    chunks = re.split('(\d+(?:\.\d+)?)', item)
    for ii in range(len(chunks)):
        if chunks[ii] and chunks[ii][0] in '0123456789':
            if '.' in chunks[ii]: numtype = float
            else: numtype = int
            # wrap in tuple with '0' to explicitly specify numbers come first
            chunks[ii] = (0, numtype(chunks[ii]))
        else:
            chunks[ii] = (1, chunks[ii])
    return (chunks, item)

def natsort(seq):
    "Sort a sequence of text strings in a reasonable order."
    alist = [item for item in seq]
    alist.sort(key=natsort_key)
    return alist


def makeUniformMAFdist(low=0.02, high=0.5):
    """Fake a non-uniform maf distribution to make the data
    more interesting. Provide uniform 0.02-0.5 distribution"""
    MAFdistribution = []
    for i in xrange(int(100*low),int(100*high)+1):
       freq = i/100.0 # uniform
       MAFdistribution.append(freq)
    return MAFdistribution

def makeTriangularMAFdist(low=0.02, high=0.5, beta=5):
    """Fake a non-uniform maf distribution to make the data
    more interesting - more rare alleles """
    MAFdistribution = []
    for i in xrange(int(100*low),int(100*high)+1):
       freq = (51 - i)/100.0 # large numbers of small allele freqs
       for j in range(beta*i): # or i*i for crude exponential distribution 
            MAFdistribution.append(freq)
    return MAFdistribution

def makeFbathead(rslist=[], chromlist=[], poslist=[], width=100000):
    """header row
    """
    res = ['%s_%s_%s' % (chromlist[x], poslist[x], rslist[x]) for x in range(len(rslist))]
    return ' '.join(res)

def makeMap( width=500000, MAFdistribution=[], useGP=False):
    """make snp allele and frequency tables for consistent generation"""
    usegp = 1
    snpdb = 'snp126'
    hgdb = 'hg18'
    alleles = []
    freqs = []
    rslist = []
    chromlist = []
    poslist = []
    for snp in range(width):
        random.shuffle(ALLELES)
        alleles.append(ALLELES[0:2]) # need two DIFFERENT alleles!
        freqs.append(random.choice(MAFdistribution)) # more rare alleles
    if useGP:
        try:
            import MySQLdb
            genome = MySQLdb.Connect('localhost', 'hg18', 'G3gn0m3')
            curs = genome.cursor() # use default cursor
        except:
            if debug:
                print 'cannot connect to local copy of golden path'
            usegp = 0
    if usegp and useGP: # urrrgghh getting snps into chrom offset order is complicated....
        curs.execute('use %s' % hgdb)
        print 'Collecting %d real rs numbers - this may take a while' % width
        # get a random draw of enough reasonable (hapmap) snps with frequency data
        s = '''select distinct chrom,chromEnd, name from %s where avHet > 0 and chrom not like '%%random'
        group by name order by rand() limit %d''' % (snpdb,width)
        curs.execute(s)
        reslist = curs.fetchall()
        reslist = ['%s\t%09d\t%s' % (x[3:],y,z) for x,y,z in reslist] # get rid of chr
        reslist = natsort(reslist)
        for s in reslist:
            chrom,pos,rs = s.split('\t')
            rslist.append(rs)
            chromlist.append(chrom)
            poslist.append(pos)
    else:
        chrom = '1'
        for snp in range(width):
            pos = '%d' % (1000*snp)
            rs = 'rs00%d' % snp
            rslist.append(rs)
            chromlist.append(chrom)
            poslist.append(pos)
    return alleles,freqs, rslist, chromlist, poslist

def writeMap(fprefix = '', fpath='./', rslist=[], chromlist=[], poslist=[], width = 500000):
    """make a faked plink compatible map file - fbat files
    have the map written as a header line"""
    outf = '%s.map'% (fprefix)
    outf = os.path.join(fpath,outf)
    amap = open(outf, 'w')
    res = ['%s\t%s\t0\t%s' % (chromlist[x],rslist[x],poslist[x]) for x in range(len(rslist))]
    res.append('')
    amap.write('\n'.join(res))
    amap.close()

def makeMissing(genos=[], missrate = 0.03, missval = '0'):
    """impose some random missingness"""
    nsnps = len(genos)
    for snp in range(nsnps): # ignore first 6 columns
        if random.random() <= missrate:
            genos[snp] = '%s %s' % (missval,missval)
    return genos

def makeTriomissing(genos=[], missrate = 0.03, missval = '0'):
    """impose some random missingness on a trio - moth eaten like real data"""
    for person in (0,1):
        nsnps = len(genos[person])
        for snp in range(nsnps):
            for person in [0,1,2]:
                if random.random() <= missrate:
                    genos[person][snp] = '%s %s' % (missval,missval)
    return genos


def makeTriomendel(p1g=(0,0),p2g=(0,0), kiddip = (0,0)):
    """impose some random mendels on a trio
    there are 8 of the 9 mating types we can simulate reasonable errors for
    Note, since random mating dual het parents can produce any genotype we can't generate an interesting
    error for them, so the overall mendel rate will be lower than mendrate, depending on
    allele frequency..."""
    if p1g[0] <> p1g[1] and p2g[0] <> p2g[1]: # both parents het
            return kiddip # cannot simulate a mendel error - anything is legal!
    elif (p1g[0] <> p1g[1]): # p1 is het parent so p2 must be hom
        if p2g[0] == 0: # - make child p2 opposite hom for error
            kiddip = (1,1)
        else:
            kiddip = (0,0)
    elif (p2g[0] <> p2g[1]): # p2 is het parent so p1 must be hom
        if p1g[0] == 0: # - make child p1 opposite hom for error
            kiddip = (1,1)
        else:
            kiddip = (0,0)
    elif (p1g[0] == p1g[1]): # p1 is hom parent and if we get here p2 must also be hom
        if p1g[0] == p2g[0]: # both parents are same hom - make child either het or opposite hom for error
            if random.random() <= 0.5:
                kiddip = (0,1)
            else:
                if p1g[0] == 0:
                    kiddip = (1,1)
                else:
                    kiddip = (0,0)
        else: # parents are opposite hom - return any hom as an error
            if random.random() <= 0.5:
                kiddip = (0,0)
            else:
                kiddip = (1,1)
    return kiddip
            
            


def makeFam(width=100, freqs={}, alleles={}, trio=1, missrate=0.03, missval='0', mendrate=0.0):
    """this family is a simple trio, constructed by random mating two random genotypes
    TODO: why not generate from chromosomes - eg hapmap
    set each haplotype locus according to the conditional
    probability implied by the surrounding loci - eg use both neighboring pairs, triplets
    and quads as observed in hapmap ceu"""
    dadped = '%d 1 0 0 1 1 %s'
    mumped = '%d 2 0 0 2 1 %s' # a mother is a mum where I come from :)
    kidped = '%d 3 1 2 %d %d %s'
    family = [] # result accumulator
    sex = random.choice((1,2)) # for the kid
    affected = random.choice((1,2))
    genos = [[],[],[]] # dad, mum, kid - 0/1 for common,rare initially, then xform to alleles
    # parent1...kidn lists of 0/1 for common,rare initially, then xformed to alleles
    for snp in xrange(width):
        f = freqs[snp]           
        for i in range(2): # do dad and mum
            p = random.random()
            a1 = a2 = 0
            if p <= f: # a rare allele
               a1 = 1
            p = random.random()
            if p <= f: # a rare allele
               a2 = 1
            if a1 > a2:
                a1,a2 = a2,a1 # so ordering consistent - 00,01,11
            dip = (a1,a2)
            genos[i].append(dip) # tuples of 0,1
        a1 = random.choice(genos[0][snp]) # dad gamete  
        a2 = random.choice(genos[1][snp]) # mum gamete
        if a1 > a2:
            a1,a2 = a2,a1 # so ordering consistent - 00,01,11
        kiddip = (a1,a2) # NSFW mating!
        genos[2].append(kiddip)
        if mendrate > 0:
            if random.random() <= mendrate:
                genos[2][snp] = makeTriomendel(genos[0][snp],genos[1][snp], kiddip)
        achoice = alleles[snp]
        for g in genos: # now convert to alleles using allele dict
          a1 = achoice[g[snp][0]] # get allele letter
          a2 = achoice[g[snp][1]]              
          g[snp] = '%s %s' % (a1,a2)
    if missrate > 0:
        genos = makeTriomissing(genos=genos,missrate=missrate, missval=missval)
    family.append(dadped % (trio,' '.join(genos[0]))) # create a row for each member of trio
    family.append(mumped % (trio,' '.join(genos[1])))
    family.append(kidped % (trio,sex,affected,' '.join(genos[2])))
    return family

def makePerson(width=100, aff=1, freqs={}, alleles={}, id=1, missrate = 0.03, missval='0'):
    """make an entire genotype vector for an independent subject"""
    sex = random.choice((1,2))
    if not aff:
        aff = random.choice((1,2))
    genos = [] #0/1 for common,rare initially, then xform to alleles
    family = []
    personped = '%d 1 0 0 %d %d %s'
    poly = (0,1)
    for snp in xrange(width):
        achoice = alleles[snp]
        f = freqs[snp]
        p = random.random()
        a1 = a2 = 0
        if p <= f: # a rare allele
           a1 = 1
        p = random.random()
        if p <= f: # a rare allele
           a2 = 1
        if a1 > a2:
            a1,a2 = a2,a1 # so ordering consistent - 00,01,11
        a1 = achoice[a1] # get allele letter
        a2 = achoice[a2]
        g = '%s %s' % (a1,a2)
        genos.append(g)
    if missrate > 0.0:
        genos = makeMissing(genos=genos,missrate=missrate, missval=missval)
    family.append(personped % (id,sex,aff,' '.join(genos)))
    return family

def makeHapmap(fprefix= 'fakebigped',width=100, aff=[], freqs={},
               alleles={}, nsubj = 2000, trios = True, mendrate=0.03, missrate = 0.03, missval='0'):
    """ fake a hapmap file and a pedigree file for eg haploview
    this is arranged as the transpose of a ped file - cols are subjects, rows are markers
    so we need to generate differently since we can't do the transpose in ram reliably for
    a few billion genotypes...
    """
    outheadprefix = 'rs# alleles chrom pos strand assembly# center protLSID assayLSID panelLSID QCcode %s'
    cfake5 = ["illumina","urn:LSID:illumina.hapmap.org:Protocol:Golden_Gate_1.0.0:1", 
"urn:LSID:illumina.hapmap.org:Assay:27741:1","urn:lsid:dcc.hapmap.org:Panel:CEPH-30-trios:1","QC+"]
    yfake5 = ["illumina","urn:LSID:illumina.hapmap.org:Protocol:Golden_Gate_1.0.0:1", 
"urn:LSID:illumina.hapmap.org:Assay:27741:1","urn:LSID:dcc.hapmap.org:Panel:Yoruba-30-trios:1","QC+"]
    sampids = ids
    if trios:
        ts = '%d trios' % int(nsubj/3.)
    else:
        ts = '%d unrelated subjects' % nsubj
    res = ['#%s fake hapmap file %d snps and %s, faked by %s' % (timenow(), width, ts, prog),]
    res.append('# ross lazarus me fecit')
    res.append(outheadprefix % ' '.join(sampids)) # make a header compatible with hapmap extracts
    outf = open('%s.hmap' % (fprefix), 'w')
    started = time.time()
    if trios:
        ntrios = int(nsubj/3.)
        for n in ntrios: # each is a dict
            row = copy.copy(cfake5) # get first fields
            row = map(str,row)
            if race == "YRI":
                row += yfake5
            elif race == 'CEU':
                row += cfake5
            else:
                row += ['NA' for x in range(5)] # 5 dummy fields = center protLSID assayLSID panelLSID QCcode
            row += [''.join(sorted(line[x])) for x in sampids] # the genotypes in header (sorted) sample id order
            res.append(' '.join(row))
    res.append('')
    outfname = '%s_%s_%s_%dkb.geno' % (gene,probeid,race,2*flank/1000)
    f = file(outfname,'w')
    f.write('\n'.join(res))
    f.close()
    print '### %s: Wrote %d lines to %s' % (timenow(), len(res),outfname)
     

def makePed(fprefix= 'fakebigped', fpath='./',
            width=500000, nsubj=2000, MAFdistribution=[],alleles={},
            freqs={}, fbatstyle=True, mendrate = 0.0, missrate = 0.03, missval='0',fbathead=''):
    """fake trios with mendel consistent random mating genotypes in offspring
    with consistent alleles and MAFs for the sample"""
    res = []
    if fbatstyle: # add a header row with the marker names
        res.append(fbathead) # header row for fbat
    outfname = '%s.ped'% (fprefix)
    outfname = os.path.join(fpath,outfname)
    outf = open(outfname,'w')
    ntrios = int(nsubj/3.)
    outf = open(outfile, 'w')
    started = time.time()
    for trio in xrange(ntrios):
        family = makeFam(width=width, freqs=freqs, alleles=alleles, trio=trio,
                         missrate = missrate, mendrate=mendrate, missval=missval)
        res += family
        if (trio + 1) % 10 == 0: # write out to keep ram requirements reasonable
            if (trio + 1) % 50 == 0: # show progress
                dur = time.time() - started
                if dur == 0:
                    dur = 1.0
                print 'Trio: %d, %4.1f genos/sec at %6.1f sec' % (trio + 1, width*trio*3/dur, dur)
            outf.write('\n'.join(res))
            outf.write('\n')
            res = []
    if len(res) > 0: # some left
        outf.write('\n'.join(res))
    outf.write('\n')
    outf.close()
    if debug:
        print '##makeped : %6.1f seconds total runtime' % (time.time() - started)

def makeIndep(fprefix = 'fakebigped', fpath='./',
              width=500000, Nunaff=1000, Naff=1000, MAFdistribution=[],
              alleles={}, freqs={}, fbatstyle=True, missrate = 0.03, missval='0',fbathead=''):
    """fake a random sample from a random mating sample
    with consistent alleles and MAFs"""
    res = []
    Ntot = Nunaff + Naff
    status = [1,]*Nunaff
    status += [2,]*Nunaff
    outf = '%s.ped' % (fprefix)
    outf = os.path.join(fpath,outf)
    outf = open(outf, 'w')
    started = time.time()
    #sample = personMaker(width=width, affs=status, freqs=freqs, alleles=alleles, Ntomake=Ntot)
    if fbatstyle: # add a header row with the marker names
        res.append(fbathead) # header row for fbat
    for id in xrange(Ntot):
        if id < Nunaff:
            aff = 1
        else:
            aff = 2
        family = makePerson(width=width, aff=aff, freqs=freqs, alleles=alleles, id=id+1)
        res += family
        if (id % 50 == 0): # write out to keep ram requirements reasonable
            if (id % 200 == 0): # show progress
                dur = time.time() - started
                if dur == 0:
                    dur = 1.0
                print 'Id: %d, %4.1f genos/sec at %6.1f sec' % (id, width*id/dur, dur)
            outf.write('\n'.join(res))
            outf.write('\n')
            res = []
    if len(res) > 0: # some left
        outf.write('\n'.join(res))
    outf.write('\n')
    outf.close()
    print '## makeindep: %6.1f seconds total runtime' % (time.time() - started)

u = """
Generate either trios or independent subjects with a prespecified
number of random alleles and a uniform or triangular MAF distribution for
stress testing. No LD is simulated - alleles are random. Offspring for
trios are generated by random mating the random parental alleles so there are
no Mendelian errors unless the -M option is used. Mendelian errors are generated
randomly according to the possible errors given the parental mating type although
this is fresh code and not guaranteed to work quite right yet - comments welcomed

Enquiries to ross.lazarus@gmail.com

eg to generate 700 trios with 500k snps, use:
fakebigped.py -n 2100 -s 500000
or to generate 500 independent cases and 500 controls with 100k snps and 0.02 missingness (MCAR), use:
fakebigped.py -c 500 -n 1000 -s 100000 -m 0.02

fakebigped.py -o myfake -m 0.05 -s 100000 -n 2000
will make fbat compatible myfake.ped with 100k markers in
666 trios (total close to 2000 subjects), a uniform MAF distribution and about 5% MCAR missing

fakebigped.py -o myfake -m 0.05 -s 100000 -n 2000 -M 0.05
will make fbat compatible myfake.ped with 100k markers in
666 trios (total close to 2000 subjects), a uniform MAF distribution,
about 5% Mendelian errors and about 5% MCAR missing


fakebigped.py  -o myfakecc -m 0.05 -s 100000 -n 2000 -c 1000 -l
will make plink compatible myfakecc.ped and myfakecc.map (that's what the -l option does),
with 100k markers in 1000 cases and 1000 controls (affection status 2 and 1 respectively),
a triangular MAF distribution (more rare alleles) and about 5% MCAR missing

You should see about 1/4 million genotypes/second so about an hour for a
500k snps in 2k subjects and about a 4GB ped file - these are BIG!!

"""

import sys, os, glob

galhtmlprefix = """<?xml version="1.0" encoding="utf-8" ?>
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


def doImport(outfile=None,outpath=None):
    """ import into one of the new html composite data types for Rgenetics
        Dan Blankenberg with mods by Ross Lazarus 
        October 2007
    """
    flist = glob.glob(os.path.join(outpath,'*'))
    outf = open(outfile,'w')
    outf.write(galhtmlprefix % prog)
    for i, data in enumerate( flist ):
        outf.write('<li><a href="%s">%s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1]))
    outf.write('<br><h3>This is simulated null genotype data generated by Rgenetics!</h3>')
    outf.write('%s called with command line:<br><pre>' % prog)
    outf.write(' '.join(sys.argv))
    outf.write('\n</pre>\n')
    outf.write("</div></body></html>")
    outf.close()



if __name__ == "__main__":
    """
    """
    parser = OptionParser(usage=u, version="%prog 0.01")
    a = parser.add_option
    a("-n","--nsubjects",type="int",dest="Ntot",
      help="nsubj: total number of subjects",default=2000)
    a("-t","--title",dest="title",
      help="title: file basename for outputs",default='fakeped')
    a("-c","--cases",type="int",dest="Naff",
      help="number of cases: independent subjects with status set to 2 (ie cases). If not set, NTOT/3 trios will be generated", default = 0)
    a("-s","--snps",dest="width",type="int",
      help="snps: total number of snps per subject", default=1000)
    a("-d","--distribution",dest="MAFdist",default="Uniform",
      help="MAF distribution - default is Uniform, can be Triangular")
    a("-o","--outf",dest="outf",
      help="Output file", default = 'fakeped')
    a("-p","--outpath",dest="outpath",
      help="Path for output files", default = './')
    a("-l","--pLink",dest="outstyle", default='L',
      help="Ped files as for Plink - no header, separate Map file - default is Plink style")
    a("-w","--loWmaf", type="float", dest="lowmaf", default=0.01, help="Lower limit for SNP MAF (minor allele freq)")
    a("-m","--missing",dest="missrate",type="float",
      help="missing: probability of missing MCAR - default 0.0", default=0.0)
    a("-v","--valmiss",dest="missval",
      help="missing character: Missing allele code - usually 0 or N - default 0", default="0")
    a("-M","--Mendelrate",dest="mendrate",type="float",
      help="Mendelian error rate: probability of a mendel error per trio, default=0.0", default=0.0)   
    a("-H","--noHGRS",dest="useHG",type="int",
      help="Use local copy of UCSC snp126 database to generate real rs numbers", default=True)
    (options,args) = parser.parse_args()
    low = options.lowmaf
    try:
        os.makedirs(options.outpath)
    except:
        pass
    if options.MAFdist.upper() == 'U':
        mafDist = makeUniformMAFdist(low=low, high=0.5)
    else:
        mafDist = makeTriangularMAFdist(low=low, high=0.5, beta=5)
    alleles,freqs, rslist, chromlist, poslist = makeMap(width=int(options.width),
                                        MAFdistribution=mafDist, useGP=False)
    fbathead = []
    s = string.whitespace+string.punctuation
    trantab = string.maketrans(s,'_'*len(s))
    title = string.translate(options.title,trantab)
    
    if options.outstyle == 'F':
        fbatstyle = True
        fbathead = makeFbathead(rslist=rslist, chromlist=chromlist, poslist=poslist, width=options.width)
    else:
        fbatstyle = False
        writeMap(fprefix=defbasename, rslist=rslist, fpath=options.outpath,
                 chromlist=chromlist, poslist=poslist, width=options.width)
    if options.Naff > 0: # make case control data
        makeIndep(fprefix = defbasename, fpath=options.outpath,
                  width=options.width, Nunaff=options.Ntot-options.Naff,
                  Naff=options.Naff, MAFdistribution=mafDist,alleles=alleles, freqs=freqs,
                  fbatstyle=fbatstyle, missrate=options.missrate, missval=options.missval,
                  fbathead=fbathead)
    else:
        makePed(fprefix=defbasename, fpath=options.fpath,
            width=options.width, MAFdistribution=mafDist, nsubj=options.Ntot,
            alleles=alleles, freqs=freqs, fbatstyle=fbatstyle, missrate=options.missrate,
            mendrate=options.mendrate, missval=options.missval,
                  fbathead=fbathead)
    doImport(outfile=options.outf,outpath=options.outpath)


        

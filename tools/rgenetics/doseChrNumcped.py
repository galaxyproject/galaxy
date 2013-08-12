#!env python
"""
Sept More pedigree changes
langech2007@gmail.com to Ross, Scott, Jessica, Supinda, Blanca
show details 11:33 AM (7 hours ago)
Yes that is correct


Sent via BlackBerry from T-Mobile
- Hide quoted text -

-----Original Message-----
From: Ross Lazarus <ross.lazarus@channing.harvard.edu>
Date: Sat, 10 Sep 2011 11:28:37
To: Christoph Lange<langech2007@gmail.com>
Cc: Scott Weiss<restw@channing.harvard.edu>; Jessica Su<jessica.a.su@gmail.com>; Supinda Bunyavanich<resbu@channing.harvard.edu>; Blanca 
Himes<rebeh@channing.harvard.edu>
Subject: Re: pbat error

Thanks for clarifying that requirement - presumably the parental IDs
must be non-existing subjects so can also be drawn from UID?

So, something like:

1. For all EVE cohorts:
   -for each subject
        -replace IID and FID and non-zero mother/father ids with
their 16bit CRC to generate number strings < 9 characters in length
        -record all converted family ids in a set - call these EID
        -pass all records through as input to step 3

2. Generate a list of (eg 10000) integers which are not in EID - call this UID

3. for each cohort:
    -for each family id:
        -pass all pedigree records with both mother id = 0 and father
id = 0 with genotypes through to the cped file without alteration
        -identify all sets of offspring sharing the same mother id or father id
        -if the set is of size 1:
            -pass the single offspring record through with genotypes
to the final cped file
        -else:
            -pass the first of these offspring pedigree records
through  without alteration with genotypes to the cped file
            -for all except the first of those sets of offspring:
                -replace mother/father IDs with IDs drawn from UID
and remove those IDs from UID
                -replace family ID with a new ID chosen from UID and
remove that ID from UID
                -pass the altered record through with genotypes to
the final cped file

# july 30 finally, someone reveals that pbat needs 9 or less digits for ids
# tried 16 bit crc but get clashes in EVERY cohort :(
# now just take the first 8 bytes of the crc32 - testeve shows that works without clashes 
# July 15 added crc32 to make all ids 32 bits for pbat - needs testing
# July 14 ross lazarus
# whoopsie - forgot to transform pedigree dict values as well as keys...
# June 2 ross lazarus
# changes to accommodate a pbat wart - alphas not permitted in IDs
# easiest to munge here at conversion I think since ids are only read in 2 places - the .fam file and the transposed dosage file
# Need to hack ids uniformly - rule is that a non-digit character 'c' is replaced by the string representation 
# of the integer returned by ord(c)
# We similarly also need to attack pheno file ids and get it right.
# /mnt/memefs/proj/EVE_GWAS/EVE_DISTRIBUTION/020111_EVE_genotype_files/ASTHMA_GWAS/pbat/06272011_EVE_phenoPC.phe
# use pheno as the parameter to run the hardcoded file names below through the id converter
# updated to take CL parameters
# started may 2010 for supinda and jessica by ross
# For the eve project - was a raw converter mach dosage to cped - fbat with dosage rather than 2 genotypes.
# updated june 29 to amalgamate across eve cohorts imputed dosage data 
# assumes ALL chrX files in the directory are from cohorts to be joined
# make an fbat file of each dosage file
# subject ids are in first row
# subsequent rows have rs a1 a2 then dosages for each subject
SNP A1 A2 500003 20100003 500003 20200003 500003 20300003 500004 20100004 500004 20100005 500004 20200004 500004 20300004 500008 20100008 
500010 20100010 500010 
20200010 500$
rs11089130 C G 0.556 0.652 0.591 0.700 0.684 0.832 0.614 0.655 0.576 0.582 0.588 0.569 0.604 0.731 0.579 0.640 0.700 0.631 0.607 0.588 0.607 
0.684 0.677 0.677 0.745 
0.636 0.$
rs915675 A C 0.325 0.319 0.389 0.408 0.387 0.362 0.420 0.549 0.470 0.434 0.568 0.384 0.338 0.439 0.586 0.487 0.423 0.464 0.493 0.456 0.462 
0.348 0.455 0.520 0.326 
0.450 0.53$
rs915677 A G 0.103 0.111 0.140 0.130 0.119 0.109 0.149 0.118 0.113 0.117 0.119 0.112 0.125 0.166 0.180 0.129 0.151 0.143 0.124 0.114 0.181 
0.110 0.127 0.118 0.119 
0.127 0.09$
pedigree from ALLWHITE.fam perhaps
"""

import sys,os,glob,string,random,zlib,copy

phesource="/mnt/memefs/proj/EVE_GWAS/EVE_DISTRIBUTION/020111_EVE_genotype_files/ASTHMA_GWAS/pbat/06272011_EVE_phenoPC.phe"
phedest="/mnt/memefs/proj/EVE_GWAS/EVE_DISTRIBUTION/020111_EVE_genotype_files/fam_files/combined/06272011_EVE_phenoPCNumID.phe"
debug = False


        
def allNum(s=''):
    """ encode a potentially alphanumeric string into all numerics by 32bit crc
        this deprecates and probably speeds up what was done previously 
        
        replacing letters with their ord() values as strings - eg 0c0->0990
        must no less unique than the original alphanumeric key?
    """
    if s == '0':
        return s # noop
    if s == '-':
        print '##Error: Input pedigree contains %s as an identifier - this will cause pbat to barf - replaced with random new id'
        nres = '%d' % random.randint(1,99999999)
    else:
        nres = '%d' % zlib.crc32(s)
        nres = nres[:8]
    return nres

def testEVE(g= 'ALL*.fam'):
    """see if any duplicate ids if we replace letters with numbers
    """
    for fname in glob.glob(g):
        f = open(fname,'r').readlines()
        f = [x.strip().split() for x in f]
        f = [map(None,x) for x in f]
        ids = ['%s_%s' % (x[0], x[1]) for x in f]
        ids2 = ['%s_%s' % (allNum(x[0]), allNum(x[1])) for x in f]
        lens = [len(x) for x in ids2]
        maxl = max(lens)
        print '## max l = %d, %s' % (maxl,' '.join([x for x in ids2 if len(x) == maxl][:20]))
        nids = len(set(ids))
        nids2 = len(set(ids2))
        if nids <> nids2:
               print '## Nope, %s has %d real ids (%s) but %d alpha stripped ids (%s)' % (fname,nids,ids[:20],nids2,ids2[:20])
        else:
              print fname,'is all good with numbers replaced with a letter'



def writeFbat(fnames=[],ofname=None,pedigree={}):
    """write doses in fbat format, appending all individuals in files in fnames list to the output cped format file
    note ugly requirement for reading entire input file into ram - makes it simpler to code and I hope thus more reliable
    pedigree is keyed by fid_iid
    """
    outf = open(ofname,'w')
    rslist = None
    rsdict = None
    firstfile = None
    crosswalk = None # may need to map inconsistent snp offsets
    seenIds = {}
    for i,fname in enumerate(fnames):
        if debug:
            print 'processing %s' % fname
        inf = open(fname,'r')
        dat = [x.strip().split() for x in inf] # ughh. No real choice as we need to transpose
        head = dat.pop(0) # rs a1 a2 fid_id,... 
        head = head[3:] # drop snp a1 a2
        myrslist = [x[0] for x in dat] # transpose (parse) rs list
        dat = [x[3:] for x in dat] #  now drop first 3 columns - rs a1 a2 to simplify the book keeping
        lenhead = len(head) # actual # ids * 2
        imax = lenhead - 1
        oids = ['%s_%s' % (head[j],head[j+1]) for j in range(0,imax,2)] # pair up fid and iid
        newids = ['%s_%s' % (pedigree[oid][0],pedigree[oid][1]) for oid in oids] 
        assert len(oids) == len(newids),'##Error: len oids = %d, newids = %d' % (len(oids),len(newids))
        if debug:
            print '# head %s len = %d' % (head[:30],len(head))
            print '# oids %s len = %d' % (oids[:10],len(oids))
            print '# newids %s len = %d' % (newids[:10],len(newids))
        if i == 0: # take first as reference
            seenIds = dict(zip(oids,range(len(oids))))
            rslist = myrslist # make others conform
            if debug: 
                 print '## %s len rslist = %d' % (fname,len(rslist))
            outf.write(' '.join(rslist)) # fbat header row - we output doses always in this order
            outf.write('\n')
            rsdict = dict(zip(rslist,range(len(rslist)))) # output row offset = index for future subcohort crosswalks
            firstfile = fname
            crosswalk = None # never needed first time
        else: # create crosswalk for rs numbers - turns out not to be needed for blacks at least so far
            seen = [x for x in oids if seenIds.get(x,None)]
            if len(seen) > 0:
                 print '## Seeing repeated oids %s in file %s' % (seen,fname) 
                 print '## please fix and try again - ending'
                 sys.exit(1)
            nextseen = len(seenIds)
            for j,anid in enumerate(oids):
                  seenIds.setdefault(anid,nextseen+j)
            crosswalk = [rsdict.get(x,None) for x in myrslist] # may be same as range()
            missing = [x for x in crosswalk if x == None]
            if len(missing) > 0:
                 print 'File %s is missing %d snps compared with %s' % (fname,len(missing),firstfile) 
            different = [x for j,x in enumerate(crosswalk) if j <> x] # not same order as (arbitrary) first file in series
            if len(different) > 0: # need to lookup real location of each snp
                 print 'File %s has %d differently ordered snps compared with %s' % (fname,len(different),firstfile)
            else: # no need for lookup
                 crosswalk = None
        if debug:
              print '## len(ids) = %d - %s' % (len(ids),ids[:10])
        for i,id in enumerate(oids):
            ped = pedigree.get(id,None)
            if ped:
                offset = i # bookkeeping - snps as columns for this subject when we transpose
                if crosswalk:
                    offset = crosswalk[offset] # pointer                
                doses = ' '.join([x[offset] for x in dat]) # to transpose the ith subject's doses in same order as first file rs
                row = '%s %s\n' % (' '.join(ped),doses)
                outf.write(row)
            else:
                print '## no pedigree found matching oid %s in %s' % (id,fname)
        del dat # not sure if this really helps - memory seems to grow with use...sigh
    outf.close()

def readPed(fname=None):
    """ parse a fam file into a pedigree dict keyed by fid_iid
    ugh. christoph now wants probands to have fake parental ids august 2011
    so we look for founder id's not listed as someone's parent
    """
    p = open(fname,'r').readlines()
    bad = open('%s_missingparents.txt' % fname,'w')
    p = [x.strip().split() for x in p]
    plen = len(p)
    print '## original p = %s' % ','.join(['%s_%s' % (x[0],x[1]) for x in p[:20]])
    fp = []
    for ped,row in enumerate(p):
        newrow = copy.deepcopy(row)
        for i in range(4):
           if row[i] <> '0':
               newrow[i] = allNum(row[i])
        fp.append(newrow)
    fids = set([x[0] for x in fp])
    iddict = dict(zip([(x[0],x[1]) for x in fp],range(plen))) # for quick lookups
    assert len(iddict) == plen,'pedigree IID clash - iddict has %d, fp has %d' % (len(iddict),plen)
    # use index into p to find people
    fathers = [(i,(x[0],x[2])) for i,x in enumerate(fp)] 
    # fathers defined by being referred to as fathers
    mothers = [(i,(x[0],x[3])) for i,x in enumerate(fp) if x[3] <> '0'] # mothers ditto
    parents = [x[1] for x in fathers]
    parents += [x[1] for x in mothers] # symbols in iid to recognise parents
    uparents = set(parents)
    neither = [i for i,x in enumerate(fp) if (x[0],x[1]) not in uparents] # not a parent - must be a proband
    partheno = [i for i,x in enumerate(fp) if x[2] == x[3] and x[2] <> '0']
    operFID = dict(zip(fids,[[] for x in fids]))
    for i in neither: # these are offsets into p of probands
        ped = fp[i]
        fid = ped[0]
        operFID[fid].append(i) # pedigree to hit - store for fixing later
        """
    for missp in missmum:
        misspi = [x[0] for x in missp] # pointer into 
        orphan = fp[i]
        orphan[3] = potentialfakes.pop()
        fp[i] = orphan
        res = '## Fixed pedigree = mother id %s at row %d changed to in %s' % (p[misspi][3],misspi,fp[misspi][3],fname)
        bad.write('%s\n' % res)
        bad.write('\n')     
    for missp in missdad:
        misspi = [x[0] for x in missp] # pointer into 
        orphan = fp[i]
        orphan[2] = potentialfakes.pop()
        fp[i] = orphan
        res = '## Fixed pedigree = father id %s at row %d changed to in %s' % (p[misspi][2],misspi,fp[misspi][2],fname)
        bad.write('%s\n' % res)
        bad.write('\n')     
    """
    duaAnakCukup = [x for x in fids if operFID.get(x) > 1]
    print '### Will fix fids - dua anak cukup = ',duaAnakCukup 
    potentialfakes = range(1000000)
    potentialfakes = [x for x in potentialfakes if not iddict.get((x,x),None)] # remove any existing ids
    random.shuffle(potentialfakes)
    print '##Fixing %d probands to have fake parents for Christoph using %d potential fake iids (!)' % (len(neither),len(potentialfakes))
    for fid in duaAnakCukup:
        offspring = operFID[fid]
        for i,ped in enumerate(offspring): # leave first alone
            rec = fp[ped]
            if rec[2] == '0':
                rec[2] = potentialfakes.pop()
            if rec[3] == '0':
                rec[3] = potentialfakes.pop()
            fp[ped] = rec
            if i > 0:
                notgood = True
                while notgood:
                    newfid = potentialfakes.pop()
                    newm = potentialfakes.pop()
                    newf = potentialfakes.pop()
                    rec[0] = '%d' % newfid
                    rec[2] = '%d' % newm
                    rec[3] = '%d' % newf
                    if iddict.get((newfid,rec[1]),None):
                        notgood = True
                    else:
                        fp[ped] = rec
                        notgood = False
    
    partheno = [i for i,x in enumerate(fp) if x[2] == x[3] and x[2] <> '0']
    if len(partheno) > 0:
        res = ['##crc induced parthenogenesis at row %d in file %s - orig=%s:crc=%s' % (i+1,fname,p[i],fp[i]) for i in partheno]
        bad.write('\n'.join(res))
        bad.write('\n')
        print '\n'.join(res)
    bad.close()
    for ped,row in enumerate(p):
        affection = row[5]
        if affection == '-9':
            fp[ped][5] = '0'
    pk = ['%s_%s' % (x[0],x[1]) for x in p] # original keys
    pedigree = dict(zip(pk,fp))
    xwalk = open('%scrosswalk.xls' % fname,'w')
    head = ['oFID','oIID','oFaID','oMoID','oGender','oAffection', 'nFID','nIID','nFaID','nMoID','nGender','nAffection']
    xwalk.write('\t'.join(head))
    xwalk.write('\n')
    for ped,row in enumerate(p):
        pk = '%s_%s' % (row[0],row[1])
        affection = row[5]
        newrow = pedigree.get(pk,None)
        if newrow:
            s = '%s\t%s\n' % ('\t'.join(row),'\t'.join(newrow))
            xwalk.write(s)
        else:
            print '###ERROR: pk = %s not found in pedigree crosswalk' % pk
    xwalk.close()
    print '## p',p[:20]
    print '## fp',fp[:20]
    return pedigree

def conv(pedfname=None,dosedir=None,chrlist=None):
    """ read pedigree from .fam file
    for each dosage file, write out an fbat format version
    """
    pedigree = readPed(pedfname)
    print '## read %s -> %d rows' % (pedfname,len(pedigree.keys()))
    race = os.path.split(dosedir)[-1]
    if race == '':
        race = os.path.split(dosedir)[0] # if given as whites/
    random.shuffle(chrlist)
    print 'chrlist=',chrlist
    for chrom in chrlist:
        flist = glob.glob(os.path.join(dosedir,'*_chr%d_*.dat' % chrom))
        flist.sort()
        ofname = os.path.join(dosedir,'ALL%s_chr%d.cped' % (race.upper(),chrom))
        print '## converting %s to %s' % ('+'.join(flist),ofname)
        writeFbat(flist,ofname,pedigree)


def fixpheno(phesource=None,phedest=None):
    """adjust pheno ids in exactly the same way
    """
    assert os.path.isfile(phesource),'Phenotype source file %s not found' % phesource
    xwalks = ['ALLWHITE.famcrosswalk.xls','ALLBLACK.famcrosswalk.xls','ALLHISP.famcrosswalk.xls']
    pedigree = {}
    for fn in xwalks:
        assert os.path.isfile(fn),'##Error - this conversion must now be run from the same directory (eg: /mnt/memefs/proj/EVE_GWAS/EVE_DISTRIBUTION/020111_EVE_genotype_files/fam_files/combined) as %s to ensure pedigree consistency' % fn
        p = open(fn,'r').readlines()
        p = p[1:] # drop header
        for i,row in enumerate(p):
            row = row.rstrip()
            peds = row.split('\t')
            if len(peds) >= 12:
                newped = peds[6:12]
                k = '%s_%s' % (peds[0],peds[1])
                assert not pedigree.get(k,None),'##Error key %s already exists in pedigree while reading crosswalk %s' % (k,fn)                
                pedigree[k] = newped
            else:
                print '##short row %d = %s in %s' % (i,row,fn)
    inphe = open(phesource,'r').readlines()
    outphe = open(phedest,'w')
    phelen = None
    nmiss= 0
    for i,irow in enumerate(inphe):
        row = irow.split()
        if i > 0:
             if not phelen:
                phelen = len(row)
             else:
                assert len(row) == phelen,'##Error: row %d of %s is not the same length %d as the header was' % (i,phesource,phelen)
             k = '%s_%s' % (row[0],row[1])
             newped = pedigree.get(k,None)
             if newped:
                 row[0] = newped[0]
                 row[1] = newped[1]
                 outphe.write(' '.join(row))
                 outphe.write('\n')
             else:
                 nmiss += 1
                 print '##Error: row %d of %s has k %s - not found in the crosswalks' % (i,phesource,k)
        else:
            outphe.write(irow)
    outphe.close()
    print '## Converted %d ids from %s into all numeric also as %s - %d rows dropped because not in crosswalks' % (i, phesource,phedest,nmiss)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print """
Kludge to convert EVE FID and IID into all numerics for pbat which does not accept non-digit
ID characters and similarly to fix phenotype files
Imposed on code to join multiple cohort transposed MACH imputed dosage data into .cped format for pbat
        
Written by Ross Lazarus june/july 2011
There are three ways to use this software:

         1) If you pass command line parameters [fam file path] [path for MACH dosage and output files] [optional chrom list] for conversion - eg    
python doseChrNumcped.py ALLBLACKS.fam blacks/ 22,21
         it will amalgamate MACH dosage files into racial groups.
         All autosomes will be converted if no explicit chromosome list parameter is given
        
         2) to convert ids in a phenotype, supply the word "pheno" (without quotes) as the first parameter and the paths
         to the input phenotype file and the required output phenotype file - eg:
python doseChrNumcped.py pheno /some/long/path/foo.phe /another/path/foonumeric.phe   

         3) to check consistency of a pedigree in a plink .fam file, use
python doseChrNumcped.py ped [path to .fam file]
         will generate a report to a text file 'bad.txt' and print errors on the screen
"""
        sys.exit(1)
    if sys.argv[1] == 'ped':
         assert len(sys.argv)==3,'ped option checks a plink fam file but requires the path to a fam file as the second parameter'
         pf = sys.argv[2]
         assert os.path.isfile(pf),'fam file %s is not readable' % pf
         readPed(pf)
         sys.exit(0)
    if sys.argv[1] == 'eve':
         testEVE()
         sys.exit(0)

    if sys.argv[1].lower() == 'pheno':
       print sys.argv
       if len(sys.argv) > 2:
            phesource = sys.argv[2]
            assert os.path.isfile(phesource),"## supplied param 2 %s for pheno conversion is not a file" % sys.argv[2]
       if len(sys.argv) > 3:
            phedest = sys.argv[3]
            print 'phedest=',phedest
       assert phesource <> phedest, '## Sorry but I will NOT overwrite the source phenotype file %s' % phesource
       print "## doseChrNumcped converting alpha FID/IID into numerics from phenotype file %s into %s" % (phesource,phedest)
       fixpheno(phesource=phesource,phedest=phedest)
       sys.exit(0)     
    assert len(sys.argv) >= 3, '##doseChrNumcped.py 2 params required: [fam file] [directory with MACH dose files to be joined] | [1,2...]'
    famfile = sys.argv[1]
    dosedir = sys.argv[2]
    assert os.path.isfile(famfile), '## doseChrNumcped cannot open fam file %s' % famfile
    assert os.path.isdir(dosedir), '## doseChrNumcped %s is not a directory' % dosedir
    if len(sys.argv) > 3:
        try:
            chrlist = sys.argv[3].split(',')
            chrlist = map(int,chrlist)
        except:
            print '##doseChrNumcped.py: Unable to parse third (chromosome number list) parameter - should be (eg) 1,2,3 or blank for all'
            sys.exit(1)
    else:
        chrlist = range(22,0,-1)
    print '##doseChrNumcped.py making amalgamated cped for chromosomes %s in %s' % (chrlist,dosedir)
    conv(pedfname = famfile, dosedir = dosedir, chrlist=chrlist)


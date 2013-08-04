# plinkParse.py
# output scanner for a plink run
# makes tab delimited summary files for
# R/SAS summary and ucsc genome graphs
# ross lazarus me fecit march 4 2007
# in anticipation of the first CAMP wga illumina data
# can make files for plotting 
# by marker (hwe, missingness, freq)
# and by subject (missingness, X het)
# and by family (mendel errors)
# added count of heterozygous loci march 5 ross
# do we need to split stats by X and autosomes for QC?
# added missval dict for quick check
# TODO: add wig ucsc track generators for association stats

"""
notes from Plink docs

Summary statistics versus inclusion criteria

The following table summarizes the relationship between the commands to generate summary statistics (as described on the previous 
page, versus the commands to exclude individuals and/or markers, which are described on this page.

Feature                         As summary statistic    As inclusion criteria
Missingness per individual      --missing               --mind N
Missingness per marker          --missing               --geno N        
Allele frequency                --freq  --maf N
Hardy-Weinberg equilibrium      --hardy                 --hwe N
Mendel error rates              --mendel                --me N M
[rerla@meme ~/plink]$ cat *.sh
/usr/local/bin/plink --noweb --file fakeped_100000 --make-bed --out fakeped_100000
/usr/local/bin/plink --noweb --bfile fakeped_100000 --out cleantest --freq
/usr/local/bin/plink --noweb --bfile fakeped_100000 --out cleantest --missing
/usr/local/bin/plink --noweb --bfile fakeped_100000 --out cleantest --mendel
/usr/local/bin/plink --noweb --bfile fakeped_100000 --out cleantest --hardy --check-sex
/usr/local/bin/plink --noweb --bfile fakeped_100000 --make-bed --out cleanped_100000 --mind 0.1 \
--geno 0.1 --maf 0.01 --hwe 0.00001 --me 0.05 0.05

plink output samples v 0.99 for the following script and a fake ped file 100k snps

--missing generates 2 files
*.imiss by individual 
 FID  IID MISS_PHENO     N_MISS     F_MISS
   0    1          N       4928  0.0497637
   0    2          N       3912   0.039504
   0    3          N       3916  0.0395444
   1    1          N       4706  0.0475219
   1    2          N       3885  0.0392313
   1    3          N       3988  0.0402714
   2    1          N       4774  0.0482086
   2    2          N       3994   0.040332
   2    3          N       4730  0.0477643

*.lmiss by marker
 CHR         SNP   N_MISS     F_MISS
   1   rs1891910        3   0.030303
   1   rs1133647        3   0.030303
   1   rs9442371        3   0.030303
   1  rs10907178        3   0.030303
   1  rs12066903        2   0.020202
   1  rs12092254        2   0.020202
   1  rs11260554        7  0.0707071
   1  rs11466681        4   0.040404
   1  rs11466675        1   0.010101   


--freq generates one file
*.frq
 CHR          SNP   A1   A2          MAF       NM
   1    rs1891910    4    2    0.0461538      130
   1    rs1133647    3    4     0.436508      126
   1    rs9442371    1    2     0.378788      132
   1   rs10907178    1    4        0.125      128
   1   rs12066903    1    4    0.0307692      130
   1   rs12092254    1    2     0.361538      130
   1   rs11260554    2    3     0.286885      122
   1   rs11466681    4    2      0.21875      128
   1   rs11466675    4    2     0.207692      130

 --hardy generates one file  
*.hwe
        SNP     TEST                 GENO   O(HET)   E(HET)        P_HWD 
  rs1891910      ALL               0/6/59  0.09231  0.08805            1
  rs1891910      AFF                0/0/0      nan      nan           NA
  rs1891910    UNAFF               0/6/59  0.09231  0.08805            1
  rs1133647      ALL             12/31/20   0.4921   0.4919            1
  rs1133647      AFF                0/0/0      nan      nan           NA
  rs1133647    UNAFF             12/31/20   0.4921   0.4919            1


--mendel generates 4 files 
*.mendel
 FID  KID  CHR         SNP   CODE                 ERROR
  10    3    1  rs11466681      2      2/2 x 2/2 -> 4/2
  31    3    1  rs11466681      3      2/2 x */* -> 4/4
  17    3    1  rs35502961      4      */* x 4/4 -> 3/3
  10    3    1  rs34577759      3      3/3 x */* -> 4/4
  29    3    1  rs34577759      7      */* x 4/4 -> 3/3
  20    3    1    rs819976      3      4/4 x */* -> 1/1
   2    3    1   rs6684574      6      4/4 x */* -> 2/2
  13    3    1   rs4648806      7      */* x 4/4 -> 2/2
  24    3    1   rs3128291      7      */* x 3/3 -> 1/1

*.fmendel is total per family
 FID  PAT  MAT   CHLD    N
   0    1    2      1  938
  10    1    2      1 1038
  11    1    2      1  969
  12    1    2      1 1010
  13    1    2      1  986
  14    1    2      1 1055
  15    1    2      1 1002
  16    1    2      1  988
  17    1    2      1 1037
  
*.imendel is errors by individual
 FID  IID   N
   0    1  478
   0    2  466 
   0    3  938
  10    1  540
  10    2  521 
  10    3 1038
  11    1  479
  11    2  471 
  11    3  969
  
*.lmendel is errors by marker
 CHR         SNP   N
   1   rs1891910    0
   1   rs1133647    0
   1   rs9442371    0
   1  rs10907178    0
   1  rs12066903    0
   1  rs12092254    0
   1  rs11466681    2
   1  rs11466675    0
   1  rs35502961    1

--freq generates one file
*.frq
 CHR          SNP   A1   A2          MAF       NM
   1    rs1891910    4    2    0.0461538      130
   1    rs1133647    3    4     0.436508      126
   1    rs9442371    1    2     0.378788      132
   1   rs10907178    1    4        0.125      128
   1   rs12066903    1    4    0.0307692      130
   1   rs12092254    1    2     0.361538      130
   1   rs11260554    2    3     0.286885      122
   1   rs11466681    4    2      0.21875      128
   1   rs11466675    4    2     0.207692      130

--check-sex generates one file based on X heterozygosity
*.sexcheck 
 FID  IID       PEDSEX       SNPSEX       STATUS            F
   0    1            1            1           OK            1
   0    2            2            2           OK     -0.07851
   0    3            2            0      PROBLEM       0.4607
   1    1            1            1           OK            1
   1    2            2            2           OK       -1.696
   1    3            2            0      PROBLEM       0.4607
   2    1            1            1           OK            1
   2    2            2            2           OK       -0.208
   2    3            1            1           OK            1

--mind 0.1 generates one file showing famid and iid of all individuals removed
*.irem 
0       1
0       3
1       1
2       1
3       1
4       1
4       3
5       1
5       3
6       1

--make-bed seems to generate a list of males heterozygous for X calls?
*.hh
3       1       rs5988663
8       1       rs5988663
15      1       rs5988663
23      1       rs5988663
26      1       rs5988663
28      1       rs5988663
28      3       rs5988663
0       1       rs5988436
1       1       rs5988436
2       1       rs5988436
"""
import os,glob,sys,math
from optparse import OptionParser

prog = 'plinkParse'
vers = '0.0001'


missvals = {'0':'0','N':'N','-9':'-9','-':'-'} # fix me if these change!

def countHet(pedf='fakeped_500000.ped',linkageped=True,froot='fake500k'):
    """count het loci for each subject to look for outliers = ? contamination
    assume ped file is linkage format
    """
    outf = '%s_nhet.xls' % froot # must match R script
    f = file('%s.ped' % pedf,'r')
    if not linkageped:
        head = f.next() # throw away header
    hets = []
    n = 1
    for l in f:
        if n % 50 == 0:
            print 'at line %d' % n
        n += 1
        ll = l.strip().split()
        if len(ll) > 6:
            iid = '_'.join(ll[:2]) # fam_iid
            gender = ll[4]
            alleles = ll[6:]
            nallele = len(alleles)
            nhet = 0
            for i in range(nallele/2):
                a1=alleles[2*i]
                a2=alleles[2*i+1]
                if alleles[2*i] <> alleles[2*i+1]: # must be het
                    if not missvals.get(a1,None) and not missvals.get(a2,False):
                        nhet += 1
            hets.append((nhet,iid,gender)) # for sorting later
    f.close()
    hets.sort()
    hets.reverse() # biggest nhet now on top
    f = open(outf ,'w')
    res = ['%d\t%s\t%s' % (x) for x in hets] # I love list comprehensions
    res.insert(0,'nhetloci\tfamid_iid\tgender')
    res.append('')
    f.write('\n'.join(res))
    f.close()
    
def subjectRep(froot='cleantest'):
    """by subject (missingness = .imiss, mendel = .imendel)
    assume replicates have an underscore in family id for
    hapmap testing
    """
    imissfile = '%s.imiss' % froot
    imendfile = '%s.imendel' % froot
    outfile = '%s_subject.xls' % froot
    idlist = []
    imissdict = {}
    imenddict = {}
    # ------------------missing--------------------
    # imiss has FID  IID MISS_PHENO N_MISS  F_MISS
    # we want F_MISS
    f = file(imissfile,'r')
    head = f.next().strip().split() # expect above
    fidpos = head.index('FID')
    iidpos = head.index('IID')
    fpos = head.index('F_MISS')
    n = 0
    for l in f:
        ll = l.strip().split()
        if len(ll) >= fpos: # full line
            fid = ll[fidpos]
            if fid.find('_') == -1: # not replicate!                    
                iid = ll[iidpos]
                fmiss = ll[fpos]
                id = '%s_%s' % (fid,iid)
                imissdict[id] = fmiss
                idlist.append(id) # keep for output in order
    f.close()
    print 'Read %d markers from %s' % (len(imissdict.keys()),imissfile)
    # ------------------mend-------------------
    # *.imendel has FID  IID   N
    # we want N
    gotmend = True
    try:
        f = file(imendfile,'r')
    except:
        gotmend = False
        for id in idlist:
            imenddict[id] = '0'
    if gotmend:
        head = f.next().strip().split() # expect above
        npos = head.index('N')
        fidpos = head.index('FID')
        iidpos = head.index('IID')
        for l in f:
            ll = l.strip().split()
            if len(ll) >= npos: # full line
                fid = ll[fidpos]
                if fid.find('_') == -1: # not replicate!                    
                    iid = ll[iidpos]
                    id = '%s~%s' % (fid,iid)
                    nmend = ll[npos]
                    imenddict[id] = nmend
        f.close()
        print 'Read %d markers from %s' % (len(imenddict.keys()),imendfile)
    else:
        print 'No %s file - assuming not family data' % imendfile
    # now assemble and output result list
    rhead = ['famId','iId','FracMiss','Mendel_errors']
    head = '\t'.join(rhead)
    res = [head,]
    for i in xrange(len(idlist)): # for each snp in found order
        id = idlist[i]
        fid,iid = id.split('_') # recover keys
        f_missing = imissdict[id]
        nmend = imenddict.get(id,'0')
        s = '\t'.join([fid,iid,f_missing,nmend])
        res.append(s)
    f = file(outfile,'w')
    res.append('')
    f.write('\n'.join(res))
    f.close()    

def markerRep(froot='cleantest'):
    """by marker (hwe = .hwe, missingness=.lmiss, freq = .frq)
    keep a list of marker order but keep all stats in dicts
    write out a fake xls file for R or SAS etc
    kinda clunky, but..
    TODO: ensure stable if any file not found? 
    """
    hwefile = '%s.hwe' % froot
    lmissfile = '%s.lmiss' % froot
    freqfile = '%s.frq' % froot
    lmendfile = '%s.lmendel' % froot
    outfile = '%s_marker.xls' % froot
    markerlist = []
    chromlist = []
    hwedict = {}
    lmissdict = {}
    freqdict = {}
    lmenddict = {}
    # -------------------hwe--------------------------
    #    hwe has SNP TEST  GENO   O(HET)   E(HET) P_HWD
    # we want all hwe where P_HWD <> NA
    f = file(hwefile,'r')
    head = f.next().strip().split() # expect above
    testpos = head.index('TEST')
    ppos = head.index('P_HWD')
    snppos = head.index('SNP')
    for l in f:
        ll = l.strip().split()
        if len(ll) >= ppos: # full line
            if ll[ppos] <> 'NA': # worth keeping
                rs = ll[snppos]
                test = ll[testpos]
                ps = ll[ppos]
                if ps <> '1':
                    pval = '%7.5f' % -math.log(float(ps))
                else:
                    pval = '0'
                if not hwedict.get(rs,None):
                    markerlist.append(rs) # keep in order but first only!
                    hwedict[rs] = {test:pval} # first time
                else:
                    hwedict[rs][test] = pval
    f.close()
    print 'Read %d markers from %s' % (len(hwedict.keys()),hwefile)
    # ------------------missing--------------------
    # lmiss has  CHR SNP   N_MISS     F_MISS
    # we want F_MISS
    f = file(lmissfile,'r')
    head = f.next().strip().split() # expect above
    chrpos = head.index('CHR')
    ppos = head.index('F_MISS')
    npos = head.index('N_MISS')
    snppos = head.index('SNP')
    n = 0
    for l in f:
        ll = l.strip().split()
        if len(ll) >= ppos: # full line
            rs = ll[snppos]
            chrom = ll[chrpos]
            pval = ll[ppos]
            lmissdict[rs] = pval # for now, just that?
            if markerlist[n] == rs:
                chromlist.append(chrom) # one place to find it?
            else:
                print '### row %d has %s - not %s as in markerlist' % (n,rs,markerlist[n])
        n += 1
    f.close()
    print 'Read %d markers from %s' % (len(lmissdict.keys()),lmissfile)
    # ------------------freq-------------------
    # frq has CHR          SNP   A1   A2          MAF       NM
    # we want maf
    f = file(freqfile,'r')
    head = f.next().strip().split() # expect above
    mafpos = head.index('MAF')
    a1pos = head.index('A1')
    a2pos = head.index('A2')
    snppos = head.index('SNP')
    for l in f:
        ll = l.strip().split()
        if len(ll) >= mafpos: # full line
            rs = ll[snppos]
            a1 = ll[a1pos]
            a2 = ll[a2pos]
            maf = ll[mafpos]
            freqdict[rs] = (maf,a1,a2)
    f.close()
    print 'Read %d markers from %s' % (len(freqdict.keys()),freqfile)
    # ------------------mend-------------------
    # lmend has CHR SNP   N
    # we want N
    gotmend = True
    try:
        f = file(lmendfile,'r')
    except:
        gotmend = False
        for rs in markerlist:
            lmenddict[rs] = '0'
    if gotmend:
        head = f.next().strip().split() # expect above
        npos = head.index('N')
        snppos = head.index('SNP')
        for l in f:
            ll = l.strip().split()
            if len(ll) >= npos: # full line
                rs = ll[snppos]
                nmend = ll[npos]
                lmenddict[rs] = nmend
        f.close()
        print 'Read %d markers from %s' % (len(lmenddict.keys()),lmendfile)
    else:
        print 'No %s file - assuming not family data' % lmendfile
    # now assemble result list
    rhead = ['snp','chrom','maf','a1','a2','missfrac','logp_hwe_all','logp_hwe_unaff','N_Mendel']
    head = '\t'.join(rhead)
    res = [head,]
    for i in xrange(len(markerlist)): # for each snp in found order
        chrom = chromlist[i]
        rs = markerlist[i]
        f_missing = lmissdict[rs]
        maf,a1,a2 = freqdict[rs]
        hwe_all = hwedict[rs].get('ALL','0') # hope this doesn't change...
        hwe_unaff = hwedict[rs].get('UNAFF','0')
        nmend = lmenddict.get(rs,'0')
        s = '\t'.join([rs,chrom,maf,a1,a2,f_missing,hwe_all,hwe_unaff,nmend])
        res.append(s)
    f = file(outfile,'w')
    res.append('')
    f.write('\n'.join(res))
    f.close()

u = """This program will generate fake excel files for R or SAS processing from a
series of Plink () output files. Ross Lazarus, March 2007
Usage: python %s.py -f [plink output file root]
""" % prog

if __name__ == "__main__":
    parser = OptionParser(usage=u, version="%prog")
    a = parser.add_option
    a("-f","--file",type="str",dest="froot",
      help="file root: usually whatever you supplied to plink as --file",default=None)
    a("-l","--linkageped",type="str",dest="lpedfile",
      help="linkage format ped file name: usually whatever you supplied to plink as --file",default=None)
    a("-p","--ped",type="str",dest="pedfile",
      help="fbat format ped file name: ped file with marker header line",default=None)
    (options,args) = parser.parse_args()
    if options.lpedfile and options.pedfile:
        print 'Cannot use both -p and -l options'
        print u
        sys.exit(1)
    if options.froot:
        if options.lpedfile:
            countHet(options.lpedfile,linkageped=True,froot=options.froot)
        elif options.pedfile:
            countHet(options.pedfile,linkageped=False,froot=options.froot)   
        subjectRep(froot=options.froot)
        markerRep(froot=options.froot)
    else:
        print 'No file root provided - cannot run'
        print u

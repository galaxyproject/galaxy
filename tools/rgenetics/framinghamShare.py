"""
framingham share data arrives as a mess of gzipped individual genotype files
inside tarballs inside RAR archives.
Oy

Matrix format has less redundancy than individual format

Code here reads both individual and matrix format. The individual data contains
intensity and quality scores that are useful for evaluating hits, but the scale makes managing
these challenging. eg sorting the intensity data for only 1/3 (the nonprofit release) takes about 10
hours. Not sure whether it's worth the bother of loading it up...

"""

import glob, sys, os, MySQLdb, csv, copy, array

adict = {'A':'1','C':'2','G':'3','T':'4','0':'0','N':'0','1':'1','2':'2','3':'3','4':'4'}



def readPed(pedname="phs000007.pht000183.v1.p1.c2.share_ped.NPU.txt",
            ped2name='phs000007.pht000182.v1.p1.c2.shareids.NPU.txt'):
    """
    What a mess. There are
    make the start of a pedigree file
# Study accession: phs000007.v1.p1
# Table accession: pht000183.v1.p1.c2
# Consent group: Non-Profit Use Only
# Citation instructions: The study accession (phs000007.v1.p1) is used to cite the study and
#its data tables and documents. The data in this 
file shoul
cited us$
# To cite columns of data within this file, please use the variable (phv#) accessions below:
#
# 1) the table name and the variable (phv#) accessions below; or
# 2) you may cite a variable as phv#.v1.p1.c2.

##phv00024067   phv00024068     phv00024069     phv00024070     phv00024071     phv00024072     phv00024073     phv00024074     phv00024075     
phv0002 
phv0$
pedno   shareid fshare  mshare  SEX     itwin   idtype  pheno   geno    genrelease      nonprofit
1       16                      2               0       1               0       1
1       3226    9218    8228    2               3       1       1       1       0
1       8228                    2               1       1       1       1       0
1       9218    17008   16      1               1       1               1       0


    not families, but this file contains lots of subjects missing from the share_ped file!
    [rerla@meme geno]$ more phs000007.pht000182.v1.p1.c2.shareids.NPU.txt 
# Study accession: phs000007.v1.p1
# Table accession: pht000182.v1.p1.c2
# Consent group: Non-Profit Use Only
# Citation instructions: The study accession (phs000007.v1.p1) is used to cite the study and its data tables and documents. The data in this 
file should
 be cited using the accession pht000182.v1.p1.c2.
# To cite columns of data within this file, please use the variable (phv#) accessions below:
#
# 1) the table name and the variable (phv#) accessions below; or
# 2) you may cite a variable as phv#.v1.p1.c2.

##phv00024058   phv00024059     phv00024060     phv00024061     phv00024062     phv00024063     phv00024064     phv00024065     phv00024066
shareid idtype  SEX     pheno   geno    pedno   itwin   genrelease      nonprofit
1       0       2       1                               0       1
2       1       2       1               126             0       1
3       0       2       1       1                       0       1

    """
    f = file(pedname,'r')
    header = None
    ped = {}
    for row,line in enumerate(f):
        line = line.strip()
        if len(line) > 0:
            if line[0] <> '#':
                if header == None:
                    header = line.split('\t')
                    cfamid = header.index('pedno')
                    cshareid = header.index('shareid')
                    cfshareid = header.index('fshare')
                    cmshareid = header.index('mshare')
                    cgender = header.index('SEX')
                else:
                    ll = line.split('\t')
                    pednum = ll[cfamid]
                    shareid = ll[cshareid]
                    fid = '0'
                    if len(ll[cfshareid]) > 0:
                        fid = ll[cfshareid]
                    mid = '0'
                    if len(ll[cmshareid]) > 0:
                        mid = ll[cmshareid]
                    gender = ll[cgender]
                    ped[shareid] = [pednum,shareid,fid,mid,gender,'1'] # dummy affection status
    print 'read %d rows from %s' % (row,pedname)
    f = file(ped2name,'r')
    header = None
    for row,line in enumerate(f):
        line = line.strip()
        if len(line) > 0:
            if line[0] <> '#':
                if header == None:
                    header = line.split('\t')
                    cfamid = header.index('pedno')
                    cshareid = header.index('shareid')
                    cgender = header.index('SEX')
                else:
                    ll = line.split('\t')
                    shareid = ll[cshareid]
                    pednum = ll[cfamid]
                    if len(pednum) == 0:
                        pednum = '999%s' % shareid
                    fid = '0'
                    mid = '0'
                    gender = ll[cgender]
                    if not ped.get(shareid,None): # don't overwrite pedigree data if already there!
                        ped[shareid] = [pednum,shareid,fid,mid,gender,'1'] # dummy affection status
    print 'read %d rows from %s' % (row,ped2name)        
    return ped


def getsnp126Markers(gf=None):
    """
    seem to be a bunch of markers not in dbsnp126 - maybe perlegen?
    anyhoo, this is deprecated for the 2 affy sty and nsp annotation files
    from http://www.affymetrix.com/support/technical/byproduct.affx?product=500k
    """
    genome = MySQLdb.Connect('hg', 'hg18', 'g3gn0m3')
    curs = genome.cursor() # use default cursor
    rslist = []
    nok = nnok = 0
    for i,line in enumerate(gf):
        if line[0] <> '#' and len(line) > 10:
            ll = line.strip().split(',') # comma delim as at December 2007
            rs = ll[1]
            sql = 'select chrom,chromStart,name from hg18.snp126 where name = "%s"' % rs
            curs.execute(sql)
            res = curs.fetchone()
            if res:
                chrom,start,rs = res
                rslist.append((chrom,start,rs)) # so we can sort into map order
                nok += 1
            else:
                nnok += 1
                print '#### %dth null result for snp126 lookup of %s (%d ok)' % (nnok,rs,nok)
    rslist.sort()
    gf.seek(0) # rewind
    return rslist

def getMarkers():
    """use affy's annotation files
[rerla@meme affy500raw]$ head Mapping250K_Sty.na24.annot.csv
##For information about the Annotation file content, please see the bundled README file.
"Probe Set ID","Affy SNP ID","dbSNP RS ID","Chromosome","Physical Position","Strand","ChrX pseudo-autosomal region 1","Cytoband","Flank","Allele 
A","Al"
"SNP_A-1780358","10001174","rs17325399","5","54442707","+","0","q11.2","ggataatacatattca[A/G]accaataacatacagc","A","G","NM_152623 // downstream 
// 1873"
"SNP_A-1780551","10003881","rs12454921","18","52924726","-","0","q21.31","ggatatcaaagttcca[A/G]gatgtcttttgaggtt","A","G","NM_052834 // 
downstream // 76"


    """
    rslist = []
    fskel = 'Mapping250K_%s.na24.annot.csv'
    crs= 'dbSNP RS ID' # csv reader column for rs number in affy annotation file
    cstart= 'Physical Position' # pompous pratt whoever named these columns
    cchrom= 'Chromosome'
    for chip in ['Sty','Nsp']:
        fname = fskel % chip
        affyf = file(fname,'rb')
        crap = affyf.readline() # why oh why?
        f = csv.DictReader(affyf) # whew
        for n,row in enumerate(f):
            if n % 100000 == 0:
                print 'at row %d in %s' % (n,fname)
            rs = row[crs]
            if rs[0] <> '-':
                chrom=row[cchrom]
                start=row[cstart]
                try:
                    start = int(start)
                    rslist.append((chrom,start,rs))
                except:
                    print 'rs %s start = %s' % (start,rs)
    rslist.sort()
    return rslist


def getGenos(gf=None,rsdict=None):
    """read a subject genos into the right order
    """
    grs = {}
    for row in gf:
        if row[0] <> '#' and len(row.strip()) > 0:
            lrow = row.strip().split(',')
            rs = lrow[1]
            if rsdict.get(rs,None): # is a real rs
                if lrow[-1] == 'ND': # fucking idiots
                    grs[rs] = '0 0' # is missing, but the idiots who wrote the shit perl scripts are writing out crap
                else:
                    gt = lrow[4]
                    gcode = lrow[5]
                    qc = lrow[7]
                    a1i = lrow[8]
                    a2i = lrow[9]
                    g = map(None,gt)
                    g = [adict.get(x,'0') for x in g] # translate into numbers ..
                    grs[rs] = ' '.join(g) # make into '1 1' for ped file
    return grs
            
def readGenos(gdir = '/nfs/hg/framinghamShare_nov2007/geno/affy500raw',genoprefix='*.geno.*',ped={}):
    """rerla@meme affy500raw]$ head phg000006.ind.geno.NonProfit_Release.geno.10481
#File_Name: phg000006.ind.geno.NonProfit_Release.geno.10481
#Consent_group: Non-profit_use
#Sample_ID1: 10481
#ss#,rs#,ss2rsOrientation,rs2GenomeOrientation,genotype_genomic_orient,genotye_orig_code,
qc_bit_flags,genotype_quality_score,allele1_intensity,allele2_y
ss66079302,rs3094315,+,-,GA,1,0,0.002786,482.392090,445.126862
ss66273559,rs4040617,+,+,AG,1,0,0.006784,768.500610,561.713074
ss66317030,rs2980300,-,+,TC,1,0,0.001729,388.633301,387.334625
ss66185183,rs2905036,-,-,TT,2,0,0.031937,196.904343,703.350342
ss66174584,rs4245756,+,+,CC,0,0,0.018019,1021.935425,206.439590
ss66145570,rs4075116,+,-,TC,1,0,0.002691,888.154358,673.292847
    """
    rslist = None
    gglob = os.path.join(gdir,genoprefix)
    gflist = glob.glob(gglob) # should be about 2666 files or so
    outroot = 'framinghamaffy'
    mapf = file('%s.map' % outroot,'w')
    rslist = getMarkers()
    maplist = ['\t'.join((x[0],x[2],'0','%d' % x[1])) for x in rslist]
    mapf.write('\n'.join(maplist))
    mapf.write('\n')
    mapf.close()
    lrs = [x[2] for x in rslist] # just the rs numbers
    rsdict = dict(zip(lrs,lrs)) # for lookup while reading geno files
    outf = file('%s.ped' % outroot,'w')
    for i,fname in enumerate(gflist):
        shareid = fname.split('.')[-1] # should be the very last bit
        p = ped.get(shareid,None)
        if p:
            gf = file(fname,'r',2**30) # big read buffer...
            if (i % 200) == 0:
                print 'reading #%d = %s' % (i,shareid)
            genos = getGenos(gf=gf,rsdict=rsdict)
            row = []
            row += p
            row += [genos.get(rs,'0 0') for (chrom,offset,rs) in rslist] 
            outf.write(' '.join(row))
            outf.write('\n')
        else:
            print '### shareid %s not found in pedigree data' % shareid
    outf.close()

def readMatrix( ped={}, genopath='./', clean=True):
    """matrix format is less verbose
[rerla@meme dec6]$ head General_Release.geno.chr1 | more
dbSNP_ss dbSNP_rs Affy_SNPID chr pos ss2rs_orient rs2genome_orient allele1 allele2 11359...
alleles are as 'AA' etc
subjects are in named cols
map is mixed in and it's by chr file

need to transpose the cols to ped file rows
work by chromosome to permit easy parallel operations
    """
    rslist = getMarkers()
    lrs = [x[2] for x in rslist] # just the rs numbers
    rsdict = dict(zip(lrs,lrs)) # for lookup while reading geno files
    if clean:
       outfprefix = 'fram500kClean2007all'
       grskel = os.path.join(genopath,'General_Release.geno.mendel_clean.chr%s')
       npskel = os.path.join(genopath,'NonProfit_Release.geno.mendel_clean.chr%s')
    else:
       outfprefix = 'fram500kDirty2007all'
       grskel = os.path.join(genopath,'General_Release.geno.chr%s')
       npskel = os.path.join(genopath,'NonProfit_Release.geno.chr%s')
    clist = map(str,range(1,23))
    clist.append('X')
    allgenos = {}        
    allmap = []
    alloutpfname = '%sall.ped' % outfprefix 
    alloutmfname = '%sall.map' % outfprefix  
    for chrom in clist:
        genos = {}        
        outpfname = '%schr%s.ped' % (outfprefix,chrom)
        outmfname = '%schr%s.map' % (outfprefix,chrom)
        mapdone = None
        for fname in [grskel % chrom, npskel % chrom]: # read both sources - eesh
            print 'processing %s' % fname
            f = file(fname,'r')
            head = f.readline().strip().split()
            coldict = dict(zip(head,range(len(head)))) # lookup column from header
            cchr = coldict['chr'] # column in input line
            cpos = coldict['pos']
            crs = coldict['dbSNP_rs']
            ca1 = coldict['allele1']
            ca2 = coldict['allele2']
            ids = head[9:] # share id columns
            wewant = (cchr,cpos,crs,ca1,ca2)
            cids = [int(x) + 9 for x in range(len(ids))] # where to find genotype for this idlist index
            if not mapdone:
                mapdone = 1
                lmap = []
                f.seek(0)
                for row,s in enumerate(f):
                    if s[0] <> '#' and len(s) > 0 and row > 0:
                        slist = s.strip().split()
                        chrom,position,rs,a1,a2 = [slist[x] for x in wewant]
                        try:
                            pos = int(position)
                        except:
                            print 'bad pos in row %d - %s' % (row, slist[:10])
                            pos = position
                        lmap.append((chrom,pos,rs))
                mapf = file(outmfname,'w')
                lmap.sort()
                rslist = [x[2] for x in lmap]
                rsdict = dict(zip(rslist,range(len(rslist))))
                mapf.write(''.join(['%s\t%s\t0\t%s\n' % (x[0],x[2],str(x[1])) for x in lmap]))
                mapf.close()            
            for id in ids:
                genos[id] = array.array('c',['0' for x in xrange(2*len(lmap))]) # initialize the accumulator
            f.seek(0) # rewind - lastrow contains rowcount = snp count
            for row, s in enumerate(f):
                if s[0] <> '#' and len(s) > 0 and row > 0:
                    slist = s.strip().split()
                    chrom,position,rs,a1,a2 = [slist[x] for x in wewant]
                    genolist = [slist[x] for x in cids] # should work! magic
                    rsn = rsdict.get(rs,None) # index of this rs in each genotype row
                    if rsn <> None:
                        for n,id in enumerate(ids): # transpose
                            g = genolist[n] # AA etc
                            lg = map(None,g)[:2] # '0 0'
                            genos[id][2*rsn] = lg[0]
                            genos[id][(2*rsn)+1] = lg[1] # it's an array to save space
                    else:
                        print 'cannot find rs %s in rsdict' % rs
        for id in genos.keys():
            if not allgenos.get(id,None):
                allgenos[id] = array.array('c',[])
            allgenos[id] += genos[id] # append to the big array - not sure we have ram enough?
        allmap += lmap
        # all this chrom groups done -write ped lines
        pf = file(outpfname,'w')
        ids = genos.keys()
        ids.sort()
        for id in ids:
            if ped.get(id,None):
                genolist = genos[id] # array of char
                p = ped[id]
                row = copy.copy(p)
                row += genolist
                pf.write(' '.join(row))
                pf.write('\n')
            else:
                print 'shareid %d not found in pedigree files' % id
        pf.close()
    # write the big files 
    mapf = file(alloutmfname,'w')
    mapf.write(''.join(['%s\t%s\t0\t%s\n' % (x[0],x[2],str(x[1])) for x in allmap]))
    mapf.close()            
    pf = file(alloutpfname,'w')
    ids = allgenos.keys()
    ids.sort()
    for id in ids:
        if ped.get(id,None):
            genolist = allgenos[id] # array of char
            p = ped[id]
            row = copy.copy(p)
            row += genolist
            pf.write(' '.join(row))
            pf.write('\n')
        else:
            print 'shareid %d not found in pedigree files' % id
    pf.close()

        
    
def readFram():
    dictped = readPed(pedname="phs000007.pht000183.v1.p1.c2.share_ped.NPU.txt",
                   ped2name='phs000007.pht000182.v1.p1.c2.shareids.NPU.txt')
    #readGenos(gdir = '/nfs/hg/framinghamShare_nov2007/geno/affy500raw',genoprefix='*.geno.*',ped=ped)
    # use readGenos for the individual format files with 
    if len(sys.argv) > 1:
        genopath = sys.argv(1)
    else:
        genopath = './'
    readMatrix(ped=dictped, genopath=genopath, clean=True)


if __name__ == "__main__":
    readFram()

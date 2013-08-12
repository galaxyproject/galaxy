#convert share_pulmpheno_flags.csv 
# into phe format - header with space delim field names
# rows with famid iid to match the fbat file ids
# copyright ross lazarus january 2008
# released under the LGPL
# for the rgenetics project

import csv,os,sys

def readPed(pedname="/nfs/framinghamShare_nov2007/geno/phs000007.pht000183.v1.p1.c2.share_ped.NPU.txt",
            ped2name='/nfs/framinghamShare_nov2007/geno/phs000007.pht000182.v1.p1.c2.shareids.NPU.txt'):
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


"""
[rerla@hg pphe]$ head *csv
shareid,ppfev1adj,ppfvcadj,ppfefadj,ppratioadj,ppfefratadj,callrate,het_rate,non_inherit_flag,het_flag,callrate_flag
1990,0.7094941275,0.1767481807,,0.9447942965,,,,,,
454,0.4102760059,0.1075244963,0.5996797501,0.526133561,0.685045083,0.9891405702,0.2777487637,,,
19199,0.3857441922,-0.322331702,,1.1886408882,,,,,,
15873,-1.367512962,-1.855853278,-0.76791166,1.1124870844,0.4427592175,,,,,
5731,-0.706766055,-1.019799573,-0.294164921,0.5188129259,0.2387249048,,,,,
10556,-0.101632404,-0.063901099,-0.592163643,-0.122199038,-0.537448884,0.9774568457,0.2817327065,,,
26209,1.3623431787,0.4877545678,,1.4148605105,,,,,,
25435,1.3400690317,0.5246610612,2.9444944462,1.3294345215,2.5900294046,,,,,
21614,-0.124965108,0.1856793555,-0.219551002,-0.363087765,-0.19050899,,,,,
"""

pulphe = 'share_pulmpheno_flags.csv'
outfname = 'share_pulmpheno.phe'
ped = readPed()
f = file(pulphe,'rb')
outf = file(outfname,'w')
head = None
delim = ','
for s in f:
   ls = s.strip().split(delim)
   if not head:
         head = ls[:-3] # drop flags
         outf.write(' '.join(head))
         outf.write('\n')
   else:
      shareid = ls[0]
      iid,famid,pa,ma,gender,affection=ped[shareid]
      ls.insert(0,famid) # to make a phe file!
      outf.write(' '.join(ls))
      outf.write('\n')
outf.close()

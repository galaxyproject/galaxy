#!env python
"""
Copyright Ross Lazarus (ross.lazarus@gmail.com) September 2011
All rights reserved
Released to you under terms of the LGPL
=========================================
updated 5 september 2011 ross lazarus
GAK! 
miRDEEP2 insists that the format of fasta names is spaceless - so these need to be fixed from mirbase

Update - so just use the ID which is the first part of the fasta sequence name - it searches nicely at mirbase

=========================================
quick hack to split stuff downloaded from mirbase into species and loc files for galaxy

galaxy@omics:/data/galaxy$ head mature.fa 
>cel-let-7 MIMAT0000001 Caenorhabditis elegans let-7
UGAGGUAGUAGGUUGUAUAGUU
>cel-let-7* MIMAT0015091 Caenorhabditis elegans let-7*
UGAACUAUGCAAUUUUCUACCUUAC
>cel-lin-4 MIMAT0000002 Caenorhabditis elegans lin-4
UCCCUGAGACCUCAAGUGUGA
>cel-lin-4* MIMAT0015092 Caenorhabditis elegans lin-4*
ACACCUGGGCUCUCCGGGUAC
>cel-miR-1* MIMAT0020301 Caenorhabditis elegans miR-1*
CAUACUUCCUUACAUGCCCAUA

and

galaxy@omics:/data/galaxy$ head hairpin.fa 
>cel-let-7 MI0000001 Caenorhabditis elegans let-7 stem-loop
UACACUGUGGAUCCGGUGAGGUAGUAGGUUGUAUAGUUUGGAAUAUUACCACCGGUGAAC
UAUGCAAUUUUCUACCUUACCGGAGACAGAACUCUUCGA
>cel-lin-4 MI0000002 Caenorhabditis elegans lin-4 stem-loop
AUGCUUCCGGCCUGUUCCCUGAGACCUCAAGUGUGAGUGUACUAUUGAUGCUUCACACCU
GGGCUCUCCGGGUACCAGGACGGUUUGAGCAGAU
>cel-mir-1 MI0000003 Caenorhabditis elegans miR-1 stem-loop
AAAGUGACCGUACCGAGCUGCAUACUUCCUUACAUGCCCAUACUAUAUCAUAAAUGGAUA
UGGAAUGUAAAGAAGUAUGUAGAACGGGGUGGUAGU
>cel-mir-2 MI0000004 Caenorhabditis elegans miR-2 stem-loop
"""
import sys
import os
import time

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


loc_header="""# loc file automatically generated from mirbase data
# by %s
# at %s
# Idea is to separate out all mirs by species
# no dbkey available of course so 
# format is dumb - tab separated rows with organism name, value, loc path
# where loc path is constructed from a parameter passed in to %s and the generated file name
# talk about kludge...
"""

if len(sys.argv) < 3:
    print '##error: mir_species.py requires a fasta mirbase file as the first parameter and the future loc file datapath as the second'
    sys.exit(1)
progname = os.path.basename(sys.argv[0])
infname = sys.argv[1]
locpath = sys.argv[2]
assert os.path.isdir(locpath),'##Error: %s cannot find a directory called %s' % (progname,locpath)
assert os.path.isfile(infname),'##Error: %s cannot open supplied fasta file %s' % (progname,infname)
fasta = open(infname,'rb').readlines()
species = [' '.join(x.split(' ')[2:4]) for x in fasta if x.startswith('>')]
species = list(set(species))
species.sort()
counts = {} # mir count for each species for a fancy loc file name
outfnames = ['%s.%s' % (x.replace(' ','_'),infname) for x in species]
outfiles = [open(x,'w') for x in outfnames]
outdict = dict(zip(species,outfiles))
seqname = None
seq = None
spec = None
for row in fasta:
    if row.startswith('>'):
        if seq:
           counts.setdefault(spec,0)
           counts[spec] += 1
           f = outdict.get(spec)
           f.write('%s\n%s' % (seqname.split(' ')[0],''.join(seq)))
        seq = []
        seqname = None
        spec = None
        spec = ' '.join(row.split(' ')[2:4]) 
        seqname = row.rstrip()
    else:
        seq.append(row)
if seq: # last one
   counts.setdefault(spec,0)
   counts[spec] += 1
   f = outdict.get(spec)
   f.write('%s\n%s\n' % (seqname.replace(' ','_'),''.join(seq)))
for f in outdict.values():
    f.close()
# make loc file
fname = os.path.basename(infname)
locname = '%s_miR_fasta.loc' % os.path.splitext(fname)[0]
f = open(locname,'w')
f.write(loc_header % (progname,timenow(),progname))
for i,species in enumerate(species):
    fname = os.path.basename(outfnames[i])
    ofn = os.path.join(locpath,fname)
    row = [species,'%s (%d mirs)' % (species,counts[species]),ofn]
    f.write('\t'.join(row))
    f.write('\n')
f.close()
print '%s done at %s' % (progname,timenow())
print 'Move the %s file generated to your galaxy root tool-data/ directory' % locname
print 'and add it to your galaxy root tool_data_table_conf.xml file'
print 'You will need to restart Galaxy to make it available'

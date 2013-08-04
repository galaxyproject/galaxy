"""pb to haploview

 Linkage data should be in the Linkage Pedigree (pre MAKEPED) format, with columns of family, individual,
 father, mother, gender, affected status and genotypes. The file should not have a header line
 (i.e. the first line should be for the first individual, not the names of the columns).
 Please note that Haploview can only interpret biallelic markers - markers with greater than two
 alleles (e.g. microsatellites) will not work correctly. A sample line from such a file might look something like

3	12	8	9	1	2		1 2	3 3	0 0	4 2
(a)	(b)	(c)	(d)	(e)	(f)		(------------g-----------)

(a) pedigree name
    A unique alphanumeric identifier for this individual's family.
    Unrelated individuals should not share a pedigree name.
(b) individual ID
    An alphanumeric identifier for this individual. Should be unique within his family (see above).
(c) father's ID
    Identifier corresponding to father's individual ID or "0" if unknown father.
    Note that if a father ID is specified, the father must also appear in the file.
(d) mother's ID
    Identifier corresponding to mother's individual ID or "0" if unknown mother
    Note that if a mother ID is specified, the mother must also appear in the file.
(e) sex
    Individual's gender (1=MALE, 2=FEMALE).
(f) affectation status
    Affectation status to be used for association tests (0=UNKNOWN, 1=UNAFFECTED, 2=AFFECTED).
(g) marker genotypes
    Each marker is represented by two columns (one for each allele, separated by a space)
    and coded 1-4 where: 1=A, 2=C, 3=G, T=4. A 0 in any of the marker genotype position (as in the the genotypes for the third marker above) indicates missing data. 

It is also worth noting that this format can be used with non-family based data. Simply use
a dummy value for the pedigree name (1, 2, 3...) and fill in zeroes for father and mother ID.
It is important that the "dummy" value for the ped name be unique for each individual.
Affectation status can be used to designate cases vs. controls (2 and 1, respectively).

Marker Information File

    The marker info file is two columns, marker name and position.
    The positions can be either absolute chromosomal coordinates or relative positions.
    It might look something like this:

    
    marker01 190299
    marker02 190950
    marker03 191287
    

    An optional third column can be included in the info file to make additional notes for specific SNPs.
    SNPs with additional information are highlighted in green on the LD display.
    For instance, you could make note that the first SNP is a coding variant as follows:

marker01 190299 CODING_SNP
marker02 190950
marker03 191287
    


"""

__version__ = '$Revision: 1.2 $'
__date__ = '$Date: 2005/07/15 20:54:41 $'

import string,sys,os,getopt,copy,optparse

missing = ['N','n','.','?']
alleletran = {'0':'0','N':'0', 'A':'1','C':'2','G':'3','T':'4','1':'1','2':'2','3':'3','4':'4','+':'1','-':'2','X':'0'}  
lettertran = {'0':'0','1':'A','2':'C','3':'G','4':'T'} 
try:
    ps = os.path.sep
except:
    ps = '/'
progname = myname = sys.argv[0].split(ps)[-1]


class Error(Exception):
    """Exception raised for errors in the input.
    Attributes:
         message -- explanation of the error
    """

    def __init__(self,message):
        self.message = message


def getfromfile(infname):
    """
    """
    try:
        f = open(infname,'r')
        fl = f.readlines()
        f.close()
    except:
        raise Error('%s:getfromfile error: Unable to open/read ped file %s' % (progname,infname))
    if len(fl) < 2:
        raise Error('%s:getfromfile error: ped file %s has 2 or less lines' % (progname,infname))
    return fl

    
def makepreped(fl=[],usepop=[], cases=[],maplines=[]):
     """read pb, construct fake pedigree and map
     updated march 2011 to require an ordered map file
     """
     mapres = []
     mappos = {}
     idpos  = {}
     pedres = []
     locusa = {}
     annores = [] # for annovar 1000g lookup
     maps = [x.strip().split('\t') for x in maplines]
     rs = [x[1] for x in maps]
     offsets = [x[3] for x in maps]
     chroms = [x[0] for x in maps]
     rslookup = dict(zip(rs,range(len(rs))))
     for linenum, l in enumerate(fl):
         if linenum > 0:
             ll = l.strip().split()
             if len(ll) >= 4: # must have locus,id,a1,a2
                 locus,id,a1,a2 = ll[:4]
                 assert rslookup.get(locus,None) <> None,'Cannot find locus %s in supplied map file - rs = %s' % (locus,rs)
                 if len(usepop) == 0 or id[0] in usepop: # filter on those first letters
                     if len(a1) > 1:
                         a1 = "+" # indel?
                     if len(a2) > 1:
                         a2 = "+"
                     try:
                         a1 = alleletran[a1]
                         a2 = alleletran[a2]
                     except:
                         s = 'Unable to translate a1 %s a2 %s for id %s' % (a1,a2,id)
                         print s
                     if not locusa.has_key(locus):
                         locusa[locus] = []
                     if not a1 in missing :
                         if not a1 in locusa[locus]:
                             locusa[locus].append(a1)
                     if not a2 in missing :
                         if not a2 in locusa[locus]:
                             locusa[locus].append(a2)
                     if not mappos.has_key(locus):
                         mappos[locus] = 0
                     if not idpos.has_key(id):
                         idpos[id] = {}
                     if not idpos[id].has_key(locus):
                         idpos[id][locus] = (a1,a2)
                     else:
                         s = 'Duplicate locus/id at line %d for %s/%s' % (linenum,locus,id)
                         print s
             else:
                 s = 'Dud line # %d = %s' % (linenum,l)
                 print s
     s = 'Processed %d lines, %d ids and %d markers' % (linenum,len(idpos.keys()),len(mappos.keys()))
     print s
     for i,snp in enumerate(rs):
         s = '%s  %s' % (snp,offsets[i])
         mapres.append(s)
         s = '%s\t%s\t%s\t%s\t%s\t%s' % (chroms[i],offsets[i],offsets[i],lettertran[locusa[snp][0]],lettertran[locusa[snp][1]],snp)
         annores.append(s)
     famid = 0
     for id in idpos:
         famid += 1
         if id[0] in cases:
             affected = '2'
         else:
             affected = '1'
         ped = ['%d' % famid,'1','0','0','1',affected] # fake a pedigree
         for snp in rs:
             a1 = a2 = 'N'
             try:
                 a1,a2 = idpos[id][snp] # add genotypes
             except:
                 print 'No genotypes found for id %s snp %s' % (id,snp)
             #a1 = locusa[snp].index(a1) + 1
             #a2 = locusa[snp].index(a2) + 1
             ped.append('%s %s' % (a1,a2))
         pedres.append(' '.join(ped)) # fake the premakeped line
     return pedres,mapres,annores
     
def opedtopb(pb,ped,map):
    """ file version - no mo zope
    """
    assert os.path.isfile(pb),'# opedtopb cannot read supplied ped file %s' % pb
    pbf = open(pb,'r')
    pbl = pbf.readlines()
    assert len(pbl) > 1, '%s: file  %s contains 1 or less lines' % (progname,pb)    
    pedres,mapres = makepreped(fl=pbl,usepop=[], cases=[])
    pf = open(ped,'w')
    pf.write('\n'.join(pedres))
    pf.write('\n')
    pf.close()
    mf = open(ped,'w')
    mf.write('\n'.join(mapres))
    mf.write('\n')
    mf.close()

def howtouse():
    """
    """
    print 'python %s -p [prettybase file] -c [list of id prefixes for cases] -u [list of id prefixes to use]' % myname
    print 'converts a pb file into a pre makeped and map files for haploview'
    sys.exit(0)

def main():
    """
    """
    caseprefixes = useprefixes = []
    pedname = None
    mapname = None
    op = optparse.OptionParser()
    op.add_option('-m', '--map', default=None)
    op.add_option('-p', '--prettybase', default=None)
    op.add_option('-c', '--caseprefixes', default=None)
    op.add_option('-u', '--useprefixes', default=None)
    op.add_option('-o', '--outped', default=None)
    opts, args = op.parse_args()
    assert opts.prettybase <> None, 'No input -p prettybase - try -h for options help'   
    assert opts.map <> None, 'Must have a proper map for this data with the -m parameter'
    pbf = os.path.split(opts.prettybase)[-1]
    pbf = os.path.splitext(pbf)[0]
    if opts.outped == None:
        outped = '%s.ped' % pbf
    else:
        outped = opts.outped
    outhaplomapname = '%s.markerinfo' % pbf
    outanno = '%s.annores' % pbf
    if opts.caseprefixes:
        caseprefixes = map(None,opts.caseprefixes)
        print '## case prefixes = ',caseprefixes
    else:
        caseprefixes = []
    if opts.useprefixes:
        useprefixes = map(None,opts.useprefixes)
        print '## use prefixes = ',useprefixes
    else:
        useprefixes = []
    try:
        pblines = getfromfile(opts.prettybase)
    except Error,e:
        print e.message
        sys.exit()
    print 'read %d pb lines' % len(pblines)
    try:
        maplines = getfromfile(opts.map)
    except Error,e:
        print e.message
        sys.exit()
    print 'read %d map lines' % len(maplines)
    pedres,mapres,annores = makepreped(pblines,useprefixes,caseprefixes,maplines)
    aline = len(pedres[0].split())
    nmarkers = (aline-6)/2
    print 'nmarkers in new pedfile = %d; in map file = %d' % (nmarkers,len(mapres))
    f = file(outhaplomapname,'w')
    f.write('\n'.join(mapres))
    f.write('\n')
    f.close()
    f = file(outped,'w')
    f.write('\n'.join(pedres))
    f.write('\n')
    f.close()
    f = file(outanno,'w')
    f.write('\n'.join(annores))
    f.write('\n')
    f.close()



if __name__ == '__main__':
     main()


               

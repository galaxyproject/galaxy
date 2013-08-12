# rgEigMerge
# for rgenetics
# ross lazarus me fecit 24 december 2007
# released under the LGPL
# galaxy tool to merge multiple eigenstratgeno files
# so (for example) hapmap outgroups can be added to eigenstrat plots
# to give a sense of scale
# idea from a slide Lon Cardon showed at BioC2007
# tested initially with hapmap data and framingham share dataz
#
# seems more elegant to join existing eigenstrat files
# rather than do the joining at the ped file because of the desire to
# maintain the population name for each sample in
# a single ped file

import sys,os,array,time
#from rgEigMerge_code import doImport
#def doImport(import_path,base_name,outhtml,title)

progname = os.path.split(sys.argv[0])[1]

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


class eigenMerge:
    """class to merge multiple eigenstrat format files
    """
    
    def __init__(self, logf = None, destdir="/foo/bar", sourcedir="/bar/foo", basenames=[], outroot=""):
        """
        take a list of eigenstrat format file basenames and merge them - used for outgroups from
        hapmap for eigenstrat plots
        """
        self.maps = []
        self.eigs = []
        self.indivs = []
        self.sourcedir = sourcedir
        self.destdir = destdir
        self.logf = logf
        self.basenames = basenames
        self.outroot = outroot
        for basename in basenames:
            self.readEig(basename)
        self.postRead()
        
    def readEig(self, basename="example"):
        """read this eigenstrat format set of files 
        """        
        eigroot = os.path.join(self.sourcedir,basename)
        eigf = '%s.eigenstratgeno' % eigroot
        mapf = '%s.map' % eigroot
        indf = '%s.ind' % eigroot
        f = file(indf,'r')
        indiv = []
        for l in f:
            ll = l.strip().split() # id gender status
            status = ll[2]
            ll[2] = '%s_%s' % (basename,status) # fix for combined plots
            indiv.append(' '.join(ll))
        f.close()
        mymap = []
        f = file(mapf,'r')
        for l in f:
            if len(l.strip()) > 0:
                row = l.strip().split()
                try:
                    ipos = int(row[3])
                except: # some framingham genos have ND !
                    ipos = None
                mymap.append((row[0],ipos,row[1])) # chrom, offset, rs so we can order by chrom position
        f.close()
        rslist = [x[2] for x in mymap] # chrom rs gpos offset in original order of this file
        nrs = len(mymap)
        eig = {}
        f = file(eigf,'r')
        for lnum,l in enumerate(f):
            if (lnum+1) % 100000 == 0:
                print 'at line %d in file %s' % (lnum,eigf)
            rs = rslist[lnum] # map file corresponds to the genotype order
            ll = map(None,l.strip()) # make a list of genotype codes per subject
            eig[rs] = array.array('c',ll) # append an efficient representation of eigenstrat geno codes
        f.close()
        self.indivs.append(indiv) # save for writing out
        self.maps.append(mymap)
        self.eigs.append(eig)
        

    def postRead(self):
        """have lists of ind,map and eig
        Note that map has none for position for some snps - we ignore all of these.
        
        check rectangularity and ensure correct major allele assignment
        after reading all the ped files - rationalise the rslist
        so we have the lowest common denominator - we don't want missingness by sample
        because that will bias the PCA !?
        note maps have been changed to be chrom offset rs       
        """
        nmaps = len(self.maps)
        rsdict = {}
        maxmaplen = -9
        for n,amap in enumerate(self.maps): # find longest map
            if len(amap) > maxmaplen:
                bigmap = amap
                maxmaplen = len(amap)
                bigmapn = n
        rslist = [x[2] for x in bigmap if x[1] <> None] # rs in order if annotated with a position
        ubigmap = [x for x in bigmap if x[1] <> None] # always ignore these bad position snps
        urslist = [x[2] for x in ubigmap]
        rsdict = dict(zip(urslist,ubigmap)) # for fast lookups
        for n,amap in enumerate(self.maps): # need to ensure that all rs are in all files
            if n <> bigmapn: # ignore the largest map
                maprs = [x[2] for x in amap if x[1] <> None] # always ignore these bad position snps
                uamap = [x for x in amap if x[1] <> None]
                myrsdict = dict(zip(maprs,uamap)) # dict keyed 
                # check this file has all rs in rsdict
                rk = rsdict.keys() # do this for every new map as it gets smaller
                for rs in rk:
                    if not myrsdict.get(rs,None): # not in this file so we have to drop it
                        del rsdict[rs]
        rsv = rsdict.values() # all the map entries
        rsv.sort()
        rslist = [x[2] for x in rsv if x[1] <> None]
        print 'after reading %d maps, we have %d rs in common' % (nmaps,len(rslist))
        finalmap = [rsdict[x] for x in rslist] # in genomic order
        self.commonmap = ['%s\t%s\t0\t%d\n' % (x[0],x[2],x[1]) for x in finalmap]
        # lowest common denominator of rs numbers ready to write as a map file
        self.rslist = rslist # in genomic order - we need to make sure each eig[] is written out in this order

    def eigenRowGenerator(self):
        """ generator to iterate over rows of the final output
        eigenstrat geno file by ensuring all input files are output in the right order
        in terms of the final map and indiv files.
        """
        for rs in self.rslist: # ensure order is fixed
            outeig = array.array('c',[])
            for n,myeig in enumerate(self.eigs): # ensure correct output order for markers
                row = myeig.get(rs,None)
                if row: # it should exist!
                    outeig += row # concatenate arrays for efficiency
                else:
                    print '## bad news, cannot find rs %s in the %d eigen' % (n,rs)
                    ok = false
            yield ''.join(outeig)

    def note(self,kind='map',outfname=None,n=0):
        s = 'writeOut %s: Now writing %d rows to %s file %s\n' % (timenow(),n,kind,outfname)
        print s
        self.logf.write(s)
        
            
    def writeOut(self,basename='All'):
        """Write the amalgamated files
        """
        outfname = os.path.join(self.destdir,'%s.eigenstratgeno' % self.outroot)
        outf = file(outfname,'w')
        res = self.eigenRowGenerator()
        for x in res: # yes, this is slower than outf.write('\n'.join(res))
            # but that fails with framingham because the file is too big for a python string!
            outf.write(x)
            outf.write('\n')
        outf.close()
        res = []
        for ind in self.indivs: # concatenate in right order 
                res += ind # the eigenstrat individual file
        outfname = os.path.join(self.destdir,'%s.ind' % self.outroot)
        outf = file(outfname,'w')
        self.note(kind='individual', outfname=outfname,n=len(self.commonmap))
        outf.write('\n'.join(res)) # not too big we hope
        outf.write('\n')
        outf.close()
        outfname = os.path.join(self.destdir,'%s.map' % self.outroot)
        outf = file(outfname,'w')
        self.note(kind='map file', outfname=outfname,n=len(self.commonmap))
        outf.write(''.join(self.commonmap))
        outf.close()
    
def process():
    """
    called as python2.4 rgEigMerge.py outfile base_name "joinbasenames" sourcedir file_type_dir logfile
    """
    nparam = 7
    if len(sys.argv) < 7:
        print >> sys.stdout, '%s expected %d params, got %d %s' % (progname,nparam,len(sys.argv),sys.argv)
        print 'eg python2.4 %s outfile base_name "ineig1 ineig2" sourcdir eigenstrat logfile' % (progname)
    outfile = sys.argv[1]
    base_name = sys.argv[2]
    joinbasenames = sys.argv[3].split()
    sourcedir = sys.argv[4]
    file_type_dir = sys.argv[5]
    logf = file(sys.argv[6],'w')
    em = eigenMerge(logf=logf,destdir=file_type_dir,sourcedir=sourcedir,basenames=joinbasenames,outroot=base_name)    
    em.writeOut(basename=base_name)
    # doImport(file_type_dir, base_name, outfile, base_name)
    # doImport(import_path,base_name,outhtml,title)


if __name__ == "__main__":
    process()

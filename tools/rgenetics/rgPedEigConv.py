"""
## class oct 2007 ross lazarus
## changed to use arrays rather than lists
## for snp vectors to save some space and maybe some time
## this is slow compared to convertf but doesn't require
## a whole slew of configuration parameters in a text file :)
## linkage format ped file to eigenstrat
## ross lazarus me fecit august 14 2007
## convertf seems to want a 7 column pedigree
## eigenstrat format is transposed with 1 line per snp and
## number of ref alleles for each marker for each subject
## subjects are in indiv file as sampleid gender label
## markers are in a linkage pedigree map file format
## how to avoid holding entire ped file in ram?
## read a line,
## need an allele count
## start by assuming first seen allele is major, then reverse if wrong
"""
import sys,os,shutil,array,time

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


def readMap(fprefix="example"):
    """
    """
    map = []
    f = file('%s.map' % fprefix,'r')
    for l in f:
        ll = l.strip().split()
        if len(ll) >= 4:
            map.append((ll[:4]))
    return map

def majAllele(adict={'A':20,'C':100}):
    """return commonest allele
    """
    ak = adict.keys()
    if len(ak) == 1: # mono
        return ak[0] # is major allele
    m = None
    maxn = -9
    for k,n in adict.iteritems():
        if n > maxn:
            maxn = n
            m = k
    return m



class convertPedEigen:

    def __init__(self,fprefix="example",outfroot="example", linkage=True, logf = None, fo=True,oo=False,
        labels=['FounderNonAff','FounderAff','OffspringNonAff','OffspringAff']):
        """
         def convertPedEigen(fprefix="example",outfroot="example", linkage=True, logf = None, fo=True,oo=False,
          labels=['FounderNonAff','FounderAff','OffspringNonAff,OffspringAff']):
        """
        missing = ['N','0','.']
        # eigenstrat codes
        emissval = '9'
        ehet = '1'
        ehom1 = '0'
        ehom2 = '2'
        swapdict = {ehom1:ehom2,ehom2:ehom1,ehet:ehet,emissval:emissval} # if initial ref allele was wrong, use these to swap
        mdict = dict(zip(missing,missing))
        f = file('%s.ped' % fprefix,'r')
        if linkage: # read map file
            map = readMap(fprefix)
            rslist = [x[1] for x in map] # get rs numbers
            outmap = file('%s.map' % outfroot,'w')
            maps = ['\t'.join(x) for x in map]
            maps.append('')
            logf.write('rgPedEigConv.py %s: Writing map file\n' % (timenow()))
            outmap.write('\n'.join(maps))
        else:
            head = f.next().strip()
            rslist = head.split()
        nrs = len(rslist) # number of markers
        elen = 2*nrs + 6 # expected # elements on each line
        logf.write('rgPedEigConv.py %s: found %d for nrs\n' % (timenow(),nrs))
        eig = {}
        eig['founders'] = [array.array('c',[]) for x in xrange(nrs)] # marker rows, subject cols
        eig['offspring'] = [array.array('c',[]) for x in xrange(nrs)] # marker rows, subject cols
        adicts = [{} for x in xrange(nrs)] # count of alleles in a dict for each marker
        refallele = [None for x in xrange(nrs)] # list of first observed alleles
        nsubj = 0
        indiv = {'founders':[],'offspring':[]}
        for lnum,l in enumerate(f):
            ll = l.strip().split()
            if (lnum+1) % 200 == 0:
                logf.write('rgPedEigConv.py %s: Processing line %d\n' % (timenow(),lnum+1))
            if len(ll) < elen: # ? short ?
                logf.write('rgPedEigConv.py %s: Line %d is %d long, expected %d\n' % (timenow(),lnum,len(ll),elen))
            else:
                nsubj += 1
                sid = '%s_%s' % (ll[0],ll[1])
                isFounder = isOff = False
                status = labels[0] # founder unaff
                if ll[2] <> '0' and ll[3] <> '0': # has parent ids
                   iclass = 'offspring'
                   status = labels[2] # unaffected offspring
                   if ll[5] == '2':
                        status = labels[3] # affected offspring
                else:
                   iclass = 'founders'
                   if ll[5] == '2':
                        status = labels[1] #change from unaff to aff founder label
                gender = 'M'
                if ll[4] == '2':
                    gender = 'F'
                indiv[iclass].append('%s %s %s' % (sid,gender,status)) # for the ind file
                for snp in xrange(nrs):
                    g1,g2 = ll[2*snp + 6],ll[2*snp + 7] # pair of genos
                    if mdict.get(g1,None) or mdict.get(g2,None): # one or both missing
                        esnp = emissval # missing value
                    else:
                        if not refallele[snp]:
                            refallele[snp] = g1 # first one we saw!
                        for g in (g1,g2):
                            if adicts[snp].get(g,None): # bump
                                adicts[snp][g] += 1
                            else:
                                adicts[snp][g] = 1 # first time
                        if g1 == g2: # hom
                            if g1 == refallele[snp]:
                                esnp = ehom2 # 2 copies of current reference allele
                            else:
                                esnp = ehom1 # no copies
                        else:
                            esnp = ehet # het - always has one copy of reference allele
                    eig[iclass][snp].append(esnp) # append the eigenstrat geno code for this new subject
        logf.write('rgPedEigConv.py %s: Now checking major allele assignment and fixing as needed\n' % timenow())
        for snp in xrange(nrs): # now check to see if reference = major allele
            major = majAllele(adicts[snp])
            if major <> refallele[snp]: # either None or we need to change all the codes
                if major <> None:
                  for iclass in eig.keys():
                    for i in range(len(eig[iclass][snp])):
                        if eig[iclass][snp][i] <> emissval:
                            eig[iclass][snp][i] = swapdict[eig[iclass][snp][i]]
        self.eig = eig
        self.indiv = indiv
        self.fo = fo
        self.oo = oo
        self.outfroot = outfroot
        self.nrs = nrs
        self.fprefix = fprefix
        self.logf = logf


    def writeOut(self):
        outclass = ['offspring','founders'] # do everyone if not one or other
        if self.fo: # do founders
               outclass = ['founders',]
        if self.oo: # do offspring only
               outclass = ['offspring',]
        res = []
        for iclass in outclass:
               res += [''.join(x) for x in self.eig[iclass]] # convert to rows
        res.append('\n')
        res = '\n'.join(res) # convert to write
        outfname = '%s.eigenstratgeno' % self.outfroot
        outf = file(outfname,'w')
        self.logf.write('rgPedEigConv.py %s: Now writing %d columns of genotype output to %s\n' % (timenow(),self.nrs,outfname))
        outf.write(res)
        outf.close()
        res = []
        for iclass in outclass:
               res += self.indiv[iclass] # the eigenstrat individual file
        outfname = '%s.ind' % self.outfroot
        outf = file(outfname,'w')
        self.logf.write('rgPedEigConv.py %s: Now writing %d rows to individual file %s\n' % (timenow(),len(res),outfname))
        outf.write('\n'.join(res))
        outf.close()
        outfname = '%s.map' % self.outfroot
        mapf = file('%s.map' % self.fprefix,'r')
        res = mapf.read()
        outf = file(outfname,'w')
        self.logf.write('rgPedEigConv.py %s: Now writing %d rows to mapfile %s\n' % (timenow(),len(res),outfname))
        outf.write(res)
        outf.close()

if __name__ == "__main__":
    """ shall we run the smartpca while we're here?

     smartpca.perl -i fakeped_100.eigenstratgeno -a fakeped_100.map -b fakeped_100.ind -p fakeped_100 -e fakeped_100.eigenvals -l 
        fakeped_100.eigenlog -o fakeped_100.eigenout

    called as

    Updated oct 4 - converters now need to clone the behaviour of creating a new
    rgenetics data file which is really an html file
      

    <command interpreter="python2.4">
    rgPedEigConv.py $i.extra_files_path/$i.metadata.base_name $i.metadata.base_name
    "$title" $outfile.files_path $outfile $founders $offspring "$uf" "$af" "$uo" "$ao"
    </command>


    """
    if len(sys.argv) < 11:
        print 'Need an input linkage ped file root and some flags for offspring and founders'
        print 'Given that, will write a set of eigenstrat input files'
        #print 'eg python2.4 rgPedEigConv.py '
        sys.exit(1)
    ename = sys.argv[2]
    title = sys.argv[3].replace(' ','_')
    outpath = sys.argv[4]
    try:
        os.makedirs(outpath)
    except:
        pass
    logfile = sys.argv[5]
    foundonly = sys.argv[6].lower() == 'true'
    offonly = sys.argv[7].lower() == 'true'
    labels = sys.argv[8:12] # eg  labels=['FounderNonAff','FounderAff','OffspringNonAff,OffspringAff']
    lf = file(logfile,'w')
    froot = sys.argv[1]
    outfroot = os.path.join(outpath,ename)  
    f = file('%s.ped' % froot,'r')
    l1 = f.next().strip().split()
    l2 = f.next().strip().split()
    f.close()
    if len(l1) <> len(l2): # must be fbat
        linkage = False
    else:
        linkage = True
    s = '## rgPedEigConv.py: froot=%s, outfroot=%s, logf=%s\nargv = %s\n' % (froot, outfroot, logfile, sys.argv)
    print >> sys.stdout, s # so will appear as blurb for file
    lf.write(s)
    c = convertPedEigen(fprefix=froot,outfroot=outfroot,linkage=linkage,logf = lf,
                        fo = foundonly, oo = offonly, labels=labels)
    c.writeOut()
    lf.close()
    
    

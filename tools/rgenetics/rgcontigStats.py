# contigStats.py
# copyright ross lazarus
# released under the LGPL
# for the rgenetics project
# august 2011
# counts N50 etc for contigs 
# from an assembly

import re
import sys
import os
import optparse
import bisect



FDELIM = '>' # start of fasta id entry

class contigStats:
    """
    >>> r = re.compile('[gc]',re.I)
>>> x = r.findall('gCAbcgC')
>>> x
['g', 'C', 'c', 'g', 'C'] 
    """
    
    def __init__(self,opts=None):
        """setup to count N50 etc in a list of fasta contigs
        """
        self.opts = opts
        self.fasta = opts.fastafiles
        for f in self.fasta:
            assert os.path.isfile(f),'##ERROR: contigStats cannot open supplied fasta file %s' % f
        self.gcall = None
        self.maxlen = None
        self.nseq = None
        self.totseqlen = None
        self.outputdir=opts.outputdir
        self.plots=opts.plots
        self.gc = re.compile('[gc]',re.I) # ignore case
        self.stats = []
        self.seqdict = {} # keyed by fasta name
        self.countSeq()
        if len(self.seqdict) > 10:
            self.calcStats()
        else:
            print >> sys.stderr,'##ERROR: contigStats found fewer than 10 sequences in the input files %s - cannot calculate stats' % self.fasta
            sys.exit(1)
        if opts.plots:
            self.plotHist()
            
    def plotHist(self,ncuts=100):
        """ histogram and cumulative histogram of seqlen
        useless really...
        """
        try:
            import rpy
        except:
            print >> sys.stderr,'##ERROR: plotHist unable to import rpy - cannot plot'
            return 1
        chist = os.path.join(self.outputdir,'cumlenhistogram.pdf')
        ahist = os.path.join(self.outputdir,'lenhistogram.pdf')
        lvec = self.seqdict.values()
        lvec = [len(x) for x in lvec] # parse out sequence length
        rpy.r.assign("lvec",lvec)
        rpy.r("pdf(file='%s')" % ahist) 
        rpy.r('h=hist(lvec,main="Distribution of contig lengths",xlab="Contig Length",ylab="Count",breaks=100,col="maroon")')
        rpy.r('h')
        rpy.r("dev.off()")
        rpy.r('h$counts=cumsum(h$counts)')
        rpy.r('h$density=cumsum(h$density)')
        rpy.r('h$intensities=h$density')
        rpy.r("pdf(file='%s')" % chist) 
        rpy.r('plot(h, freq=TRUE, main="Cumulative distribution of contig lengths",xlab="Contig Length",ylab="Cumulative Count",col="maroon")')
        rpy.r("dev.off()")               
        
    def countGC(self,s=''):
        """ return gc fraction of sequence s
        """
        assert len(s) > 0,'##ERROR: countGC got an empty sequence string'
        x = self.gc.findall(s) # get number of gc in contig
        gc = len(x)
        l = float(len(s))
        return (gc,100.0*gc/len(s)) # gc percentage
    

    def countSeq(self):
        """ calculate gc and length for all contigs
        """
        seqdict = {}
        contig = ''
        
        def countS(contig='',id=None):
            """ add contig to dict
            """
            if id == None:
                print >> sys.stderr,'##Error contigStats getStats: file %s does not seem to be a valid fasta with %s delimiting sequence names?' % (f,FDELIM)
                sys.exit(1)
            if seqdict.get(id):
                print >> sys.stderr, '##ERROR: contigStats found duplicate fasta id %s in file %s' % (id,f)
                sys.exit(1)
            else:
                seqdict[id] = contig

            
        for fname in self.fasta:
            f = open(fname,'r')
            id = None
            contig = ''
            for row in f.readlines():
                row = row.strip()
                if row.startswith(FDELIM):
                    if len(contig) > 0: # deal with previous contig
                        countS(contig=contig,id=id)
                        contig = ''
                    id = row[1:] # TODO? first non whitespace is end of id
                else:
                    if row:
                        if id == None:
                            print >> sys.stderr,'##Error contigStats getStats: file %s does not seem to start with %s - is it a valid fasta?' % (f,FDELIM)
                            sys.exit(1)
                        contig += row
            if len(contig) > 0: # deal with last contig
                countS(contig=contig,id=id)
        self.seqdict = seqdict
        
    def calcStats(self):
        """ do calculations after counting fasta files
        """
        ncuts = 20 # dodeciles eg
        N50 = ncuts/2
        N75 = ncuts/4
        N25 = 3*ncuts/4
        ckeys = self.seqdict.keys()
        res = [] # list of (length, gc frac)
        totlen = []
        tlen = 0
        gctot = 0 # for overall GC estimate
        min = 99999999
        for k in ckeys:
            s = self.seqdict[k]
            slen = len(s)
            if slen < min:
                min=slen
            tlen += slen
            gcc,gcp = self.countGC(s)
            res.append((slen,gcp))
            gctot += gcc
        self.minlen = min
        self.gcall = gctot*100/float(tlen)
        tfrac = tlen/ncuts # eg dodeciles
        res.sort() # from smallest to largest length
        cum = 0
        for r in res:
            cum += r[0]
            totlen.append(cum)
        self.maxlen = res[-1][0]
        self.nseq = len(res)
        self.totseqlen = tlen
        self.meanseqlen = float(tlen)/self.nseq
        midpoint = self.nseq/2
        if self.nseq % 2 == 0: # median edge case
            self.medianseqlen = (res[midpoint][0] + res[midpoint+1][0])/2.0
        else:
            self.medianseqlen = res[midpoint][0]
        cuts = [tfrac*x for x in range(ncuts+1)] # 0..tlen
        icuts = [bisect.bisect(totlen,x) for x in cuts] # indices in res corresponding to total bp counts in ncuts
        stats = []
        for i in range(ncuts):
            start = icuts[i] # first is zero
            end = icuts[i+1] # last will be tlen
            segment = res[start:end]
            if len(segment) > 0:
                gc = sum([x[1] for x in segment])/len(segment) # mean gc
                minlen = res[start][0] # smallest length for this group = N50 eg
                stats.append((minlen,gc,self.nseq - start))
            else:
                print >> sys.stderr,'##ERROR calcstats: segment length of zero for i=%d; ncuts=%s; icuts=%s,totlen=%s' % (i,ncuts,icuts,totlen)
                sys.exit(1)
        self.stats = stats
        self.n50 = stats[N50][0] # len of relevant cutpoint
        self.n75 = stats[N75][0] # len of relevant cutpoint
        self.n25 = stats[N25][0] # len of relevant cutpoint
            
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        op = optparse.OptionParser()
        a = op.add_option
        a('-f','--fastafiles',default=[],action="append", dest='fastafiles')
        a('-d','--outputdir',default='./') # for plots
        a('-p','--plots',default='')
        a('-o','--outputfile',default='contigStats.xls')
        opts, args = op.parse_args()
        assert opts.fastafiles > [],'##ERROR contigStats requires one or more fasta file paths on the command line passed as -f fastq1,fastq2... '        
        s = contigStats(opts=opts)
        f = open(opts.outputfile,'w')
        w = f.write
        w('#Measure\tValue\n')
        w('contig_count\t%d\n' % s.nseq)
        w('N25\t%d\n' % s.n25)
        w('N50\t%d\n' % s.n50)
        w('N75\t%d\n' % s.n75)
        w('mean_contig_len\t%4.1f\n' % s.meanseqlen)
        w('median_contig_len\t%4.1f\n' % s.medianseqlen)
        w('max_contig_len\t%d\n' % s.maxlen)
        w('min_contig_len\t%d\n' % s.minlen)
        w('mean_contig_gc_pct\t%5.2f\n' % s.gcall)
        f.close()
    else:
        print >> sys.stderr,'##ERROR contigStats requires one or more fasta file paths as parameters'
        sys.exit(1)

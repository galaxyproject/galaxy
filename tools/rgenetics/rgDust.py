"""
rgDust.py
Copyright Ross Lazarus October 2011
All rights reserved but released to you under the LGPL
counts and optionally filters low complexity reads from fasta or bam
TODO add fastq

for low complexity filtering of sequences

python version of idea from 
[Bioc-sig-seq] Low-complexity read filtering/trimming

=========================

Herve Pages hpages at fhcrc.org 
Mon Feb 23 22:24:40 CET 2009
Previous message: [Bioc-sig-seq] Low-complexity read filtering/trimming
Next message: [Bioc-sig-seq] Bioinformatics virtual issue on NGS
Messages sorted by: [ date ] [ thread ] [ subject ] [ author ]
A small correction to my previous algorithm used for computing the
scores. In my previous email I suggested this:

   tnf <- trinucleotideFrequency2(dict0)
   scores <- rowSums(tnf * tnf)

but I think it would be more accurate and closer to the DUST
approach to start penalizing a read when it contains triplets
with frequency >= 2 i.e. the first time a triplet occurs in a
read should not count. This leads to the following code:

   tnf2 <- tnf - 1L
   tnf2[tnf2 < 0] <- 0L
   scores <- rowSums(tnf2 * tnf2)

   > summary(scores)
      Min. 1st Qu.  Median    Mean 3rd Qu.    Max.
      0.00    8.00   12.00   24.59   19.00 1024.00

Now whatever the length of the reads is, they have a chance
to obtain a score of 0, which happens when all triplets in
the read are distinct. This new score is more meaningful IMO.

H.


> Hi Cei,
> 
> Here is a suggestion for question 1).
> 
> DUST seems to have been designed to mask regions in long DNA sequences.
> They count tri-nucleotide frequencies in a 64-nucleotide sliding windows
> so, strictly speaking, the algo doesn't work anymore with short reads.
> In addition your problem seems simpler to me, because, if I understand
> correctly, you don't want to mask regions within the reads, but just
> want to keep or drop the entire read based on its "complexity".
> The notion of "complexity" as defined by DUST could be reused though, by
> applying trinucleotideFrequency() to the DNAStringSet object containing
> the reads, replacing all coefficients in the resulting matrix by its
> square, applying rowSums() to it, and finally using the resulting score
> to filter the reads (high score meaning low complexity):
> 
>   library(ShortRead)
>   rfq <- readFastq("some_path", pattern="s_1_sequence.txt")
>   dict0 <- sread(rfq)
> 
>   tnf <- trinucleotideFrequency(dict0)
>   scores <- rowSums(tnf * tnf)
> 
>   table(scores)  # choose a cut-off value
>   clean_dict <- dict0[scores < cut_off]
> 
> There is one technical problem though: the top-level loop in
> trinucleotideFrequency() is still written in R so that won't work
> for millions of reads. The temporary workaround is to implement
> a vcountPDict-based version of trinucleotideFrequency():
> 
>   trinucleotideFrequency2 <- function(x)
>   {
>     all_triplets <- DNAStringSet(mkAllStrings(c("A", "C", "G", "T"), 3))
>     pd <- PDict(all_triplets)
>     t(vcountPDict(pd, x))
>   }
> 
> trinucleotideFrequency2() will take about 20 seconds on a
> 4-million 35-mers DNAStringSet object.
> 
> I calculated the scores for a set of 4.47 millions unaligned
> 35-mers from a single lane of a real Solexa experiment and got:
> 
>   > summary(scores)
>      Min. 1st Qu.  Median    Mean 3rd Qu.    Max.
>     22.00   49.00   55.00   66.95   63.00 1089.00
> 
>   > dict0[scores >= 200]
>     A DNAStringSet instance of length 63331
>           width seq
>       [1]    35 AAAAAACCAAAACCAAACAAATAAAAACCCCAAAT
>       [2]    35 GATAGATAGATAGATAGATAGATAGGGTAGATAGG
>       [3]    35 GTGTGTGTGTGTGTGTGTGTATGTGTGTGTGCGTT
>       [4]    35 GGTAGGTAGGTAGGTCAGGTAGGTAGGTAGGTAGG
>       [5]    35 TGGTTGGTGTGTGTGTGTGTGTGTGTGTGTGTGTG
>       [6]    35 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
>       [7]    35 GTGTGTCTGTGTGTCTGTGTGTCTGTGTGTGTCTG
>       [8]    35 GTATGTGTGCTTTGTGTGTGTGGTGTGTGTGTGGT
>       [9]    35 GAGAGTGTGTGTGTGAGAGAGAGTGTGTGTGTGAG
>       ...   ... ...
>   [63323]    35 AAAAAAAAAAAAAAAAAAAAACGAAGAAAAAAAAG
>   [63324]    35 AAAAAAAAAAAAAAAAAAAAAAAAAGAAAAGAACA
>   [63325]    35 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
>   [63326]    35 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
>   [63327]    35 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
>   [63328]    35 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
>   [63329]    35 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
>   [63330]    35 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
>   [63331]    35 AAAAAAAGAAAAAAAAAAAAAAAAGAGAAAAAAAA
> 
> Note that 1089 is the score obtained by the poly-As, poly-Cs,
> etc... (1089 = 33^2, this is the highest possible score for a
> 35-mer).
> 
> H.
> 
> 
> Cei Abreu-Goodger wrote:
>> Hi all,
>>
>> I've been playing around with some Solexa small-RNA reads using 
>> ShortRead and Biostrings. I've used the 'trimLRPatterns' function to 
>> remove adapter sequence, and I've been trying to remove low-complexity 
>> sequences with 'srFilter'. I would first really like to congratulate 
>> all the people involved for the great work. There are two situations 
>> in which I would be grateful for some suggestions, though:
>>
>> 1) I have many "low-complexity" reads. Some are simply polyA, polyC, 
>> etc. But some others are runs of "ATATAT" or "CACACACA", etc. 
>> Previously I would have used "dust" on the command line to filter out 
>> this kind of read in a fasta file. Any ideas on how to achieve similar 
>> functionality in the ShortRead world?
>>
>> 2) For some reads I may have a "N-rich" patch inside the read, for 
>> example:
>> AATAAAGTGCTTACAGTGNNNNTNNATNCAATACCG
>>
>> I would ideally like to trim of everything starting at the "N-rich" 
>> part. I was trying to implement something with 'vmatchPattern', but if 
>> I allow for mismatches (for a more flexible search) I will also get 
>> hits starting before the run of Ns.
>>
>> Many thanks,
>>
>> Cei
>>
>>
>>
>> sessionInfo()
>>
>> R version 2.9.0 Under development (unstable) (2009-02-13 r47919)
>> i386-apple-darwin9.6.0
>>
>> locale:
>> C
>>
>> attached base packages:
>> [1] stats     graphics  grDevices datasets  utils     methods   base
>>
>> other attached packages:
>> [1] ShortRead_1.1.39   lattice_0.17-20    BSgenome_1.11.9 
>> Biostrings_2.11.28
>> [5] IRanges_1.1.38     Biobase_2.3.10
>>
>> loaded via a namespace (and not attached):
>> [1] Matrix_0.999375-20 grid_2.9.0
>>
>>
> 

-- 

Program in Computational Biology
Division of Public Health Sciences
Fred Hutchinson Cancer Research Center
1100 Fairview Ave. N, M2-B876
P.O. Box 19024
Seattle, WA 98109-1024

E-mail: hpages at fhcrc.org
Phone:  (206) 667-5791
Fax:    (206) 667-1319

Previous message: [Bioc-sig-seq] Low-complexity read filtering/trimming
Next message: [Bioc-sig-seq] Bioinformatics virtual issue on NGS
Messages sorted by: [ date ] [ thread ] [ subject ] [ author ]
More information about the Bioc-sig-sequencing mailing list
"""


import sys
import os
import time
import optparse
import pysam
import copy


class trinuc():  
    """Based on Herve Pages posts to the BioC list
       This uses very little ram so is slow compared to an inmemory R data structure
       but it's ok for filtering - a 30M/1GB bam takes about 20 minutes on omics
    """
    
    def __init__(self,opts=None,alphabet=['a','c','g','t']):
        """ to get a eg 64 bit vector of trinucleotides
        """
        self.opts = opts
        self.alphabet=alphabet
        tris = []
        for x in alphabet:
             for y in alphabet:
                 for z in alphabet:
                     tris.append('%s%s%s' % (x,y,z))
        self.dicttris = dict(zip(tris,range(len(tris)))) # lookup offset
        self.tris = tris
        self.score = int(opts.score)
        self.seqlen = int(opts.seqlen) # default is 36
        if opts.report:
            self.reportfname = opts.report
        else:
            self.reportfname = 'rgDustCount.xls'
        self.outputfname = opts.output
        self.rejectfname = opts.reject
        self.inputfname = opts.input
        if self.outputfname and self.score:
            self.filtering = True
            if not opts.reject:
                self.rejectfname = '%s_dust_gt_%d.%s' % (opts.output,self.score,opts.informat)
        else:
            self.filtering = False

    def report(self):
        """
        """
        if opts.informat=='bam' or opts.informat=='sam':
            hist = self.dustBam()
        elif opts.informat=='fasta' or opts.informat=="collapsedfasta":
            hist = self.dustFasta()
        elif opts.informat=='fastq':
            hist = self.dustFastq()
        else:
            hist = {'opts.informat not bam, sam, fastq, fasta':0}
            return hist
        res = ['#Complexity\tN\tCumN\tPctl',]
        cumn = 0
        xmax = max(hist.keys())
        nseq = float(sum(hist.values()))
        for x in range(xmax+1):
            n = hist.get(x,0)
            cumn += n
            res.append('%d\t%d\t%d\t%5.2f' % (x,n,cumn,100*(nseq-cumn)/nseq))
        repf = open(self.reportfname,'w')
        s = '\n'.join(res)
        repf.write(s)
        repf.write('\n')
        repf.close()
        return hist
        
    def getMeanScore(self,query = ''):
        """
        complexity in fasta or with long bam sequences. Need median score self.seqlen nt windows to match short read expectations
        """
        scores = []
        cutstart = 0
        qn = len(query)
        if qn > self.seqlen:
            cuts = range(self.seqlen,qn,self.seqlen)
        elif qn <= self.seqlen:
            return self.scoreTris(query) # short sequences will have biased low scores..
        for cut in cuts:
            ss = query[cutstart:cut]
            cutstart += self.seqlen
            if len(ss) >= self.seqlen:
                v = self.scoreTris(ss)
                scores.append(v)
        scores.sort()
        sn = len(scores)
        if sn > 3: # return median score for sequence if > 1
            mid = int(round(sn/2)) - 1 # if sn=2, mid = 0, return mean; if sn=3,mid=1
            if sn % 2 == 0:
                score = (scores[mid]+ scores[mid+1])/2.0
            else:
                score = scores[mid]
        else: # 3,2 or 1 so return mean
            score = float(sum(scores))/sn
        return int(score)
        
    def scoreTris(self,s=''):
        """ return vector count for all possible trinucleotides
        allow 1 occurrence per tri so complex sequences can score 0 
        low complexity will have many of a few so sum square of (count-1) over all trinucleotides
        36bp read = 33 possible triplets = 33**2 = 1089 max score if homopolymer or zero if no repeated trinucleotides
        """
        s = s.lower()
        rowsum = 0
        tris = [0 for x in self.tris] # empty counting list
        for i in range(len(s)-2):
            tri = s[i:(i+3)]
            tri = tri.replace('n','a')
            ntri = self.dicttris[tri]
            tris[ntri] += 1
        for n in tris:
            if n > 1: # allow one of each trinucleotide so can score zero if max complexity
                rowsum += (n-1)**2
        return rowsum
 
    def dustFasta(self):
        """score histogram and optional filter
        """
        input = open(self.inputfname,'r')
        scores = {}
        if self.filtering:
            outf = open(self.outputfname,'w')
            rejectf = open(self.rejectfname,'w')
        fasta = []
        for i,row in enumerate(input):
            if row.startswith('>'):      
                if len(fasta) > 0:
                    s = ''.join([x.strip() for x in fasta]) # one big string
                    v = self.getMeanScore(s)
                    scores.setdefault(v,0)
                    scores[v] += 1
                    if self.filtering:
                        if (v < self.score): # write all below cutoff to score out
                            if seqname:
                                outf.write(seqname)
                            outf.write(''.join(fasta))
                        else:
                            if seqname:
                                rejectf.write(seqname)
                            rejectf.write(''.join(fasta))
                seqname = row # is fasta?
                fasta = []
                continue  
            else:
                fasta.append(row)
        if self.filtering:
            outf.close()
            rejectf.close()        
        return scores

    def dustFastq(self):
        """score histogram and optional filter
        """
        input = open(self.inputfname,'r')
        scores = {}
        if self.filtering:
            outf = open(self.outputfname,'w')
            rejectf = open(self.rejectfname,'w')
        fastq = []
        for i,row in enumerate(input):
            if i % 4 == 0: # start or zero
                if fastq > []:
                    query = fastq[1].strip()
                    v = self.getMeanScore(query)
                    scores.setdefault(v,0)
                    scores[v] += 1
                    if self.filtering:
                        if (v < self.score): # write all below cutoff to score out
                            outf.write(''.join(fastq))
                        else:
                            rejectf.write(''.join(fastq))
                fastq = []
            fastq.append(row)
        if self.filtering:
            outf.close()
            rejectf.close()
        return scores

    def dustBam(self):
        """score histogram and optional filter
        takes about 20 minutes for 30M sequences in a 1GB bam
        25000/sec or so is not so bad...
        """
        samfile = pysam.Samfile( self.inputfname, "rb" )
        scores = {}
        if self.filtering:
           output = pysam.Samfile(self.outputfname, "wb", template=samfile)
           reject = pysam.Samfile(self.rejectfname, "wb", template=samfile)
        for i,read in enumerate(samfile):
            v = self.getMeanScore(read.query)
            scores.setdefault(v,0)
            scores[v] += 1
            if self.filtering:
                if v < self.score:
                    output.write(read)
                else:
                    reject.write(read)
        if self.filtering:
            output.close()
            reject.close()
        samfile.close()
        return scores
        
 
def test(opts=None):
     t = trinuc(opts=opts)
     for x in ['AAAAAACCAAAACCAAACAAATAAAAACCCCAAAT','GGGCTACATGACGGTCCTGTATTTAGCCAGAGGATC','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']:
        v = t.getMeanScore(x)
        print x,v 


if __name__ == "__main__":
    """
    """
    op = optparse.OptionParser()
    a = op.add_option
    a('--input',default=None) # no need for bai
    a('--report',default=None)
    a('--output',default=None)
    a('--reject',default=None)
    a('--score',default='200')
    a('--informat',default='bam')
    a('--test',default=None)
    a('--seqlen',default='36')
    opts, args = op.parse_args()
    t = trinuc(opts=opts)
    if opts.test:
        test(opts=opts)
        sys.exit(0) 
    assert os.path.isfile(opts.input),'## dust runner unable to open supplied input file %s' % opts.input
    hist = t.report()


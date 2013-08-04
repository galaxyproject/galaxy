"""
rlazarus@ross-hp:~/rgalaxy$ cat ~/Downloads/miRNA_bcseq2seqcounts.R.txt 
#####################################################################
# usage : miRNA_bcseq2seqcounts.R <countfile> <allinigned list file> <base name>
#
# Turns the counts into a a matrix
#
# TODO:logging
########################################################################
cntfile=commandArgs()[length(commandArgs())-2]
allfile=commandArgs()[length(commandArgs())-1]
targetbase=commandArgs()[length(commandArgs())]

ydat<-xtabs(V3~V2+V1,read.delim(cntfile,header=F))
attr(ydat,"call")<-NULL; attr(ydat,"class")<-NULL
allist<-read.delim(allfile,header=F)
output<-merge(ydat,allist,by.x="row.names",by.y="V1",all.x=T)
agoutput<-aggregate(output[,2:(ncol(output)-1)],by=list(output$V2),FUN=sum)
#countM <- outer( rep(1, nrow(agoutput[,-1])), colSums(agoutput[,-1]) )
#normData <- agoutput[,-1] / countM * 1e6
write.table(output,paste(sep="",targetbase,"_raw.txt"),sep="\t",quote=F,col.names=T,row.names=F)
write.table(agoutput,paste(sep="",targetbase,"_mapped.txt"),sep="\t",quote=F,col.names=T,row.names=F)


rlazarus@ross-hp:~/rgalaxy$ cat ~/Downloads/miRNA_bcseq2seqcounts.sh
#!/bin/bash
###############################################################################
#
# Turns a mutiplex experiment into two sets of tables of counts raw and an aligned
# usage: miRNA_bcseq2seqcounts.sh <adapter sequence> <sequence file> <genome>
# i.e.: miRNA_bcseq2seqcounts.sh CGTATGCCGTCTTCTGCTTG /data2/sequence/FC057/FC057_5_sequence.txt /app/genomes/mirna_hairpin/mmu/mmu_mirna_hairpin.fa
#
# assumption - barcode is 6bp at end
# TODO: logging
###############################################################################

#Set our params
ADAPTER=$1
SEQFILE=$2
BSEQFILE=`basename $SEQFILE`
LID=`echo $BSEQFILE|sed 's/_sequence.txt//'`
TARG=`echo $SEQFILE|sed 's/_sequence.txt//'`
WRKDIR=/tmp/$BSEQFILE.wrk.$$
BCFILE=$WRKDIR/bc.txt
CLIPPEDFILE=$WRKDIR/$BSEQFILE.clipped
COUNTSFILE=$WRKDIR/cnt.txt
GENOID=$3
PFX=$GENOID
#lets start fresh
#[ -d $WRKDIR ] && rm -r $WRKDIR
mkdir $WRKDIR
#generate barcode file
echo AAGTAT     AAGTAT >  $BCFILE
echo ATCCTT     ATCCTT >> $BCFILE
echo AGAGGT     AGAGGT >> $BCFILE
echo TAGGTT     TAGGTT >> $BCFILE
echo TCTCTT     TCTCTT >> $BCFILE
echo TTGTTT     TTGTTT >> $BCFILE
echo CACTCT     CACTCT >> $BCFILE
echo CTGCCT     CTGCCT >> $BCFILE
echo GAATGT     GAATGT >> $BCFILE
echo GTACCT     GTACCT >> $BCFILE
#clip our reads -l 24  6(barcode) + 18(miRNA min )
fastx_clipper -a $ADAPTER -l 24 -c -i $SEQFILE -o $CLIPPEDFILE
#split
cat $CLIPPEDFILE | fastx_barcode_splitter.pl --bcfile $BCFILE --prefix $WRKDIR/ --suffix .split --eol
#count
for I in `ls $WRKDIR/*.split |grep -v unmatched`
do
SAMPID=`echo $I | sed 's/\.split$//'|sed 's/.*\///'`
cat $I |sed -n '2~4p'|sort |sed 's/......$//' |sort |uniq -c |awk -v nm="$LID-$SAMPID" '{print nm"\t"$2"\t"$1}' >>$COUNTSFILE
done
#unique reads to fa file
cat $COUNTSFILE |cut -f2| sort|uniq |awk '{print ">"$0"\n"$0}'> $COUNTSFILE.fa
#align
bwa aln $PFX $COUNTSFILE.fa -f $COUNTSFILE.fa.sai
bwa samse -f $COUNTSFILE.fa.sam $PFX $COUNTSFILE.fa.sai $COUNTSFILE.fa
#map alignment
cat $COUNTSFILE.fa.sam|grep -v @ |cut -f1,3 > $WRKDIR/allist.txt
#generate matrixes
Rscript ./miRNA_bcseq2seqcounts.R $COUNTSFILE $WRKDIR/allist.txt $TARG
"""

import logging
import os
import sys
import glob
import optparse

SEQTEXT = '_sequence.txt' # typical end sequence
SPLITEXT = '.split'

class miRfixer:
    """ simple class for fixing mir fastq files
    derived from a shell script and R code written by Antony Kaspi
    ross lazarus copyright August 2011
    LGPL for the rgenetics project
    """
    def __init__(self,opts=None):
        assert opts.adapters <> None,'##Error: miRfixer init got no adapter input parameter'
        assert opts.seqfile <> None,'##Error: miRfixer init got no seqfile input parameter'
        self.workdir = os.getcwd() # assume we're in temp galaxy job directory
        self.adapter = opts.adapter
        self.seqfiles = opts.seqfiles
        self.logfile = open(opts.logfile,'a')
        for fn in (opts.outclip,opts.outcount):
            f = open(fn,'w') # create output files for appending
        for seqfile in opts.seqfiles:
            bseqfile = os.path.basename(seqfile)
            laneid = bseqfile.replace(opts.seqtxt,'')
            target = seqfile.replace(opts.seqtxt,'')
            self.genMat(seqfile=seqfile,laneid=laneid)
            
        self.logfile.close()
           
        
    def genMat(self,seqfile=None,laneid=''):
        """ want counts of unique clipped reads and a fasta file for mapping 
        """
        pfd,tempclip = tempfile.mkstemp(dir=self.workdir,suffix = 'tempclip.fastq')
        cfd,tempcounts = tempfile.mkstemp(dir=self.workdir,suffix = 'tempcount.xls')
        lfd,templog = tempfile.mkstemp(dir=self.workdir,suffix = 'tempcount.log')
        tlog = open(templog,'w')
        cl1 = ['fastx_clipper','-a %s' % self.opts.adapter,'-l %s' % self.opts.cliplen,'-c','-i %s' % seqfile,'-o %s' % tempclip]
        cl2 = ['fastx_barcode_splitter.pl','< %s' % tempclip,'--bcfile',self.opts.barcodefile,'--prefix %s/' % self.workdir,'--suffix %s' % SPLITEXT,'--eol']
        x = subprocess.Popen(cl1,shell=True,stdout=tlog,stderr=tlog)
        retval = x.wait()
        tlog.close()
        outlog = open(tlog,'r').readlines()
        self.logfile.write('Executing %s\n' % (' '.join(cl1)))
        self.logfile.write(''.join(outlog))
        tlog = open(templog,'w')        
        x = subprocess.Popen(cl2,shell=True,stdout=tlog,stderr=tlog)
        retval = x.wait()
        tlog.close()
        outlog = open(tlog,'r').readlines()
        self.logfile.write('Executing %s\n' % (' '.join(cl2)))
        self.logfile.write(''.join(outlog))  
        workfiles = glob.glob('*%s' % SPLITEXT)
        workfiles = [x for x in workfiles if (x.lower().find('unmatched') == -1)]
        for fname in workfiles: # get counts of unique clipped reads
            fq = open(os.path.join(self.workdir,fname),'r').readlines()
            sampid = fname.replace(SPLITEXT,'') # gives barcode
            sequences = [x for i,x in enumerate(fq) if (i > 0) and (i % 4 == 0)] # every 4th row 
            seqcounts = dict(zip(sequences, [0 for x in sequences] )) # will only ever have unique keys..
            for x in sequences:
                seqcounts[x] += 1
            usequences = seqcounts.keys()
            usequences.sort()
            cf = open(self.opts.outcounts,'a')
            res = ['%s-%s\t%s\t%d\n' % (laneid,sampid,x,seqcounts[x]) for x in usequences]
            cf.write(''.join(res))
            cf.close()
            
            
        clippedfile = open(self.opts.outclip,'a')
        countsfile = open(self.opts.outcounts,'a')
        
BSEQFILE=`basename $SEQFILE`
LID=`echo $BSEQFILE|sed 's/_sequence.txt//'`
TARG=`echo $SEQFILE|sed 's/_sequence.txt//'`
WRKDIR=/tmp/$BSEQFILE.wrk.$$
BCFILE=$WRKDIR/bc.txt
CLIPPEDFILE=$WRKDIR/$BSEQFILE.clipped
COUNTSFILE=$WRKDIR/cnt.txt
GENOID=$3
PFX=$GENOID
#lets start fresh
#[ -d $WRKDIR ] && rm -r $WRKDIR
mkdir $WRKDIR
#generate barcode file
echo AAGTAT     AAGTAT >  $BCFILE
echo ATCCTT     ATCCTT >> $BCFILE
echo AGAGGT     AGAGGT >> $BCFILE
echo TAGGTT     TAGGTT >> $BCFILE
echo TCTCTT     TCTCTT >> $BCFILE
echo TTGTTT     TTGTTT >> $BCFILE
echo CACTCT     CACTCT >> $BCFILE
echo CTGCCT     CTGCCT >> $BCFILE
echo GAATGT     GAATGT >> $BCFILE
echo GTACCT     GTACCT >> $BCFILE
#clip our reads -l 24  6(barcode) + 18(miRNA min )
fastx_clipper -a $ADAPTER -l 24 -c -i $SEQFILE -o $CLIPPEDFILE
#split
cat $CLIPPEDFILE | fastx_barcode_splitter.pl --bcfile $BCFILE --prefix $WRKDIR/ --suffix .split --eol
#count
for I in `ls $WRKDIR/*.split |grep -v unmatched`
do
SAMPID=`echo $I | sed 's/\.split$//'|sed 's/.*\///'`
cat $I |sed -n '2~4p'|sort |sed 's/......$//' |sort |uniq -c |awk -v nm="$LID-$SAMPID" '{print nm"\t"$2"\t"$1}' >>$COUNTSFILE
done
#unique reads to fa file
cat $COUNTSFILE |cut -f2| sort|uniq |awk '{print ">"$0"\n"$0}'> $COUNTSFILE.fa
#align
bwa aln $PFX $COUNTSFILE.fa -f $COUNTSFILE.fa.sai
bwa samse -f $COUNTSFILE.fa.sam $PFX $COUNTSFILE.fa.sai $COUNTSFILE.fa
#map alignment
cat $COUNTSFILE.fa.sam|grep -v @ |cut -f1,3 > $WRKDIR/allist.txt
#generate matrixes
Rscript ./miRNA_bcseq2seqcounts.R $COUNTSFILE $WRKDIR/allist.txt $TARG        
        
        
        
if __name__ == "__main__":
        op = optparse.OptionParser()
        a = op.add_option
        a('-s','--seqfiles',default=[],action="append", dest='seqfiles')
        a('-a','--adapter',default=None) # for plots
        a('-l','--barcodelen',default='6')
        a('-c','--cliplen',default='24') # barcodelen 6 + min mirlen 18
        a('-b','--barcodefile',default=None)
        a('-x','--outcounts',default='mirFix.xls')
        a('-p','--outclip',default='mirFix.fastq')
        a('-q','--seqtext',default=SEQTEXT) # for parsing out FCnnn from sequence file name
        opts, args = op.parse_args()
        assert opts.seqfiles > [],'##ERROR rgfixMir requires one or more sequence fasta file paths on the command line passed as -s fastq1,fastq2... '        
        assert opts.barcodefile <> None,'##ERROR rgfixMir requires a barcode file path on the command line passed as -b [barcode file path]'        
        assert opts.adapter <> None,'##ERROR rgfixMir requires an adapter sequence on the command line passed as -a [adapter - eg CGTATGCCGTCTTCTGCTTG]'        

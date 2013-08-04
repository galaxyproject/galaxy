"""
Recommended procedure for local realignment
Started nov 20 ross lazarus for rgenetics
Source code Copyright ross lazarus November 20 2010
All rights reserved 
Released for rgenetics under the LGPL 

Implementation in Galaxy of the recommended procedures and code documented at
http://www.broadinstitute.org/gsa/wiki/index.php/Local_realignment_around_indels

Creating Intervals

Step 1: Determining (small) suspicious intervals which are likely in need of realignment
The realigner needs to be told which locations are potentially in need of realignment. There are several heuristics used to determine the locations:
A. If one or more reads contain an indel in them (and are aligned correctly), one would want to make sure that the other indel-containing reads in the pileup are aligned correctly.
B. Occasionally it is the case that you have a SNP call set for your file that you'd like to use in searching for clustered SNP calls 
(which are suspicious and are often caused by indels). Note that the realigner works best with an unfiltered SNP list if at all possible.
C. When you do not have (or do not want to use) an available SNP call set, we can also detect clustered loci with high entropy 
(i.e. lots of mismatches). Generally, one would use method B or method C, but not both.
D. If you have known indels (e.g. from dbSNP), you can include those positions.
Example Command
Bracketed arguments are not required.
 java -Xmx1g -jar /path/to/GenomeAnalysisTK.jar \
  -T RealignerTargetCreator \
  -R /path/to/reference.fasta \
  -o /path/to/output.intervals \
  [-I /path/to/input.bam] \
  [-L intervals] \
  [-B:snps,VCF /path/to/SNP_calls.vcf] \
  [-B:indels,VCF /path/to/indel_calls.vcf] \
  [-D /path/to/dbsnp.rod]
Explanation of Arguments
The -L option is used to restrict the search to a specific region or set of regions instead of the whole genome.
The -o argument is used to specify the list of intervals being output and that should in turn be passed to the realigner in the next step.
The -B snps binding would be used to pass in SNP calls so that the target creator can find clustered SNPs.
The -B indels and dbsnp bindings would be used to pass in known indel sites for the realigner to target.
Other Available Arguments
--minReadsAtLocus N [the minimum coverage at a locus for the entropy calculation to be enabled; default=4]
--windowSize N [any two SNP calls and/or high entropy positions are considered clustered when they occur no more than N basepairs apart; default=10]
--mismatchFraction f [fraction of total sum of base qualities at a position that need to mismatch for the position to be considered to have high entropy; 
default=0.15; to disable, set to <= 0 or > 1]
Note that this fraction should be adjusted based on your particular data set. For deep coverage and/or when looking for indels with low allele 
frequency, this number should be smaller.
--maxIntervalSize [max size in bp of intervals that we'll pass to the realigner; default=500]
Because the realignment algorithm is N^2, allowing too large an interval might take too long to completely realign.
--realignReadsWithBadMates; this is the same argument as that in the next step for the IndelRealigner (see there for more details). 
It is crucial that the RealignerTargetCreator and the 
IndelRealigner see the exact same reads, so if you plan on using this argument with the IndelRealigner then you must provide it here too.
Realigning

Step 2: Running the realigner over your intervals
Please note that this tool uses the Picard SAMFileWriter implementation to write a final input bam file. 
This is relevant because SAMFileWriter writes out temporary "blocks" of reads to the Java temporary directory and then 
merges them all into a final bam at the end. Cleaning large bam files (or even many small bams that are large in aggregate) 
requires large temp space (see the example below showing how to instruct Java to use a custom temp directory) and the ability to open many files simultaneously.
Standard Command
java -Xmx4g -Djava.io.tmpdir=/path/to/tmpdir \  [this argument recommended when dealing with large input]
  -jar /path/to/GenomeAnalysisTK.jar \
  -I <input.bam> \
  -R <ref.fasta> \
  -T IndelRealigner \
  -targetIntervals <intervalListFromStep1Above.intervals> \
  -o <realignedBam.bam> \
  [-B:indels,VCF /path/to/indel_calls.vcf] \
  [-D /path/to/dbsnp.rod]
  [-compress 0]    [this argument recommended to speed up the process as this is only a temporary file]
Other Optional Arguments
-compress, --bam_compression; Compression level to use for output bams. If running FixMateInformation (so that the output of the IndelRealigner is only temporary, 
it's faster to turn off compression by setting it to 0); [default:5, recommended=0]
-LOD, --LODThresholdForCleaning; LOD threshold above which the realigner will proceed to realign; default=5.0]
This term is equivalent to "significance" - i.e. is the improvement significant enough to merit realignment? Note that this number should be adjusted based on your 
particular data set. For low coverage and/or when looking for indels with low allele frequency, this number should be smaller.
-targetNotSorted, --targetIntervalsAreNotSorted; This tool assumes that the target interval list is sorted; if the list turns out to be unsorted, it will throw an 
exception. Use this argument when your interval list is not sorted to instruct the Realigner to first sort it in memory.
-knownsOnly, --useOnlyKnownIndels; Don't run 'Smith-Waterman' to generate alternate consenses; use only known indels provided as RODs for constructing the alternate references.
ARGUMENTS FOR EXPERT USERS ONLY
--EntropyThreshold; percentage of mismatching base quality scores at a position to be considered having high entropy [default=0.15]
This is similar to the argument in the RealignerTargetCreator walker. The point here is that the realigner will only proceed with the realignment 
(even above the given threshold) if it minimizes entropy among the reads (and doesn't simply push the mismatch column to another position). 
This parameter is just a heuristic and should be adjusted based on your particular data set.
--maxConsensuses; max alternate consensuses to try (necessary to improve performance in deep coverage) [default=30]
If you need to find the optimal solution regardless of running time, use a higher number.
--maxReadsForConsensuses; max reads (chosen randomly) used for finding the potential alternate consensuses 
(necessary to improve performance in deep coverage) [default=120]
If you need to find the optimal solution regardless of running time, use a higher number.
--maxReadsForRealignment; max reads allowed at an interval for realignment. If this value is exceeded, 
realignment is not attempted and the reads are passed to the output file(s) as is [default=20000]
If you need to allow more reads (e.g. with very deep coverage) regardless of memory, use a higher number.
--maxReadsInRam; max reads allowed to be kept in memory at a time by the SAMFileWriter [default=500,000]
If too low, the tool may run out of system file descriptors needed to perform sorting; if too high, the tool may run out of memory.
--realignReadsWithBadMates; by default, the Realigner does not try to realign reads whose mates map to other chromosomes 
(because it complicates the Fix Mate Information step by requiring that work to be done genome-wide instead of being able to split up the jobs by chromosome). 
Use the 'realignReadsWithBadMates' argument to turn off this feature. Note that if using this argument then you must provide it also in the previous (RealignerTargetCreator) step.
--sortInCoordinateOrderEvenThoughItIsHighlyUnsafe; we are providing this option for the single case that a user's bam file 
is made up of single-end reads only (and therefore won't need to fix mate pairs in the next step). To be clear, we will not support use of this 
option for anyone running the Realigner with paired-end reads.

Fixing Mate Pairs

Step 3: Fixing the mate pairs of realigned reads
We recommend using the Picard FixMateInformation tool, available here. It can take your query-name-sorted bams and produce a fixed, coordinate-sorted bam.
Standard Command
java -Djava.io.tmpdir=/path/to/tmpdir \  [this argument recommended when dealing with large input]
  -jar FixMateInformation.jar \
  INPUT=<input1.bam> \
  [INPUT=<input2.bam>] \
  .
  .
  [INPUT=<inputN.bam>] \
  OUTPUT=<fixedBam.bam> \
  SO=coordinate \
  VALIDATION_STRINGENCY=SILENT

"""
import os,string,sys,optparse,shutil,tempfile 
from subprocess import Popen 
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,timenow,getFileString,whereis
progname = os.path.split(sys.argv[0])[1]


class GATKRealign():
    """
    classy!
    """
    
    def __init__(self,opts=None,cl=[],tidy=True):
        """
        """
        self.ourname = 'rgGATKRecal'
        self.opts = opts
        self.tidy = tidy
        self.cl = ' '.join(cl) # ready for the htmlfile output
        self.delme = []
        killme = string.punctuation + string.whitespace
        trantab = string.maketrans(killme,'_'*len(killme))
        self.title = self.opts.title.translate(trantab)
        self.tlogname = os.path.join(self.opts.outdir,'%s_rg%s_Log.txt' % (self.title,self.ourname))
        self.tlog = open(self.tlogname,'w')
        self.outtxt = '%s_%s_Out.txt' % (self.title,self.ourname)
        self.info = '%s on %s at %s' % (self.ourname,self.title,timenow())
        self.runGATK()
        self.writehtml()


        
    def run(self,cl=None,redir=True):
        assert cl <> None
        fd,templog = tempfile.mkstemp(dir=self.opts.outdir,suffix='%s.txt' % self.title)
        tlf = open(templog,'w')
        if redir:
           process = Popen(' '.join(cl), shell=True, stderr=tlf, stdout=tlf, cwd=self.opts.outdir)
        else:
           process = Popen(' '.join(cl), shell=True, cwd=self.opts.outdir)
        rval = process.wait()
        tlf.close()
        tlogs = ''.join(open(templog,'r').readlines())
        if len(tlogs) > 1:
            s = '## executing %s returned status %d and log (stdout/stderr) records: \n%s\n' % (' '.join(cl),rval,tlogs)
        else:
            s = '## executing %s returned status %d. Nothing appeared on stderr/stdout\n' % (' '.join(cl),rval)
        os.unlink(templog) # always
        self.tlog.write(s)
        
    def bamToSam(self,infile=None):
        """
        use samtools view to convert bam to sam
        """
        fd,tempsam = tempfile.mkstemp(dir=self.opts.outdir,suffix='%sTemp.sam' % self.title)
        cl = ['samtools view -h -o',tempsam,infile]
        self.run(cl)
        return tempsamexampleBAM.bam 
    
    def writehtml(self):
        """
        write the report as html
        """
        logdat = open(self.tlogname,'r').readlines()
        res = []
        res.append(galhtmlprefix % progname)
        res.append(galhtmlattr % (progname,timenow()))
        try:
            flist = os.listdir(self.opts.outdir)
        except:
            flist = []
        if len(flist) > 0: # show what's left
            flist = [x for x in flist if not (x.startswith('.') or x == 'None')]
            pdfs = [x for x in flist if os.path.splitext(x)[-1].lower() == '.pdf']
            tlist = [(os.path.getmtime(os.path.join(self.opts.outdir,x)),x) for x in flist]
            tlist.sort()
            flist = [x[1] for x in tlist]
            if len(pdfs) > 0:
                cells = []
                pdfs.sort()
                res.append('<div><table cellpadding="5" cellspacing="10">\n')
                for p in pdfs:                           
                    pfname = os.path.split(p)[-1]
                    pfroot = os.path.splitext(pfname)[0]
                    imghref = '%s.jpg' % pfroot # thumbnail name from mogrify
                    cl = ['mogrify', '-resize x300 -write %s %s' % (imghref,pfname),]
                    self.run(cl)
                    s = '<a href="%s"><img src="%s" title="%s" hspace="10" align="middle"></a>' % (pfname,imghref,pfname)
                    cells.append('<td>%s</br>%s</td>' % (pfroot,s))
                ncells = len(cells)
                for i in range(ncells):
                    if i % 2 == 1:
                        res.append('<tr>%s%s</tr>\n' % (cells[i-1],cells[i])) 
                if ncells % 2 == 0: # last one
                        res.append('<tr colspan="2">%s</tr>\n' % (cells[-1]))                     
                res.append('</table></div>\n')
            res.append('<div><b>Output files.</b><hr/>\n')
            res.append('<table>\n')
            for i,f in enumerate(flist):
                fn = os.path.split(f)[-1]
                fs = getFileString(fn,self.opts.outdir)
                res.append('<tr><td><a href="%s">%s</a></td></tr>\n' % (fn,fs))
            res.append('</table></div>\n')
        res.append('<b>Your job produced the following log of activity - check here for a record of what was done and any unexpected events</b><hr/>')
        res.append('\n%s' % '<br/>'.join(logdat))
        res.append('<hr/>Note: The freely available <a href="http://www.broadinstitute.org/gsa/wiki/index.php/Main_Page">GATK</a> \n')
        res.append('did all the work reportexampleBAM.bam ed here. GATK is an independent non-Galaxy community resource, whose third party tools were')
        res.append('orchestrated by the Galaxy rgGATKRecalibrate wrapper and this command line from the Galaxy form:<br/>\n%s' % (self.cl))
        res.append(galhtmlpostfix)
        f = open(self.opts.htmlout,'w')
        f.write('\n'.join(res))
        f.close()
           
 
    def cleanup(self):
        if self.tidy:
            for fname in self.delme:
                try:
                    os.unlink(fname)
                except:
                    pass
        print >> sys.stdout, self.info # for info        
  
        
    def runGATK(self):
        """
        from the GATK documentation at http://www.broadinstitute.org/gsa/wiki/index.php/Local_realignment_around_indels
        java -Xmx1g -jar /path/to/GenomeAnalysisTK.jar \
        -T RealignerTargetCreator \
        -R /path/to/reference.fasta \
        -o /path/to/output.intervals \
        [-I /path/to/input.bam] \
        [-L intervals] \
        [-B:snps,VCF /path/to/SNP_calls.vcf] \
        [-B:indels,VCF /path/to/indel_calls.vcf] \
        [-D /path/to/dbsnp.rod]
        UGH - gatk insists that input files have a .bam extension.
        Yuck - and same for bed files.

        """
        fhb,fakebam = tempfile.mkstemp(dir=self.opts.outdir,suffix='pernicketyGATKextension.bam')
        os.unlink(fakebam)
        self.delme.append(fakebam)
        fhd,fakebed = tempfile.mkstemp(dir=self.opts.outdir,suffix='pernicketyGATKextension.bed')
        os.unlink(fakebed)
        self.delme.append(fakebed)
        os.symlink(self.opts.input,fakebam)      
        cl = ['java -Xmx%s' % self.opts.maxjheap,'-jar',self.opts.gatkjar,'-T RealignerTargetCreator -R', self.opts.refseqfasta]
        cl += ['-I',fakebam,'-U ALLOW_UNINDEXED_BAM','-o',self.opts.outintervalsfile]
        if self.opts.dbsnp_rod > "":
            cl += ['-D', self.opts.dbsnp_rod] # needed so we don't need the .bai index file
        if self.opts.intervals > '':
            os.symlink(self.opts.intervals,fakebed)      
            cl += ['-L',fakebed]
        if self.opts.indelcalls > '':
            cl += ['-B:indels,VCF',self.opts.indelcalls]
        if self.opts.snpcalls > '':
            cl += ['-B:snps,VCF',self.opts.snpcalls]
        # experimental backstop broken?
        # cl += ['--default_read_group','test','--default_platform','Illumina']
        self.run(cl)
        cl = ['java -Xmx%s' % self.opts.maxjheap,'-Djava.io.tmpdir=%s' % self.opts.tmp_dir,'-jar',self.opts.gatkjar]
        cl += ['-l INFO -R', self.opts.refseqfasta,'-I',fakebam,'-o',self.opts.outrealignedbam]
        cl += ['-U ALLOW_UNINDEXED_BAM','-T IndelRealigner','-targetIntervals',fakebed]
        if self.opts.dbsnp_rod > "":
            cl += ['-D', self.opts.dbsnp_rod] # needed so we don't need the .bai index file
        if self.opts.indelcalls > '':
            cl += ['-B:indels,VCF',self.opts.indelcalls]
        #cl += ['--default_read_group','test','--default_platform','Illumina']
        self.run(cl)
        if self.opts.isPaired.lower() == 'true':
            assert os.path.isfile(opts.fixMatejar),'## Picard FixMateInformation not available - please install in the tool-data/shared/jars folder from http://picard.sourceforge.net/'
            cl = ['java -Xmx%s' % self.opts.maxjheap,'-Djava.io.tmpdir=%s' % self.opts.tmp_dir,'-jar',self.opts.fixMatejar]
            cl += ['I=',self.opts.outrealignedbam,'SORT_ORDER=coordinate','VALIDATION_STRINGENCY=LENIENT']
            self.run(cl)
        self.tlog.close()
        self.cleanup()


    
if __name__ == '__main__':
    '''
     <command interpreter="python">
   rgGATKLocalRealign.py --input "$input_file" -n "$out_prefix" --tmp_dir "${__new_file_path__}" -o "$out_realigned_bam" 
   -d "$html_file.files_path" -t "$html_file" -isPaired "$isPaired"
   --gatkjar "${GALAXY_DATA_INDEX_DIR}/shared/jars/GenomeAnalysisTK.jar" --fixMatejar "${GALAXY_DATA_INDEX_DIR}/shared/jars/FixMateInformation.jar" 
#if $gSrc.refGenomeSource=="indexed":
   --refseqfasta "$gSrc.indices.value"
#else
   --refseqfasta "$gSrc.ownFile"
#end if

#if $dSrc.refdbsnpSource=="indexed":
   --dbsnp_rod "$dSrc.indices.value"
#elif $dSrc.refdbsnpSource=="ownFile":
   --dbsnp_rod "$dSrc.ownFile"
#end if
#if $sSrc.snpsSource=="ownFile":
   --snpcalls "$sSrc.ownFile"
#end if
#if $iSrc.indelSource=="ownFile":
   --indelcalls "$iSrc.ownFile"
#end if
#if $tSrc.interSource=="history":
   --intervals "$tSrc.ownFile"
#end if
  </command>
    '''
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-n', '--title', default="GATK Recalibrate")
    op.add_option('--snpcalls', default="")
    op.add_option('--indelcalls', default='')
    op.add_option('--intervals', default='')
    op.add_option('--dbsnp_rod', default="")
    op.add_option('--refseqfasta', default="")
    op.add_option('--outintervalsfile', default="rg_GATK_outintervals.intervals")
    op.add_option('-o','--outrealignedbam', default="rg_out_GATK_realigned.bam")
    op.add_option('--isPaired', default='false') 
    op.add_option('-t', '--htmlout', default="")
    op.add_option('-d', '--outdir', default="")
    op.add_option('-x', '--maxjheap', default='4g')
    op.add_option('--tmp_dir', default='/tmp')
    op.add_option('-g','--gatkjar',default='')
    op.add_option('--fixMatejar',default='')
    opts, args = op.parse_args()

    assert opts.input <> None
    assert os.path.isfile(opts.input),'## input file (%s) not a file' % opts.input
    assert os.path.isfile(opts.gatkjar),'## GATK toolkit not available - please install in the tool-data/shared/jars folder from http://www.broadinstitute.org/gsa/wiki/index.php/Main_Page'
    assert os.path.isfile(opts.refseqfasta),'## Reference sequence fasta file not available'
    try:
        os.makedirs(opts.tmp_dir)
    except:
        pass
    try:
        os.makedirs(opts.outdir)
    except:
        pass
    x = GATKRealign(opts=opts,cl=sys.argv)
    

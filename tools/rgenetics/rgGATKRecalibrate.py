"""
docs from http://www.broadinstitute.org/gsa/wiki/index.php/Base_quality_score_recalibration


CountCovariates
java -Xmx4g -jar GenomeAnalysisTK.jar \
  -l INFO \
  -R resources/Homo_sapiens_assembly18.fasta \
  --DBSNP resources/dbsnp_129_hg18.rod \
  [-B:mask,VCF sitesToMask.vcf] \
  -I my_reads.bam \
  -T CountCovariates \ 
   -cov ReadGroupCovariate \
   -cov QualityScoreCovariate \
   -cov CycleCovariate \
   -cov DinucCovariate \
   -recalFile my_reads.recal_data.csv
This GATK command walks over all of the reads in my_reads.bam and tabulates data about the following features of the bases:
Read group the read belongs to X assigned quality score X machine cycle producing this base X current base + previous base (dinucleotide)
For each of such bin, we count the number of bases within the bin and how often such bases mismatch the reference base, excluding loci known to vary in the population, using our dbSNP_129_hg18.rod file. After running over all reads, CountCovariates produces a file called my_reads.recal_data.csv, which contains the data needed to recalibrate reads. The format of this file is described below.
To use a new covariate in this calculation simply add it to the list of covariates passed to the walker using the -cov argument. Note that the read group and quality score covariates are required covariates will be added for you if not specified at the command line. Use the --list option for a list of all available covariates.
While running CountCovariates, you will see something that looks like:
55 [main] INFO root  - -------------------------------------------------------
55 [main] INFO root  - Program Name: org.broadinstitute.sting.gatk.CommandLineGATK
55 [main] INFO root  - Program Args: -l INFO -R /broad/1KG/reference/human_b36_both.fasta -T CountCovariates -D /humgen/gsa-scr1/GATK_Data/dbsnp_129_b36.rod 
-I /broad/1KG/DCC/ftp/data/NA12872/alignment/NA12872.454.SRP000031.2009_06.bam -recalFile 454.test.recal_data.csv 
55 [main] INFO root  - Time/Date: 2009/06/25 08:55:19
56 [main] INFO root  - -------------------------------------------------------
61 [main] INFO org.broadinstitute.sting.gatk.GenomeAnalysisEngine  - Processing ROD bindings: 1 -> dbSNP : dbsnp : /humgen/gsa-scr1/GATK_Data/dbsnp_129_b36.rod
61 [main] INFO org.broadinstitute.sting.gatk.GenomeAnalysisEngine  - Created binding from dbsnp to /humgen/gsa-scr1/GATK_Data/dbsnp_129_b36.rod of type class 
org.broadinstitute.sting.gatk.refdata.rodDbSNP
63 [main] INFO org.broadinstitute.sting.gatk.executive.MicroScheduler  - Creating linear microscheduler
273 [main] INFO org.broadinstitute.sting.gatk.GenomeAnalysisEngine  - Strictness is SILENT
301 [main] INFO org.broadinstitute.sting.gatk.walkers.Walker  - Created recalibration data collectors for 114 read group(s)
510 [main] INFO org.broadinstitute.sting.gatk.traversals.TraversalEngine  - [PROGRESS] Traversed to 1:1, processing 1 loci in 0.23 secs (234000.00 secs per 1M loci)
21140 [main] INFO org.broadinstitute.sting.gatk.traversals.TraversalEngine  - [PROGRESS] Traversed to 1:1857000, processing 1,000,000 loci in 20.87 secs (20.87 secs per 1M loci)
TableRecalibration
After counting covariates in the initial BAM File, we then walk through the BAM file again and rewrite the quality scores (in the QUAL field) using the data in the recal_data.csv file, into a new BAM file.
java -Xmx4g -jar GenomeAnalysisTK.jar \
  -l INFO \  
  -R resources/Homo_sapiens_assembly18.fasta \
  -I my_reads.bam \
  -T TableRecalibration \
   -outputBam my_reads.recal.bam \
   -recalFile my_reads.recal_data.csv
This command uses the recalibration table data in my_reads.recal_data.csv produced by CountCovariates to recalibrate the quality scores in my_reads.bam, writing out a new BAM file my_reads.recal.bam with recalibrated QUAL field values.
Effectively the new quality score is the sum of the global difference between reported quality scores and the empirical quality, plus the quality bin specific shift, plus the cycle x qual and dinucleotide x qual effect. Following recalibration, the read quality scores are much closer to their empirical scores than before. This means they can be used in a statistically robust manner for downstream processing, such as SNP calling. In additional, by accounting for quality changes by cycle and sequence context, we can identify truly high quality bases in the reads, often finding a subset of bases that are Q30 even when no bases were originally labeled as such.
While running TableRecalibrate, you will see output that looks something like
56 [main] INFO root  - -------------------------------------------------------
56 [main] INFO root  - Program Name: org.broadinstitute.sting.gatk.CommandLineGATK
56 [main] INFO root  - Program Args: -l INFO -R /broad/1KG/reference/human_b36_both.fasta -T TableRecalibration -I data/SRR002385.raw.sorted.cleaned.bam 
-recalFile 454.2/SRR002385.raw.sorted.cleaned.SEQUENTIAL.init.recal_data.csv -outputBAM 454.2/foo.bam
57 [main] INFO root  - Time/Date: 2009/06/25 08:53:04
57 [main] INFO root  - -------------------------------------------------------
61 [main] INFO org.broadinstitute.sting.gatk.executive.MicroScheduler  - Creating linear microscheduler
230 [main] INFO org.broadinstitute.sting.gatk.GenomeAnalysisEngine  - Strictness is SILENT
NFO  15:45:52,881 TableRecalibrationWalker - Reading in the data from input file... 
INFO  15:45:52,885 TableRecalibrationWalker - The covariates being used here:  
INFO  15:45:52,885 TableRecalibrationWalker - [Read Group, Reported Quality Score, Cycle, Dinucleotide] 
INFO  15:45:55,324 TableRecalibrationWalker - ...done! 
INFO  15:45:55,324 TableRecalibrationWalker - Creating collapsed tables for use in sequential calculation... 
INFO  15:45:56,201 TableRecalibrationWalker - ...done! 
5435 [main] INFO org.broadinstitute.sting.gatk.traversals.TraversalEngine  - [PROGRESS] Traversed 1 reads in 5.20 secs (5202000.00 secs per 1M reads)
35508 [main] INFO org.broadinstitute.sting.gatk.traversals.TraversalEngine  - [PROGRESS] Traversed 486,685 reads in 35.28 secs (72.49 secs per 1M reads)

Source code Copyright ross lazarus November 19 2010
All rights reserved 
Released for rgenetics under the LGPL 
"""
import os,string,sys,optparse,shutil,tempfile,glob
from subprocess import Popen 
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,timenow,getFileString,whereis
progname = os.path.split(sys.argv[0])[1]

""" 
Estimate library complexity

"""



class GATKRecal():
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
        self.GATK_CVFlags = opts.GATK_CVflags  
        self.Rscriptpath = whereis('Rscript')
        self.info = '%s on %s at %s' % (self.ourname,self.title,timenow())
        if self.Rscriptpath == None: # GATK wants the explicit path to Rscript which comes with R now
            p = os.environ.get('PATH', '')
            self.tlog.write('### Cannot find %s on %s\n' % (program,p))
            self.Rscriptpath = '/share/shared/lx26-amd64/bin/Rscript'
        self.pdfoutdir = os.path.join(self.opts.outdir,'pdfplots')
        self.preplotprefix = 'rgPreRecal_'
        self.postplotprefix = 'rgPostRecal_'
        try:
            os.makedirs(self.pdfoutdir)
        except:
            self.tlog.write('## unable to create pdf output dir %s' % self.pdfoutdir)
        self.delme.append(self.pdfoutdir)
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
            s = '## executing %s returned status %d.\n' % (' '.join(cl),rval)
        os.unlink(templog) # always
        self.tlog.write(s)
        
    def samidxstats(self,infile=None):
        """
        use samtools idxstats
        """
        fd,tempstats = tempfile.mkstemp(dir=self.opts.outdir,suffix='%sidxStats.txt' % self.title)
        cl = ['samtools -idxstats',infile,'>',tempstats]
        self.run(cl)
        return tempstats
    
    def writeImages(self,pdfs=[],res=[]):
        """ images are in pairs PRE_foo.pdf and POST_foo.pdf
        match by sorting
        """
        pres = [x for x in pdfs if os.path.split(x)[-1].startswith(self.preplotprefix)]
        posts = [x for x in pdfs if os.path.split(x)[-1].startswith(self.postplotprefix)]
        pres.sort()
        posts.sort()
        npdfs = max(len(pres),len(posts))
        if len(pres) <> len(posts):
            tlog = open(self.tlogname,'w')
            tlog.write('### pres (%s) and posts (%s) not same length' % (','.join(pres),','.join(posts)))
            tlog.close()
        res.append('<div><table cellpadding="5" cellspacing="10">\n')
        res.append('<tr><th colspan="2">GATK Analysis Plots</th></tr>\n')
        res.append('<tr><th>Input Covariates</th><th>Recalibrated Covariates</th></tr>\n')
        for i in range(npdfs): # these are all the posts - need to move, rename and make thumbnails
            if i < len(pres):
                prepdf = pres[i]
                prefname = os.path.split(prepdf)[-1]
                prefroot = os.path.splitext(prefname)[0]
                preimghref = '%s.jpg' % prefroot
            else:
                prefname = preimghref = 'PreRecal Image Not found'
            if i < len(posts):
                postpdf = posts[i]
                postfname = os.path.split(postpdf)[-1]
                postfroot = os.path.splitext(postfname)[0]
                postimghref = '%s.jpg' % postfroot            
            else:
                postfname = postimghref = 'PostRecal Image Not found'                                   
            spre = '<a href="%s"><img src="%s" title="%s" hspace="10" align="middle"></a>' % (prefname,preimghref,prefname)
            spost = '<a href="%s"><img src="%s" title="%s" hspace="10" align="middle"></a>' % (postfname,postimghref,postfname)
            res.append('<tr><td>%s</td><td>%s</td></tr>' % (spre,spost))
        res.append('</table></div>\n')
        return res
    
    def writehtml(self):
        """
        write the report as html
        note complications needed to write pre and post reports - they have to be separated since gatk insists on giving them all the same names
        but at least allows a separate output directory...
        """
        logdat = open(self.tlogname,'r').readlines()
        res = []
        res.append(galhtmlprefix % progname)
        res.append(galhtmlattr % (progname,timenow()))
        res.append('<font size="-2">Note: The freely available <a href="http://www.broadinstitute.org/gsa/wiki/index.php/Main_Page">GATK</a>')
        res.append('did all the calculations arranged here in your Galaxy history')
        try:
            flist = os.listdir(self.opts.outdir)
        except:
            flist = []
        if len(flist) > 0: # show what's left after cleanup
            flist = [x for x in flist if not (x.startswith('.') or x == 'None')]
            pdfs = [x for x in flist if os.path.splitext(x)[-1].lower() == '.pdf']
            tlist = [(os.path.getmtime(os.path.join(self.opts.outdir,x)),x) for x in flist]
            tlist.sort()
            flist = [x[1] for x in tlist]
            if len(pdfs) > 0:
                res = self.writeImages(pdfs,res)
            res.append('<div><b>Output files.</b><hr/>\n')
            res.append('<table>\n')
            for i,f in enumerate(flist):
                fn = os.path.split(f)[-1]
                fs = getFileString(fn,self.opts.outdir)
                res.append('<tr><td><a href="%s">%s</a></td></tr>\n' % (fn,fs))
            res.append('</table></div>\n')
        res.append('<b>Your job produced the following log of activity - check here for a record of what was done and any unexpected events</b><hr/>')
        res.append('\n%s' % '<br/>'.join(logdat))
        res.append(galhtmlpostfix)
        f = open(self.opts.htmlout,'w')
        f.write('\n'.join(res))
        f.close()
        
    def movepdfs(self,prefix='rgPreRecal_',fromdir='',todir=''):
        """
        rename and move analysis output analysis data and pdfs
        make thumbnails while we're at it for pdfs
        """
        g = os.path.join(fromdir,'*')
        flist = glob.glob(g)
        for p in flist: # rename and move
            opath,name = os.path.split(p)
            dest = os.path.join(todir,'%s%s' % (prefix,name)) # PRE_foo.pdf
            shutil.move(p,dest)           
            if name.lower().endswith('.pdf'):
                pdfroot = os.path.splitext(dest)[0]
                imghref = '%s.jpg' % pdfroot # thumbnail name from mogrify
                cl = ['mogrify', '-resize x300', '-write %s %s' % (imghref,dest)]
                self.run(cl)
                
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
        from the GATK documentation, http://www.broadinstitute.org/gsa/wiki/index.php/Base_quality_score_recalibration
        we want 3 separate steps
        
        java -Xmx4g -jar GenomeAnalysisTK.jar \
          -l INFO \
          -R resources/Homo_sapiens_assembly18.fasta \
          --DBSNP resources/dbsnp_129_hg18.rod \
          [-B:mask,VCF sitesToMask.vcf] \
          -I my_reads.bam \
          -T CountCovariates \ 
           -cov ReadGroupCovariate \
           -cov QualityScoreCovariate \
           -cov CycleCovariate \
           -cov DinucCovariate \
           -recalFile my_reads.recal_data.csv

        then
        java -Xmx4g -jar GenomeAnalysisTK.jar \
          -l INFO \  
          -R resources/Homo_sapiens_assembly18.fasta \
          -I my_reads.bam \
          -T TableRecalibration \
           -outputBam my_reads.recal.bam \
           -recalFile my_reads.recal_data.csv


        then 
        java -Xmx4g -jar AnalyzeCovariates.jar \
         -recalFile /path/to/recal.table.csv  \
         -outputDir /path/to/output_dir/  \
         -resources resources/  \
         -ignoreQ 5

        UGH - gatk insists that input files have a .bam extension.

        """
        fht,fakebam = tempfile.mkstemp(dir=self.opts.outdir,suffix='pernickityGATKfakebamextension.bam')
        os.unlink(fakebam)
        self.delme.append(fakebam)
        os.symlink(self.opts.input,fakebam)        
        cl = ['java -Xmx%s' % self.opts.maxjheap,'-jar',self.opts.gatkjar,'-l INFO -R', self.opts.refseqfasta]
        cl += ['-D', self.opts.dbsnp_rod,'-I',fakebam,'-U ALLOW_UNINDEXED_BAM','-T CountCovariates'] # needed so we don't need the .bai index file
        if self.opts.sitestomask > '':
            cl.append('-B:mask,VCF %s' % (self.opts.sitestomask))
        cl += [self.opts.GATK_CVflags,'-recalFile',self.opts.prerecalfile]
        if self.opts.add_default_rg:
            cl.append('--default_read_group Fake --default_platform Illumina')
        self.run(cl) # preanalysis
        if self.Rscriptpath == None:
            self.tlog.write('### GATK setup problem - Cannot locate Rscript on the path - unable to run reports')
        else:
            cl = ['java -Xmx%s' % self.opts.maxjheap,'-jar',self.opts.ancojar,'-recalFile',self.opts.prerecalfile,'-Rscript',self.Rscriptpath]
            cl += ['-outputDir',self.pdfoutdir, '-ignoreQ',self.opts.ignoreQ,'-resources',self.opts.gatkRscriptsdir]
            self.run(cl) # preplots
            self.movepdfs(self.preplotprefix,self.pdfoutdir,self.opts.outdir)
        cl = ['java -Xmx%s' % self.opts.maxjheap,'-jar',self.opts.gatkjar,'-l INFO -R', self.opts.refseqfasta,'-I',fakebam]
        cl += ['-U ALLOW_UNINDEXED_BAM','-T TableRecalibration --out',self.opts.outrecalbam,'-recalFile',self.opts.prerecalfile]
        if self.opts.add_default_rg:
            cl.append('--default_read_group Fake --default_platform Illumina')
        self.run(cl) # adjust
        os.unlink(fakebam) # it's a symlink
        os.symlink(self.opts.outrecalbam,fakebam)        
        cl = ['java -Xmx%s' % self.opts.maxjheap,'-jar',self.opts.gatkjar,'-l INFO -R', self.opts.refseqfasta]
        cl += ['-D', self.opts.dbsnp_rod,'-I',fakebam,'-U ALLOW_UNINDEXED_BAM','-T CountCovariates'] # needed so we don't need the .bai index file
        if self.opts.sitestomask > '':
            cl.append('-B:mask,VCF %s' % (self.opts.sitestomask))
        cl += [self.opts.GATK_CVflags,'-recalFile',self.opts.postrecalfile]
        cl += ['--default_read_group','test','--default_platform','Illumina']
        self.run(cl) # post analysis
        if self.Rscriptpath == None:
            self.tlog.write('### GATK setup problem - Cannot locate Rscript on the path - unable to run post recalibrate reports')
        else:
            cl = ['java -Xmx%s' % self.opts.maxjheap,'-jar',self.opts.ancojar,'-recalFile',self.opts.postrecalfile,'-Rscript',self.Rscriptpath]
            cl += ['-outputDir',self.pdfoutdir, '-ignoreQ',self.opts.ignoreQ,'-resources',self.opts.gatkRscriptsdir]
            self.run(cl) # post plots
            self.movepdfs(self.postplotprefix,self.pdfoutdir,self.opts.outdir)
        self.tlog.close()   
        self.cleanup()
 

    
if __name__ == '__main__':
    '''
   <command interpreter="python">
   rgGATKRecalibrate.py -i "$input_file" -n "$out_prefix" --tmp_dir "${__new_file_path__}" -o "$out_recal_bam" 
   --GATK_CVflags "-T CountCovariates $GATK_CVflags" -d "$html_file.files_path" -t "$html_file" -x "$maxheap"
   --gatkjar "${GALAXY_DATA_INDEX_DIR}/shared/jars/GenomeAnalysisTK.jar" --ancojar "${GALAXY_DATA_INDEX_DIR}/shared/jars/AnalyzeCovariates.jar"
   --gatkRscriptsdir "${GALAXY_DATA_INDEX_DIR}/shared/R"
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

#if $vSrc.vcfmaskSource=="indexed":
   --sitestomask "$vSrc.indices.value"
#elif $vSrc.vcfmaskSource=="ownFile":
   --sitestomask "$vSrc.ownFile"
#end if

  </command>
    '''
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-n', '--title', default="GATK Recalibrate")
    op.add_option('--GATK_CVflags', default='-cov ReadGroupCovariate -cov QualityScoreCovariate -cov CycleCovariate -cov DinucCovariate')
    op.add_option('--dbsnp_rod', default="/share/shared/data/dbsnp/dbsnp_129_hg18.rod")
    op.add_option('--refseqfasta', default="/share/shared/data/hg18/hg18.fasta")
    op.add_option('--prerecalfile', default="rg_GATK_prerecalfile.csv")
    op.add_option('--postrecalfile', default="rg_GATK_postrecalfile.csv")
    op.add_option('-o','--outrecalbam', default="rg_out_GATK_recalfile.bam")
    op.add_option('--sitestomask', default="")
    op.add_option('-t', '--htmlout', default="")
    op.add_option('-d', '--outdir', default="")
    op.add_option('-x', '--maxjheap', default='4g')
    op.add_option('--tmp_dir', default='/tmp')
    op.add_option('-g','--gatkjar',default='')
    op.add_option('-a','--ancojar',default='')
    op.add_option('-r','--gatkRscriptsdir',default='')
    op.add_option('--ignoreQ',default='5')
    op.add_option('--add_default_rg',default='false')
    opts, args = op.parse_args()

    assert opts.input <> None
    assert os.path.isfile(opts.input),'## input file not available'
    assert os.path.isfile(opts.ancojar),'## GATK analyse covariates jar not available'
    assert os.path.isfile(opts.gatkjar),'## GATK toolkit not available'
    try:
        os.makedirs(opts.tmp_dir)
    except:
        pass
    try:
        os.makedirs(opts.outdir)
    except:
        pass
    x = GATKRecal(opts=opts,cl=sys.argv)
    

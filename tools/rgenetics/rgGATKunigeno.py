"""
GATK Depth of Coverage
Implementation in Galaxy of the recommended procedures and code documented at
http://www.broadinstitute.org/gsa/wiki/index.php/Depth_of_Coverage_v3.

Started nov 20 ross lazarus for rgenetics
Source code Copyright ross lazarus November 20 2010
All rights reserved 
Released for rgenetics under the LGPL 

"""
import os,string,sys,optparse,shutil,tempfile 
from subprocess import Popen 
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,timenow,getFileString
progname = os.path.split(sys.argv[0])[1]


class GATKunigeno():
    """
    classy!
    """
    
    def __init__(self,opts=None,cl=[],tidy=True,verbose=True):
        """
        """
        self.ourname = 'rgGATKunigeno'
        self.opts = opts
        self.tidy = tidy
        self.verbose = verbose
        self.cl = ' '.join(cl) # ready for the htmlfile output
        self.delme = []
        self.bamslist = opts.bams
        killme = string.punctuation + string.whitespace
        trantab = string.maketrans(killme,'_'*len(killme))
        self.title = self.opts.title.translate(trantab)
        self.metricsname = os.path.join(self.opts.outdir,'%s_rg%s_Metrics.txt' % (self.title,self.ourname))
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
  
        
    def runGATK(self):
        """
         java -jar GenomeAnalysisTK.jar \
         -R resources/Homo_sapiens_assembly18.fasta \
         -T UnifiedGenotyper \
         -I sample1.bam [-I sample2.bam ...] \
         -D resources/dbsnp_129_hg18.rod \
         -o snps.raw.vcf \
         -stand_call_conf [50.0] \
         -stand_emit_conf 10.0 \
         -dcov [50] \ 
         [-L targets.interval_list]
        UGH - gatk insists that input files have a .bam extension.
        verbose,--verbose_mode specifies the output file used to print debugging information.
        -metrics,--metrics_file specifies the output file used to print various metrics about callability.
        """
        self.fakebams = []
        for b in self.bamslist: # gatk is pernickety and gives you a lengthy lecture before letting you know about what.
            fht,fakebam = tempfile.mkstemp(dir=self.opts.outdir,suffix='irritatingGATKpernickitiness.bam')
            self.delme.append(fakebam)
            os.unlink(fakebam)
            os.symlink(b,fakebam)        
            self.fakebams.append(fakebam)
        cl = ['java -Xmx%s' % self.opts.maxjheap,'-jar',self.opts.gatkjar,'-T UnifiedGenotyper -R', self.opts.refseqfasta]
        cl += ['-I %s' % x for x in self.fakebams]
        cl += ['-U ALLOW_UNINDEXED_BAM','-o',self.opts.outvcf,'-stand_call_conf',self.opts.stand_call_conf]
        cl += ['-stand_emit_conf',self.opts.stand_emit_conf,'-dcov',self.opts.dcov,'--metrics_file',self.metricsname]
        if self.verbose:
            cl.append('--verbose_mode')
        if self.opts.target_interval_list > '':
            fht,fakebed = tempfile.mkstemp(dir=self.opts.outdir,suffix='pernicketyGATKextension.bed')
            os.unlink(fakebed)
            self.delme.append(fakebed)
            os.symlink(self.opts.intervals,fakebed)      
            cl += ['-L',fakebed]
        self.run(cl)
        self.tlog.close()
        self.cleanup() # remove anything scheduled for deletion before making html files list
            
 
    def cleanup(self):
        if self.tidy:
            for fname in self.delme:
                try:
                    os.unlink(fname)
                except:
                    pass
        print >> sys.stdout, self.info # for info        


    
if __name__ == '__main__':
    '''
      <command interpreter="python">
       rgGATKunigeno.py --bams "$input_file" -n "$out_prefix" --tmp_dir "${__new_file_path__}" 
       -d "$html_file.files_path" -t "$html_file"  -dcov "$dcov" -stand_call_conf "$stand_call_conf"  -stand_emit_conf "$stand_emit_conf"
       --gatkjar "${GALAXY_DATA_INDEX_DIR}/shared/jars/GenomeAnalysisTK.jar" 
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
    #if $all_bases:
      -all_bases
    #end if
      </command>
    '''
    op = optparse.OptionParser()
    op.add_option('--bams', type="string", action="append") # bam inputs    
    op.add_option('-n', '--title', default="GATK Recalibrate")
    op.add_option('--refseqfasta', default="")
    op.add_option('--dbsnp_rod', default="")    
    op.add_option('-o','--outvcf' ,default="rg_GATK_unigeno.vcf")
    op.add_option('-t', '--htmlout', default="")
    op.add_option('-d', '--outdir', default="")
    op.add_option('-x', '--maxjheap', default='4g')
    op.add_option('--tmp_dir', default='/tmp')
    op.add_option('-g','--gatkjar',default='')
    op.add_option('-stand_call_conf', default="50.0")
    op.add_option('-stand_emit_conf', default="10.0")
    op.add_option('-dcov', default="50") 
    op.add_option('-L','--targets_interval_list', default="") 

    opts, args = op.parse_args()

    assert opts.input <> None
    assert os.path.isfile(opts.input),'## input file (%s) not a file' % opts.input
    assert os.path.isfile(opts.gatkjar),'## Please install GATK jars in the tool-data/shared/jars folder from http://www.broadinstitute.org/gsa/wiki/index.php/Main_Page'
    assert os.path.isfile(opts.refseqfasta),'## Reference sequence fasta file not available'
    try:
        os.makedirs(opts.tmp_dir)
    except:
        pass
    try:
        os.makedirs(opts.outdir)
    except:
        pass
    x = GATKDoC(opts=opts,cl=sys.argv)
    

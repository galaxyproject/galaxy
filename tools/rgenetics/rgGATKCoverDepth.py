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


class GATKDoC():
    """
    classy!
    """
    
    def __init__(self,opts=None,cl=[],fargs=[],tidy=True):
        """
        """
        self.ourname = 'rgGATKCoverDepth'
        self.fargs = fargs
        self.opts = opts
        self.tidy = tidy
        self.cl = ' '.join(cl) # ready for the htmlfile output
        self.delme = []
        killme = string.punctuation + string.whitespace
        trantab = string.maketrans(killme,'_'*len(killme))
        self.title = self.opts.title.translate(trantab)
        self.tlogname = os.path.join(self.opts.outdir,'%s_rg%s_Log.txt' % (self.title,self.ourname))
        self.tlog = open(self.tlogname,'w')
        self.info = '%s on %s at %s' % (self.ourname,self.title,timenow())
        try:
            os.makedirs(self.opts.outdir)
            self.tlog.write('# made out dir %s\n' % self.opts.outdir) 
        except:
            pass
        
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
        T DepthOfCoverage
        -R /path/to/your/reference.fasta
        -I /path/to/your/bam_file.bam
        -o /path/to/your/output_file
        UGH - gatk insists that input files have a .bam extension.

        """
        fht,fakebam = tempfile.mkstemp(dir=self.opts.outdir,suffix='stupidGATKfakebamextension.bam')
        os.unlink(fakebam)
        self.delme.append(fakebam)
        os.symlink(self.opts.input,fakebam)    
        outcoverage = os.path.join(self.opts.outdir,'rgGATK_outcoverdepth.%s' % self.opts.outputFormat)    
        cl = ['java -Xmx%s' % self.opts.maxjheap,'-jar',self.opts.gatkjar,'-T DepthOfCoverage -R', self.opts.refseqfasta]
        cl += ['-I',fakebam,'-U ALLOW_UNINDEXED_BAM','-o',outcoverage,'--outputFormat',self.opts.outputFormat]
        if self.opts.minMappingQuality > "":
            cl += ['--minMappingQuality', self.opts.minMappingQuality] # needed so we don't need the .bai index file
        if self.opts.minBaseQuality > '':
            cl += ['--minBaseQuality',self.opts.minBaseQuality]
        for f in self.fargs: # pass the flags - display more compact as a multiselect list?
            if f in opts.flags:
                cl.append('--%s' % f)
        if self.opts.summaryCoverageThreshold <> None:
            cl += ['--summaryCoverageThreshold %s' % x for x in self.opts.summaryCoverageThreshold if x <> 'None']
        if self.opts.partitionType <> None:
            cl += ['--partitionType %s' % x for x in self.opts.partitionType if x <> 'None']
        self.run(cl)
        self.tlog.close()
        self.cleanup()
        self.writehtml()
            
 
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
   rgGATKCoverDepth.py -i "$input_file" -n "$out_prefix" --tmp_dir "${__new_file_path__}" 
   -d "$html_file.files_path" -t "$html_file" --flags "$flags"
   --gatkjar "${GALAXY_DATA_INDEX_DIR}/shared/jars/GenomeAnalysisTK.jar" 
#if $gSrc.refGenomeSource=="indexed":
   --refseqfasta "$gSrc.indices.value"
#else
   --refseqfasta "$gSrc.ownFile"
#end if
#if $minMappingQuality > "":
   --minMappingQuality "$minMappingQuality"
#end if
#if $minBaseQuality > '':
   --minBaseQuality "$minBaseQuality"
#end if
  </command>
    '''
    fargs = ['printBaseCounts','omitLocusTable','omitIntervals','omitDepthOutputAtEachBase','omitSampleSummary','includeDeletions','ignoreDeletionSites']
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-n', '--title', default="GATK Recalibrate")
    op.add_option('--refseqfasta', default="")
    op.add_option('-t', '--htmlout', default="")
    op.add_option('-d', '--outdir', default="")
    op.add_option('-x', '--maxjheap', default='4g')
    op.add_option('--tmp_dir', default='/tmp')
    op.add_option('-g','--gatkjar',default='')
    op.add_option('--minMappingQuality', default="")
    op.add_option('--minBaseQuality', default="")
    op.add_option('--flags', type="string", action="append") 
    op.add_option('--outputFormat', default="csv")
    op.add_option('--partitionType', type="string", action="append") 
    op.add_option('--summaryCoverageThreshold', type="string", action="append")
    opts, args = op.parse_args()
    # flag arguments presented as a multiselect to save form size
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
    x = GATKDoC(opts=opts,cl=sys.argv,fargs=fargs)
    x.runGATK()

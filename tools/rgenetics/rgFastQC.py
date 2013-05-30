"""
# May 2013 ross added check for bogus gz extension - fastqc gets confused
# added sanitizer for user supplied name
# removed shell and make cl a sequence for Popen call
# ross lazarus August 10 2012 in response to anon insecurity report
wrapper for fastqc

called as
  <command interpreter="python">
    rgFastqc.py -i $input_file -d $html_file.files_path -o $html_file -n "$out_prefix"
  </command>



Current release seems overly intolerant of sam/bam header strangeness
Author notified...


"""
import re
import os
import sys
import subprocess
import optparse
import shutil
import tempfile
from rgutils import getFileString
import zipfile
import gzip

class FastQC():
    """wrapper
    """
    
    
    def __init__(self,opts=None):
        assert opts <> None
        self.opts = opts
        
        
    def run_fastqc(self):
        """
        In batch mode fastqc behaves not very nicely - will write to a new folder in
        the same place as the infile called [infilebasename]_fastqc
    rlazarus@omics:/data/galaxy/test$ ls FC041_1_sequence_fastqc
    duplication_levels.png  fastqc_icon.png          per_base_n_content.png         per_sequence_gc_content.png       summary.txt
    error.png               fastqc_report.html       per_base_quality.png           per_sequence_quality.png          tick.png
    fastqc_data.txt         per_base_gc_content.png  per_base_sequence_content.png  sequence_length_distribution.png  warning.png

        """
        serr = ''
        dummy,tlog = tempfile.mkstemp(prefix='rgFastQC',suffix=".log",dir=self.opts.outputdir)
        sout = open(tlog, 'w')
        fastq = os.path.basename(self.opts.input)
        cl = [self.opts.executable,'--outdir=%s' % self.opts.outputdir]
        if self.opts.informat in ['sam','bam']:
            cl.append('--f=%s' % self.opts.informat)
        if self.opts.contaminants <> None :
            cl.append('--contaminants=%s' % self.opts.contaminants)
        # patch suggested by bwlang https://bitbucket.org/galaxy/galaxy-central/pull-request/30
	# use a symlink in a temporary directory so that the FastQC report reflects the history input file name
        infname = self.opts.inputfilename
        linf = infname.lower()
        trimext = False
        # decompression at upload currently does NOT remove this now bogus ending - fastqc will barf
        # patched may 29 2013 until this is fixed properly
        if ( linf.endswith('.gz') or linf.endswith('.gzip') ): 
            f = gzip.open(self.opts.input)
            try:
               testrow = f.readline()
            except:
               trimext = True
            f.close()
        elif linf.endswith('bz2'):
           f = bz2.open(self.opts.input,'rb')
           try:
              f.readline()
           except:
              trimext = True
           f.close()
        elif linf.endswith('.zip'):
           if not zipfile.is_zipfile(self.opts.input):
              trimext = True
        if trimext:
           infname = os.path.splitext(infname)[0]
        fastqinfilename = re.sub(ur'[^a-zA-Z0-9_\-\.]', '_', os.path.basename(infname))
        link_name = os.path.join(self.opts.outputdir, fastqinfilename)
        os.symlink(self.opts.input, link_name)
        cl.append(link_name)        
        sout.write('# FastQC cl = %s\n' % ' '.join(cl))
        sout.flush()
        p = subprocess.Popen(cl, shell=False, stderr=sout, stdout=sout, cwd=self.opts.outputdir)
        retval = p.wait()
        sout.close()
        runlog = open(tlog,'r').readlines()
        os.unlink(link_name)
        flist = os.listdir(self.opts.outputdir) # fastqc plays games with its output directory name. eesh
        odpath = None
        for f in flist:
            d = os.path.join(self.opts.outputdir,f)
            if os.path.isdir(d):
                if d.endswith('_fastqc'):
                    odpath = d 
        hpath = None
        if odpath <> None:
            try: 
                hpath = os.path.join(odpath,'fastqc_report.html')
                rep = open(hpath,'r').readlines() # for our new html file but we need to insert our stuff after the <body> tag
            except:
                pass
        if hpath == None:
            serr = '\n'.join(runlog)       
            res =  ['## odpath=%s: No output found in %s. Output for the run was:<pre>\n' % (odpath,hpath),]
            res += runlog
            res += ['</pre>\n',
                   'Please read the above for clues<br/>\n',
                   'If you selected a sam/bam format file, it might not have headers or they may not start with @HD?<br/>\n',
                   'It is also possible that the log shows that fastqc is not installed?<br/>\n',
                   'If that is the case, please tell the relevant Galaxy administrator that it can be snarfed from<br/>\n',
                   'http://www.bioinformatics.bbsrc.ac.uk/projects/fastqc/<br/>\n',]
            return res,1,serr
        self.fix_fastqcimages(odpath)
        flist = os.listdir(self.opts.outputdir) # these have now been fixed
        excludefiles = ['tick.png','warning.png','fastqc_icon.png','error.png']
        flist = [x for x in flist if not x in excludefiles]
        for i in range(len(rep)): # need to fix links to Icons and Image subdirectories in lastest fastqc code - ugh
            rep[i] = rep[i].replace('Icons/','')
            rep[i] = rep[i].replace('Images/','')

        html = self.fix_fastqc(rep,flist,runlog)
        return html,retval,serr
        

        
    def fix_fastqc(self,rep=[],flist=[],runlog=[]):
        """ add some of our stuff to the html
        """
        bodyindex = len(rep) -1  # hope they don't change this
        footrow = bodyindex - 1 
        footer = rep[footrow]
        rep = rep[:footrow] + rep[footrow+1:]
        res = ['<div class="module"><h2>Files created by FastQC</h2><table cellspacing="2" cellpadding="2">\n']
        flist.sort()
        for i,f in enumerate(flist):
             if not(os.path.isdir(f)):
                 fn = os.path.split(f)[-1]
                 res.append('<tr><td><a href="%s">%s</a></td></tr>\n' % (fn,getFileString(fn, self.opts.outputdir)))
        res.append('</table>\n') 
        res.append('<a href="http://www.bioinformatics.bbsrc.ac.uk/projects/fastqc/">FastQC documentation and full attribution is here</a><br/><hr/>\n')
        res.append('FastQC was run by Galaxy using the rgenetics rgFastQC wrapper - see http://rgenetics.org for details and licensing\n</div>')
        res.append(footer)
        fixed = rep[:bodyindex] + res + rep[bodyindex:]
        return fixed # with our additions


    def fix_fastqcimages(self,odpath):
        """ Galaxy wants everything in the same files_dir
        """
        icpath = os.path.join(odpath,'Icons')
        impath = os.path.join(odpath,'Images')
        for adir in [icpath,impath,odpath]:
            if os.path.exists(adir):
                flist = os.listdir(adir) # get all files created
                for f in flist:
                   if not os.path.isdir(os.path.join(adir,f)):
                       sauce = os.path.join(adir,f)
                       dest = os.path.join(self.opts.outputdir,f)
                       shutil.move(sauce,dest)
                os.rmdir(adir)

    

if __name__ == '__main__':
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-j', '--inputfilename', default=None)    
    op.add_option('-o', '--htmloutput', default=None)
    op.add_option('-d', '--outputdir', default="/tmp/shortread")
    op.add_option('-f', '--informat', default='fastq')
    op.add_option('-n', '--namejob', default='rgFastQC')
    op.add_option('-c', '--contaminants', default=None)
    op.add_option('-e', '--executable', default='fastqc')
    opts, args = op.parse_args()
    assert opts.input <> None
    assert os.path.isfile(opts.executable),'##rgFastQC.py error - cannot find executable %s' % opts.executable
    if not os.path.exists(opts.outputdir): 
        os.makedirs(opts.outputdir)
    f = FastQC(opts)
    html,retval,serr = f.run_fastqc()
    f = open(opts.htmloutput, 'w')
    f.write(''.join(html))
    f.close()
    if retval <> 0:
         print >> sys.stderr, serr # indicate failure
         
    


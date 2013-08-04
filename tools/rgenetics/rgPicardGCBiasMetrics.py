import os,string,sys,optparse,shutil
from subprocess import Popen
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,timenow,PicardBase

progname = os.path.split(sys.argv[0])[1]

'''
picard wrapper
remember to set VALIDATION_STRINGENCY=LENIENT or you will go crazy like mike and I already did...

'''


class PicardGC(PicardBase):
    """ simple class to wrap gc bias
    """
    
    def __init__(self,opts=None):
        """
        """
        PicardBase.__init__(self,opts=opts)
        assert os.path.isfile(self.opts.ref),'PicardGC needs a reference sequence - cannot read %s' % self.opts.ref
        self.fakefasta = os.path.join(self.opts.outdir,'%s_fake.fasta' % os.path.basename(self.opts.ref))
        try:
            os.symlink(self.opts.ref, self.fakefasta)
        except:
            s = '## unable to symlink %s to %s - different devices? May need to replace with shutil.copy'
            info = s
            shutil.copy(self.opts.ref, self.fakefasta)
        self.title = self.opts.title.translate(self.trantab)
        
    def runGC(self):
        """
        """
        x = 'rgPicardGCBiasMetrics'
        pdfname = '%s.pdf' % x
        jpgname = '%s.jpg' % x
        tempout = os.path.join(self.opts.outdir,'rgPicardGCBiasMetrics.out')
        temppdf = os.path.join(self.opts.outdir,pdfname)
        temptab = os.path.join(self.opts.outdir,'rgPicardGCBiasMetrics.xls')
        self.clparams['R='] = self.fakefasta                 
        self.clparams['WINDOW_SIZE='] = self.opts.windowsize
        self.clparams['MINIMUM_GENOME_FRACTION='] = self.opts.mingenomefrac
        self.clparams['INPUT='] = self.opts.input
        self.clparams['OUTPUT='] = tempout
        self.clparams['TMP_DIR='] = self.opts.tmpdir
        self.clparams['CHART_OUTPUT='] = temppdf
        self.clparams['SUMMARY_OUTPUT='] = temptab
        self.clparams['VALIDATION_STRINGENCY='] = 'LENIENT'   
        self.runPic()
        if os.path.isfile(temppdf):
            cl2 = ['convert','-resize x400',temppdf,os.path.join(self.opts.outdir,jpgname)] # make the jpg for fixPicardOutputs to find
            s = self.runCL(cl=cl2,output_dir=self.opts.outdir)
        else:
            s='### runGC: Unable to find pdf %s - please check the log for the causal problem\n' % temppdf
        lf = open(self.log_filename,'a')
        lf.write(s)
        lf.write('\n')
        lf.close()
        os.unlink(self.fakefasta)
        self.fixPicardOutputs(tempout=temptab,output_dir=self.opts.outdir,
          html_output=self.opts.htmloutput,progname=progname, maxloglines=200)


if __name__ == '__main__':
    '''
    called as
  <command interpreter="python">
    rgPicardGCBiasMetrics.py -i "$input_file" -d "$html_file.files_path" -o "$html_file"
    -w "$windowsize" -m "$mingenomefrac" -n "$out_prefix" --tmp_dir "${__new_file_path__}"
    -j ${GALAXY_DATA_INDEX_DIR}/shared/jars/CollectGcBiasMetrics.jar -x "$maxheap"
#if $genomeSource.refGenomeSource == "history":
    -r "$genomeSource.ownFile"
#else:
    -r "$genomeSource.indices"
#end if

    called as
    java -jar /share/shared/galaxy/tool-data/shared/jars/CollectGcBiasMetrics.jar REFERENCE_SEQUENCE="hg18.fasta"
    MINIMUM_GENOME_FRACTION=0.00001 INPUT=test.bam OUTPUT=picardASMetrics.txt OUTPUT=test.txt CHART_OUTPUT=test.pdf
    WINDOW_SIZE=100 VALIDATION_STRINGENCY=LENIENT

    '''
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-o', '--htmloutput', default=None)
    op.add_option('-d', '--outdir', default="/tmp/GCMetrics")
    op.add_option('-r', '--ref', default='')
    op.add_option('', '--own_ref', default='')
    op.add_option('-w', '--windowsize', default='100')
    op.add_option('-m', '--mingenomefrac', default='0.00001')
    op.add_option('-j', '--jar', default='')
    op.add_option('-l', '--log', default=None)
    op.add_option('-n', '--title', default='GC Bias Metrics')
    op.add_option('-x', '--maxjheap', default='4g')
    op.add_option('--tmpdir', default='/share/shared/tmp')
    opts, args = op.parse_args()
    g = PicardGC(opts=opts)
    g.runGC()

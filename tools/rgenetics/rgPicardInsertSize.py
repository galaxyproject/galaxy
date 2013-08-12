import os,string,sys,optparse,shutil,tempfile 
from subprocess import Popen 
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,timenow, getFileString, PicardBase 
progname = os.path.split(sys.argv[0])[1]

""" 
insert size metrics 
Copyright ross lazarus oct 31 (happy halloween!) 
All rights reserved 
Released for rgenetics under the LGPL 
"""



class insertSize(PicardBase):
    """
    insertsize metrics 
    """
    
    def __init__(self,opts=None,cl=[],tidy=False):
        """
        """
        PicardBase.__init__(self,opts=opts)
        self.tidy = tidy
        self.isPDF = 'InsertSizeHist.pdf'
        self.pdfpath = os.path.join(self.opts.outdir,self.isPDF)
    
    def doIS(self):
        """
        """
        hout = 'InsertSizeOut.txt'
        histpdf = self.isPDF
        self.clparams['I='] = opts.input
        self.clparams['O='] = hout
        self.clparams['HISTOGRAM_FILE='] = histpdf
        self.clparams['VALIDATION_STRINGENCY='] = 'LENIENT'
        if self.opts.taillimit <> '0':
            self.clparams['TAIL_LIMIT='] = self.opts.taillimit
        if self.opts.histwidth <> '0':
            self.clparams['HISTOGRAM_WIDTH='] = self.opts.histwidth
        if float(self.opts.minpct) > 0.0:
            self.clparams['MINIMUM_PCT='] = self.opts.minpct
        self.runPic()   
        if os.path.exists(self.pdfpath):
            cl2 = ['mogrify', '-format jpg -resize x400 %s' % (self.pdfpath)]
            s = self.runCL(cl=cl2,output_dir=self.opts.outdir)
        else:
            s = 'Unable to find expected pdf file %s\n' % self.pdfpath
        lf = open(self.log_filename,'a')
        lf.write(s)
        lf.write('\n')
        lf.close()
        self.fixPicardOutputs(tempout=os.path.join(self.opts.outdir,hout),output_dir=self.opts.outdir,
                  html_output=self.opts.htmlout,progname=progname)

    
if __name__ == '__main__':
    '''
    <command interpreter="python">
   rgPicardInsertSize.py -i "$input_file" -n "$out_prefix" -o "$out_file" --tmp_dir "${__new_file_path__}"
   -l "$tailLimit" -w "$histWidth" -p "$minPct" -n "$newformat"
   -j "${GALAXY_DATA_INDEX_DIR}/shared/jars/CollectInsertSizeMetrics.jar" -d "$html_file.files_path" -t "$html_file"
  </command>
    '''
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-n', '--title', default="Insert size metrics")
    op.add_option('-l', '--taillimit', default="0")
    op.add_option('-w', '--histwidth', default="0")
    op.add_option('-p', '--minpct', default="0.01")
    op.add_option('-t', '--htmlout', default="")
    op.add_option('-d', '--outdir', default="")
    op.add_option('-x', '--maxjheap', default='2g')
    op.add_option('--tmpdir', default='/tmp')
    op.add_option('-j','--jar',default='')
    opts, args = op.parse_args()
    x = insertSize(opts=opts)
    x.doIS()

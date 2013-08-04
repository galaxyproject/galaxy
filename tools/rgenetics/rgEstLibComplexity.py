import os,string,sys,optparse,shutil,tempfile 
from subprocess import Popen 
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,timenow, getFileString, PicardBase
progname = os.path.split(sys.argv[0])[1]

""" 
Estimate library complexity
Copyright ross lazarus oct 31 (happy halloween!) 
All rights reserved released for rgenetics under the LGPL 
"""



class libraryComplexity(PicardBase):
    """
    wrapper
    """
    
    def __init__(self,opts=None):
        """
        """
        PicardBase.__init__(self, opts=opts)
        self.outtxt = 'estlibcompout.txt'
        
    
  
        
    def doLC(self):
        """ build dict for cl and run. clean up outputs
        """

        self.clparams['I='] = opts.input
        self.clparams['O='] = self.outtxt
        self.clparams['VALIDATION_STRINGENCY='] = 'LENIENT'
        if float(self.opts.minid) > 0:
            self.clparams['MIN_IDENTICAL_BASES='] = self.opts.minid
        if float(self.opts.maxdiff) > 0.0:
            self.clparams['MAX_DIFF_RATE='] = self.opts.maxdiff
        if float(self.opts.minmeanq) > 0:
            self.clparams['MIN_MEAN_QUALITY=']  = self.opts.minmeanq
        if self.opts.readregex > '':
            self.clparams['READ_NAME_REGEX='] = '"%s"' % self.opts.readregex
        if float(self.opts.optdupedist) > 0:
            self.clparams['OPTICAL_DUPLICATE_PIXEL_DISTANCE=']  = self.opts.optdupedist
        self.runPic()
        self.fixPicardOutputs(tempout=os.path.join(self.opts.outdir,self.outtxt),output_dir=self.opts.outdir,
                  html_output=self.opts.htmlout,progname=progname)

           
if __name__ == '__main__':
    '''
    <command interpreter="python">
   rgEstLibComplexity.py -i "$input_file" -n "$out_prefix" --tmp_dir "${__new_file_path__}" --minid "$minID"
   --maxdiff "$maxDiff" --minmeanq "$minMeanQ" --readregex "$readRegex" --optdupedist "$optDupeDist"
   -j "${GALAXY_DATA_INDEX_DIR}/shared/jars/EstimateLibraryComplexity.jar" -d "$html_file.files_path" -t "$html_file"
   </command>

    '''
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-n', '--title', default="Estimate Library Complexity")
    op.add_option('--minid', default="5")
    op.add_option('--maxdiff', default="0.03")
    op.add_option('--minmeanq', default="20")
    op.add_option('--readregex', default="[a-zA-Z0-9]+:[0-9]:([0-9]+):([0-9]+):([0-9]+).*")
    op.add_option('--optdupedist', default="100")
    op.add_option('-t', '--htmlout', default="")
    op.add_option('-d', '--outdir', default="")
    op.add_option('-x', '--maxjheap', default='2g')
    op.add_option('--tmpdir', default='/tmp')
    op.add_option('-j','--jar',default='')
    opts, args = op.parse_args()
    tool = libraryComplexity(opts=opts)
    tool.doLC()
    

import os,string,sys,optparse,shutil,tempfile 
from subprocess import Popen 
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,timenow, getFileString, PicardBase
progname = os.path.split(sys.argv[0])[1]

""" 
Mark duplicates with Picard
Copyright ross lazarus nov 17 2010
All rights reserved released for rgenetics under the LGPL 
"""



class markDups(PicardBase):
    """
    picard mark duplicates  
    """
    
    def __init__(self,opts=None,tidy=True):
        """
        """
        PicardBase.__init__(self,opts=opts)
        self.tidy = tidy
        self.metricstxt = 'rgPicardMarkDupsout.txt'
        self.metricstab = os.path.join(self.opts.outdir,self.metricstxt)
        self.inputext = opts.inputext
    
    
    def doMD(self):
        """
        """
        self.input = self.opts.input # default
        if self.inputext == 'sam':
            s,tinfile = self.samToBam(infile=self.opts.input,outdir=self.opts.outdir)
            self.delme.append(tinfile)
            self.input = tinfile     
        if self.opts.assumesorted == 'false': # we need to sort input
            self.realinput = self.input
            self.input = '%s.sorted' % (os.path.basename(self.realinput))
            self.input = os.path.join(self.opts.outdir,self.input)
            s = self.sortSam(self.realinput,self.input,self.opts.outdir)
            self.input = '%s.%s' % (self.input,self.inputext) # samtools sort adds this
            self.delme.append(self.input)
        self.clparams['I='] = self.input
        self.clparams['O='] = self.opts.outbam
        self.clparams['M='] = self.metricstab
        self.clparams['VALIDATION_STRINGENCY='] = 'LENIENT'
        if self.opts.remdups == 'true':
            self.clparams['REMOVE_DUPLICATES='] = self.opts.remdups
        self.clparams['ASSUME_SORTED='] = 'true' # we always sort if false
        if self.opts.readregex > '':
            self.clparams['READ_NAME_REGEX='] = '"%s"' % self.opts.readregex
        if float(self.opts.optdupedist) > 0:
            self.clparams['OPTICAL_DUPLICATE_PIXEL_DISTANCE='] = self.opts.optdupedist
        self.runPic()
        self.fixPicardOutputs(tempout=self.metricstab,output_dir=self.opts.outdir,maxloglines=200,
                  html_output=self.opts.htmlout,progname=progname)
                  
 
    
if __name__ == '__main__':
    '''
      <command interpreter="python">
   rgPicardMarkDups.py -i "$input_file" -n "$out_prefix" --tmp_dir "${__new_file_path__}" 
#if $remdupes:
  --remdups "true"
#end if
    --assumesorted "$assumeSorted" --readregex "$readRegex" --optdupedist "$optDupeDist"
   -j "${GALAXY_DATA_INDEX_DIR}/shared/jars/MarkDuplicates.jar" -d "$html_file.files_path" -t "$html_file"
  </command>


    '''
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-e', '--inputext', default=None)
    op.add_option('-o', '--outbam', default=None)
    op.add_option('-n', '--title', default="markDupes")
    op.add_option('--remdups', default='false') 
    op.add_option('--assumesorted', default='true') 
    op.add_option('--readregex', default="[a-zA-Z0-9]+:[0-9]:([0-9]+):([0-9]+):([0-9]+).*")
    op.add_option('--optdupedist', default="100")
    op.add_option('-t', '--htmlout', default="")
    op.add_option('-d', '--outdir', default="")
    op.add_option('-x', '--maxjheap', default='2g')
    op.add_option('--tmpdir', default='/tmp')
    op.add_option('-j','--jar',default='')
    opts, args = op.parse_args()
    opts.sortme = opts.assumesorted == 'false'
    assert opts.input <> None
    assert opts.outbam <> None
    assert os.path.isfile(opts.input)
    assert os.path.isfile(opts.jar)
    try:
        os.makedirs(opts.tmp_dir)
    except:
        pass
    try:
        os.makedirs(opts.outdir)
    except:
        pass
    x = markDups(opts=opts)
    x.doMD()

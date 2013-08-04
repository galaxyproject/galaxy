import os, sys
import shutil, tempfile
import optparse
import string

from rgutils import timestamp, PicardBase

progname = os.path.split(sys.argv[0])[1]

"""
fix mate pair information
Copyright ross lazarus oct 31 (happy halloween!)
All rights reserved
released for rgenetics under the LGPL
"""



class fixMate(PicardBase):
    
    def __init__(self, opts=None):
        PicardBase.__init__(self,opts=opts)
        
    def runFixMate(self):
        fd,self.tempout = tempfile.mkstemp(prefix='tempbam') 
        self.clparams['I='] = self.opts.input
        self.clparams['O='] = self.tempout
        self.clparams['SORT_ORDER='] = self.opts.sortorder
        self.runPic()
        print ''.join(open(self.log_filename,'r').readlines())
        # Picard tool produced intermediate bam file. Depending on the
        # desired format, we either just move to final location or create
        # a sam version of it.
        if self.opts.newformat == 'sam':
            tlog, tempsam = self.bamToSam(self.tempout,self.opts.outdir)
            shutil.move(tempsam,os.path.abspath(self.opts.output))
        else:
            shutil.move(self.tempout, os.path.abspath(self.opts.output))       
        
if __name__ == '__main__':
    '''
    <command interpreter="python">
    rgPicardFixMate.py -i "$input_file" -o "$out_file" --tmp_dir "${__new_file_path__}"  
    --newformat "$newformat" -j "${GALAXY_DATA_INDEX_DIR}/shared/jars/FixMateInformation.jar"
   </command>
    '''
    op = optparse.OptionParser()
    op.add_option('-j','--jar')
    op.add_option('-i', '--input', default=None)
    op.add_option('--input-type', default=None)
    op.add_option('-o', '--output', default=None)
    op.add_option('--newformat', default='bam')
    op.add_option('-x', '--maxjheap', default='2g')
    op.add_option('--tmpdir', default='/tmp')
    op.add_option('-n', '--title', default='')
    op.add_option('-v','--verbose', action='store_true')
    op.add_option('-s', '--sortorder', default='query')
    opts, args = op.parse_args()
    opts.outdir = opts.tmpdir
    fm = fixMate(opts)
    fm.runFixMate()



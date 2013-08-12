import os,string,sys,optparse,shutil
from subprocess import Popen
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,timenow, PicardBase

progname = os.path.split(sys.argv[0])[1]


'''
picard wrapper
remember to set VALIDATION_STRINGENCY=LENIENT or you will go crazy like mike and I already did...

'''
# note base.css has a table.colored but it sucks

usage_msg = """
python rgPicardHsMetrics.py -i $input_file -d $html_file.files_path -o $html_file
    -b $bait_bed -t $target_bed -n "$out_prefix" --tmp_dir "${__new_file_path__}"
    -j ${GALAXY_DATA_INDEX_DIR}/shared/jars/CalculateHsMetrics.jar  
"""




class hsMetrics(PicardBase):
    
    def __init__(self, opts=None):
        PicardBase.__init__(self,opts=opts)
        self.baitf = os.path.join(self.opts.outdir,'rgPicardHsMetrics.bait')
        self.targetf = os.path.join(self.opts.outdir,'rgPicardHsMetrics.target')

    def makePicInterval(self,inbed=None,outf=None):
        """ picard wants bait and target files to have the same header length as the incoming bam/sam 
        why the fock this is enforced seems really bizarro but it is - attempts to construct
        a meaningful (ie accurate) representation fail because of this - might as well just take the frikking 
        bed without a header, dumbos.
 
        """
        assert inbed <> None
        bed = open(inbed,'r').readlines()
        self.thead = os.path.join(self.opts.outdir,'tempSamHead.txt')
        if self.opts.intype == 'sam':
            cl = ['samtools view -H -S',self.opts.input,'>',self.thead]
        else:
            cl = ['samtools view -H',self.opts.input,'>',self.thead]
        self.runCL(cl=cl,output_dir=self.opts.outdir)
        head = open(self.thead,'r').readlines()
        s = '## got %d rows of header\n' % (len(head))
        lf = open(self.log_filename,'a')
        lf.write(s)
        lf.close()
        o = open(outf,'w')
        o.write(''.join(head))
        o.write(''.join(bed))
        o.close()
        return outf                 

    def runHS(self):
        """
        """
        self.baitf = self.makePicInterval(self.opts.bait,self.baitf)
        if opts.target == opts.bait: # same file sometimes
            self.targetf = self.baitf
        else:
            self.targetf = self.makePicInterval(self.opts.target,self.targetf)   
        tempout = os.path.join(opts.outdir,'rgPicardHsMetrics.out')


        self.clparams['BAIT_INTERVALS='] = self.baitf
        self.clparams['TARGET_INTERVALS='] = self.targetf
        self.clparams['INPUT='] = os.path.abspath(self.opts.input)
        self.clparams['OUTPUT='] = tempout
        self.clparams['VALIDATION_STRINGENCY='] = 'LENIENT'
        self.clparams['TMP_DIR='] = self.opts.tmpdir
        self.runPic()
        self.fixPicardOutputs(tempout=tempout, output_dir=self.opts.outdir, 
                         html_output=os.path.join(self.opts.outdir, self.opts.htmloutput),
                         progname=progname)
      

if __name__ == '__main__':
    '''
    run as
    java -jar /share/shared/galaxy/tool-data/shared/jars/CalculateHsMetrics.jar 
    BAIT_INTERVALS=test.pic TARGET_INTERVALS=test.pic INPUT=test.bam OUTPUT=picardHsMetrics.txt

    called as <command interpreter="python">
    rgPicardHsMetrics.py -i $input_file -d $html_file.files_path -o $html_file
    -b $bait_bed -t $target_bed -n "$out_prefix" --tmp_dir "${__new_file_path__}"
    -j ${GALAXY_DATA_INDEX_DIR}/shared/jars/CalculateHsMetrics.jar 
  </command>
    '''
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    op = optparse.OptionParser(usage=usage_msg)
    op.add_option('-i', '--input')
    op.add_option('-y','--intype',default='bam')
    op.add_option('-o', '--htmloutput')
    op.add_option('-d', '--outdir', default="/tmp/HsMetrics")
    op.add_option('-b', '--bait')
    op.add_option('-t', '--target')
    op.add_option('-j', '--jar', default='')
    op.add_option('-l', '--log', default='')
    op.add_option('-n', '--title', default='HsMetrics')
    op.add_option('-x', '--maxjheap', default='2g')
    op.add_option('--tmpdir', default='/tmp')
    opts, args = op.parse_args()
    h = hsMetrics(opts=opts)
    h.runHS()



    
    

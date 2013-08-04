import os,string,sys,optparse,shutil
import shutil
import pdb
from subprocess import Popen
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,timenow,PicardBase

progname = os.path.split(sys.argv[0])[1]

'''
picard wrapper - seems to work better when NO reference sequence supplied...

remember to set VALIDATION_STRINGENCY=LENIENT or you will go crazy like mike and I already did...

'''

class PicardASM(PicardBase):
    """ simple class to wrap ASM
    """
    
    def __init__(self,opts=None):
        """
        """
        PicardBase.__init__(self,opts=opts)
        # Opts.adapters needs to be one string. If it's None, it must be coerced to empty str.
        opts.adapters = opts.adapters or ''
        self.tempout = os.path.join(self.opts.outdir,'picardAlignSumMetrics_out.txt')
        # Picard only accepts reference files that have a 'fasta' extension name
        if not self.opts.refseq.endswith('fasta'):
            new_filename = '%s.fasta' % self.opts.refseq
            destination = os.path.join(self.opts.outdir, new_filename)
            shutil.copy(os.path.abspath(self.opts.refseq), destination)
            self.opts.refseq = destination
                        
    def ASM(self):
        """
        """
        self.clparams['ASSUME_SORTED='] = self.opts.assume_sorted
        adaptorseqs = ''.join([' ADAPTER_SEQUENCE=%s' % x for x in self.opts.adapters])
        self.clparams[adaptorseqs] = ' ' # ugh
        self.clparams['IS_BISULFITE_SEQUENCED='] = self.opts.bisulphite
        self.clparams['MAX_INSERT_SIZE='] = self.opts.maxinsert
        self.clparams['OUTPUT='] = self.tempout
        self.clparams['VALIDATION_STRINGENCY='] = 'LENIENT'
        self.clparams['TMP_DIR='] = self.opts.tmpdir
        if not self.opts.assume_sorted: # we need to sort input
            self.fakeinput = '%s.sorted' % self.input
            s = self.sortSam(self.input,self.fakeinput,self.opts.outdir)
            self.delme.append(self.fakeinput)
            self.clparams['INPUT='] = self.fakeinput
        else:
            self.clparams['INPUT='] = os.path.abspath(self.opts.input)            
        self.runPic()
        self.fixPicardOutputs(tempout=self.tempout, output_dir=self.opts.outdir, 
                         html_output=os.path.join(self.opts.outdir, self.opts.htmloutput),
                         progname=progname)



if __name__ == '__main__':
    '''
    run this Picard tool as
    java -jar /share/shared/galaxy/tool-data/shared/jars/CollectAlignmentSummaryMetrics.jar REFERENCE_SEQUENCE="hg18.fasta" 
    ASSUME_SORTED=true ADAPTER_SEQUENCE='' IS_BISULFITE_SEQUENCED=false MAX_INSERT_SIZE=100000 INPUT=test.bam 
    OUTPUT=picardASMetrics.txt VALIDATION_STRINGENCY=LENIENT

    called as
        rgPicardASMetrics.py -i "$input_file" -d "$html_file.files_path" -o "$html_file"
    -s "$sorted" -b "$bisulphite" -a "$adaptors" -m $maxinsert -n "$out_prefix"
    -j ${GALAXY_DATA_INDEX_DIR}/shared/jars/CollectAlignmentSummaryMetrics.jar
#if $genomeSource.refGenomeSource == "history":
    -r "$genomeSource.ownFile"
#else:
    -r "$genomeSource.indices"
#end if

    '''
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-o', '--htmloutput', default=None)
    op.add_option('-d', '--outdir', default="/tmp/AsMetrics")
    op.add_option('-r', '--refseq', default='')
    op.add_option('-s', '--assume-sorted', default='true')
    op.add_option('-a', '--adapters', action='append', type="string")
    op.add_option('-b', '--bisulphite', default='false')
    op.add_option('-m', '--maxinsert', default='100000')
    op.add_option('-j', '--jar', default='')
    op.add_option('-l', '--log', default=None)
    op.add_option('-n', '--title', default='Alignment Summary Metrics')
    op.add_option('-x', '--maxjheap', default='2g')
    op.add_option('--tmpdir', default='/tmp')
    opts, args = op.parse_args()
    p = PicardASM(opts=opts)
    p.ASM()



        


    

    
    

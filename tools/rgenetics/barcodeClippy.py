"""
barcodeClippy.py

   We have a directory like
   vgalaxy)galaxy@omics:/data/fastq$ ls
build                                    FC070_2_prediab.fastq  FC071_5_ctrl.fastq                         FC077_8_TTGTTT_HUVEC_STIM3_sequence.txt
FC057_8_AAGTAT_THP_UNSTIM1_sequence.txt  FC070_3_t2d.fastq      FC071_6_prediab.fastq                      FC084_8_AAGTAT_Platelet1_sequence.txt
FC057_8_AGAGGT_THP_STIMMP1_sequence.txt  FC070_4_ctrl.fastq     FC071_7_t2dm.fastq                         FC084_8_ATCCTT_PlateletMP1_sequence.txt
FC057_8_ATCCTT_THP_STIM1_sequence.txt    FC070_5_prediab.fastq  FC077_8_AAGTAT_HUVEC_UNSTIM1_sequence.txt  FC084_8_CACTCT_Platelet3_sequence.txt
FC057_8_CACTCT_THP_UNSTIM3_sequence.txt  FC070_6_t2d.fastq      FC077_8_AGAGGT_HUVEC_UNSTIM3_sequence.txt  FC084_8_CTGCCT_PlateletMP3_sequence.txt
FC057_8_CTGCCT_THP_STIM3_sequence.txt    FC070_7_ctrl.fastq     FC077_8_ATCCTT_HUVEC_UNSTIM2_sequence.txt  FC084_8_TCTCTT_Platelet2_sequence.txt
FC057_8_GAATGT_THP_STIMMP3_sequence.txt  FC070_8_prediab.fastq  FC077_8_CACTCT_HUVEC_STIMMP1_sequence.txt  FC084_8_TTGTTT_PlateletMP2_sequence.txt
FC057_8_TAGGTT_THP_UNSTIM2_sequence.txt  FC071_1_t2dm.fastq     FC077_8_CTGCCT_HUVEC_STIMMP2_sequence.txt  fixbc.py
FC057_8_TCTCTT_THP_STIM2_sequence.txt    FC071_2_ctrl.fastq     FC077_8_GAATGT_HUVEC_STIMMP3_sequence.txt  pip-log.txt
FC057_8_TTGTTT_THP_STIMMP2_sequence.txt  FC071_3_prediab.fastq  FC077_8_TAGGTT_HUVEC_STIM1_sequence.txt
FC070_1_ctrl.fastq                       FC071_4_t2dm.fastq     FC077_8_TCTCTT_HUVEC_STIM2_sequence.txt



   FASTA/Q Clipper

	$ fastx_clipper -h
	usage: fastx_clipper [-h] [-a ADAPTER] [-D] [-l N] [-n] [-d N] [-c] [-C] [-o] [-v] [-z] [-i INFILE] [-o OUTFILE]

	version 0.0.6
	   [-h]         = This helpful help screen.
	   [-a ADAPTER] = ADAPTER string. default is CCTTAAGG (dummy adapter).
	   [-l N]       = discard sequences shorter than N nucleotides. default is 5.
	   [-d N]       = Keep the adapter and N bases after it.
			  (using '-d 0' is the same as not using '-d' at all. which is the default).
	   [-c]         = Discard non-clipped sequences (i.e. - keep only sequences which contained the adapter).
	   [-C]         = Discard clipped sequences (i.e. - keep only sequences which did not contained the adapter).
	   [-k]         = Report Adapter-Only sequences.
	   [-n]         = keep sequences with unknown (N) nucleotides. default is to discard such sequences.
	   [-v]         = Verbose - report number of sequences.
			  If [-o] is specified,  report will be printed to STDOUT.
			  If [-o] is not specified (and output goes to STDOUT),
			  report will be printed to STDERR.
	   [-z]         = Compress output with GZIP.
	   [-D]		= DEBUG output.
	   [-i INFILE]  = FASTA/Q input file. default is STDIN.
	   [-o OUTFILE] = FASTA/Q output file. default is STDOUT.

   
"""

import os
import glob
import subprocess

class clippy:
    def __init__(self,exe='',adapter='',infile='',outfile='',output_dir=''):
        self.cl=[exe,'-i',infile,'-o',outfile,'-c','-v','-a',adapter]
        self.exe = exe
        self.adapter = adapter
        self.tlog = 'clippy_%s.log' % adapter
        self.output_dir=output_dir
	print 'Will write %s clipping %s from %s' % (outf,infile,adapter)

    def clip(self):
        """
        """
        sto = open(self.tlog,'w')
        x = subprocess.Popen(' '.join(self.cl),shell=True,stdout=sto,stderr=sto,cwd=self.output_dir)
        retval = x.wait()
        sto.close()
        l = open(self.tlog,'r').readlines()
        return l
            
def main(indir,outdir):
    """
    """
    g = os.path.join(indir,'FC0*_??????_*sequence.txt')
    fnames = glob.glob(g)
    print 'fnames',fnames
    dlist = [x.split('_') for x in fnames]    
    for i,infile in enumerate(fnames):
        adapter = dlist[i][2]
        outfile = os.path.join(outdir,'%s_clipped.fastq' % infile)
        c = clippy('fastx_clipper',adapter,infile,outfile,outdir)
        c.clip()
            
if __name__ == "__main__":
    if len(sys.argv) < 3:
         print 'clippy sad. need input and output directories on command line to make clippy happy'
         sys.exit(1)
    main(sys.argv[1],sys.argv[2])
    
            


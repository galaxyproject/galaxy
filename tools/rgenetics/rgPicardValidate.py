import os, sys
import shutil, tempfile
import optparse
import string
from subprocess import Popen

import pysam

from rgutils import PicardBase

progname = os.path.split(sys.argv[0])[1]
verbose = True
tidy = False


class PicardValidate(PicardBase):
    '''picard wrapper for validatesam tool
    '''

    
    def __init__(self,opts=None):
        """
        """
        PicardBase.__init__(self, opts=opts)
        self.tempout = os.path.join(opts.outdir,'rgPicardValidate.out') 
        self.temptab = os.path.join(opts.outdir,'rgPicardValidate.xls')
        self.sortedfile = os.path.join(self.opts.outdir,'rgcleansam.sorted')
    
     

    def cleanSam(self, insam=None, newsam=None, picardErrors=[],outformat=None):
        """
        stub - need to do the work of removing all the error sequences
        pysam is cool
        infile = pysam.Samfile( "-", "r" )
        outfile = pysam.Samfile( "-", "w", template = infile )
        for s in infile: outfile.write(s)
        
        errors from ValidateSameFile.jar look like
        WARNING: Record 32, Read name SRR006041.1202260, NM tag (nucleotide differences) is missing
        ERROR: Record 33, Read name SRR006041.1042721, Empty sequence dictionary.
        ERROR: Record 33, Read name SRR006041.1042721, RG ID on SAMRecord not found in header: SRR006041

        """
        assert os.path.isfile(insam), 'rgPicardValidate cleansam needs an input sam file - cannot find %s' % insam
        assert newsam <> None, 'rgPicardValidate cleansam needs an output new sam file path'
        removeNames = [x.split(',')[1].replace(' Read name ','') for x in picardErrors if len(x.split(',')) > 2]
        remDict = dict(zip(removeNames,range(len(removeNames))))
        infile = pysam.Samfile(insam,'rb')
        info = 'found %d identifiable error sequences in picardErrors out of %d' % (len(removeNames),len(picardErrors))
        if len(removeNames) > 0:
            outfile = pysam.Samfile(newsam,'wb',template=infile)
            i = 0
            for row in infile:
                if not remDict.get(row.qname,None): # not to be cleaned
                    outfile.write(row)
                else:
                    i += 1
            info = '%s\n%s' % (info, 'Wrote %s after removing %d rows from %s' % (newsam,i,insam))
            outfile.close()
            infile.close()
        else: # we really want a nullop or a simple pointer copy
            infile.close()
            if newsam:
                shutil.copy(insam,newsam)
        lf = open(self.log_filename,'a')
        lf.write(info)
        lf.write('\n')
        lf.close()
                
    def validate(self):
        """
        """
        self.stf = open(self.log_filename,'w')
        tlog = None
        if self.opts.datatype == 'sam': # need to work with a bam 
            tlog,tempbam = self.samToBam(opts.input,opts.outdir)
            self.delme.append(tempbam)
            try:
                tlog = self.sortSam(tempbam,self.sortedfile,self.opts.outdir)
            except:
                print '## exception on sorting sam file %s' % self.opts.input
        else: # is already bam
            try:
                tlog = self.sortSam(self.opts.input,self.sortedfile,self.opts.outdir)
            except: # bug - [bam_sort_core] not being ignored - TODO fixme
                print '## exception on sorting bam file %s' % self.opts.input
        if tlog:
            print '##tlog=',tlog
            self.stf.write(tlog)
            self.stf.write('\n')
        self.sortedfile = '%s.bam' % self.sortedfile        

        self.clparams['O='] = self.tempout
        self.clparams['TMP_DIR='] = self.opts.tmpdir
        self.clparams['I='] = self.sortedfile
        if self.opts.maxoutput == '0':
            self.opts.maxoutput = '65535'
        self.clparams['MAX_OUTPUT='] = self.opts.maxoutput
        if self.opts.ignore[0] <> 'None': # picard error values to ignore
            igs = ['IGNORE=%s' % x for x in self.opts.ignore if x <> 'None']
            self.clparams[' '.join(igs)] = ' ' # ugh
        if self.opts.bisulphite.lower() <> 'false':
            self.clparams['IS_BISULFITE_SEQUENCED='] = 'true'
        if self.opts.refseq <> '':
            self.clparams['R='] = self.opts.refseq
            
        self.runPic()
         

        if self.opts.dryrun <> 'dryrun': # want to run cleansam
            if self.opts.dryrun == 'sam':
                outformat = 'sam'
                newsam = self.opts.sam
            elif self.opts.dryrun == 'bam':
                outformat = 'bam'            
                newsam = self.opts.bam
            pe = open(self.tempout,'r').readlines()
            self.cleanSam(insam=self.sortedfile, newsam=newsam, picardErrors=pe,outformat=outformat)
        else:
            self.delme.append(self.sortedfile) # not wanted
        self.stf.close()
        self.fixPicardOutputs(tempout=self.tempout, output_dir=self.opts.outdir, transpose=False,
                         html_output=os.path.join(self.opts.outdir, self.opts.htmloutput),
                         progname=progname)
 


if __name__ == '__main__':
    '''
    called as
     <command interpreter="python">
    rgPicardValidate.py -i "$input_file" --datatype "$input_file.ext" -d "$html_file.files_path" -o "$html_file"
    -t "$out_prefix" -e "$ignore" -b "$bisulphite" -m "$maxerrors" -y "$new_format"
    -j ${GALAXY_DATA_INDEX_DIR}/shared/jars/ValidateSamFile.jar
#if $genomeSource.refGenomeSource == "history":
    -r "$genomeSource.ownFile"
#elif $genomeSource.refGenomeSource=="indexed":
    -r "$genomeSource.indices"
#end if
#if $new_format=='sam':
 --sam "$out_file"
#elif $new_format=='bam':
 --bam "$out_file"
#end if
  </command>

    '''
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-o', '--htmloutput', default=None)
    op.add_option('-d', '--outdir', default="/tmp/validateSam") 
    op.add_option('-r', '--refseq', default='')
    op.add_option('-e', '--ignore', action='append', type="string")
    op.add_option('-y', '--dryrun', default='dryrun')
    op.add_option('--sam', default='None')
    op.add_option('--bam', default='None')
    op.add_option('-m', '--maxoutput', default='0')
    op.add_option('-b', '--bisulphite', default='false')
    op.add_option('-j', '--jar', default='')
    op.add_option('-l', '--log', default='rgValidateSam.log')
    op.add_option('-t', '--title', default='Validate Sam/Bam')
    op.add_option('-x', '--maxjheap', default='8g')
    op.add_option('--tmpdir', default='/tmp')
    op.add_option('--datatype', default='bam')
    opts, args = op.parse_args()
    try:
        os.makedirs(opts.outdir)
    except:
        pass
    assert opts.input <> None
    p = PicardValidate(opts=opts)
    p.validate()
       

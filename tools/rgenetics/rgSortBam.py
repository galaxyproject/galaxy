import os,string,sys,optparse,shutil,tempfile
from subprocess import Popen
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,timenow,getFileString
progname = os.path.split(sys.argv[0])[1]

"""
From http://www.broadinstitute.org/gsa/wiki/index.php/Input_files_for_the_GATK
- Do we always need to do this after bwa has generated an alignment?
Eeesh..

Fixing BAM files with alternative sortings

The GATK requires that the BAM file be sorted in the same order as the
reference. Unfortunately, many BAM files have headers that are sorted
in some other order -- lexicographical order is a common alternative.
To resort the BAM file so that it matches your reference, you will
have to strip out the BAM file's reference, replacing it with the
reference from your header. To do this:
Convert the bam -> sam, stripping away the header
Reimport the bam, using your reference's fai as the ref_index. This
step results in an 'unsorted' bam with a correctly sorted header.
Sort the bam file using 'samtools sort'.
Index the file
For example:
samtools view <your file>.bam > -o <new file>.sam
samtools import <your reference>.fai <your file>.sam <your
file>.sorted_header.bam
samtools sort <your file>.sorted_header.bam <your file>.sorted
samtools index <your file>.sorted.bam

galaxy users will need to option to replace headers using a built in or history fasta index
so much stuffing around needed below to preserve any existing metadata
and to index a history fasta if needed
"""


class sortBAM():
    """
    replace a header in a sam or bam
    """
    
    def __init__(self,opts=None,cl=[],tidy=True):
        """
        """
        self.ourname = 'rgSortBam'
        self.opts = opts
        self.tidy = tidy
        self.cl = ' '.join(cl) # ready for the htmlfile output
        self.delme = []
        killme = string.punctuation + string.whitespace
        trantab = string.maketrans(killme,'_'*len(killme))
        self.title = self.opts.title.translate(trantab)
        fd,self.tlogname = tempfile.mkstemp(dir=self.opts.tmpdir,suffix='rgSortBam.log')
        self.tlog = open(self.tlogname,'w')
        self.info = '%s on %s at %s' % (self.ourname,self.opts.title,timenow())
    
    def getSamExtraHeaders(self,tempsam=None):
        """
        """
        ehead = []
        assert tempsam <> None
        f = open(tempsam,'r')
        for row in f:
            if not row.startswith('@'): # end of headers
                break
            if not row.startswith('@SQ') and not row.startswith('@HD'):
                ehead.append(row) # we sort so the HD header is bogus
        f.close()
        return ehead

    def run(self,cl=None,redir=True):
        assert cl <> None
        fd,templog = tempfile.mkstemp(dir=self.opts.outdir,suffix='rgSortBamRun.log')
        tlf = open(templog,'w')
        if redir:
           process = Popen(' '.join(cl), shell=True, stderr=tlf, stdout=tlf, cwd=self.opts.outdir)
        else: # samtools calmd outputs to stdout so we only capture stderr
           process = Popen(' '.join(cl), shell=True, stderr=tlf, cwd=self.opts.outdir)
        rval = process.wait()
        tlf.close()
        tlogs = open(templog,'r').readlines()
        if len(tlogs) > 1:
            if len(tlogs) > 50:
                s = '## executing %s returned status %d and truncated log (stdout/stderr) records: \n%s\n...\n%s\n' % (''.join(cl),rval,''.join(tlogs[0:25]),''.join(tlogs[-25:]))
            else:
                s = '## executing %s returned status %d and log (stdout/stderr) records: \n%s\n' % (' '.join(cl),rval,tlogs)
        else:
            s = '## executing %s returned status %d. Nothing appeared on stderr/stdout\n' % (' '.join(cl),rval)
        os.unlink(templog) # if empty
        self.tlog.write(s)

    def makeFaidx(self):
        # must make a temp softlink to index as samtools faidx will try to write [inputpath].fai 
        fd,tempfasta = tempfile.mkstemp(dir=self.opts.outdir,suffix='rgfakeFasta.fasta')
        self.delme.append(tempfasta)
        cl = ['cp',self.opts.fasta,tempfasta]
        self.run(cl)
        cl = ['samtools faidx',tempfasta]
        self.run(cl)
        tempfai = '%s.fai' % tempfasta
        return tempfai

        
    def bamToSam(self,infile=None):
        """
        use samtools view to convert bam to sam
        """
        fd,tempsam = tempfile.mkstemp(dir=self.opts.outdir,suffix='rgSortBamTemp.sam')
        self.delme.append(tempsam)
        cl = ['samtools view -h -o',tempsam,infile]
        self.run(cl)
        return tempsam

    def samToBam(self,infile=None):
        """
        use samtools view to convert sam to bam
        """
        fd,tempbam = tempfile.mkstemp(dir=self.opts.outdir,suffix='rgSortBamTemp.bam')
        self.delme.append(tempbam)
        cl = ['samtools view -h -b -S -o',tempbam,infile] 
        self.run(cl)
        return tempbam

    def removeHeaders(self,infile=None):
        """
        use samtools view to remove headers
        """
        fd,tempsam = tempfile.mkstemp(dir=self.opts.outdir,suffix='rgSortBamTempheadless.sam')
        self.delme.append(tempsam) # we're replacing it
        cl = ['samtools view -S -o',tempsam,infile]  # input sam and output sam no header
        self.run(cl)
        return tempsam
    
    def runCalmd(self,infile=None):
        """
        samtools calmd assuming a bam - convenient to do it with sortedbam before adding rest of header metadata
        """
        fd,tempbam = tempfile.mkstemp(dir=self.opts.outdir,suffix='rgCalmdTemp.bam')
        self.delme.append(tempbam)
        if self.opts.fai: # punt that we have a built  
            refseq = os.path.splitext(self.opts.fai)[0] # ugh
        else:
            refseq = self.opts.fasta
        cl = ['samtools calmd -b',infile,refseq,'>',tempbam]
        self.run(cl,redir=False) # must NOT redirect stdout!!
        return tempbam
        
    def runCleanSam(self,infile=None,isSam=True,outBam=False):
        """
        optional trim of reads beyond refseq - returns sam if isSam otherwise bam
        """
        fd,tempclean = tempfile.mkstemp(dir=self.opts.outdir,suffix='rgCleanSam')
        self.delme.append(tempclean)
        if isSam:        
            cl = ['java -Xmx2g -jar',self.opts.jar,'INPUT=%s' % infile,'OUTPUT=%s' % tempclean,'VERBOSITY=DEBUG','VALIDATION_STRINGENCY=LENIENT']
        else: # given bam we have to do some work
            sam = self.bamToSam(infile=infile)
            self.delme.append(sam)
            cl = ['java -Xmx2g -jar',self.opts.jar,'INPUT=%s' % sam,'OUTPUT=%s' % tempclean,'VERBOSITY=DEBUG','VALIDATION_STRINGENCY=LENIENT']
        self.run(cl)
        if not outBam: # we always end up with sam in tempclean
            tempclean = self.bamToSam(infile=tempclean)
        return tempclean

    def replaceHead(self,ehead=[],newbam=None):
        """
        ugly - probably optional
        """
        assert newbam <> None
        self.tlog.write('## WARNING putting back non @SQ metadata (%s) from %s' % (ehead,self.opts.input))
        fd,newsamout = tempfile.mkstemp(dir=self.opts.outdir,suffix='rgfixheadout.sam')
        self.delme.append(newsamout)
        tempsam = self.bamToSam(infile=newbam)
        self.delme.append(tempsam)
        f = open(newsamout,'w') # keep repaired file here
        headDone = False
        for row in open(tempsam,'r').readlines():
            if not headDone and (not row.startswith('@')):
               headDone=True
               f.write(''.join(ehead))           
            f.write(row)
        f.close()
        # fixed stuff is in newsamout
        newbamout = self.samToBam(newsamout)
        return newbamout

    def sortme(self):
        """
        """
        if self.opts.informat == 'bam': # need text so use samtools view
            tempsam = self.bamToSam(infile=self.opts.input)
        else:
            tempsam = self.opts.input # is already sam
        ehead = self.getSamExtraHeaders(tempsam=tempsam)
        # maybe we do not need to do this? we ended up with multiple @RG?
        tempsam = self.removeHeaders(tempsam)
        if len(ehead) == 0:
            self.tlog.write('## ehead is empty on %s - there was only @SQ and @HD' % tempsam)
        if self.opts.fasta > '': # supplied genome fasta needs indexing
            newsamfai = self.makeFaidx()    
        else: # use supplied fai
            newsamfai = self.opts.fai
        fd,sortedbam = tempfile.mkstemp(dir=self.opts.outdir,suffix='rgSortBamSorted') 
        self.delme.append(sortedbam)
        self.delme.append('%s.bam' % sortedbam) # cos that's what sort makes..
        fd,newbam = tempfile.mkstemp(dir=self.opts.outdir,suffix='rgSortBamnewbam.bam')
        self.delme.append(newbam) # if we need bam, we can copy this to galaxy output    
        cl = ['samtools import',newsamfai,tempsam,newbam] # stitch the adjusted headers
        self.run(cl)
        makeBam=(self.opts.newformat=="bam")
        if len(ehead) > 0: # eesh - need to view and add the additional non SQ metadata headers back again
            newbam = self.replaceHead(ehead=ehead,newbam=newbam)
        cl = ['samtools sort',newbam,sortedbam]
        self.run(cl)
        sortedbam = '%s.bam' % sortedbam # samtools insists on adding .bam
        # sortedbam is go
        if self.opts.runcalmd == "true": # use the -b flag and remember to redirect back into sortedbam
            newbam = self.runCalmd(infile=newbam)
        if self.opts.runcleansam == "true":
            newout=self.runCleanSam(infile=sortedbam,isSam=False,outBam=makeBam) 
            # newout is whatever we need format
        else:
            newout = sortedbam # may not need to do much
            if not makeBam:
                newout = self.bamToSam(infile=sortedbam)
        cl = ['cp',newout,self.opts.output]
        self.run(cl)
        self.delme.append(newout)
        self.tlog.close()
        self.cleanup()
        print >> sys.stdout, self.info # to appear in history

    def cleanup(self):
        if self.tidy:
            for fname in self.delme:
                try:
                    os.unlink(fname)
                except:
                    pass
    

    def makehtml(self): 
        """
        write the report as html
        """
        logdat = open(self.tlogname,'r').readlines()
        self.cleanup() # do it here so should be no files in list 
        res = []
        res.append(galhtmlprefix % progname)   
        res.append(galhtmlattr % (progname,timenow()))
        res.append('<b>Your job produced the following outputs - check here for a record of what was done and any unexpected events</b><hr/>')
        try:
            flist = os.listdir(self.opts.outdir)
        except:
            flist = []
        if len(flist) > 0: # we should clean everything up - picard doesn't tell us what it did in cleansam unfortunately
            flist = [x for x in flist if not (x.startswith('.') or x == 'None')]
            tlist = [(os.path.getmtime(os.path.join(self.opts.outdir,x)),x) for x in flist]
            tlist.sort()
            flist = [x[1] for x in tlist]
            res.append('<b>Output files.</b><hr/>\n')
            res.append('<table>\n')
            for i,f in enumerate(flist):
                fn = os.path.split(f)[-1]
                fs = getFileString(fn,self.opts.outdir)
                res.append('<tr><td><a href="%s">%s</a></td></tr>\n' % (fn,fs))
            res.append('</table><p/>\n')
        res.append('<b>Log of activity</b><hr/>\n')
        res.append('\n%s' % '<br/>'.join(logdat))
        res.append('<hr/>Note: A diabolical combination of the freely available <a href="http://picard.sourceforge.net/command-line-overview.shtml">Picard software</a> \n')
        res.append('and <a href="http://samtools.sourceforge.net">Samtools software</a>\n')
        res.append('generated all outputs reported here. These third party tools were')
        res.append('orchestrated by the Galaxy rgSortBam wrapper and this command line from the Galaxy form:<br/>\n%s' % (self.cl))   
        res.append(galhtmlpostfix)
        f = open(self.opts.htmlout,'w')
        f.write('\n'.join(res))
        f.close()

    
if __name__ == '__main__':
    '''
   rgSortBam.py -i "$input_file" --informat "$input_file.ext" -o "$out_file" -n "$out_prefix"
   --newformat "$new_format" --tmpdir "${__new_file_path__}" -m "$html_file" -d "$html_file.files_path"
#if $runCleanSam:
--cleansam ${GALAXY_DATA_INDEX_DIR}/shared/jars/CleanSam.jar
#end if
#if $runCalmd:
--calmd "true"
#end if
#if $newHead.refGenomeSource=="indexed":
   --fai "$newHead.indexsrc"
#else
   --fasta "$newHead.indexsrc"
#end if
    '''
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-o', '--output', default=None)
    op.add_option('-n', '--title', default="SortSamBam")
    op.add_option('-m', '--htmlout', default="SortSamBam.html")
    op.add_option('-d', '--outdir', default=".")
    op.add_option('--newformat', default='bam')
    op.add_option('--informat', default='bam')
    op.add_option('-x', '--maxjheap', default='2g')
    op.add_option('--tmpdir', default='/tmp')
    op.add_option('--fai', default='')
    op.add_option('--fasta', default='')
    op.add_option('-j','--jar',default='')
    op.add_option('--runcalmd', default='false')
    op.add_option('--runcleansam', default='false') # will have the cleansam jar path
    opts, args = op.parse_args()
    assert opts.input <> None
    assert os.path.isfile(opts.input) 
    assert not (opts.fasta == '' and opts.fai == '')
    assert not (opts.fasta > '' and opts.fai > '')
    try:
        os.makedirs(opts.tmpdir)
    except:
        pass
    try:
        os.makedirs(opts.outdir)
    except:
        pass
    sb = sortBAM(opts=opts,cl=sys.argv)
    sb.sortme()
    sb.makehtml()
    
    

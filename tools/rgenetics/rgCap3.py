"""
August 2011
cap3 wrapper for Galaxy
Copyright 2011 Ross lazarus
Released under the LGPL
cap3 executables only :( from http://seq.cs.iastate.edu/
This is old skool software - read name lengths are limited to about 40 characters so get truncated and mixed up 
if longer. Need to truncate them so some spacer chars are removed and the leading 

  -a  N  specify band expansion size N > 10 (20)
  -b  N  specify base quality cutoff for differences N > 15 (20)
  -c  N  specify base quality cutoff for clipping N > 5 (12)
  -d  N  specify max qscore sum at differences N > 100 (250)
  -e  N  specify extra number of differences N > 10 (20)
  -f  N  specify max gap length in any overlap N > 10 (300)
  -g  N  specify gap penalty factor N > 0 (6)
  -h  N  specify max overhang percent length N > 5 (20)
  -m  N  specify match score factor N > 0 (2)
  -n  N  specify mismatch score factor N < 0 (-5)
  -o  N  specify overlap length cutoff > 20 (30)
  -p  N  specify overlap percent identity cutoff N > 65 (75)
  -r  N  specify reverse orientation value N >= 0 (1)
  -s  N  specify overlap similarity score cutoff N > 100 (500)
  -t  N  specify max number of word occurrences N > 30 (500)
  -u  N  specify min number of constraints for correction N > 0 (4)
  -v  N  specify min number of constraints for linking N > 0 (2)
  -w  N  specify file name for clipping information (none)
  -x  N  specify prefix string for output file names (cap)
  -y  N  specify clipping range N > 5 (250)
  -z  N  specify min no. of good reads at clip pos N > 0 (2)

quality scores must be in phred phormat and are phudged with phredphudger
oy.
"""
import optparse
import tempfile
import os
import sys
import subprocess
import time
from rgutils import galhtmlprefix,galhtmlpostfix,galhtmlattr,getFileString

readnameRemove = ['_',':','HWUSI-EAS'] # these are all replaced with '' to shorten readnames due to cap3 space limit

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


class cap3:
    """Class to wrap cap3
    """
    
    def __init__(self,myName=None,opts=None,phredphudger=33):
        """
        split input fastq
@SEQ_ID
GATTTGGGGTTCAAAGCAGTATCGATCAAATAGTAAATCCATTTGTTCAACTCACAGTTT
+
!''*((((***+))%%%++)(%%%%).1***-+*''))**55CCF>>>>>>CCCCCCC65
        """
        self.progname=myName
        self.opts = opts
        self.phredphudger = int(opts.phredphudger)
        if not os.path.isdir(opts.outputdir):
            try:
                os.makedirs(opts.outputdir)
            except:
                print >> sys.stderr,'##Error: cap3 unable to create or find output directory %s. Stopping' % (opts.outputdir)
                sys.exit(1)
        cl = []
        infq = opts.fastqin
        froot = os.path.split(infq)[-1]
        fasta = os.path.join(opts.outputdir,froot)
        qual = '%s.qual' % fasta
        if not (os.path.isfile(fasta) and os.path.isfile(qual)): # build
            f = open(infq,'r')
            fa = open(fasta,'w')
            fq = open(qual,'w')
            for i,row in enumerate(f):
                rown = i % 4
                if rown == 2:
                    continue
                elif rown == 0:
                    if not row.startswith('@'):
                        print >> sys.stderr,'##Error: input fastq file %s row %d (%s) does not start with "@"' % (infq,i,row)
                        sys.exit(1)
                    id = row[1:]
                    for replaceme in readnameRemove:
                        id = id.replace(replaceme,'')
                    fa.write('>%s' % (id))
                elif rown == 1:
                    fa.write(row)
                    rowlen = len(row.strip())
                elif rown == 3:
                    if len(row.strip()) <> rowlen:
                        print >> sys.stderr,'##Error: input fastq file %s row %d (%s) length %d differs from sequence %d' % (infq,i,row,len(row.strip()),rowlen)
                        sys.exit(1)
                    row = row.strip()
                    q = map(ord,row)
                    q = ['%d' % (x - self.phredphudger) for x in q]
                    s = ' '.join(q)
                    fq.write('>%s%s\n' % (id,s)) # phrap phucking phormat - see www.phrap.org/phredphrap/phrap.html 
            fa.close()
            fq.close()
            f.close()
        a = cl.append        
        a('cap3')
        a(fasta)
        a('-a %s' % opts.band_expansion)
        a('-b %s' % opts.bqdiff) 
        a('-c %s' % opts.bqclip)
        a('-d %s' % opts.maxqscoresum)
        a('-e %s' % opts.extradiff)
        a('-f %s' % opts.maxgap)
        a('-g %s' % opts.gapfact)
        a('-h %s' % opts.maxoverhang)
        a('-i %s' % opts.segscore)
        a('-j %s' % opts.chainscore)
        a('-k %s' % opts.endclip)
        a('-m %s' % opts.matchscore) 
        a('-n %s' % opts.mismatchscore)
        a('-o %s' % opts.overlapcut)
        a('-p %s' % opts.overlapidentity)
        a('-r %s' % opts.reverseorientation)
        a('-s %s' % opts.overlapsimilarity)
        a('-t %s' % opts.maxword)
        a('-u %s' % opts.mincon) 
        a('-v %s' % opts.minlink)
        if opts.clipfile:
            a('-w %s' % opts.clipfile)
        a('-x %s' % opts.outprefix)
        a('-y %s' % opts.cliprange)
        a('-z %s' % opts.mingood)
        self.cl = cl
        

    def run(self):
        """
        """       
        fplog,tlog = tempfile.mkstemp(prefix="cap3runner.log",dir=self.opts.outputdir)
        cap3out = os.path.join(self.opts.outputdir,"cap3out.cap3")
        ste = open(tlog,'w')
        sto = open(cap3out,'w')
        x = subprocess.Popen(' '.join(self.cl),shell=True,stdout=sto,stderr=ste,cwd=self.opts.outputdir)
        retval = x.wait()
        sto.close()
        ste.close()
        try:
            mlog = file(tlog,'r').readlines()
            os.unlink(tlog) # no longer needed
        except:
            mlog = '### %s Strange - no std out from cap3 when running command line\n%s' % (timenow(),' '.join(cl))
        flist = os.listdir(self.opts.outputdir)
        flist.sort()
        flist = [os.path.join(self.opts.outputdir,x) for x in flist] # ugh
        html = [galhtmlprefix % self.progname,]
        html.append('<h1>Outputs from CAP3</h1>')
        html.append('CL=%s' % ' '.join(self.cl))
        if len(flist) > 0:
            html.append('<table>\n')
            for row in flist:
                fdir,fname = os.path.split(row)
                if not fname.startswith('.nfs'):
                     html.append('<tr><td><a href="%s">%s</a></td></tr>' % (fname,getFileString(fname,fdir)))
            html.append('</table>\n')
        else:
            html.append('<h2>### Error - CAP3 returned no files - please confirm that parameters are sane</h1>')    
        html.append('<h3>CAP3 log follows below</h3><hr><pre>\n')
        html += mlog
        html.append('</pre>\n')   
        html.append(galhtmlattr % (self.progname,timenow()))
        html.append(galhtmlpostfix)
        htmlf = file(self.opts.outhtml,'w')
        htmlf.write('\n'.join(html))
        htmlf.write('\n')
        htmlf.close()
        return retval

if __name__ == "__main__":
    """called as
    rgCap3.py --fastqin "$input_file" --outputdir "$html_file.files_path" --outhtml "$html_file"
    -a "${bandexp}" -b "${basecut}" -c "${baseclip}" -d "${maxqsum}" -e "${extradiff}" -f "${maxgap}"
    -g "${gapfact}" --maxoverhang "${maxoverhang}" -i "${segscore}" -j "${chainscore}" -k "${endclip}"
    -m "${matchscore}" -n "${mismatchscore}" -o "${overlapcut}" -p "${overlapidentity}"
    -r "${reverseorient}" -s "${overlapsim}" -t "${maxword}" -u "${mincorrect}" -v "${minlink}"
    -x "${out_prefix}" -y "${cliprange}" -z "${mingood}" --cap3exe "cap3"
  </command>
    
    """
    op = optparse.OptionParser()
    a = op.add_option
    a('--fastqin',default=None)
    a('--phredphudger',default='33')
    a('-a','--band_expansion',default='20')
    a('-b','--bqdiff',default='20') 
    a('-c','--bqclip',default='12')
    a('-d','--maxqscoresum',default='200')
    a('-e','--extradiff',default='30')
    a('-f','--maxgap',default='20')
    a('-g','--gapfact',default='6')
    a('--maxoverhang',default='20')
    a('-i','--segscore',default='40')
    a('-j','--chainscore',default='80')
    a('-k','--endclip',default='1')
    a('-m','--matchscore',default='2') 
    a('-n','--mismatchscore',default='-5')
    a('-o','--overlapcut',default='30')
    a('-p','--overlapidentity',default='75')
    a('-r','--reverseorientation',default='1')
    a('-s','--overlapsimilarity',default='500')
    a('-t','--maxword',default='500')
    a('-u','--mincon',default='4') 
    a('-v','--minlink',default='2')
    a('-w','--clipfile',default=None)
    a('-x','--outprefix',default='cap3')
    a('-y','--cliprange',default='250')
    a('-z','--mingood',default='2')
    a( '--cap3exe', default="/usr/local/bin/cap3")
    a( '--outputdir',default=".")
    a('--outhtml', default=None)
    opts, args = op.parse_args() 
    assert os.path.isfile(opts.fastqin),'## cap3 runner unable to open supplied input file %s' % opts.fastqin
    myName=os.path.split(sys.argv[0])[-1]
    m = cap3(myName, opts=opts)
    retcode = m.run()
    if retcode:
        sys.exit(retcode) # indicate failure to job runner
    
    

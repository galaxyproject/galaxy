"""
# modified june 2 ross lazarus to add units option at Assaf Gordon's suggestion
# rgWebLogo3.py
# wrapper to check that all fasta files are same length

"""
import optparse, os, sys, subprocess, tempfile

WEBLOGO = 'weblogo' # executable name for weblogo3 - confusing isn't it?

class WL3:
    """
    simple wrapper class to check fasta sequence lengths are all identical
    """
    FASTASTARTSYM = '>'
    badseq = '## error - sequences in file %s are not all the same length - cannot proceed. Please read the tool documentation carefully'

    def __init__(self,opts=None):
        assert opts<>None,'WL3 class needs opts passed in - got None'
        self.opts = opts
        self.fastaf = file(self.opts.input,'r')
        self.clparams = {}

    def whereis(self,program):
        for path in os.environ.get('PATH', '').split(':'):
            if os.path.exists(os.path.join(path, program)) and not os.path.isdir(os.path.join(path, program)):
                return os.path.join(path, program)
        return None

    def runCL(self):
        """ construct and run a command line
        """
        wl = self.whereis(WEBLOGO)
        if not wl:
             print >> sys.stderr, '## rgWebLogo3.py error - cannot locate the weblogo binary %s on the current path' % WEBLOGO
             print >> sys.stderr, '## Please ensure it is installed and working from http://code.google.com/p/weblogo'
             sys.exit(1)
        cll = [WEBLOGO,]
        cll += [' '.join(it) for it in list(self.clparams.items())]
        cl = ' '.join(cll)
        assert cl > '', 'runCL needs a command line as clparms'
        fd,templog = tempfile.mkstemp(suffix='rgtempRun.txt')
        tlf = open(templog,'w')
        process = subprocess.Popen(cl, shell=True, stderr=tlf, stdout=tlf)
        rval = process.wait()
        tlf.close()
        tlogs = ''.join(open(templog,'r').readlines())
        if len(tlogs) > 1:
            s = '## executing %s returned status %d and log (stdout/stderr) records: \n%s\n' % (cl,rval,tlogs)
        else:
            s = '## executing %s returned status %d. Nothing appeared on stderr/stdout\n' % (cl,rval)
        os.unlink(templog) # always
        if rval <> 0:
             print >> sys.stderr, '## rgWebLogo3.py error - executing %s returned error code %d' % (cl,rval)
             print >> sys.stderr, '## This may be a data problem or a tool dependency (%s) installation problem' % WEBLOGO
             print >> sys.stderr, '## Please ensure %s is correctly installed and working on the command line -see http://code.google.com/p/weblogo' % WEBLOGO
             sys.exit(1)
        return s

        
    def iter_fasta(self):
        """
        generator for fasta sequences from a file
        """
        aseq = []
        seqname = None
        for i,row in enumerate(self.fastaf):
            if row.startswith(self.FASTASTARTSYM):
                if seqname <> None: # already in a sequence
                    s = ''.join(aseq)
                    l = len(s)
                    yield (seqname,l)
                    seqname = row[1:].strip()
                    aseq = []
                else:
                    if i > 0:
                        print >> sys.stderr,'Invalid fasta file %s - does not start with %s - please read the tool documentation carefully' % (self.opts.input,self.FASTASTARTSYM)
                        sys.exit(1)
                    else:
                        seqname = row[1:].strip() 
            else: # sequence row
                if seqname == None:
                    print >> sys.stderr,'Invalid fasta file %s - does not start with %s - please read the tool documentation carefully' % (self.opts.input,self.FASTASTARTSYM)
                    sys.exit(1) 
                else:
                    aseq.append(row.strip())
                
        if seqname <> None: # last one
            l = len(''.join(aseq))
            yield (seqname,l)
                
        
    def fcheck(self):
        """ are all fasta sequence same length?
        might be mongo big
        """
        flen = None
        lasti = None
        f = self.iter_fasta()
        for i,(seqname,seqlen) in enumerate(f):
            lasti = i
            if i == 0:
                flen = seqlen
            else:
                if seqlen <> flen:
                    print >> sys.stderr,self.badseq % self.opts.input
                    sys.exit(1)
        return '# weblogo input %s has %d sequences all of length %d' % (self.opts.input,lasti,flen)


    def run(self):
        check = self.fcheck()
        self.clparams['-f'] = self.opts.input
        self.clparams['-o'] = self.opts.output
        self.clparams['-t'] = '"%s"' % self.opts.logoname # must be wrapped as a string       
        self.clparams['-F'] = self.opts.outformat       
        if self.opts.size <> None:
            self.clparams['-s'] = self.opts.size
        if self.opts.lower <> None:
            self.clparams['-l'] = self.opts.lower
        if self.opts.upper <> None:
            self.clparams['-u'] = self.opts.upper        
        if self.opts.colours <> None:
            self.clparams['-c'] = self.opts.colours
        if self.opts.units <> None:
            self.clparams['-U'] = self.opts.units
        s = self.runCL()
        return check,s


if __name__ == '__main__':
    '''
    called as
<command interpreter="python"> 
    rgWebLogo3.py --outformat $outformat -s $size -i $input -o $output -t "$logoname" -c "$colours"
#if $range.mode == 'part'
-l "$range.seqstart" -u "$range.seqend"
#end if
    </command>

    '''
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-F', '--outformat', default='png')
    op.add_option('-s', '--size', default=None) 
    op.add_option('-o', '--output', default='rgWebLogo3')
    op.add_option('-t', '--logoname', default='rgWebLogo3')
    op.add_option('-c', '--colours', default=None)
    op.add_option('-l', '--lower', default=None)
    op.add_option('-u', '--upper', default=None)  
    op.add_option('-U', '--units', default=None)  
    opts, args = op.parse_args()
    assert opts.input <> None,'weblogo3 needs a -i parameter with a fasta input file - cannot open'
    assert os.path.isfile(opts.input),'weblogo3 needs a valid fasta input file - cannot open %s' % opts.input
    w = WL3(opts)
    checks,s = w.run()
    print >> sys.stdout, checks # for info

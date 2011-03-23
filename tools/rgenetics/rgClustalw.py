"""
rgclustalw.py
wrapper for clustalw necessitated by bad choice of output path for .dnd file based on input file. Naughty.
Copyright ross lazarus march 2011
All rights reserved
Licensed under the LGPL
"""

import sys,optparse,os,subprocess,tempfile,shutil

class Clustrunner:
    """
    """
    def __init__(self,opts=None):
        self.opts = opts
        self.iname = 'infile_copy'
        shutil.copy(self.opts.input,self.iname) 

    def run(self):
        tlf = open(self.opts.outlog,'w')
        cl = ['clustalw2 -INFILE=%s -OUTFILE=%s -OUTORDER=%s -TYPE=%s -OUTPUT=%s' % (self.iname,self.opts.output,self.opts.out_order,self.opts.dnarna,self.opts.outform)]
        if self.opts.seq_range_end <> None and self.opts.seq_range_start <> None:
            cl.append('-RANGE=%s,%s' % (self.opts.seq_range_start,self.opts.seq_range_end))
        if self.opts.outform=='CLUSTAL' and self.opts.outseqnos <> None:
            cl.append('-SEQNOS=ON')
        process = subprocess.Popen(' '.join(cl), shell=True, stderr=tlf, stdout=tlf)
        rval = process.wait()
        dndf = '%s.dnd' % self.iname
        if os.path.exists(dndf):
            tlf.write('\nClustal created the following dnd file for your information:\n')
            dnds = open('%s.dnd' % self.iname,'r').readlines()
	    for row in dnds:
                tlf.write(row)
            tlf.write('\n')
        tlf.close()
        os.unlink(self.iname)
    


if __name__ == "__main__":
    op = optparse.OptionParser()
    op.add_option('-i', '--input', default=None)
    op.add_option('-o', '--output', default=None)
    op.add_option('-t', '--outname', default="rgClustal")
    op.add_option('-s', '--out_order', default='ALIGNMENT')
    op.add_option('-f', '--outform', default='CLUSTAL')
    op.add_option('-e', '--seq_range_end',default=None)
    op.add_option('-b', '--seq_range_start',default=None)
    op.add_option('-l','--outlog',default='rgClustalw.log')
    op.add_option('-q', '--outseqnos',default=None)    
    op.add_option('-d', '--dnarna',default='DNA')    
    
    opts, args = op.parse_args()
    assert opts.input <> None
    assert os.path.isfile(opts.input)
    c = Clustrunner(opts)
    c.run()
    
            


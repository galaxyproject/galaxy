"""
August 2011
MapSplice wrapper for Galaxy
Copyright 2011 Ross lazarus
Released under the LGPL
http://www.netlab.uky.edu/p/bioinfo/MapSpliceManual
"""
import optparse
import tempfile
import os
import sys
import subprocess
import time
import shutil
from rgutils import galhtmlprefix, galhtmlpostfix, galhtmlattr, getFileString

progname = os.path.split(sys.argv[0])[1]

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


class MapSplice:
    """Class to wrap mapsplice
    """
    
    def __init__(self, opts=None):
        self.opts = opts
        cl = []
        a = cl.append
        a(sys.executable) # use the python we were called with
        a(opts.mapspliceexe)
        a('-u %s' % opts.readsfile)
        a('-c %s' % opts.chromosomefilesdir)
        a('-w %s' % opts.readlen)        
        a('-L %s' % opts.seglen)
        a('-E %s' % opts.segmentmismatches)
        a('-Q %s' % opts.readtype)
        a('-B %s' % opts.Bowtieidx)
        a('-X %s' % opts.Bowtiethreads) 
        a('-o %s' % opts.outputdir)
        if opts.semican <> '':
            a(opts.semican)
        if opts.fuscan <> '':
            a(opts.fuscan)
        if opts.fusion <> '':
            a(opts.fusion)
        if opts.mapsegdir <> '':
            a(opts.mapsegdir)
        if opts.fullrun <> '':
            a(opts.fullrun)
        if opts.searchwhole <> '':
            a(opts.searchwhole)
        self.cl = cl
 
    def postrun(self,mlog=[]):
        """
        """
        flist = os.listdir(self.opts.outputdir)
        flist.sort()
        html = [galhtmlprefix % progname,]
        html.append('<h1>%s MapSplice results</h1>' % self.opts.title)
        if len(flist) > 0:
            html.append('<table>\n')
            for fname in flist:
                fpath = os.path.join(self.opts.outputdir,fname)
                if not os.path.isdir(fpath):
                    n,e = os.path.splitext(fname)
                    if e == '.sam':
                       shutil.move(fpath,self.opts.outsam)
                    else:
                       fs = getFileString(fname,self.opts.outputdir)
                       html.append('<tr><td><a href="%s">%s</a></td></tr>' % (fname,fs))
            html.append('</table>\n')
        else:
            html.append('<h2>### Error - MapSplice returned no files to %s - please confirm that parameters are sane</h1>' % self.opts.outputdir)    
        html.append('<h3>MapSplice log follows below</h3><hr><pre>\n')
        html += mlog
        html.append('</pre>\n')   
        html.append(galhtmlattr % (progname,timenow()))
        html.append(galhtmlpostfix)
        htmlf = file(self.opts.outhtml,'w')
        htmlf.write('\n'.join(html))
        htmlf.write('\n')
        htmlf.close()
    

    def runMapSplice(self):
        """
        """       
        fplog,tlog = tempfile.mkstemp(suffix="mapsplicerunner.log")
        sto = file(tlog,'w')
        x = subprocess.Popen(' '.join(self.cl),shell=True,stdout=sto,stderr=sto,cwd=self.opts.outputdir)
        retval = x.wait()
        sto.close()
        try:
            mlog = file(tlog,'r').readlines()
        except:
            mlog = ['### %s Strange - no std out from mapsplice when running command line\n%s' % (timenow(),' '.join(cl)),]
        mlog.append('### runmapsplice retval = %d' % retval)
        os.unlink(tlog) # no longer needed
        self.postrun(mlog=mlog)
        return retval

if __name__ == "__main__":
    """called as
    <command interpreter="python"> 
mapsplice.py -e ${GALAXY_DATA_INDEX_DIR}/shared/python/mapsplice/mapsplice_segments.py -u "$fastqf" 
-B "${ filter( lambda x: str( x[0] ) == str( $genomeSource.index ), $__app__.tool_data_tables[ 'bowtie_indices' ].get_fields() )[0][-1] }"
-c "${ filter( lambda x: str( x[0] ) == str( $genomeSource.index ), $__app__.tool_data_tables[ 'all_chrom_fasta' ].get_fields() )[0][-1] }"
-o "$outhtml.files_path" -h "$outhtml" -L "$seglen" -E "$segmismatches" --semican "$semican" --fuscan "$fuscan" --fusion "$fusion" --mapsegdir "$mapsegdir"
--searchwhole "$searchwhole" --fullrun "$fullrun" --outsam "$outsam"
    </command>
    """
    op = optparse.OptionParser()
    op.add_option('-e', '--mapspliceexe', default="mapsplice_segments.py")
    op.add_option('-u', '--readsfile', default=None)
    op.add_option('-B', '--Bowtieidx', default=None)
    op.add_option('-c', '--chromosomefilesdir', default=None)
    op.add_option('-o', '--outputdir',default=None)
    op.add_option('-t', '--outhtml', default=None)
    op.add_option('-L', '--seglen', default="18")
    op.add_option('-w', '--readlen', default="36")
    op.add_option('-E', '--segmentmismatches', default="1")
    op.add_option('-Q', '--readtype', default="fq")
    op.add_option('-X', '--Bowtiethreads', default="1")
    op.add_option('--semican', default="")
    op.add_option('--fuscan',default="")
    op.add_option('--fusion', default="")
    op.add_option('--mapsegdir', default="")
    op.add_option('--searchwhole', default="false")
    op.add_option('--fullrun',default="false")
    op.add_option('--outsam',default=None)
    op.add_option('--title',default='MapSplice Run')
    opts, args = op.parse_args() 
    assert os.path.isfile(opts.readsfile),'## mapsplice runner unable to open supplied input file %s' % opts.reads-file
    assert os.path.isfile(opts.mapspliceexe),'## mapsplice runner unable to open supplied mapsplice python file %s' % opts.mapspliceexe
    if not os.path.isdir(opts.outputdir):
        os.makedirs(opts.outputdir)
    m = MapSplice(opts=opts)
    retcode = m.runMapSplice()
    if retcode:
        sys.exit(retcode) # indicate failure to job runner
    
    

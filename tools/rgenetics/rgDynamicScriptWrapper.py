# rgDynamicScriptWrapper.py
# derived from
# rgBaseScriptWrapper.py
# to run some user supplied code 
# extremely dangerous
# trusted users only - private site only
# a list in the xml is searched - only users in the list can run this tool.
# 
# copyright ross lazarus (ross.lazarus@gmail.com) May 2012
# 
# all rights reserved
# Licensed under the LGPL for your pleasure
# Derived from rgDGE.py in May 2012
# generalized to run required interpreter
# to make your own tools based on a given script and interpreter such as perl or python
# clone this and the corresponding xml wrapper
# replace the parameters/inputs/outputs and the configfile contents with your script
# Use the $foo syntax to place your parameter values inside the script to assign them - at run time, the script will be used as a template
# and returned as part of the output to the user - with the right values for all the parameters.
# Note that this assumes you want all the outputs arranged as a single Html file output 
# after this generic script runner runs your script with the specified interpreter,
# it will collect all output files into the specified output_html, making thumbnails for all the pdfs it finds and making links for all the other files.

import sys 
import shutil 
import subprocess 
import os 
import time 
import tempfile 
import optparse

progname = os.path.split(sys.argv[0])[1] 
myversion = 'V000.1 May 2012' 
verbose = False 
debug = False


galhtmlprefix = """<?xml version="1.0" encoding="utf-8" ?> 
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"> 
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en"> 
<head> <meta http-equiv="Content-Type" content="text/html; charset=utf-8" /> 
<meta name="generator" content="Galaxy %s tool output - see http://g2.trac.bx.psu.edu/" /> 
<title></title> 
<link rel="stylesheet" href="/static/style/base.css" type="text/css" /> 
</head> 
<body> 
<div class="document"> 
""" 
galhtmlattr = """<b><a href="http://rgenetics.org">Galaxy Rgenetics Base Script Wrapper based </a> tool output %s run at %s</b><br/>""" 
galhtmlpostfix = """</div></body></html>\n"""

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))
# characters that are allowed but need to be escaped
mapped_chars = { '>' :'__gt__',
                 '<' :'__lt__',
                 "'" :'__sq__',
                 '"' :'__dq__',
                 '{' :'__oc__',
                 '}' :'__cc__',
                 '@' : '__at__', 
                 '\n' : '__cn__',
                 '\r' : '__cr__',
                 '\t' : '__tc__',
                 '#' : '__pd__',
                 '[' :'__ob__',
                 ']' :'__cb__',
                 '\t' : 'Xt', 
                 'systemCallsAreNotAllowed' : 'system'
                 }

def restore_text(text):
    """Restores sanitized text"""  
    if not text:
        return text
    for key, value in mapped_chars.items():
        text = text.replace(value, key)
    return text
    
class ScriptRunner:
    """class is a wrapper for an arbitrary script
    """

    def __init__(self,opts=None):
        """
        run the script
        cheetah/galaxy will provide an escaped string so
        __pd__ your script goes here
        __cr____cn__ourargs __lt__- commandArgs(TRUE)
        __cr____cn__inf = ourargs[1]
        __cr____cn__outf = ourargs[2]
        __cr____cn__inp = read.table(inf,head=T,rownames=F,sep=__sq__Xt__sq__)
        __cr____cn__ write.table(inp,outf, quote=FALSE, sep=__dq__Xt__dq__,row.names=F)
        __cr____cn__sessionInfo()
        __cr____cn__
        """
        self.thumbformat = 'jpg'
        self.opts = opts
        self.toolname = opts.tool_name.replace(' ','_')
        s = open(self.opts.script_path,'r').read()
        self.script = restore_text(s)
        if opts.output_dir: # may not want these complexities if a simple script
            self.tlog = os.path.join(opts.output_dir,"%s_runner.log" % self.toolname)
            artifactpath = os.path.join(opts.output_dir,'%s_run.script' % self.toolname) 
            artifact = open(artifactpath,'w')
            artifact.write(self.script)
            artifact.write('\n')
            artifact.close()
        self.cl = []
        a = self.cl.append
        a(opts.interpreter)
        a('-') # use stdin
        a(opts.input_tab)
        a(opts.output_tab)

    def compressPDF(self,inpdf=None,thumbformat='png'):
        """need absolute path to pdf
        """
        assert os.path.isfile(inpdf), "## Input %s supplied to %s compressPDF not found" % (inpdf,self.myName)
        hf,hlog = tempfile.mkstemp(suffix="%s.log" % self.toolname)
        sto = open(hlog,'w')
        outpdf = '%s_compressed' % inpdf
        cl = ["gs", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-sOutputFile=%s" % outpdf,inpdf]
        x = subprocess.Popen(cl,stdout=sto,stderr=sto,cwd=self.opts.output_dir)
        retval1 = x.wait()
        if retval1 == 0:
            os.unlink(inpdf)
            shutil.move(outpdf,inpdf)
        outpng = '%s.%s' % (os.path.splitext(inpdf)[0],thumbformat)
        cl2 = ['convert', inpdf, outpng]
        x = subprocess.Popen(cl2,stdout=sto,stderr=sto,cwd=self.opts.output_dir)
        retval2 = x.wait()
        sto.close()
        retval = retval1 or retval2
        return retval


    def getfSize(self,fpath,outpath):
        """
        format a nice file size string
        """
        size = ''
        fp = os.path.join(outpath,fpath)
        if os.path.isfile(fp):
            n = float(os.path.getsize(fp))
            if n > 2**20:
                size = ' (%1.1f MB)' % (n/2**20)
            elif n > 2**10:
                size = ' (%1.1f KB)' % (n/2**10)
            elif n > 0:
                size = ' (%d B)' % (int(n))
        return size


    def run(self):
        """
        """
        if self.opts.output_dir:
            sto = open(self.tlog,'w')
            p = subprocess.Popen(' '.join(self.cl),shell=True,stdout=sto,stderr=sto,stdin=subprocess.PIPE,cwd=self.opts.output_dir)
        else:
            p = subprocess.Popen(' '.join(self.cl),shell=True,stdin=subprocess.PIPE)            
        p.stdin.write(self.script)
        p.stdin.close()
        retval = p.wait()
        if self.opts.output_dir:
            sto.close()
            flist = os.listdir(self.opts.output_dir)
            flist = [x for x in flist if x <> 'Rplots.pdf']
            flist.sort()
            html = [galhtmlprefix % progname,]
            html.append('<h2>Galaxy %s outputs run at %s</h2></br>Click on a thumbnail below to download the original PDF</br>\n' % (self.toolname,timenow()))
            fhtml = []
            if len(flist) > 0:
                html.append('<table cellpadding="3" cellspacing="3">\n')
                for fname in flist:
                    dname,e = os.path.splitext(fname)
                    sfsize = self.getfSize(fname,self.opts.output_dir)
                    if e.lower() == '.pdf' : # compress and make a thumbnail
                        thumb = '%s.%s' % (dname,self.thumbformat)
                        pdff = os.path.join(self.opts.output_dir,fname)
                        retval = self.compressPDF(inpdf=pdff,thumbformat=self.thumbformat)
                        if retval == 0:
                            s= '<tr><td><a href="%s"><img src="%s" title="Click to download a PDF of %s" hspace="10" width="600"></a></td></tr>\n' % (fname,thumb,fname)
                            html.append(s)
                        fhtml.append('<li><a href="%s">%s %s</a></li>' % (fname,fname,sfsize))
                    else:
                       fhtml.append('<li><a href="%s">%s %s</a></li>' % (fname,fname,sfsize))
                html.append('</table>\n')
                if len(fhtml) > 0:
                    fhtml.insert(0,'<ul>')
                    fhtml.append('</ul>')
                    html += fhtml # add all non-pdf files to the end of the display
            else:
                html.append('<h2>### Error - %s returned no files - please confirm that parameters are sane</h1>' % self.opts.interpreter)
            html.append('<h3>%s log follows below</h3><hr><pre>\n' % self.opts.interpreter)
            rlog = open(self.tlog,'r').readlines()
            html += rlog
            html.append('%s CL = %s</br>\n' % (self.toolname,' '.join(sys.argv)))
            html.append('CL = %s</br>\n' % (' '.join(self.cl)))
            html.append('</pre>\n')
            html.append(galhtmlattr % (progname,timenow()))
            html.append(galhtmlpostfix)
            htmlf = file(self.opts.output_html,'w')
            htmlf.write('\n'.join(html))
            htmlf.write('\n')
            htmlf.close()
        return retval
  

def main():
    u = """
    This is a Galaxy wrapper. It expects to be called by a special purpose tool.xml as:
    <command interpreter="python">rgBaseScriptWrapper.py --script_path "$scriptPath" --tool_name "foo" --interpreter "Rscript"
    </command>
    """
    permitted_users = ['rlazarus@bakeridi.edu.au','akaspi@bakeridi.edu.au','mziemann@bakeridi.edu.edu']
    op = optparse.OptionParser()
    a = op.add_option
    a('--script_path',default=None)
    a('--tool_name',default=None)
    a('--interpreter',default=None)
    a('--output_dir',default=None)
    a('--output_html',default=None)
    a('--input_tab',default='NONE')
    a('--output_tab',default='NONE')
    a('--user_email',default=None)
    a('--bad_user',default=None)
    opts, args = op.parse_args()
    assert not opts.bad_user,'%s is NOT authorized to use this tool. Please ask your friendly admin' % opts.bad_user
    assert opts.tool_name,'## Dynamic script wrapper expects a tool name - eg --tool_name=DESeq'
    assert opts.interpreter,'## Dynamic script wrapper expects an interpreter - eg --interpreter=Rscript'
    assert os.path.isfile(opts.script_path),'## Dynamic script wrapper expects a script path - eg --script_path=foo.R'
    if opts.output_dir:
        try:
            os.makedirs(opts.output_dir)
        except:
            pass
    r = ScriptRunner(opts)
    retcode = r.run()
    if retcode:
        sys.exit(retcode) # indicate failure to job runner


if __name__ == "__main__":
    main()



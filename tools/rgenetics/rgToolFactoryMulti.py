# rgToolFactory.py
# derived from 
# rgBaseScriptWrapper.py
# but designed to run arbitrary user supplied code 
# extremely dangerous!!
# trusted users only - private site only
# a list in the xml is searched for users permitted to run this tool.
# DO NOT install on a public or important site - local instance only
# generated tools are fine as they just run normally and their user cannot do anything unusually insecure
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
import tarfile
import re
import shutil

progname = os.path.split(sys.argv[0])[1] 
myversion = 'V000.1 May 2012' 
verbose = False 
debug = False


def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))
# characters that are allowed but need to be escaped

class ScriptRunner:
    """class is a wrapper for an arbitrary script
    """

    def __init__(self,opts=None):
        """
        run the script
        
        """
        if opts.output_dir: # simplify for the tool tarball
            os.chdir(opts.output_dir)
        self.thumbformat = 'jpg'
        self.opts = opts
        self.toolname = re.sub('[^a-zA-Z0-9_]+', '', opts.tool_name)
        self.toolid = self.toolname
        s = open(self.opts.script_path,'r').read()
        self.script = s
        self.myname = sys.argv[0] # get our name because we write ourselves out as a tool later
        self.pyfile = self.myname # crude but efficient - the cruft won't hurt much
        self.xmlfile = '%s.xml' % self.toolname
        self.sfile = '%s.%s' % (self.toolname,opts.interpreter)
        if opts.input_list:
            inpfiles = [x.split(',')[0] for x in opts.input_list]
            inpnames = [x.split(',')[1] for x in opts.input_list]
            inpfiles = [x.replace("'","") for x in inpfiles] # remove bogus quotes
            inpnames = [x.replace("'","") for x in inpfiles]
            inpfiles = [x.replace('"',"") for x in inpfiles] # remove bogus quotes
            inpnames = [x.replace('"',"") for x in inpfiles]
	    self.inputfiles = ','.join(inpfiles)
            self.inputnames = ','.join(inpnames)
 	else:
            self.inputfiles = 'None'
            self.inputnames = 'None'
        if opts.output_dir: # may not want these complexities 
            self.tlog = os.path.join(opts.output_dir,"%s_runner.log" % self.toolname)
            artifactpath = os.path.join(opts.output_dir,'%s_run.script' % self.toolname) 
            artifact = open(artifactpath,'w')
            artifact.write(self.script)
            artifact.write('\n')
            artifact.close()
        if opts.make_Tool: # need this code and the user script for the tarball 
            localscript = open(self.sfile,'w')
            localscript.write(self.script)
            localscript.close()
            shutil.copyfile(self.myname,'%s.py' % self.toolname) # for tool and for user 
        self.cl = []
        self.html = []
        a = self.cl.append
        a(opts.interpreter)
        a('-') # use stdin
        a(self.inputfiles)
        a(opts.output_tab)
        a(self.inputnames)
        self.outFormats = 'tabular' # TODO make this an option at tool generation time
        self.inputFormats = 'tabular' # TODO make this an option at tool generation time


    def makeXML(self):
        """
        Create a Galaxy xml tool wrapper for the new script as a string to write out
        fixme - use templating or something less fugly than this.
        Here's an example of what we produce

        <tool id="reverse" name="reverse" version="0.01">
            <description>a tabular file</description>
            <command interpreter="python">
            reverse.py --script_path "$runMe" --interpreter "python" 
            --tool_name "reverse" --input_tab "$input1" --output_tab "$tab_file" 
            </command>
            <inputs>
            <param name="input1"  type="data" format="tabular" label="Select a suitable input file from your history"/><param name="job_name" type="text" label="Supply a name for the outputs to remind you what they contain" value="reverse"/>

            </inputs>
            <outputs>
            <data format="tabular" name="tab_file" label="${job_name}"/>

            </outputs>
            <help>
            
**What it Does**

Reverse the columns in a tabular file

            </help>
            <configfiles>
            <configfile name="runMe">
            
# reverse order of columns in a tabular file
import sys
inp = sys.argv[1]
outp = sys.argv[2]
i = open(inp,'r')
o = open(outp,'w')
for row in i:
     rs = row.rstrip().split('\t')
     rs.reverse()
     o.write('\t'.join(rs))
     o.write('\n')
i.close()
o.close()
 

            </configfile>
            </configfiles>
            </tool>
        
        """    
        newXML="""<tool id="%(toolid)s" name="%(toolname)s" version="0.01">
            %(tooldesc)s
            %(command)s
            <inputs>
            %(inputs)s
            </inputs>
            <outputs>
            %(outputs)s
            </outputs>
            <help>
            %(help)s
            </help>
            <configfiles>
            <configfile name="runMe">
            %(script)s
            </configfile>
            </configfiles>
            </tool>""" # needs a dict with toolname, toolid, interpreter, scriptname, command, inputs as a multi line string ready to write, outputs ditto, help ditto
               
        newCommand="""<command interpreter="python">
            %(toolname)s.py --script_path "$runMe" --interpreter "%(interpreter)s" 
            --tool_name "%(toolname)s" %(command_inputs)s %(command_outputs)s 
            </command>""" # may NOT be an input or htmlout
        tooltests = """<tests><test>
        <param name="input1" value="%s" ftype="%s"/>
        <param name="job_name" value="test1"/>
        <param name="runMe" value="$runMe"/>
        </test><tests>"""
        xdict = {}
        xdict['script'] = self.script # configfile is least painful way to embed script to avoid external dependencies
        if self.opts.help_text:
            xdict['help'] = open(self.opts.help_text,'r').read()
        else:
            xdict['help'] = 'Please ask the tool author for help as none was supplied at tool generation'
        if self.opts.tool_desc:
            xdict['tooldesc'] = '<description>%s</description>' % self.opts.tool_desc
        else:
            xdict['tooldesc'] = ''
        xdict['command_outputs'] = '' 
        xdict['outputs'] = '' 
        if self.opts.input_tab <> 'None':
            xdict['command_inputs'] = '--input_tab "$input1"'
            xdict['inputs'] = '<param name="input1"  type="data" format="%s" label="Select a suitable input file from your history"/>' % self.inputFormats
        else:
            xdict['command_inputs'] = '' # assume no input - eg a random data generator          
            xdict['inputs'] = ''
        xdict['inputs'] += '<param name="job_name" type="text" label="Supply a name for the outputs to remind you what they contain" value="%s"/>\n' % self.toolname
        xdict['toolname'] = self.toolname
        xdict['toolid'] = self.toolid
        xdict['interpreter'] = self.opts.interpreter
        xdict['scriptname'] = self.sfile
        if self.opts.make_HTML:
            xdict['command_outputs'] += '--output_dir "$html_file.files_path" --output_html "$html_file" --make_HTML "yes"'
            xdict['outputs'] +=  '<data format="html" name="html_file" label="${job_name}.html"/>\n'
        if self.opts.output_tab <> 'None':
            xdict['command_outputs'] += '--output_tab "$tab_file"'
            xdict['outputs'] += '<data format="%s" name="tab_file" label="${job_name}"/>\n' % self.outFormats
        xdict['command'] = newCommand % xdict
        xmls = newXML % xdict
        xf = open(self.xmlfile,'w')
        xf.write(xmls)
        xf.write('\n')
        xf.close()
        # ready for the tarball


    def makeTooltar(self):
        """
        a tool is a gz tarball with eg
        /toolname/tool.xml /toolname/tool.py /toolname/test-data/test1_in.foo ...
        """
        retval = self.run()
        if retval:
            print >> sys.stderr,'## Run failed. Cannot build yet. Please fix and retry'
            sys.exit(1)
        self.makeXML()
        tdir = self.toolname
        os.mkdir(tdir)
        if self.opts.input_tab <> 'None': # we may have test data?
            testdir = os.path.join(tdir,'test-data')
            os.mkdir(testdir) # make tests directory
            shutil.copyfile(self.opts.input_tab,os.path.join(testdir,'test1_in.tab'))
            if self.opts.output_tab <> 'None':
                shutil.copyfile(self.opts.output_tab,os.path.join(testdir,'test1_out.tab'))
            if self.opts.make_HTML:
                shutil.copyfile(self.opts.output_html,os.path.join(testdir,'test1_out.html'))
            if self.opts.output_dir:
                shutil.copyfile(self.tlog,os.path.join(testdir,'test1_out.log'))
        shutil.copyfile(self.xmlfile,os.path.join(tdir,self.xmlfile))
        shutil.copyfile(self.pyfile,os.path.join(tdir,'%s.py' % self.toolname))
        shutil.copyfile(self.sfile,os.path.join(tdir,self.sfile))
        tarpath = "%s.gz" % self.toolname
        tar = tarfile.open(tarpath, "w:gz")
        tar.add(tdir,arcname=self.toolname)
        tar.close()
        shutil.copy(tarpath,self.opts.new_tool)
        shutil.rmtree(tdir)
        ## TODO: replace with optional direct upload to local toolshed?
        return retval

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

    def makeHtml(self):
        """ Create an HTML file content to list all the artefacts found in the output_dir
        """

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
        galhtmlattr = """<hr/><b><a href="http://rgenetics.org">Galaxy Tool Factory Script Wrapper</a> tool output %s run at %s</b><br/>""" 
        galhtmlpostfix = """</div></body></html>\n"""

        flist = os.listdir(self.opts.output_dir)
        flist = [x for x in flist if x <> 'Rplots.pdf']
        flist.sort()
        html = [galhtmlprefix % progname,]
        html.append('<h2>Galaxy %s outputs run at %s</h2><br/>\n' % (self.toolname,timenow()))
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
           fhtml.append('</ul><br/>')
           html += fhtml # add all non-pdf files to the end of the display
        else:
            html.append('<h2>### Error - %s returned no files - please confirm that parameters are sane</h1>' % self.opts.interpreter)
            html.append('<h3>%s log follows below</h3><hr/><pre><br/>\n' % self.opts.interpreter)
        rlog = open(self.tlog,'r').readlines()
        html += rlog
        html.append('<br/>%s CL = %s<br/>\n' % (self.toolname,' '.join(sys.argv)))
        html.append('</pre>\n')
        html.append(galhtmlattr % (progname,timenow()))
        html.append(galhtmlpostfix)
        htmlf = file(self.opts.output_html,'w')
        htmlf.write('\n'.join(html))
        htmlf.write('\n')
        htmlf.close()
        self.html = html


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
        if self.opts.make_HTML:
            self.makeHtml()
        return retval
  

def main():
    u = """
    This is a Galaxy wrapper. It expects to be called by a special purpose tool.xml as:
    <command interpreter="python">rgBaseScriptWrapper.py --script_path "$scriptPath" --tool_name "foo" --interpreter "Rscript"
    </command>
    """
    op = optparse.OptionParser()
    a = op.add_option
    a('--script_path',default=None)
    a('--tool_name',default=None)
    a('--interpreter',default=None)
    a('--output_dir',default=None)
    a('--output_html',default=None)
    a('--input_list',default=[],action="append")
    a('--output_tab',default="None")
    a('--user_email',default=None)
    a('--bad_user',default=None)
    a('--make_Tool',default=None)
    a('--make_HTML',default=None)
    a('--help_text',default=None)
    a('--tool_desc',default=None)
    a('--new_tool',default=None)
    opts, args = op.parse_args()
    assert not opts.bad_user,'%s is NOT authorized to use this tool. Please ask your friendly admin' % opts.bad_user
    assert opts.tool_name,'## Tool Factory expects a tool name - eg --tool_name=DESeq'
    assert opts.interpreter,'## Tool Factory wrapper expects an interpreter - eg --interpreter=Rscript'
    assert os.path.isfile(opts.script_path),'## Tool Factory wrapper expects a script path - eg --script_path=foo.R'
    if opts.output_dir:
        try:
            os.makedirs(opts.output_dir)
        except:
            pass
    r = ScriptRunner(opts)
    if opts.make_Tool:
        retcode = r.makeTooltar()
    else:
        retcode = r.run()
    if retcode:
        sys.exit(retcode) # indicate failure to job runner


if __name__ == "__main__":
    main()



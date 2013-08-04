"""
test eg:

/tmp/test$  python /data/galaxy/tools/rgenetics/rggoseq.py        --input "/data/galaxy/database/files/010/dataset_10750.dat"       
 --idColN "1"        --idType "refGene"        --splitOn "_"        --splitRange "0"        --pColN "2"       
 --dbKey "hg19"        --out_tab "foo.tab"        --out_html "foo.html"        --out_dir "."


rggoseq:
wrapper for goseq
modified from dge code
writes R code as stdin for rscript to avoid NFS complications from writing the R code then trying to execute it as a file 
ross lazarus mods november 18 2011 Boston.                                      
"""

import sys 
import shutil 
import subprocess 
import os 
import time 
import tempfile 
import optparse
import StringIO
myName = os.path.split(sys.argv[0])[1] 
myversion = 'V0.02 November 2011' 
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
galhtmlattr = """<b><a href="http://rgenetics.org">Galaxy Rgenetics</a> tool output %s run at %s</b><br/>""" 
galhtmlpostfix = """</div></body></html>\n"""

goseqR = """
do_goseq = function(fdrthresh=0.05,
inputfile="/home/ross/Downloads/t2d_vs_prediabDGE.xls",
pValcol="p.value",
genomeBuildKey = 'hg19',
geneIDdialect = 'geneSymbol',
OutputSig='topTable.xls',
geneIdcol=1,
amigourl="http://amigo.geneontology.org/cgi-bin/amigo/term_details?term=")
{ 

ef=function(s) {return(unlist(strsplit(s,splitchar))[splitN])} # split and return

library('goseq')
counts<-read.table(inputfile,header=T,row.names=F,sep='\t')                           
#Load tab file assume header
ngeneId = names(counts)[geneIdcol]
print(paste('## geneID col =',geneIdcol,'=',ngeneId,'\n'))
gid = counts[,ngeneId] # get col containing gene ids 
npval = names(counts)[pValcol]
print(paste('## pval col =',pValcol,'=',npval,'\n'))
pvals = counts[,npval]
bhpvals = p.adjust(pvals, method="BH")
bhpsig = as.integer(bhpvals < fdrthresh) 
names(bhpsig) = gid
pwf = nullp(bhpsig, genomeBuildKey, geneIDdialect)
wall=goseq(pwf,genomeBuildKey, geneIDdialect)
test=goseq(pwf,genomeBuildKey, geneIDdialect,method="Sampling",repcnt=2000)
pdf("Wallenius_vs_null.pdf")
plot(log10(wall[,2]), log10(test[match(test[,1],wall[,1]),2]), xlab="Wallenius p value (-log10(p))",
     ylab="Null (permuted) p-value (-log10(p)",main="Estimated vs Null p value distributions")
abline(0,1,col=3,lty=2)
grid(col="blue")
dev.off()
test = wall
test$ebh = p.adjust(test$over_represented_pvalue, method="BH")
test$esigt = test$ebh < fdrthresh
test$esig = as.integer(test$esigt)
enriched = test$category[test$esigt]

if (sum(test$esig) > 0)
{
gp = c()
gurl = c()
gont = c()
gdef = c()
gterm = c()
gsyn = c()
for(go in enriched){
 gp = c(gp,test$ebh[test$category==go])
 g = GOTERM[[go]]
 url=paste(amigourl,go,sep='')
 gurl = c(gurl,url)
 s = g@Ontology
 gont = c(gont,s)
 s = g@Definition
 gdef = c(gdef,s)
 s = g@Term
 gterm = c(gterm,s)
 y = g@Synonym
 s = paste(y,collapse=';') # ugh R.
 gsyn = c(gsyn,s)
 }

 topres = cbind(enriched,gurl,gp,gterm,gont,gdef,gsyn)
 colnames(topres) = c('GSID','AmigoURL','BH_AdjP','GTerm','GOntology','GDefinition','GSynonym')
 write.table(topres,file=OutputSig,sep="\t",col.names=T,row.names=F)
} # if

} # do_goseq


parameters <- commandArgs(trailingOnly=T)

## Error handling
if (length(parameters) < 6){
  print("Not enough Input files supplied. Specify at least two input files.", quote=F)
  print("", quote=F)
  usage()
}
ok = require('goseq') && require('GO.db')
if  (! ok) {
s = sessionInfo()
emess=paste("## this tool requires GO.db and goseq to be installed to this R\n",s)
write(emess, stderr())
quit(save=F, status=1)
}
fdrthresh           <- as.double(parameters[1])
inputfile   <- as.character(parameters[2])
pValcol   <- as.integer(parameters[3])
genomeBuildKey     <- as.character(parameters[4])
geneIDdialect     <- as.character(parameters[5])
OutputSig  <- as.character(parameters[6])
geneIdcol   <- as.integer(parameters[7])
do_goseq(fdrthresh,inputfile,pValcol,genomeBuildKey,geneIDdialect,OutputSig,geneIdcol)
#Run the main function
# for the log
sessionInfo()


"""


def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))
    
class goseq:
    """class is a wrapper for goseq - note hard coded script above so it's all in one place for Galaxy
       TODO: add separate analyses for up and down regulated genes - need to have fold change column and
       perhaps easier in the python part leaving the GO part as it is since that's working?
       need to add parameter - fold change to xml and to opts
    """

    def __init__(self,opts=None):
        """
        """
        self.myName=myName
        self.thumbformat = 'jpg'
        self.tlog = os.path.join(opts.out_dir,"%s_runner.log" % self.myName)
        self.rname = os.path.join(opts.out_dir,"%s.r" % self.myName) # leave a copy for user
        self.opts = opts
        # use this object as stdin for the rscript call because
        # rscript = open(rfname,'r') # nfs mounts seem to cause SGE problems if they're cached - where's the file?
        self.sanityCheck()
        self.cl = []
        a = self.cl.append
        a('Rscript')
        a('-') # use stdin
        a("%s" % opts.fdrthresh)
        a("%s" % opts.input)
        a("%s" % opts.pColN)
        a("%s" % opts.dbKey)    
        a("%s" % opts.idType)
        a("%s" % opts.out_tab)      
        a("%s" % opts.idColN)      
        self.warn = []

    def sanityCheck(self):
        """ check that pval col makes sense and no missing gene ids
        """
        sane = True
        sanes = ''
        pColN = int(opts.pColN) - 1 # python cf R
        idColN = int(opts.idColN) - 1 # python cf R
        indat = open(self.opts.input,'r').readlines()
        head = indat.pop(0)
        indat = [x.strip().split('\t') for x in indat]
        try:
            pvals = [x[pColN] for x in indat]
            gids = [x[idColN] for x in indat]
        except:
            sanes = '## goseq input Error: unable to parse idColN or pColN - first row = %s' % '\t'.join(indat[0])
            sane = False
            pvals = []
            gids = []
        maxp = max(pvals)
        minp = min(pvals)
        if maxp > 1.0 or minp < 0.0:
            sanes = '## goseq input Error: column %d (%s) has values outside 0 to 1 - %f to %f' % (pColN+1,head[pColN],minp,maxp)
            sane = False
        return sane,sanes   

    def compressPDF(self,inpdf=None,thumbformat='png'):
        """need absolute path to pdf
        this works a treat for mongo pdfs.
        """
        assert os.path.isfile(inpdf), "## Input %s supplied to %s compressPDF not found" % (inpdf,self.myName)
        sto = open(self.tlog,'a')
        outpdf = '%s_compressed' % inpdf
        cl = ["gs", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-sOutputFile=%s" % outpdf,inpdf]
        x = subprocess.Popen(cl,stdout=sto,stderr=sto,cwd=self.opts.out_dir)
        retval1 = x.wait()
        if retval1 == 0:
            os.unlink(inpdf)
            shutil.move(outpdf,inpdf)
        outpng = '%s.%s' % (os.path.splitext(inpdf)[0],thumbformat)
        cl2 = ['convert', inpdf, outpng]
        x = subprocess.Popen(cl2,stdout=sto,stderr=sto,cwd=self.opts.out_dir)
        retval2 = x.wait()
        sto.close()
        retval = retval1 or retval2
        return retval

    def do_run(self):
        """
        """
        sto = open(self.tlog,'w')
        sane,sanes = self.sanityCheck()
        if not sane:
            print >> stderr, sanes
            sys.exit(1) # flag error
        p = subprocess.Popen(' '.join(self.cl),shell=True,stdin=subprocess.PIPE,stdout=sto,stderr=sto,cwd=self.opts.out_dir)
        p.stdin.write(goseqR)
        p.stdin.close()
        retval = p.wait()
        sto.close()
        r = open(self.rname,'w') # so the user sees the code
        r.write(goseqR)
        r.write('\n')
        r.close()
        flist = os.listdir(self.opts.out_dir)
        flist.sort()
        html = [galhtmlprefix % progname,]
        html.append('<h2>Galaxy goseq outputs run at %s</h2></br>Click on the images below to download high quality PDF versions</br>\n' % timenow())
        if len(self.warn) > 0:
            html.append('<h3>WARNING:</h3>\n<ol>')
            for w in self.warn:
                html.append('<li>%s</li>' % w)
            html.append('</ol>\n')
        if len(flist) > 0:
            html.append('<table>\n')
            for fname in flist:
                dname,e = os.path.splitext(fname)
                if e.lower() == '.pdf' : # compress and make a thumbnail
                    thumb = '%s.%s' % (dname,self.thumbformat)
                    pdff = os.path.join(self.opts.out_dir,fname)
                    retval = self.compressPDF(inpdf=pdff,thumbformat=self.thumbformat)
                    if retval == 0:
                        s= '<tr><td><a href="%s"><img src="%s" title="Click to download a print quality PDF of %s" hspace="10" width="600"></a></td></tr>' \
                         % (fname,thumb,fname)
                    else:
                        dname = '%s (thumbnail image not_found)' % fname
                        s= '<tr><td><a href="%s">%s</a></td></tr>' % (fname,dname)
                    html.append(s)
                else:
                   html.append('<tr><td><a href="%s">%s</a></td></tr>' % (fname,fname))
            html.append('</table>\n')
        else:
            html.append('<h2>### Error - R returned no files - please confirm that parameters are sane</h1>')
        html.append('<h3>R log follows below</h3><hr><pre>\n')
        rlog = open(self.tlog,'r').readlines()
        rlog = [x.strip() for x in rlog if len(x.strip()) > 1] 
        rlog = [x for x in rlog if x.find(' %') == -1]
        html += rlog
        html.append('%s CL = %s</br>\n' % (self.myName,' '.join(sys.argv)))
        html.append('goseq.R CL = %s</br>\n' % (' '.join(self.cl)))
        html.append('</pre>\n')
        html.append(galhtmlattr % (progname,timenow()))
        html.append(galhtmlpostfix)
        htmlf = file(self.opts.out_html,'w')
        htmlf.write('\n'.join(html))
        htmlf.write('\n')
        htmlf.close()
        return retval
  


def test(opts=None):
     t = trinuc(opts=opts)
     for x in ['AAAAAACCAAAACCAAACAAATAAAAACCCCAAAT','GGGCTACATGACGGTCCTGTATTTAGCCAGAGGATC','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']:
        v = t.countTris(x)
        print x,v 


def main():
    u = """
    This is a Galaxy wrapper. It expects to be called by goseq.xml as:
  <command>
    rggoseq.py
       --input "$input"
       --idColN "$idColN"
       --idType "$idType"
       --pColN "$pColN"
       --dbKey "${input.metadata.dbkey}"
       --out_tab "$out_tab"
       --out_html "$out_html"
       --out_dir "$out_html.files_path"
  </command>
    """
    op = optparse.OptionParser()
    a = op.add_option
    a('--input',default=None)
    a('--out_tab',default=None)
    a('--out_html',default=None)
    a('--out_dir',default=None)
    a('--idColN',default=None)
    a('--pColN',default=None)
    a('--idType',default=None)
    a('--dbKey',default=None)
    a('--fdrthresh',default='0.05')
    opts, args = op.parse_args()
    assert os.path.isfile(opts.input),'## goseq runner unable to open supplied input file %s' % opts.input
    assert opts.pColN,'## goseq runner requires a pCol eg --pCol 4'
    assert opts.idType,'## goseq runner requires Gene ID column eg --idType - eg refGene'
    if not os.path.exists(opts.out_dir):
        os.makedirs(opts.out_dir)
    m = goseq(opts=opts)
    retcode = m.do_run()
    if retcode:
        print >> sys.stderr, '##ERROR: goseq.r returned an error status - check the log for details'
        sys.exit(retcode) # indicate failure to job runner
 
 


if __name__ == "__main__":
    main()


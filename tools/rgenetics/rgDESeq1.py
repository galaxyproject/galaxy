# ross lazarus
# updated nov 2011 for R 2.14.0 and edgeR update 
import sys 
import shutil 
import subprocess 
import os 
import time 
import tempfile 
import optparse

progname = os.path.split(sys.argv[0])[1] 
myversion = 'V000.1 September 2011' 
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

DESeqSCRIPT="""
library('DESeq')
library('biomaRt')
# some code developed for Tom Karagianis
# feb 2012
# copyright ross lazarus
# licensed under the LGPL
# enjoy
# TODO: translate transcripts into gene names. Could use synergizer

doPPlot = T

getGnames = function(keys=c("NM_006945", "NM_152486", "NM_198317"),attribs=c('REFSEQ','SYMBOL','GENENAME'),keytype="REFSEQ",organism='Hs')
{
# quick way to lookup keys (eg nm_ numbers) - make sure right db file is in play
if (! organism %in% c('Mm','Hs'))
   stop(paste('## unknown organism',organism,'passed to getGnames - halting'))

if (organism == 'Mm')
    if (! require(org.Mm.eg.db)) stop('Cannot load org.Mm.eg.db - please install it')
       else gn = select(org.Mm.eg.db,keys,cols=attribs,keytype=keytype)
  
if (organism == 'Hs') {
    if (! require(org.Hs.eg.db)) stop('Cannot load org.Hs.eg.db - please install it')
       else gn = select(org.Hs.eg.db,keys,cols=attribs,keytype=keytype)
    }
rownames(gn) = gn[,attribs[1]]
return(gn)
}

mdsPlot = function(cmat,myTitle,groups,treatname)
{
# Classical MDS
# N rows (objects) x p columns (variables)
# each row identified by a unique row name
    col.map = function(g) {if (g==treatname) "#FF0000" else "#0000FF"}
    pcols = unlist(lapply(groups,col.map))
    mydata = t(cmat) # transpose
    #mydata = log2(mydata)
    d <- dist(mydata) # euclidean distances between the rows
    fit <- cmdscale(d,eig=TRUE, k=2) # k is the number of dim
    # plot solution 
    x <- fit$points[,1]
    y <- fit$points[,2]
    plot(x, y, xlab="Dimension 1", ylab="Dimension 2", 
       main=paste(myTitle,"MDS"),type="n", col=pcols)
    text(x, y, labels = row.names(mydata), cex=0.7, col=pcols)
    legend(x="topleft",legend=unique(groups),fill=unique(pcols))
}

hmapPlot = function(cmat,myTitle,groups,treatname,nsamp=250,sFactors=c())
{ 
    nrows = nrow(cmat) 
    col.map = function(g) {if (g==treatname) "#FF0000" else "#0000FF"}
    pcols = unlist(lapply(groups,col.map))
    mtitle = paste('Heatmap:',nrows,'Contigs')
    if (nrows > nsamp) {
      cmat = cmat[1:nsamp,]
      mtitle = paste('Heatmap of top ',nsamp,' normalised differential counts from ',nrows,' contigs)',sep='')
    }
    for (col in 1:length(sFactors)) cmat[,col] = cmat[,col]/sFactors[col]
    colnames(cmat) = groups
    outpdfname = paste(myTitle,'heatMap.pdf',sep='_')
    pdf(outpdfname)
    heatmap(cmat,main=mtitle,cexRow=0.3,cexCol=0.5,ColSideColors=pcols)
    dev.off()
}
cumPlot = function(rs,maint,myTitle)
{   # too many zeros...
        pdfname = paste(myTitle,"RowsumCum.pdf",sep='_')
        pdf(pdfname)
        crs = sort(rs,decreasing=T)
        nrs = length(crs)
        xvec = 1:nrs
        xvec = 100.0*((nrs-xvec) / nrs)
        hist(rs,breaks=250, ylim=c(0,1000),main=maint,xlab="Contig Row Sum",
              ylab="N (Truncated at 1000)",col="maroon")
        dev.off()
}

qqPlot = function(pvector, main=NULL, ...)
# stolen from https://gist.github.com/703512
{
    o = -log10(sort(pvector,decreasing=F))
    e = -log10( 1:length(o)/length(o) )
    plot(e,o,pch=19,cex=1, main=main, ...,
        xlab=expression(Expected~~-log[10](italic(p))),
        ylab=expression(Observed~~-log[10](italic(p))),
        xlim=c(0,max(e)), ylim=c(0,max(o)))
    lines(e,e,col="red")
    grid(col = "lightgray", lty = "dotted")
}

maPlot = function(bint,tannotation,myTitle,thresh=0.05)
# maplot with red significant genes
{ 
    nsig = nrow(subset(bint,bint$padj < thresh))
    pdfname = paste(tannotation,'MAplot.pdf',sep='_')
    pdf(pdfname)
    plot(bint$baseMean,bint$log2FoldChange,log="x",
         main=paste(myTitle,' MA Plot ',nsig,' (Red) significant at FDR=',thresh,sep=''),sub=tannotation,xlab="Normalised Mean Expression",ylab="log2 Fold Change",
         pch=20,cex=ifelse(bint$padj < thresh,0.3,0.1),col=ifelse(bint$padj < thresh,"red","black"))
    abline(h=0,v=0,col="darkblue")
    grid( col = "lightgray", lty = "dotted")
    dev.off()
    if (doPPlot) {
    pdfname = paste(tannotation,'pval_qq.pdf',sep='_')
    pdf(pdfname)
        qqPlot(bint$pval,main=paste(tannotation,'QQ plot'))
    dev.off()
    }
}

diagPlot = function(countd,myTitle) 
{
    pdfname = paste(myTitle,'dispEsts.pdf',sep='_')
    pdf(pdfname) 
    plot(rowMeans(counts(countd,normalized=T)), 
    fitInfo(countd)$perGeneDispEsts,
    main=paste(myTitle,'Gene Dispersion Estimate Plot'),xlab="Mean Expresson",ylab="Dispersion",
    pch='.',log='xy',sub="(Red line = dispersion model chosen)")
    xg = 10^seq(-0.5,5,length.out=300)
    lines(xg,fitInfo(countd)$dispFun(xg),col="red")
    grid( col = "lightgray", lty = "dotted")
    dev.off()
}

writeRnk = function(descr,annores)
{ 
    realFc = abs(annores$log2FoldChange)
    realBig = max(realFc[realFc != Inf])
    values = ifelse(abs(annores$log2FoldChange) == Inf,ifelse(annores$baseMeanA==0,-annores$baseMeanB-realBig,annores$baseMeanA+realBig),annores$log2FoldChange)
    # fiddle Inf and -Inf values to keep them at the top/bottom for gsea
    # horrible hack necessitated by TomK's single sample analyses where zero counts are found in some samples but large counts in others..
    dtt = data.frame(Contig=annores$REFSEQ,Rankval=values,row.names=NULL)
    dtt = dtt[! (is.na(dtt$Contig) | is.na(dtt$Rankval)),] # GSEA does not like na's
    dtt = dtt[order(dtt$Rankval,decreasing=T),]
    outf = paste(descr,'.rnk',sep='')
    write.table(dtt,file=outf,col.names=T,row.names=FALSE,sep='\t',quote=FALSE) 
}

doOne = function(cleand,f1,f2,myTitle,fdrthresh,useAnno,doRnk,nToShow,topTable,groups) {

    descr = paste(myTitle,f1,'vs',f2,sep='_')
    tres = nbinomTest(cleand,f1,f2)
    annores = cbind(useAnno,subset(tres,select = -id))
    annores = annores[order(annores$pval),]
    fn = topTable
    write.table(annores,file=fn,row.names=F,sep='\t',quote=F)
    rownames(annores) = 1:nrow(annores)
    print(paste('Top',nToShow,'For',descr),quote=F)
    print(head(annores,n=nToShow),quote=F)
    if (doRnk==T) writeRnk(descr,annores)
    cmat = counts(cleand)
    cmat = cmat[order(tres$padj,decreasing=F),]
    mdsPlot(cmat=cmat,myTitle=myTitle,groups=groups,treatname=f1)
    maPlot(bint=tres,tannotation=descr,myTitle=myTitle,thresh=fdrthresh)
    sFactors = sizeFactors(cleand)
    hmapPlot(cmat=cmat,myTitle=myTitle,groups=groups,treatname=f1,nsamp=200,sFactors)    
}
        
doDESeq = function(rawd,myTitle='DESeq',conditions=c(),myOrg='none',topTable='topTable.xls',
                    keytype="REFSEQ",fdrthresh=0.05,filterquantile=0.3,nToShow=20,doRnk=T)
{
        # do allpairs if no conditions passed in
        options(width=512)
        doAllpairs = F
        cn = colnames(rawd)
        nsamp = length(cn)
        if (length(conditions) == nsamp) {
               conds = conditions
               print(paste('## Note: doDESeq using conditions = ',paste(conds,collapse=',')))
               }              
        else { conds = cn # if no conds passed in assume is all pairs
               print(paste('## Warning: doDESeq got conditions = ',paste(conditions,collapse=','),'but colnames = ',
                   paste(cn,collapse=','),' so using colnames and comparing all possible pairs of individual samples')) 
               doAllpairs = T
               allPairs = combn(unique(cn),2)
               }
        conds = factor(conds)
        classes = unique(conds)
        if (length(classes) > 2)
            stop(paste('## This version of DESeq unable to deal with >2 classes - got',classes))
        rawd = newCountDataSet(rawd,conds)
        rs = rowSums(counts(rawd))
        allN = length(rs)
        nonzerod = rawd[(rs > 0),] # remove all zero count genes
        rs = rowSums(counts(nonzerod)) # after removing no shows
        nzN = length(rs)
        useme = (rs > quantile(rs,filterquantile))
        cleand = nonzerod[useme,]
        cleanrs = rowSums(counts(cleand))
        cleanN = length(cleanrs)
        maint = paste(myTitle,'(NS filter at',filterquantile,'quantile)')
        cumPlot(cleanrs,maint,myTitle)
        cid = rownames(counts(cleand))
	if (myOrg == 'none')
              gnames = data.frame(REFSEQ=cid,rownames=cid) 
        else  gnames = getGnames(keys=gs,keytype=keytype,attribs=c('REFSEQ','SYMBOL','GENENAME'),organism=myOrg)  
        useAnno = gnames # annotation
        cleand = estimateSizeFactors(cleand)
        sFactors = sizeFactors(cleand)
        print(paste('## Read',allN,'probes. Removed',nzN,'probes with no reads. After filtering at count quantile =',filterquantile,'there are',cleanN,'probes to analyse'),quote=F)
        print('## DESeq estimated size factors for each sample:',quote=F)
        print(sFactors,quote=F)
        if (doAllpairs == T) 
          { # blind - no variances
                cleand = estimateDispersions(cleand,method="blind",sharingMode="fit-only")
                for (coln in 1:ncol(allPairs)) {
                        f1 = allPairs[1,coln]
                        f2 = allPairs[2,coln]
                        doOne(cleand=cleand,f1=f1,f2=f2,myTitle=myTitle,fdrthresh=fdrthresh,
                            useAnno=useAnno,doRnk=doRnk,nToShow=nToShow,topTable=topTable,groups=conds)
                }
         } else  {
                cleand = estimateDispersions(cleand)
                doOne(cleand=cleand,f1=classes[1],f2=classes[2],myTitle=myTitle,fdrthresh=fdrthresh,
                useAnno=useAnno,doRnk=doRnk,nToShow=nToShow,topTable=topTable,groups=conds)                
          }
        diagPlot(cleand,myTitle)
        print(sessionInfo())
        print(paste('##',date(),'Completed',myTitle),quote=F)
}


parameters <- commandArgs(trailingOnly=T)

## Error handling
if (length(parameters) < 10){
  print(paste("Not enough command line parameters supplied: ",paste(parameters,collapse=' ')), quote=F)
  print("", quote=F)
}

Out_Dir         <- as.character(parameters[1])
Input           <- as.character(parameters[2])
TreatmentName   <- as.character(parameters[3])
TreatmentCols   <- as.character(parameters[4])
ControlName     <- as.character(parameters[5])
ControlCols     <- as.character(parameters[6])
outputfilename  <- as.character(parameters[7])
fdrtype  <- as.character(parameters[8])
fdrthresh = as.numeric(parameters[9])
myTitle = as.character(parameters[10])
myOrg = as.character(parameters[11])
filterquantile = as.numeric(parameters[12])

#Set our columns 
TCols           = as.numeric(strsplit(TreatmentCols,",")[[1]])-1  
CCols           = as.numeric(strsplit(ControlCols,",")[[1]])-1  
cat('## got TCols=')
cat(TCols)
cat('; CCols=')
cat(CCols)
cat('\n')

group<-strsplit(TreatmentCols,",")[[1]]

## Create output dir if non existent
if (file.exists(Out_Dir) == F) dir.create(Out_Dir)

Count_Matrix<-read.table(Input,header=T,row.names=1,sep='\t')                           #Load tab file assume header
Count_Matrix<-Count_Matrix[,c(TCols,CCols)]
rn = rownames(Count_Matrix)
islib = rn %in% c('librarySize','NotInBedRegions')
LibSizes = Count_Matrix[subset(rn,islib),][1] # take first
Count_Matrix = Count_Matrix[subset(rn,! islib),]
group<-c(rep(TreatmentName,length(TCols)), rep(ControlName,length(CCols)) )             #Build a group descriptor
colnames(Count_Matrix) <- paste(group,colnames(Count_Matrix),sep="_")                   #Relable columns

results <- doDESeq (rawd=Count_Matrix,myTitle=myTitle,conditions=group,myOrg=myOrg,topTable=outputfilename,
        keytype="REFSEQ",fdrthresh=0.05,filterquantile=filterquantile,nToShow=20,doRnk=T) #Run the main function
# for the log
sessionInfo()

"""

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))
    
class DESeq:
    """class is a wrapper for deseq - note hard coded script above so it's all in one place for Galaxy"""

    def __init__(self,myName=None,opts=None):
        """
Out_Dir         <- as.character(parameters[1])
Input           <- as.character(parameters[2])
TreatmentName   <- as.character(parameters[3])
TreatmentCols   <- as.character(parameters[4])
ControlName     <- as.character(parameters[5])
ControlCols     <- as.character(parameters[6])
outputfilename  <- as.character(parameters[7])
fdrtype  <- as.character(parameters[8])
fdrthresh = as.numeric(parameters[9])
myTitle = as.character(parameters[10])
myOrg = as.character(parameters[11])
        """
        self.jtitle = opts.jtitle.replace(' ','_')
        self.thumbformat = 'jpg'
        self.tlog = os.path.join(opts.output_dir,"DESeq_runner.log")
        self.opts = opts
        self.myName=myName
        warn = []
        if not os.path.exists(opts.output_dir):
            os.makedirs(opts.output_dir)
            warn.append('##Info: created %s' % opts.output_dir)             
        artifactpath = os.path.join(opts.output_dir,'DESeq.R') 
        artifact = open(artifactpath,'w')
        artifact.write(DESeqSCRIPT)
        artifact.close()
        self.cl = []
        a = self.cl.append
        a('Rscript --verbose')
        a('-') # use stdin rather than artifactpath or set noac in nfs mount
        a("'%s'" % opts.output_dir) # quote everything or problems with spaces in names
        a("'%s'" % opts.input_matrix)
        a("'%s'" % opts.treatname)
        a("'%s'" % opts.treatcols)
        a("'%s'" % opts.ctrlname)
        a("'%s'" % opts.ctrlcols)
        a("'%s'" % opts.output_tab)        
        a("'%s'" % opts.fdrtype)            
        a("%s" % opts.fdrthresh)        
        a("'%s'" % self.jtitle)        
        a("'%s'" % opts.org)        
        a("'%s'" % opts.filterQuantile)        
        tc = opts.treatcols.split(',')
        stc = set(tc)
        cc = opts.ctrlcols.split(',')
        scc = set(cc)
        if len(scc) <> len(cc):
            self.opts.ctrlcols = ','.join(scc)
            warn.append('##WARNING - duplicate control columns supplied %s - reduced to unique set %s' % (','.join(cc),','.join(scc)))
        if len(stc) <> len(tc):
            self.opts.treatcols = ','.join(stc)
            warn.append('##WARNING - duplicate treatment columns supplied %s - reduced to unique set %s' % (','.join(tc),','.join(stc)))
        self.warn = warn

    def remove_redundancy(sl=[],delim='_'):
        """ take a list of strings and return it filtered of all delim substrings common to all strings
         eg ['a_b_c','b_z','b_q_y'] -> ['a_c','z','q_y']
        """
        clean = []
        sls = [x.split(delim) for x in sl] # substring list
        c = {} # concordance count for all substrings
        ns = len(sl) # n input strings
        for i,ilist in enumerate(sls):
            for j,ss in enumerate(ilist):
                try:
                   n = int(ss)
                except ValueError: # don't process simple integers - may be important ids so can be redundant
                    clist = c.get(ss,[]) # empty list if ss is new term
                    clist.append(i) 
                    c[ss] = clist # each entry has a list of strings containing it
        in_all = [x for x in c if len(c[x]) == ns] # words in concordance present in ALL strings
        nall = len(in_all)
        if nall > 0:
            din_all = dict(zip(in_all,range(nall))) # for faster lookups
            for i,ilist in enumerate(sls):
                lclean = [] # new substring list for unfiltered substrings
                for j,ss in enumerate(ilist):
                    if din_all.get(ss,None) == None: # not common to all inputs
                       lclean.append(ss) # ready to construct new string
                clean.append(delim.join(lclean)) # restore delim in non redundant verson
            return clean
        else:
            return sl    


    def compressPDF(self,inpdf=None,thumbformat='png'):
        """need absolute path to pdf
        """
        assert os.path.isfile(inpdf), "## Input %s supplied to %s compressPDF not found" % (inpdf,self.myName)
        hf,hlog = tempfile.mkstemp(suffix="dgecompress.log")
        sto = open(hlog,'w')
        outpdf = '%s_compressed' % inpdf
        cl = ["gs", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-sOutputFile=%s" % outpdf,inpdf]
        x = subprocess.Popen(' '.join(cl),stdout=sto,stderr=sto,shell=True,cwd=self.opts.output_dir)
        retval1 = x.wait()
        try:
            os.unlink(inpdf)
            shutil.move(outpdf,inpdf)
        except:
            self.warn.append('Unable to copy %s to %s' % (outpdf,inpdf))
        outpng = '%s.%s' % (os.path.splitext(inpdf)[0],thumbformat)
        cl2 = ['convert', inpdf, outpng]
        x = subprocess.Popen(' '.join(cl2),stdout=sto,stderr=sto,shell=True,cwd=self.opts.output_dir)
        retval2 = x.wait()
        sto.close()
        clog = open(hlog,'r').readlines()
        retval = retval1 + retval2
        return retval,clog

    def run(self):
        """
        """
        sto = open(self.tlog,'w')
        p = subprocess.Popen(' '.join(self.cl),shell=True,stdout=sto,stderr=sto,stdin=subprocess.PIPE,cwd=self.opts.output_dir)
        p.stdin.write(DESeqSCRIPT)
        p.stdin.close()
        #p.communicate(DESeqSCRIPT)
        retval = p.wait()
        sto.close()
        flist = os.listdir(self.opts.output_dir)
        flist.sort()
        html = [galhtmlprefix % progname,]
        html.append('<h2>Galaxy DESeq outputs run at %s with FDR threshold=%s</h2></br>Click on the images below to download as PDF</br>\n' % (timenow(),self.opts.fdrthresh))
        if len(flist) > 0:
            html.append('<table>\n')
            for fname in flist:
                dname,e = os.path.splitext(fname)
                if e.lower() == '.pdf' : # compress and make a thumbnail
                    thumb = '%s.%s' % (dname,self.thumbformat)
                    pdff = os.path.join(self.opts.output_dir,fname)
                    retval,clog = self.compressPDF(inpdf=pdff,thumbformat=self.thumbformat)
                    if len(clog) > 0:
                        self.warn += clog
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
        html += rlog
        html.append('%s CL = %s</br>\n' % (self.myName,' '.join(sys.argv)))
        html.append('DGE.R CL = %s</br>\n' % (' '.join(self.cl)))
        html.append('</pre>\n')
        if len(self.warn) > 0:
            html.append('<h3>Notes:</h3>\n<ol>')
            for w in self.warn:
                html.append('<li>%s</li>' % w)
            html.append('</ol>\n')
        html.append(galhtmlattr % (progname,timenow()))
        html.append(galhtmlpostfix)
        htmlf = file(self.opts.output_html,'w')
        htmlf.write('\n'.join(html))
        htmlf.write('\n')
        htmlf.close()
        return retval
  

def main():
    u = """
    This is a Galaxy wrapper. It expects to be called by DGE.xml as:
  <command interpreter="python">rgDGE.py --output_html "$html_file.files_path" --input_matrix "$input1" --treatcols "$Treat_cols"
       --treatname "$treatment_name" --ctrlcols "$Control_cols" --ctrlname "$control_name" --output_tab "$outtab" --output_html
        "$html_file" --output_dir "$html_file.files_path"   --fdrtype "$fdrtype" --priorn "$priorn" --fdrthresh "$fdrthresh"
  </command>
    """
    op = optparse.OptionParser()
    a = op.add_option
    a('--input_matrix',default=None)
    a('--output_tab',default=None)
    a('--output_html',default=None)
    a('--treatcols',default=None)
    a('--treatname',default='Treatment')
    a('--ctrlcols',default=None)
    a('--ctrlname',default='Control')
    a('--output_dir',default=None)
    a('--fdrtype',default='BY') #  fdr/BH/holm/hochberg/hommel/bonferroni/BY/none
    a('--fdrthresh',default='0.05')
    a('--jtitle',default='DESeq')
    a('--org',default='none')
    a('--filterQuantile',default='0.3')
    opts, args = op.parse_args()
    assert opts.input_matrix and opts.output_html,u
    assert os.path.isfile(opts.input_matrix),'## DESeq runner unable to open supplied input file %s' % opts.input_matrix
    assert opts.treatcols,'## DESeq runner requires a comma separated list of treatment columns eg --treatcols 4,5,6'
    assert opts.treatcols,'## DESeq runner requires a comma separated list of control columns eg --ctlcols 2,3,7'
    myName=os.path.split(sys.argv[0])[-1]
    m = DESeq(myName, opts=opts)
    retcode = m.run()
    if retcode:
        sys.exit(retcode) # indicate failure to job runner
 
 
 
if __name__ == "__main__":
    main()




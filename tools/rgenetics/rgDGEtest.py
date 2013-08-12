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
if (organism == 'Mm') {
    if ! require(org.Mm.eg.db) stop('Cannot load org.Mm.eg.db - please install it')
    else gn = select(org.Mm.eg.db,keys,cols=attribs,keytype=keytype)
else if (organism) == 'Hs') {
    if ! require(org.Hs.eg.db) stop('Cannot load org.Hs.eg.db - please install it')
    else gn = select(org.Hs.eg.db,keys,cols=attribs,keytype=keytype)
    }
else stop(paste('## unknown organism',organism,'passed to getGnames - halting')
rownames(gn) = gn$REFSEQ
return(gn)
}

cumPlot = function(rs,myTitle)
{   # too many zeros...
        pdfname = paste(myTitle,"readCountCum.pdf",sep='_')
        pdf(pdfname)
        crs = sort(rs,decreasing=T)
        nrs = length(crs)
        xvec = 1:nrs
        xvec = 100.0*((nrs-xvec) / nrs)
        hist(rs, col="maroon", breaks=100, ylim=c(0,1000),main=myTitle,sub="Read Count Distribution (counts truncated at 1000)",ylab="Read Count")
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
    dtt = data.frame(annores$REFSEQ,values,row.names=NULL)
    colnames(dtt) = c('Contig','Rankval')
    dtt = dtt[! (is.na(dtt$Contig) | is.na(dtt$Rankval)),] # GSEA does not like na's
    dtt = dtt[order(dtt$Rankval,decreasing=T),]
    outf = paste(descr,'.rnk',sep='')
    write.table(dtt,file=outf,col.names=T,row.names=FALSE,sep='\t',quote=FALSE) 
}

doOne = function(cleand,f1,f2,myTitle,fdrthresh,useAnno,doRnk,nToShow) {

    descr = paste(myTitle,f1,'vs',f2,sep='_')
    tres = nbinomTest(cleand,f1,f2)
    maPlot(bint=tres,tannotation=descr,myTitle=myTitle,thresh=fdrthresh)
    annores = cbind(useAnno,subset(tres,select = -id))
    annores = annores[order(annores$pval),]
    fn = paste(descr,'topTable.xls',sep='_')
    write.table(annores,file=fn,row.names=F,sep='\t',quote=F)
    rownames(annores) = 1:nrow(annores)
    print(paste('Top',nToShow,'For',descr),quote=F)
    print(head(annores,n=nToShow),quote=F)
    if (doRnk==T) writeRnk(descr,annores)
}
        
doDESeq = function(exf = 'EX094_human_mRNA-seq_counts.txt',myTitle='TomK_DESeq_Feb2012',conditions=c(),
                                        keytype="REFSEQ",fdrthresh=0.05,filterquantile=0.3,nToShow=20,doRnk=T)
{
        # do allpairs if no conditions passed in
        options(width=512)
        doAllpairs = F
        print(paste('## ',date(),'Starting',myTitle,'using inputfile = ',exf),quote=F)
        rawd = read.table(exf,head=T,sep='\t',row.names=1)
        cn = colnames(rawd)
        gs = rownames(rawd)
        gn = getGnames(keys=gs,keytype=keytype) 
        nsamp = length(cn)
        if (length(conditions) == nsamp]) {
               conds = conditions
               print(paste('## Note: doDESeq using conditions = ',conds))              
        else { conds = cn # if no conds passed in assume is all pairs
               print(paste('## Warning: doDESeq got conditions = ',conditions,'but colnames = ',cn,' so using colnames and comparing all possible pairs of individual samples')) 
               doAllpairs = T
               allPairs = combn(unique(cn),2)
             }
        conds = factor(conds)
        rawd = newCountDataSet(rawd,conds)
        rs = rowSums(counts(rawd))
        allN = length(rs)
        cumPlot(rs,myTitle)
        nonzerod = rawd[(rs > 0),] # remove all zero count genes
        rs = rowSums(counts(nonzerod)) # after removing no shows
        nzN = length(rs)
        useme = (rs > quantile(rs,filterquantile))
        cleand = nonzerod[useme,]
        cleanrs = rowSums(counts(cleand))
        cleanN = length(cleanrs)
        cumPlot(cleanrs,paste(myTitle,'After NS filter at',filterquantile,'quantile'))
        cid = rownames(counts(cleand))
        useAnno = gn[cid,] # annotation
        cleand = estimateSizeFactors(cleand)
        print(paste('## Read',allN,'probes. Removed',nzN,'probes with no reads. After filtering at count quantile =',filterquantile,'there are',cleanN,'probes to analyse'),quote=F)
        print('## DESeq estimated size factors for each sample:',quote=F)
        print(sizeFactors(cleand),quote=F)
        if (doAllpairs == T) 
          { # blind - no variances
                cleand = estimateDispersions(cleand,method="blind",sharingMode="fit-only")
                for (coln in 1:ncol(allPairs)) {
                        f1 = allPairs[1,coln]
                        f2 = allPairs[2,coln]
                        doOne(cleand=cleand,f1=f1,f2=f2,myTitle=myTitle,fdrthresh=fdrthresh,useAnno=useAnno,doRnk=doRnk,nToShow=nToShow)
                }
         } else  {
                cleand = estimateDispersions(cleand)
                doOne(cleand=cleand,f1=conds[1],f2=conds[2],myTitle=myTitle,fdrthresh=fdrthresh,useAnno=useAnno,doRnk=doRnk,nToShow=nToShow)                
          }
        diagPlot(cleand,myTitle)
        print(sessionInfo())
        print(paste('##',date(),'Completed',myTitle,'using inputfile = ',exf),quote=F)
}


doDESeq(exf = 'EX094_human_mRNA-seq_counts.txt',myTitle='TomK_DESeq_Feb2012',keytype="REFSEQ",fdrthresh=0.05,nToShow=20)

"""


edgeRSCRIPT="""
#### edgeR.Rscript
# updated npv 2011 for R 2.14.0 and edgeR 2.4.0 by ross
# Performs DGE on a count table containing n replicates of two conditions
#
# Parameters
#
# 1 - Output Dir

# Writen by: S.Lunke and A.Kaspi
####


usage <- function(){
  print("#### edgeR.R", quote=F)
  print("", quote=F)
  print("Performs DGE on a count table containing n replicates of two conditions", quote=F)
  print("", quote=F)
  print("USAGE: Rscript edgeR.R <OUT_DIR> <INPUT> <TreatmentName> <ControlName> <Treatcol1,2,3> <Controlcol1,2,3>", quote=F)
  print("", quote=F)
  print(" Parameters", quote=F)
  print("", quote=F)
  print(" 1 - Output Dir", quote=F)
  print(" 2 - Input File", quote=F)
  print(" 3 - Treatment name", quote=F)
  print(" 4 - Treatment Columns i.e. 3,4,6", quote=F)
  print(" 5 - Control name", quote=F)
  print(" 6 - Control Columns i.e. 2,7,8", quote=F)
  print(" 7 - Output tabular file name", quote=F)
  print(" 8 - FDR method (fdr/BH/holm/hochberg/hommel/bonferroni/BY/none", quote=F)


  print("", quote=F)
  print(" Interface writen by: S.Lunke and A.Kaspi", quote=F)
  print(" Makes extensive use of the edgeR software - Mark D. Robinson, Davis J. McCarthy, Gordon K. Smyth, PMCID: PMC2796818", quote=F)
  print("####", quote=F)
  q()
   }

hmap = function(normData,DE,nmeans=4,outpdfname="heatMap.pdf",nsamp=250,fdrthresh=0.05,TName='Treatment',group=NA)
{
# Perform clustering for significant pvalues after controlling FWER
    col.map = function(g) {if (g==TName) "#FF0000" else "#0000FF"}
    pcols = unlist(lapply(group,col.map))
    DEG = normData[p.adjust(DE$table$p.value, method=fdrtype) < fdrthresh,]
    kdegs = DEG
    nrows = nrow(DEG)
    mtitle = paste('Heatmap: DE genes n =',nrows)
    if (nrows > nsamp) {
      kdegs = DEG[sample(nrows,nsamp),]
      mtitle = paste('Heatmap: Random subset of ',nsamp,' from ',nrows,' DE genes)',sep='')
    }
    newcolnames = substr(colnames(kdegs),1,20)
    colnames(kdegs) = newcolnames
    pdf(outpdfname)
    heatmap(kdegs,main=mtitle,cexRow=0.3,cexCol=0.5,ColSideColors=pcols)
    dev.off()
}
## edgeIt runs edgeR
edgeIt <- function (Count_Matrix,group,outputfilename,fdrtype='fdr',priorn=5,fdrthresh=0.05,outputdir='.',libSize=c()) {


        ## Error handling
        if (length(unique(group))!=2){
                print("Number of conditions identified in experiment does not equal 2")
                q()
        }

        #The workhorse  
        require(edgeR)
        ng = nrow(Count_Matrix)
        mr<-colSums(Count_Matrix)/1e6
        gt1rpin3 <- rowSums(Count_Matrix/mr > 1) >=3
        lo<-colSums(Count_Matrix[!gt1rpin3,])
        Count_Matrix<-Count_Matrix[gt1rpin3,]
        print(paste("## count matrix low count = ",lo)) 

        ## Setup DGEList object
        DGEList <- DGEList(counts=Count_Matrix, group = group)

        #Extract T v C names
        TName=unique(group)[1]
        CName=unique(group)[2]
        print(paste('prior.n =',priorn))
        # Outfile name - we need something more predictable than   
        # outfile <- paste(Out_Dir,"/",TName,"_Vs_",CName, sep="")
        # since it needs to be renamed and squirted into the history so added as a paramter
        # a simple filter! DGEList <- DGEList[rowSums(d$counts) >= 5,]
        # Filter all tags that have less than one read per million in half + 1 or more libraries. n = ceiling(length(colnames(DGEList))/2)+1
        n = ceiling(length(colnames(DGEList))/2)+1
        #DGEList <- DGEList[rowSums(1e+06 * DGEList$counts/expandAsMatrix(DGEList$samples$lib.size, dim(DGEList)) > 1) >= n, ]
        nng = nrow(DGEList)
        delta = ng - nng
        print(paste("## rgDGE Filtered ",delta," of ",ng," rows as having fewer than 3 col counts > 1",sep='' ))
        DGEList = calcNormFactors(DGEList)
        DGEList = estimateCommonDisp(DGEList)
        print(paste('Common Dispersion =',sqrt(DGEList$common.dispersion)))
        DGEList = estimateTagwiseDisp(DGEList,prior.n=priorn, trend="movingave", grid.length=1000)
        DE = exactTest(DGEList,dispersion='tagwise')
        normData <- (1e+06 * DGEList$counts/expandAsMatrix(DGEList$samples$lib.size, dim(DGEList)))
        colnames(normData) <- paste( "norm",colnames(normData),sep="_")
        #Prepare our output file
        output <- cbind( 
                Name=as.character(rownames(DGEList$counts)),
                DE$table,
                adj.p.value=p.adjust(DE$table$p.value, method=fdrtype),
                Dispersion=DGEList$tagwise.dispersion,normData,
                DGEList$counts
        )
        soutput = output[order(output$p.val),] # sorted into p value order - for quick toptable
        #Write output
        write.table(soutput,outputfilename, quote=FALSE, sep="\t",row.names=F)
        print("## Top tags")
        print(topTags(DE,n=20))
        ## Plot MAplot
        deTags = rownames(output[output$adj.p.value < fdrthresh,])
        nsig = length(deTags)
        print(paste('##',nsig,'tags significant at adj p=',fdrthresh))
        print('## deTags')
        print(head(deTags))
        pdf(paste(outputdir,"Smearplot.pdf",sep='/'))
        plotSmear(DGEList,de.tags=deTags,main=paste("Smear Plot for ",TName,' Vs ',CName,' (FDR@',fdrthresh,' N = ',nsig,')',sep=''))
        grid(col="blue")
        dev.off()

        ## Plot MDS
        sample_colors <-  ifelse (DGEList$samples$group==group[1], 1, 2)
        pdf(paste(outputdir,"MDSplot.pdf",sep='/'))
        plotMDS.DGEList(DGEList,main=paste("MDS Plot for",TName,'Vs',CName),cex=0.5,col=sample_colors,pch=sample_colors)
        legend(x="topleft", legend = c(group[1],group[length(group)]),col=c(1,2), pch=19)
        grid(col="blue")
        dev.off()
        if (FALSE==TRUE) { 
        # need a design matrix and glm to use this
	glmfit <- glmFit(DGEList, design) 
        goodness <- gof(glmfit, pcutoff=fdrpval)
        sum(goodness$outlier)
        rownames(d)[goodness$outlier]
        z <- limma::zscoreGamma(goodness$gof.statistic, shape=goodness$df/2, scale=2)
        pdf(paste(outputdir,"GoodnessofFit.pdf",sep='/'))
        qq <- qqnorm(z, panel.first=grid(), main="tagwise dispersion")
        abline(0,1,lwd=3)
        points(qq$x[goodness$outlier],qq$y[goodness$outlier], pch=16, col="dodgerblue")
	dev.off()
        }
        if (nsig > 10) {
            ## plot heatmap using subsample if large number of DGE
            hmap(normData,DE,nmeans=4,outpdfname=paste(outputdir,"heatMap.pdf",sep='/'),nsamp=250,fdrthresh=fdrthresh,TName=TName,group=group)
            }
        #Return our main table
        output 
  
}       #Done

#### MAIN ####

parameters <- commandArgs(trailingOnly=T)

## Error handling
if (length(parameters) < 6){
  print("Not enough Input files supplied. Specify at least two input files.", quote=F)
  print("", quote=F)
  usage()
}

Out_Dir         <- as.character(parameters[1])
Input           <- as.character(parameters[2])
TreatmentName   <- as.character(parameters[3])
TreatmentCols   <- as.character(parameters[4])
ControlName     <- as.character(parameters[5])
ControlCols     <- as.character(parameters[6])
outputfilename  <- as.character(parameters[7])
fdrtype  <- as.character(parameters[8])
priorn  <- as.integer(parameters[9])
fdrthresh = as.numeric(parameters[10])


#Set our columns 
TCols           = as.numeric(strsplit(TreatmentCols,",")[[1]])-1 #+1
CCols           = as.numeric(strsplit(ControlCols,",")[[1]])-1 #+1
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
if (priorn <= 0) {priorn <- ceiling(20/(length(group)-1))} # estimate prior.n if not provided
# see http://comments.gmane.org/gmane.comp.lang.r.sequencing/2009 
results <- edgeIt(Count_Matrix,group,outputfilename,fdrtype,priorn,fdrthresh,Out_Dir) #Run the main function
# for the log
sessionInfo()

"""

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))
    
class edgeR:
    """class is a wrapper for edgeR - note hard coded script above so it's all in one place for Galaxy"""

    def __init__(self,myName=None,opts=None):
        """
        Rscript edgeR.R results HGHN_mRNA_counts.txt HiGly 2,3 Control 1,4
Out_Dir         <- as.character(parameters[1])
Input           <- as.character(parameters[2])
TreatmentName   <- as.character(parameters[3])
TreatmentCols   <- as.character(parameters[4])
ControlName     <- as.character(parameters[5])
ControlCols     <- as.character(parameters[6])
outputfilename  <- as.character(parameters[7])
 FDR method (fdr/BH/holm/hochberg/hommel/bonferroni/BY/none
        """
        self.thumbformat = 'jpg'
        self.tlog = os.path.join(opts.output_dir,"edgeR_runner.log")
        self.opts = opts
        self.myName=myName
        warn = []
        if not os.path.exists(opts.output_dir):
            os.makedirs(opts.output_dir)
            warn.append('##Info: created %s' % opts.output_dir)             
        artifactpath = os.path.join(opts.output_dir,'edgeR.R') 
        artifact = open(artifactpath,'w')
        artifact.write(edgeRSCRIPT)
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
        a("%s" % opts.priorn)        
        a("%s" % opts.fdrthresh)        
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

    def runedgeR(self):
        """
        """
        sto = open(self.tlog,'w')
        p = subprocess.Popen(' '.join(self.cl),shell=True,stdout=sto,stderr=sto,stdin=subprocess.PIPE,cwd=self.opts.output_dir)
        p.stdin.write(edgeRSCRIPT)
        p.stdin.close()
        #p.communicate(edgeRSCRIPT)
        retval = p.wait()
        sto.close()
        flist = os.listdir(self.opts.output_dir)
        flist.sort()
        html = [galhtmlprefix % progname,]
        html.append('<h2>Galaxy DGE outputs run at %s with FDR threshold=%s</h2></br>Click on the images below to download as PDF</br>\n' % (timenow(),self.opts.fdrthresh))
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
        "$html_file" --output_dir "$html_file.files_path" --method "edgeR"  --fdrtype "$fdrtype" --priorn "$priorn" --fdrthresh "$fdrthresh"
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
    a('--priorn',default='5')
    a('--method',default='edgeR')
    a('--fdrtype',default='fdr') #  fdr/BH/holm/hochberg/hommel/bonferroni/BY/none
    a('--fdrthresh',default='0.05')
    opts, args = op.parse_args()
    assert opts.input_matrix and opts.output_html,u
    assert os.path.isfile(opts.input_matrix),'## DGE runner unable to open supplied input file %s' % opts.input_matrix
    assert opts.treatcols,'## DGE runner requires a comma separated list of treatment columns eg --treatcols 4,5,6'
    assert opts.treatcols,'## DGE runner requires a comma separated list of control columns eg --ctlcols 2,3,7'
    myName=os.path.split(sys.argv[0])[-1]
    m = DGE(myName, opts=opts)
    retcode = m.runedgeR()
    if retcode:
        sys.exit(retcode) # indicate failure to job runner
 
 
 
if __name__ == "__main__":
    main()




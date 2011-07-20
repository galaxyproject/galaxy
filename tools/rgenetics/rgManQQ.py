#!/usr/local/bin/python
# updated july 20 to fix sort order - R unique() sorts into strict collating order
# so need to sort after unique to revert to lexicographic order for x axis on Manhattan
# rgmanqq updated july 19 to deal with x,y and mt
# lots of fixes
# ross lazarus
import sys,math,shutil,subprocess,os,time,tempfile,string
from os.path import abspath
from rgutils import timenow, RRun, galhtmlprefix, galhtmlpostfix, galhtmlattr
progname = os.path.split(sys.argv[0])[1]
myversion = 'V000.1 March 2010'
verbose = False
debug = False

rcode="""
# license not stated so I'm assuming LGPL is ok for my derived work?
# generalised so 3 core fields passed as parameters ross lazarus March 24 2010 for rgenetics
# Originally created as qqman with the following 
# attribution:
#--------------
# Stephen Turner
# http://StephenTurner.us/
# http://GettingGeneticsDone.blogspot.com/

# Last updated: 19 July 2011 by Ross Lazarus
# R code for making manhattan plots and QQ plots from plink output files. 
# With GWAS data this can take a lot of memory. Recommended for use on 
# 64bit machines only, for now. 

#

library(ggplot2)

coloursTouse = c('firebrick','darkblue','goldenrod','darkgreen')
# not too ugly but need a colour expert please...


DrawManhattan = function(pvals=Null,chrom=Null,offset=Null,title=NULL, max.y="max",suggestiveline=0, genomewide=T, size.x.labels=9, 
              size.y.labels=10, annotate=F, SNPlist=NULL,grey=0) {
        if (annotate & is.null(SNPlist)) stop("You requested annotation but provided no SNPlist!")
        genomewideline=NULL # was genomewideline=-log10(5e-8)
        if (genomewide) { # use bonferroni since might be only a small region?
            genomewideline = -log10(0.05/length(pvals)) }
        offset = as.integer(offset)
        pvals = as.double(pvals)
        chro = as.integer(chrom) # already dealt with X and friends?
        d=data.frame(CHR=chro,BP=offset,P=pvals)
        #limit to only chrs 1-22, x=23,y=24,Mt=25?
        d=d[d$CHR %in% 1:25, ]
        if ("CHR" %in% names(d) & "BP" %in% names(d) & "P" %in% names(d) ) {
                #d=na.omit(d)
                d=d[d$P>0 & d$P<=1, ]
                d$logp = as.double(-log10(d$P))
                d$pos=NA
                ticks=NULL
                lastbase=0
                chrlist = unique(d$CHR)
                chrlist = sort(chrlist) # returns lexical ordering 
                nchr = length(chrlist) # may be any number?
                if (nchr >= 2) {
                for (x in c(1:nchr)) {
                        i = chrlist[x] # need the chrom number - may not == index
                        if (x == 1) { # first time
                                d[d$CHR==i, ]$pos=d[d$CHR==i, ]$BP
                                tks = d[d$CHR==i, ]$pos[floor(length(d[d$CHR==i, ]$pos)/2)+1]
                        }       else {
                                lastchr = chrlist[x-1] # previous whatever the list
                                lastbase=lastbase+tail(subset(d,CHR==lastchr)$BP, 1)
                                d[d$CHR==i, ]$pos=d[d$CHR==i, ]$BP+lastbase
                                if (sum(is.na(lastchr),is.na(lastbase),is.na(d[d$CHR==i, ]$pos))) { 
                                   cat(paste('manhattan: For',title,'chrlistx=',i,'lastchr=',lastchr,'lastbase=',lastbase,'pos=',d[d$CHR==i,]$pos))
                                }   
                                tks=c(tks, d[d$CHR==i, ]$pos[floor(length(d[d$CHR==i, ]$pos)/2)+1])

                        }
                    ticklim=c(min(d$pos),max(d$pos))
                    xlabs = chrlist
                    }
                } else { # nchr is 1
                   nticks = 10
                   last = max(offset)
                   first = min(offset)
                   tks = c()
                   t = (last-first)/nticks # units per tick
                   for (x in c(1:nticks)) tks = c(tks,round(x*t))
                   xlabs = tks
                   ticklim = c(first,last)
                } # else
                if (grey) {mycols=rep(c("gray10","gray60"),max(d$CHR))
                           } else {
                           mycols=rep(coloursTouse,max(d$CHR))
                           }

                if (max.y=="max") maxy=ceiling(max(d$logp)) else maxy=max.y
                maxy = max(maxy,1.1*genomewideline)
                if (annotate) d.annotate=d[as.numeric(substr(d$SNP,3,100)) %in% SNPlist, ]
                if (nchr >= 2) {
                        manplot=qplot(pos,logp,data=d, ylab=expression(-log[10](italic(p))) , colour=factor(CHR))
                        manplot=manplot+scale_x_continuous(name="Chromosome", breaks=tks, labels=xlabs) }
                else {
                        manplot=qplot(BP,logp,data=d, ylab=expression(-log[10](italic(p))) , colour=factor(CHR))
                        manplot=manplot+scale_x_continuous("BP") }                 
                manplot=manplot+scale_y_continuous(limits=c(0,maxy), breaks=1:maxy, labels=1:maxy)
                manplot=manplot+scale_colour_manual(value=mycols)
                if (annotate) {  manplot=manplot + geom_point(data=d.annotate, colour=I("green3")) } 
                manplot=manplot + opts(legend.position = "none") 
                manplot=manplot + opts(title=title)
                manplot=manplot+opts(
                        panel.background=theme_blank(), 
                        axis.text.x=theme_text(size=size.x.labels, colour="grey50"), 
                        axis.text.y=theme_text(size=size.y.labels, colour="grey50"), 
                        axis.ticks=theme_segment(colour=NA)
                )
                if (suggestiveline) manplot=manplot+geom_hline(yintercept=suggestiveline,colour="blue", alpha=I(1/3))
                if (genomewideline) manplot=manplot+geom_hline(yintercept=genomewideline,colour="red")
                manplot
        }       else {
                stop("Make sure your data frame contains columns CHR, BP, and P")
        }
}



qq = function(pvector, title=NULL, spartan=F) {
        # Thanks to Daniel Shriner at NHGRI for providing this code for creating expected and observed values
        o = -log10(sort(pvector,decreasing=F))
        e = -log10( 1:length(o)/length(o) )
        # you could use base graphics
        # plot(e,o,pch=19,cex=0.25, xlab=expression(Expected~~-log[10](italic(p))), 
        # ylab=expression(Observed~~-log[10](italic(p))), xlim=c(0,max(e)), ylim=c(0,max(e)))
        # lines(e,e,col="red")
        #You'll need ggplot2 installed to do the rest
        qq=qplot(e,o, xlim=c(0,max(e)), ylim=c(0,max(o))) + stat_abline(intercept=0,slope=1, col="red")
        qq=qq+opts(title=title)
        qq=qq+scale_x_continuous(name=expression(Expected~~-log[10](italic(p))))
        qq=qq+scale_y_continuous(name=expression(Observed~~-log[10](italic(p))))
        if (spartan) plot=plot+opts(panel.background=theme_rect(col="grey50"), panel.grid.minor=theme_blank())
        qq
}

"""

# we need another string to avoid confusion over string substitutions with %in%
# instantiate rcode2 string with infile,chromcol,offsetcol,pvalscols,title before saving and running

rcode2 = """rgqqMan = function(infile="%s",chromcolumn=%d, offsetcolumn=%d, pvalscolumns=c(%s), 
title="%s",grey=%d) {
rawd = read.table(infile,head=T,sep='\\t')
dn = names(rawd)
cc = dn[chromcolumn]
oc = dn[offsetcolumn] 
rawd[,cc] = sub('chr','',rawd[,cc],ignore.case = T) # just in case
rawd[,cc] = sub(':','',rawd[,cc],ignore.case = T) # ugh
rawd[,cc] = sub('X',23,rawd[,cc],ignore.case = T)
rawd[,cc] = sub('Y',24,rawd[,cc],ignore.case = T)
rawd[,cc] = sub('Mt',25,rawd[,cc], ignore.case = T)
nams = c(cc,oc) # for sorting
plen = length(rawd[,1])
print(paste('###',plen,'values read from',infile,'read - now running plots',sep=' '))
rawd = rawd[do.call(order,rawd[nams]),]
# mmmf - suggested by http://onertipaday.blogspot.com/2007/08/sortingordering-dataframe-according.html
# in case not yet ordered
if (plen > 0) {
  for (pvalscolumn in pvalscolumns) {
  if (pvalscolumn > 0) 
     {
     cname = names(rawd)[pvalscolumn]
     mytitle = paste('p=',cname,', ',title,sep='')
     myfname = chartr(' ','_',cname)
     myqqplot = qq(rawd[,pvalscolumn],title=mytitle)
     ggsave(filename=paste(myfname,"qqplot.png",sep='_'),myqqplot,width=6,height=4,dpi=100)
     print(paste('## qqplot on',cname,'done'))
     if ((chromcolumn > 0) & (offsetcolumn > 0)) {
         print(paste('## manhattan on',cname,'starting',chromcolumn,offsetcolumn,pvalscolumn))
         mymanplot= DrawManhattan(chrom=rawd[,chromcolumn],offset=rawd[,offsetcolumn],pvals=rawd[,pvalscolumn],title=mytitle,grey=grey)
         print(paste('## manhattan plot on',cname,'done'))
         ggsave(filename=paste(myfname,"manhattan.png",sep='_'),mymanplot,width=6,height=4,dpi=100)
         }
         else {
              print(paste('chrom column =',chromcolumn,'offset column = ',offsetcolumn,
              'so no Manhattan plot - supply both chromosome and offset as numerics for Manhattan plots if required'))
              } 
     } 
  else {
        print(paste('pvalue column =',pvalscolumn,'Cannot parse it so no plots possible'))
      }
  } # for pvalscolumn
 } else { print('## Problem - no values available to plot - was there really a chromosome and offset column?') }
}

rgqqMan() 
# execute with defaults as substituted
"""


def doManQQ(input_fname,chrom_col,offset_col,pval_cols,title,grey,ctitle,outdir,beTidy=False):
    """ 
    we may have an interval file or a tabular file - if interval, will have chr1... so need to adjust
    to chrom numbers
    draw a qq for pvals and a manhattan plot if chrom/offset <> 0
    contains some R scripts as text strings - we substitute defaults into the calls
    to make them do our bidding - and save the resulting code for posterity
    this can be called externally, I guess...for QC eg?
    """
    if debug:
        print 'doManQQ',input_fname,chrom_col,offset_col,pval_cols,title,grey,ctitle,outdir
    rcmd = '%s%s' % (rcode,rcode2 % (input_fname,chrom_col,offset_col,pval_cols,title,grey))
    if debug:
        print 'running\n%s\n' % rcmd
    rlog,flist = RRun(rcmd=rcmd,title=ctitle,outdir=outdir)
    rlog.append('## R script=')
    rlog.append(rcmd)
    return rlog,flist
  

def main():
    u = """<command interpreter="python">
        rgManQQ.py '$input_file' "$name" '$out_html' '$out_html.files_path' '$chrom_col' '$offset_col' '$pval_col'
    </command>
    """
    npar = 8
    if len(sys.argv) < npar:
            print >> sys.stdout, '## error - too few command line parameters - wanting %d' % npar
            print >> sys.stdout, u
            sys.exit(1)
    input_fname = sys.argv[1]
    title = sys.argv[2]
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    ctitle = title.translate(trantab)
    outhtml = sys.argv[3]
    outdir = sys.argv[4]
    try:
         chrom_col = int(sys.argv[5])
    except:
         chrom_col = -1
    try:
        offset_col = int(sys.argv[6])
    except:
        offset_col = -1
    p = sys.argv[7].strip().split(',')
    try:
        q = [int(x) for x in p]
    except:
        p = -1
    if chrom_col == -1 or offset_col == -1: # was passed as zero - do not do manhattan plots
        chrom_col = -1
        offset_col = -1
    grey = 0
    if (sys.argv[8].lower() in ['1','true']):
       grey = 1
    if p == -1:
        print >> sys.stderr,'## Cannot run rgManQQ - missing pval column'
        sys.exit(1)
    p = ['%d' % (int(x) + 1) for x in p]
    rlog,flist = doManQQ(input_fname,chrom_col+1,offset_col+1,','.join(p),title,grey,ctitle,outdir)
    flist.sort()
    html = [galhtmlprefix % progname,]
    html.append('<h1>%s</h1>' % title)
    if len(flist) > 0:
        html.append('<table>\n')
        for row in flist:
            fname,expl = row # RRun returns pairs of filenames fiddled for the log and R script
            e = os.path.splitext(fname)[-1]
            if e in ['.png','.jpg']:
               s= '<tr><td><a href="%s"><img src="%s" title="%s hspace="10" width="400"><br>(Click to download image %s)</a></td></tr>' \
                 % (fname,fname,expl,expl )
               html.append(s)
            else:
               html.append('<tr><td><a href="%s">%s</a></td></tr>' % (fname,expl))
        html.append('</table>\n')
    else:
        html.append('<h2>### Error - R returned no files - please confirm that parameters are sane</h1>')    
    html.append('<h3>R log follows below</h3><hr><pre>\n')
    html += rlog
    html.append('</pre>\n')   
    html.append(galhtmlattr % (progname,timenow()))
    html.append(galhtmlpostfix)
    htmlf = file(outhtml,'w')
    htmlf.write('\n'.join(html))
    htmlf.write('\n')
    htmlf.close()
    
  

if __name__ == "__main__":
    main()



"""
oct 2009 - multiple output files 
Dear Matthias,

Yes, you can define number of outputs dynamically in Galaxy. For doing
this, you'll have to declare one output dataset in your xml and pass
its ID ($out_file.id) to your python script. Also, set
force_history_refresh="True" in your tool tag in xml, like this:
<tool id="split1" name="Split" force_history_refresh="True">
In your script, if your outputs are named in the following format,
primary_associatedWithDatasetID_designation_visibility_extension
(_DBKEY), all your datasets will show up in the history pane.
associatedWithDatasetID is the $out_file.ID passed from xml,
designation will be a unique identifier for each output (set in your
script),
visibility can be set to visible if you want the dataset visible in
your history, or notvisible otherwise
extension is the required format for your dataset (bed, tabular, fasta
etc)
DBKEY is optional, and can be set if required (e.g. hg18, mm9 etc)

One of our tools "MAF to Interval converter" (tools/maf/
maf_to_interval.xml) already uses this feature. You can use it as a
reference.

qq.chisq Quantile-quantile plot for chi-squared tests
Description
This function plots ranked observed chi-squared test statistics against the corresponding expected
order statistics. It also estimates an inflation (or deflation) factor, lambda, by the ratio of the trimmed
means of observed and expected values. This is useful for inspecting the results of whole-genome
association studies for overdispersion due to population substructure and other sources of bias or
confounding.
Usage
qq.chisq(x, df=1, x.max, main="QQ plot",
sub=paste("Expected distribution: chi-squared (",df," df)", sep=""),
xlab="Expected", ylab="Observed",
conc=c(0.025, 0.975), overdisp=FALSE, trim=0.5,
slope.one=FALSE, slope.lambda=FALSE,
thin=c(0.25,50), oor.pch=24, col.shade="gray", ...)
Arguments
x A vector of observed chi-squared test values
df The degreees of freedom for the tests
x.max If present, truncate the observed value (Y) axis here
main The main heading
sub The subheading
xlab x-axis label (default "Expected")
ylab y-axis label (default "Observed")
conc Lower and upper probability bounds for concentration band for the plot. Set this
to NA to suppress this
overdisp If TRUE, an overdispersion factor, lambda, will be estimated and used in calculating
concentration band
trim Quantile point for trimmed mean calculations for estimation of lambda. Default
is to trim at the median
slope.one Is a line of slope one to be superimpsed?
slope.lambda Is a line of slope lambda to be superimposed?
thin A pair of numbers indicating how points will be thinned before plotting (see
Details). If NA, no thinning will be carried out
oor.pch Observed values greater than x.max are plotted at x.max. This argument sets
the plotting symbol to be used for out-of-range observations
col.shade The colour with which the concentration band will be filled
... Further graphical parameter settings to be passed to points()

Details
To reduce plotting time and the size of plot files, the smallest observed and expected points are
thinned so that only a reduced number of (approximately equally spaced) points are plotted. The
precise behaviour is controlled by the parameter thin, whose value should be a pair of numbers.
The first number must lie between 0 and 1 and sets the proportion of the X axis over which thinning
is to be applied. The second number should be an integer and sets the maximum number of points
to be plotted in this section.
The "concentration band" for the plot is shown in grey. This region is defined by upper and lower
probability bounds for each order statistic. The default is to use the 2.5 Note that this is not a
simultaneous confidence region; the probability that the plot will stray outside the band at some
point exceeds 95
When required, he dispersion factor is estimated by the ratio of the observed trimmed mean to its
expected value under the chi-squared assumption.
Value
The function returns the number of tests, the number of values omitted from the plot (greater than
x.max), and the estimated dispersion factor, lambda.
Note
All tests must have the same number of degrees of freedom. If this is not the case, I suggest
transforming to p-values and then plotting -2log(p) as chi-squared on 2 df.
Author(s)
David Clayton hdavid.clayton@cimr.cam.ac.uki
References
Devlin, B. and Roeder, K. (1999) Genomic control for association studies. Biometrics, 55:997-1004
"""

import sys, random, math, copy,os, subprocess, tempfile
from rgutils import RRun, rexe

rqq = """
# modified by ross lazarus for the rgenetics project may 2000
# makes a pdf for galaxy from an x vector of chisquare values
# from snpMatrix
# http://www.bioconductor.org/packages/bioc/html/snpMatrix.html
 qq.chisq <-
  function(x, df=1, x.max,
    main="QQ plot",
    sub=paste("Expected distribution: chi-squared (",df," df)", sep=""),
    xlab="Expected", ylab="Observed",
    conc=c(0.025, 0.975), overdisp=FALSE, trim=0.5,
    slope.one=T, slope.lambda=FALSE,
    thin=c(0.5,200), oor.pch=24, col.shade="gray", ofname="qqchi.pdf",
    h=6,w=6,printpdf=F,...) {

    # Function to shade concentration band

    shade <- function(x1, y1, x2, y2, color=col.shade) {
      n <- length(x2)
      polygon(c(x1, x2[n:1]), c(y1, y2[n:1]), border=NA, col=color)
    }

    # Sort values and see how many out of range

    obsvd <- sort(x, na.last=NA)
    N <- length(obsvd)
    if (missing(x.max)) {
      Np <- N
    }
    else {
      Np <- sum(obsvd<=x.max)
    }
    if(Np==0)
      stop("Nothing to plot")

    # Expected values

    if (df==2) {
      expctd <- 2*cumsum(1/(N:1))
    }
    else {
      expctd <- qchisq(p=(1:N)/(N+1), df=df)
    }

    # Concentration bands

    if (!is.null(conc)) {
      if(conc[1]>0) {
        e.low <- qchisq(p=qbeta(conc[1], 1:N, N:1), df=df)
      }
      else {
        e.low <- rep(0, N)
      }
      if (conc[2]<1) {
        e.high <- qchisq(p=qbeta(conc[2], 1:N, N:1), df=df)
      }
      else {
        e.high <- 1.1*rep(max(x),N)
      }
    }

    # Plot outline

    if (Np < N)
      top <- x.max
    else
      top <- obsvd[N]
    right <- expctd[N]
    if (printpdf) {pdf(ofname,h,w)}
    plot(c(0, right), c(0, top), type="n", xlab=xlab, ylab=ylab,
         main=main, sub=sub)

    # Thinning

    if (is.na(thin[1])) {
      show <- 1:Np
    }
    else if (length(thin)!=2 || thin[1]<0 || thin[1]>1 || thin[2]<1) {
      warning("invalid thin parameter; no thinning carried out")
      show <- 1:Np
    }
    else {
      space <- right*thin[1]/floor(thin[2])
      iat <- round((N+1)*pchisq(q=(1:floor(thin[2]))*space, df=df))
      if (max(iat)>thin[2])
        show <- unique(c(iat, (1+max(iat)):Np))
      else
        show <- 1:Np
    }
    Nu <- floor(trim*N)
    if (Nu>0)
      lambda <- mean(obsvd[1:Nu])/mean(expctd[1:Nu])
    if (!is.null(conc)) {
      if (Np<N)
        vert <- c(show, (Np+1):N)
      else
        vert <- show
      if (overdisp)
        shade(expctd[vert], lambda*e.low[vert],
              expctd[vert], lambda*e.high[vert])
      else
        shade(expctd[vert], e.low[vert], expctd[vert], e.high[vert])
    }
    points(expctd[show], obsvd[show], ...)
    # Overflow
    if (Np<N) {
      over <- (Np+1):N
      points(expctd[over], rep(x.max, N-Np), pch=oor.pch)
    }
    # Lines
    line.types <- c("solid", "dashed", "dotted")
    key <- NULL
    txt <- NULL
    if (slope.one) {
      key <- c(key, line.types[1])
      txt <- c(txt, "y = x")
      abline(a=0, b=1, lty=line.types[1])
    }
    if (slope.lambda && Nu>0) {
      key <- c(key, line.types[2])
      txt <- c(txt, paste("y = ", format(lambda, digits=4), "x", sep=""))
      if (!is.null(conc)) {
        if (Np<N)
          vert <- c(show, (Np+1):N)
        else
          vert <- show
      }
      abline(a=0, b=lambda, lty=line.types[2])
    }
    if (printpdf) {dev.off()}
    # Returned value

    if (!is.null(key))
       legend(0, top, legend=txt, lty=key)
    c(N=N, omitted=N-Np, lambda=lambda)

  }

"""


               
    
def makeQQ(dat=[], sample=1.0, maxveclen=4000, fname='fname',title='title',
           xvar='Sample',h=8,w=8,logscale=True,outdir=None):
    """
    y is data for a qq plot and ends up on the x axis go figure
    if sampling, oversample low values - all the top 1% ?
    assume we have 0-1 p values
    """
    R = []
    colour="maroon"
    nrows = len(dat)
    dat.sort() # small to large
    fn = float(nrows)
    unifx = [x/fn for x in range(1,(nrows+1))]
    if logscale:
        unifx = [-math.log10(x) for x in unifx] # uniform distribution
    if sample < 1.0 and len(dat) > maxveclen:
        # now have half a million markers eg - too many to plot all for a pdf - sample to get 10k or so points
        # oversample part of the distribution
        always = min(1000,nrows/20) # oversample smaller of lowest few hundred items or 5%
        skip = int(nrows/float(maxveclen)) # take 1 in skip to get about maxveclen points
        if skip <= 1:
            skip = 2
        samplei = [i for i in range(nrows) if (i < always) or (i % skip == 0)]
        # always oversample first sorted (here lowest) values
        yvec = [dat[i] for i in samplei] # always get first and last
        xvec = [unifx[i] for i in samplei] # and sample xvec same way
        maint='QQ %s (random %d of %d)' % (title,len(yvec),nrows)
    else:
        yvec = [x for x in dat] 
        maint='QQ %s (n=%d)' % (title,nrows)
        xvec = unifx
    if logscale:
        maint = 'Log%s' % maint
        mx = [0,math.log10(nrows)] # if 1000, becomes 3 for the null line
        ylab = '-log10(%s) Quantiles' % title
        xlab = '-log10(Uniform 0-1) Quantiles'
        yvec = [-math.log10(x) for x in yvec if x > 0.0]
    else:
        mx = [0,1]
        ylab = '%s Quantiles' % title
        xlab = 'Uniform 0-1 Quantiles'

    xv = ['%f' % x for x in xvec]
    R.append('xvec = c(%s)' % ','.join(xv))
    yv = ['%f' % x for x in yvec]
    R.append('yvec = c(%s)' % ','.join(yv))
    R.append('mx = c(0,%f)' % (math.log10(fn)))
    R.append('pdf("%s",h=%d,w=%d)' % (fname,h,w))
    R.append("par(lab=c(10,10,10))")
    R.append('qqplot(xvec,yvec,xlab="%s",ylab="%s",main="%s",sub="%s",pch=19,col="%s",cex=0.8)' % (xlab,ylab,maint,title,colour))
    R.append('points(mx,mx,type="l")')
    R.append('grid(col="lightgray",lty="dotted")')
    R.append('dev.off()')
    RRun(rcmd=R,title='makeQQplot',outdir=outdir)



def main():
    u = """
    """
    u = """<command interpreter="python">
        rgQQ.py "$input1" "$name" $sample "$cols" $allqq $height $width $logtrans $allqq.id $__new_file_path__ 
    </command>                                                                                                 

    </command>
    """
    print >> sys.stdout,'## rgQQ.py. cl=',sys.argv
    npar = 11
    if len(sys.argv) < npar:
            print >> sys.stdout, '## error - too few command line parameters - wanting %d' % npar
            print >> sys.stdout, u
            sys.exit(1)
    in_fname = sys.argv[1]
    name = sys.argv[2]
    sample = float(sys.argv[3])
    head = None
    columns = [int(x) for x in sys.argv[4].strip().split(',')] # work with python columns!
    allout = sys.argv[5]
    height = int(sys.argv[6])
    width = int(sys.argv[7])
    logscale = (sys.argv[8].lower() == 'true')
    outid = sys.argv[9] # this is used to allow multiple output files 
    outdir = sys.argv[10]
    nan_row = False
    rows = []
    for i, line in enumerate( file( sys.argv[1] ) ):
        # Skip comments
        if  line.startswith( '#' ) or ( i == 0 ):
            if i == 0:
                 head = line.strip().split("\t")
            continue
        if len(line.strip()) == 0:
            continue
        # Extract values and convert to floats
        fields = line.strip().split( "\t" )
        row = []
        nan_row = False
        for column in columns:
            if len( fields ) <= column:
                return fail( "No column %d on line %d: %s" % ( column, i, fields ) )
            val = fields[column]
            if val.lower() == "na":
                nan_row = True
            else:
                try:
                    row.append( float( fields[column] ) )
                except ValueError:
                    return fail( "Value '%s' in column %d on line %d is not numeric" % ( fields[column], column+1, i ) )
        if not nan_row:
           rows.append( row )
    if i > 1:
       i = i-1 # remove header row from count
    if head == None:
       head = ['Col%d' % (x+1) for x in columns]
    R = []
    for c,column in enumerate(columns): # we appended each column in turn
        outname = allout
        if c > 0: # after first time
            outname = 'primary_%s_col%s_visible_pdf' % (outid,column)
            outname = os.path.join(outdir,outname)
        dat = []
        nrows = len(rows) # sometimes lots of NA's!!
        for arow in rows:
           dat.append(arow[c]) # remember, we appended each col in turn!
        cname = head[column]        
        makeQQ(dat=dat,sample=sample,fname=outname,title='%s_%s' % (name,cname),
                   xvar=cname,h=height,w=width,logscale=logscale,outdir=outdir)



if __name__ == "__main__":
    main()

"""
# generate an xml galaxy descriptor skeleton for an arbitrary r function
Will always require tweaking - how to discover the output names for example?

in R, something like:
MultiSNPAssoc.batch<-function(filei, thMAF=0.05, alpha= 0.05, 
   nSubj=500, encode='7p15',  ORAAgBB=2, pre=0.5, startRep=1, endRep=10, snpDensity=0.01,race='CEU')

is the required prototype
pass the r script name and function name as params and this script will generate a galaxy xml file
ross lazarus me fecit november 2007
for the rgenetics project

A typical galaxy tool interface looks like:
<tool id="plinkCaCo1" name="CaseControl">
    <code file="listFiles.py"/> 
    <code file="plinkCaCo_code.py"/> 
  
    <description>Statistical tests</description>
  
    <command interpreter="python2.4">
        plinkCaCo.py $i $name $test $outformat $out_file1 $logf $map
    </command>
    
    <inputs>    
       <param name="i"  type="select" label="Genotype file" dynamic_options="get_lib_bedfiles()" /> 
       <param name="map"  type="select" label="Map file corresponding" dynamic_options="get_lib_mapfiles()" /> 
       <param name='name' type='text' value='CaseControl' />
       <param name="test" type="select" label="Type of statistical test" dynamic_options="get_test_opts()" />
       <param name="outformat" type="select" label="Format of file to output" dynamic_options="get_out_formats()" />
   </inputs>

   <outputs>  
       <data format="text" name="out_file1" />
       <data format="text" name="logf" parent="out_file1" />
   </outputs>
<help>
help text goes here
</help>
</tool>
"""

testR = """# cl mods by ross oct 21 2005
# params are now minf,maf,nCase,start,end,dens,simOR,prevalence
# use Byng et al.'s (2003) method to estimate the power
# Byng MC, Whittaker JC, Cuthbert AP, Mathew CG, Lewis CM (2003),
# SNP Subset Selection for Genetic Association Studies,
# Annals of Human Genetics, Vol. 67, pp. 543-556

source("power.Byng2.S")


# This code is designed to estimate statistical power assuming that
# any marker in a set of SNPs could be the disease susceptibility locus (DSL)
# but that the experimenter cannot afford to genotype all markers, so must rely on 
# LD to detect a DSL through testing a small subset of markers.
# Power for various SNP subsample densities is estimated
# as the proportion of all markers for which a sample simulated to give
# a fixed odds ratio for every marker (as the "DSL") in turn
# has a minimum P value which an investigator might naively declare significant, at various
# sample densities - this is what an investigator would do - test the subset to see if
# any tests were significant. A Bonferroni corrected threshold is written to the output file
# so the results can also be estimated for corrected alpha.
# Note: There is a python script which munges all the output files 
# This code does not do the actual power calculations - it writes .res files
# which contain the minimum p value for each replication at each sample density for
# the DSL which are specified on the command line.
# Note: multiple replications are performed for each snp subsample
# density for each "DSL" in turn (!) so this takes a long time to run
# but this is necessary because there is substantial variability between
# the "quality" of random subsets of markers to detect a DSL through linkage 
# disequilibrium. To get tight ci's around power estimates requires a very large
# number of replications - this current version is pretty skimpy.. 
# 
# code logic is something like this:
# 1. read parameters
# 2. read input file of haplotypes (these are real phased hapmap ENCODE data!)
# 3. remove all markers below the specified MAF
# 4. For dsl in firstdsl:lastdsl do
# 5.    for each sample density do
# 6.        for replication in firstrep:lastrep do
# 7a.           draw a random subset of markers (exclude DSL) of size to match sample density
# 7b.           draw case/control sample so the DSL is more common in cases
# 7c.           perform armitage test on each of the subset of markers
# 7d.           record the minimum p value for later processing
# 
# cleaned up may 25 ross 
# updated may 25 weiliang added code to estimate appropriate parameters to
# generate under a given OR and an additive genetic model
# May 11: added penetrance to output to explore the relationship between the
# way we're generating and the "right" way.
# Also added command line target OR parameter - may need penetrance too...
#
# april 12 - fdr routines and additional fdr cutoff p value added by Weiliang Qiu
# april 11 - added simOddsratio and simBaseline explicitly set to 2.0 and 0.998 usually
# April 10 - makeccbatch has been updated to invert any columns with maf > 0.5 so minor allele is
# always coded 1 because the native hapmap phased files do not follow this convention
# the updated file has .fixed appended to it's name and is used in the batch script
# updated april 9 to produce tab delimited output files 
#
# april 8 update to include DSL MAF in controls and odds ratio so we can check
# the generating process and the region so we can amalgamate all the results files
# for analysis later if needed
# april 7 update - changed .res filename to shorten
# added dsl armitage p value to .res file
# takes longer to run since we now take a fresh random sample to test each replicate 
# at each sampling density for each DSL - a boat load of cpu time. april 5 2005 ross

# modified on April 5, 2005, Weiliang Qiu
# Now we randomly generate cases and controls from chromosomes for each
# marker (SNPs)

# added outer loop and command line parameters to allow better control
# only ever 1 input file together with a range of DSL's to test
# ross lazarus april 5 for testing on the hpres.mgh.harvard.edu cluster

# Modified on April 4, 2005, Weiliang Qiu
# changed the usage of ccpower.R. Now the arguments are 'inputFile', '[thMAF]'
#   '[nSubj]', where 'thMAF' and 'nSubj' are optional.
# changed the arguments of functions 'MultiSNPAssoc.batch', 'MultiSNPAssoc',
#   and 'MultiSNPAssoc'
# cases and controls are now randomly generated with certain probabilities from
#   chromosomes.
# In function 'MultiSNPAssoc', we calculate the sampling probabilities for
#   cases and controls
# In function 'MultiSNPAssoc2', we generate cases and controls.

# Added random subsamples for each trial - need very large case/control samples to
# work with!
# Added command line argument parsing for the data file and the range of snp to process
# in preparation for parallelizing out the tasks
# It looks like p values are more variable for small marker density samples
# so I added the mean and sd of pvalues at each sampling density
# we might need to tune the number of replicated tests at each density to
# achieve a preset coefficient of variation so our power estimates are more stable?
# added marker density as a percentage as first column of output
# march 30 ross lazarus

# Modified march 29, ross lazarus
# changed sample density array into a constant defined early
# and stopped it after 0.25 since the higher densities take longer
# to run because of more tests - probably not informative since such dense
# samples of SNPs are not practicable at present.
# output filename extension changed to res
# third column of results table changed to the
# bonferroni adjusted alpha value - alpha added as
# a parameter with default 0.05

# created on March 29, 2005, Weiliang Qiu
# Reference: Hao et al. (2004). Power Estimation of Multiple SNP
# Association Test of Case-Control Study and Application.
# Genetic Epidemiology 26:22-30.


########################################################

# D -- diseased
# A -- minor allele
# B -- common allele
# ORAAgBB=OR(AA|BB)=pen(AA)/[1-pen(AA)] * [1-pen(BB)]/pen(AA)
# pen(AA)=Pr(D|AA), pen(BB)=Pr(D|BB), where D is disease
# pre -- population prevalence Pr(D)

# main program 

# INPUTS>>>>>>>>>>>>>>>>
# filei -- input filename
# ratioVec -- vector of sample densities, i.e. the ratios of markers to be 
#             selected 
# nIter -- number of replcations for each combination of sample density and
#          DSL 
# thMAF -- threshold for MAF. SNPs with MAF<thMAF will not be considered as
#          a DSL
# alpha -- significant level of a Amitage test
# nSubj -- for each generated data set, there are nSubj cases and nSubj control
# sDSL --  label of the start SNP
# eDSL --  labe of the end SNP. For each SNP (from sDSL to eDSL), we regard
#          it as a DSL and generate simulated data to test LD for this DSL, and
#          calculate the powr of the test.
# resroot -- root part of the output files
# fdrMethod -- methods to get FDR adjusted pvalues. Available methods include
#              "Hochberg", "BH", "Holm", "Sidak", "BL" 
# ORAAgBB -- Odds ratio = p1*(1-p2)/[p2*(1-p1)] where p1=Pr(D|AA), p2=Pr(D|BB)
# pre -- population prevalence=Pr(disease)
#
# OUTPUTS >>>>>>>>>>>>>>>>
#  a 'sum(nIter)' by 19 matrix (see the function 'MultiSNPAssoc2()') recording 
#    intermediate results such as minimum p-value
#    mean p-values, standard error of p-values, etc.
# 
MultiSNPAssoc.batch<-function(filei, thMAF=0.05, alpha= 0.05, 
                              nSubj=500, encode='7p15',  ORAAgBB=2, pre=0.5, startRep=1, endRep=10, snpDensity=0.01,race='CEU')
{
    # read data
    # rows are 120 chromosomes
    # columns are SNPs
    y<-read.table(filei, header=FALSE)
    message = paste('Read ',filei)
    print(message)
    # delete markers (SNPs) whose MAF<thMAF
    MAF<-apply(y, 2, mean)
    # need to reverse some markers but this is now done in makeccbatch.py     
    
    pos<-which(MAF<thMAF)
    if(length(pos)>0)
    { 
     y<-y[, -pos] 
     message = paste(length(pos),'marker(s) deleted as being below MAF',thMAF,'leaving',length(y[1,]),'snps')
     print(message)
    } 

    res<-MultiSNPAssoc(y,  startRep, endRep, snpDensity, alpha, nSubj, encode, ORAAgBB, pre, race)
#    # write results to file
#    output<-paste(resroot, ".res",sep="") # eg 7p15dsl.1.res
#    write.table(res, file=output, row.names=FALSE, col.names=TRUE,sep='\t',quote=FALSE)
#    message = paste('wrote results for dsl to ',output)
#    print(message)
#
}

# Multiple SNP Association Test
#
# INPUTS >>>>>>>>>>>
# y -- chromosome data matrix with 'nr' rows and 'nc' columns. Rows correspond
#      to chromosomes; columns correspond to markers (SNPs). y_{ij}=1 if
#      the j-th marker at i-th chromosome is rare. Otherwise y_{ij}=0
# genoMat -- a 14400 by 3 matrix of all 14400 possible genotypes 
#            by randomly mating 120 chromosomes. First two columns are the pair
#            of alleles of a genotype. (0,0)--BB, (0,1) or (1,0) -- AB, 
#            (1, 1) -- AA. The 3rd  column is the code for the 
#            genotype. The coding is additive coding. 0--BB; 1--AB; 2--AA.
# ratioVec -- vector of sample densities, i.e. the ratios of markers to be 
#             selected 
# nIter -- number of replcations for each combination of sample density and
#          DSL 
# alpha -- significant level of a Amitage test
# nSubj -- for each generated data set, there are nSubj cases and nSubj control
# dsl -- indicate which of SNP (i.e. column of the matrix y) is regarded as DSL
# encode --?? 
# fdrMethod -- methods to get FDR adjusted pvalues. Available methods include
#              "Hochberg", "BH", "Holm", "Sidak", "BL" 
# ORAAgBB=OR(AA|BB)=p1*(1-p2)/[p2*(1-p1)], where
#   p1=Pr(D|AA), p2=Pr(D|BB)
# pre -- population prevalence Pr(D)
#
# OUTPUTS >>>>>>>>>>>>>>>>
#  a 'sum(nIter)' by 5 matrix (see the function 'MultiSNPAssoc2()') recording 
#    intermediate results such as minimum p-value
#    mean p-values, standard error of p-values, etc.
# 
MultiSNPAssoc<-function(y,  startRep, endRep, snpDensity,
                        alpha=0.05, nSubj=500, encode='?', ORAAgBB=4, pre=0.5, race='CEU')
{
  # second outermost loop
  # for each marker density
  reps = endRep - startRep + 1
  fileTag = paste('OR',ORAAgBB,'rep',startRep,'to',endRep,'at',as.integer(100*snpDensity),'pc',sep='')  
  message = paste('SNP Subset ratio ',snpDensity,': ',reps,' iterations starting')
  print(message)  
  tmp<-MultiSNPAssoc2(y, snpDensity, nreps=reps, fileTag = fileTag, nSubj=nSubj, alpha = 0.05 , region=encode, 
  ORAAgBB=ORAAgBB, pre=pre, race=race)

}

MultiSNPAssoc2<-function(y, snpDensity=0.01, nreps=10, fileTag='10to20at1pc', nSubj = 500, alpha = 0.05, region='?',
 ORAAgBB=4, pre=0.15, race='CEU')
# Multiple SNP Association Test
#
# inputs>>>>>>>>>>>>>>>>
# y -- chromosome data matrix with 'nr' rows and 'nc' columns. Rows correspond
#      to chromosomes; columns correspond to markers (SNPs). y_{ij}=1 if
#      the j-th marker at i-th chromosome is rare. Otherwise y_{ij}=0
# genoMat -- a 14400 by 3 matrix of all 14400 possible genotypes 
#            by randomly mating 120 chromosomes. First two columns are the pair
#            of alleles of a genotype. (0,0)--BB, (0,1) or (1,0) -- AB, 
#            (1, 1) -- AA. The 3rd  column is the code for the 
#            genotype. The coding is additive coding. 0--BB; 1--AB; 2--AA.
# snpDensity -- we will take a subset (nc*snpDensity number of markers) of markers
# nreps -- number of replcations for the specified combination of 
#          sample density and DSL 
# nSubj -- for each generated data set, there are nSubj cases and nSubj control
# alpha -- significant level of a Amitage test
# dsl -- indicate which of SNP (i.e. column of the matrix y) is regarded as DSL
# encode --?? 
# fdrMethod -- methods to get FDR adjusted pvalues. Available methods include
#              "Hochberg", "BH", "Holm", "Sidak", "BL" 
# ORAAgBB=OR(AA|BB)=p1*(1-p2)/[p2*(1-p1)], where
#   p1=Pr(D|AA), p2=Pr(D|BB)
# pre -- population prevalence Pr(D)

# outputs>>>>>>>>>>>>>>>>
# 1st column of 'resMat' is the chosen marker density
# 2nd column of 'resMat' is number of selected markers
# 3rd is the number of replications
# 4th is the input 'gene' 
# 5th is the power
{
  # inner loop - for each marker density, do multiple replications and 
  # record min p value of each
  # for a .res file which is written by the enclosing loop
  nc<-ncol(y)
  snpsamplespace <- 1:nc # 
  isFirst = TRUE
  outfilename<-paste(region,race,fileTag,".res",sep="") 
  snpsneeded = round(nc*snpDensity) # for random subsample
  for(i in 1:nreps)
  {
    snpsubset <-sample(snpsamplespace, size=snpsneeded, replace=FALSE) # without replacement!
    # estimate power of the random set of markers 
    # by using Byng et al.'s (2003) method
    nsubjects<-2*nSubj # ncase+ncontrol
    tmp<-fun.calc.power(y, snpsubset, nsubjects, alpha)
    powers<-tmp$powers
    MAFs<-tmp$MAFs
    power<-mean(powers)
    cat("dens=",snpDensity,"nreps=", nreps, " i=", i, "nsnp=",length(snpsubset)," mean(powers)=", power, "\n")
    mm<-length(MAFs)
    res<-data.frame(markerDens=rep(snpDensity,mm), 
                    nMarker=rep(length(snpsubset),mm), 
                    totaliters=rep(nreps,mm), 
                    region=rep(region,mm),
                    OR = rep(ORAAgBB,mm), 
                    iter=rep(i,mm), 
                    SNP=1:length(MAFs),
                    MAFs=MAFs, 
                    powers=powers)
    if(isFirst==TRUE)
    { myappend<-FALSE }
    else { myappend<-TRUE }
    write.table(res, file=outfilename, row.names=FALSE, 
      col.names=isFirst,sep='\t',
      quote=FALSE, append=myappend)
    isFirst<-FALSE
    message = paste('wrote results for region =',region, " replicate=", i,
      " markerDens=", snpDensity, "\n")
    print(message)

  }
}

# n -- n/2 cases and n/2 controls
fun.calc.power<-function(y, snpsubset, n, alpha=0.05)
{
  # transform 'y' to the format used in power.Byng
  y<-as.matrix(y)
  data<-fun.transform(y)

  # calculate power
  powers<-power.Byng2(snpsubset, n, data, alpha)
  return(list(powers=powers, MAFs=data$MAFs))
}

fun.transform<-function(y, K = 0.15, ORAAgBB = 4, mode = "ADD")
{
  # total number of SNPs
  n.SNPs<-ncol(y)
 
  geno.data<-collapse(y, with.freqs=FALSE)
  #cat("dim(geno.data)=",dim(geno.data), " length(geno.data)=", length(geno.data),"\n")
  #cat("n.SNPs=", n.SNPs, "\n")
  #cat("is.matrix(geno.data)=", is.matrix(geno.data), "\n")
  #cat("geno.data[1:2,]>>\n"); print(geno.data[1:2,]); cat("\n");

  ## Calculate MAFs
  MAFs <- as.vector((geno.data[,n.SNPs+1] %*% geno.data[,-(n.SNPs+1)])
            / (2*sum(geno.data[,n.SNPs+1])))

  ## Calculate the penetrances 
  #penetrances <- calc.pentrance(K, R, mode, MAFs)[[1]]
  penetrances <- calc.pentrance2(K, ORAAgBB, mode, MAFs)[[1]]
  
  if (any(penetrances > 1)) 
  {
        print("Problem with disease model. Some penetrances are > 1:")
        print(penetrances)
        stop("Execution aborted")
  }
  
  invisible(list(n.SNPs = n.SNPs,
    geno.data = geno.data,
    penetrances = penetrances,
    MAFs = MAFs,
    K = K, ORAAgBB = ORAAgBB, mode = mode,
    method = "Byng", ## Finally, all the other input parameters:
    datafile = NULL, type = "gen", header.size = 4,
    id.genotypes = TRUE, to.retain = 80))
}




# default values for parameters of 'MultiSNPAssoc.batch'
# 'alpha' -- significant level of a Amitage test
alpha = 0.05
# 'penetrances' -- c(Pr(D|BB), Pr(D|AB), Pr(D|AA))
penetrances = c(0.05,0.2,0.8) # gamma = 4

snpDensity = c(0.01)

startRep = 0 # more iterations at lower sample density
endRep = 10

# this is a fudge - should probably be tuned to provide an acceptable cv for the p values?
# ORAAgBB -- Odds ratio = p1*(1-p2)/[p2*(1-p1)] where p1=Pr(D|AA), p2=Pr(D|BB)
ORAAgBB = 2.0 
# pre -- population prevalence=Pr(disease)
pre<-0.15

# this can be set to 1.0 for testing under the null
# it does reject about alpha so I think it all works
simBaseline = 0.001/(1-0.001) # a small number to represent rare allele excess in controls


# 'commandArgs()' Provides access to a copy of the command line arguments supplied
#     when this R session was invoked.
ca = commandArgs()
nargs = length(ca)

if(nargs<11 || nargs>12) { # print out error message
  print("Error! Insufficient or too many CL arguments in\n")
  print(ca)
  print("Usage: R --vanilla --slave --args inputFile thMAF nSubj ORAAgBB startrep endrep snpdens [pre] < ccpower_ORAA_Byng2.R [> outpu)
  print("inputFile -- input file name\n")
  print("thMAF -- threshold for minor allele frequency.\n")
  print("nSubj -- number of subjects for one group. Two groups have equal number.\n")
  print("simulation OR(AA|BB) (Optional - default = 4.0)\n")
  print("simstart -- number of first replication for output file name .\n")
  print("simend -- last replication number \n")
  print("snpdensity - proportion of random snps to test \n")
  print("disease population prevalence (Optional - default to 0.5)\n")
  print("proportion of nSubj subjects that are cases (Optional - default to 0.5)\n")
  print("outputfile -- the name of the output file record intermediate outputs\n")
  #stop("Program terminated!\n")

} else {
  # the first 4 arguments are: 1) 'R'; 2) '--vanilla'; 3) '--slave'; 4) '--args'
  firstarg = 5
  files<-ca[firstarg]
  #fileroot = ca[firstarg+1]
  print(paste('got ',files))
  thMAF<- as.numeric(ca[6]) 
  nSubj<- as.integer(ca[7])
  startRep = as.integer(ca[8])
  endRep = as.integer(ca[9])
  snpDensity = as.numeric(ca[10])
  ORAAgBB = as.numeric(ca[11])

  if (nargs > 11) {
        pre = as.numeric(ca[12])
  }
  ss =  strsplit(files,'\\.') # break up into segments - the second one contains the chromosomal band
  s = unlist(ss) # extract the 8q23 or whatever from genotypes_ENr213.18q12.1_CEU_.phased
  encodeRegion = s[2] # eg 18q12
  rr = strsplit(s[3],'_')
  race = unlist(rr)[2]
  print(cat('race=',race))
  mytime<-unix.time(MultiSNPAssoc.batch(filei=files, thMAF=thMAF, alpha=alpha, nSubj=nSubj, encode=encodeRegion,
     ORAAgBB=ORAAgBB, pre=pre, startRep=startRep, endRep=endRep, snpDensity=snpDensity, race=race))
  warnings()
  cat("mytime>>\n"); print(mytime); cat("\n");
}
""".split('\n')


def iterRfuncs(rscript=[],func="foo"):
    """ generator yielding each function definition
    and their parameters with defaults if set from an R script as a list of lines
    """
    funcname = None
    funcparams = None
    inparams = 0
    infunc = 0
    for line in rscript:
        line = line.strip().replace(' ','')
        if len(line) > 0:
            if line[0] <> '#':
                if infunc:
                    lsp = line.split('{') # start of code after function def
                    if len(lsp) > 1:
                        params = '%s%s' % (params,lsp[0])
                        inparams = 0
                    else:
                        params = "%s%s" % (params,line.strip())
                else:            
                    lse = line.split('=function(')
                    lsa = line.split('<-function(')
                    if len(lse) > 1:
                        funcname,params = lse
                    elif len(lsa) > 1:
                        funcname,params = lsa
                    if funcname:
                        infunc = 1
                        inparams = 1
                        lsp = params.split('{') # start of code after function def
                        if len(lsp) > 1:
                            params = lsp[0]
                            inparams = 0
                if funcname and not inparams: # new func and params found
                    if params[-1] == ')':
                        params = params[:-1]
                    params = params.split(',')
                    dictp = {}
                    for p in params:
                        ps = p.split('=')
                        if len(ps) > 1: # has a default?
                            k,v = ps
                            if v.find('.') <> -1: # try float?
                                try:
                                    v = float(v)
                                except:
                                    pass
                            else:
                                try:
                                    v = int(v)
                                except:
                                    v = v.replace('"','')
                                    v = v.replace("'",'') # get rid of spurious r quotes
                            dictp[k] = v # this will be a string unless float or int seems better
                        else:
                            k = p
                            dictp[k] = None
                    yield funcname,dictp
                    inparams = 0
                    infunc = 0
                    funcname = None
                    funcparams = None

def genParams(params = {}):
    """ returns a list of strings for the parameters segment of a Galaxy XML tool interface
    descriptor
    """
    pseg = []
    for p in params:
        s = ["<inputs>\n<param name='%s' label='%s' " % (p,p),]
        if params[p] <> None: # has a value
            pdef = params[p]
            pval = str(pdef)
        else:
            pdef = None
            ptype = ' ' # make it a string
            pval = ' '
        ptype = type(pdef)
        if ptype == type(' '):
            s.append("type='text' size='80'")
        elif ptype == type(1):
            s.append("type='int'")
        elif ptype == type(1.1):
            s.append("type='float'")
        if pval <> ' ':
            s.append("value='%s'" % pval)
        s.append('/>')            
        pseg.append(' '.join(s))
    pseg.append('</inputs>')
    return pseg

def testRscript(s=testR):
    """
    listf = file(rscript,'r').readlines() # so we can find the function
    """
    for func,params in iterRfuncs(rscript=testR):
        print 'func=%s:\nparams=%s\nparamseg=%s' % (func,params,genParams(params))


if __name__ == "__main__":
    testRscript()
#!/usr/local/bin/python
"""
# added most of the available options for linear models
# june 2009 rml
# hack to run and process a plink quantitative trait
#

This is a wrapper for Shaun Purcell's Plink linear/logistic models for
traits, covariates and genotypes.

It requires some judgement to interpret the findings
We need some better visualizations - manhattan plots are good.
svg with rs numbers for top 1%?

toptable tools - truncate a gg file down to some low percentile

intersect with other tables - eg gene expression regressions on snps



"""

import sys,math,shutil,subprocess,os,string,tempfile,shutil,commands
from rgutils import plinke

def makeGFF(resf='',outfname='',logf=None,twd='.',name='track name',description='track description',topn=1000):
    """
    score must be scaled to 0-1000
    
    Want to make some wig tracks from each analysis
    Best n -log10(p). Make top hit the window.
    we use our tab output which has
    rs	chrom	offset	ADD_stat	ADD_p	ADD_log10p
    rs3094315	1	792429	1.151	0.2528	0.597223

    """

    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False
    header = 'track name=%s description="%s" visibility=2 useScore=1 color=0,60,120\n' % (name,description)          
    column_names = [ 'Seqname', 'Source', 'Feature', 'Start', 'End', 'Score', 'Strand', 'Frame', 'Group' ]
    halfwidth=100
    resfpath = os.path.join(twd,resf)
    resf = open(resfpath,'r')
    resfl = resf.readlines() # dumb but convenient for millions of rows
    resfl = [x.split() for x in resfl]
    headl = resfl[0]
    resfl = resfl[1:]
    headl = [x.strip().upper() for x in headl]
    headIndex = dict(zip(headl,range(0,len(headl))))
    chrpos = headIndex.get('CHROM',None)
    rspos = headIndex.get('RS',None)
    offspos = headIndex.get('OFFSET',None)
    ppos = headIndex.get('ADD_LOG10P',None)
    wewant = [chrpos,rspos,offspos,ppos]
    if None in wewant: # missing something
       logf.write('### Error missing a required header in makeGFF - headIndex=%s\n' % headIndex)
       return
    resfl = [x for x in resfl if x[ppos] > '']
    resfl = [(float(x[ppos]),x) for x in resfl] # decorate
    resfl.sort()
    resfl.reverse() # using -log10 so larger is better
    resfl = resfl[:topn] # truncate
    pvals = [x[0] for x in resfl] # need to scale
    resfl = [x[1] for x in resfl] # drop decoration
    if len(pvals) == 0:
        logf.write('### no pvalues found in resfl - %s' % (resfl[:3]))
        sys.exit(1)
    maxp = max(pvals) # need to scale
    minp = min(pvals)
    prange = abs(maxp-minp) + 0.5 # fudge
    scalefact = 1000.0/prange
    logf.write('###maxp=%f,minp=%f,prange=%f,scalefact=%f\n' % (maxp,minp,prange,scalefact))
    for i,row in enumerate(resfl):
        row[ppos] = '%d' % (int(scalefact*pvals[i]))
        resfl[i] = row # replace
    outf = file(outfname,'w')
    outf.write(header)
    outres = [] # need to resort into chrom offset order
    for i,lrow in enumerate(resfl):
        chrom,snp,offset,p, = [lrow[x] for x in wewant]
        gff = ('chr%s' % chrom,'rgGLM','variation','%d' % (int(offset)-halfwidth),
               '%d' % (int(offset)+halfwidth),p,'.','.','%s logp=%1.2f' % (snp,pvals[i]))
        outres.append(gff)
    outres = [(x[0],int(x[3]),x) for x in outres] # decorate
    outres.sort() # into chrom offset
    outres=[x[2] for x in outres] # undecorate
    outres = ['\t'.join(x) for x in outres]    
    outf.write('\n'.join(outres))
    outf.write('\n')
    outf.close()



def xformQassoc(resf='',outfname='',logf=None,twd='.'):
    """	plink.assoc.linear to gg file
from the docs
The output per each SNP might look something like:

    CHR        SNP      BP  A1       TEST   NMISS       OR      STAT         P
      5   rs000001   10001   A        ADD     664   0.7806    -1.942   0.05216
      5   rs000001   10001   A     DOMDEV     664   0.9395   -0.3562    0.7217
      5   rs000001   10001   A       COV1     664   0.9723   -0.7894    0.4299
      5   rs000001   10001   A       COV2     664    1.159    0.5132    0.6078
      5   rs000001   10001   A   GENO_2DF     664       NA     5.059    0.0797   
    need to transform into gg columns for each distinct test
    or bed for tracks?
    
    """
    logf.write('xformQassoc got resf=%s, outfname=%s\n' % (resf,outfname))
    resdict = {}
    rsdict = {}
    markerlist = []
    # plink is "clever" - will run logistic if only 2 categories such as gender
    resfs = resf.split('.')
    if resfs[-1] == 'logistic':
        resfs[-1] = 'linear'
    else:
        resfs[-1] = 'logistic'
    altresf = '.'.join(resfs)

    altresfpath = os.path.join(twd,altresf)
    resfpath = os.path.join(twd,resf)
    try:
        resf = open(resfpath,'r')
    except:
        try:
            resf = open(altresfpath,'r')
        except:
            print >> sys.stderr, '## error - no file plink output %s or %s found - cannot continue' % (resfpath, altresfpath)
            sys.exit(1)
    for lnum,row in enumerate(resf):
        if lnum == 0:
            headl = row.split()
            headl = [x.strip().upper() for x in headl]
            headIndex = dict(zip(headl,range(0,len(headl))))
            chrpos = headIndex.get('CHR',None)
            rspos = headIndex.get('SNP',None)
            offspos = headIndex.get('BP',None)
            nmisspos = headIndex.get('NMISS',None)
            testpos = headIndex.get('TEST',None)
            ppos = headIndex.get('P',None)
            coeffpos = headIndex.get('OR',None)
            if not coeffpos:
                coeffpos = headIndex.get('BETA',None)
            apos = headIndex.get('A1',None)
            statpos = headIndex.get('STAT',None)
            wewant = [chrpos,rspos,offspos,testpos,statpos,ppos,coeffpos,apos]
            if None in wewant: # missing something
               logf.write('missing a required header in xformQassoc - headIndex=%s\n' % headIndex)
               return
            llen = len(headl)        
        else: # no Nones!
            ll = row.split()
            if len(ll) >= llen: # valid line
                chrom,snp,offset,test,stat,p,coeff,allele = [ll[x] for x in wewant]
                snp = snp.strip()
                if p <> 'NA' :
                  try:
                    ffp = float(p)
                    if ffp <> 0:
                       lp =  -math.log10(ffp)
                  except:
                    lp = 0.0
                  resdict.setdefault(test,{})
                  resdict[test][snp] = (stat,p,'%f' % lp)
                  if rsdict.get(snp,None) == None:
                      rsdict[snp] = (chrom,offset)
                      markerlist.append(snp)
    # now have various tests indexed by rs
    tk = resdict.keys()
    tk.sort() # tests
    ohead = ['rs','chrom','offset']
    for t in tk: # add headers
        ohead.append('%s_stat' % t)
        ohead.append('%s_p' % t)
        ohead.append('%s_log10p' % t)
    oheads = '\t'.join(ohead)
    res = [oheads,]
    for snp in markerlist: # retain original order
        chrom,offset = rsdict[snp]
        outl = [snp,chrom,offset]
        for t in tk:
            outl += resdict[t][snp] # add stat,p for this test
        outs = '\t'.join(outl)
        res.append(outs)
    f = file(outfname,'w')
    res.append('')
    f.write('\n'.join(res))
    f.close()

                
if __name__ == "__main__":
    """

    <command interpreter="python">   
        rgGLM.py '$i.extra_files_path/$i.metadata.base_name' '$phef.extra_files_path/$phef.metadata.base_name'
        "$title1" '$predvar' '$covar' '$out_file1' '$logf' '$i.metadata.base_name'
        '$inter' '$cond' '$gender' '$mind' '$geno' '$maf' '$logistic' '$wigout'
    </command>
    """
    topn = 1000
    killme = string.punctuation+string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    if len(sys.argv) < 17:
       s = 'rgGLM.py needs 17 params - got %s \n' % (sys.argv)
       sys.stderr.write(s) # print >>,s would probably also work?
       sys.exit(0)
    blurb = 'rgGLM.py called with %s' % sys.argv
    print >> sys.stdout,blurb
    bfname = sys.argv[1]
    phename = sys.argv[2]
    title = sys.argv[3]
    title.translate(trantab)
    predvar = sys.argv[4]
    covar = sys.argv[5].strip()
    outfname = sys.argv[6] 
    logfname = sys.argv[7]
    op = os.path.split(logfname)[0]
    try: # for test - needs this done
        os.makedirs(op)
    except:
        pass    
    basename = sys.argv[8].translate(trantab)
    inter = sys.argv[9] == '1'
    cond = sys.argv[10].strip()
    if cond == 'None':
        cond = ''
    gender = sys.argv[11] == '1'
    mind = sys.argv[12]
    geno = sys.argv[13]
    maf = sys.argv[14]
    logistic = sys.argv[15].strip()=='1'
    gffout = sys.argv[16]
    me = sys.argv[0]
    phepath = '%s.pphe' % phename
    twd = tempfile.mkdtemp(suffix='rgGLM') # make sure plink doesn't spew log file into the root!
    tplog = os.path.join(twd,'%s.log' % basename) # should be path to plink log
    vcl = [plinke,'--noweb','--bfile',bfname,'--pheno-name','"%s"' % predvar,'--pheno',
           phepath,'--out',basename,'--mind %s' % mind, '--geno %s' % geno,
           '--maf %s' % maf]
    if logistic:
        vcl.append('--logistic')
        resf = '%s.assoc.logistic' % basename # plink output is here we hope
    else:
        vcl.append('--linear')
        resf = '%s.assoc.linear' % basename # plink output is here we hope
    resf = os.path.join(twd,resf)
    if gender:
        vcl.append('--sex')
    if inter:
        vcl.append('--interaction')
    if covar > 'None':
        vcl += ['--covar',phepath,'--covar-name',covar] # comma sep list of covariates
    tcfile = None
    if len(cond) > 0: # plink wants these in a file..
        dummy,tcfile = tempfile.mkstemp(suffix='condlist') #
        f = open(tcfile,'w')
        cl = cond.split()
        f.write('\n'.join(cl))
        f.write('\n')
        f.close()
        vcl.append('--condition-list %s' % tcfile)
    p=subprocess.Popen(' '.join(vcl),shell=True,cwd=twd)
    retval = p.wait()
    if tcfile:
        os.unlink(tcfile)
    plinklog = file(tplog,'r').read()
    logf = file(logfname,'w')
    logf.write(blurb)
    logf.write('\n')
    logf.write('vcl=%s\n' % vcl)
    xformQassoc(resf=resf,outfname=outfname,logf=logf,twd=twd) # leaves the desired summary file
    makeGFF(resf=outfname,outfname=gffout,logf=logf,twd=twd,name='rgGLM_TopTable',description=title,topn=topn)
    logf.write('\n')
    logf.write(plinklog)
    logf.close()
    #shutil.rmtree(twd) # clean up






#!/usr/local/bin/python
# hack to run and process a plink tdt
# expects args as
# bfilepath outname jobname outformat (wig,xls)
# ross lazarus
# for wig files, we need annotation so look for map file or complain

"""
Parameters for wiggle track definition lines
All options are placed in a single line separated by spaces:

  track type=wiggle_0 name=track_label description=center_label \
        visibility=display_mode color=r,g,b altColor=r,g,b \
        priority=priority autoScale=on|off \
        gridDefault=on|off maxHeightPixels=max:default:min \
        graphType=bar|points viewLimits=lower:upper \
        yLineMark=real-value yLineOnOff=on|off \
        windowingFunction=maximum|mean|minimum smoothingWindow=off|2-16
"""

import sys,math,shutil,subprocess,os,time,tempfile,shutil,string
from os.path import abspath
from optparse import OptionParser
from rgutils import timenow, plinke
myversion = 'v0.003 January 2010'
verbose = False



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
    # s = 'rs\tchrom\toffset\ta1\ta2\ttransmitted\tuntransmitted\tTDTChiSq\tTDTp\t-log10TDTp\tAbsTDTOR\tTDTOR'
    chrpos = headIndex.get('CHROM',None)
    rspos = headIndex.get('RS',None)
    offspos = headIndex.get('OFFSET',None)
    ppos = headIndex.get('-LOG10TDTP',None)
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
        gff = ('chr%s' % chrom,'rgTDT','variation','%d' % (int(offset)-halfwidth),
               '%d' % (int(offset)+halfwidth),p,'.','.','%s logp=%1.2f' % (snp,pvals[i]))
        outres.append(gff)
    outres = [(x[0],int(x[3]),x) for x in outres] # decorate
    outres.sort() # into chrom offset
    outres=[x[2] for x in outres] # undecorate
    outres = ['\t'.join(x) for x in outres]
    outf.write('\n'.join(outres))
    outf.write('\n')
    outf.close()



def xformTDT(infname='',resf='',outfname='',name='foo',mapf='/usr/local/galaxy/data/rg/lped/x.bim'):
    """munge a plink .tdt file into either a ucsc track or an xls file
  CHR         SNP  A1:A2      T:U_TDT       OR_TDT    CHISQ_TDT        P_TDT
   0   MitoT217C    2:3          0:0           NA           NA           NA
   0   MitoG228A    1:4          0:0           NA           NA           NA
   0   MitoT250C    2:3          0:0           NA           NA           NA
    map file has
    1       rs4378174       0       003980745
    1       rs10796404      0       005465256
    1       rs2697965       0       014023092

   grrr!
   Changed in 1.01 to
   [rerla@hg fresh]$ head database/job_working_directory/445/rgTDT.tdt
     CHR         SNP           BP  A1  A2      T      U           OR        CHISQ            P
   1  rs12562034       758311   1   3     71     79       0.8987       0.4267       0.5136
   1   rs3934834       995669   4   2     98    129       0.7597        4.233      0.03963


    """
    if verbose:
        print 'Rgenetics Galaxy Tools, rgTDT.py.xformTDT got resf=%s, outtype=%s, outfname=%s' % (resf,outtype,outfname)
    wewantcols = ['SNP','CHR','BP','A1','A2','T','U','OR','CHISQ','P']
    res = []
    s = 'rs\tchrom\toffset\ta1\ta2\ttransmitted\tuntransmitted\tTDTChiSq\tTDTp\t-log10TDTp\tAbsTDTOR\tTDTOR' # header
    res.append(s)
    rsdict = {}
    if not mapf:
        sys.stderr.write('rgTDT called but no map file provided - cannot determine locations')
        sys.exit(1)
    map = file(mapf,'r')
    for l in map: # plink map
        ll = l.strip().split()
        if len(ll) >= 3:
            rs=ll[1].strip()
            chrom = ll[0]
            if chrom.lower() == 'x':
               chrom = '23'
            if chrom.lower() == 'y':
               chrom = '24'
            if chrom.lower() == 'mito':
               chrom = '25'
            offset = ll[3]
            rsdict[rs] = (chrom,offset)
    f = open(resf,'r')
    headl = f.next().strip()
    headl = headl.split()
    wewant = [headl.index(x) for x in wewantcols]
    llen = len(headl)
    lnum = anum = 0
    for l in f:
        lnum += 1
        ll = l.strip().split()
        if len(ll) >= llen: # valid line
            snp,chrom,offset,a1,a2,t,u,orat,chisq,p = [ll[x] for x in wewant]
            if chisq == 'NA' or p == 'NA' or orat == 'NA':
                continue # can't use these lines - gg gets unhappy
            snp = snp.strip()
            lp = '0.0'
            fp = '1.0'
            fakeorat = '1.0'
            if p.upper().strip() <> 'NA':
                try:
                   fp = float(p)
                   if fp <> 0:
                       lp = '%6f' % -math.log10(fp)
                       fp = '%6f' % fp
                except:
                  pass
            else:
                p = '1.0'
            if orat.upper().strip() <> 'NA':
                try:
                   fakeorat = orat
                   if float(orat) < 1.0:
                      fakeorat = '%6f' % (1.0/float(orat)) # invert so large values big
                except:
                   pass
            else:
                orat = '1.0'
            outl = '\t'.join([snp,chrom,offset,a1,a2,t,u,chisq,p,lp,fakeorat,orat])
            res.append(outl)
    f = file(outfname,'w')
    res.append('')
    f.write('\n'.join(res))
    f.close()


if __name__ == "__main__":
    """ called as
    <command interpreter="python">
        rgTDT.py -i '$infile.extra_files_path/$infile.metadata.base_name' -o '$title' -f '$outformat' -r '$out_file1' -l '$logf' -x '${GALAXY_DATA_INDEX_DIR}/rg/bin/pl$

    </command>

    """
    u = """ called in xml as
        <command interpreter="python2.4">
        rgTDT.py -i $i -o $out_prefix -f $outformat -r $out_file1 -l $logf
    </command>
    """
    if len(sys.argv) < 6:
       s = '## Error rgTDT.py needs 5 command line params - got %s \n' % (sys.argv)
       if verbose:
            print >> sys.stdout, s
       sys.exit(0)
    parser = OptionParser(usage=u, version="%prog 0.01")
    a = parser.add_option
    a("-i","--infile",dest="bfname")
    a("-o","--oprefix",dest="oprefix")
    a("-f","--formatOut",dest="outformat")
    a("-r","--results",dest="outfname")
    a("-l","--logfile",dest="logf")
    a("-d","--du",dest="uId")
    a("-e","--email",dest="uEmail")
    a("-g","--gff",dest="gffout",default="")
    (options,args) = parser.parse_args()
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    title = options.oprefix
    title = title.translate(trantab)
    map_file = '%s.bim' % (options.bfname) #
    me = sys.argv[0]
    alogf = options.logf # absolute paths
    od = os.path.split(alogf)[0]
    try:
      os.path.makedirs(od)
    except:
      pass
    aoutf = options.outfname # absolute paths
    od = os.path.split(aoutf)[0]
    try:
      os.path.makedirs(od)
    except:
      pass
    vcl = [plinke,'--noweb', '--bfile',options.bfname,'--out',title,'--mind','0.5','--tdt']
    logme = []
    if verbose:
        s = 'Rgenetics %s http://rgenetics.org Galaxy Tools rgTDT.py started %s\n' % (myversion,timenow())
        print >> sys.stdout,s
        logme.append(s)
        s ='rgTDT.py: bfname=%s, logf=%s, argv = %s\n' % (options.bfname,alogf, sys.argv)
        print >> sys.stdout,s
        logme.append(s)
        s = 'rgTDT.py: vcl=%s\n' % (' '.join(vcl))
        print >> sys.stdout,s
        logme.append(s)
    twd = tempfile.mkdtemp(suffix='rgTDT') # make sure plink doesn't spew log file into the root!
    tname = os.path.join(twd,title)
    p=subprocess.Popen(' '.join(vcl),shell=True,cwd=twd)
    retval = p.wait()
    shutil.copy('%s.log' % tname,alogf)
    sto = file(alogf,'a')
    sto.write('\n'.join(logme))
    resf = '%s.tdt' % tname # plink output is here we hope
    xformTDT(options.bfname,resf,aoutf,title,map_file) # leaves the desired summary file
    gffout = options.gffout
    if gffout > '':
        makeGFF(resf=aoutf,outfname=gffout,logf=sto,twd='.',name='rgTDT_Top_Table',description=title,topn=1000)
    shutil.rmtree(twd)
    sto.close()




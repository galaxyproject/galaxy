"""parse an fbat log
qqplot
"""

import sys,os, math, tempfile, subprocess, StringIO

prog = os.path.split(sys.argv[0])[-1]
removetempfiles = 0

def parsefbatlog(fname=''):
    """look for lines of the format
    read in: 9 markers from 900 pedigrees (901 nuclear families,2757 persons)
    medelian error: locus rs1860184_731, pedigree 136 [1400,318]
    and results like
    A total of 3750286 mendelian errors have been found        
genotypes of families with mendelian error have been reset to 0
>> load share_pulmpheno.phe
6 quantitative traits have been successfully read          
9340 persons have been phenotyped
warning: 1191 persons are not in any pedigrees            
>> trait ppfev1adj
affection ppfev1adj** ppfvcadj ppfefadj ppratioadj ppfefratadj
>> fbat
trait ppfev1adj; offset 0.000; model additive; test bi-allelic; minsize 10; min_freq 0.000; p 1.000; maxcmh 1000

Marker        Allele   afreq   fam#     S-E(S)      Var(S)       Z           P
------------------------------------------------------------------------------
rs10900309    2        0.184    865     14.574     509.676   0.646    0.518558
rs10900309    4        0.816    865    -14.574     509.676  -0.646    0.518558
rs12039954    2        0.082    433     -5.929     204.286  -0.415    0.678284
    """
    mendelerrors = {}
    markers = {}
    res = []
    lastrs = None
    try:
        f = open(fname,'r')
    except:
        print '**No fbat log file %s found - Mendelian errors not removed' % logf
        return mendelerrors,res,markers
    for linenum,l in enumerate(f):
        if l[:2].lower() == 'rs': # results line
            ll = l.strip().split()
            if len(ll) >= 8:
                rs = ll[0]
                afreq = float(ll[2])
                if (afreq < 0.5) or ((afreq == 0.5) and (float(ll[4]) < 0)): 
                    row = [ll[n] for n in [0,2,6,7]]
                    res.append(row)
                #marker,allele,afreq,fam,ses,vars,z,p = ll
            else:
                print 'short row at line %d = %s' % (linenum,l)
        elif l.find('locus') <> -1: # might be of interest
            marker = ''
            pedigree = ''
            l = l.replace(',',' ')
            ll = l.strip().split()
            for i in range(len(ll)):
                if ll[i].lower() == 'locus': # warning - could change with fbat upgrades?
                    marker = ll[i+1]
                elif ll[i].lower() == 'pedigree':
                    pedigree = ll[i+1]
            if marker > '':
                if not markers.has_key(marker):
                    markers[marker] = []
                if not mendelerrors.has_key(pedigree):
                    mendelerrors[pedigree] = [marker,]
                else:
                    mendelerrors[pedigree].append(marker)
                if pedigree not in markers[marker]:
                    markers[marker].append(pedigree)
        elif l[:6].lower == 'marker':
            head = l.strip().split()
    return mendelerrors,res,markers

def runfbat(fbatpedf=None, smendelfile=None, mmendelfile=None, ggoutfile=None,
            log=None, phefile=None, phelist=[], centered=[], empirical=[]):
    """Swap fbat log files to get the mendel errors out, then get the results for each trait out separately for
    keeping, and amalgamated into a genome graphs file. Use a bunch of temp files and operate fbat in batch
    mode by feeding a list of commands from stdin as part of the Popen run...
    """
    fbate = "/usr/local/bin/fbat"
    clist = [] # these will be fed via stdin to fbat!
    (f,mendelfile) = tempfile.mkstemp(prefix=prog,suffix='.log')
    (f,batfile) = tempfile.mkstemp(prefix=prog,suffix='.bat')
    clist.append('log %s' % (mendelfile)) # write all mendel errors here
    s = "load %s" % fbatpedf
    clist.append(s)
    traitlogs = []
    f = file(phefile,'r')
    phes = f.readline().strip().split()
    dphes = dict(zip(phes,phes)) # header dicts
    f.close()
    clist.append('load %s' % (phefile))
    for i, phe in enumerate(phelist): # add trait and fbat flags to list
        (f,afilename) = tempfile.mkstemp(prefix=prog,suffix='.log')
        traitlogs.append(afilename) # to use later to parse logs
        clist.append('trait %s' % phe)
        clist.append('log %s' % (afilename)) # switch log files - we'll parse them later
        task = ['fbat',]
        if len(centered) > i:
            c = centered[i]
            e = empirical[i]
            if e:
                task.append('-e')
            if c:
                task.append('-o')
        s = ' '.join(task)
        clist.append(s)
    clist.append('quit\n')
    log.write('Using the following fbat commands\n')
    log.write('\n'.join(clist))
    log.write('\n')
    print 'using ','\n'.join(clist)
    f = file(batfile,'w')
    f.write('\n'.join(clist))
    f.close()
    vcl = ' '.join([fbate,' < %s' % batfile, '> /dev/null'])
    x = subprocess.Popen(vcl,shell=True) # ignore stdout
    retval = x.wait()
    me,res,markers = parsefbatlog(mendelfile)
    if removetempfiles:
        os.unlink(mendelfile)
        os.unlink(batfile)
    mlist = []
    for m in markers.keys():
        mlist.append((len(markers[m]),m)) # replace with count of pedigrees, marker tuple for sorting
    mlist.sort()
    mlist.reverse()
    plist = []
    for p in me.keys():
        plist.append((len(me[p]),p))
    plist.sort()
    plist.reverse()
    res = []
    res.append('Marker\tNMendel')
    outf = open(mmendelfile,'w')
    for (n,m) in mlist:
        res.append('%s\t%d' % (m,n))
    outf.write('\n'.join(res))
    outf.close()
    res = []
    outf = open(smendelfile,'w')    
    res.append('FamilyId\tNMendel')
    for (n,p) in plist:
        res.append('%s\t%d' % (p,n))
    res.append('')
    outf.write('\n'.join(res))
    outf.close()
    fout = file(ggoutfile,'w')
    fout.write('marker\ttrait\tafreq\tz\tp\tlog10p\n')
    for n,afilename in enumerate(traitlogs):
        trait = phelist[n]
        me,fres,markers = parsefbatlog(afilename)
        print 'for %s got fres=%s' % (afilename,fres[:50])
        # run fbat, then parse the output file
        for row in fres: # marker,afreq,z,p 
            try:
                lp = -math.log10(float(row[3]))
            except:
                lp = 1.0
            row.insert(1,trait)
            row.append('%e' % lp)
            fout.write('\t'.join(row))
            fout.write('\n')
        if removetempfiles:
            os.unlink(afilename)
    fout.close()        


def parse():
    """ 
      <command interpreter="python2.4">
        rgFbat.py "$title" "$phecols" "$out_file1" "$logfile"
        $smendelfile $mmendelfile $fbatped.extra_files_path $fbatped.name
        $fbatphe.extra_files_path $fbatphe.name
    </command>   
    """
    jobname = sys.argv[1]
    phecols = sys.argv[2].split(',')
    ggoutfile = sys.argv[3]
    logfile = sys.argv[4]
    smendelfile = sys.argv[5]
    mmendelfile = sys.argv[6]
    peddir  = sys.argv[7]
    pedname = sys.argv[8]
    pedpath = os.path.join(peddir,'%s.ped' % pedname)
    phedir = sys.argv[9]
    phename = sys.argv[10]
    phepath = os.path.join(phedir,'%s.phe' % phename)
    centered = []
    empirical = []
    if len(sys.argv) >= 13:
        centered=sys.argv[11].split()
        empirical=sys.argv[12].split()
    log = file(logfile,'w')
    s = '## Rgenetics http://rgenetics.org Galaxy Tools - cl=%s \n' % (' '.join(sys.argv))
    print >> sys.stdout, s
    log.write(s)
    runfbat(fbatpedf=pedpath, smendelfile=smendelfile, mmendelfile=mmendelfile, ggoutfile=ggoutfile,
            log =log , phefile=phepath, phelist=phecols, centered=[], empirical=[])
    log.close()

if __name__ == "__main__":
    parse()
"""
fakephe.py
ross lazarus sept 30 2007
This is available under the LGPL as defined then.

use the pedigree data for ids

use pythons generators to literally generate a bunch of random phenotype measurements

Plink format at http://pngu.mgh.harvard.edu/~purcell/plink/data.shtml#pheno
is

To specify an alternate phenotype for analysis, i.e. other than the one in the *.ped file (or, if using a binary fileset, the
*.fam file), use the --pheno option:
plink --file mydata --pheno pheno.txt

where pheno.txt is a file that contains 3 columns (one row per individual):

     Family ID
     Individual ID
     Phenotype

NOTE The original PED file must still contain a phenotype in column 6 (even if this is a dummy phenotype, e.g. all missing),
unless the --no-pheno flag is given.

If an individual is in the original file but not listed in the alternate phenotype file, that person's phenotype will be set to
missing. If a person is in the alternate phenotype file but not in the original file, that entry will be ignored. The order of
the alternate phenotype file need not be the same as for the original file.

If the phenotype file contains more than one phenotype, then use the --mpheno N option to specify the Nth phenotype is the one
to be used:
plink --file mydata --pheno pheno2.txt --mpheno 4

where pheno2.txt contains 5 different phenotypes (i.e. 7 columns in total), this command will use the 4th for analysis
(phenotype D):

     Family ID
     Individual ID
     Phenotype A
     Phenotype B
     Phenotype C
     Phenotype D
     Phenotype E

Alternatively, your alternate phenotype file can have a header row, in which case you can use variable names to specify which
phenotype to use. If you have a header row, the first two variables must be labelled FID and IID. All subsequent variable names
cannot have any whitespace in them. For example,

     FID    IID      qt1   bmi    site
     F1     1110     2.3   22.22  2
     F2     2202     34.12 18.23  1
     ...

then
plink --file mydata --pheno pheno2.txt --pheno-name bmi --assoc

will select the second phenotype labelled "bmi", for analysis

Finally, if there is more than one phenotype, then for basic association tests, it is possible to specify that all phenotypes
be tested, sequentially, with the output sent to different files: e.g. if bigpheno.raw contains 10,000 phenotypes, then
plink --bfile mydata --assoc --pheno bigpheno.raw --all-pheno

will loop over all of these, one at a time testing for association with SNP, generating a lot of output. You might want to use
the --pfilter command in this case, to only report results with a p-value less than a certain value, e.g. --pfilter 1e-3.

WARNING Currently, all phenotypes must be numerically coded, including missing values, in the alternate phenotype file. The
default missing value is -9, change this with --missing-phenotype, but it must be a numeric value still (in contrast to the
main phenotype in the PED/FAM file. This issue will be fixed in future releases.
Covariate files

===========================
rgfakePhe.xml
<tool id="fakePhe1" name="Fake phenos">
  <description>for multiple null fake phenotype</description>
  <command interpreter="python2.4">rgfakePhe.py $input1 '$title1' $out_file1 $log_file1 $script_file</command>
   <inputs>
    <page>
    <param name="input1"
         type="library" format="lped"
         label="Pedigree from Dataset"/>
    <param name="title1" type="text"
         value="My fake phenos" size="60"
         label="Title for outputs"/>
    </page>
    <page>
    <repeat name="fakePhe" title="Phenotypes to Fake">
        <param name="pName" type="text" label="Phenotype Name">
        </param>
      <conditional name="series">
        <param name="phetype" type="select" label="Phenotype Type">
          <option value="rnorm" selected="true">Random normal variate</option>
          <option value="cat">Random categorical</option>
        </param>
        <when value="rnorm">
          <param name="Mean" type="float" value="0.0" label="Mean">
          </param>
          <param name="SD" type="float" label="SD" value="1.0">
          </param>
        </when>
        <when value="cat">
          <param name="values" type="text" value="1,2,3,fiddle" label="comma separated values to choose from">
          </param>
        </when>
      </conditional>
    </repeat>
    </page>
</inputs>
<configfiles>
<configfile name="script_file">
#for $n, $f in enumerate($fakePhe)
#if $f.series.phetype=='rnorm'
{'pN':'$f.pName','pT':'$f.series.phetype','pP':"{'Mean':'$f.series.Mean', 'SD':'$f.series.SD'}"}
#elif $f.series.phetype=='cat'
{'pN':'$f.pName','pT':'$f.series.phetype','pP':"{'values':'$f.series.values'}"}
#end if
#end for
</configfile>
</configfiles>

 <outputs>
    <data format="pphe" name="out_file1" />
    <data format="text" name="log_file1" parent="out_file1"/>
  </outputs>

<help>
.. class:: infomark

This tool allows you to generate an arbitrary (sort of)
synthetic phenotype file with measurements drawn from normal,
gamma, or categorical distributions. These are for testing under
the null hypothesis of no association - the values are random but
from user specified distributions.

-----

.. class:: warningmark

This tool is very experimental

-----

- **Pedigree** is a library pedigree file - the id's will be used in the synthetic null phenotypes
- **Title** is a name to give to the output phenotype file

On the next page, you can add an unlimited number of various kinds of phenotypes including choices for
categorical ones or distributions with specific parameters

Just keep adding new ones until you're done then use the Execute button to run the generation




**Example from another tool to keep you busy and in awe**

Input file::

    1   68  4.1
    2   71  4.6
    3   62  3.8
    4   75  4.4
    5   58  3.2
    6   60  3.1
    7   67  3.8
    8   68  4.1
    9   71  4.3
    10  69  3.7

Create a two series XY plot on the above data:

- Series 1: Red Dashed-Line plot between columns 1 and 2
- Series 2: Blue Circular-Point plot between columns 3 and 2

.. image:: ./static/images/xy_example.jpg
</help>
</tool>



"""

import random,copy,sys,os,time,string,math

doFbatphe = False

galhtmlprefix = """<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta name="generator" content="Galaxy %s tool output - see http://g2.trac.bx.psu.edu/" />
<title></title>
<link rel="stylesheet" href="/static/style/base.css" type="text/css" />
</head>
<body>
<div class="document">
"""


def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


def poisson(lamb=2):
    """
    algorithm poisson random number (Knuth):
    init:
         Let L = e^-lamb, k = 0 and p = 1.
    do:
         k = k + 1.
         Generate uniform random number u in [0,1] and let p = p u.
    while p >= L.
    return k - 1.
    """
    lamb = float(lamb)
    l = math.e**(-lamb)
    k=0
    p=1
    while 1:
        while p >= l:
            k += 1
            u = random.uniform(0.0,1.0)
            p *= u
        yield '%e' % (k - 1)

def gammaPhe(alpha=1,beta=1):
    """generator for random values from a gamma
    """
    while 1: # an iterator for a random phenotype
        dat = random.gammavariate(float(alpha),float(beta))
        yield '%e' % dat

def weibullPhe(alpha=1,beta=1):
    """generator for random values from a weibull distribution
    """
    while 1: # an iterator for a random phenotype
        dat = random.weibullvariate(float(alpha),float(beta))
        yield '%e' % dat

def normPhe(mean=0,sd=1):
    """generator for random values from a normal distribution
    """
    while 1:# an iterator for a random phenotype
        dat = random.normalvariate(float(mean),float(sd))
        yield '%e' % dat

def expoPhe(mean=1):
    """generator for random values from an exponential distribution
    """
    lamb = 1.0/float(mean)
    while 1:# an iterator for a random phenotype
        dat = random.expovariate(lamb)
        yield '%e' % dat


def catPhe(values='1,2,3'):
    """ Schrodinger's of course.
    """
    v = values.split(',')
    while 1:# an iterator for a random phenotype
        dat = random.choice(v)
        yield dat

def uniPhe(low=0.0,hi=1.0):
    """generator for a uniform distribution
       what if low=-5 and hi=-2
    """
    low = float(low)
    hi = float(hi)
    while 1: # unif phenotype
        v = random.uniform(low,hi) # 0-1
        yield '%e' % v

def getIds(indir='foo'):
    """read identifiers - first 2 cols from a pedigree file or fam file
    """
    inpath = os.path.split(indir)[0] # get root
    infam = '%s.fam' % indir
    inped = '%s.ped' % indir # if there's a ped
    flist = os.listdir(inpath)
    if len(flist) == 0:
        print >> sys.stderr, '### Error - input path %s is empty' % indir
        sys.exit(1)
    if os.path.exists(infam):
        pfname = infam
    elif os.path.exists(inped):
        pfname = inped
    else:
        print >> sys.stderr, '### Error - input path %s contains no ped or fam' % indir
        sys.exit(1)   
    f = file(pfname,'r')
    ids = []
    for l in f:
        ll = l.split()
        if len(ll) > 5: # ok line?
            ids.append(ll[:2])
    return ids

def makePhe(phes = [],ids=[]):
    """Create the null phenotype values and append them to the case id
    phes is the (generator, headername) for each column
    for a phe file, ids are the case identifiers for the phenotype file
    res contains the final strings for the file
    each column is derived by iterating
    over the generator actions set up by makePhes
    """
    header = ['FID','IID'] # for plink
    res = copy.copy(ids)
    for (f,fname) in phes:
        header.append(fname)
        for n,subject in enumerate(ids):
            res[n].append(f.next()) # generate the right value
    res.insert(0,header)
    res = [' '.join(x) for x in res] # must be space delim for fbat
    return res

def makePhes(pheTypes=[], pheNames=[], pheParams=[]):
    """set up phes for makePhe
    each has to have an iterator (action) and a name
    """
    action = None
    phes = []
    for n,pt in enumerate(pheTypes):
        name = pheNames[n]
        if pt == 'rnorm':
            m = pheParams[n].get('Mean',0.0)
            s = pheParams[n].get('SD',1.0)
            action = normPhe(mean=m,sd=s) # so we can just iterate over action
        elif pt == 'rgamma':
            m = pheParams[n].get('Alpha',0.0)
            s = pheParams[n].get('Beta',1.0)
            action = gammaPhe(alpha=m,beta=s)
        if pt == 'exponential':
            m = pheParams[n].get('Mean',1.0)
            action = expoPhe(mean=m) # so we can just iterate over action
        elif pt == 'weibull':
            m = pheParams[n].get('Alpha',0.0)
            s = pheParams[n].get('Beta',1.0)
            action = weibullPhe(alpha=m,beta=s)
        elif pt == 'cat':
            v = pheParams[n].get('values',['?',])
            action = catPhe(values=v)
        elif pt == 'unif':
            low = pheParams[n].get('low',0.0)
            hi = pheParams[n].get('hi',1.0)
            action = uniPhe(low=low,hi=hi)
        elif pt == 'poisson':
            lamb = pheParams[n].get('lamb',1.0)
            action = poisson(lamb=lamb)
        phes.append((action,name))
    return phes

def doImport(outfile='test',flist=[],expl='',mylog=[]):
    """ import into one of the new html composite data types for Rgenetics
        Dan Blankenberg with mods by Ross Lazarus
        October 2007
    """
    outf = open(outfile,'w')
    progname = os.path.basename(sys.argv[0])
    outf.write(galhtmlprefix % progname)
    if len(flist) > 0:
        outf.write('<ol>\n')
        for i, data in enumerate( flist ):
           outf.write('<li><a href="%s">%s %s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1],expl))
        outf.write('</ol>\n')
    else:
           outf.write('No files found')
    outf.write('<hr/><h4>Log of run follows:</h4><br/><pre>%s\n</pre><br/><hr/>' % ('\n'.join(mylog)))
    outf.write("</div></body></html>\n")
    outf.close()


def test():
    """test case
    need to get these out of a galaxy form - series of pages - get types
    on first screen, names on second, params on third?
    holy shit. this actually works I think
    """
    pT = ['rnorm','rnorm','rnorm','rnorm','cat','unif']
    pN = ['SysBP','DiaBP','HtCM','WtKG','Race','age']
    pP = [{'Mean':'120','SD':'10'},{'Mean':'90','SD':'15'},{'Mean':'160','SD':'20'},{'Mean':'60','SD':'20'}, \
          {'values':'Blink,What,Yours,green'},{'low':16,'hi':99}]
    phes = makePhes(pheTypes=pT, pheNames=pN, pheParams=pP)
    ids = []
    for i in range(10):
        ids.append(['fid%d' % i,'iid%d' % i])
    pheres = makePhe(phes=phes,ids=ids)
    res = [''.join(x) for x in pheres]
    print '\n'.join(res)



if __name__ == "__main__":
    """
   <command interpreter="python">rgfakePhe.py '$infile1.extra_files_path/$infile1.metadata.base_name'
   "$title1" '$ppheout' '$ppheout.files_path' '$script_file '
   </command>
    The xml file for this tool is complex, and allows any arbitrary number of
    phenotype columns to be specified from a couple of optional types - rnorm, cat
    are working now.

    Note that we create new files in their respective library directories and link to them in the output file
    so they can be displayed and downloaded separately

    """
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    progname = os.path.basename(sys.argv[0])
    cl = '## at %s, %s got cl= %s' % (timenow(),progname,' '.join(sys.argv))
    print >> sys.stdout,cl
    if len(sys.argv) < 5:
        test()
    else:
        inped = sys.argv[1]
        title = sys.argv[2].translate(trantab)
        ppheout = sys.argv[3]
        pphe_path = sys.argv[4]
        scriptfile = sys.argv[5]
        ind = file(scriptfile,'r').readlines()
        mylog = []
        s = '## %s starting at %s<br/>\n' % (progname,timenow())
        mylog.append(s)
        mylog.append(cl)
        s = '## params = %s<br/>\n' % (' '.join(sys.argv[1:]))
        mylog.append(s)
        s = '\n'.join(ind)
        mylog.append('Script file %s contained %s<br/>\n' % (scriptfile,s))
        pT = []
        pN = []
        pP = []
        for l in ind:
            l = l.strip()
            if len(l) > 1:
                adict = eval(l)
                pT.append(adict.get('pT',None))
                pN.append(adict.get('pN',None))
                pP.append(eval(adict.get('pP',None)))
        s = '## pt,pn,pp=%s,%s,%s<br/>\n' % (str(pT),str(pN),str(pP))
        mylog.append(s)
        phes = makePhes(pheTypes=pT, pheNames=pN, pheParams=pP)
        ids = getIds(indir=inped) # for labelling rows
        pheres = makePhe(phes=phes,ids=ids) # random values from given distributions
        try:
            os.makedirs(pphe_path)
        except:
            pass
        outname = os.path.join(pphe_path,title)
        pphefname = '%s.pphe' % outname
        f = file(pphefname, 'w')
        f.write('\n'.join(pheres))
        f.write('\n')
        f.close()
        if doFbatphe:
            try:
                os.makedirs(fphe_path)
            except:
                pass
            outname = os.path.join(fphe_path,title)
            fphefname = '%s.phe' % outname
            f = file(fphefname, 'w')
            header = pheres[0].split()
            pheres[0] = ' '.join(header[2:])# remove iid fid from header for fbat
            f.write('\n'.join(pheres))
            f.close()
            doImport(outfile=fpheout,flist=[fphefname,],expl='(FBAT phenotype format)',mylog=mylog)
        #doImport(outfile='test',flist=[],expl='',mylog=[]):
        doImport(outfile=ppheout,flist=[pphefname,],expl='(Plink phenotype format)',mylog=mylog)


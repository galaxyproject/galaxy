#!/usr/bin/env python

from galaxy import eggs
import sys, string
from rpy import *
import numpy

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

infile = sys.argv[1]
x_cols = sys.argv[2].split(',')
method = sys.argv[3]
outfile = sys.argv[4]
outfile2 = sys.argv[5]

if method == 'svd':
    scale = center = "FALSE"
    if sys.argv[6] == 'both':
        scale = center = "TRUE"
    elif sys.argv[6] == 'center':
        center = "TRUE"
    elif sys.argv[6] == 'scale':
        scale = "TRUE"
    
fout = open(outfile,'w')
elems = []
for i, line in enumerate( file ( infile )):
    line = line.rstrip('\r\n')
    if len( line )>0 and not line.startswith( '#' ):
        elems = line.split( '\t' )
        break 
    if i == 30:
        break # Hopefully we'll never get here...

if len( elems )<1:
    stop_err( "The data in your input dataset is either missing or not formatted properly." )

x_vals = []

for k,col in enumerate(x_cols):
    x_cols[k] = int(col)-1
    x_vals.append([])

NA = 'NA'
skipped = 0
for ind,line in enumerate( file( infile )):
    if line and not line.startswith( '#' ):
        try:
            fields = line.strip().split("\t")
            valid_line = True
            for k,col in enumerate(x_cols):
                try:
                    xval = float(fields[col])
                except:
                    skipped += 1 
                    valid_line = False
                    break
            if valid_line:
                for k,col in enumerate(x_cols):
                    xval = float(fields[col])
                    x_vals[k].append(xval)
        except:
            skipped += 1

x_vals1 = numpy.asarray(x_vals).transpose()
dat= r.list(array(x_vals1))

set_default_mode(NO_CONVERSION)
try:
    if method == "cor":
        pc = r.princomp(r.na_exclude(dat), cor = r("TRUE"))
    elif method == "cov":
        pc = r.princomp(r.na_exclude(dat), cor = r("FALSE"))
    elif method=="svd":
        pc = r.prcomp(r.na_exclude(dat), center = r(center), scale = r(scale))
except RException, rex:
    stop_err("Encountered error while performing PCA on the input data: %s" %(rex))

set_default_mode(BASIC_CONVERSION)
summary = r.summary(pc, loadings="TRUE")
ncomps = len(summary['sdev'])

if type(summary['sdev']) == type({}):
    comps_unsorted = summary['sdev'].keys()
    comps=[]
    sd = summary['sdev'].values()
    for i in range(ncomps):
        sd[i] = summary['sdev'].values()[comps_unsorted.index('Comp.%s' %(i+1))]
        comps.append('Comp.%s' %(i+1))
elif type(summary['sdev']) == type([]):
    comps=[]
    for i in range(ncomps):
        comps.append('Comp.%s' %(i+1))
        sd = summary['sdev']

print >>fout, "#Component\t%s" %("\t".join(["%s" % el for el in range(1,ncomps+1)]))
print >>fout, "#Std. deviation\t%s" %("\t".join(["%.4g" % el for el in sd]))
total_var = 0
vars = []
for s in sd:
    var = s*s
    total_var += var
    vars.append(var)
for i,var in enumerate(vars):
    vars[i] = vars[i]/total_var
       
print >>fout, "#Proportion of variance explained\t%s" %("\t".join(["%.4g" % el for el in vars]))

print >>fout, "#Loadings\t%s" %("\t".join(["%s" % el for el in range(1,ncomps+1)]))
xcolnames = ["c%d" %(el+1) for el in x_cols]
if 'loadings' in summary: #in case of princomp
    loadings = 'loadings'
elif 'rotation' in summary: #in case of prcomp
    loadings = 'rotation'
for i,val in enumerate(summary[loadings]):
    print >>fout, "%s\t%s" %(xcolnames[i], "\t".join(["%.4g" % el for el in val]))

print >>fout, "#Scores\t%s" %("\t".join(["%s" % el for el in range(1,ncomps+1)]))
if 'scores' in summary: #in case of princomp
    scores = 'scores'
elif 'x' in summary: #in case of prcomp
    scores = 'x'
for obs,sc in enumerate(summary[scores]):
    print >>fout, "%s\t%s" %(obs+1, "\t".join(["%.4g" % el for el in sc]))

r.pdf( outfile2, 8, 8 )
r.biplot(pc)
r.dev_off()
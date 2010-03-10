#!/usr/bin/env python

"""
Run kernel CCA using kcca() from R 'kernlab' package

usage: %prog [options]
   -i, --input=i: Input file
   -o, --output1=o: Summary output
   -x, --x_cols=x: X-Variable columns
   -y, --y_cols=y: Y-Variable columns
   -k, --kernel=k: Kernel function
   -f, --features=f: Number of canonical components to return
   -s, --sigma=s: sigma
   -d, --degree=d: degree
   -l, --scale=l: scale
   -t, --offset=t: offset
   -r, --order=r: order

usage: %prog input output1 x_cols y_cols kernel features sigma(or_None) degree(or_None) scale(or_None) offset(or_None) order(or_None)
"""

from galaxy import eggs
import sys, string
from rpy import *
import numpy
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

#Parse Command Line
options, args = doc_optparse.parse( __doc__ )
#{'options= kernel': 'rbfdot', 'var_cols': '1,2,3,4', 'degree': 'None', 'output2': '/afs/bx.psu.edu/home/gua110/workspace/galaxy_bitbucket/database/files/000/dataset_260.dat', 'output1': '/afs/bx.psu.edu/home/gua110/workspace/galaxy_bitbucket/database/files/000/dataset_259.dat', 'scale': 'None', 'offset': 'None', 'input': '/afs/bx.psu.edu/home/gua110/workspace/galaxy_bitbucket/database/files/000/dataset_256.dat', 'sigma': '1.0', 'order': 'None'}

infile = options.input
x_cols = options.x_cols.split(',')
y_cols = options.y_cols.split(',')
kernel = options.kernel
outfile = options.output1
ncomps = int(options.features)
fout = open(outfile,'w')

if ncomps < 1:
    print "You chose to return '0' canonical components. Please try rerunning the tool with number of components = 1 or more."
    sys.exit()
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
y_vals = []
for k,col in enumerate(y_cols):
    y_cols[k] = int(col)-1
    y_vals.append([])
NA = 'NA'
skipped = 0
for ind,line in enumerate( file( infile )):
    if line and not line.startswith( '#' ):
        try:
            fields = line.strip().split("\t")
            valid_line = True
            for col in x_cols+y_cols:
                try:
                    assert float(fields[col])
                except:
                    skipped += 1
                    valid_line = False
                    break
            if valid_line:
                for k,col in enumerate(x_cols):
                    try:
                        xval = float(fields[col])
                    except:
                        xval = NaN#
                    x_vals[k].append(xval)
                for k,col in enumerate(y_cols):
                    try:
                        yval = float(fields[col])
                    except:
                        yval = NaN#
                    y_vals[k].append(yval)
        except:
            skipped += 1

x_vals1 = numpy.asarray(x_vals).transpose()
y_vals1 = numpy.asarray(y_vals).transpose()

x_dat= r.list(array(x_vals1))
y_dat= r.list(array(y_vals1))

try:
    r.suppressWarnings(r.library('kernlab'))
except:
    stop_err('Missing R library kernlab')
            
set_default_mode(NO_CONVERSION)
if kernel=="rbfdot" or kernel=="anovadot":
    pars = r.list(sigma=float(options.sigma))
elif kernel=="polydot":
    pars = r.list(degree=float(options.degree),scale=float(options.scale),offset=float(options.offset))
elif kernel=="tanhdot":
    pars = r.list(scale=float(options.scale),offset=float(options.offset))
elif kernel=="besseldot":
    pars = r.list(degree=float(options.degree),sigma=float(options.sigma),order=float(options.order))
elif kernel=="anovadot":
    pars = r.list(degree=float(options.degree),sigma=float(options.sigma))
else:
    pars = rlist()
    
try:
    kcc = r.kcca(x=x_dat, y=y_dat, kernel=kernel, kpar=pars, ncomps=ncomps)
except RException, rex:
    stop_err("Encountered error while performing kCCA on the input data: %s" %(rex))

set_default_mode(BASIC_CONVERSION)    
kcor = r.kcor(kcc)
if ncomps == 1:
    kcor = [kcor]
xcoef = r.xcoef(kcc)
ycoef = r.ycoef(kcc)

print >>fout, "#Component\t%s" %("\t".join(["%s" % el for el in range(1,ncomps+1)]))

print >>fout, "#Correlation\t%s" %("\t".join(["%.4g" % el for el in kcor]))
    
print >>fout, "#Estimated X-coefficients\t%s" %("\t".join(["%s" % el for el in range(1,ncomps+1)]))
for obs,val in enumerate(xcoef):
    print >>fout, "%s\t%s" %(obs+1, "\t".join(["%.4g" % el for el in val]))

print >>fout, "#Estimated Y-coefficients\t%s" %("\t".join(["%s" % el for el in range(1,ncomps+1)]))
for obs,val in enumerate(ycoef):
    print >>fout, "%s\t%s" %(obs+1, "\t".join(["%.4g" % el for el in val]))

#!/usr/bin/env python

"""
Run kernel PCA using kpca() from R 'kernlab' package

usage: %prog [options]
   -i, --input=i: Input file
   -o, --output1=o: Summary output
   -p, --output2=p: Figures output
   -c, --var_cols=c: Variable columns
   -k, --kernel=k: Kernel function
   -f, --features=f: Number of principal components to return
   -s, --sigma=s: sigma
   -d, --degree=d: degree
   -l, --scale=l: scale
   -t, --offset=t: offset
   -r, --order=r: order

usage: %prog input output1 output2 var_cols kernel features sigma(or_None) degree(or_None) scale(or_None) offset(or_None) order(or_None)
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
x_cols = options.var_cols.split(',')
kernel = options.kernel
outfile = options.output1
outfile2 = options.output2
ncomps = int(options.features)
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
            for k,col in enumerate(x_cols):
                try:
                    xval = float(fields[col])
                except:
                    #xval = r('NA')
                    xval = NaN#
                x_vals[k].append(xval)
        except:
            skipped += 1

x_vals1 = numpy.asarray(x_vals).transpose()
dat= r.list(array(x_vals1))

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
    pars = r.list()
    
try:
    kpc = r.kpca(x=r.na_exclude(dat), kernel=kernel, kpar=pars, features=ncomps)
except RException, rex:
    stop_err("Encountered error while performing kPCA on the input data: %s" %(rex))
set_default_mode(BASIC_CONVERSION)
    
eig = r.eig(kpc)
pcv = r.pcv(kpc)
rotated = r.rotated(kpc)

comps = eig.keys()
eigv = eig.values()
for i in range(ncomps):
    eigv[comps.index('Comp.%s' %(i+1))] = eig.values()[i]

print >>fout, "#Component\t%s" %("\t".join(["%s" % el for el in range(1,ncomps+1)]))

print >>fout, "#Eigenvalue\t%s" %("\t".join(["%.4g" % el for el in eig.values()]))
    
print >>fout, "#Principal component vectors\t%s" %("\t".join(["%s" % el for el in range(1,ncomps+1)]))
for obs,val in enumerate(pcv):
    print >>fout, "%s\t%s" %(obs+1, "\t".join(["%.4g" % el for el in val]))

print >>fout, "#Rotated values\t%s" %("\t".join(["%s" % el for el in range(1,ncomps+1)]))
for obs,val in enumerate(rotated):
    print >>fout, "%s\t%s" %(obs+1, "\t".join(["%.4g" % el for el in val]))

r.pdf( outfile2, 8, 8 )
if ncomps != 1:
    r.pairs(rotated,labels=r.list(range(1,ncomps+1)),main="Scatterplot of rotated values")
else:
    r.plot(rotated, ylab='Comp.1', main="Scatterplot of rotated values")
r.dev_off()
#!/usr/bin/env python

from galaxy import eggs

import sys, string
from rpy import *
import numpy

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

infile = sys.argv[1]
y_col = int(sys.argv[2])-1
x_cols = sys.argv[3].split(',')
outfile = sys.argv[4]
outfile2 = sys.argv[5]
print "Predictor columns: %s; Response column: %d" %(x_cols,y_col+1)
fout = open(outfile,'w')

for i, line in enumerate( file ( infile )):
    line = line.rstrip('\r\n')
    if len( line )>0 and not line.startswith( '#' ):
        elems = line.split( '\t' )
        break 
    if i == 30:
        break # Hopefully we'll never get here...

if len( elems )<1:
    stop_err( "The data in your input dataset is either missing or not formatted properly." )

y_vals = []
x_vals = []

for k,col in enumerate(x_cols):
    x_cols[k] = int(col)-1
    x_vals.append([])
    
NA = 'NA'
for ind,line in enumerate( file( infile )):
    if line and not line.startswith( '#' ):
        try:
            fields = line.split("\t")
            try:
                yval = float(fields[y_col])
            except Exception, ey:
                yval = r('NA')
            y_vals.append(yval)
            for k,col in enumerate(x_cols):
                try:
                    xval = float(fields[col])
                except Exception, ex:
                    xval = r('NA')
                x_vals[k].append(xval)
        except:
            pass

response_term = ""

x_vals1 = numpy.asarray(x_vals).transpose()

dat= r.list(x=array(x_vals1), y=y_vals)

r.library("leaps")
 
set_default_mode(NO_CONVERSION)
try:
    leaps = r.regsubsets(r("y ~ x"), data= r.na_exclude(dat))
except RException, rex:
    stop_err("Error performing linear regression on the input data.\nEither the response column or one of the predictor columns contain no numeric values.")
set_default_mode(BASIC_CONVERSION)

summary = r.summary(leaps)
tot = len(x_vals)
pattern = "["
for i in range(tot):
    pattern = pattern + 'c' + str(int(x_cols[int(i)]) + 1) + ' '
pattern = pattern.strip() + ']'  
print >>fout, "#Vars\t%s\tR-sq\tAdj. R-sq\tC-p\tbic" %(pattern)
for ind,item in enumerate(summary['outmat']):
    print >>fout, "%s\t%s\t%s\t%s\t%s\t%s" %(str(item).count('*'), item, summary['rsq'][ind], summary['adjr2'][ind], summary['cp'][ind], summary['bic'][ind])


r.pdf( outfile2, 8, 8 )
r.plot(leaps, scale="Cp", main="Best subsets using Cp Criterion")
r.plot(leaps, scale="r2", main="Best subsets using R-sq Criterion")
r.plot(leaps, scale="adjr2", main="Best subsets using Adjusted R-sq Criterion")
r.plot(leaps, scale="bic", main="Best subsets using bic Criterion")

r.dev_off()

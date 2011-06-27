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
            except:
                yval = r('NA')
            y_vals.append(yval)
            for k,col in enumerate(x_cols):
                try:
                    xval = float(fields[col])
                except:
                    xval = r('NA')
                x_vals[k].append(xval)
        except:
            pass

x_vals1 = numpy.asarray(x_vals).transpose()

dat= r.list(x=array(x_vals1), y=y_vals)

set_default_mode(NO_CONVERSION)
try:
    linear_model = r.lm(r("y ~ x"), data = r.na_exclude(dat))
except RException, rex:
    stop_err("Error performing linear regression on the input data.\nEither the response column or one of the predictor columns contain only non-numeric or invalid values.")
set_default_mode(BASIC_CONVERSION)

coeffs=linear_model.as_py()['coefficients']
yintercept= coeffs['(Intercept)']
summary = r.summary(linear_model)

co = summary.get('coefficients', 'NA')
"""
if len(co) != len(x_vals)+1:
    stop_err("Stopped performing linear regression on the input data, since one of the predictor columns contains only non-numeric or invalid values.")
"""

try:
    yintercept = r.round(float(yintercept), digits=10)
    pvaly = r.round(float(co[0][3]), digits=10)
except:
    pass

print >>fout, "Y-intercept\t%s" %(yintercept)
print >>fout, "p-value (Y-intercept)\t%s" %(pvaly)

if len(x_vals) == 1:    #Simple linear  regression case with 1 predictor variable
    try:
        slope = r.round(float(coeffs['x']), digits=10)
    except:
        slope = 'NA'
    try:
        pval = r.round(float(co[1][3]), digits=10)
    except:
        pval = 'NA'
    print >>fout, "Slope (c%d)\t%s" %(x_cols[0]+1,slope)
    print >>fout, "p-value (c%d)\t%s" %(x_cols[0]+1,pval)
else:    #Multiple regression case with >1 predictors
    ind=1
    while ind < len(coeffs.keys()):
        try:
            slope = r.round(float(coeffs['x'+str(ind)]), digits=10)
        except:
            slope = 'NA'
        print >>fout, "Slope (c%d)\t%s" %(x_cols[ind-1]+1,slope)
        try:
            pval = r.round(float(co[ind][3]), digits=10)
        except:
            pval = 'NA'
        print >>fout, "p-value (c%d)\t%s" %(x_cols[ind-1]+1,pval)
        ind+=1

rsq = summary.get('r.squared','NA')
adjrsq = summary.get('adj.r.squared','NA')
fstat = summary.get('fstatistic','NA')
sigma = summary.get('sigma','NA')

try:
    rsq = r.round(float(rsq), digits=5)
    adjrsq = r.round(float(adjrsq), digits=5)
    fval = r.round(fstat['value'], digits=5)
    fstat['value'] = str(fval)
    sigma = r.round(float(sigma), digits=10)
except:
    pass

print >>fout, "R-squared\t%s" %(rsq)
print >>fout, "Adjusted R-squared\t%s" %(adjrsq)
print >>fout, "F-statistic\t%s" %(fstat)
print >>fout, "Sigma\t%s" %(sigma)

r.pdf( outfile2, 8, 8 )
if len(x_vals) == 1:    #Simple linear  regression case with 1 predictor variable
    sub_title =  "Slope = %s; Y-int = %s" %(slope,yintercept)
    try:
        r.plot(x=x_vals[0], y=y_vals, xlab="X", ylab="Y", sub=sub_title, main="Scatterplot with regression")
        r.abline(a=yintercept, b=slope, col="red")
    except:
        pass
else:
    r.pairs(dat, main="Scatterplot Matrix", col="blue")
try:
    r.plot(linear_model)
except:
    pass
r.dev_off()

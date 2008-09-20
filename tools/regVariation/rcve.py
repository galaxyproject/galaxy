#!/usr/bin/env python

from galaxy import eggs

import sys, string
from rpy import *
import numpy

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def sscombs(s):
    if len(s) == 1:
        return [s]
    else:
        ssc = sscombs(s[1:])
        return [s[0]] + [s[0]+comb for comb in ssc] + ssc


infile = sys.argv[1]
y_col = int(sys.argv[2])-1
x_cols = sys.argv[3].split(',')
outfile = sys.argv[4]

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
    """
    try:
        float( elems[x_cols[k]] )
    except:
        try:
            msg = "This operation cannot be performed on non-numeric column %d containing value '%s'." %( col, elems[x_cols[k]] )
        except:
            msg = "This operation cannot be performed on non-numeric data."
        stop_err( msg )
    """
NA = 'NA'
for ind,line in enumerate( file( infile )):
    if line and not line.startswith( '#' ):
        try:
            fields = line.split("\t")
            try:
                yval = float(fields[y_col])
            except Exception, ey:
                yval = r('NA')
                #print >>sys.stderr, "ey = %s" %ey
            y_vals.append(yval)
            for k,col in enumerate(x_cols):
                try:
                    xval = float(fields[col])
                except Exception, ex:
                    xval = r('NA')
                    #print >>sys.stderr, "ex = %s" %ex
                x_vals[k].append(xval)
        except:
            pass

x_vals1 = numpy.asarray(x_vals).transpose()
dat= r.list(x=array(x_vals1), y=y_vals)

set_default_mode(NO_CONVERSION)
try:
    full = r.lm(r("y ~ x"), data= r.na_exclude(dat))    #full model includes all the predictor variables specified by the user
except RException, rex:
    stop_err("Error performing linear regression on the input data.\nEither the response column or one of the predictor columns contain no numeric values.")
set_default_mode(BASIC_CONVERSION)

summary = r.summary(full)
fullr2 = summary.get('r.squared','NA')

if fullr2 == 'NA':
    stop_error("Error in linear regression")

if len(x_vals) < 10:
    s = ""
    for ch in range(len(x_vals)):
        s += str(ch)
else:
    stop_err("This tool only works with less than 10 predictors.")

print >>fout, "#Model\tR-sq\tRCVE_Terms\tRCVE_Value"
all_combos = sorted(sscombs(s), key=len)
all_combos.reverse()
for j,cols in enumerate(all_combos):
    #if len(cols) == len(s):    #Same as the full model above
    #    continue
    if len(cols) == 1:
        x_vals1 = x_vals[int(cols)]
    else:
        x_v = []
        for col in cols:
            x_v.append(x_vals[int(col)])
        x_vals1 = numpy.asarray(x_v).transpose()
    dat= r.list(x=array(x_vals1), y=y_vals)
    set_default_mode(NO_CONVERSION)
    red = r.lm(r("y ~ x"), data= dat)    #Reduced model
    set_default_mode(BASIC_CONVERSION)
    summary = r.summary(red)
    redr2 = summary.get('r.squared','NA')
    try:
        rcve = (float(fullr2)-float(redr2))/float(fullr2)
    except:
        rcve = 'NA'
    col_str = ""
    for col in cols:
        col_str = col_str + str(int(x_cols[int(col)]) + 1) + " "
    col_str.strip()
    rcve_col_str = ""
    for col in s:
        if col not in cols:
            rcve_col_str = rcve_col_str + str(int(x_cols[int(col)]) + 1) + " "
    rcve_col_str.strip()
    if len(cols) == len(s):    #full model
        rcve_col_str = "-"
        rcve = "-"
    try:
        redr2 = "%.4f" %(float(redr2))
    except:
        pass
    try:
        rcve = "%.4f" %(float(rcve))
    except:
        pass
    print >>fout, "%s\t%s\t%s\t%s" %(col_str,redr2,rcve_col_str,rcve)

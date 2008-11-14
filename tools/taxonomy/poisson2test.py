#!/usr/local/bin/python

import sys
from math import *
from rpy import *


if ((len(sys.argv)-1) != 6):
    print 'too few parameters' 
    print 'usage: inputfile, col1, col2, d-value(not 0), p-val correction method(0 or 1)'
    sys.exit()
    
try:
    lines_arr = open(sys.argv[1]).readlines()
except IOError:
    print'cannot open',sys.argv[1]
    sys.exit()  
 
try:
    i = int(sys.argv[2]) #first column to compare
    j = int(sys.argv[3]) #second colum to compare
    d = float(sys.argv[4]) #correction factor
    k = int(sys.argv[5]) #p-val correction method
    outfile = open(sys.argv[6],'w') # output data
    
    if (i>j):
        print 'column order not correct col1 < col2'
        print 'usage: inputfile, col1, col2, d-value, p-val correction method'
        sys.exit()      
        
    try:
        a = 1 / d
        assert k in [0,1]
    except ZeroDivisionError:
        print 'd cannot be 0'
        print 'usage: inputfile, col1, col2, d-value, p-val correction method'
        sys.exit()
    except:
        print ' p-val correction should be 0 or 1 (0 = "bonferroni", 1 = "fdr")'
        print 'usage: inputfile, col1, col2, d-value, p-val correction method'
        sys.exit()
except ValueError:
    print 'parameters are not integers'
    print 'usage: inputfile, col1, col2, d-value, p-val correction method'
    sys.exit()
   

fsize = len(lines_arr)

z1 = []
z2 = []
pz1 = []
pz2 = []
field = []

if d<1: # Z score calculation
    for line in lines_arr:
        line.strip()
        field = line.split('\t')
        
        x = int(field[j-1]) #input column 2
        y = int(field[i-1]) #input column 1
        if y>x:
            z1.append(float((y - ((1/d)*x))/sqrt((1/d)*(x + y))))
            z2.append(float((2*(sqrt(y+(3/8))-sqrt((1/d)*(x+(3/8)))))/sqrt(1+(1/d))))
        else:
            tmp_var1 = x
            x = y
            y = tmp_var1
            z1.append(float((y - (d*x))/sqrt(d*(x + y))))
            z2.append(float((2*(sqrt(y+(3/8))-sqrt(d*(x+(3/8)))))/sqrt(1+d)))
            
else: #d>1 Z score calculation
    for line in lines_arr:
        line.strip()
        field = line.split('\t')
        x = int(field[i-1]) #input column 1
        y = int(field[j-1]) #input column 2
        
        if y>x:
            z1.append(float((y - (d*x))/sqrt(d*(x + y))))
            z2.append(float((2*(sqrt(y+(3/8))-sqrt(d*(x+(3/8)))))/sqrt(1+d)))
        else:
            tmp_var2 = x
            x = y
            y = tmp_var2
            z1.append(float((y - ((1/d)*x))/sqrt((1/d)*(x + y))))
            z2.append(float((2*(sqrt(y+(3/8))-sqrt((1/d)*(x+(3/8)))))/sqrt(1+(1/d))))
        
  
   


# P-value caluculation for z1 and z2
for p in z1:
    
    pz1.append(float(r.pnorm(-abs(float(p)))))

for q in z2:
    
    pz2.append(float(r.pnorm(-abs(float(q)))))    

# P-value correction for pz1 and pz2

if k == 0:
    corrz1 = r.p_adjust(pz1,"bonferroni",fsize)
    corrz2 = r.p_adjust(pz2,"bonferroni",fsize)
  
   
else:
  
    corrz1 = r.p_adjust(pz1,"fdr",fsize)
    corrz2 = r.p_adjust(pz2,"fdr",fsize)
    

#printing all columns
for n in range(fsize):
    print >> outfile, "%s\t%4.3f\t%4.3f\t%8.6f\t%8.6f\t%8.6f\t%8.6f" %(lines_arr[n].strip(),z1[n],z2[n],pz1[n],pz2[n],corrz1[n],corrz2[n])


      
      
      
          

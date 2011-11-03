#!/usr/bin/env python
"""

usage: %prog bed_file_1 bed_file_2 out_file
    -1, --cols1=N,N,N,N: Columns for chr, start, end, strand in first file
    -2, --cols2=N,N,N,N,N: Columns for chr, start, end, strand, name/value in second file
"""
from galaxy import eggs

import collections
import sys, string
#import numpy
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
import sys, traceback, fileinput
from warnings import warn
from galaxy.tools.util.galaxyops import *
from bx.cookbook import doc_optparse


#export PYTHONPATH=~/galaxy/lib/
#running command python WeightedAverage.py interval_interpolate.bed value_interpolate.bed interpolate_result.bed

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def FindRate(chromosome,start_stop,dictType):
    OverlapList=[]
    for tempO in dictType[chromosome]:
        DatabaseInterval=[tempO[0],tempO[1]]
        Overlap=GetOverlap(start_stop,DatabaseInterval)
        if Overlap>0:
            OverlapList.append([Overlap,tempO[2]])
                                 
    if len(OverlapList)>0:
   
        SumRecomb=0
        SumOverlap=0
        for member in OverlapList:
            SumRecomb+=member[0]*member[1]
            SumOverlap+=member[0]    
        averageRate=SumRecomb/SumOverlap
                               
        return averageRate
                               
    else:
        return 'NA'
                                                       
                           
    
def GetOverlap(a,b):
    return min(a[1],b[1])-max(a[0],b[0])

options, args = doc_optparse.parse( __doc__ )

try:
    chr_col_1, start_col_1, end_col_1, strand_col1 = parse_cols_arg( options.cols1 )
    chr_col_2, start_col_2, end_col_2, strand_col2, name_col_2 = parse_cols_arg( options.cols2 )      
    input1, input2, input3 = args
except Exception, eee:
    print eee
    stop_err( "Data issue: click the pencil icon in the history item to correct the metadata attributes." )
    


fd2=open(input2)
lines2=fd2.readlines()
RecombChrDict=collections.defaultdict(list)

skipped=0
for line in lines2:
    temp=line.strip().split()
    try:
        assert float(temp[int(name_col_2)])
    except:
        skipped+=1
        continue
    tempIndex=[int(temp[int(start_col_2)]),int(temp[int(end_col_2)]),float(temp[int(name_col_2)])]
    RecombChrDict[temp[int(chr_col_2)]].append(tempIndex)

print "Skipped %d features with invalid values" %(skipped)

fd1=open(input1)
lines=fd1.readlines()
finalProduct=''
for line in lines:
    temp=line.strip().split('\t')
    chromosome=temp[int(chr_col_1)]
    start=int(temp[int(start_col_1)])
    stop=int(temp[int(end_col_1)])
    start_stop=[start,stop]
    RecombRate=FindRate(chromosome,start_stop,RecombChrDict)
    try:
        RecombRate="%.4f" %(float(RecombRate))
    except:
        RecombRate=RecombRate
    finalProduct+=line.strip()+'\t'+str(RecombRate)+'\n'
fdd=open(input3,'w')
fdd.writelines(finalProduct)
fdd.close()

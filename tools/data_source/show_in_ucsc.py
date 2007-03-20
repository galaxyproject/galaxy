#!/usr/bin/env python2.4
"""
Tool to display multiple datasets at the UCSC genome browser at a time, along with their custom track details. 
Done by: Guru
"""

import sys,os, urllib

outfile=sys.argv[len(sys.argv)-1]	#.split('/')[3]
inputs = []

#PROCESS THE INPUTS TO GET THE DATASET IDs
i=1
while i < len(sys.argv)-1:
	if sys.argv[i].count("/") != 0:
		inputs.append(sys.argv[i].split('/')[3].split('_')[1].split('.')[0])
	else:
		inputs.append(sys.argv[i].replace(',','').replace("]",'').replace("[",""))
	i+=1


#Get unique dataset IDs
inputs.sort()
unique_inp = []
for inp in inputs:
	if (not(inp in unique_inp)):       
		unique_inp.append(inp)

#Read from the url to output buffer
output=""	
for inp in unique_inp:
	sock = urllib.urlopen("http://test.g2.bx.psu.edu/display_custom_bed?id="+inp)	#URL Hardcoded
	htmlSource = sock.read() 
	sock.close() 
	output = output + htmlSource + "\n"

#Write the output into the output file
fout=open(outfile,"w")
print >>fout, output
fout.close()

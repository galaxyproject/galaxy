#!/usr/bin/env python2.4
"""
Tool to display multiple datasets at the UCSC genome browser at a time, along with their custom track details. 
Done by: Guru
"""

import sys,os

primary = sys.argv[2]
color_list = [sys.argv[3].replace('-',',')]
visib_list = [sys.argv[4]]

if sys.argv[5]:
	for color in sys.argv[5].split(','):
		color_list.append(color.replace('-',','))

if sys.argv[6]:
	visib_list.extend(sys.argv[6].split(","))
					   
#visib_list = [sys.argv[4], sys.argv[6]]
input_list = []
input_list.append(primary)

name_list = [sys.argv[7].replace("_NAME_","").replace("_SPACE_"," ").replace("_OPEN_","(").replace("_CLOSE_",")")]
i=8
for item in sys.argv[8:]:
	if item.count("_NAME_") != 0 or item == "customTrack2.bed":
		item=item.replace("_NAME_","").replace("_SPACE_"," ").replace("_OPEN_","(").replace("_CLOSE_",")")
		for sym in ["(u__sq__","u__sq__","__sq__,","__sq__)","__sq__","__ob__", "__cb__"]:
			item = item.replace(sym, "")
		name_list.append(item)
		i+=1
	else:
		break	

for item in sys.argv[i:]:	
	if item.count("/") == 0:
		item = item.replace(',','').replace("]",'').replace("[","")
		try:
			assert int(item)
			item = "./database/files/dataset_" + item + ".dat"
		except:
			pass
	input_list.append(item)

out=[]
if color_list[1] == 'None':
	color_list.pop()
	visib_list.pop()
	j=1
	while j < len(input_list):
		color_list.append('0,0,0')
		visib_list.append('1')
		j+=1

fout = open(sys.argv[1],"w")
for k,inp in enumerate(input_list):
	print >>fout, "track name='%s' visibility=%d color=%s" %(name_list[k],int(visib_list[k]),color_list[k])
	print >>fout, open(inp,"r").read()
fout.close()

print "Display %d tracks in UCSC" %(len(input_list))




#! /usr/bin/python
# this is a tool that creates new row/s
import sys, sets, re

def get_wrap_func(value):
    try:
        check = float(value)
        return 'float(%s)'
    except:
        return 'str(%s)'

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

# we expect 5 parameters
if len(sys.argv) != 5:
    print sys.argv
    stop_err('Usage: python get_flanks.py input out_file size direction')


inp_file  = sys.argv[1]
out_file  = sys.argv[2]
size = int(sys.argv[3])
direction = sys.argv[4]



elems = []
newline = ""

for line in open ( inp_file ):
    line = line.strip()
    if line and not line.startswith( '#' ):
        elems = line.split( '\t' )
	if direction == "up":
		if elems[5] == '+':
		    elems[1] = int(elems[1]) - size
		    elems[2] = int(elems[1]) + size
		    newline = newline + elems[0] + '\t' + str(elems[1]) + '\t' + str(elems[2]) + '\t' + elems[3] + '\t' + elems[4] + '\t' + elems[5] + '\n'
		elif elems[5] == '-':
		    elems[1] = elems[2]
		    elems[2] = int(elems[2]) + size
		    newline = newline + elems[0] + '\t' + elems[1] + '\t' + str(elems[2]) + '\t' + elems[3] + '\t' + elems[4] + '\t' + elems[5] + '\n'

	elif direction == "down":
		if elems[5] == '-':
		    elems[1] = int(elems[1]) - size
		    elems[2] = int(elems[1]) + size
		    newline = newline + elems[0] + '\t' + str(elems[1]) + '\t' + str(elems[2]) + '\t' + elems[3] + '\t' + elems[4] + '\t' + elems[5] + '\n'
		elif elems[5] == '+':
		    elems[1] = elems[2]
		    elems[2] = int(elems[2]) + size
		    newline = newline + elems[0] + '\t' + elems[1] + '\t' + str(elems[2]) + '\t' + elems[3] + '\t' + elems[4] + '\t' + elems[5] + '\n'
		   	    
	elif direction == "both":
		newelem1 = int(elems[1]) - size
		newelem2 = elems[1]
		newelem3 = elems[2]
		newelem4 = int(elems[2]) + size
		newline1 = elems[0] + '\t' + str(newelem1) + '\t' + newelem2 + '\t' + elems[3] + '\t' + elems[4] + '\t' + elems[5] + '\n'
		newline2 = elems[0] + '\t' + newelem3 + '\t' + str(newelem4) + '\t' + elems[3] + '\t' + elems[4] + '\t' + elems[5] + '\n'
		newline = newline + newline1 + newline2 
	
    
    elif line == "":
        break

if not elems:
    stop_err('Empty file?')    

if len(elems) == 1:
    if len(line.split()) != 1:
        stop_err('This tool can only be run on tab delimited files')


#
# create output
#
try:
    fo = open(out_file,'w')
except:
    print >> sys.stderr, "Unable to open output file"
    sys.exit(0)
fo.write(newline)
fo.close()





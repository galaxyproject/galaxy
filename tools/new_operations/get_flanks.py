#! /usr/bin/python
# this is a tool that creates new row/s
#Done by: Guru
import sys, sets, re, os

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

"""
Determine the number of columns in the input file and the data type for each
"""
elems = []
if os.path.exists( inp_file ):
    for line in open( inp_file ):
        line = line.strip()
        if line and not line.startswith( '#' ):
            elems = line.split( '\t' )
            break
else:
    stop_err('The input data file "%s" does not exist.' % inp_file)

if not elems:
    stop_err('No non-blank or non-comment lines in input data file "%s"' % inp_file)    

if len(elems) < 3:
    if len(line.split()) != 1:
        stop_err('This tool can only be run on tab delimited files')



cols = []
for ind, elem in enumerate(elems):
    name = 'c%d' % ( ind + 1 )
    cols.append(name)
    
col = ', '.join(cols)
assign = "%s = line.split('\\t')" % col

if len(elems) < 6:
    strand = '+'
else:
    strand = elems[5]

elems = []
newline=''
newline1=''
newline2=''

#newline = newline + elems[0] + '\\t' + str(elems[1]) + '\\t' + str(elems[2]) + '\\t' + elems[3] + '\\t' + elems[4] + '\\t' + elems[5] + '\\n'
#newline = newline + elems[0] + '\\t' + elems[1] + '\\t' + str(elems[2]) + '\\t' + elems[3] + '\\t' + elems[4] + '\\t' + elems[5] + '\\n'
            
code = """
for line in open ( inp_file ):
    line = line.strip()
    if line and not line.startswith( '#' ):
        elems = line.split( '\\t' )
        if direction == 'up':
            if strand == '+':
                elems[2] = int(elems[1])
                elems[1] = int(elems[1]) - size
            elif strand == '-':
                elems[1] = elems[2]
                elems[2] = int(elems[2]) + size
            for elem in elems:
                newline = newline + str(elem) + '\\t'
            newline = newline.strip() + '\\n'
        elif direction == 'down':
            if strand == '-':
                elems[2] = int(elems[1])
                elems[1] = int(elems[1]) - size
            elif strand == '+':
                elems[1] = elems[2]
                elems[2] = int(elems[2]) + size
            for elem in elems:
                newline = newline + str(elem) + '\\t'
            newline = newline.strip() + '\\n'
    	elif direction == 'both':
            newelem1 = int(elems[1]) - size
            newelem2 = elems[1]
            newelem3 = elems[2]
            newelem4 = int(elems[2]) + size
            elems[1]=newelem1
            elems[2]=newelem2
            newline1=''
            for elem in elems:
                newline1 = newline1 + str(elem) + '\\t' #elems[0] + '\\t' + str(newelem1) + '\\t' + newelem2 + '\\t' + elems[3] + '\\t' + elems[4] + '\\t' + elems[5] + '\\n'
            elems[1]=newelem3
            elems[2]=newelem4
            newline2=''
            for elem in elems:
                newline2 = newline2 + str(elem) + '\\t' #newline2 = elems[0] + '\\t' + newelem3 + '\\t' + str(newelem4) + '\\t' + elems[3] + '\\t' + elems[4] + '\\t' + elems[5] + '\\n'
            newline = newline + newline1.strip() + '\\n' + newline2.strip() + '\\n'  
	
    elif line == '':
        break
"""

exec code

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





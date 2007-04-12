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
Determine the number of columns in the input file
"""
elems = []
if os.path.exists( inp_file ):
    for line in open( inp_file ):
        line = line.strip()
        if line and not line.startswith( '#' ):
            elems = line.split( '\t' )
            break
else:
    print 'The input file does not exist.'
    sys.exit()

if not elems:
    print 'No non-blank or non-comment lines in the input data file'
    sys.exit()
    
if len(elems) < 3:
    if len(line.split()) != 1:
        print 'This tool can only be run on tab delimited data'
        sys.exit()

if len(elems) < 6:
    strand = '+'
else:
    strand = elems[5]

try:
    fo = open(out_file,'w')
except:
    print >> sys.stderr, "Unable to open output file"
    sys.exit()

skipped_lines = 0
first_invalid_line = 0
invalid_line = None
elems = []
for i, line in enumerate( open( inp_file )):
    line = line.strip()
    if line and (not line.startswith( '#' )) and line != '':
        try:
            elems = line.split( '\t' )
            if direction == 'up':
                if strand == '+':
                    elems[2] = elems[1]
                    elems[1] = str(int(elems[1]) - size)
                elif strand == '-':
                    elems[1] = elems[2]
                    elems[2] = str(int(elems[2]) + size)
                print >>fo, '\t'.join(elems)
                
            elif direction == 'down':
                if strand == '-':
                    elems[2] = elems[1]
                    elems[1] = str(int(elems[1]) - size)
                elif strand == '+':
                    elems[1] = elems[2]
                    elems[2] = str(int(elems[2]) + size)
                print >>fo, '\t'.join(elems)
            
            elif direction == 'both':
                newelem1 = str(int(elems[1]) - size)
                newelem2 = elems[1]
                newelem3 = elems[2]
                newelem4 = str(int(elems[2]) + size)
                elems[1]=newelem1
                elems[2]=newelem2
                print >>fo, '\t'.join(elems)
                elems[1]=newelem3
                elems[2]=newelem4
                print >>fo, '\t'.join(elems)
                
        except:
            skipped_lines += 1
            if not invalid_line:
                first_invalid_line = i + 1
                invalid_line = line

fo.close()

if direction == 'up':
    direction = "Upstream"
elif direction == 'down':
    direction = "Downstream"

print 'Flank length : %d and location : %s ' %(size, direction)
if skipped_lines > 0:
    print '(Data issue: skipped %d invalid lines starting at line #%d which is "%s")' % ( skipped_lines, first_invalid_line, invalid_line )
    







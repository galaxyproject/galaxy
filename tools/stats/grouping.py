#!/usr/bin/env python
#Guruprasad Ananda
"""
This tool provides the SQL "group by" functionality.
"""
import sys, string, re, commands, tempfile
from rpy import *

fout = open(sys.argv[1], "w")
inputfile = sys.argv[2]

ops = []
cols = []
for var in sys.argv[4:]:
    ops.append(var.split()[0])
    cols.append(var.split()[1])

groupcol = string.atoi(sys.argv[3])
if groupcol > len( open(inputfile).readline().split('\t') ):
    print >> sys.stderr, "Column %d does not exist." %(groupcol)
    sys.exit()
groupcol = groupcol-1

for k,col in enumerate(cols):
    col = int(col)
    flds = open(inputfile).readline().split('\t')
    if col > len( flds ):
        print >> sys.stderr, "Column %d does not exist." %(col)
        sys.exit()
    else:
        if ops[k] != "c":
            try:
                assert float(flds[col-1])
            except:
                print >> sys.stderr, "Operation '%s' cannot be performed on non-numeric column %d." %(ops[k],col)
                sys.exit()

tmpfile = tempfile.NamedTemporaryFile()   
try:
    commandline = "sort -f "+"+"+str(groupcol)+" -o "+tmpfile.name+" "+inputfile
except Exception, exc:
    print >>sys.stdout, 'Initialization error -> %s' % exc
    sys.exit()
errorcode, stdout = commands.getstatusoutput(commandline)

previtem = ""
prevvals = []
skipped_lines = 0
first_invalid_line = 0
invalid_line = None

for line in open(tmpfile.name):
    fields = line.split("\t")
    item = fields[groupcol]
    if previtem != "":
        if item == previtem:    #Keep iterating and storing values till a new item is encountered.
            previtem = item
            for i,col in enumerate(cols):
                col = string.atoi(col)
                col = col-1
                prevvals[i].append(fields[col].strip())
        else:   #When a new item is encountered, write the previous item and the corresponding aggregate values into the output file.
            outstr = previtem
            try:
                for i,op in enumerate(ops):
                    rfunc = "r." + op 
                    if op != 'c':
                        for j,elem in enumerate(prevvals[i]):
                            prevvals[i][j] = float(elem)
                        rout = "%.2f" %(eval(rfunc)(prevvals[i]))
                    else:
                        rout = eval(rfunc)(prevvals[i])
                    outstr += "\t" + str(rout)
                print >>fout, outstr
            except:
                skipped_lines += 1
            previtem = item   
            prevvals = [] 
            for col in cols:
                col = string.atoi(col)
                col = col-1
                vallist = []
                vallist.append(fields[col].strip())
                prevvals.append(vallist)
    else:           #visited only once right at the start of the iteration.
        previtem = item
        for col in cols:
            col = string.atoi(col)
            col = col-1
            vallist = []
            vallist.append(fields[col].strip())
            prevvals.append(vallist)

outstr = previtem
for i,op in enumerate(ops):
    rfunc = "r." + op 
    if op != 'c':
        for j,elem in enumerate(prevvals[i]):
            prevvals[i][j] = float(elem)
        rout = "%.2f" %(eval(rfunc)(prevvals[i]))
    else:
        rout = eval(rfunc)(prevvals[i])
    outstr += "\t" + str(rout)
print >>fout, outstr

print "Group by column %d" %(groupcol+1)

#!/usr/bin/env python
#Guruprasad Ananda
"""
This tool provides the SQL "group by" functionality.
"""
import sys, string, re, commands, tempfile
from rpy import *

inputfile = sys.argv[2]

ops = []
cols = []
elems = []

for var in sys.argv[4:]:
    ops.append(var.split()[0])
    cols.append(var.split()[1])

"""
At this point, ops and cols will look something like this:
ops:  ['mean', 'min', 'c']
cols: ['1', '3', '4']
"""

for i, line in enumerate( file ( inputfile )):
    line = line.rstrip('\r\n')
    if len( line )>0 and not line.startswith( '#' ):
        elems = line.split( '\t' )
        break
    if i == 30:
        break # Hopefully we'll never get here...

if len( elems )<1:
    print >> sys.stderr, "The data in your input dataset is either missing or not formatted properly."
    sys.exit()

group_col = int( sys.argv[3] )-1

for k,col in enumerate(cols):
    col = int(col)-1
    if ops[k] != 'c':
        """
        We'll get here only if the user didn't choose 'Concatenate', which is the
        only aggregation function that can be used on columns containing strings.
        """
        try:
            map( float, elems[col] )
        except:
            print >> sys.stderr, "Operation '%s' cannot be performed on non-numeric column %d containing value %s." %(ops[k], col+1, elems[col])
            sys.exit()

tmpfile = tempfile.NamedTemporaryFile()

try:
    """
    The -k option for the Posix sort command is as follows:
    -k, --key=POS1[,POS2]
    start a key at POS1, end it at POS2 (origin 1)
    In other words, column positions start at 1 rather than 0, so 
    we need to add 1 to group_col.
    """
    command_line = "sort -f -k " + str(group_col+1) + " -o " + tmpfile.name + " " + inputfile
except Exception, exc:
    print >> sys.stderr, 'Initialization error -> %s' % exc
    sys.exit()

error_code, stdout = commands.getstatusoutput(command_line)

if error_code != 0:
    print >> sys.stderr, "Sorting input dataset resulted in error: ", error_code, stdout
    sys.exit()
    
prev_item = ""
prev_vals = []
skipped_lines = 0
first_invalid_line = 0
invalid_line = ''
invalid_value = ''
invalid_column = 0
fout = open(sys.argv[1], "w")

for ii, line in enumerate( file( tmpfile.name )):
    if line and not line.startswith( '#' ):
        try:
            fields = line.split("\t")
            item = fields[group_col]
            if prev_item != "":
                """
                At this level, we're grouping on values (item and prev_item) in group_col
                """
                if item == prev_item:
                    """
                    Keep iterating and storing values until a new value is encountered.
                    """
                    for i, col in enumerate(cols):
                        col = int(col)-1
                        valid = True
                        """
                        Before appending the current value, make sure it is numeric if the
                        operation for the column requires it.
                        """
                        if ops[i] != 'c':
                            try:
                                float( fields[col].strip())
                            except:
                                valid = False
                                skipped_lines += 1
                                if not first_invalid_line:
                                    first_invalid_line = ii+1
                                    invalid_value = fields[col]
                                    invalid_column = col+1
                        if valid:
                            prev_vals[i].append(fields[col].strip())
                else:   
                    """
                    When a new value is encountered, write the previous value and the 
                    corresponding aggregate values into the output file.  This works 
                    due to the sort on group_col we've applied to the data above.
                    """
                    out_str = prev_item

                    for i, op in enumerate( ops ):
                        rfunc = "r." + op 
                        if op != 'c':
                            for j, elem in enumerate( prev_vals[i] ):
                                prev_vals[i][j] = float( elem )
                            rout = "%.2f" %( eval( rfunc )( prev_vals[i] ))
                        else:
                            rout = eval( rfunc )( prev_vals[i] )

                        out_str += "\t" + str(rout)

                    print >>fout, out_str

                    prev_item = item   
                    prev_vals = [] 
                    for col in cols:
                        col = int(col)-1
                        val_list = []
                        val_list.append(fields[col].strip())
                        prev_vals.append(val_list)
            else:
                """
                This only occurs once, right at the start of the iteration.
                """
                prev_item = item
                for col in cols:
                    col = int(col)-1
                    val_list = []
                    val_list.append(fields[col].strip())
                    prev_vals.append(val_list)

        except Exception, exc:
            print >> sys.stderr, "Error executing aggregation functions: %s" %exc
            sys.exit()
    else:
        skipped_lines += 1
        if not first_invalid_line:
            first_invalid_line = ii+1

"""
Handle the last grouped value
"""
out_str = prev_item

for i, op in enumerate(ops):
    rfunc = "r." + op 
    if op != 'c':
        for j, elem in enumerate( prev_vals[i] ):
            prev_vals[i][j] = float( elem )
        rout = "%.2f" %( eval( rfunc )( prev_vals[i] ))
    else:
        rout = eval( rfunc )( prev_vals[i] )
        
    out_str += "\t" + str( rout )

print >>fout, out_str

"""
Generate a useful info message.
"""
msg = "--Group by c%d: " %(group_col+1)
for i,op in enumerate(ops):
    if op == 'c':
        op = 'concat'
    msg += op + "[c" + cols[i] + "] "
if skipped_lines > 0:
    msg+= "--skipped %d invalid lines starting with line %d.  Value '%s' in column %d is not numeric." % ( skipped_lines, first_invalid_line, invalid_value, invalid_column )

print msg

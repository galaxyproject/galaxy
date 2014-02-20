#!/usr/bin/env python
# Guruprasad Ananda
# Refactored 2011 to use numpy instead of rpy, Kanwei Li
"""
This tool provides the SQL "group by" functionality.
"""
import sys, commands, tempfile, random
try:
    import numpy
except:
    from galaxy import eggs
    eggs.require( "numpy" )
    import numpy

from itertools import groupby

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def mode(data):
    counts = {}
    for x in data:
        counts[x] = counts.get(x,0) + 1
    maxcount = max(counts.values())
    modelist = []
    for x in counts:
        if counts[x] == maxcount:
            modelist.append( str(x) )
    return ','.join(modelist)
    
def main():
    inputfile = sys.argv[2]
    ignorecase = int(sys.argv[4])
    ops = []
    cols = []
    round_val = []
    data_ary = []
    
    if sys.argv[5] != "None":
        oldfile = open(inputfile,'r')
        oldfilelines = oldfile.readlines()
        newinputfile = "input_cleaned.tsv"
        newfile = open(newinputfile,'w')
        asciitodelete = sys.argv[5].split(',')
        for i in range(len(asciitodelete)):
            asciitodelete[i] = chr(int(asciitodelete[i]))
        for line in oldfilelines:
            if line[0] not in asciitodelete:
                newfile.write(line)
        oldfile.close()
        newfile.close()
        inputfile = newinputfile

    for var in sys.argv[6:]:
        op, col, do_round = var.split()
        ops.append(op)
        cols.append(col)
        round_val.append(do_round)
    """
    At this point, ops, cols and rounds will look something like this:
    ops:  ['mean', 'min', 'c']
    cols: ['1', '3', '4']
    round_val: ['no', 'yes' 'no']
    """

    try:
        group_col = int( sys.argv[3] )-1
    except:
        stop_err( "Group column not specified." )
    
    str_ops = ['c', 'length', 'unique', 'random', 'cuniq', 'Mode'] #ops that can handle string/non-numeric inputs
    
    tmpfile = tempfile.NamedTemporaryFile()
    
    try:
        """
        The -k option for the Posix sort command is as follows:
        -k, --key=POS1[,POS2]
        start a key at POS1, end it at POS2 (origin 1)
        In other words, column positions start at 1 rather than 0, so 
        we need to add 1 to group_col.
        if POS2 is not specified, the newer versions of sort will consider the entire line for sorting. To prevent this, we set POS2=POS1.
        """
        case = ''
        if ignorecase == 1:
            case = '-f' 
        command_line = "sort -t '	' %s -k%s,%s -o %s %s" % (case, group_col+1, group_col+1, tmpfile.name, inputfile)
    except Exception, exc:
        stop_err( 'Initialization error -> %s' %str(exc) )
    
    error_code, stdout = commands.getstatusoutput(command_line)
    
    if error_code != 0:
        stop_err( "Sorting input dataset resulted in error: %s: %s" %( error_code, stdout ))
        
    fout = open(sys.argv[1], "w")
    
    def is_new_item(line):
        try:
            item = line.strip().split("\t")[group_col]
        except IndexError:
            stop_err( "The following line didn't have %s columns: %s" % (group_col+1, line) )
            
        if ignorecase == 1:
            return item.lower()
        return item
        
    for key, line_list in groupby(tmpfile, key=is_new_item):
        op_vals = [ [] for op in ops ]
        out_str = key
        multiple_modes = False
        mode_index = None
        
        for line in line_list:
            fields = line.strip().split("\t")
            for i, col in enumerate(cols):
                col = int(col)-1 # cXX from galaxy is 1-based
                try:
                    val = fields[col].strip()
                    op_vals[i].append(val)
                except IndexError:
                    sys.stderr.write( 'Could not access the value for column %s on line: "%s". Make sure file is tab-delimited.\n' % (col+1, line) )
                    sys.exit( 1 )
                
        # Generate string for each op for this group
        for i, op in enumerate( ops ):
            data = op_vals[i]
            rval = ""
            if op == "mode":
                rval = mode( data )
            elif op == "length":
                rval = len( data )
            elif op == "random":
                rval = random.choice(data)
            elif op in ['cat', 'cat_uniq']:
                if op == 'cat_uniq':
                    data = numpy.unique(data)
                rval = ','.join(data)
            elif op == "unique":
                rval = len( numpy.unique(data) )
            else:
                # some kind of numpy fn
                try:
                    data = map(float, data)
                except ValueError:
                    sys.stderr.write( "Operation %s expected number values but got %s instead.\n" % (op, data) )
                    sys.exit( 1 )
                rval = getattr(numpy, op)( data )
                if round_val[i] == 'yes':
                    rval = round(rval)
                else:
                    rval = '%g' % rval
                        
            out_str += "\t%s" % rval
        
        fout.write(out_str + "\n")
    
    # Generate a useful info message.
    msg = "--Group by c%d: " %(group_col+1)
    for i, op in enumerate(ops):
        if op == 'cat':
            op = 'concat'
        elif op == 'cat_uniq':
            op = 'concat_distinct'
        elif op == 'length':
            op = 'count'
        elif op == 'unique':
            op = 'count_distinct'
        elif op == 'random':
            op = 'randomly_pick'
        
        msg += op + "[c" + cols[i] + "] "
    
    print msg
    fout.close()
    tmpfile.close()

if __name__ == "__main__":
    main()

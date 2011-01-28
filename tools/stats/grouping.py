#!/usr/bin/env python
#Guruprasad Ananda
"""
This tool provides the SQL "group by" functionality.
"""
import sys, string, re, commands, tempfile, random
from rpy import *

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def main():
    inputfile = sys.argv[2]
    ignorecase = int(sys.argv[4])
    ops = []
    cols = []
    rounds = []
    elems = []
    
    for var in sys.argv[5:]:
        ops.append(var.split()[0])
        cols.append(var.split()[1])
        rounds.append(var.split()[2])
    
    if 'Mode' in ops:
        try:
            r.library('prettyR')
        except:
            stop_err('R package prettyR could not be loaded. Please make sure it is installed.')
    
    """
    At this point, ops, cols and rounds will look something like this:
    ops:  ['mean', 'min', 'c']
    cols: ['1', '3', '4']
    rounds: ['no', 'yes' 'no']
    """
    
    for i, line in enumerate( file ( inputfile )):
        line = line.rstrip('\r\n')
        if len( line )>0 and not line.startswith( '#' ):
            elems = line.split( '\t' )
            break
        if i == 30:
            break # Hopefully we'll never get here...
    
    if len( elems )<1:
        stop_err( "The data in your input dataset is either missing or not formatted properly." )
    
    try:
        group_col = int( sys.argv[3] )-1
    except:
        stop_err( "Group column not specified." )
    
    str_ops = ['c', 'length', 'unique', 'random', 'cuniq', 'Mode'] #ops that can handle string/non-numeric inputs
    for k,col in enumerate(cols):
        col = int(col)-1
        if ops[k] not in str_ops:
            # We'll get here only if the user didn't choose 'Concatenate' or 'Count' or 'Count Distinct' or 'pick randmly', which are the
            # only aggregation functions that can be used on columns containing strings.
            try:
                float( elems[col] )
            except:
                try:
                    msg = "Operation '%s' cannot be performed on non-numeric column %d containing value '%s'." %( ops[k], col+1, elems[col] )
                except:
                    msg = "Operation '%s' cannot be performed on non-numeric data." %ops[k]
                stop_err( msg )
    
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
        command_line = "sort -t '	' " + case + " -k" + str(group_col+1) +"," + str(group_col+1) + " -o " + tmpfile.name + " " + inputfile
    except Exception, exc:
        stop_err( 'Initialization error -> %s' %str(exc) )
    
    error_code, stdout = commands.getstatusoutput(command_line)
    
    if error_code != 0:
        stop_err( "Sorting input dataset resulted in error: %s: %s" %( error_code, stdout ))
        
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
            line = line.rstrip( '\r\n' )
            try:
                fields = line.split("\t")
                item = fields[group_col]
                if ignorecase == 1:
                    item = item.lower()
                if prev_item != "":
                    # At this level, we're grouping on values (item and prev_item) in group_col
                    if item == prev_item:
                        # Keep iterating and storing values until a new value is encountered.
                        for i, col in enumerate(cols):
                            col = int(col)-1
                            valid = True
                            # Before appending the current value, make sure it is numeric if the
                            # operation for the column requires it.
                            if ops[i] not in str_ops:
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
                        multiple_modes = False
                        mode_index = None
                        for i, op in enumerate( ops ):
                            if op == 'cuniq':
                                rfunc = "r.c"
                            else:
                                rfunc = "r." + op 
                            if op not in str_ops:
                                for j, elem in enumerate( prev_vals[i] ):
                                    prev_vals[i][j] = float( elem )
                                rout = eval( rfunc )( prev_vals[i] )
                                if rounds[i] == 'yes':
                                    rout = int(round(float(rout)))
                                else:
                                    rout = '%g' %(float(rout))
                            else:
                                if op != 'random':
                                    rout = eval( rfunc )( prev_vals[i] )
                                else:
                                    try:
                                        rand_index = random.randint(0,len(prev_vals[i])-1)  #if the two inputs to randint are equal, it seems to throw a ValueError. This can't be reproduced with the python interpreter in its interactive mode. 
                                    except Exception, ValueError:
                                        rand_index = 0
                                    rout = prev_vals[i][rand_index]
                            
                            if op == 'Mode' and rout == '>1 mode':
                                multiple_modes = True
                                mode_index = i
                            if op == 'unique':
                                rfunc = "r.length" 
                                rout = eval( rfunc )( rout )
                            if op in ['c', 'cuniq']:
                                if op == 'c':
                                    if type(rout) == type([]):
                                        out_str += "\t" + ','.join(rout)
                                    else:
                                        out_str += "\t" + str(rout)
                                else:
                                    if type(rout) == type([]):
                                        out_str += "\t" + ','.join(list(set(rout)))
                                    else:
                                        out_str += "\t" + str(rout)
                            else:
                                out_str += "\t" + str(rout)
                        if multiple_modes and mode_index != None:
                            out_str_list = out_str.split('\t')
                            for val in prev_vals[mode_index]:
                                out_str = '\t'.join(out_str_list[:mode_index+1]) + '\t' + str(val) + '\t' + '\t'.join(out_str_list[mode_index+2:])
                                print >>fout, out_str.rstrip('\t')
                        else:
                            print >>fout, out_str
    
                        prev_item = item   
                        prev_vals = [] 
                        for col in cols:
                            col = int(col)-1
                            val_list = []
                            val_list.append(fields[col].strip())
                            prev_vals.append(val_list)
                else:
                    # This only occurs once, right at the start of the iteration.
                    prev_item = item
                    for col in cols:
                        col = int(col)-1
                        val_list = []
                        val_list.append(fields[col].strip())
                        prev_vals.append(val_list)
    
            except Exception, exc:
                skipped_lines += 1
                if not first_invalid_line:
                    first_invalid_line = ii+1
        else:
            skipped_lines += 1
            if not first_invalid_line:
                first_invalid_line = ii+1
    
    # Handle the last grouped value
    out_str = prev_item
    multiple_modes = False
    mode_index = None
    for i, op in enumerate(ops):
        if op == 'cuniq':
            rfunc = "r.c"
        else:
            rfunc = "r." + op 
        try:
            if op not in str_ops:
                for j, elem in enumerate( prev_vals[i] ):
                    prev_vals[i][j] = float( elem )
                rout = eval( rfunc )( prev_vals[i] )
                if rounds[i] == 'yes':
                    rout = int(round(float(rout)))
                else:
                    rout = '%g' %(float(rout))
            else:
                if op != 'random':
                    rout = eval( rfunc )( prev_vals[i] )
                else:
                    try:
                        rand_index = random.randint(0,len(prev_vals[i])-1)  #if the two inputs to randint are equal, it seems to throw a ValueError. This can't be reproduced with the python interpreter in its interactive mode. 
                    except Exception, ValueError:
                        rand_index = 0
                    rout = prev_vals[i][rand_index]
            
            if op == 'Mode' and rout == '>1 mode':
                multiple_modes = True
                mode_index = i      
            if op == 'unique':
                rfunc = "r.length" 
                rout = eval( rfunc )( rout )  
            if op in ['c','cuniq']:
                if op == 'c':
                    if type(rout) == type([]):
                        out_str += "\t" + ','.join(rout)
                    else:
                        out_str += "\t" + str(rout)
                else:
                    if type(rout) == type([]):
                        out_str += "\t" + ','.join(list(set(rout)))
                    else:
                        out_str += "\t" + str(rout)
            else:
                out_str += "\t" + str( rout )
        except:
            skipped_lines += 1
            if not first_invalid_line:
                first_invalid_line = ii+1
    
    if multiple_modes and mode_index != None:
        out_str_list = out_str.split('\t')
        for val in prev_vals[mode_index]:
            out_str = '\t'.join(out_str_list[:mode_index+1]) + '\t' + str(val) + '\t' + '\t'.join(out_str_list[mode_index+2:])
            print >>fout, out_str.rstrip('\t')
    else:
        print >>fout, out_str
    
    # Generate a useful info message.
    msg = "--Group by c%d: " %(group_col+1)
    for i,op in enumerate(ops):
        if op == 'c':
            op = 'concat'
        elif op == 'length':
            op = 'count'
        elif op == 'unique':
            op = 'count_distinct'
        elif op == 'random':
            op = 'randomly_pick'
        elif op == 'cuniq':
            op = 'concat_distinct'
        msg += op + "[c" + cols[i] + "] "
    if skipped_lines > 0:
        msg+= "--skipped %d invalid lines starting with line %d.  Value '%s' in column %d is not numeric." % ( skipped_lines, first_invalid_line, invalid_value, invalid_column )
    
    print msg

if __name__ == "__main__":
    main()

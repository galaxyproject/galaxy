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
    in_columns = int( sys.argv[5] )
    show_remaining_cols = sys.argv[4]
    
    ops = []
    cols = []
    rounds = []
    elems = []
    
    for var in sys.argv[6:]:
        ops.append(var.split()[0])
        cols.append(var.split()[1])
        rounds.append(var.split()[2])
    
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
    
    for k,col in enumerate(cols):
        col = int(col)-1
        if ops[k] not in ['c', 'length', 'unique', 'random']:
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
        command_line = "sort -f -k " + str(group_col+1) +"," + str(group_col+1) + " -o " + tmpfile.name + " " + inputfile
    except Exception, exc:
        stop_err( 'Initialization error -> %s' %str(exc) )
    
    error_code, stdout = commands.getstatusoutput(command_line)
    
    if error_code != 0:
        stop_err( "Sorting input dataset resulted in error: %s: %s" %( error_code, stdout ))
    
    if show_remaining_cols == 'yes':
        show_cols_list = [1]*in_columns
        show_cols_list[group_col] = 0
        for c in cols:
            c = int(c)-1
            show_cols_list[c] = 0
        #at the end of this, only the indices of the remaining columns will be set to 1
        remaining_cols = [j for j,k in enumerate(show_cols_list) if k==1] #this is the list of remaining column indices
      
    prev_item = ""
    prev_vals = []
    remaining_vals = []
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
                if prev_item != "":
                    # At this level, we're grouping on values (item and prev_item) in group_col
                    if item == prev_item:
                        # Keep iterating and storing values until a new value is encountered.
                        for i, col in enumerate(cols):
                            col = int(col)-1
                            valid = True
                            # Before appending the current value, make sure it is numeric if the
                            # operation for the column requires it.
                            if ops[i] not in ['c','length', 'unique','random']:
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
                        #Store values from all the remaning columns
                        if show_remaining_cols == 'yes':
                            for j, index in enumerate(remaining_cols):
                                remaining_vals[j].append(fields[index].strip())
                    else:   
                        """
                        When a new value is encountered, write the previous value and the 
                        corresponding aggregate values into the output file.  This works 
                        due to the sort on group_col we've applied to the data above.
                        """
                        out_list = ['']*in_columns
                        out_list[group_col] = str(prev_item)
                        
                        for i, op in enumerate( ops ):
                            rfunc = "r." + op 
                            if op not in ['c','length','unique','random']:
                                for j, elem in enumerate( prev_vals[i] ):
                                    prev_vals[i][j] = float( elem )
                                if rounds[i] == 'yes':
                                    rout = "%f" %( eval( rfunc )( prev_vals[i] ))
                                    rout = int(round(float(rout)))
                                else:
                                    rout = "%g" %( eval( rfunc )( prev_vals[i] ))
                                
                            else:
                                if op != 'random':
                                    rout = eval( rfunc )( prev_vals[i] )
                                else:
                                    rand_index = random.randint(0,len(prev_vals[i])-1)
                                    rout = prev_vals[i][rand_index]
                                    
                            if op == 'unique':
                                rfunc = "r.length" 
                                rout = eval( rfunc )( rout )

                            out_list[int(cols[i])-1] = str(rout)
                        
                        if show_remaining_cols == 'yes':
                            for index,el in enumerate(remaining_cols):
                                if index == 0:
                                    try:
                                        random_index = random.randint(0,len(remaining_vals[index])-1)
                                    except:
                                        random_index = 0
                                #pick a random value from each of the remaning columns 
                                rand_out = remaining_vals[index][random_index]
                                out_list[el] = str(rand_out)
                            
                        print >>fout, '\t'.join([elem for elem in out_list if elem != ''])
    
                        prev_item = item   
                        prev_vals = [] 
                        for col in cols:
                            col = int(col)-1
                            val_list = []
                            val_list.append(fields[col].strip())
                            prev_vals.append(val_list)
                        
                        if show_remaining_cols == 'yes':
                            remaining_vals = []
                            for index in remaining_cols:
                                remaining_val_list = []
                                remaining_val_list.append(fields[index].strip())
                                remaining_vals.append(remaining_val_list)
                        
                else:
                    # This only occurs once, right at the start of the iteration.
                    prev_item = item
                    for col in cols:
                        col = int(col)-1
                        val_list = []
                        val_list.append(fields[col].strip())
                        prev_vals.append(val_list)
                    
                    if show_remaining_cols == 'yes':
                        remaining_vals = []
                        for index in remaining_cols:
                            remaining_val_list = []
                            remaining_val_list.append(fields[index].strip())
                            remaining_vals.append(remaining_val_list)
    
            except Exception:
                skipped_lines += 1
                if not first_invalid_line:
                    first_invalid_line = ii+1
        else:
            skipped_lines += 1
            if not first_invalid_line:
                first_invalid_line = ii+1
    
    # Handle the last grouped value
    out_list = ['']*in_columns
    out_list[group_col] = str(prev_item)
    
    for i, op in enumerate(ops):
        rfunc = "r." + op 
        try:
            if op not in ['c','length','unique','random']:
                for j, elem in enumerate( prev_vals[i] ):
                    prev_vals[i][j] = float( elem )
                if rounds[i] == 'yes':
                    rout = '%f' %( eval( rfunc )( prev_vals[i] ))
                    rout = int(round(float(rout)))
                else:
                    rout = '%g' %( eval( rfunc )( prev_vals[i] ))
            else:
                if op != 'random':
                    rout = eval( rfunc )( prev_vals[i] )
                else:
                    rand_index = random.randint(0,len(prev_vals[i])-1)
                    rout = prev_vals[i][rand_index]
                    
            if op == 'unique':
                rfunc = "r.length" 
                rout = eval( rfunc )( rout )    
            out_list[int(cols[i])-1] = str(rout)
        except:
            skipped_lines += 1
            if not first_invalid_line:
                first_invalid_line = ii+1
    if show_remaining_cols == 'yes':
        for index,el in enumerate(remaining_cols):
            if index == 0:
                try:
                    random_index = random.randint(0,len(remaining_vals[index])-1)
                except:
                    random_index = 0
            rand_out = remaining_vals[index][random_index]
            out_list[el] = str(rand_out)
    
    print >>fout, '\t'.join([elem for elem in out_list if elem != ''])
    
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
        msg += op + "[c" + cols[i] + "] "
    if skipped_lines > 0:
        msg+= "--skipped %d invalid lines starting with line %d.  Value '%s' in column %d is not numeric." % ( skipped_lines, first_invalid_line, invalid_value, invalid_column )
    
    print msg

if __name__ == "__main__":
    main()

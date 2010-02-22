#!/usr/bin/env python
#Guruprasad Ananda
"""
Least Common Ancestor tool.
"""
import sys, string, re, commands, tempfile, random

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def main():
    try:
        inputfile = sys.argv[1]
        outfile = sys.argv[2]
        rank_bound = int( sys.argv[3] )
        """
        Mapping of ranks:
        root        :2, 
        superkingdom:3, 
        kingdom     :4, 
        subkingdom  :5, 
        superphylum :6, 
        phylum      :7, 
        subphylum   :8, 
        superclass  :9, 
        class       :10, 
        subclass    :11, 
        superorder  :12, 
        order       :13, 
        suborder    :14, 
        superfamily :15,
        family      :16,
        subfamily   :17,
        tribe       :18,
        subtribe    :19,
        genus       :20,
        subgenus    :21,
        species     :22,
        subspecies  :23,
        """
    except:
        stop_err("Syntax error: Use correct syntax: program infile outfile")
    
    fin = open(sys.argv[1],'r')
    for j, line in enumerate( fin ):
        elems = line.strip().split('\t')
        if len(elems) < 24:
            stop_err("The format of the input dataset is incorrect. Taxonomy datatype should contain at least 24 columns.")
        if j > 30:
            break
        cols = range(1,len(elems))
    fin.close()
       
    group_col = 0
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

    prev_item = ""
    prev_vals = []
    remaining_vals = []
    skipped_lines = 0
    fout = open(outfile, "w")
    block_valid = False
    
    
    for ii, line in enumerate( file( tmpfile.name )):
        if line and not line.startswith( '#' ) and len(line.split('\t')) >= 24: #Taxonomy datatype should have at least 24 columns
            line = line.rstrip( '\r\n' )
            try:
                fields = line.split("\t")
                item = fields[group_col]
                if prev_item != "":
                    # At this level, we're grouping on values (item and prev_item) in group_col
                    if item == prev_item:
                        # Keep iterating and storing values until a new value is encountered.
                        if block_valid:
                            for i, col in enumerate(cols):
                                if col >= 3:
                                    prev_vals[i].append(fields[col].strip())
                                    if len(set(prev_vals[i])) > 1:
                                        block_valid = False
                                        break
                            
                    else:   
                        """
                        When a new value is encountered, write the previous value and the 
                        corresponding aggregate values into the output file.  This works 
                        due to the sort on group_col we've applied to the data above.
                        """
                        out_list = ['']*24
                        out_list[0] = str(prev_item)
                        out_list[1] = str(prev_vals[0][0])
                        out_list[2] = str(prev_vals[1][0])
                        
                        for k, col in enumerate(cols):
                            if col >= 3 and col < 24:
                                if len(set(prev_vals[k])) == 1:
                                    out_list[col] = prev_vals[k][0]
                                else:
                                    break
                        while k < 23:
                            out_list[k+1] = 'n' 
                            k += 1
                        
                        j = 0
                        while True:
                            try:
                                out_list.append(str(prev_vals[23+j][0]))
                                j += 1
                            except:
                                break
                            
                        if rank_bound == 0:     
                            print >>fout, '\t'.join(out_list).strip()
                        else:
                            if ''.join(out_list[rank_bound:24]) != 'n'*( 24 - rank_bound ):
                                print >>fout, '\t'.join(out_list).strip()
                        
                        block_valid = True
                        prev_item = item   
                        prev_vals = [] 
                        for col in cols:
                            val_list = []
                            val_list.append(fields[col].strip())
                            prev_vals.append(val_list)
                        
                else:
                    # This only occurs once, right at the start of the iteration.
                    block_valid = True
                    prev_item = item    #groupby item
                    for col in cols:    #everyting else
                        val_list = []
                        val_list.append(fields[col].strip())
                        prev_vals.append(val_list)
            
            except:
                skipped_lines += 1
        else:
            skipped_lines += 1
            
    # Handle the last grouped value
    out_list = ['']*24
    out_list[0] = str(prev_item)
    out_list[1] = str(prev_vals[0][0])
    out_list[2] = str(prev_vals[1][0])
    
    for k, col in enumerate(cols):
        if col >= 3 and col < 24:
            if len(set(prev_vals[k])) == 1:
                out_list[col] = prev_vals[k][0]
            else:
                break
    while k < 23:
        out_list[k+1] = 'n' 
        k += 1
    
    j = 0
    while True:
        try:
            out_list.append(str(prev_vals[23+j][0]))
            j += 1
        except:
            break
        
    if rank_bound == 0:     
        print >>fout, '\t'.join(out_list).strip()
    else:
        if ''.join(out_list[rank_bound:24]) != 'n'*( 24 - rank_bound ):
            print >>fout, '\t'.join(out_list).strip()
        
    if skipped_lines > 0:
        print "Skipped %d invalid lines." % ( skipped_lines )
    
if __name__ == "__main__":
    main()
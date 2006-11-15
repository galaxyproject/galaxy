#!/usr/bin/env python2.4

# No initialization required.


#return lists of columns available
def get_available_columns( input_filename ):
    rval = []
    elems = []
    
    file_in = open(input_filename, 'r')
    oneline =  file_in.readline()
    if oneline :
        elems = oneline.split('\t')
    file_in.close()
 
    rval.append( ("&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;", "0", True) )
    ncol = len(elems)
    while ncol > 0:
        rval.append( (str(ncol), str(ncol), True) )
	ncol = ncol -1
	
    return rval

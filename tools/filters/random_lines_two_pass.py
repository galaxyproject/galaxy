#!/usr/bin/env python
#Dan Blankenberg
#Selects N random lines from a file and outputs to another file, maintaining original line order
#allows specifying a seed
#does two passes to determine line counts and offsets, and then to output contents

import optparse, random 

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-s', '--seed', dest='seed', action='store', type="string", default=None, help='Set the random seed.' )
    (options, args) = parser.parse_args()
    
    assert len( args ) == 3, "Invalid command line specified."
    
    input = open( args[0] )
    output = open( args[1], 'wb' )
    num_lines = int( args[2] )
    assert num_lines > 0, "You must select at least one line."
    
    if options.seed is not None:
        random.seed( options.seed )
    
    #get line offsets
    line_offsets = []
    while True:
        offset = input.tell()
        if input.readline():
            line_offsets.append( offset )
        else:
            break
    
    total_lines = len( line_offsets )
    assert num_lines <= total_lines, "Error: asked to select more lines (%i) than there were in the file (%i)." % ( num_lines, total_lines )
    
    #get random line offsets
    while len( line_offsets ) > num_lines:
        line_offsets.pop( random.randint( 0, len( line_offsets ) - 1 ) )
    
    #write out random lines
    for line_offset in line_offsets:
        input.seek( line_offset )
        output.write( input.readline() )
    input.close()
    output.close()
    print "Kept %i of %i total lines." % ( num_lines, total_lines )
    if options.seed is not None:
        print 'Used random seed of "%s".' % options.seed
    
if __name__=="__main__": __main__()

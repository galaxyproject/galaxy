#! /usr/bin/python
"""
run megablast for metagenomics data
"""

import sys, os, tempfile

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def __main__():
    
    db_build = sys.argv[1]
    query_filename = sys.argv[2].strip()
    output_filename = sys.argv[3].strip()
    mega_word_size = sys.argv[4]        # -W
    mega_iden_cutoff = sys.argv[5]      # -p
    mega_evalue_cutoff = sys.argv[6]      # -e
    mega_temp_output = tempfile.NamedTemporaryFile().name
    mega_filter = sys.argv[7]           # -F
    GALAXY_DATA_INDEX_DIR = sys.argv[8]
    DB_LOC = "%s/blastdb.loc" % GALAXY_DATA_INDEX_DIR

    # megablast parameters
    try:
        int(mega_word_size)    
    except:
        stop_err('Invalid value for word size')
    try:
        float(mega_iden_cutoff)
    except:
        stop_err('Invalid value for identity cut-off')
    try:
        float(mega_evalue_cutoff)
    except:
        stop_err('Invalid value for Expectation value')

    # prepare the database
    db = {}
    for i, line in enumerate( file( DB_LOC ) ):
        line = line.rstrip( '\r\n' )
        if not line or line.startswith('#'):
            continue
        fields = line.split()
        if len(fields) == 2:
            db[(fields[0])] = fields[1]

    if not db.has_key(db_build):
        stop_err('Cannot locate the target database. Please check your location file.')
    
    # arguments for megablast    
    chunk = db[(db_build)]
    megablast_command = "megablast -d %s -i %s -o %s -m 8 -a 8 -W %s -p %s -e %s -F %s 2>&1" \
        % ( chunk, query_filename, mega_temp_output, mega_word_size, mega_iden_cutoff, mega_evalue_cutoff, mega_filter ) 
        
    try:
        os.system( megablast_command )
    except Exception, e:
        stop_err( str( e ) )

    output = open(output_filename,'w')
    invalid_lines = 0
    for i, line in enumerate( file( mega_temp_output ) ):
        line = line.rstrip( '\r\n' )
        fields = line.split()
        try:
            gi, gi_len = fields[1].split('_')
            new_line = "%s\t%s\t%s\t%s" % ( fields[0], gi, gi_len, '\t'.join( fields[2:] ) )
        except:
            invalid_lines += 1
            new_line = line
        output.write( "%s\n" % new_line )
    output.close()
    
    if invalid_lines:
        print "Skipped %d invalid lines. " % invalid_lines
        
    # megablast generates a file called error.log, if empty, delete it, if not, show the contents
    if os.path.exists( './error.log' ):
        for i, line in enumerate( file( './error.log' ) ):
            line = line.rstrip( '\r\n' )
            print line
        os.remove( './error.log' )
    
if __name__ == "__main__" : __main__()
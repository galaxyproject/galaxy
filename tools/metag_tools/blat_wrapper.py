#! /usr/bin/python

import os, sys, tempfile

def stop_err(msg):
    
    sys.stderr.write(msg)
    sys.stderr.write("\n")
    sys.exit()
    
def check_nib_file( dbkey, GALAXY_DATA_INDEX_DIR ):
    nib_file = "%s/alignseq.loc" % GALAXY_DATA_INDEX_DIR
    nib_path = ''
    nibs = {}
    for i, line in enumerate( file( nib_file ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( "#" ):
            fields = line.split()
            if len( fields ) < 3:
                continue
            if ( fields[0] == 'seq' ):
                nibs[( fields[1] )] = fields[2]
    if nibs.has_key( dbkey ):
        nib_path = nibs[( dbkey )]
    return nib_path

def check_twobit_file( dbkey, GALAXY_DATA_INDEX_DIR ):
    twobit_file = "%s/twobit.loc" % GALAXY_DATA_INDEX_DIR
    twobit_path = ''
    twobits = {}
    for i, line in enumerate( file( twobit_file ) ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( "#" ): 
            fields = line.split()
            if len( fields ) < 2:
                continue
            twobits[( fields[0] )] = fields[1]
    if twobits.has_key( dbkey ):
        twobit_path = twobits[( dbkey )]
    return twobit_path

def __main__():
    # I/O
    source_format = sys.argv[1]        # 0: dbkey; 1: upload file
    target_file = sys.argv[2]
    query_file = sys.argv[3]
    output_file = sys.argv[4]
    
    try:
        test = float(sys.argv[5])
        min_iden = sys.argv[5]
    except:
        stop_err('Invalid value for minimal identity')
    
    try:  
        test = int(sys.argv[6])
        tile_size = sys.argv[6]
        assert test >= 6 and test <= 18
    except:
        stop_err('Invalid value for tile size. DNA word size must be between 6 and 18.')
        
    try:
        test = int(sys.argv[7])
        one_off = sys.argv[7]
    except:
        stop_err('Invalid value for mismatch numbers in the word')
        
    GALAXY_DATA_INDEX_DIR = sys.argv[8]

    all_files = []
    if (source_format == '0'):

        # check target genome
        dbkey = target_file
        if dbkey == '?':
            print >> sys.stdout, "No genome build specified. please check your dataset."
            sys.exit()
        nib_path = check_nib_file( dbkey, GALAXY_DATA_INDEX_DIR )
        twobit_path = check_twobit_file( dbkey, GALAXY_DATA_INDEX_DIR )
        if not os.path.exists( nib_path ) and not os.path.exists( twobit_path ):
            stop_err("No sequences are available for %s, request them by reporting this error." % dbkey)
    
        # check the query file, see whether all of them are legitimate sequence
        if (nib_path and os.path.isdir(nib_path)):
            compress_files = os.listdir(nib_path)
            target_path = nib_path
        elif (twobit_path):
            compress_files = [twobit_path]
            target_path = ""
        else:
            stop_err("Requested genome build has no available sequence.")
            
        for file in compress_files:
            file = target_path + '/' + file
            file = os.path.normpath(file)
            all_files.append(file)
    else:
        all_files = [target_file]
        
    for detail_file_path in all_files:
        output_tempfile = tempfile.NamedTemporaryFile().name
        command = 'blat ' + detail_file_path + ' ' + query_file + ' ' + output_tempfile + ' -oneOff=' + one_off + ' -tileSize=' + tile_size + ' -minIdentity=' + min_iden + ' -mask=lower -noHead -out=pslx 2>&1'
        os.system(command)
        os.system('cat %s >> %s' %(output_tempfile, output_file))
        os.remove(output_tempfile)
        
if __name__ == '__main__': __main__()

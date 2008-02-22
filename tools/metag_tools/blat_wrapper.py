#! /usr/bin/python

import os, sys, tempfile

nib_file = "/depot/data2/galaxy/alignseq.loc"
twobit_file = "/depot/data2/galaxy/twobit.loc"

def check_nib_file( dbkey ):
    nib_path = ''
    nibs = {}
    for line in open( nib_file ):
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

def check_twobit_file( dbkey ):
    twobit_path = ''
    twobits = {}
    for line in open( twobit_file ):
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
    min_iden = sys.argv[5]
    tile_size = sys.argv[6]
    one_off = sys.argv[7]
    
    all_files = []
    if (source_format == '0'):
        # check target genome
        dbkey = target_file
        if dbkey == '?':
            print >> sys.stdout, "No genome build specified. please check your dataset."
            sys.exit()
        nib_path = check_nib_file( dbkey )
        twobit_path = check_twobit_file( dbkey )
        if not os.path.exists( nib_path ) and not os.path.exists( twobit_path ):
            print >> sys.stdout, "No sequences are available for %s, request them by reporting this error." % dbkey
            sys.exit()
    
        # check the query file, see whether all of them are legitimate sequence
        if (nib_path):
            compress_files = os.listdir(nib_path)
            target_path = nib_path
        elif (twobit_path):
            compress_files = twobit_path
            target_path = ""
        else:
            print >> sys.stdout, "Requested genome build has no available sequence."
            sys.exit()
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

if __name__ == '__main__': __main__()

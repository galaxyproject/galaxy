#!/usr/bin/env python

import os, sys, tempfile

assert sys.version_info[:2] >= (2.4)

def stop_err( msg ):
    
    sys.stderr.write( "%s\n" % msg )
    sys.exit()
    

def __main__():
    
    # I/O
    target_path = sys.argv[1]
    infile = sys.argv[2]
    scorefile = sys.argv[3]
    high_score = sys.argv[4]            # -q
    high_len = sys.argv[5]              # -M
    read_len = sys.argv[6]              # -w
    align_len = sys.argv[7]             # -h
    mismatch = sys.argv[8]              # -m
    output_file = sys.argv[9]
    
    try: 
        float(high_score)
    except:
        stop_err('Invalid value for minimal quality score.')

    try:
        int(high_len)
    except:
        stop_err('Invalid value for minimal high quality bases.')
            
    # first guess the read length
    guess_read_len = 0
    seq = ''
    for i, line in enumerate(open(infile)):
        line = line.rstrip('\r\n')
        if line.startswith('>'):
            if seq:
                guess_read_len = len(seq)
                break
        else:
            seq += line
            
    try: 
        test = int(read_len)
        if test == 0:
            read_len = str(guess_read_len)
        else:
            assert test >= 20 and test <= 64
    except:
        stop_err('Invalid value for read length. Must be between 20 and 64.')

    
    try:
        int(align_len)    
    except:
        stop_err('Invalid value for minimal length of a hit.')
    
    try:
        int(mismatch)
    except:
        stop_err('Invalid value for mismatch numbers in an alignment.')
    
    all_files = []
    if os.path.isdir(target_path):
        # check target genome
        fa_files = os.listdir(target_path)
            
        for file in fa_files:
            file = "%s/%s" % ( target_path, file )
            file = os.path.normpath(file)
            all_files.append(file)
    else:
        stop_err("No sequences for %s are available for search, please report this error." %(target_path))
   
    for detail_file_path in all_files:
        output_tempfile = tempfile.NamedTemporaryFile().name
        command = "rmapq -q %s -M %s -h %s -w %s -m %s -Q %s -c %s %s -o %s 2>&1" % ( high_score, high_len, align_len, read_len, mismatch, scorefile, detail_file_path, infile, output_tempfile )
        #print command
        try:
            os.system( command )
        except Exception, e:
            stop_err( str( e ) )

        try:
            assert os.system( 'cat %s >> %s' % ( output_tempfile, output_file ) ) == 0
        except Exception, e:
            stop_err( str( e ) )
        
        try:
            os.remove( output_tempfile )
        except:
            pass

            
if __name__ == '__main__': __main__()

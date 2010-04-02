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
    read_len = sys.argv[3]              # -w
    align_len = sys.argv[4]             # -h
    mismatch = sys.argv[5]              # -m
    output_file = sys.argv[6]
    
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
        #assert test >= 0 and test <= int(0.1*int(read_len))
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
        command = "rmap -h %s -w %s -m %s -c %s %s -o %s 2>&1" % ( align_len, read_len, mismatch, detail_file_path, infile, output_tempfile )
        #print command
        try:
            os.system( command )
        except Exception, e:
            stop_err( str( e ) )

        try:
            os.system( 'cat %s >> %s' % ( output_tempfile, output_file ) )
        except Exception, e:
            stop_err( str( e ) )
        
        try:
            os.remove( output_tempfile )
        except:
            pass
        
        
if __name__ == '__main__': __main__()

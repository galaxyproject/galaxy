#! /usr/bin/python

"""
3. create test files, run functional test
"""

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
    
    try: 
        test = int(read_len)
        assert test >= 20 and test <= 64
    except:
        stop_err('Invalid value for read length. Must be between 20 and 64.')
    
    try:
        int(align_len)    
    except:
        stop_err('Invalid value for minimal length of an alignment.')
    
    try:
        test = int(mismatch)
        assert test >= 0 and test <= int(0.1*int(read_len))
    except:
        stop_err('Invalid value for mismatch numbers in an alignment. Please use a value smaller than %d' % (int(0.1*int(read_len))))
    
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
            assert os.system( command ) == 0
        except:
            stop_err('Execution failed. Please check whether RMAP was installed.')

        try:
            assert os.system( 'cat %s >> %s' % ( output_tempfile, output_file ) ) == 0
        except:
            stop_err('Failed to integrate files.')
        
        try:
            os.remove( output_tempfile )
        except:
            pass
        
        
if __name__ == '__main__': __main__()

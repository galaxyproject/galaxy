#! /usr/bin/python
"""
run megablast for metagenomics data
"""

import sys, os


def stop_err(msg):
    
    sys.stderr.write(msg)
    sys.stderr.write("\n")
    sys.exit()
    

def __main__():
    
    # file I/O
    db_build = sys.argv[1]
    query_filename = sys.argv[2].strip()
    output_filename = sys.argv[3].strip()
    mega_word_size = sys.argv[4]        # -W
    mega_iden_cutoff = sys.argv[5]      # -p
    mega_disc_word = sys.argv[6]        # -t
    
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
        int(mega_disc_word)    
    except:
        stop_err('Invalid value for discontiguous word template')
    
    mega_disc_type = sys.argv[7]        # -N
    mega_filter = sys.argv[8]           # -F
    
    GALAXY_DATA_INDEX_DIR = sys.argv[9]
    DB_LOC = "%s/blastdb.loc" % GALAXY_DATA_INDEX_DIR
        
    # prepare the database
    db = {}
    for i, line in enumerate(file(DB_LOC)):
        line = line.rstrip('\r\n')
        
        if not line: continue
        if line.startswith('#'): continue
        
        fields = line.split()
        if len(fields) == 2:
            db[(fields[0])] = fields[1]
            
    if not db.has_key(db_build):
        stop_err('Cannot locate the target database. Please check your location file.')
    
    # arguments for megablast    
    chunk = db[(db_build)]
    megablast_arguments = ["megablast", "-d", chunk, "-i", query_filename, "-o", output_filename]
    megablast_parameters = ["-m", "8", "-a", "8"]
    megablast_user_inputs = ["-W", mega_word_size, "-p", mega_iden_cutoff, "-t", mega_disc_word, "-N", mega_disc_type, "-F", mega_filter]
    megablast_command = " ".join(megablast_arguments) + " " + " ".join(megablast_parameters) + " " + " ".join(megablast_user_inputs) + " 2>&1" 
        
    try:
        os.system(megablast_command)
    except:
        stop_err('Unable to run megablast. Please make sure megablast is installed and available in the search path.')
    
    # megablast generates a file called error.log, if empty, delete it, if not, show the contents
    if os.path.exists('./error.log'):
        for i, line in enumerate( file('./error.log') ):
            line = line.rstrip('\r\n')
            print line
        os.remove('./error.log')
    
if __name__ == "__main__" : __main__()
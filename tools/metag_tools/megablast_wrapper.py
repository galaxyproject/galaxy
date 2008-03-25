#! /usr/bin/python
"""
run megablast for metagenomics data
"""

import sys, os, tempfile, subprocess
#from megablast_xml_parser import *

def __main__():
    # file I/O
    db_build = sys.argv[1]
    query_filename = sys.argv[2]
    output_filename = sys.argv[3]
    
    # megablast parameters
    mega_word_size = sys.argv[4]        # -W
    mega_iden_cutoff = sys.argv[5]      # -p
    mega_disc_word = sys.argv[6]        # -t
    mega_disc_type = sys.argv[7]        # -N
    mega_filter = sys.argv[8]           # -F
    GALAXY_DATA_INDEX_DIR = sys.argv[9]
    DB_LOC = "%s/blastdb.loc" % GALAXY_DATA_INDEX_DIR
    output_file = open(output_filename, 'w')
    
    # prepare the database
    db = {}
    db_file = open(DB_LOC, "r")
    for i, line in enumerate(db_file):
        line = line.rstrip('\r\n')
        fields = line.split()
        db[(fields[0])] = []
        for j in xrange(1, len(fields)):
            db[(fields[0])].append(fields[j])
    
    # prepare to run megablast
    retcode = subprocess.call('which megablast 2>&1', shell='True')
    if retcode < 0:
        print >> sys.stderr, "Cannot locate megablast."
        sys.exit()
        
    for chunk in db[(db_build)]:
        megablast_arguments = ["megablast", "-d", chunk, "-i", query_filename]
        megablast_parameters = ["-m", "8", "-a", "8"]
        megablast_user_inputs = ["-W", mega_word_size, "-p", mega_iden_cutoff, "-t", mega_disc_word, "-N", mega_disc_type, "-F", mega_filter]
        megablast_command = " ".join(megablast_arguments) + " " + " ".join(megablast_parameters) + " " + " ".join(megablast_user_inputs) + " 2>&1" 
        
        # use Anton's parser
        megablast_output = os.popen(megablast_command)
        #parse_megablast_xml_output(megablast_output,output_file)
        # to avoid reading whole file into memory
        for i, line in enumerate(megablast_output):
            line = line.rstrip('\r\n')
            print >> output_file, line 
        
    output_file.close()
    
    # megablast generates a file called error.log, if empty, delete it, if not, show the contents
    if os.path.exists('./error.log'):
        for i, line in enumerate( file('./error.log') ):
            line = line.rstrip('\r\n')
            print >> sys.stdout, line
        os.remove('./error.log')
    
if __name__ == "__main__" : __main__()
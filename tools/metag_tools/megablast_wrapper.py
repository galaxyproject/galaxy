#! /usr/bin/python
"""
run megablast for metagenomics data
BED format
MAF format
database builds file
usage: %prog database/reference query output output_format
Wen-Yu Chung
"""
import sys, os, tempfile

DB_LOC = "/depot/data2/galaxy/blastdb.loc"

def print_bed_format(fields, file_handle):
    #print " ".join(fields)
    print >> file_handle, "\t".join(fields)
    return 0

def print_maf_format(fields, file_handle):
    score = fields.pop(0)
    print >> file_handle, "a score=%s" %score
    print >> file_handle, "s %s" %" ".join(fields)
    print >> file_handle
    return 0

def parse_megablast_output(filename, output_format, file_handle):
    fields = []
    file_to_be_parsed = open(filename, 'r')
    for i, line in enumerate(file_to_be_parsed):
        line = line.strip('\r\n')
        if (not line.startswith("#")):
            [query_id, subject_id, iden, align_length, mismatches, gaps, q_start, q_end, s_start, s_end, evalue, bit_score] = line.split()
            if (int(s_start) > int(s_end)): 
                strand = "-"
                temp = s_start
                s_start = s_end
                s_end = temp
            else:
                strand = "+"
            if (output_format == "bed"):
                fields = [subject_id, s_start, s_end, query_id, str(0), strand]
                print_bed_format(fields, file_handle)
            else:
                fields = [bit_score, subject_id, s_start, str(int(align_length)-int(gaps)), strand, "srcSize", "text"]
                print_maf_format(fields, file_handle)
    return 0

def __main__():
    # file I/O
    db_build = sys.argv[1]
    query_filename = sys.argv[2]
    output_format = sys.argv[3]
    output_filename = sys.argv[4]
    
    # megablast parameters
    mega_word_size = sys.argv[5]    # -W
    mega_iden_cutoff = sys.argv[6]    # -p
    mega_disc_word = sys.argv[7]        # -t
    mega_disc_type = sys.argv[8]        # -N
    mega_filter = sys.argv[9]        # -F
    
    output_file = open(output_filename, 'w')
    
    # prepare the database
    db = {}
    db_file = open(DB_LOC, "r")
    for i, line in enumerate(db_file):
        line = line.strip('\r\n')
        fields = line.split()
        db[(fields[0])] = []
        for j in xrange(1, len(fields)):
            db[(fields[0])].append(fields[j])
    #print "\n".join(db[(db_build)])
    
    # prepare to run megablast
    #for chunk in db[(db_build)]:
    chunk = db[(db_build)][0]        # test
    if 1:
        megablast_output_file = tempfile.NamedTemporaryFile('w')
        megablast_output_filename = megablast_output_file.name
    
        megablast_arguments = ["/home/wychung/megablast", "-d", chunk, "-i", query_filename, "-o", megablast_output_filename] 
        megablast_parameters = ["-m", "8", "-D", "3", "-a", "1"]
        megablast_user_inputs = ["-W", mega_word_size, "-p", mega_iden_cutoff, "-t", mega_disc_word, "-N", mega_disc_type, "-F", mega_filter]
        megablast_command = " ".join(megablast_arguments) + " " + " ".join(megablast_parameters) + " " + " ".join(megablast_user_inputs) + " 2>&1"
        #print megablast_command
        os.system(megablast_command)
        
        parse_megablast_output(megablast_output_filename, output_format, output_file)
        megablast_output_file.close()
    
    output_file.close()
        
if __name__ == "__main__" : __main__()
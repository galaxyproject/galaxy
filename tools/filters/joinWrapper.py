#!/usr/bin/env python
#Guruprasad Ananda
"""
This tool provides the UNIX "join" functionality.
"""
import sys, os, tempfile

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def main():
    infile1 = sys.argv[1]
    infile2 = sys.argv[2]
    field1 = int(sys.argv[3])
    field2 = int(sys.argv[4])
    mode =sys.argv[5]
    outfile = sys.argv[6]
    
    tmpfile1 = tempfile.NamedTemporaryFile()
    tmpfile2 = tempfile.NamedTemporaryFile()
    
    try:
        #Sort the two files based on specified fields
        os.system("sort -k %d -o %s %s" %(field1, tmpfile1.name, infile1))
        os.system("sort -k %d -o %s %s" %(field2, tmpfile2.name, infile2))
    except Exception, exc:
        stop_err( 'Initialization error -> %s' %str(exc) )
        
    option = ""
    for line in file(tmpfile1.name):
        line = line.strip()
        if line:
            elems = line.split('\t')
            for j in range(1,len(elems)+1):
                if j == 1:
                    option = "1.1"
                else:
                    option = option + ",1." + str(j) 
            break
    
    if mode == "V":
        cmdline = 'join -v 1 -o %s -1 %d -2 %d %s %s | tr " " "\t" > %s' %(option, field1, field2, tmpfile1.name, tmpfile2.name, outfile)
    else:
        cmdline = 'join -o %s -1 %d -2 %d %s %s | tr " " "\t" > %s' %(option, field1, field2, tmpfile1.name, tmpfile2.name, outfile)
    
    try:
        os.system(cmdline) 
    except Exception, exj:
        stop_err('Error joining the two datasets -> %s' %str(exj))
       
if __name__ == "__main__":
    main()

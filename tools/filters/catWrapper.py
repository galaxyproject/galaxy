#!/usr/bin/env python
#By, Guruprasad Ananda.

from galaxy import eggs
import sys, os

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()
    
def main():
    outfile = sys.argv[1]
    infile = sys.argv[2]
    catfiles = sys.argv[3:]
    try:
        fout = open(sys.argv[1],'w')
    except Exxception, ex:
        stop_err("Output file cannot be opened for writing\n" + str(ex))
    try:
        fin = open(sys.argv[2],'r')
    except Exception, ex:
        stop_err("Input file cannot be opened for reading\n" + str(ex))
    cmdline = "cat %s %s > %s" % (infile, ' '.join(catfiles), outfile)
    try:
        os.system(cmdline)
    except Exception, ex:
        stop_err("Error encountered with cat\n" + str(ex))
        
if __name__ == "__main__": main()
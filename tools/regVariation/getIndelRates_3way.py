#!/usr/bin/env python
#Guruprasad Ananda

import sys, os, tempfile, string

assert sys.version_info[:2] >= ( 2, 4 )

fout = open(sys.argv[2],'w')
winsize = int(sys.argv[3])
species_ind = int(sys.argv[4]) 

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def rate_estimator(win, blk_lines, wstart, wend, wspecies):
    inserts = 0.0
    deletes = 0.0
    ilengths = {}    #dict containing lengths of blocks(without gaps) having insertion in wspecies
    dlengths = {}    #dict containing lengths of blocks(without gaps) having deletion in wspecies
    prev_bnum = -1
    for bline in blk_lines:
        items = bline.split('\t')
        bnum = int(items[0])
        bevent = items[1]
        if not(bevent.startswith(wspecies)):
            continue
        if bevent.endswith('insert'):
            inserts += 1
            #Add lengths only if the insert belongs to a new alignment block
            if not(ilengths.has_key(bnum)):
                ilengths[bnum] = int(items[species_ind].split(':')[1])
                #prev_bnum = bnum
        elif bevent.endswith('delete'):
            deletes += 1
            #Add lengths only if the delete belongs to a new alignment block
            if not(dlengths.has_key(bnum)):
                dlengths[bnum] = int(items[species_ind].split(':')[1])
                #prev_bnum = bnum
    try:
        total_ilength = sum(ilengths.values())
        irate = inserts/total_ilength
    except:
        irate = 0
    try:
        total_dlength = sum(dlengths.values())
        drate = deletes/total_dlength
    except:
        drate = 0
    print >>fout, "%s\t%s\t%s\t%s\t%.2e\t%.2e" %(win, wspecies, wstart, wend, irate , drate)
    
def main():
    GALAXY_TMP_FILE_DIR = sys.argv.pop()
    infile = sys.argv[1]
    for i, line in enumerate( file ( infile )):
        line = line.rstrip('\r\n')
        if len( line )>0 and not line.startswith( '#' ):
            elems = line.split( '\t' )
            break
        if i == 30:
            break # Hopefully we'll never get here...
    
    if len( elems ) != 15:
        stop_err( "This tool only works on tabular data output by 'Fetch Indels from 3-way alignments' tool. The data in your input dataset is either missing or not formatted properly." )
    
    wspecies = elems[species_ind].split(':')[0].split('.')[0]
    fin = open(infile, 'r')
    skipped = 0
    blk=0
    win=0
    linestr=""
    sorted_infile = tempfile.NamedTemporaryFile( dir=GALAXY_TMP_FILE_DIR )
    cmdline = "sort -n -k"+str(species_ind+2)+" -o "+sorted_infile.name+" "+infile
    try:
        os.system(cmdline)
    except:
        stop_err("Encountered error while sorting the input file.")
    
    print >>fout, "#Window\tSpecies\tWindow_Start\tWindow_End\tInsertion_Rate\tDeletion_Rate"
    
    for line in sorted_infile.readlines():
        line = line.strip("\r\n")
        if not(line) or line == "":
            continue
        elems = line.split('\t')
        try:
            assert int(elems[0])
            assert len(elems) == 15
        except Exception, eon:
            continue
        
        if not(elems[1].startswith(wspecies)):    #Event doesn't belong to the selected species
            continue
        
        try:
            assert wstart
        except NameError:
            wstart = int(elems[species_ind+1]) - int(elems[species_ind+1])%winsize + 1
            wend = wstart + winsize
        lstart = int(elems[species_ind + 1])
        
        if lstart in range(wstart,wend+1):
            linestr += line.strip()
            linestr += "\n"
        else:
            try:
                win += 1
                blk_lines = linestr.strip().split("\n")
                rate_estimator(str(win), blk_lines, str(wstart), str(wend), wspecies)
                linestr = ""
            except:
                skipped += 1
                pass
            linestr=line.strip()+"\n"
            wstart = int(elems[species_ind+1]) - int(elems[species_ind+1])%winsize + 1
            wend = wstart + winsize
    if linestr != "":
        try:
            win += 1
            blk_lines = linestr.strip().split("\n")
            rate_estimator(str(win), blk_lines, str(wstart), str(wend), wspecies)
        except:
            skipped += 1
            pass
    if skipped:
        print "Skipped %s windows as invalid." %(skipped)
if __name__ == "__main__":
    main()
    
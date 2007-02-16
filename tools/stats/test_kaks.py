#! /usr/bin/python
# this tool computes Ka/Ks ratios for the alignments in the input file
import sys, sets, re, os, tempfile

curdir = os.path.dirname(sys.argv[0])
curdir = os.path.abspath(curdir)

def kaks(blocknum,seqs):
			 
     seqcnt = len(seqs)
     ratio = ""
     #curdir = os.getcwd()
     #print ("curdir = %s", curdir)
     
     workdir = curdir + "/kaks"
     os.chdir(workdir)
   
     try:
         j =0
	 flagmat = []
	 for i in range(seqcnt): flagmat.append([1]*seqcnt)
	 while j < seqcnt-1:
		k = j + 1
		while k < seqcnt: 
			if len(seqs[j].strip()) != len(seqs[k].strip()):
				myratio = "Unequal lengths"
				ratio = str(blocknum) + "\t" + "-" + "\t" + "-" + "\t" + str(myratio) 
				flagmat[j][k] = -1	
				return ratio
			k += 1
		j += 1
	 j=0
	 while j < seqcnt-1:
		k = j + 1
		while k < seqcnt:
	 		flagmat[j][k] = 1
			if ((len(seqs[j]))%3 != 0):
	 			chop = (len(seqs[j]))%3
				seq1 = seqs[j]
				seq2 = seqs[k]
				seq1 = seq1[:-chop]
				seq2 = seq2[:-chop]
				seqs[j] = seq1
				seqs[k] = seq2	
			k += 1
		j += 1


	# create the input file
	 f = open('seqfile', 'w')
	 i=0
	 print >>f, seqcnt, len(seqs[0]), 'I'
         print >>f
	 while i < seqcnt:
	 	print >>f, "name" 
		i += 1
 	 i=0
	 print >>f, 1
	 while i < seqcnt:
		print >>f, seqs[i]
		i += 1
	 f.close()
	
	 
         # run yn00 on the input file 
		 
	 outfile = tempfile.NamedTemporaryFile()
	 cmdline = "./yn00 -s seqfile -o " + outfile.name + " > /dev/null"
	 os.system(cmdline) 	
	 
	 	
	 # compute the Ka/Ks ratio from the output file
	
	 line = ''
	 lines = outfile.readlines()
	 #print ("lines : %s", lines)
	 if len(lines) == 0:
		myratio = "STOP codon encountered" 
		ratio = str(blocknum) + "\t" + "-" + "\t" + "-" + "\t" + str(myratio) 
		return ratio
	 else:
	 	i = 0
		fields = list()
		pairs = seqcnt*(seqcnt-1)/2
		while i != len(lines):
		     if lines[i] ==  'seq. seq.     S       N        t   kappa   omega     dN +- SE    dS +- SE\n':
			 k = 0 
			 ratio=""
			 while k < pairs:
			 	fields.append(lines[i+2+k])
				subfields = fields[k].split()
	     			Ka = subfields[7]
				Ks = subfields[10]
				
				if Ka != 'nan' and Ks != 'nan':
					try:
		    				myratio = float(Ka)/float(Ks)
						myratio = round (myratio, 3)
					except:
						myratio = 'nan'
		    			
		    			ratio = ratio + str(blocknum) + "\t" + subfields[0] + "\t" + subfields[1] + "\t" + str(myratio) + "\n"
				else:
		    			ratio = ratio + str(blocknum) + "\t" + subfields[0] + "\t" + subfields[1] + "\t" + 'nan'+ "\n"
				k+=1
			 break
		     else:
			 i += 1
			 
		
	 outfile.close()
	 
	
     
     finally:
        os.chdir(curdir)
     
    
     return ratio.strip()



if len(sys.argv) != 3:	
	print ("kaks usage: ./test_kaks.py input_file output_file")	    		
	sys.exit()
inp_file  = sys.argv[1]
out_file = sys.argv[2]
fp = open(inp_file)
filestr = fp.read()
blocksep = "\n\n"
j = 0
blocknum = 1
fo = open(out_file, 'w')
filestr = filestr.strip()
blocks = filestr.split(blocksep)

print >> fo, "Block" + "\t" + "Seq" + "\t" + "Seq" + "\t" + "ka/ks ratio"
while j < len(blocks):
    
    sets = blocks[j].split(">")
    sequences = list()
    seqcnt = 1
    while seqcnt < len(sets):
	subset = sets[seqcnt].split("\n")
	
	k=2
    	if k < len(subset):
		subset[1] = subset[1] + subset[k]
		k += 1 
	subset[1]=subset[1].replace(" ","")
	subset[1]=subset[1].replace("\r","")
	subset[1]=subset[1].replace("\t","")	
	sequences.append(subset[1].replace("\n","")) 
    	seqcnt += 1
    if sequences != []:
    	ratio = kaks(j+1,sequences)   # j+1 is the block number
        print >>fo, ratio
    	j += 1
    	blocknum += 1
    else:
	fo.close()
	fo = open(out_file, 'w')
	fo.write("Input error found at block " + str(j+1)+"\n")
	fp.close()
	sys.exit()
fo.close()
fp.close()

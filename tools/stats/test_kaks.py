#! /usr/bin/python
# this tool computes Ka/Ks ratios for the alignments in the input file
import sys, sets, re, os

def kaks(subset1, subset2):

     aligns = [subset1, subset2]
     ratio = 0
     curdir = os.getcwd()
          
     try:
         # create control file
         out = file("yn00.ctl", "w")
         print >>out, "seqfile = seqfile"
         print >>out, "outfile = outfile"
         out.close()

	 if len(subset1) != len(subset2):
	 	ratio = "Error: The two sequences have unequal lengths"	 
		return ratio
	 if ((len(subset2))%3 != 0):
	 	chop = (len(subset2))%3
		subset1 = subset1[:-chop]
		subset2 = subset2[:-chop]

         # create the input file
         f = open('seqfile', 'w')
         print >>f, len(aligns), len(subset2), 'I'
         print >>f
	 print >>f, "name1" +"\n"+ "name2" 
	 print >>f, 1
	 print >>f, subset1+ "\n" + subset2 + "\n"
         f.close()

	 # run yn00 on the input file 
	 os.system("./yn00 yn00.ctl > /dev/null")
	 
	 	
	 # compute the Ka/Ks ratio from the output file
	 f = open('outfile', 'r')
	 line = ''
	 lines = f.readlines()
	 if len(lines) == 0:
		ratio = "Error: One of the sequences contains either a stop codon or invalid character(s)" 
		return ratio
	 else:
	 	i = 0
		fields = ""
		while i != len(lines):
		     if lines[i] ==  'seq. seq.     S       N        t   kappa   omega     dN +- SE    dS +- SE\n':
			 fields = lines[i+2]
			 break
		     else:
			 i += 1
			 
		subfields = fields.split()
	     	Ka = subfields[7]
		Ks = subfields[10]
		if Ka != 'nan' and Ks != 'nan':
		    ratio = float(Ka)/float(Ks)
		    ratio = round (ratio, 2)
		else:
		    ratio = 'nan'
		f.close()
	 
	
     
     finally:
        os.chdir(curdir)
     
     return ratio



if len(sys.argv) != 3:	
	print ("kaks usage: ./test_kaks.py input_file output_file")	    		
	sys.exit()
inp_file  = sys.argv[1]
out_file = sys.argv[2]
fp = open(inp_file)
s1 = fp.read()
sets = s1.split(">")

j = 1
fo = open(out_file, 'w')
while j < len(sets):
    subset1 = sets[j].split("\n")
    subset2 = sets[j+1].split("\n")
    k=2
    if k < len(subset1):
	subset1[1] = subset1[1] + subset1[k]
	k += 1
    k=2
    if k < len(subset2):
	subset2[1] = subset2[1] + subset2[k]
	k += 1	
    subset1[1].replace(" ","")
    subset1[1].replace("\r","")
    subset1[1].replace("\t","")
    subset2[1].replace(" ","")
    subset2[1].replace("\r","")
    subset2[1].replace("\t","")
   
    ratio = kaks(subset1[1].replace("\n",""), subset2[1].replace("\n",""))
    
    print >>fo, "Ka/Ks ratio : " + str(ratio) + "\n>" + sets[j].strip() + "\n>" + sets[j+1].strip() + "\n"
    j += 2
fo.close()
fp.close()

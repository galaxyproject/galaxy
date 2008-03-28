#!/usr/bin/env python
import urllib, sys, os, sets, findcluster_mysql_subs 
from time import time, localtime, strftime
import pkg_resources
pkg_resources.require( "sqlalchemy>=0.2" )
from sqlalchemy import *

assert sys.version_info[:2] >= ( 2, 4 )
      
if __name__ == '__main__':
   nargv = len(sys.argv)
   if nargv < 2 :
      findcluster_mysql_subs.usage()
      sys.exit()
       
   #----------------------------------------------------------------------------------------
   #--------------------------read params and files-----------------------------------------
   genome_name = ''
   chrom_name = ''
   chroms = dict()
   blocks = []
   range = 0
   blkstring = ''
   chrs = []
   ptnstring = ''
   ptns = []
   patterns = []
   wsize = 3500
   shsize = 32
   n = 1
   info_file = 'None'
   while n < nargv :
      #get the genome parameter
      if   sys.argv[n] == "-g" : genome_name = sys.argv[n+1]

      elif sys.argv[n] == "-x" : 
         flag = sys.argv[n+1].split(',')
	 flags=dict()
	 for ff in flag: 
	    flags[ff] = 1
      #get the blocks from input box
      elif sys.argv[n] == "-f" : 
#         if flags.get('f') == 1 : 
         if 1 : 
            while 1: 
	       if sys.argv[n+1][0]!='-': blkstring = blkstring + sys.argv[n+1] + ' '
	       else: break
	       n = n + 1
	    nn = 0
	    while nn < len(blkstring) :
	       if blkstring[nn]=='X' and blkstring[nn+1]=='X' : 
	          blkstring=blkstring[:nn]+' '+blkstring[nn+2:]
	          nn = nn - 2
	       if blkstring[nn]==' ' : 
	          if blkstring[nn-1]!=' ': blkstring=blkstring[:nn]+' '+blkstring[nn+1:] 
	          else : 
	             blkstring=blkstring[:nn]+blkstring[nn+1:]
		     nn = nn - 1
	       nn = nn + 1
	    if len(blkstring) != 0 :  
	       blks = blkstring.strip().split(' ')
	       for blk in blks :
	          block = []
		  start = int(blk.split(':')[1].split('-')[0])
		  end   = int(blk.split(':')[1].split('-')[1])
	          block.append(blk.split(':')[0].split('chr')[1])
	          block.append(start-range)
	          block.append(end+range)
	          blocks.append(block)
	          chroms[blk.split(':')[0].split('chr')[1]] = 1
      #get the blocks from bed file
      elif sys.argv[n] == "-b" : 
#         if flags.get('b')==1 and os.path.exists(sys.argv[n+1]) : 
         if os.path.exists(sys.argv[n+1]) : 
            bed_file = open(sys.argv[n+1], 'r')
	    for line in bed_file.readlines() :
	       block = []
	       start = int(line.split('\t')[1])
	       end   = int(line.split('\t')[2])
	       block.append(line.split('\t')[0].split('chr')[1])
	       block.append(start-range)
	       block.append(end+range)
	       blocks.append(block)
	       chroms[line.split('\t')[0].split('chr')[1]] = 1
      #get the chroms from check box
      elif sys.argv[n] == "-c" : 
         if flags.get('c')==1 and sys.argv[n+1][0]!='-' and sys.argv[n+1]!=None and sys.argv[n+1]!='None':
            chromstmp = sys.argv[n+1].strip('\n').split(',')
	    for  chromtmp in chromstmp:
	       block=[]
	       block.append(chromtmp)
	       block.append(0)
	       block.append(0)
	       blocks.append(block)
               chroms[chromtmp] = 1
      #get the chroms from check box
      elif sys.argv[n] == "-r" : range = int(sys.argv[n+1])
	       
      
      #get the window size and header size. In our program, the header size is fixed to be 32.
      elif sys.argv[n] == "-w" : wsize = int(sys.argv[n+1])
      elif sys.argv[n] == "-s" : shsize = int(sys.argv[n+1])

      #output files
      elif sys.argv[n] == "-o" : out_file = open(sys.argv[n+1], 'w')
      elif sys.argv[n] == "-i" : info_file = open(sys.argv[n+1], 'w')
      elif sys.argv[n] == "-l" : log_file = open(sys.argv[n+1], 'w')

      #get the patterns information
      elif sys.argv[n] == "-p" : 
         while 1: 
	    if sys.argv[n+1][0]!='-': ptnstring = ptnstring + sys.argv[n+1] + ' '
	    else: break
	    n = n + 1
	 nn = 0
	 code = 'ACGTMRWSYKBDHVN0123456789'
	 while nn < len(ptnstring) :
	    if code.find(ptnstring[nn])==-1 : 
	       if ptnstring[nn-1]!=' ': ptnstring=ptnstring[:nn]+' '+ptnstring[nn+1:] 
	       else : 
	          ptnstring=ptnstring[:nn]+ptnstring[nn+1:]
		  nn = nn - 1
	    nn = nn + 1
	 ptns = ptnstring.strip().split(' ')
      n = n + 1
   
   #check the genome, chroms, and ptns not to be empty
   if genome_name=='' or len(chroms)==0 or ptns=='': 
      findcluster_mysql_subs.usage()
      sys.exit()
   
   #---pattern data--------
   patterns = []
   patterns_c = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
   patterns_name = dict()
   combines = dict()
   n = 0
   nptns = len(ptns)/2
   while n < nptns: 
      patterns.append(ptns[2*n])
      combines[ptns[2*n]] =  int(ptns[2*n+1])
      patterns_name[ptns[2*n]] = patterns_c[n]
      n = n + 1

   #restrict the pattern to be longer than 2bp(not include 2)
   code = 'ACGTMRWSYKBDHV'
   for pattern in patterns:
      n = 0
      for c in pattern:
         if code.find(c)!=-1 : n = n + 1
      if n < 3: sys.exit() 
   


   #----------------------------------------------------------------------------------------
   #-------------------------- find clusters -----------------------------------------------
   #--------print bed file header---------
   out_file.write("#1. chrom")
   out_file.write("\n#2. chromStart.Note:The first base in a chromosome is numbered 0.")
   out_file.write("\n#3. chromEnd")
   out_file.write("\n#4. Pattern order. E.g. BABCBD, each letter represents one pattern.")
   out_file.write("\n#5. score. If the track line useScore attribute is set to 1 for this annotation data set, the score value will determine the level of gray.")
   out_file.write("\n#6. strand")
   out_file.write("\n#7. thickStart. The starting position at which the feature is drawn thickly.")
   out_file.write("\n#8. thickEnd. The ending position at which the feature is drawn thickly.")
   out_file.write("\n#9. itemRgb. An RGB value of the form R,G,B (e.g. 255,0,0). If the track line itemRgb is set to 'On', this RBG value will determine the display color. ")
   out_file.write("\n#10. blockCount. The number of blocks (exons) in the BED line.")
   out_file.write("\n#11. blockSizes. A comma-separated list of the block sizes. ")
   out_file.write("\n#12. blockStarts. A comma-separated list of block starts.\n")

   result = dict()
   for chrom_name in chroms.keys() : 
      if chrom_name != '' :
         result[chrom_name] = findcluster_mysql_subs.scan_chromosome(genome_name, chrom_name, blocks, patterns, combines, patterns_name, wsize, shsize, out_file, log_file) 
   
   #----------------------------------------------------------------------------------------
   #-------------------------- print out results -------------------------------------------
   if info_file == 'None' :
      print "%-30s\t" % " ", 
      ii = 0 
      while ii<len(patterns) :
         print patterns_c[ii], "\t", 
         ii = ii + 1
      print "clust\tclust(no-overlap)\n",
      for block in blocks :
         strtmp = block[0]+":"+str(block[1])+"-"+str(block[2])
         print "%-30s\t" % strtmp, 
         for pattern in patterns :
            npos = 0
            for pos in result[block[0]]['M'][pattern]:
               if pos>=block[1] and (pos<=block[2] or block[2]==0) : 
                  npos = npos + 1
            print npos, "\t",
         nclus = 0
         for key in result[block[0]]['NO'].keys() :
            clus = result[block[0]]['NO'][key]
            if clus['start']>=block[1] and ( clus['start']<=block[2] or block[2]==0) or  clus['end']>=block[1] and ( clus['end']<=block[2] or block[2]==0) : 
               nclus = nclus + 1
         print result[chrom_name]['C'], "\t", nclus
      print "Note:\n1)",
      ii = 0 
      while ii<len(patterns) :
         print patterns_c[ii], "-", patterns[ii], "\t",
         ii = ii + 1
      print "\n", 
      print "2) clust - clusters in all the blocks on the curent chromosome"
      print "3) clust(no-overlap) - clusters without overlap in current block"
      
   else: 
      ii = 0 
      info_file.write("%-30s\t" % " ")
      while ii<len(patterns) :
         info_file.write(str(patterns_c[ii])+"\t") 
         ii = ii + 1
      info_file.write("clust\tclust(no-overlap)\n")
      for block in blocks :
         strtmp = block[0]+":"+str(block[1])+"-"+str(block[2])
         info_file.write("%-30s\t" % strtmp) 
         for pattern in patterns :
            npos = 0
            for pos in result[block[0]]['M'][pattern]:
               if pos>=block[1] and (pos<=block[2] or block[2]==0) : 
                  npos = npos + 1
            info_file.write(str(npos)+"\t")
         nclus = 0
         for key in result[block[0]]['NO'].keys() :
            clus = result[block[0]]['NO'][key]
            if clus['start']>=block[1] and ( clus['start']<=block[2] or block[2]==0) or  clus['end']>=block[1] and ( clus['end']<=block[2] or block[2]==0) : 
               nclus = nclus + 1
         info_file.write(str(result[chrom_name]['C'])+"\t"+str(nclus)+"\n")
      info_file.write("Note:\n1) ") 
      ii = 0 
      while ii<len(patterns) :
         info_file.write(str(patterns_c[ii])+"-"+str(patterns[ii])+"\t") 
         ii = ii + 1
      info_file.write(str("\n") )
      info_file.write("2) clust-clusters in all the blocks on the curent chromosome\n")
      info_file.write("3) clust(no-overlap)-clusters without overlap in current block\n")

   """if info_file != 'None' : 
      info_file.write("%-35s\t" % "Chromome arm:")
      for chrom_name in chroms.keys() : 
         if chrom_name != '' :
            info_file.write("%s" % chrom_name)
         info_file.write("\t")
      info_file.write("\n")

      for pattern in patterns :
         info_file.write("Occurrences of site %-s\t" % str(patterns_name[pattern]+"("+pattern+"):"))
         for chrom_name in chroms.keys() : 
            if chrom_name != '' :
               info_file.write("%d\t" % len(result[chrom_name]['M'][pattern]))
         info_file.write("\n")

      info_file.write("%s" % "Clusters satisfying '")
      for pattern in patterns :
         if combines[pattern] != 0 : 
            info_file.write(" %-d%s" % (combines[pattern], patterns_name[pattern]))
      info_file.write(" ':%s\t" % "")
      for chrom_name in chroms.keys() : 
         if chrom_name != '' :
            info_file.write("%d\t" % result[chrom_name]['C'])
      info_file.write("\n")
      
      info_file.write("%-s\t" % "After merging overlapping clusters:")
      for chrom_name in chroms.keys() : 
         if chrom_name != '' :
            info_file.write("%d\t" % len(result[chrom_name]['NO']))
      info_file.write("\n")

   #-------------------------------------------------------------------------------------	 
   else :
      print "%-50s" % "Chromome arm:",   
      for chrom_name in chroms.keys() : 
         if chrom_name != '' :
            print "%10s" % chrom_name, 
      print 
      
      for pattern in patterns :
         print "Occurrences of site %-30s" % str(patterns_name[pattern]+"("+pattern+"):"), 
         for chrom_name in chroms.keys() : 
            if chrom_name != '' :
               print "%10d" % len(result[chrom_name]['M'][pattern]),
         print 
      
      print "%s" % "Clusters satisfying '",
      for pattern in patterns :
         if combines[pattern] != 0 : 
            print "%-d%s" % (combines[pattern], patterns_name[pattern]), 
      print "':%14s" % "", 
      for chrom_name in chroms.keys() : 
         if chrom_name != '' :
            print "%10d" % result[chrom_name]['C'],
      print 
      
      print "%-50s" % "After merging overlapping clusters:",   
      for chrom_name in chroms.keys() : 
         if chrom_name != '' :
            print "%10d" % len(result[chrom_name]['NO']),
      print 
   """

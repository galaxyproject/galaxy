#!/usr/bin/env python2.4
import urllib, sys, os, sets, findcluster_pygre_subs 
from time import time, localtime, strftime
import pkg_resources
pkg_resources.require( "sqlalchemy>=0.2" )
from sqlalchemy import *

      
if __name__ == '__main__':
   nargv = len(sys.argv)
   if nargv < 2 :
      findcluster_pygre_subs.usage()
      sys.exit()
       
   #----------------------------------------------------------------------------------------
   #--------------------------read params and files-----------------------------------------
   genome_name = ''
   chrom_name = ''
   chroms = []
   ptnstring = ''
   ptns = []
   patterns = []
   wsize = 3500
   shsize = 32
   n = 1
   info_file = 'None'
   while n < nargv :
      if sys.argv[n] == "-g" : genome_name = sys.argv[n+1]
      elif sys.argv[n] == "-c" : chroms = sys.argv[n+1].strip('\n').split(',')
      elif sys.argv[n] == "-w" : wsize = int(sys.argv[n+1])
      elif sys.argv[n] == "-s" : shsize = int(sys.argv[n+1])
      elif sys.argv[n] == "-o" : out_file = open(sys.argv[n+1], 'w')
      elif sys.argv[n] == "-i" : info_file = open(sys.argv[n+1], 'w')
      elif sys.argv[n] == "-l" : log_file = open(sys.argv[n+1], 'w')
      #get the patterns information
      elif sys.argv[n] == "-p" : 
         while 1: 
	    if sys.argv[n+1][0]!='-': ptnstring = ptnstring + sys.argv[n+1] + ' '
	    else: break
	    n = n + 1
	 n = n - 1
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
      n = n + 2
   
   #check the genome, chroms, and ptns not to be empty
   if genome_name=='' or chroms=='' or ptns=='': 
      findcluster_pygre_subs.usage()
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

   #restrict the pattern to be longer than 3bp(not include N)
   code = 'ACGTMRWSYKBDHV'
   for pattern in patterns:
      n = 0
      for c in pattern:
         if code.find(c)!=-1 : n = n + 1
      if n < 4: sys.exit() 
   


   #----------------------------------------------------------------------------------------
   #-------------------------- find clusters -----------------------------------------------
   result = dict()
   for chrom_name in chroms : 
      if chrom_name != '' :
         result[chrom_name] = findcluster_pygre_subs.scan_chromosome(genome_name, chrom_name, patterns, combines, patterns_name, wsize, shsize, out_file, log_file) 
   
   #----------------------------------------------------------------------------------------
   #-------------------------- print out results -------------------------------------------
   if info_file != 'None' : 
      info_file.write("%-35s\t" % "Chromome arm:")
      for chrom_name in chroms: 
         if chrom_name != '' :
            info_file.write("%s\t" % chrom_name)
      info_file.write("\n")

      for pattern in patterns :
         info_file.write("Occurrences of site %-s\t" % str(patterns_name[pattern]+"("+pattern+"):"))
         for chrom_name in chroms: 
            if chrom_name != '' :
               info_file.write("%d\t" % len(result[chrom_name]['M'][pattern]))
         info_file.write("\n")

      info_file.write("%s" % "Clusters satisfying '")
      for pattern in patterns :
         if combines[pattern] != 0 : 
            info_file.write(" %-d%s" % (combines[pattern], patterns_name[pattern]))
      info_file.write(" ':%s\t" % "")
      for chrom_name in chroms: 
         if chrom_name != '' :
            info_file.write("%d\t" % result[chrom_name]['C'])
      info_file.write("\n")
      
      info_file.write("%-s\t" % "After merging overlapping clusters:")
      for chrom_name in chroms: 
         if chrom_name != '' :
            info_file.write("%d\t" % len(result[chrom_name]['NO']))
      info_file.write("\n")

   #-------------------------------------------------------------------------------------	 
   else :
      print "%-50s" % "Chromome arm:",   
      for chrom_name in chroms: 
         if chrom_name != '' :
            print "%10s" % chrom_name, 
      print 
      
      for pattern in patterns :
         print "Occurrences of site %-30s" % str(patterns_name[pattern]+"("+pattern+"):"), 
         for chrom_name in chroms: 
            if chrom_name != '' :
               print "%10d" % len(result[chrom_name]['M'][pattern]),
         print 
      
      print "%s" % "Clusters satisfying '",
      for pattern in patterns :
         if combines[pattern] != 0 : 
            print "%-d%s" % (combines[pattern], patterns_name[pattern]), 
      print "':%14s" % "", 
      for chrom_name in chroms: 
         if chrom_name != '' :
            print "%10d" % result[chrom_name]['C'],
      print 
      
      print "%-50s" % "After merging overlapping clusters:",   
      for chrom_name in chroms: 
         if chrom_name != '' :
            print "%10d" % len(result[chrom_name]['NO']),
      print 


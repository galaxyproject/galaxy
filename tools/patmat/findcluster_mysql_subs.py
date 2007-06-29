#!/usr/bin/env python2.4
import sys, os, sets
#import pg
from time import time, localtime, strftime
import pkg_resources
pkg_resources.require( "sqlalchemy>=0.2" )
from sqlalchemy import *
STDERR = sys.stderr

   
#---------------------------------------------------------------------------------------------------
#--------------------sub-functions for findcluster.py----------------------------------------------------

#return genomes available in the datasets
def get_available_data_genomes( ):
   sqlquery = "SELECT distinct genome, genome_desc from genome order by genome_desc"
   db = create_engine('mysql://stree:12345@scofield.bx.psu.edu/stree')
   conn = db.connect()
   matchs = conn.execute(sqlquery)

   available_sets = []
   for match in matchs : 
      available_sets.append( (match[1], match[0], True) )
   available_sets.append( ("---", "---", True) )
   conn.close()
   return available_sets
   
#return chroms available of the genome in the datasets
def get_available_data_chroms( genome ):
   sqlquery = "SELECT chrom from genome where genome= \'%s\' order by chrom" % genome 
   db = create_engine('mysql://stree:12345@scofield.bx.psu.edu/stree')
   conn = db.connect()
   available_sets = []
   
   nn = 1
   while nn < 3 : 
      matchs = conn.execute(sqlquery)
      for match in matchs : 
         if len(match[0]) == nn and match[0].isdigit():
            available_sets.append( (match[0], match[0], True) )
      nn = nn + 1 
   matchs = conn.execute(sqlquery)
   for match in matchs : 
      if not match[0].isdigit():
         available_sets.append( (match[0], match[0], True) )
   conn.close()
   return available_sets


#---------------------------------------------------------------------------------------------------
#--------------------sub-functions for findcluster.py----------------------------------------------------

def usage() : 
   print 'Usage: python findcluster_mysql.py -g dm2 -c 2L -p patterns -w 3500 -s 32 -o out_file -i info_file -l log_file'
   print '  -g   (required) genome name'
   print '  -c   (required) chromosome names, e.g."2L,2R," (seperated by comma) '
   print '  -p   (required) string of patterns, per pattern per line, e.g."AYFGDFGA,2," (seperated by anything but pattern codes and -) '
   print '  -w   (optional) cluster window size(default 3500)'
   print '  -s   (optional) suffix header size(default 32)'
   print '  -o   (required) output file'
   print '  -o   (optional) info file'
   print '  -o   (required) log file'

def sn2num(sn) :
   if sn == 'A' : return 0
   if sn == 'C' : return 1
   if sn == 'G' : return 2
   if sn == 'T' : return 3
   return 4

def dna2num(dna, mdna, bit) :
   nn = 0
   num = [0,0]
   while nn<bit: 
      if nn<mdna : 
         if sn2num(dna[nn]) == 4 : return [0,0]
         num[0] = num[0]*4 + sn2num(dna[nn])
	 num[1] = num[0] + 1 
      else : 
         num[0] = num[0]*4
         num[1] = num[1]*4
      nn = nn + 1
   num[0] = num[0] - 9223372036854775807
   num[1] = num[1] - 9223372036854775807
   return num

def expand_pattern(pattern=[]):
   sl_code     = {'A':'A','C':'C','G':'G','T':'T','M':'AC','R':'AG','W':'AT','S':'CG','Y':'CT','K':'GT','V':'ACG','H':'ACT','D':'AGT','B':'CGT','N':'ACGTN' }
   mpattern = len(pattern)
   s = []
   ss = []
   if mpattern == 1 :
      s = sl_code[pattern[0]]
      return s
   else :
      s = expand_pattern(pattern[:mpattern-1])
      for string in s:
         for ch in sl_code[pattern[mpattern-1]] :
            ss.append(string+ch)
      return ss

def expand_pattern_cmpl(pattern=[]):
   sl_code_cmpl = {'A':'T','C':'G','G':'C','T':'A','M':'AC','R':'CT','W':'AT','S':'CG','Y':'AG','K':'AC','V':'CGT','H':'AGT','D':'ACT','B':'ACG','N':'ACGTN'}
   mpattern = len(pattern)
   s = []
   ss = []
   if mpattern == 1 :
      ss = sl_code_cmpl[pattern[0]]
      return ss
   else :
      s = expand_pattern_cmpl(pattern[:mpattern-1])
      for string in s:
         for ch in sl_code_cmpl[pattern[mpattern-1]] :
            ss.append(ch+string)
      return ss

def del_same(matchs):
   mmatchs = len(matchs)
   n = mmatchs - 2
   kk = mmatchs - 1
   while n >= 0 :
      if matchs[n] ==  matchs[kk] :
         del matchs[n]
         kk = kk - 1
      else :
         kk = n
      n = n - 1
   return matchs
   
def sortedDictValues(adict):
   keys = adict.keys()
   keys.sort()
   return map(adict.get, keys)

def pattern_match(conn, shsize, pat, table_name, log_file):
   mpattern = len(pat)
   patterns = expand_pattern(pat)
   patterns_cmpl = expand_pattern_cmpl(pat)

   matchs = []
   log_file.write(strftime("\n%Y-%b-%d %H:%M:%S", localtime()))
   log_file.write("\tmatch: %-10s..." % pat) 

   num = dna2num(patterns[0], mpattern, shsize)
   sqlquery = "SELECT chromStart from %s where " % table_name + "num>=%s " % num[0] + "and num<%s " % num[1] 
   for pattern in patterns:
      num=dna2num(pattern, mpattern, shsize)
      sqlquery = sqlquery + "or num>=%s " % num[0] + "and num<%s " % num[1]
   for pattern in patterns_cmpl:
      num=dna2num(pattern, mpattern, shsize)
      sqlquery = sqlquery + "or num>=%s " % num[0] + "and num<%s " % num[1]
   sqlquery = sqlquery + " order by chromStart" 
   log_file.write(strftime("\t%H:%M:%S", localtime()))
   log_file.write("...query database") 
   rr = conn.execute(sqlquery)
   log_file.write(strftime("\t%H:%M:%S", localtime()))
   log_file.write("...extract matchs") 
   for match in rr : 
      matchs.append(match[0])
   matchs_tmp = del_same(matchs) 
   log_file.write("\t(%d)" % len(matchs_tmp))

   return matchs_tmp

def scan_chromosome(genome_name, chrom_name, patterns, combines, patterns_name, wsize, shsize, out_file, log_file) :
   log_file.write(strftime("\n%Y-%b-%d %H:%M:%S", localtime()))
   log_file.write("\tStart on chrom %s" % chrom_name)
   result = dict()
   result['M'] = dict()


   #----------------------------------------------------------------------------------------
   #----------------find matchs-------------------------------------------------------------
   db = create_engine('mysql://stree:12345@scofield.bx.psu.edu/stree')
   conn = db.connect()
   total_matchs = 0
   table_name = genome_name + "_" + chrom_name
   for pattern in patterns: 
      result['M'][pattern] = pattern_match(conn, shsize, pattern, table_name, log_file)
      total_matchs = total_matchs + len(result['M'][pattern])
   conn.close()

   #----------------------------------------------------------------------------------------
   #---------------find pattern combination in window---------------------------------------
   log_file.write(strftime("\n%Y-%b-%d %H:%M:%S", localtime()))
   log_file.write("\tFind clusters in %d wsize ... " % wsize)
   kk = 0
   clusters = dict()
   nnclusters = 0

   n = dict()
   ismatch = dict()
   for pattern in patterns :
      n[pattern] = 0
      ismatch[pattern] = 0
   clusters_temp = dict()
   clusters_temp["positions"] = []
   clusters_temp["patterns"]  = []
   clusters_temp["strands"]   = []


   nn = 0
   jj = 0
   while nn < total_matchs -1 :
   
      # put matches of the patterns into clusters_temp: start from nnth match 
      if len(clusters_temp["positions"]) >0 : 
	 ismatch[clusters_temp["patterns"][0]] = ismatch[clusters_temp["patterns"][0]] - 1
         del clusters_temp["positions"][0]
         del clusters_temp["patterns"][0]
         del clusters_temp["strands"][0]
      while jj < total_matchs :  
         for pattern in patterns :
	    if len(result['M'][pattern])>0 :
               current_pat = pattern
	       break
         for pattern in patterns : 
            if len(result['M'][pattern])>0 :
	       if result['M'][pattern][n[pattern]] < result['M'][current_pat][n[current_pat]]: 
	          current_pat = pattern
	 if len(clusters_temp["positions"]) > 0 : 
	    if result['M'][current_pat][n[current_pat]] > clusters_temp["positions"][0] + wsize : 
               break
         ismatch[current_pat] = ismatch[current_pat] + 1   
         clusters_temp["positions"].append(result['M'][current_pat][n[current_pat]]) 
         clusters_temp["patterns"].append(current_pat)
         clusters_temp["strands"].append('+')
         n[current_pat] = n[current_pat] + 1
	 if n[current_pat] == len(result['M'][current_pat]) : 
	    for pattern in patterns :
	       while n[pattern] < len(result['M'][pattern]):
	          if result['M'][pattern][n[pattern]] < clusters_temp["positions"][0] + wsize : 
	             clusters_temp["positions"].append(result['M'][pattern][n[pattern]]) 
                     clusters_temp["patterns"].append(pattern)
                     clusters_temp["strands"].append('+')
		  n[pattern] = n[pattern] + 1
	    jj = total_matchs
	    nn = total_matchs
         jj = jj + 1


      #check if the cluster contains the minimum occurrences of patterns
      allmatch = 0
      for pattern in patterns :  
         if combines[pattern] != 0 and ismatch[pattern] < combines[pattern]:
            allmatch = 1


      #if yes, add the clusters_temp to clusters array
      if allmatch == 0 : 
         nnclusters = nnclusters + 1
	 
	 #kk==0, means it's the first cluster
	 if kk == 0 : 
            clusters[kk] = dict()
            clusters[kk]["start"] = clusters_temp["positions"][0]
	    clusters[kk]["positions"] = []
	    clusters[kk]["patterns"] = []
	    clusters[kk]["strands"] = []
	    ii = 0
	    nclusters_temp = len(clusters_temp["positions"])
	    while ii < nclusters_temp : 
	       clusters[kk]["positions"].append(clusters_temp["positions"][ii]-clusters[kk]["start"])
	       clusters[kk]["patterns"].append(patterns_name[clusters_temp["patterns"][ii]])
	       ii = ii + 1
	    clusters[kk]["strands"].extend(clusters_temp["strands"])
            clusters[kk]["end"] = clusters_temp["positions"][-1] + len(clusters_temp["patterns"][-1])
            kk = kk + 1
	 else : 
	 
	    #if the clusters_temp overlaps with the last cluster in the cluster array, then merge them
	    if clusters_temp["positions"][0] <= clusters[kk-1]["end"]: 
	       ii = 0 
	       while ii < len(clusters_temp["positions"]) : 
	          if clusters_temp["positions"][ii] > clusters[kk-1]["end"] - len(clusters_temp["patterns"][ii]) : 
	             clusters[kk-1]["positions"].append(clusters_temp["positions"][ii]-clusters[kk-1]["start"])
	             clusters[kk-1]["patterns"].append(patterns_name[clusters_temp["patterns"][ii]])
	             clusters[kk-1]["strands"].append(clusters_temp["strands"][ii])
		  ii = ii + 1
               clusters[kk-1]["end"] = clusters_temp["positions"][-1] + len(clusters_temp["patterns"][-1])
	    
	    #otherwise, add as a new cluster to the array
	    else : 
               clusters[kk] = dict()
               clusters[kk]["start"] = clusters_temp["positions"][0]
	       clusters[kk]["positions"] = []
	       clusters[kk]["patterns"] = []
	       clusters[kk]["strands"] = []
	       ii = 0
	       nclusters_temp = len(clusters_temp["positions"])
	       while ii < nclusters_temp : 
	          clusters[kk]["positions"].append(clusters_temp["positions"][ii]-clusters[kk]["start"])
	          clusters[kk]["patterns"].append(patterns_name[clusters_temp["patterns"][ii]])
	          ii = ii + 1
	       clusters[kk]["strands"].extend(clusters_temp["strands"])
               clusters[kk]["end"] = clusters_temp["positions"][-1] + len(clusters_temp["patterns"][-1])
               kk = kk + 1
      nn = nn + 1
   log_file.write("\t%d" % nnclusters)
   nclusters = len(clusters)
   result['C'] = nnclusters
   result['NO'] = clusters
   
   
   #----------------------------------------------------------------------------------------
   #-----------------print clusters without overlap----------------------------------------------------------
   log_file.write(strftime("\n%Y-%b-%d %H:%M:%S", localtime()))
   log_file.write("\tMerge overlap clusters...") 
   log_file.write("\t\t%d" % nclusters)
   patterns_len = dict()
   for pattern in patterns : 
      patterns_len[patterns_name[pattern]] = len(pattern)

   #--------print bed file header---------
   out_file.write("#1. chrom")
   out_file.write("#2. chromStart.Note:The first base in a chromosome is numbered 0.")
   out_file.write("#3. chromEnd")
   out_file.write("#4. Pattern order. E.g. BABCBD, each letter represents one pattern.")
   out_file.write("#5. score. If the track line useScore attribute is set to 1 for this annotation data set, the score value will determine the level of gray.")
   out_file.write("#6. strand")
   out_file.write("#7. thickStart. The starting position at which the feature is drawn thickly.")
   out_file.write("#8. thickEnd. The ending position at which the feature is drawn thickly.")
   out_file.write("#9. itemRgb. An RGB value of the form R,G,B (e.g. 255,0,0). If the track line itemRgb attribute is set to "On", this RBG value will determine the display color. ")
   out_file.write("#10. blockCount. The number of blocks (exons) in the BED line.")
   out_file.write("#11. blockSizes. A comma-separated list of the block sizes. ")
   out_file.write("#12. blockStarts. A comma-separated list of block starts.")

   kk = 0
   while kk < nclusters:
      if clusters.get(kk) != None : 
         if clusters[kk]["end"] - clusters[kk]["start"] != clusters[kk]["positions"][-1] + patterns_len[clusters[kk]["patterns"][-1]] : 
	    log_file.write("\n"+chrom_name)
	    log_file.write("\t"+str(kk)+"/"+str(nclusters))
	    log_file.write("\t"+str(clusters[kk]["end"] - clusters[kk]["start"] - clusters[kk]["positions"][-1]) )
	    clusters[kk]["end"] = clusters[kk]["start"] + clusters[kk]["positions"][-1] + patterns_len[clusters[kk]["patterns"][-1]]
         out_file.write(str("chr%s" % chrom_name))
	 out_file.write("\t")
         out_file.write(str(clusters[kk]["start"]))
	 out_file.write("\t")
         out_file.write(str(clusters[kk]["end"]))
	 out_file.write("\t")
	 name = str(clusters[kk]["patterns"]).replace("'", "").replace(",","").replace(" ","").replace("[","").replace("]","")
	 if len(name) > 30 : 
	    name = "c"+str(kk)
         out_file.write(name)
	 out_file.write("\t0\t+\t")
         out_file.write(str(clusters[kk]["start"]))
	 out_file.write("\t")
         out_file.write(str(clusters[kk]["end"]))
	 out_file.write("\t0\t")
         out_file.write(str(len(clusters[kk]["patterns"])))
	 out_file.write("\t")
	 for pattern in clusters[kk]["patterns"] : 
	    out_file.write("%d," % patterns_len[pattern])
	 out_file.write("\t")
         out_file.write(str(clusters[kk]["positions"]).replace("L", "").replace(" ","").replace("[","").replace("]",""))
	 out_file.write(",\n")
      kk = kk + 1
   
   log_file.write(strftime("\n%Y-%b-%d %H:%M:%S\t", localtime()))
   log_file.write("OK!") 

   return result



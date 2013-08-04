# galaxy tool xml files can define a galaxy supplied output filename
# that must be passed to the tool and used to return output
# here, the plink log file is copied to that file and removed
# took a while to figure this out!
# use exec_before_job to give files sensible names
#

import sys,shutil,os

print >> sys.stdout, 'rgGvarICC.py started'
if len(sys.argv) < 4:
  print >> sys.stdout, 'expected 10 params in sys.argv, got %d - %s' % (len(sys.argv),sys.argv)
  print >> sys.stdout, """this script will check a list of gene names (HUGO symbols..)
for Sanger Genvar Illumina U6 probes and report whether there's likely more signal than noise.
Takes 3 parameters 
-g comma_del_gene_list
-r comma_del_race_list
-o a new filename root for the output """
  sys.exit(1)

plink = '/usr/local/bin/plink'
outfprefix = sys.argv[2]
vcl = [plink,'--noweb','--bfile',sys.argv[1],'--make-bed','--out',outfprefix,'--mind',sys.argv[3],
'--geno',sys.argv[4],'--maf',sys.argv[6],'--hwe',sys.argv[5],'--me',sys.argv[7],sys.argv[8]]
os.spawnv(os.P_WAIT,plink,vcl)
shutil.copyfile('%s.log' % outfprefix,sys.argv[9]) # create log file for galaxy
os.remove('%s.log' % outfprefix) # this file ends up wherever the tool happens to think it's running



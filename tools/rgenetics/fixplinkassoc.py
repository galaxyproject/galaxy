#!/usr/local/bin/python

"""
rewrite a plink tdt output file for gene graphs
ross lazarus 
march 11 2007
march 17 2007 - added OR inverter for OR < 1
"""
from sys import argv
import math

def fix(plinkout="hm",tag='test'):
   #  CHR         SNP   A1      F_A      F_U   A2        CHISQ            P           OR 
   #   1   rs3094315    G   0.6685   0.1364    A        104.1    1.929e-24        12.77 
   # write as a genegraph input file
   inf = file('%s.assoc' % plinkout,'r')
   outf = file('%sassoc.xls' % plinkout,'w')
   res = ['rs\tlog10p%s\tFakeInvOR%s\tRealOR%s' % (tag,tag,tag)]
   head = inf.next()
   for l in inf:
    ll = l.split()
    if len(ll) >= 6:
      try:
      	p = float(ll[7])
      	logp = '%3.3f' % -math.log10(p)
      except:
        logp = '0'
      try:
         orat = ll[8]
         if orat == 'NA':
            orat = '0'
      except:
         orat = '0'
      orat2 = orat
      if float(orat) < 1 and float(orat) > 0.0:
         orat2 = '%3.3f' % (1.0/float(orat))
      outl = [ll[1],logp, orat2, orat]
      res.append('\t'.join(outl))
   outf.write('\n'.join(res))
   outf.write('\n')
   outf.close()
   inf.close()

if __name__=="__main__":
  if len(argv) > 1:
    if len(argv) >= 2:
      tag = argv[2]
    else:
      tag = 'test'
    fix(argv[1],tag=tag)
  else:
    print 'Need plink .assoc file name to convert for gene graphs (and an optional tag to distinguish track names)'


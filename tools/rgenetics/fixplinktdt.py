#!/usr/local/bin/python

"""
rewrite a plink tdt output file for gene graphs
ross lazarus 
march 11 2007
"""
from sys import argv
import math

def fix(plinkout="hm"):
   # CHR         SNP  A1:A2      T:U_TDT       OR_TDT    CHISQ_TDT        P_TDT 
   #   1   rs3094315    G:A        10:12       0.8333       0.1818       0.6698 
   # write as a genegraph input file
   inf = file('%s.tdt' % plinkout,'r')
   outf = file('%stdt.xls' % plinkout,'w')
   res = ['rs\tlog10p\tInf_Families']
   head = inf.next()
   for l in inf:
    ll = l.split()
    if len(ll) >= 6:
      totinf = sum(map(int,ll[3].split(':')))
      try:
      	p = float(ll[6])
      	logp = '%3.3f' % -math.log10(p)
      except:
        logp = '0'
      try:
         ninf = '%d' % totinf
      except:
         ninf = '0'
      outl = [ll[1],logp, ninf]
      res.append('\t'.join(outl))
   outf.write('\n'.join(res))
   outf.write('\n')
   outf.close()
   inf.close()

if __name__=="__main__":
  if len(argv) > 1:
    fix(argv[1])
  else:
    print 'Need plink .tdt file name to convert for gene graphs'


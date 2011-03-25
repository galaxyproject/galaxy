# before running the qc, need to rename various output files
import os,string,time
from galaxy import datatypes 


def get_phecols(phef='',selectOne=0):
   """return column names """
   phepath = phef.extra_files_path
   phename = phef.metadata.base_name
   phe = os.path.join(phepath,'%s.pphe' % phename)
   head = open(phe,'r').next()
   c = head.strip().split()[2:] # first are fid,iid
   res = [(cname,cname,False) for cname in c]
   if len(res) >= 1:
       if selectOne:
          x,y,z = res[0] # 0,1 = fid,iid
          res[0] = (x,y,True) # set second selected
       else:
          res.insert(0,('None','None',True))
   else:
      res = [('None','no phenotype columns found',False),]
   return res


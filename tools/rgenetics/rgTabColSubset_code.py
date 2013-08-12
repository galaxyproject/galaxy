from galaxy import app
import galaxy.util,os

def getcols(fname=""):
   """return column names other than chr offset as a select list"""
   res = [('Please select an input file from your history to subset','None',True),] # default
   try:
       d = fname.dataset.get_file_name()
   except:
       res = [('? %s' % fname,'?',False),]
       return res
   head = open(d,'r').readline()
   cols = head.strip().split('\t')
   res = [(cname,'%d' % n,(n<4)) for n,cname in enumerate(cols)]
   return res



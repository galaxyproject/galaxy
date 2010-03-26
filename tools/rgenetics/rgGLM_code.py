# before running the qc, need to rename various output files
import os,string,time
from galaxy import datatypes 

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

def get_out_formats():
    """return options for formats"""
    dat = [['ucsc track','wig'],['ucsc genome graphs','gg'],['tab delimited','xls']]
    dat = [(x[0],x[1],False) for x in dat]
    dat.reverse()
    return dat

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


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the data"""
    killme=string.punctuation+string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    job_name = param_dict.get( 'title1', 'GLM' )
    job_name = job_name.encode().translate(trantab)
    outxls = ['tabular','%s_GLM.xls' % job_name]
    logtxt = ['txt','%s_GLM_log.txt' % job_name]
    ggout = ['gg','%s_GLM_topTable.gff' % job_name]
    lookup={}
    lookup['out_file1'] = outxls
    lookup['logf'] = logtxt
    lookup['gffout'] = ggout
    info = '%s GLM output by rgGLM created at %s' % (job_name,timenow())
    for name in lookup.keys():
        data = out_data[name]
        data_type,newname = lookup.get(name,(None,None))
        if data_type <> None:
            data.name = newname
            data.info = info
            out_data[name] = data
        else:
            print >> stdout,'no output matching %s in exec after hook for rgGLM' % name
    app.model.context.flush()

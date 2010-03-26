from galaxy import app
import galaxy.util,string

librepos = '/usr/local/galaxy/data/rg'
myrepos = '/home/rerla/galaxy'
marchinirepos = '/usr/local/galaxy/data/rg/snptest'

#Provides Upload tool with access to list of available builds


def get_rgRegionOutFormats():
    """return options for formats"""
    dat = [['ucsc track','wig',False],['Strict genome graphs (rs+floats)','gg',True],['tab delimited','xls',False]]
    dat = [(x[0],x[1],x[2]) for x in dat]
    return dat


def get_phecols(phef):
   """return column names """
   head = open(phef,'r').next()
   c = head.strip().split()
   res = [(cname,cname,False) for cname in c]
   x,y,z = res[2] # 0,1 = fid,iid
   res[2] = (x,y,True) # set second selected
   return res


def getAllcols(fname="/usr/local/galaxy/data/camp2007/camp2007.xls",outformat='gg'):
   """return column names other than chr offset as a select list"""
   head = open(fname,'r').next()
   c = head.strip().split()
   res = [(cname,'%d' % n,True) for n,cname in enumerate(c)]
  
   return res


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the data"""
    data_name = param_dict.get( 'tag', 'My region' )
    outformat = param_dict.get( 'outformat', 'gg' )
    outfile = param_dict.get( 'outfile1', 'lped' )
    for name, data in out_data.items():
       if name == 'tag':
         data = app.datatypes_registry.change_datatype(data, outformat)
         data.name = data_name
         out_data[name] = data


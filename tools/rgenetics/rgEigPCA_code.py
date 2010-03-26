from galaxy import datatypes,model
import sys,time,string

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the html output file
    """
    indatname = inp_data['i'].name
    job_name = param_dict.get( 'title', 'Eigenstrat run' )
    job_name = job_name.encode()
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    job_name = job_name.translate(trantab)
    info = '%s rgEigPCA2 on %s at %s' % (job_name,indatname,timenow())
    exts = ['html','txt']
    for i,ofname in enumerate(['out_file1','pca']):
        data = out_data[ofname]
        ext = exts[i]
        newname = '%s.%s' % (job_name,ext)
        data.name = newname
        data.info = info
        out_data[ofname] = data
    app.model.context.flush()

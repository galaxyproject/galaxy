from galaxy import datatypes,model
import sys,time,string

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    """Sets the name of the html output file
    """
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    job_name = param_dict.get( 'title1', 'rgGRR' )
    newname = '%s.html' % job_name.translate(trantab)
    indatname = inp_data['i'].name
    info = '%s Mean allele sharing on %s at %s' % (job_name,indatname,timenow())
    ofname = 'out_file1'
    data = out_data[ofname]
    data.name = newname
    data.info = info
    out_data[ofname] = data
    app.model.context.flush()

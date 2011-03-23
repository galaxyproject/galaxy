from galaxy import app
import os, string, time

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))



def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    name,data = out_data.items()[0]
    basename = param_dict['title']
    basename = basename.encode()
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    title = basename.translate(trantab)
    info = '%s filtered by rgClean.py at %s' % (title,timenow())
    data.change_datatype('pbed')
    #data.file_name = data.file_name
    data.metadata.base_name = title
    data.name = '%s.pbed' % title
    data.info = info
    data.readonly = True
    app.model.context.flush()




from galaxy import app
import os, string, time

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))



def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    name,data = out_data.items()[0]
    basename = param_dict['title1']
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    title = basename.encode().translate(trantab)
    info = '%s filtered by rgLDIndep.py at %s' % (title,timenow())
    data.file_name = data.file_name
    data.metadata.base_name = title
    data.name = '%s.pbed' % title
    data.info = info
    app.model.context.flush()




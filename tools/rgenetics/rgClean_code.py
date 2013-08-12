from galaxy import app
import os, string

# Create link to files here
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    data = out_data.values()[0]
    uid = '%d' % (data.history.user.id)
    ftd = param_dict['file_type_dir']
    repository = param_dict['repository']
    basename = param_dict['title']
    efp = os.path.join(repository,uid,ftd)
    data.change_datatype(os.path.split(ftd)[-1])
    data.file_name = data.file_name
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    title = basename.translate(trantab)    
    data.metadata.base_name = title
    data.name = title
    data.flush()
    data.dataset_file.extra_files_path = efp
    data.dataset_file.readonly = True
    data.flush()
    app.model.flush()




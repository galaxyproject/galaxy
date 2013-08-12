#build list of available data
import os, sys, glob


repository = "/usr/local/galaxy/data/rg/library"
#repository = "/home/rossl/rgalaxy/rgdata"

def get_available_file_types():
    import_files = []
    try:
        flist = glob.glob(os.path.join(repository,'*'))
        flist = [os.path.splitext(x)[0] for x in flist] # get unique filenames
        flist = list(set(flist)) # remove dupes
        flist.sort()
        for i, data in enumerate( flist ):
            import_files.append( (os.path.split(data)[-1], data, False) )
    except:
        pass
    if len(import_files) < 1:
        import_files.append(('No data available','None',True))
    return import_files

#return available datasets for build
def get_available_data( file_type_dir, build='hg18' ):
    #we need to allow switching of builds, and properly set in post run hook
    import_files = []
    try:
        flist = glob.glob(os.path.join(repository,file_type_dir,'*'))
        flist = [os.path.splitext(x)[0] for x in flist] # get unique filenames
        flist = list(set(flist)) # remove dupes
        flist.sort()
        for i, data in enumerate( flist ):
            import_files.append( (os.path.split(data)[-1], os.path.split(data)[-1], False) )
    except:
        pass
    if len(import_files) < 1:
        import_files.append(('No data available for this build','None',True))
    return import_files



# Create link to files here
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    data = out_data.values()[0]
    data.change_datatype(os.path.split(param_dict['file_type_dir'])[-1])
    data.file_name = data.file_name
    base_name = param_dict['base_name']
    data.metadata.base_name = base_name
    data.name = base_name
    data.flush()
    data.dataset_file.extra_files_path = param_dict['file_type_dir']
    data.dataset_file.readonly = True
    data.flush()
    app.model.flush()




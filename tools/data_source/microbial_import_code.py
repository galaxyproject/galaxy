
#post processing, set build for data and add additional data to history
from galaxy import datatypes, config, jobs 
from shutil import copyfile
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    history = out_data.items()[0][1].history
    if history == None:
        print "unknown history!"
        return
    kingdom = param_dict.get( 'kingdom', None )
    #group = param_dict.get( 'group', None )
    org = param_dict.get( 'org', None )
    
    #if not (kingdom or group or org):
    if not (kingdom or org):
        print "Parameters are not available."
    
    new_stdout = ""
    split_stdout = stdout.split("\n")
    basic_name = ""
    for line in split_stdout:
        fields = line.split("\t")
        if fields[0] == "#File1":
            description = fields[1]
            chr = fields[2]
            dbkey = fields[3]
            file_type = fields[4]
            name, data = out_data.items()[0]
            basic_name = data.name
            data.name = data.name + " (" + microbe_info[kingdom][org]['chrs'][chr]['data'][description]['feature'] +" for " + microbe_info[kingdom][org]['name'] + ":" + chr + ")"
            data.dbkey = dbkey
            data.info = data.name
            data = app.datatypes_registry.change_datatype( data, file_type )
            data.init_meta()
            data.set_peek()
            app.model.flush()
        elif fields[0] == "#NewFile":
            description = fields[1]
            chr = fields[2]
            dbkey = fields[3]
            filepath = fields[4]
            file_type = fields[5]
            newdata = app.model.Dataset()
            newdata.extension = file_type
            newdata.name = basic_name + " (" + microbe_info[kingdom][org]['chrs'][chr]['data'][description]['feature'] +" for "+microbe_info[kingdom][org]['name']+":"+chr + ")"
            newdata.flush()
            history.add_dataset( newdata )
            newdata.flush()
            app.model.flush()
            try:
                copyfile(filepath,newdata.file_name)
                newdata.info = newdata.name
                newdata.state = jobs.JOB_OK
            except:
                newdata.info = "The requested file is missing from the system."
                newdata.state = jobs.JOB_ERROR
            newdata.dbkey = dbkey
            newdata.init_meta()
            newdata.set_peek()
            #
            app.model.flush()

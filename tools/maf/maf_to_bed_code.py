import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf
from galaxy import datatypes, config, jobs 
from shutil import move

def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    output_data = out_data.items()[0][1]
    history = output_data.history
    if history == None:
        print "unknown history!"
        return
    new_stdout = ""
    split_stdout = stdout.split("\n")
    basic_name = output_data.name
    output_data_list = []
    for line in split_stdout:
        if line.startswith("#FILE1"):
            fields = line.split("\t")
            dbkey = fields[1]
            filepath = fields[2]
            output_data.dbkey = dbkey
            output_data.name = basic_name + " (" + dbkey + ")"
            app.model.context.add( output_data )
            app.model.context.flush()
            output_data_list.append(output_data)
        elif line.startswith("#FILE"):
            fields = line.split("\t")
            dbkey = fields[1]
            filepath = fields[2]
            newdata = app.model.HistoryDatasetAssociation( create_dataset = True, sa_session = app.model.context )
            newdata.set_size()
            newdata.extension = "bed"
            newdata.name = basic_name + " (" + dbkey + ")"
            app.model.context.add( newdata )
            app.model.context.flush()
            history.add_dataset( newdata )
            app.security_agent.copy_dataset_permissions( output_data.dataset, newdata.dataset )
            app.model.context.add( history )
            app.model.context.flush()
            try:
                move(filepath,newdata.file_name)
                newdata.info = newdata.name
                newdata.state = newdata.states.OK
            except:
                newdata.info = "The requested file is missing from the system."
                newdata.state = newdata.states.ERROR
            newdata.dbkey = dbkey
            newdata.init_meta()
            newdata.set_meta()
            newdata.set_peek()
            app.model.context.flush()
            output_data_list.append(newdata)
        else:
            new_stdout = new_stdout + line
        for data in output_data_list:
            if data.state == data.states.OK:
                data.info = new_stdout
                app.model.context.add( data )
                app.model.context.flush()

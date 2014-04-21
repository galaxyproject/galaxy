import os
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.align import maf
from galaxy import datatypes, config, jobs 
from shutil import move

def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    output_data = out_data.items()[0][1]
    new_stdout = ""
    split_stdout = stdout.split("\n")
    for line in split_stdout:
        if line.startswith("#FILE1"):
            fields = line.split("\t")
            dbkey = fields[1]
            output_data.dbkey = dbkey
            output_data.name = "%s (%s)" % ( output_data.name, dbkey )
            app.model.context.add( output_data )
            app.model.context.flush()
        else:
            new_stdout = "%s\n%s" % ( new_stdout, line )
    for data in output_data.creating_job.output_datasets:
        data = data.dataset
        data.info = new_stdout
        app.model.context.add( data )
        app.model.context.flush()

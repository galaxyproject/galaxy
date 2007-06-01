#post processing, if bed file, change to interval file
from galaxy import datatypes
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    for name, data in out_data.items():
        if data.ext == "bed":
            data = app.datatypes_registry.change_datatype(data, "interval")
            data.flush()
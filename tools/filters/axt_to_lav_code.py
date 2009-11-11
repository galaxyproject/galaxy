
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    for name,data in out_data.items():
        if name == "seq_file2":
            data.dbkey = param_dict['dbkey_2']
            app.model.context.add( data )
            app.model.context.flush()
            break
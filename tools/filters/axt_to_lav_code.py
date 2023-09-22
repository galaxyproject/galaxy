def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    data = out_data["seq_file2"]
    data.dbkey = param_dict["dbkey_2"]
    app.model.context.add(data)
    app.model.context.flush()

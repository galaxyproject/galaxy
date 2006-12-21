#Set build, name, and info for each output BED file
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    new_stdout = ""
    filename_to_build = {}
    for line in stdout.split("\n"):
        if line.startswith("#FILE"):
            fields = line.split("\t")
            filename_to_build[fields[1]]=fields[2].strip()
        else:
            new_stdout = new_stdout + line
    for name,data in out_data.items():
        try:
            data.info = new_stdout +"\n"+ stderr
            data.dbkey = filename_to_build[data.file_name]
            data.name = data.name + " ("+data.dbkey+")"
            data.flush()
        except:
            continue
    app.model.flush()
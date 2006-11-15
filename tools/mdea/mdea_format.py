from galaxy import datatypes
def exec_after_process(app, inp_data, out_data, param_dict,tool, stdout, stderr):
    ext   = param_dict.get('out_format', 'html')
    items = out_data.items()   
    for name, data in items: 
        data =  datatypes.change_datatype(data, ext)
        data.flush()
    app.model.flush()

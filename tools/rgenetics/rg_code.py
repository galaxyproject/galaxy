from galaxy import app

def exec_before_job(app, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    data_name = param_dict.get( 'name', 'PlinkQCclean' )
    data_name = '%s.log' % data_name
    data_type = param_dict.get( 'type', 'txt' )
    name, data = out_data.items()[0]
    data = app.datatypes_registry.change_datatype(data, data_type)
    data.name = data_name
    out_data[name] = data


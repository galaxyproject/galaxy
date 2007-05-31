# runs after the job (and after the default post-filter)

def validate(incoming):
    """Validator"""
    #raise Exception, 'not quite right'
    pass

def exec_before_job( app, inp_data, out_data, param_dict, tool=None):
    """Sets the name of the data"""
    dataid = param_dict.get( 'dataid', None )
    data = app.model.Dataset.get( dataid )
    if data:
        data.info = data.states.RUNNING
        data.flush()

def exec_after_process( app, inp_data, out_data, param_dict, **kwd):
    """Sets the name of the data"""
    dataid = param_dict.get( 'dataid', None )
    data = app.model.Dataset.get(dataid)
    if data:
        data.state = data.states.OK
        data.set_peek()
        data.flush()

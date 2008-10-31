"""
Classes encapsulating Galaxy tool parameters.
"""

from basic import *
from galaxy.util.json import *

def check_param( trans, param, incoming_value, param_values ):
    """
    Check the value of a single parameter `param`. The value in 
    `incoming_value` is converted from its HTML encoding and validated.
    The `param_values` argument contains the processed values of 
    previous parameters (this may actually be an ExpressionContext 
    when dealing with grouping scenarios).
    """
    value = incoming_value
    error = None
    try:
        if value is not None or isinstance(param, DataToolParameter):
            # Convert value from HTML representation
            value = param.from_html( value, trans, param_values )
            # Allow the value to be converted if neccesary
            filtered_value = param.filter_value( value, trans, param_values )
            # Then do any further validation on the value
            param.validate( filtered_value, trans.history )
        elif value is None and isinstance( param, SelectToolParameter ):
           # An empty select list or column list
           param.validate( value, trans.history ) 
    except ValueError, e:
        error = str( e )
    return value, error

def params_to_strings( params, param_values, app ):
    """
    Convert a dictionary of parameter values to a dictionary of strings
    suitable for persisting. The `value_to_basic` method of each parameter
    is called to convert its value to basic types, the result of which
    is then json encoded (this allowing complex nested parameters and 
    such).
    """
    rval = dict()
    for key, value in param_values.iteritems():
        if key in params:
            value = params[ key ].value_to_basic( value, app )
        rval[ key ] = str( to_json_string( value ) )
    return rval
    
def params_from_strings( params, param_values, app, ignore_errors=False ):
    """
    Convert a dictionary of strings as produced by `params_to_strings`
    back into parameter values (decode the json representation and then
    allow each parameter to convert the basic types into the parameters
    preferred form).
    """
    rval = dict()
    for key, value in param_values.iteritems():
        value = json_fix( from_json_string( value ) )
        if key in params:
            value = params[key].value_from_basic( value, app, ignore_errors )
        rval[ key ] = value 
    return rval

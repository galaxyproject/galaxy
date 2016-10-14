"""
Classes encapsulating Galaxy tool parameters.
"""
import re
from json import dumps, loads

from galaxy.util.expressions import ExpressionContext
from galaxy.util.json import json_fix

from .basic import DataCollectionToolParameter, DataToolParameter, RuntimeValue, SelectToolParameter
from .grouping import Conditional, Repeat, Section, UploadDataset

REPLACE_ON_TRUTHY = object()

# Some tools use the code tag and access the code base, expecting certain tool parameters to be available here.
__all__ = ( 'DataCollectionToolParameter', 'DataToolParameter', 'SelectToolParameter' )


def visit_input_values( inputs, input_values, callback, name_prefix='', label_prefix='', parent_prefix='', context=None, no_replacement_value=REPLACE_ON_TRUTHY ):
    """
    Given a tools parameter definition (`inputs`) and a specific set of
    parameter `values`, call `callback` for each non-grouping parameter,
    passing the parameter object, value, a constructed unique name,
    and a display label.

    If the callback returns a value, it will be replace the old value.

    >>> from xml.etree.ElementTree import XML
    >>> from galaxy.util.bunch import Bunch
    >>> from galaxy.util.odict import odict
    >>> from galaxy.tools.parameters.basic import TextToolParameter, BooleanToolParameter
    >>> from galaxy.tools.parameters.grouping import Repeat
    >>> a = TextToolParameter( None, XML( '<param name="a"/>' ) )
    >>> b = Repeat()
    >>> c = TextToolParameter( None, XML( '<param name="c"/>' ) )
    >>> d = Repeat()
    >>> e = TextToolParameter( None, XML( '<param name="e"/>' ) )
    >>> f = Conditional()
    >>> g = BooleanToolParameter( None, XML( '<param name="g"/>' ) )
    >>> h = TextToolParameter( None, XML( '<param name="h"/>' ) )
    >>> i = TextToolParameter( None, XML( '<param name="i"/>' ) )
    >>> b.name = 'b'
    >>> b.inputs = odict([ ('c', c), ('d', d) ])
    >>> d.name = 'd'
    >>> d.inputs = odict([ ('e', e), ('f', f) ])
    >>> f.test_param = g
    >>> f.name = 'f'
    >>> f.cases = [ Bunch( value='true', inputs= { 'h': h } ), Bunch( value='false', inputs= { 'i': i } ) ]
    >>>
    >>> def visitor( input, value, prefix, prefixed_name, **kwargs ):
    ...     print 'name=%s, prefix=%s, prefixed_name=%s, value=%s' % ( input.name, prefix, prefixed_name, value )
    >>> inputs = odict([('a',a),('b',b)])
    >>> nested = odict([ ('a', 1), ('b', [ odict([('c', 3), ( 'd', [odict([ ('e', 5), ('f', odict([ ('g', True), ('h', 7) ])) ]) ])]) ]) ])
    >>> visit_input_values( inputs, nested, visitor )
    name=a, prefix=, prefixed_name=a, value=1
    name=c, prefix=b_0|, prefixed_name=b_0|c, value=3
    name=e, prefix=b_0|d_0|, prefixed_name=b_0|d_0|e, value=5
    name=g, prefix=b_0|d_0|, prefixed_name=b_0|d_0|f|g, value=True
    name=h, prefix=b_0|d_0|, prefixed_name=b_0|d_0|f|h, value=7
    >>> params_from_strings( inputs, params_to_strings( inputs, nested, None ), None )[ 'b' ][ 0 ][ 'd' ][ 0 ][ 'f' ][ 'g' ] is True
    True
    """
    def callback_helper( input, input_values, name_prefix, label_prefix, parent_prefix, context=None, error=None ):
        args = {
            'input'             : input,
            'parent'            : input_values,
            'value'             : input_values.get( input.name ),
            'prefixed_name'     : '%s%s' % ( name_prefix, input.name ),
            'prefixed_label'    : '%s%s' % ( label_prefix, input.label or input.name ),
            'prefix'            : parent_prefix,
            'context'           : context,
            'error'             : error
        }
        if input.name not in input_values:
            args[ 'error' ] = 'No value found for \'%s\'.' % args.get( 'prefixed_label' )
        new_value = callback( **args )
        if no_replacement_value is REPLACE_ON_TRUTHY:
            replace = bool( new_value )
        else:
            replace = new_value != no_replacement_value
        if replace:
            input_values[ input.name ] = new_value

    context = ExpressionContext( input_values, context )
    payload = { 'context': context, 'no_replacement_value': no_replacement_value }
    for input in inputs.values():
        if isinstance( input, Repeat ) or isinstance( input, UploadDataset ):
            values = input_values[ input.name ] = input_values.get( input.name, [] )
            for i, d in enumerate( values ):
                d[ '__index__' ] = i
                new_name_prefix = name_prefix + '%s_%d|' % ( input.name, i )
                new_label_prefix = label_prefix + '%s %d > ' % ( input.title, i + 1 )
                visit_input_values( input.inputs, d, callback, new_name_prefix, new_label_prefix, parent_prefix=new_name_prefix, **payload )
        elif isinstance( input, Conditional ):
            values = input_values[ input.name ] = input_values.get( input.name, {} )
            new_name_prefix = name_prefix + input.name + '|'
            case_error = None
            try:
                input.get_current_case( values[ input.test_param.name ] )
            except:
                case_error = 'The selected case is unavailable/invalid.'
                pass
            callback_helper( input.test_param, values, new_name_prefix, label_prefix, parent_prefix=name_prefix, context=context, error=case_error )
            values[ '__current_case__' ] = input.get_current_case( values[ input.test_param.name ] )
            visit_input_values( input.cases[ values[ '__current_case__' ] ].inputs, values, callback, new_name_prefix, label_prefix, parent_prefix=name_prefix, **payload )
        elif isinstance( input, Section ):
            values = input_values[ input.name ] = input_values.get( input.name, {} )
            new_name_prefix = name_prefix + input.name + '|'
            visit_input_values( input.inputs, values, callback, new_name_prefix, label_prefix, parent_prefix=name_prefix, **payload )
        else:
            callback_helper( input, input_values, name_prefix, label_prefix, parent_prefix=parent_prefix, context=context )


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
        if trans.workflow_building_mode:
            if isinstance( value, RuntimeValue ):
                return [ { '__class__' : 'RuntimeValue' }, None ]
            if isinstance( value, dict ):
                if value.get( '__class__' ) == 'RuntimeValue':
                    return [ value, None ]
        value = param.from_json( value, trans, param_values )
        param.validate( value, trans )
    except ValueError as e:
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
    for key, value in param_values.items():
        if key in params:
            value = params[ key ].value_to_basic( value, app )
        rval[ key ] = str( dumps( value ) )
    return rval


def params_from_strings( params, param_values, app, ignore_errors=False ):
    """
    Convert a dictionary of strings as produced by `params_to_strings`
    back into parameter values (decode the json representation and then
    allow each parameter to convert the basic types into the parameters
    preferred form).
    """
    rval = dict()
    for key, value in param_values.items():
        value = json_fix( loads( value ) )
        if key in params:
            value = params[ key ].value_from_basic( value, app, ignore_errors )
        rval[ key ] = value
    return rval


def params_to_incoming( incoming, inputs, input_values, app, name_prefix="" ):
    """
    Given a tool's parameter definition (`inputs`) and a specific set of
    parameter `input_values` objects, populate `incoming` with the html values.

    Useful for e.g. the rerun function.
    """
    for input in inputs.values():
        if isinstance( input, Repeat ) or isinstance( input, UploadDataset ):
            for d in input_values[ input.name ]:
                index = d[ '__index__' ]
                new_name_prefix = name_prefix + '%s_%d|' % ( input.name, index )
                params_to_incoming( incoming, input.inputs, d, app, new_name_prefix )
        elif isinstance( input, Conditional ):
            values = input_values[ input.name ]
            current = values[ '__current_case__' ]
            new_name_prefix = name_prefix + input.name + '|'
            incoming[ new_name_prefix + input.test_param.name ] = values[ input.test_param.name ]
            params_to_incoming( incoming, input.cases[current].inputs, values, app, new_name_prefix )
        elif isinstance( input, Section ):
            values = input_values[ input.name ]
            new_name_prefix = name_prefix + input.name + '|'
            params_to_incoming( incoming, input.inputs, values, app, new_name_prefix )
        else:
            value = input_values.get( input.name )
            incoming[ name_prefix + input.name ] = value


def update_param( prefixed_name, input_values, new_value ):
    """
    Given a prefixed parameter name, e.g. 'parameter_0|parameter_1', update
    the corresponding input value in a nested input values dictionary.
    """
    for key in input_values:
        match = re.match( '^' + key + '_(\d+)\|(.+)', prefixed_name )
        if match and not key.endswith( "|__identifier__" ):
            index = int( match.group( 1 ) )
            if isinstance( input_values[ key ], list ) and len( input_values[ key ] ) > index:
                update_param( match.group( 2 ), input_values[ key ][ index ], new_value )
        else:
            match = re.match( '^' + key + '\|(.+)', prefixed_name )
            if isinstance( input_values[ key ], dict ) and match:
                update_param( match.group( 1 ), input_values[ key ], new_value )
            elif prefixed_name == key:
                input_values[ key ] = new_value

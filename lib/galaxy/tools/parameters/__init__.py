"""
Classes encapsulating Galaxy tool parameters.
"""
from __future__ import print_function

from json import dumps

from boltons.iterutils import remap

from galaxy.util import unicodify
from galaxy.util.expressions import ExpressionContext
from galaxy.util.json import safe_loads
from .basic import DataCollectionToolParameter, DataToolParameter, is_runtime_value, runtime_to_json, SelectToolParameter
from .grouping import Conditional, Repeat, Section, UploadDataset

REPLACE_ON_TRUTHY = object()

# Some tools use the code tag and access the code base, expecting certain tool parameters to be available here.
__all__ = ('DataCollectionToolParameter', 'DataToolParameter', 'SelectToolParameter')


def visit_input_values(inputs, input_values, callback, name_prefix='', label_prefix='', parent_prefix='', context=None, no_replacement_value=REPLACE_ON_TRUTHY, replace_optional_connections=False):
    """
    Given a tools parameter definition (`inputs`) and a specific set of
    parameter `values`, call `callback` for each non-grouping parameter,
    passing the parameter object, value, a constructed unique name,
    and a display label.

    If the callback returns a value, it will be replace the old value.

    >>> from collections import OrderedDict
    >>> from xml.etree.ElementTree import XML
    >>> from galaxy.util.bunch import Bunch
    >>> from galaxy.tools.parameters.basic import TextToolParameter, BooleanToolParameter
    >>> from galaxy.tools.parameters.grouping import Repeat
    >>> a = TextToolParameter(None, XML('<param name="a"/>'))
    >>> b = Repeat()
    >>> c = TextToolParameter(None, XML('<param name="c"/>'))
    >>> d = Repeat()
    >>> e = TextToolParameter(None, XML('<param name="e"/>'))
    >>> f = Conditional()
    >>> g = BooleanToolParameter(None, XML('<param name="g"/>'))
    >>> h = TextToolParameter(None, XML('<param name="h"/>'))
    >>> i = TextToolParameter(None, XML('<param name="i"/>'))
    >>> j = TextToolParameter(None, XML('<param name="j"/>'))
    >>> b.name = b.title = 'b'
    >>> b.inputs = OrderedDict([ ('c', c), ('d', d) ])
    >>> d.name = d.title = 'd'
    >>> d.inputs = OrderedDict([ ('e', e), ('f', f) ])
    >>> f.test_param = g
    >>> f.name = 'f'
    >>> f.cases = [Bunch(value='true', inputs= {'h': h}), Bunch(value='false', inputs= { 'i': i })]
    >>>
    >>> def visitor(input, value, prefix, prefixed_name, prefixed_label, error, **kwargs):
    ...     print('name=%s, prefix=%s, prefixed_name=%s, prefixed_label=%s, value=%s' % (input.name, prefix, prefixed_name, prefixed_label, value))
    ...     if error:
    ...         print(error)
    >>> inputs = OrderedDict([('a', a),('b', b)])
    >>> nested = OrderedDict([('a', 1), ('b', [OrderedDict([('c', 3), ('d', [OrderedDict([ ('e', 5), ('f', OrderedDict([ ('g', True), ('h', 7)]))])])])])])
    >>> visit_input_values(inputs, nested, visitor)
    name=a, prefix=, prefixed_name=a, prefixed_label=a, value=1
    name=c, prefix=b_0|, prefixed_name=b_0|c, prefixed_label=b 1 > c, value=3
    name=e, prefix=b_0|d_0|, prefixed_name=b_0|d_0|e, prefixed_label=b 1 > d 1 > e, value=5
    name=g, prefix=b_0|d_0|, prefixed_name=b_0|d_0|f|g, prefixed_label=b 1 > d 1 > g, value=True
    name=h, prefix=b_0|d_0|, prefixed_name=b_0|d_0|f|h, prefixed_label=b 1 > d 1 > h, value=7
    >>> params_from_strings(inputs, params_to_strings(inputs, nested, None), None)['b'][0]['d'][0]['f']['g'] is True
    True

    >>> # Conditional test parameter value does not match any case, warning is shown and child values are not visited
    >>> f.test_param = j
    >>> nested['b'][0]['d'][0]['f']['j'] = 'j'
    >>> visit_input_values(inputs, nested, visitor)
    name=a, prefix=, prefixed_name=a, prefixed_label=a, value=1
    name=c, prefix=b_0|, prefixed_name=b_0|c, prefixed_label=b 1 > c, value=3
    name=e, prefix=b_0|d_0|, prefixed_name=b_0|d_0|e, prefixed_label=b 1 > d 1 > e, value=5
    name=j, prefix=b_0|d_0|, prefixed_name=b_0|d_0|f|j, prefixed_label=b 1 > d 1 > j, value=j
    The selected case is unavailable/invalid.

    >>> # Test parameter missing in state, value error
    >>> del nested['b'][0]['d'][0]['f']['j']
    >>> visit_input_values(inputs, nested, visitor)
    name=a, prefix=, prefixed_name=a, prefixed_label=a, value=1
    name=c, prefix=b_0|, prefixed_name=b_0|c, prefixed_label=b 1 > c, value=3
    name=e, prefix=b_0|d_0|, prefixed_name=b_0|d_0|e, prefixed_label=b 1 > d 1 > e, value=5
    name=j, prefix=b_0|d_0|, prefixed_name=b_0|d_0|f|j, prefixed_label=b 1 > d 1 > j, value=None
    No value found for 'b 1 > d 1 > j'.

    >>> # Conditional parameter missing in state, value error
    >>> del nested['b'][0]['d'][0]['f']
    >>> visit_input_values(inputs, nested, visitor)
    name=a, prefix=, prefixed_name=a, prefixed_label=a, value=1
    name=c, prefix=b_0|, prefixed_name=b_0|c, prefixed_label=b 1 > c, value=3
    name=e, prefix=b_0|d_0|, prefixed_name=b_0|d_0|e, prefixed_label=b 1 > d 1 > e, value=5
    name=j, prefix=b_0|d_0|, prefixed_name=b_0|d_0|f|j, prefixed_label=b 1 > d 1 > j, value=None
    No value found for 'b 1 > d 1 > j'.

    >>> # Conditional input name has changed e.g. due to tool changes, key error
    >>> f.name = 'f_1'
    >>> visit_input_values(inputs, nested, visitor)
    name=a, prefix=, prefixed_name=a, prefixed_label=a, value=1
    name=c, prefix=b_0|, prefixed_name=b_0|c, prefixed_label=b 1 > c, value=3
    name=e, prefix=b_0|d_0|, prefixed_name=b_0|d_0|e, prefixed_label=b 1 > d 1 > e, value=5
    name=j, prefix=b_0|d_0|, prefixed_name=b_0|d_0|f_1|j, prefixed_label=b 1 > d 1 > j, value=None
    No value found for 'b 1 > d 1 > j'.

    >>> # Other parameters are missing in state
    >>> nested = OrderedDict([('b', [OrderedDict([( 'd', [OrderedDict([('f', OrderedDict([('g', True), ('h', 7)]))])])])])])
    >>> visit_input_values(inputs, nested, visitor)
    name=a, prefix=, prefixed_name=a, prefixed_label=a, value=None
    No value found for 'a'.
    name=c, prefix=b_0|, prefixed_name=b_0|c, prefixed_label=b 1 > c, value=None
    No value found for 'b 1 > c'.
    name=e, prefix=b_0|d_0|, prefixed_name=b_0|d_0|e, prefixed_label=b 1 > d 1 > e, value=None
    No value found for 'b 1 > d 1 > e'.
    name=j, prefix=b_0|d_0|, prefixed_name=b_0|d_0|f_1|j, prefixed_label=b 1 > d 1 > j, value=None
    No value found for 'b 1 > d 1 > j'.
    """
    def callback_helper(input, input_values, name_prefix, label_prefix, parent_prefix, context=None, error=None):
        value = input_values.get(input.name)
        args = {
            'input'             : input,
            'parent'            : input_values,
            'value'             : value,
            'prefixed_name'     : '%s%s' % (name_prefix, input.name),
            'prefixed_label'    : '%s%s' % (label_prefix, input.label or input.name),
            'prefix'            : parent_prefix,
            'context'           : context,
            'error'             : error
        }
        if input.name not in input_values:
            args['error'] = 'No value found for \'%s\'.' % args.get('prefixed_label')
        new_value = callback(**args)
        if no_replacement_value is REPLACE_ON_TRUTHY:
            replace = bool(new_value)
        else:
            replace = new_value != no_replacement_value
        if replace:
            input_values[input.name] = new_value
        elif replace_optional_connections and is_runtime_value(value):
            input_values[input.name] = input.value

    def get_current_case(input, input_values):
        try:
            return input.get_current_case(input_values[input.test_param.name])
        except (KeyError, ValueError):
            return -1

    context = ExpressionContext(input_values, context)
    payload = {'context': context, 'no_replacement_value': no_replacement_value}
    for input in inputs.values():
        if isinstance(input, Repeat) or isinstance(input, UploadDataset):
            values = input_values[input.name] = input_values.get(input.name, [])
            for i, d in enumerate(values):
                d['__index__'] = i
                new_name_prefix = name_prefix + '%s_%d|' % (input.name, i)
                new_label_prefix = label_prefix + '%s %d > ' % (input.title, i + 1)
                visit_input_values(input.inputs, d, callback, new_name_prefix, new_label_prefix, parent_prefix=new_name_prefix, **payload)
        elif isinstance(input, Conditional):
            values = input_values[input.name] = input_values.get(input.name, {})
            new_name_prefix = name_prefix + input.name + '|'
            case_error = None if get_current_case(input, values) >= 0 else 'The selected case is unavailable/invalid.'
            callback_helper(input.test_param, values, new_name_prefix, label_prefix, parent_prefix=name_prefix, context=context, error=case_error)
            values['__current_case__'] = get_current_case(input, values)
            if values['__current_case__'] >= 0:
                visit_input_values(input.cases[values['__current_case__']].inputs, values, callback, new_name_prefix, label_prefix, parent_prefix=name_prefix, **payload)
        elif isinstance(input, Section):
            values = input_values[input.name] = input_values.get(input.name, {})
            new_name_prefix = name_prefix + input.name + '|'
            visit_input_values(input.inputs, values, callback, new_name_prefix, label_prefix, parent_prefix=name_prefix, **payload)
        else:
            callback_helper(input, input_values, name_prefix, label_prefix, parent_prefix=parent_prefix, context=context)


def check_param(trans, param, incoming_value, param_values):
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
            if is_runtime_value(value):
                return [runtime_to_json(value), None]
        value = param.from_json(value, trans, param_values)
        param.validate(value, trans)
    except ValueError as e:
        error = unicodify(e)
    return value, error


def params_to_strings(params, param_values, app, nested=False):
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
            value = params[key].value_to_basic(value, app)
        rval[key] = value if nested else str(dumps(value, sort_keys=True))
    return rval


def params_from_strings(params, param_values, app, ignore_errors=False):
    """
    Convert a dictionary of strings as produced by `params_to_strings`
    back into parameter values (decode the json representation and then
    allow each parameter to convert the basic types into the parameters
    preferred form).
    """
    rval = dict()
    param_values = param_values or {}
    for key, value in param_values.items():
        value = safe_loads(value)
        if key in params:
            value = params[key].value_from_basic(value, app, ignore_errors)
        rval[key] = value
    return rval


def params_to_incoming(incoming, inputs, input_values, app, name_prefix=""):
    """
    Given a tool's parameter definition (`inputs`) and a specific set of
    parameter `input_values` objects, populate `incoming` with the html values.

    Useful for e.g. the rerun function.
    """
    for input in inputs.values():
        if isinstance(input, Repeat) or isinstance(input, UploadDataset):
            for d in input_values[input.name]:
                index = d['__index__']
                new_name_prefix = name_prefix + '%s_%d|' % (input.name, index)
                params_to_incoming(incoming, input.inputs, d, app, new_name_prefix)
        elif isinstance(input, Conditional):
            values = input_values[input.name]
            current = values['__current_case__']
            new_name_prefix = name_prefix + input.name + '|'
            incoming[new_name_prefix + input.test_param.name] = values[input.test_param.name]
            params_to_incoming(incoming, input.cases[current].inputs, values, app, new_name_prefix)
        elif isinstance(input, Section):
            values = input_values[input.name]
            new_name_prefix = name_prefix + input.name + '|'
            params_to_incoming(incoming, input.inputs, values, app, new_name_prefix)
        else:
            value = input_values.get(input.name)
            incoming[name_prefix + input.name] = value


def update_dataset_ids(input_values, translate_values, src):

    def replace_dataset_ids(path, key, value):
        """Exchanges dataset_ids (HDA, LDA, HDCA, not Dataset) in input_values with dataset ids used in job."""
        current_case = input_values
        if key == 'id':
            for i, p in enumerate(path):
                if isinstance(current_case, (list, dict)):
                    current_case = current_case[p]
            if src == current_case.get('src'):
                return key, translate_values.get(current_case['id'], value)
        return key, value

    return remap(input_values, visit=replace_dataset_ids)


def populate_state(request_context, inputs, incoming, state, errors={}, prefix='', context=None, check=True):
    """
    Populates nested state dict from incoming parameter values.
    >>> from collections import OrderedDict
    >>> from xml.etree.ElementTree import XML
    >>> from galaxy.util.bunch import Bunch
    >>> from galaxy.tools.parameters.basic import TextToolParameter, BooleanToolParameter
    >>> from galaxy.tools.parameters.grouping import Repeat
    >>> trans = Bunch(workflow_building_mode=False)
    >>> a = TextToolParameter(None, XML('<param name="a"/>'))
    >>> b = Repeat()
    >>> b.min = 0
    >>> b.max = 1
    >>> c = TextToolParameter(None, XML('<param name="c"/>'))
    >>> d = Repeat()
    >>> d.min = 0
    >>> d.max = 1
    >>> e = TextToolParameter(None, XML('<param name="e"/>'))
    >>> f = Conditional()
    >>> g = BooleanToolParameter(None, XML('<param name="g"/>'))
    >>> h = TextToolParameter(None, XML('<param name="h"/>'))
    >>> i = TextToolParameter(None, XML('<param name="i"/>'))
    >>> b.name = 'b'
    >>> b.inputs = OrderedDict([('c', c), ('d', d)])
    >>> d.name = 'd'
    >>> d.inputs = OrderedDict([('e', e), ('f', f)])
    >>> f.test_param = g
    >>> f.name = 'f'
    >>> f.cases = [Bunch(value='true', inputs= { 'h': h }), Bunch(value='false', inputs= { 'i': i })]
    >>> inputs = OrderedDict([('a',a),('b',b)])
    >>> flat = OrderedDict([('a', 1), ('b_0|c', 2), ('b_0|d_0|e', 3), ('b_0|d_0|f|h', 4), ('b_0|d_0|f|g', True)])
    >>> state = OrderedDict()
    >>> populate_state(trans, inputs, flat, state, check=False)
    >>> print(state['a'])
    1
    >>> print(state['b'][0]['c'])
    2
    >>> print(state['b'][0]['d'][0]['e'])
    3
    >>> print(state['b'][0]['d'][0]['f']['h'])
    4
    """
    context = ExpressionContext(state, context)
    for input in inputs.values():
        state[input.name] = input.get_initial_value(request_context, context)
        key = prefix + input.name
        group_state = state[input.name]
        group_prefix = '%s|' % (key)
        if input.type == 'repeat':
            rep_index = 0
            del group_state[:]
            while True:
                rep_prefix = '%s_%d' % (key, rep_index)
                if not any(incoming_key.startswith(rep_prefix) for incoming_key in incoming.keys()) and rep_index >= input.min:
                    break
                if rep_index < input.max:
                    new_state = {'__index__' : rep_index}
                    group_state.append(new_state)
                    populate_state(request_context, input.inputs, incoming, new_state, errors, prefix=rep_prefix + '|', context=context, check=check)
                rep_index += 1
        elif input.type == 'conditional':
            if input.value_ref and not input.value_ref_in_group:
                test_param_key = prefix + input.test_param.name
            else:
                test_param_key = group_prefix + input.test_param.name
            test_param_value = incoming.get(test_param_key, group_state.get(input.test_param.name))
            value, error = check_param(request_context, input.test_param, test_param_value, context) if check else [test_param_value, None]
            if error:
                errors[test_param_key] = error
            else:
                try:
                    current_case = input.get_current_case(value)
                    group_state = state[input.name] = {}
                    populate_state(request_context, input.cases[current_case].inputs, incoming, group_state, errors, prefix=group_prefix, context=context, check=check)
                    group_state['__current_case__'] = current_case
                except Exception:
                    errors[test_param_key] = 'The selected case is unavailable/invalid.'
                    pass
            group_state[input.test_param.name] = value
        elif input.type == 'section':
            populate_state(request_context, input.inputs, incoming, group_state, errors, prefix=group_prefix, context=context, check=check)
        elif input.type == 'upload_dataset':
            file_count = input.get_file_count(request_context, context)
            while len(group_state) > file_count:
                del group_state[-1]
            while file_count > len(group_state):
                new_state = {'__index__' : len(group_state)}
                for upload_item in input.inputs.values():
                    new_state[upload_item.name] = upload_item.get_initial_value(request_context, context)
                group_state.append(new_state)
            for i, rep_state in enumerate(group_state):
                rep_index = rep_state['__index__']
                rep_prefix = '%s_%d|' % (key, rep_index)
                populate_state(request_context, input.inputs, incoming, rep_state, errors, prefix=rep_prefix, context=context, check=check)
        else:
            param_value = _get_incoming_value(incoming, key, state.get(input.name))
            value, error = check_param(request_context, input, param_value, context) if check else [param_value, None]
            if error:
                errors[key] = error
            state[input.name] = value


def _get_incoming_value(incoming, key, default):
    """
    Fetch value from incoming dict directly or check special nginx upload
    created variants of this key.
    """
    if '__' + key + '__is_composite' in incoming:
        composite_keys = incoming['__' + key + '__keys'].split()
        value = dict()
        for composite_key in composite_keys:
            value[composite_key] = incoming[key + '_' + composite_key]
        return value
    else:
        return incoming.get(key, default)

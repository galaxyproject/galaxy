"""
Classes encapsulating Galaxy tool parameters.
"""

from json import dumps
from typing import (
    cast,
    Dict,
    Optional,
    Union,
)

from boltons.iterutils import remap

from galaxy.util import unicodify
from galaxy.util.expressions import ExpressionContext
from galaxy.util.json import safe_loads
from .basic import (
    DataCollectionToolParameter,
    DataToolParameter,
    ParameterValueError,
    SelectToolParameter,
    ToolParameter,
)
from .grouping import (
    Conditional,
    Group,
    Repeat,
    Section,
    UploadDataset,
)
from .workflow_utils import (
    is_runtime_value,
    NO_REPLACEMENT,
    runtime_to_json,
)
from .wrapped import flat_to_nested_state
from .._types import (
    InputFormatT,
    ParameterValidationErrorsT,
    ToolStateDumpedToJsonInternalT,
    ToolStateDumpedToJsonT,
    ToolStateDumpedToStringsT,
    ToolStateJobInstancePopulatedT,
    ToolStateJobInstanceT,
)

REPLACE_ON_TRUTHY = object()

# Some tools use the code tag and access the code base, expecting certain tool parameters to be available here.
__all__ = ("DataCollectionToolParameter", "DataToolParameter", "SelectToolParameter")

ToolInputsT = Dict[str, Union[Group, ToolParameter]]


def visit_input_values(
    inputs,
    input_values,
    callback,
    name_prefix="",
    label_prefix="",
    parent_prefix="",
    context=None,
    no_replacement_value=REPLACE_ON_TRUTHY,
    replace_optional_connections=False,
    allow_case_inference=False,
    unset_value=None,
):
    """
    Given a tools parameter definition (`inputs`) and a specific set of
    parameter `values`, call `callback` for each non-grouping parameter,
    passing the parameter object, value, a constructed unique name,
    and a display label.

    If the callback returns a value, it will be replace the old value.

    >>> from galaxy.util import XML
    >>> from galaxy.util.bunch import Bunch
    >>> from galaxy.tools.parameters.basic import TextToolParameter, BooleanToolParameter
    >>> from galaxy.tools.parameters.grouping import Repeat
    >>> a = TextToolParameter(None, XML('<param name="a"/>'))
    >>> b = Repeat('b')
    >>> c = TextToolParameter(None, XML('<param name="c"/>'))
    >>> d = Repeat('d')
    >>> e = TextToolParameter(None, XML('<param name="e"/>'))
    >>> f = Conditional('f')
    >>> g = BooleanToolParameter(None, XML('<param name="g"/>'))
    >>> h = TextToolParameter(None, XML('<param name="h"/>'))
    >>> i = TextToolParameter(None, XML('<param name="i"/>'))
    >>> j = TextToolParameter(None, XML('<param name="j"/>'))
    >>> b.title = 'b'
    >>> b.inputs = dict([ ('c', c), ('d', d) ])
    >>> d.title = 'd'
    >>> d.inputs = dict([ ('e', e), ('f', f) ])
    >>> f.test_param = g
    >>> f.cases = [Bunch(value='true', inputs= {'h': h}), Bunch(value='false', inputs= { 'i': i })]
    >>>
    >>> def visitor(input, value, prefix, prefixed_name, prefixed_label, error, **kwargs):
    ...     print('name=%s, prefix=%s, prefixed_name=%s, prefixed_label=%s, value=%s' % (input.name, prefix, prefixed_name, prefixed_label, value))
    ...     if error:
    ...         print(error)
    >>> inputs = dict([('a', a),('b', b)])
    >>> nested = dict([('a', 1), ('b', [dict([('c', 3), ('d', [dict([ ('e', 5), ('f', dict([ ('g', True), ('h', 7)]))])])])])])
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
    >>> nested = dict([('b', [dict([( 'd', [dict([('f', dict([('g', True), ('h', 7)]))])])])])])
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
        value = input_values.get(input.name, unset_value)
        args = {
            "input": input,
            "parent": input_values,
            "value": value,
            "prefixed_name": f"{name_prefix}{input.name}",
            "prefixed_label": f"{label_prefix}{input.label or input.name}",
            "prefix": parent_prefix,
            "context": context,
            "error": error,
        }
        if input.name not in input_values:
            args["error"] = f"No value found for '{args.get('prefixed_label')}'."
        new_value = callback(**args)

        # is this good enough ? feels very ugh
        if new_value == [no_replacement_value]:
            # Single unspecified value in multiple="true" input with a single null input, pretend it's a singular value
            new_value = no_replacement_value
        if isinstance(new_value, list):
            # Maybe mixed input, I guess tool defaults don't really make sense here ?
            # Would e.g. be default dataset in multiple="true" input, you wouldn't expect the default to be inserted
            # if other inputs are connected and provided.
            new_value = [item if not item == no_replacement_value else None for item in new_value]

        if no_replacement_value is REPLACE_ON_TRUTHY:
            replace = bool(new_value)
        else:
            replace = new_value != no_replacement_value
        if replace:
            input_values[input.name] = new_value
        elif replace_optional_connections:
            # Only used in workflow context
            has_default = hasattr(input, "value")
            if new_value is value is NO_REPLACEMENT:
                # NO_REPLACEMENT means value was connected but left unspecified
                if has_default:
                    # Use default if we have one
                    input_values[input.name] = input.value
                else:
                    # Should fail if input is not optional and does not have default value
                    # Effectively however depends on parameter implementation.
                    # We might want to raise an exception here, instead of depending on a tool parameter value error.
                    input_values[input.name] = None

            elif is_runtime_value(value) and has_default:
                input_values[input.name] = input.value

    def get_current_case(input, input_values):
        test_parameter = input.test_param
        test_parameter_name = test_parameter.name
        try:
            if test_parameter_name not in input_values and allow_case_inference:
                return input.get_current_case(test_parameter.get_initial_value(None, input_values))
            else:
                return input.get_current_case(input_values[test_parameter_name])
        except (KeyError, ValueError):
            return -1

    context = ExpressionContext(input_values, context)
    payload = {
        "context": context,
        "no_replacement_value": no_replacement_value,
        "allow_case_inference": allow_case_inference,
        "unset_value": unset_value,
    }
    for input in inputs.values():
        if isinstance(input, Repeat) or isinstance(input, UploadDataset):
            values = input_values[input.name] = input_values.get(input.name, [])
            for i, d in enumerate(values):
                d["__index__"] = i
                new_name_prefix = name_prefix + "%s_%d|" % (input.name, i)
                new_label_prefix = label_prefix + "%s %d > " % (input.title, i + 1)
                visit_input_values(
                    input.inputs,
                    d,
                    callback,
                    new_name_prefix,
                    new_label_prefix,
                    parent_prefix=new_name_prefix,
                    **payload,
                )
        elif isinstance(input, Conditional):
            values = input_values[input.name] = input_values.get(input.name, {})
            new_name_prefix = f"{name_prefix + input.name}|"
            case_error = None if get_current_case(input, values) >= 0 else "The selected case is unavailable/invalid."
            callback_helper(
                input.test_param,
                values,
                new_name_prefix,
                label_prefix,
                parent_prefix=name_prefix,
                context=context,
                error=case_error,
            )
            values["__current_case__"] = get_current_case(input, values)
            if values["__current_case__"] >= 0:
                visit_input_values(
                    input.cases[values["__current_case__"]].inputs,
                    values,
                    callback,
                    new_name_prefix,
                    label_prefix,
                    parent_prefix=name_prefix,
                    **payload,
                )
        elif isinstance(input, Section):
            values = input_values[input.name] = input_values.get(input.name, {})
            new_name_prefix = f"{name_prefix + input.name}|"
            visit_input_values(
                input.inputs, values, callback, new_name_prefix, label_prefix, parent_prefix=name_prefix, **payload
            )
        else:
            callback_helper(
                input, input_values, name_prefix, label_prefix, parent_prefix=parent_prefix, context=context
            )


def check_param(trans, param, incoming_value, param_values, simple_errors=True):
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
        if simple_errors:
            error = unicodify(e)
        else:
            error = e
    return value, error


def params_to_json_internal(
    params: ToolInputsT, param_values: ToolStateJobInstancePopulatedT, app
) -> ToolStateDumpedToJsonInternalT:
    """Return ToolStateDumpedToJsonT for supplied validated and populated parameters."""
    return cast(
        ToolStateDumpedToJsonInternalT, params_to_strings(params, param_values, app, nested=True, use_security=False)
    )


def params_to_json(params: ToolInputsT, param_values: ToolStateJobInstancePopulatedT, app) -> ToolStateDumpedToJsonT:
    """Return ToolStateDumpedToJsonT for supplied validated and populated parameters."""
    return cast(ToolStateDumpedToJsonT, params_to_strings(params, param_values, app, nested=True, use_security=True))


def params_to_strings(
    params: ToolInputsT,
    param_values: ToolStateJobInstancePopulatedT,
    app,
    nested=False,
    use_security=False,
) -> Union[ToolStateDumpedToJsonT, ToolStateDumpedToJsonInternalT, ToolStateDumpedToStringsT]:
    """
    Convert a dictionary of parameter values to a dictionary of strings
    suitable for persisting. The `value_to_basic` method of each parameter
    is called to convert its value to basic types, the result of which
    is then json encoded (this allowing complex nested parameters and
    such). If `nested` this will remain as a sort of JSON-ifiable dictionary
    (ToolStateDumpedToJsonT), otherwise these will dumped into strings of the
    JSON (ToolStateDumpedToStringsT). If use_security is False, this will return
    object references with decoded (integer) IDs, otherwise they will be encoded
    strings.
    """
    rval = {}
    for key, value in param_values.items():
        if key in params:
            value = params[key].value_to_basic(value, app, use_security=use_security)
        rval[key] = value if nested or value is None else str(dumps(value, sort_keys=True))
    return rval


def params_from_strings(params: Dict[str, Union[Group, ToolParameter]], param_values, app, ignore_errors=False) -> Dict:
    """
    Convert a dictionary of strings as produced by `params_to_strings`
    back into parameter values (decode the json representation and then
    allow each parameter to convert the basic types into the parameters
    preferred form).
    """
    rval = {}
    param_values = param_values or {}
    for key, value in param_values.items():
        param = params.get(key)
        if not param or not (param.type == "text" and value == "null"):
            # safe_loads attempts to handle some, but not all divergent handling
            # between JSON types and python types. TODO: We should let the
            # parameters handle all conversion, since they know what is an
            # appropriate coercion between types. e.g 'false' should be a string
            # in a text parameter, while it should be a boolean in a boolean parameter.
            # This would resolve a lot of back and forth in the various to/from methods.
            value = safe_loads(value)
        if param:
            try:
                value = param.value_from_basic(value, app, ignore_errors)
            except ParameterValueError:
                continue
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
                index = d["__index__"]
                new_name_prefix = name_prefix + "%s_%d|" % (input.name, index)
                params_to_incoming(incoming, input.inputs, d, app, new_name_prefix)
        elif isinstance(input, Conditional):
            values = input_values[input.name]
            current = values["__current_case__"]
            new_name_prefix = f"{name_prefix + input.name}|"
            incoming[new_name_prefix + input.test_param.name] = values[input.test_param.name]
            params_to_incoming(incoming, input.cases[current].inputs, values, app, new_name_prefix)
        elif isinstance(input, Section):
            values = input_values[input.name]
            new_name_prefix = f"{name_prefix + input.name}|"
            params_to_incoming(incoming, input.inputs, values, app, new_name_prefix)
        else:
            value = input_values.get(input.name)
            incoming[name_prefix + input.name] = value


def update_dataset_ids(input_values, translate_values, src):
    def replace_dataset_ids(path, key, value):
        """Exchanges dataset_ids (HDA, LDA, HDCA, not Dataset) in input_values with dataset ids used in job."""
        current_case = input_values
        if key == "id":
            for p in path:
                if isinstance(current_case, (list, dict)):
                    current_case = current_case[p]
            if src == current_case.get("src"):
                return key, translate_values.get(current_case["id"], value)
        return key, value

    return remap(input_values, visit=replace_dataset_ids)


def populate_state(
    request_context,
    inputs: ToolInputsT,
    incoming: ToolStateJobInstanceT,
    state: ToolStateJobInstancePopulatedT,
    errors: Optional[ParameterValidationErrorsT] = None,
    context=None,
    check=True,
    simple_errors=True,
    input_format: InputFormatT = "legacy",
):
    """
    Populates nested state dict from incoming parameter values.
    """
    if errors is None:
        errors = {}
    if input_format == "legacy":
        _populate_state_legacy(
            request_context,
            inputs,
            incoming,
            state,
            errors=errors,
            context=context,
            check=check,
            simple_errors=simple_errors,
        )
        return
    elif input_format == "21.01":
        context = ExpressionContext(state, context)
        for input in inputs.values():
            state[input.name] = input.get_initial_value(request_context, context)
            group_state = state[input.name]
            if input.type == "repeat":
                repeat_input = cast(Repeat, input)
                repeat_name = repeat_input.name
                repeat_incoming = incoming.get(repeat_name) or []
                if repeat_incoming and (
                    len(repeat_incoming) > repeat_input.max or len(repeat_incoming) < repeat_input.min
                ):
                    errors[repeat_name] = "The number of repeat elements is outside the range specified by the tool."
                else:
                    del group_state[:]
                    for rep in repeat_incoming:
                        new_state: ToolStateJobInstancePopulatedT = {}
                        group_state.append(new_state)
                        repeat_errors: ParameterValidationErrorsT = {}
                        populate_state(
                            request_context,
                            repeat_input.inputs,
                            rep,
                            new_state,
                            repeat_errors,
                            context=context,
                            check=check,
                            simple_errors=simple_errors,
                            input_format=input_format,
                        )
                        if repeat_errors:
                            errors[repeat_input.name] = repeat_errors

            elif input.type == "conditional":
                conditional_input = cast(Conditional, input)
                test_param = cast(ToolParameter, conditional_input.test_param)
                test_param_value = incoming.get(conditional_input.name, {}).get(test_param.name)
                value, error = (
                    check_param(request_context, test_param, test_param_value, context, simple_errors=simple_errors)
                    if check
                    else [test_param_value, None]
                )
                if error:
                    errors[test_param.name] = error
                else:
                    try:
                        current_case = conditional_input.get_current_case(value)
                        group_state = state[conditional_input.name] = {}
                        cast_errors: ParameterValidationErrorsT = {}
                        incoming_for_conditional = cast(
                            ToolStateJobInstanceT, incoming.get(conditional_input.name) or {}
                        )
                        populate_state(
                            request_context,
                            conditional_input.cases[current_case].inputs,
                            incoming_for_conditional,
                            group_state,
                            cast_errors,
                            context=context,
                            check=check,
                            simple_errors=simple_errors,
                            input_format=input_format,
                        )
                        if cast_errors:
                            errors[conditional_input.name] = cast_errors
                        group_state["__current_case__"] = current_case
                    except Exception:
                        errors[test_param.name] = "The selected case is unavailable/invalid."
                group_state[test_param.name] = value

            elif input.type == "section":
                section_input = cast(Section, input)
                section_errors: ParameterValidationErrorsT = {}
                incoming_for_state = cast(ToolStateJobInstanceT, incoming.get(section_input.name) or {})
                populate_state(
                    request_context,
                    section_input.inputs,
                    incoming_for_state,
                    group_state,
                    section_errors,
                    context=context,
                    check=check,
                    simple_errors=simple_errors,
                    input_format=input_format,
                )
                if section_errors:
                    errors[section_input.name] = section_errors

            elif input.type == "upload_dataset":
                raise NotImplementedError

            else:
                param_value = _get_incoming_value(incoming, input.name, state.get(input.name))
                value, error = (
                    check_param(request_context, input, param_value, context, simple_errors=simple_errors)
                    if check
                    else [param_value, None]
                )
                if error:
                    errors[input.name] = error
                state[input.name] = value
    else:
        raise Exception(f"Input format {input_format} not recognized; input_format must be either legacy or 21.01.")


def _populate_state_legacy(
    request_context,
    inputs: ToolInputsT,
    incoming: ToolStateJobInstanceT,
    state: ToolStateJobInstancePopulatedT,
    errors,
    prefix="",
    context=None,
    check=True,
    simple_errors=True,
):
    if context is None:
        context = flat_to_nested_state(incoming)
    context = ExpressionContext(state, context)
    for input in inputs.values():
        state[input.name] = input.get_initial_value(request_context, context)
        key = prefix + input.name
        group_state = state[input.name]
        group_prefix = f"{key}|"
        if input.type == "repeat":
            repeat_input = cast(Repeat, input)
            rep_index = 0
            del group_state[:]
            while True:
                rep_prefix = "%s_%d" % (key, rep_index)
                rep_min_default = repeat_input.default if repeat_input.default > repeat_input.min else repeat_input.min
                if (
                    not any(incoming_key.startswith(rep_prefix) for incoming_key in incoming.keys())
                    and rep_index >= rep_min_default
                ):
                    break
                if rep_index < repeat_input.max:
                    new_state: ToolStateJobInstancePopulatedT = {"__index__": rep_index}
                    group_state.append(new_state)
                    _populate_state_legacy(
                        request_context,
                        repeat_input.inputs,
                        incoming,
                        new_state,
                        errors,
                        prefix=f"{rep_prefix}|",
                        context=context,
                        check=check,
                        simple_errors=simple_errors,
                    )
                rep_index += 1
        elif input.type == "conditional":
            conditional_input = cast(Conditional, input)
            test_param = cast(ToolParameter, conditional_input.test_param)
            if conditional_input.value_ref and not conditional_input.value_ref_in_group:
                test_param_key = prefix + test_param.name
            else:
                test_param_key = group_prefix + test_param.name
            test_param_value = incoming.get(test_param_key, group_state.get(test_param.name))
            value, error = (
                check_param(
                    request_context,
                    test_param,
                    test_param_value,
                    context,
                    simple_errors=simple_errors,
                )
                if check
                else [test_param_value, None]
            )
            if error:
                errors[test_param_key] = error
            else:
                try:
                    current_case = conditional_input.get_current_case(value)
                    group_state = state[conditional_input.name] = cast(ToolStateJobInstancePopulatedT, {})
                    _populate_state_legacy(
                        request_context,
                        conditional_input.cases[current_case].inputs,
                        incoming,
                        group_state,
                        errors,
                        prefix=group_prefix,
                        context=context,
                        check=check,
                        simple_errors=simple_errors,
                    )
                    group_state["__current_case__"] = current_case
                except Exception:
                    errors[test_param_key] = "The selected case is unavailable/invalid."
            group_state[test_param.name] = value
        elif input.type == "section":
            section_input = cast(Section, input)
            _populate_state_legacy(
                request_context,
                section_input.inputs,
                incoming,
                group_state,
                errors,
                prefix=group_prefix,
                context=context,
                check=check,
                simple_errors=simple_errors,
            )
        elif input.type == "upload_dataset":
            dataset_input = cast(UploadDataset, input)
            file_count = dataset_input.get_file_count(request_context, context)
            while len(group_state) > file_count:
                del group_state[-1]
            while file_count > len(group_state):
                new_state_upload: ToolStateJobInstancePopulatedT = {"__index__": len(group_state)}
                for upload_item in dataset_input.inputs.values():
                    new_state_upload[upload_item.name] = upload_item.get_initial_value(request_context, context)
                group_state.append(new_state_upload)
            for rep_index, rep_state in enumerate(group_state):
                rep_index = rep_state.get("__index__", rep_index)
                rep_prefix = "%s_%d|" % (key, rep_index)
                _populate_state_legacy(
                    request_context,
                    dataset_input.inputs,
                    incoming,
                    rep_state,
                    errors,
                    prefix=rep_prefix,
                    context=context,
                    check=check,
                    simple_errors=simple_errors,
                )
        else:
            param_value = _get_incoming_value(incoming, key, state.get(input.name))
            value, error = (
                check_param(request_context, input, param_value, context, simple_errors=simple_errors)
                if check
                else [param_value, None]
            )
            if error:
                errors[key] = error
            state[input.name] = value


def _get_incoming_value(incoming, key, default):
    """
    Fetch value from incoming dict directly or check special nginx upload
    created variants of this key.
    """
    if f"__{key}__is_composite" in incoming:
        composite_keys = incoming[f"__{key}__keys"].split()
        value = {}
        for composite_key in composite_keys:
            value[composite_key] = incoming[f"{key}_{composite_key}"]
        return value
    else:
        return incoming.get(key, default)

import logging

log = logging.getLogger(__name__)

SKIP_INPUT = object()


def json_wrap(inputs, input_values, as_dict=None, handle_files="SKIP"):
    if as_dict is None:
        as_dict = {}

    for input in inputs.values():
        input_name = input.name
        value = input_values[input_name]
        json_value = _json_wrap_input(input, value, handle_files=handle_files)
        if json_value is SKIP_INPUT:
            continue
        as_dict[input_name] = json_value
    return as_dict


def _json_wrap_input(input, value, handle_files="SKIP"):
    input_type = input.type
    if input_type == "repeat":
        repeat_job_value = []
        for d in value:
            repeat_instance_job_value = {}
            json_wrap(input.inputs, d, repeat_instance_job_value)
            repeat_job_value.append(repeat_instance_job_value)
        json_value = repeat_job_value
    elif input_type == "conditional":
        values = value
        current = values["__current_case__"]
        conditional_job_value = {}
        json_wrap(input.cases[current].inputs, values, conditional_job_value)
        test_param = input.test_param
        test_param_name = test_param.name
        test_value = _json_wrap_input(test_param, values[test_param_name])
        conditional_job_value[test_param_name] = test_value
        json_value = conditional_job_value
    elif input_type == "section":
        values = value
        section_job_value = {}
        json_wrap(input.inputs, values, section_job_value)
        json_value = section_job_value
    elif input_type == "data" and input.multiple:
        if handle_files == "SKIP":
            return SKIP_INPUT
        raise NotImplementedError()
    elif input_type == "data":
        if handle_files == "SKIP":
            return SKIP_INPUT
        raise NotImplementedError()
    elif input_type == "data_collection":
        if handle_files == "SKIP":
            return SKIP_INPUT
        raise NotImplementedError()
    elif input_type in ["select", "text", "color", "hidden"]:
        json_value = _cast_if_not_none(value, str)
    elif input_type == "float":
        json_value = _cast_if_not_none(value, float, empty_to_none=True)
    elif input_type == "integer":
        json_value = _cast_if_not_none(value, int, empty_to_none=True)
    elif input_type == "boolean":
        json_value = _cast_if_not_none(value, bool)
    elif input_type == "data_column":
        # value is a SelectToolParameterWrapper()
        json_value = [int(_) for _ in _cast_if_not_none(value.value, list)]
    else:
        raise NotImplementedError("input_type [%s] not implemented" % input_type)

    return json_value


def _cast_if_not_none(value, cast_to, empty_to_none=False):
    # log.debug("value [%s], type[%s]" % (value, type(value)))
    if value is None or (empty_to_none and str(value) == ''):
        return None
    else:
        return cast_to(value)


__all__ = ('json_wrap', )

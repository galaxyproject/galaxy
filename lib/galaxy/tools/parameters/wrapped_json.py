import logging
log = logging.getLogger(__name__)


def json_wrap(inputs, input_values, as_dict=None, handle_files="SKIP"):
    if as_dict is None:
        as_dict = {}

    for input in inputs.itervalues():
        input_name = input.name
        input_type = input.type
        value = input_values[input_name]
        if input_type == "repeat":
            repeat_job_value = []
            for d in input_values[input.name]:
                repeat_instance_job_value = {}
                json_wrap(input.inputs, d, repeat_instance_job_value)
                repeat_job_value.append(repeat_instance_job_value)
            as_dict[input_name] = repeat_job_value
        if input_type == "conditional":
            values = input_values[input_name]
            current = values["__current_case__"]
            conditional_job_value = {}
            json_wrap(input.cases[current].inputs, values, conditional_job_value)
            as_dict[input_name] = conditional_job_value
        if input_type == "section":
            values = input_values[input_name]
            section_job_value = {}
            json_wrap(input.inputs, values, section_job_value)
            as_dict[input_name] = section_job_value
        elif input_type == "data" and input.multiple:
            if handle_files == "SKIP":
                continue
            raise NotImplementedError()
        elif input_type == "data":
            if handle_files == "SKIP":
                continue
            raise NotImplementedError()
        elif input_type == "data_collection":
            if handle_files == "SKIP":
                continue
            raise NotImplementedError()
        elif input_type == "select" or input_type == "text":
            value = input_values[input_name]
            json_value = _cast_if_not_none(value, str)
            as_dict[input_name] = json_value
        elif input_type == "float":
            value = input_values[input_name]
            json_value = _cast_if_not_none(value, float, empty_to_none=True)
            as_dict[input_name] = json_value
        elif input_type == "integer":
            value = input_values[input_name]
            json_value = _cast_if_not_none(value, int, empty_to_none=True)
            as_dict[input_name] = json_value
        elif input_type == "boolean":
            value = input_values[input_name]
            json_value = _cast_if_not_none(value, bool)
            as_dict[input_name] = json_value
        else:
            raise NotImplementedError("input_type [%s] not implemented" % input_type)
    return as_dict


def _cast_if_not_none(value, cast_to, empty_to_none=False):
    # log.debug("value [%s], type[%s]" % (value, type(value)))
    if value is None or (empty_to_none and str(value) == ''):
        return None
    else:
        return cast_to(value)


__all__ = ['json_wrap']

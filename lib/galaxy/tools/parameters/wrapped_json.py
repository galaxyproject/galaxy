import json
import logging
from typing import (
    Any,
    Dict,
    List,
    Sequence,
    TYPE_CHECKING,
)

from packaging.version import Version

if TYPE_CHECKING:
    from galaxy.tools.parameters.wrappers import (
        DatasetCollectionWrapper,
        DatasetFilenameWrapper,
    )

log = logging.getLogger(__name__)

SKIP_INPUT = object()


def json_wrap(inputs, input_values, profile, as_dict=None, handle_files="skip"):
    if as_dict is None:
        as_dict = {}

    for input in inputs.values():
        input_name = input.name
        value_wrapper = input_values[input_name]
        json_value = _json_wrap_input(input, value_wrapper, profile, handle_files=handle_files)
        if json_value is SKIP_INPUT:
            continue
        as_dict[input_name] = json_value
    return as_dict


def data_input_to_path(v):
    path = _cast_if_not_none(v, str)
    if path == "None":
        path = None
    return path


def data_collection_input_to_path(v):
    return v.all_paths


def data_collection_input_to_staging_path_and_source_path(
    v: "DatasetCollectionWrapper", invalid_chars: Sequence[str] = ("/",), include_collection_name: bool = False
) -> List[Dict[str, Any]]:
    staging_paths = v.get_all_staging_paths(
        invalid_chars=invalid_chars, include_collection_name=include_collection_name
    )
    if v.element_identifiers_extensions_paths_and_metadata_files:
        element_identifiers, extensions, source_paths, metadata_files = zip(
            *v.element_identifiers_extensions_paths_and_metadata_files
        )
    else:
        element_identifiers, extensions, source_paths, metadata_files = (), (), (), ()
    return [
        {
            "element_identifier": element_identifier,
            "ext": extension,
            "staging_path": staging_path,
            "source_path": source_path,
            "metadata_files": [
                {"staging_path": f"{staging_path}.{mf[0]}", "source_path": mf[1]} for mf in metadata_files
            ],
        }
        for element_identifier, extension, staging_path, source_path, metadata_files in zip(
            element_identifiers, extensions, staging_paths, source_paths, metadata_files
        )
    ]


def data_input_to_staging_path_and_source_path(
    v: "DatasetFilenameWrapper", invalid_chars: Sequence[str] = ("/",)
) -> Dict[str, Any]:
    staging_path = v.get_staging_path(invalid_chars=invalid_chars)
    # note that the element identifier should be always a list
    return {
        "element_identifier": [v.element_identifier],
        "ext": v.file_ext,
        "staging_path": staging_path,
        "source_path": data_input_to_path(v),
        "metadata_files": [
            {"staging_path": f"{staging_path}.{mf[0]}", "source_path": mf[1]} for mf in v.all_metadata_files
        ],
    }


def _json_wrap_input(input, value_wrapper, profile, handle_files="skip"):
    input_type = input.type

    if input_type == "repeat":
        repeat_job_value = []
        for d in value_wrapper:
            repeat_instance_job_value = {}
            json_wrap(input.inputs, d, profile, repeat_instance_job_value, handle_files=handle_files)
            repeat_job_value.append(repeat_instance_job_value)
        json_value = repeat_job_value
    elif input_type == "conditional":
        values = value_wrapper
        current = values["__current_case__"]
        conditional_job_value = {}
        json_wrap(input.cases[current].inputs, values, profile, conditional_job_value, handle_files=handle_files)
        test_param = input.test_param
        test_param_name = test_param.name
        test_value = _json_wrap_input(test_param, values[test_param_name], profile, handle_files=handle_files)
        conditional_job_value[test_param_name] = test_value
        json_value = conditional_job_value
    elif input_type == "section":
        values = value_wrapper
        section_job_value = {}
        json_wrap(input.inputs, values, profile, section_job_value, handle_files=handle_files)
        json_value = section_job_value
    elif input_type == "data" and input.multiple:
        if handle_files == "paths":
            json_value = [data_input_to_path(v) for v in value_wrapper]
        elif handle_files == "staging_path_and_source_path":
            json_value = [data_input_to_staging_path_and_source_path(v) for v in value_wrapper]
        elif handle_files == "skip":
            return SKIP_INPUT
        else:
            raise NotImplementedError()
    elif input_type == "data":
        if handle_files == "paths":
            json_value = data_input_to_path(value_wrapper)
        elif handle_files == "staging_path_and_source_path":
            json_value = data_input_to_staging_path_and_source_path(value_wrapper)
        elif handle_files == "skip":
            return SKIP_INPUT
        elif handle_files == "OBJECT":
            if value_wrapper:
                if isinstance(value_wrapper, list):
                    value_wrapper = value_wrapper[0]
                json_value = _hda_to_object(value_wrapper)
                if input.load_contents:
                    with open(str(value_wrapper), mode="rb") as fh:
                        json_value["contents"] = fh.read(input.load_contents).decode("utf-8", errors="replace")
                return json_value
            else:
                return None
        else:
            raise NotImplementedError()
    elif input_type == "data_collection":
        if handle_files == "skip":
            return SKIP_INPUT
        elif handle_files == "paths":
            return data_collection_input_to_path(value_wrapper)
        elif handle_files == "staging_path_and_source_path":
            return data_collection_input_to_staging_path_and_source_path(value_wrapper)
        raise NotImplementedError()
    elif input_type in ["text", "color", "hidden"]:
        if getattr(input, "optional", False) and value_wrapper is not None and value_wrapper.value is None:
            json_value = None
        else:
            json_value = _cast_if_not_none(value_wrapper, str)
    elif input_type == "float":
        json_value = _cast_if_not_none(value_wrapper, float, empty_to_none=True)
    elif input_type == "integer":
        json_value = _cast_if_not_none(value_wrapper, int, empty_to_none=True)
    elif input_type == "boolean":
        if input.optional and value_wrapper is not None and value_wrapper.value is None:
            json_value = None
        else:
            json_value = _cast_if_not_none(value_wrapper, bool, empty_to_none=input.optional)
    elif input_type == "select":
        if Version(str(profile)) < Version("20.05"):
            json_value = _cast_if_not_none(value_wrapper, str)
        else:
            if input.multiple:
                json_value = [str(_) for _ in _cast_if_not_none(value_wrapper.value, list)]
            else:
                json_value = _cast_if_not_none(value_wrapper.value, str)
    elif input_type == "data_column":
        # value is a SelectToolParameterWrapper()
        if input.multiple:
            json_value = [int(_) for _ in _cast_if_not_none(value_wrapper.value, list)]
        else:
            json_value = [_cast_if_not_none(value_wrapper.value, int)]
    elif input_type == "directory_uri":
        json_value = _cast_if_not_none(value_wrapper, str)
    else:
        raise NotImplementedError(f"input_type [{input_type}] not implemented")

    return json_value


def _hda_to_object(hda):
    if hda.extension == "expression.json":
        # We may have a null data value
        with open(str(hda)) as inp:
            try:
                rval = json.loads(inp.read(5))
                if rval is None:
                    return rval
            except Exception:
                pass
    hda_dict = hda.to_dict()
    metadata_dict = {}

    for key, value in hda_dict.items():
        if key.startswith("metadata_"):
            metadata_dict[key[len("metadata_") :]] = value

    return {
        "file_ext": hda_dict["file_ext"],
        "file_size": hda_dict["file_size"],
        "name": hda_dict["name"],
        "metadata": metadata_dict,
        "src": {"src": "hda", "id": hda.id},
    }


def _cast_if_not_none(value, cast_to, empty_to_none=False):
    # log.debug("value [%s], type[%s]" % (value, type(value)))
    if value is None or (empty_to_none and str(value) == ""):
        return None
    else:
        return cast_to(value)


__all__ = ("json_wrap",)

from galaxy.tools.parameters.basic import (
    DataCollectionToolParameter,
    DataToolParameter,
    SelectToolParameter,
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    Repeat,
    Section,
)
from galaxy.tools.wrappers import (
    DatasetCollectionWrapper,
    DatasetFilenameWrapper,
    DatasetListWrapper,
    ElementIdentifierMapper,
    InputValueWrapper,
    SelectToolParameterWrapper,
)

PARAMS_UNWRAPPED = object()


def copy_identifiers(source, destination):
    if isinstance(source, dict):
        for k, v in source.items():
            if k.endswith("|__identifier__"):
                if isinstance(destination, dict):
                    destination[k] = v


class WrappedParameters:
    def __init__(self, trans, tool, incoming, input_datasets=None):
        self.trans = trans
        self.tool = tool
        self.incoming = incoming
        self._params = PARAMS_UNWRAPPED
        self._input_datasets = input_datasets

    @property
    def params(self):
        if self._params is PARAMS_UNWRAPPED:
            params = make_dict_copy(self.incoming)
            self.wrap_values(self.tool.inputs, params, skip_missing_values=not self.tool.check_values)
            self._params = params
        return self._params

    def wrap_values(self, inputs, input_values, skip_missing_values=False):
        trans = self.trans
        tool = self.tool
        incoming = self.incoming

        element_identifier_mapper = ElementIdentifierMapper(self._input_datasets)

        # Wrap tool inputs as necessary
        for input in inputs.values():
            if input.name not in input_values and skip_missing_values:
                continue
            value = input_values[input.name]
            copy_identifiers(destination=value, source=input_values)
            if isinstance(input, Repeat):
                for d in value:
                    copy_identifiers(destination=d, source=value)
                    self.wrap_values(input.inputs, d, skip_missing_values=skip_missing_values)
            elif isinstance(input, Conditional):
                values = value
                current = values["__current_case__"]
                self.wrap_values(input.cases[current].inputs, values, skip_missing_values=skip_missing_values)
            elif isinstance(input, Section):
                values = value
                self.wrap_values(input.inputs, values, skip_missing_values=skip_missing_values)
            elif isinstance(input, DataToolParameter) and input.multiple:
                dataset_instances = DatasetListWrapper.to_dataset_instances(value)
                input_values[input.name] = DatasetListWrapper(
                    None,
                    dataset_instances,
                    datatypes_registry=trans.app.datatypes_registry,
                    tool=tool,
                    name=input.name,
                    formats=input.formats,
                )
            elif isinstance(input, DataToolParameter):
                wrapper_kwds = dict(
                    datatypes_registry=trans.app.datatypes_registry, tool=tool, name=input.name, formats=input.formats
                )
                element_identifier = element_identifier_mapper.identifier(value, input_values)
                if element_identifier:
                    wrapper_kwds["identifier"] = element_identifier

                input_values[input.name] = DatasetFilenameWrapper(value, **wrapper_kwds)
            elif isinstance(input, SelectToolParameter):
                input_values[input.name] = SelectToolParameterWrapper(input, value, other_values=incoming)
            elif isinstance(input, DataCollectionToolParameter):
                input_values[input.name] = DatasetCollectionWrapper(
                    None,
                    value,
                    datatypes_registry=trans.app.datatypes_registry,
                    tool=tool,
                    name=input.name,
                )
            else:
                input_values[input.name] = InputValueWrapper(input, value, incoming, tool.profile)


def make_dict_copy(from_dict):
    """
    Makes a copy of input dictionary from_dict such that all values that are dictionaries
    result in creation of a new dictionary ( a sort of deepcopy ).  We may need to handle
    other complex types ( e.g., lists, etc ), but not sure...
    Yes, we need to handle lists (and now are)...
    """
    copy_from_dict = {}
    for key, value in from_dict.items():
        if type(value).__name__ == "dict":
            copy_from_dict[key] = make_dict_copy(value)
        elif isinstance(value, list):
            copy_from_dict[key] = make_list_copy(value)
        else:
            copy_from_dict[key] = value
    return copy_from_dict


def make_list_copy(from_list):
    new_list = []
    for value in from_list:
        if isinstance(value, dict):
            new_list.append(make_dict_copy(value))
        elif isinstance(value, list):
            new_list.append(make_list_copy(value))
        else:
            new_list.append(value)
    return new_list


__all__ = ("WrappedParameters", "make_dict_copy")

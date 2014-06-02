import galaxy.tools

from galaxy.tools.parameters.basic import (
    DataToolParameter,
    DataCollectionToolParameter,
    SelectToolParameter,
)
from galaxy.tools.parameters.grouping import (
    Repeat,
    Conditional,
)
PARAMS_UNWRAPPED = object()


class WrappedParameters( object ):

    def __init__( self, trans, tool, incoming ):
        self.trans = trans
        self.tool = tool
        self.incoming = incoming
        self._params = PARAMS_UNWRAPPED

    @property
    def params( self ):
        if self._params is PARAMS_UNWRAPPED:
            params = make_dict_copy( self.incoming )
            self.wrap_values( self.tool.inputs, params, skip_missing_values=not self.tool.check_values )
            self._params = params
        return self._params

    def wrap_values( self, inputs, input_values, skip_missing_values=False ):
        trans = self.trans
        tool = self.tool
        incoming = self.incoming

        # Wrap tool inputs as necessary
        for input in inputs.itervalues():
            if input.name not in input_values and skip_missing_values:
                continue
            if isinstance( input, Repeat ):
                for d in input_values[ input.name ]:
                    self.wrap_values( input.inputs, d, skip_missing_values=skip_missing_values )
            elif isinstance( input, Conditional ):
                values = input_values[ input.name ]
                current = values[ "__current_case__" ]
                self.wrap_values( input.cases[current].inputs, values, skip_missing_values=skip_missing_values )
            elif isinstance( input, DataToolParameter ) and input.multiple:
                input_values[ input.name ] = \
                    galaxy.tools.DatasetListWrapper( input_values[ input.name ],
                                                     datatypes_registry=trans.app.datatypes_registry,
                                                     tool=tool,
                                                     name=input.name )
            elif isinstance( input, DataToolParameter ):
                input_values[ input.name ] = \
                    galaxy.tools.DatasetFilenameWrapper( input_values[ input.name ],
                                                         datatypes_registry=trans.app.datatypes_registry,
                                                         tool=tool,
                                                         name=input.name )
            elif isinstance( input, SelectToolParameter ):
                input_values[ input.name ] = galaxy.tools.SelectToolParameterWrapper( input, input_values[ input.name ], tool.app, other_values=incoming )
            elif isinstance( input, DataCollectionToolParameter ):
                input_values[ input.name ] = galaxy.tools.DatasetCollectionWrapper(
                    input_values[ input.name ],
                    datatypes_registry=trans.app.datatypes_registry,
                    tool=tool,
                    name=input.name,
                )
            else:
                input_values[ input.name ] = galaxy.tools.InputValueWrapper( input, input_values[ input.name ], incoming )


def make_dict_copy( from_dict ):
    """
    Makes a copy of input dictionary from_dict such that all values that are dictionaries
    result in creation of a new dictionary ( a sort of deepcopy ).  We may need to handle
    other complex types ( e.g., lists, etc ), but not sure...
    Yes, we need to handle lists (and now are)...
    """
    copy_from_dict = {}
    for key, value in from_dict.items():
        if type( value ).__name__ == 'dict':
            copy_from_dict[ key ] = make_dict_copy( value )
        elif isinstance( value, list ):
            copy_from_dict[ key ] = make_list_copy( value )
        else:
            copy_from_dict[ key ] = value
    return copy_from_dict


def make_list_copy( from_list ):
    new_list = []
    for value in from_list:
        if isinstance( value, dict ):
            new_list.append( make_dict_copy( value ) )
        elif isinstance( value, list ):
            new_list.append( make_list_copy( value ) )
        else:
            new_list.append( value )
    return new_list


__all__ = [ WrappedParameters, make_dict_copy ]

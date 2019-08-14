from collections import OrderedDict

def is_dict(item):
    return isinstance(item, dict) or isinstance(item, OrderedDict)


def _parse_name(name, argument):
    """Determine name of an input source from name and argument
    returns the name or if absent the argument property
    in the later case leading dashes are stripped and
    internal dashes are replaced by underscore
    """
    if name is None:
        if not argument:
            raise ValueError("parameter must specify a 'name' or 'argument'.")
        name = argument.lstrip('-').replace("-", "_")
    return name

import datetime
import uuid
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
)

ValueMapperT = Dict[str, Callable]


def dict_for(obj, **kwds):
    # Create dict to represent item.
    return dict(model_class=obj.__class__.__name__, **kwds)


class UsesDictVisibleKeys:
    """Mixin used to implement to_dict methods that consume dict_{view}_visible_keys to produce dicts.

    For typical to_dict methods that just consume a view and value mapper use the Dictifable mixin instead
    of this more low level mixin, but if you want to consume other things in your to_dict method that
    are incompatible (such as required arguments) - inherit this lower level mixin and implement a custom
    to_dict with whatever signature makes sense for the class.
    """

    def _dictify_view_keys(
        self, view: str = "collection", value_mapper: Optional[ValueMapperT] = None
    ) -> Dict[str, Any]:
        """
        Return item dictionary.
        """

        if not value_mapper:
            value_mapper = {}

        def get_value(key, item):
            """
            Recursive helper function to get item values.
            """
            # FIXME: why use exception here? Why not look for key in value_mapper
            # first and then default to to_dict?
            try:
                return item.to_dict(view=view, value_mapper=value_mapper)
            except Exception:
                assert value_mapper is not None
                if key in value_mapper:
                    return value_mapper[key](item)
                if isinstance(item, datetime.datetime):
                    return item.isoformat()
                elif isinstance(item, uuid.UUID):
                    return str(item)
                # Leaving this for future reference, though we may want a more
                # generic way to handle special type mappings going forward.
                # If the item is of a class that needs to be 'stringified' before being put into a JSON data structure
                # elif type(item) in []:
                #    return str(item)
                return item

        # Create dict to represent item.
        rval = dict_for(self)

        # Fill item dict with visible keys.
        try:
            visible_keys = self.__getattribute__(f"dict_{view}_visible_keys")
        except AttributeError:
            raise Exception(f"Unknown Dictifiable view: {view}")
        for key in visible_keys:
            try:
                item = self.__getattribute__(key)
                if isinstance(item, list):
                    rval[key] = []
                    for i in item:
                        rval[key].append(get_value(key, i))
                else:
                    rval[key] = get_value(key, item)
            except AttributeError:
                rval[key] = None

        return rval


class Dictifiable(UsesDictVisibleKeys):
    """Mixin that enables objects to be converted to dictionaries. This is useful
    when for sharing objects across boundaries, such as the API, tool scripts,
    and JavaScript code."""

    def to_dict(self, view: str = "collection", value_mapper: Optional[ValueMapperT] = None) -> Dict[str, Any]:
        """
        Return item dictionary.
        """
        return self._dictify_view_keys(view=view, value_mapper=value_mapper)

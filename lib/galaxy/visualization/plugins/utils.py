"""
Utilities for visualization plugins.
"""


# =============================================================================
class OpenObject(dict):
    # note: not a Bunch
    # TODO: move to util.data_structures
    """
    A dict that allows assignment and attribute retrieval using the dot
    operator.

    If an attribute isn't contained in the dict `None` is returned (no
    KeyError).
    JSON-serializable.
    """

    def __getitem__(self, key):
        if key not in self:
            return None
        return super().__getitem__(key)

    def __getattr__(self, key):
        return self.__getitem__(key)


# ------------------------------------------------------------------- misc
# TODO: move to utils?
def getattr_recursive(item, attr_key, *args):
    """
    Allows dot member notation in attribute name when getting an item's attribute.

    NOTE: also searches dictionaries
    """
    using_default = len(args) >= 1
    default = args[0] if using_default else None

    for attr_key in attr_key.split('.'):
        try:
            if isinstance(item, dict):
                item = item.__getitem__(attr_key)
            else:
                item = getattr(item, attr_key)

        except (KeyError, AttributeError):
            if using_default:
                return default
            raise

    return item


def hasattr_recursive(item, attr_key):
    """
    Allows dot member notation in attribute name when getting an item's attribute.

    NOTE: also searches dictionaries
    """
    if '.' in attr_key:
        attr_key, last_key = attr_key.rsplit('.', 1)
        item = getattr_recursive(item, attr_key, None)
        if item is None:
            return False
        attr_key = last_key

    try:
        if isinstance(item, dict):
            return item.__contains__(attr_key)
        else:
            return hasattr(item, attr_key)

    except (KeyError, AttributeError):
        return False

    return True

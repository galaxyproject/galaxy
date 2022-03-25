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

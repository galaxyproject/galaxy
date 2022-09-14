"""
Objects with No values
"""

from galaxy.model.metadata import MetadataCollection


class RecursiveNone:
    def __str__(self):
        return "None"

    def __repr__(self):
        return str(self)

    def __getattr__(self, name):
        value = RecursiveNone()
        setattr(self, name, value)
        return value

    def __bool__(self):
        return False

    __nonzero__ = __bool__


class NoneDataset(RecursiveNone):
    def __init__(self, datatypes_registry=None, ext="data", dbkey="?"):
        self.ext = self.extension = ext
        self.dbkey = dbkey
        assert datatypes_registry is not None
        self.datatype = datatypes_registry.get_datatype_by_extension(ext)
        self._metadata = None
        self.metadata = MetadataCollection(self)

    def __getattr__(self, name):
        return "None"

    def missing_meta(self):
        return False

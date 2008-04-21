"""
Objects with No values
"""
from galaxy.datatypes.metadata import MetadataCollection

class RecursiveNone:
    def __str__( self ):
        return "None"
    def __repr__( self ):
        return str( self )
    def __getattr__( self, name ):
        value = RecursiveNone()
        setattr( self, name, value )
        return value
    def __nonzero__( self ):
        return False

class NoneDataset( RecursiveNone ):
    def __init__( self, datatypes_registry = None, ext = 'data', dbkey = '?' ):
        self.ext = self.extension = ext
        self.dbkey = dbkey
        if datatypes_registry:
            self.datatype = datatypes_registry.get_datatype_by_extension( ext )
            self.metadata = MetadataCollection( self, self.datatype.metadata_spec )
    def missing_meta( self ):
        return False
        
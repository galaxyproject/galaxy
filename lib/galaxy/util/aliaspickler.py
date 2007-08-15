import pickle
from cStringIO import StringIO

class AliasUnpickler( pickle.Unpickler ):
    def __init__( self, aliases, *args, **kw):
        pickle.Unpickler.__init__( self, *args, **kw )
        self.aliases = aliases
    def find_class( self, module, name ):
        module, name = self.aliases.get((module,name), (module,name))
        return pickle.Unpickler.find_class( self, module, name )

class AliasPickleModule( object ):
    def __init__( self, aliases ):
        self.aliases = aliases
    def dump( self, obj, fileobj, protocol=0):
        return pickle.dump( obj, fileobj, protocol )
    def dumps( self, obj, protocol=0 ):
        return pickle.dumps( obj, protocol )
    def load( self, fileobj ):
        return AliasUnpickler( self.aliases, fileobj ).load()
    def loads( self, string ):
        fileobj = StringIO( string )
        return AliasUnpickler( self.aliases, fileobj ).load()

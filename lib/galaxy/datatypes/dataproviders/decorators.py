"""
DataProvider related decorators.
"""

# I'd like to decorate the factory methods that give data_providers by the name they can be accessed from. e.g.:
#@provides( 'id_seq' ) # where 'id_seq' is some 'data_format' string/alias
#def get_id_seq_provider( dataset, **settings ):

# then in some central dispatch (maybe data.Data), have it look up the proper method by the data_format string

# also it would be good to have this decorator maintain a list of available providers (for a datatype)

# i don't particularly want to cut up method names ( get_([\w_]*)_provider )
#!/usr/bin/env python

# adapted from: http://stackoverflow.com
#    /questions/14095616/python-can-i-programmatically-decorate-class-methods-from-a-class-instance

from functools import wraps
#from types import MethodType
import copy

import logging
log = logging.getLogger( __name__ )


# -----------------------------------------------------------------------------
_DATAPROVIDER_CLASS_MAP_KEY = 'dataproviders'
_DATAPROVIDER_METHOD_NAME_KEY = '_dataprovider_name'

# -----------------------------------------------------------------------------
def has_dataproviders( cls ):
    """
    Wraps a class (generally a Datatype), finds methods within that have been
    decorated with `@dataprovider` and adds them, by their name, to a map
    in the class.

    This allows a class to maintain a name -> method map, effectively
    'registering' dataprovider factory methods.

    .. example::
    @has_dataproviders
    class MyDtype( data.Data ):

        @dataprovider_factory( 'bler' )
        def provide_some_bler( self, dataset, **settings ):
            '''blerblerbler'''
            dataset_source = providers.DatasetDataProvider( dataset )
            # ... chain other, intermidiate providers here
            return providers.BlerDataProvider( dataset_source, **settings )

    # use the base method in data.Data
    provider = dataset.datatype.dataprovider( dataset, 'bler',
                                              my_setting='blah', ... )
    # OR directly from the map
    provider = dataset.datatype.dataproviders[ 'bler' ]( dataset,
                                                         my_setting='blah', ... )
    """
    #log.debug( 'has_dataproviders:', cls )
    # init the class dataproviders map if necc.
    if not hasattr( cls, _DATAPROVIDER_CLASS_MAP_KEY ):
        setattr( cls, _DATAPROVIDER_CLASS_MAP_KEY, {} )
    else:
        # need to deepcopy or subclasses will modify super.dataproviders as well
        existing_dataproviders = getattr( cls, _DATAPROVIDER_CLASS_MAP_KEY )
        copied_dataproviders = copy.deepcopy( existing_dataproviders )
        setattr( cls, _DATAPROVIDER_CLASS_MAP_KEY, copied_dataproviders )

    dataproviders = getattr( cls, _DATAPROVIDER_CLASS_MAP_KEY )

    # scan for methods with dataprovider names and add them to the map
    # note: this has a 'cascading' effect
    #       where it's possible to override a super's provider with a sub's
    for attr_key, attr_value in cls.__dict__.iteritems():
        #log.debug( '\t key:', attr_key )
        # can't use isinstance( attr_value, MethodType ) bc of wrapping
        if( ( callable( attr_value ) )
        and ( not attr_key.startswith( "__" ) )
        and ( getattr( attr_value, _DATAPROVIDER_METHOD_NAME_KEY, None ) ) ):
            #log.debug( '\t\t is a dataprovider', attr_key )
            name = getattr( attr_value, _DATAPROVIDER_METHOD_NAME_KEY )
            dataproviders[ name ] = attr_value

    #log.debug( 'dataproviders:' )
    #for name, fn in cls.dataproviders.items():
    #    log.debug( '\t ', name, '->', fn.__name__, fn )
    #    log.debug( '\t\t ', fn.__doc__ )
    return cls

def dataprovider_factory( name ):
    """
    Wraps a class method and marks it as a dataprovider factory.

    :param name: what name/key to register the factory under in `cls.dataproviders`
    :param type: any hashable var
    """
    #log.debug( 'dataprovider:', name )
    def named_dataprovider_factory( func ):
        #log.debug( 'named_dataprovider_factory:', name, '->', func.__name__ )
        setattr( func, _DATAPROVIDER_METHOD_NAME_KEY, name )
        #log.debug( '\t setting:', getattr( func, _DATAPROVIDER_METHOD_NAME_KEY ) )
        @wraps( func )
        def wrapped_dataprovider_factory( self, *args, **kwargs ):
            #log.debug( 'wrapped_dataprovider_factory', name, self, args, kwargs )
            return func( self, *args, **kwargs )
        return wrapped_dataprovider_factory
    return named_dataprovider_factory

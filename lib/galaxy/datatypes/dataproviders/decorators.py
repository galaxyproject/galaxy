"""
DataProvider related decorators.
"""

# I'd like to decorate the factory methods that give data_providers by the name they can be accessed from. e.g.:
# @provides( 'id_seq' ) # where 'id_seq' is some 'data_format' string/alias
# def get_id_seq_provider( dataset, **settings ):

# then in some central dispatch (maybe data.Data), have it look up the proper method by the data_format string

# also it would be good to have this decorator maintain a list of available providers (for a datatype)

# i don't particularly want to cut up method names ( get_([\w_]*)_provider )
# adapted from: http://stackoverflow.com
#    /questions/14095616/python-can-i-programmatically-decorate-class-methods-from-a-class-instance

import copy
import logging
from functools import wraps
from urllib.parse import unquote

log = logging.getLogger(__name__)

_DATAPROVIDER_CLASS_MAP_KEY = "dataproviders"
_DATAPROVIDER_METHOD_NAME_KEY = "_dataprovider_name"


def has_dataproviders(cls):
    """
    Wraps a class (generally a Datatype), finds methods within that have been
    decorated with `@dataprovider` and adds them, by their name, to a map
    in the class.

    This allows a class to maintain a name -> method map, effectively
    'registering' dataprovider factory methods::

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
    # init the class dataproviders map if necc.
    if not hasattr(cls, _DATAPROVIDER_CLASS_MAP_KEY):
        setattr(cls, _DATAPROVIDER_CLASS_MAP_KEY, {})
    else:
        # need to deepcopy or subclasses will modify super.dataproviders as well
        existing_dataproviders = getattr(cls, _DATAPROVIDER_CLASS_MAP_KEY)
        copied_dataproviders = copy.deepcopy(existing_dataproviders)
        setattr(cls, _DATAPROVIDER_CLASS_MAP_KEY, copied_dataproviders)

    dataproviders = getattr(cls, _DATAPROVIDER_CLASS_MAP_KEY)

    # scan for methods with dataprovider names and add them to the map
    # note: this has a 'cascading' effect
    #       where it's possible to override a super's provider with a sub's
    for attr_key, attr_value in cls.__dict__.items():
        # can't use isinstance( attr_value, MethodType ) bc of wrapping
        if (
            (callable(attr_value))
            and (not attr_key.startswith("__"))
            and (getattr(attr_value, _DATAPROVIDER_METHOD_NAME_KEY, None))
        ):
            name = getattr(attr_value, _DATAPROVIDER_METHOD_NAME_KEY)
            dataproviders[name] = attr_value
    return cls


def dataprovider_factory(name, settings=None):
    """
    Wraps a class method and marks it as a dataprovider factory and creates a
    function to parse query strings to __init__ arguments as the
    `parse_query_string_settings` attribute of the factory function.

    An example use of the `parse_query_string_settings`::

        kwargs = dataset.datatype.dataproviders[ provider ].parse_query_string_settings( query_kwargs )
        return list( dataset.datatype.dataprovider( dataset, provider, **kwargs ) )

    :param name: what name/key to register the factory under in `cls.dataproviders`
    :type name: any hashable var
    :param settings: dictionary containing key/type pairs for parsing query strings
        to __init__ arguments
    :type settings: dictionary
    """

    # TODO:?? use *args for settings allowing mulitple dictionaries
    # make a function available through the name->provider dispatch to parse query strings
    #   callable like:
    # settings_dict = dataproviders[ provider_name ].parse_query_string_settings( query_kwargs )
    # TODO: ugh - overly complicated but the best I could think of
    def parse_query_string_settings(query_kwargs):
        return _parse_query_string_settings(query_kwargs, settings)

    def named_dataprovider_factory(func):
        setattr(func, _DATAPROVIDER_METHOD_NAME_KEY, name)

        func.parse_query_string_settings = parse_query_string_settings
        func.settings = settings
        # TODO: I want a way to inherit settings from the previous provider( this_name ) instead of defining over and over

        @wraps(func)
        def wrapped_dataprovider_factory(self, *args, **kwargs):
            return func(self, *args, **kwargs)

        return wrapped_dataprovider_factory

    return named_dataprovider_factory


def _parse_query_string_settings(query_kwargs, settings=None):
    """
    Parse the values in `query_kwargs` from strings to the proper types
    listed in the same key in `settings`.
    """

    # TODO: this was a relatively late addition: review and re-think
    def list_from_query_string(s):
        # assume csv
        return s.split(",")

    parsers = {
        "int": int,
        "float": float,
        "bool": bool,
        "list:str": lambda s: list_from_query_string(s),
        "list:escaped": lambda s: [unquote(e) for e in list_from_query_string(s)],
        "list:int": lambda s: [int(i) for i in list_from_query_string(s)],
    }
    settings = settings or {}
    # yay! yet another set of query string parsers! <-- sarcasm
    # work through the keys in settings finding matching keys in query_kwargs
    #   if found in both, get the expected/needed type from settings and store the new parsed value
    #   if we can't parse it (no parser, bad value), delete the key from query_kwargs so the provider will use the defaults
    for key in settings:
        if key in query_kwargs:
            # TODO: this would be the place to sanitize any strings
            query_value = query_kwargs[key]
            needed_type = settings[key]
            if needed_type != "str":
                try:
                    query_kwargs[key] = parsers[needed_type](query_value)
                except (KeyError, ValueError):
                    del query_kwargs[key]

        # TODO:?? do we want to remove query_kwarg entries NOT in settings?
    return query_kwargs

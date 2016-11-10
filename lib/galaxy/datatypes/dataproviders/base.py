"""
Base class(es) for all DataProviders.
"""
# there's a blurry line between functionality here and functionality in datatypes module
# attempting to keep parsing to a minimum here and focus on chopping/pagination/reformat(/filtering-maybe?)
#   and using as much pre-computed info/metadata from the datatypes module as possible
# also, this shouldn't be a replacement/re-implementation of the tool layer
#   (which provides traceability/versioning/reproducibility)

import logging
from collections import deque

import six

from . import exceptions

log = logging.getLogger( __name__ )

_TODO = """
hooks into datatypes (define providers inside datatype modules) as factories
capture tell() when provider is done
    def stop( self ): self.endpoint = source.tell(); raise StopIteration()
implement __len__ sensibly where it can be (would be good to have where we're giving some progress - '100 of 300')
    seems like sniffed files would have this info
unit tests
add datum entry/exit point methods: possibly decode, encode
    or create a class that pipes source through - how would decode work then?

icorporate existing visualization/dataproviders
some of the sources (esp. in datasets) don't need to be re-created
YAGNI: InterleavingMultiSourceDataProvider, CombiningMultiSourceDataProvider

datasets API entry point:
    kwargs should be parsed from strings 2 layers up (in the DatasetsAPI) - that's the 'proper' place for that.
    but how would it know how/what to parse if it doesn't have access to the classes used in the provider?
        Building a giant list by sweeping all possible dprov classes doesn't make sense
    For now - I'm burying them in the class __init__s - but I don't like that
"""


# ----------------------------------------------------------------------------- base classes
class HasSettings( type ):
    """
    Metaclass for data providers that allows defining and inheriting
    a dictionary named 'settings'.

    Useful for allowing class level access to expected variable types
    passed to class `__init__` functions so they can be parsed from a query string.
    """
    # yeah - this is all too acrobatic
    def __new__( cls, name, base_classes, attributes ):
        settings = {}
        # get settings defined in base classes
        for base_class in base_classes:
            base_settings = getattr( base_class, 'settings', None )
            if base_settings:
                settings.update( base_settings )
        # get settings defined in this class
        new_settings = attributes.pop( 'settings', None )
        if new_settings:
            settings.update( new_settings )
        attributes[ 'settings' ] = settings
        return type.__new__( cls, name, base_classes, attributes )


# ----------------------------------------------------------------------------- base classes
@six.add_metaclass(HasSettings)
class DataProvider( six.Iterator ):
    """
    Base class for all data providers. Data providers:
        (a) have a source (which must be another file-like object)
        (b) implement both the iterator and context manager interfaces
        (c) do not allow write methods
            (but otherwise implement the other file object interface methods)
    """
    # a definition of expected types for keyword arguments sent to __init__
    #   useful for controlling how query string dictionaries can be parsed into correct types for __init__
    #   empty in this base class
    settings = {}

    def __init__( self, source, **kwargs ):
        """
        :param source: the source that this iterator will loop over.
            (Should implement the iterable interface and ideally have the
            context manager interface as well)
        """
        self.source = self.validate_source( source )

    def validate_source( self, source ):
        """
        Is this a valid source for this provider?

        :raises InvalidDataProviderSource: if the source is considered invalid.

        Meant to be overridden in subclasses.
        """
        if not source or not hasattr( source, '__iter__' ):
            # that's by no means a thorough check
            raise exceptions.InvalidDataProviderSource( source )
        return source

    # TODO: (this might cause problems later...)
    # TODO: some providers (such as chunk's seek and read) rely on this... remove
    def __getattr__( self, name ):
        if name == 'source':
            # if we're inside this fn, source hasn't been set - provide some safety just for this attr
            return None
        # otherwise, try to get the attr from the source - allows us to get things like provider.encoding, etc.
        if hasattr( self.source, name ):
            return getattr( self.source, name )
        # raise the proper error
        return self.__getattribute__( name )

    # write methods should not be allowed
    def truncate( self, size ):
        raise NotImplementedError( 'Write methods are purposely disabled' )

    def write( self, string ):
        raise NotImplementedError( 'Write methods are purposely disabled' )

    def writelines( self, sequence ):
        raise NotImplementedError( 'Write methods are purposely disabled' )

    # TODO: route read methods through next?
    # def readline( self ):
    #    return self.next()
    def readlines( self ):
        return [ line for line in self ]

    # iterator interface
    def __iter__( self ):
        # it's generators all the way up, Timmy
        with self:
            for datum in self.source:
                yield datum

    def __next__( self ):
        return next(self.source)

    # context manager interface
    def __enter__( self ):
        # make the source's context manager interface optional
        if hasattr( self.source, '__enter__' ):
            self.source.__enter__()
        return self

    def __exit__( self, *args ):
        # make the source's context manager interface optional, call on source if there
        if hasattr( self.source, '__exit__' ):
            self.source.__exit__( *args )
        # alternately, call close()
        elif hasattr( self.source, 'close' ):
            self.source.close()

    def __str__( self ):
        """
        String representation for easier debugging.

        Will call `__str__` on its source so this will display piped dataproviders.
        """
        # we need to protect against recursion (in __getattr__) if self.source hasn't been set
        source_str = str( self.source ) if hasattr( self, 'source' ) else ''
        return '%s(%s)' % ( self.__class__.__name__, str( source_str ) )


class FilteredDataProvider( DataProvider ):
    """
    Passes each datum through a filter function and yields it if that function
    returns a non-`None` value.

    Also maintains counters:
        - `num_data_read`: how many data have been consumed from the source.
        - `num_valid_data_read`: how many data have been returned from `filter`.
        - `num_data_returned`: how many data has this provider yielded.
    """
    # not useful here - we don't want functions over the query string
    # settings.update({ 'filter_fn': 'function' })

    def __init__( self, source, filter_fn=None, **kwargs ):
        """
        :param filter_fn: a lambda or function that will be passed a datum and
            return either the (optionally modified) datum or None.
        """
        super( FilteredDataProvider, self ).__init__( source, **kwargs )
        self.filter_fn = filter_fn if hasattr( filter_fn, '__call__' ) else None
        # count how many data we got from the source
        self.num_data_read = 0
        # how many valid data have we gotten from the source
        #   IOW, data that's passed the filter and been either provided OR have been skipped due to offset
        self.num_valid_data_read = 0
        # how many lines have been provided/output
        self.num_data_returned = 0

    def __iter__( self ):
        parent_gen = super( FilteredDataProvider, self ).__iter__()
        for datum in parent_gen:
            self.num_data_read += 1
            datum = self.filter( datum )
            if datum is not None:
                self.num_valid_data_read += 1
                self.num_data_returned += 1
                yield datum

    # TODO: may want to squash this into DataProvider
    def filter( self, datum ):
        """
        When given a datum from the provider's source, return None if the datum
        'does not pass' the filter or is invalid. Return the datum if it's valid.

        :param datum: the datum to check for validity.
        :returns: the datum, a modified datum, or None

        Meant to be overridden.
        """
        if self.filter_fn:
            return self.filter_fn( datum )
        # also can be overriden entirely
        return datum


class LimitedOffsetDataProvider( FilteredDataProvider ):
    """
    A provider that uses the counters from FilteredDataProvider to limit the
    number of data and/or skip `offset` number of data before providing.

    Useful for grabbing sections from a source (e.g. pagination).
    """
    # define the expected types of these __init__ arguments so they can be parsed out from query strings
    settings = {
        'limit' : 'int',
        'offset': 'int'
    }

    # TODO: may want to squash this into DataProvider
    def __init__( self, source, offset=0, limit=None, **kwargs ):
        """
        :param offset:  the number of data to skip before providing.
        :param limit:   the final number of data to provide.
        """
        super( LimitedOffsetDataProvider, self ).__init__( source, **kwargs )

        # how many valid data to skip before we start outputing data - must be positive
        #   (diff to support neg. indeces - must be pos.)
        self.offset = max( offset, 0 )

        # how many valid data to return - must be positive (None indicates no limit)
        self.limit = limit
        if self.limit is not None:
            self.limit = max( self.limit, 0 )

    def __iter__( self ):
        """
        Iterate over the source until `num_valid_data_read` is greater than
        `offset`, begin providing datat, and stop when `num_data_returned`
        is greater than `offset`.
        """
        if self.limit is not None and self.limit <= 0:
            return
            yield

        parent_gen = super( LimitedOffsetDataProvider, self ).__iter__()
        for datum in parent_gen:
            self.num_data_returned -= 1
            # print 'self.num_data_returned:', self.num_data_returned
            # print 'self.num_valid_data_read:', self.num_valid_data_read

            if self.num_valid_data_read > self.offset:
                self.num_data_returned += 1
                yield datum

            if self.limit is not None and self.num_data_returned >= self.limit:
                break

    # TODO: skipping lines is inefficient - somehow cache file position/line_num pair and allow provider
    #   to seek to a pos/line and then begin providing lines
    # the important catch here is that we need to have accurate pos/line pairs
    #   in order to preserve the functionality of limit and offset
    # if file_seek and len( file_seek ) == 2:
    #    seek_pos, new_line_num = file_seek
    #    self.seek_and_set_curr_line( seek_pos, new_line_num )

    # def seek_and_set_curr_line( self, file_seek, new_curr_line_num ):
    #    self.seek( file_seek, os.SEEK_SET )
    #    self.curr_line_num = new_curr_line_num


class MultiSourceDataProvider( DataProvider ):
    """
    A provider that iterates over a list of given sources and provides data
    from one after another.

    An iterator over iterators.
    """
    def __init__( self, source_list, **kwargs ):
        """
        :param source_list: an iterator of iterables
        """
        self.source_list = deque( source_list )

    def __iter__( self ):
        """
        Iterate over the source_list, then iterate over the data in each source.

        Skip a given source in `source_list` if it is `None` or invalid.
        """
        for source in self.source_list:
            # just skip falsy sources
            if not source:
                continue
            try:
                self.source = self.validate_source( source )
            except exceptions.InvalidDataProviderSource:
                continue

            parent_gen = super( MultiSourceDataProvider, self ).__iter__()
            for datum in parent_gen:
                yield datum

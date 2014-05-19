"""
Providers that provide lists of lists generally where each line of a source
is further subdivided into multiple data (e.g. columns from a line).
"""

import line

_TODO = """
move ColumnarDataProvider parsers to more sensible location

TransposedColumnarDataProvider: provides each column as a single array
    - see existing visualizations/dataprovider/basic.ColumnDataProvider
"""

import logging
log = logging.getLogger( __name__ )


# ----------------------------------------------------------------------------- base classes
class ColumnarDataProvider( line.RegexLineDataProvider ):
    """
    Data provider that provide a list of columns from the lines of its source.

    Columns are returned in the order given in indeces, so this provider can
    re-arrange columns.

    If any desired index is outside the actual number of columns
    in the source, this provider will None-pad the output and you are guaranteed
    the same number of columns as the number of indeces asked for (even if they
    are filled with None).
    """
    settings = {
        'indeces'       : 'list:int',
        'column_count'  : 'int',
        'column_types'  : 'list:str',
        'parse_columns' : 'bool',
        'deliminator'   : 'str'
    }

    def __init__( self, source, indeces=None,
            column_count=None, column_types=None, parsers=None, parse_columns=True,
            deliminator='\t', **kwargs ):
        """
        :param indeces: a list of indeces of columns to gather from each row
            Optional: will default to `None`.
            If `None`, this provider will return all rows (even when a
                particular row contains more/less than others).
            If a row/line does not contain an element at a given index, the
                provider will-return/fill-with a `None` value as the element.
        :type indeces: list or None

        :param column_count: an alternate means of defining indeces, use an int
            here to effectively provide the first N columns.
            Optional: will default to `None`.
        :type column_count: int

        :param column_types: a list of string names of types that the
            provider will use to look up an appropriate parser for the column.
            (e.g. 'int', 'float', 'str', 'bool')
            Optional: will default to parsing all columns as strings.
        :type column_types: list of strings

        :param parsers: a dictionary keyed with column type strings
            and with values that are functions to use when parsing those
            types.
            Optional: will default to using the function `_get_default_parsers`.
        :type parsers: dictionary

        :param parse_columns: attempt to parse columns?
            Optional: defaults to `True`.
        :type parse_columns: bool

        :param deliminator: character(s) used to split each row/line of the source.
            Optional: defaults to the tab character.
        :type deliminator: str

        .. note: that the subclass constructors are passed kwargs - so they're
        params (limit, offset, etc.) are also applicable here.
        """
        #TODO: other columnar formats: csv, etc.
        super( ColumnarDataProvider, self ).__init__( source, **kwargs )

        #IMPLICIT: if no indeces, column_count, or column_types passed: return all columns
        self.selected_column_indeces = indeces
        self.column_count = column_count
        self.column_types = column_types or []
        # if no column count given, try to infer from indeces or column_types
        if not self.column_count:
            if   self.selected_column_indeces:
                self.column_count = len( self.selected_column_indeces )
            elif self.column_types:
                self.column_count = len( self.column_types )
        # if no indeces given, infer from column_count
        if not self.selected_column_indeces and self.column_count:
            self.selected_column_indeces = list( xrange( self.column_count ) )

        self.deliminator = deliminator

        # how/whether to parse each column value
        self.parsers = {}
        if parse_columns:
            self.parsers = self.get_default_parsers()
            # overwrite with user desired parsers
            self.parsers.update( parsers or {} )

    def get_default_parsers( self ):
        """
        Return parser dictionary keyed for each columnar type
        (as defined in datatypes).

        .. note: primitives only by default (str, int, float, boolean, None).
            Other (more complex) types are retrieved as strings.
        :returns: a dictionary of the form:
            `{ <parser type name> : <function used to parse type> }`
        """
        #TODO: move to module level (or datatypes, util)
        return {
            # str is default and not needed here
            'int'   : int,
            'float' : float,
            'bool'  : bool,

            # unfortunately, 'list' is used in dataset metadata both for
            #   query style maps (9th col gff) AND comma-sep strings.
            #   (disabled for now)
            #'list'  : lambda v: v.split( ',' ),
            #'csv'   : lambda v: v.split( ',' ),
            ## i don't like how urlparses does sub-lists...
            #'querystr' : lambda v: dict([ ( p.split( '=', 1 ) if '=' in p else ( p, True ) )
            #                              for p in v.split( ';', 1 ) ])

            #'scifloat': #floating point which may be in scientific notation

            # always with the 1 base, biologists?
            #'int1'  : ( lambda i: int( i ) - 1 ),

            #'gffval': string or '.' for None
            #'gffint': # int or '.' for None
            #'gffphase': # 0, 1, 2, or '.' for None
            #'gffstrand': # -, +, ?, or '.' for None, etc.
        }

    def parse_value( self, val, type ):
        """
        Attempt to parse and return the given value based on the given type.

        :param val: the column value to parse (often a string)
        :param type: the string type 'name' used to find the appropriate parser
        :returns: the parsed value
            or `value` if no `type` found in `parsers`
            or `None` if there was a parser error (ValueError)
        """
        if type == 'str' or type == None: return val
        try:
            return self.parsers[ type ]( val )
        except KeyError, err:
            # no parser - return as string
            pass
        except ValueError, err:
            # bad value - return None
            return None
        return val

    def get_column_type( self, index ):
        """
        Get the column type for the parser from `self.column_types` or `None`
        if the type is unavailable.
        :param index: the column index
        :returns: string name of type (e.g. 'float', 'int', etc.)
        """
        try:
            return self.column_types[ index ]
        except IndexError, ind_err:
            return None

    def parse_column_at_index( self, columns, parser_index, index ):
        """
        Get the column type for the parser from `self.column_types` or `None`
        if the type is unavailable.
        """
        try:
            return self.parse_value( columns[ index ], self.get_column_type( parser_index ) )
        # if a selected index is not within columns, return None
        except IndexError, index_err:
            return None

    def parse_columns_from_line( self, line ):
        """
        Returns a list of the desired, parsed columns.
        :param line: the line to parse
        :type line: str
        """
        #TODO: too much going on in this loop - the above should all be precomputed AMAP...
        all_columns = line.split( self.deliminator )
        # if no indeces were passed to init, return all columns
        selected_indeces = self.selected_column_indeces or list( xrange( len( all_columns ) ) )
        parsed_columns = []
        for parser_index, column_index in enumerate( selected_indeces ):
            parsed_columns.append( self.parse_column_at_index( all_columns, parser_index, column_index ) )
        return parsed_columns

    def __iter__( self ):
        parent_gen = super( ColumnarDataProvider, self ).__iter__()
        for line in parent_gen:
            columns = self.parse_columns_from_line( line )
            yield columns

    #TODO: implement column filters here and not below - flatten hierarchy

class FilteredByColumnDataProvider( ColumnarDataProvider ):
    """
    Data provider that provide a list of columns from the lines of its source
    _only_ if they pass a given filter function.

    e.g. column #3 is type int and > N
    """
    # TODO: how to do this and still have limit and offset work?
    def __init__( self, source, **kwargs ):
        raise NotImplementedError()
        super( FilteredByColumnDataProvider, self ).__init__( source, **kwargs )


class DictDataProvider( ColumnarDataProvider ):
    """
    Data provider that zips column_names and columns from the source's contents
    into a dictionary.

    A combination use of both `column_names` and `indeces` allows 'picking'
    key/value pairs from the source.

    .. note: that the subclass constructors are passed kwargs - so they're
    params (limit, offset, etc.) are also applicable here.
    """
    settings = {
        'column_names'  : 'list:str',
    }

    def __init__( self, source, column_names=None, **kwargs ):
        """
        :param column_names: an ordered list of strings that will be used as the keys
            for each column in the returned dictionaries.
            The number of key, value pairs each returned dictionary has will
            be as short as the number of column names provided.
        :type column_names:
        """
        #TODO: allow passing in a map instead of name->index { 'name1': index1, ... }
        super( DictDataProvider, self ).__init__( source, **kwargs )
        self.column_names = column_names or []

    def __iter__( self ):
        parent_gen = super( DictDataProvider, self ).__iter__()
        for column_values in parent_gen:
            map = dict( zip( self.column_names, column_values ) )
            yield map

"""
Providers that provide lists of lists generally where each line of a source
is further subdivided into multiple data (e.g. columns from a line).
"""
import logging
import re
from urllib.parse import unquote_plus

from . import line

_TODO = """
move ColumnarDataProvider parsers to more sensible location

TransposedColumnarDataProvider: provides each column as a single array
    - see existing visualizations/dataprovider/basic.ColumnDataProvider
"""

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------------- base classes
class ColumnarDataProvider(line.RegexLineDataProvider):
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
        "indeces": "list:int",
        "column_count": "int",
        "column_types": "list:str",
        "parse_columns": "bool",
        "deliminator": "str",
        "filters": "list:str",
    }

    def __init__(
        self,
        source,
        indeces=None,
        column_count=None,
        column_types=None,
        parsers=None,
        parse_columns=True,
        deliminator="\t",
        filters=None,
        **kwargs,
    ):
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

        :param parse_columns: attempt to parse columns? Optional: defaults to `True`.
        :type parse_columns: bool

        :param deliminator: character(s) used to split each row/line of the source. Optional: defaults to the tab character.
        :type deliminator: str

        .. note:: that the subclass constructors are passed kwargs - so they're
                  params (limit, offset, etc.) are also applicable here.
        """
        # TODO: other columnar formats: csv, etc.
        super().__init__(source, **kwargs)

        # IMPLICIT: if no indeces, column_count, or column_types passed: return all columns
        self.selected_column_indeces = indeces
        self.column_count = column_count
        self.column_types = column_types or []
        # if no column count given, try to infer from indeces or column_types
        if not self.column_count:
            if self.selected_column_indeces:
                self.column_count = len(self.selected_column_indeces)
            elif self.column_types:
                self.column_count = len(self.column_types)
        # if no indeces given, infer from column_count
        if not self.selected_column_indeces and self.column_count:
            self.selected_column_indeces = list(range(self.column_count))

        self.deliminator = deliminator

        # how/whether to parse each column value
        self.parsers = {}
        if parse_columns:
            self.parsers = self.get_default_parsers()
            # overwrite with user desired parsers
            self.parsers.update(parsers or {})

        filters = filters or []
        self.column_filters = []
        for filter_ in filters:
            parsed = self.parse_filter(filter_)
            # TODO: might be better to error on bad filter/None here
            if callable(parsed):
                self.column_filters.append(parsed)

    def parse_filter(self, filter_param_str):
        split = filter_param_str.split("-", 2)
        if not len(split) >= 3:
            return None
        column, op, val = split

        # better checking v. len and indeces
        column = int(column)
        if column > len(self.column_types):
            return None
        if self.column_types[column] in ("float", "int"):
            return self.create_numeric_filter(column, op, val)
        if self.column_types[column] in ("str"):
            return self.create_string_filter(column, op, val)
        if self.column_types[column] in ("list"):
            return self.create_list_filter(column, op, val)
        return None

    def create_numeric_filter(self, column, op, val):
        """
        Return an anonymous filter function that will be passed the array
        of parsed columns. Return None if no filter function can be
        created for the given params.

        The function will compare the column at index `column` against `val`
        using the given op where op is one of:

        - lt: less than
        - le: less than or equal to
        - eq: equal to
        - ne: not equal to
        - ge: greather than or equal to
        - gt: greater than

        `val` is cast as float here and will return None if there's a parsing error.
        """
        try:
            val = float(val)
        except ValueError:
            return None
        if "lt" == op:
            return lambda d: d[column] < val
        elif "le" == op:
            return lambda d: d[column] <= val
        elif "eq" == op:
            return lambda d: d[column] == val
        elif "ne" == op:
            return lambda d: d[column] != val
        elif "ge" == op:
            return lambda d: d[column] >= val
        elif "gt" == op:
            return lambda d: d[column] > val
        return None

    def create_string_filter(self, column, op, val):
        """
        Return an anonymous filter function that will be passed the array
        of parsed columns. Return None if no filter function can be
        created for the given params.

        The function will compare the column at index `column` against `val`
        using the given op where op is one of:

        - eq: exactly matches
        - has: the column contains the substring `val`
        - re: the column matches the regular expression in `val`
        """
        if "eq" == op:
            return lambda d: d[column] == val
        elif "has" == op:
            return lambda d: val in d[column]
        elif "re" == op:
            val = unquote_plus(val)
            val = re.compile(val)
            return lambda d: val.match(d[column]) is not None
        return None

    def create_list_filter(self, column, op, val):
        """
        Return an anonymous filter function that will be passed the array
        of parsed columns. Return None if no filter function can be
        created for the given params.

        The function will compare the column at index `column` against `val`
        using the given op where op is one of:

        - eq: the list `val` exactly matches the list in the column
        - has: the list in the column contains the sublist `val`
        """
        if "eq" == op:
            val = self.parse_value(val, "list")
            return lambda d: d[column] == val
        elif "has" == op:
            return lambda d: val in d[column]
        return None

    def get_default_parsers(self):
        """
        Return parser dictionary keyed for each columnar type
        (as defined in datatypes).

        .. note:: primitives only by default (str, int, float, boolean, None).
            Other (more complex) types are retrieved as strings.

        :returns: a dictionary of the form:
            `{ <parser type name> : <function used to parse type> }`
        """
        # TODO: move to module level (or datatypes, util)
        return {
            # str is default and not needed here
            "int": int,
            "float": float,
            "bool": bool,
            # unfortunately, 'list' is used in dataset metadata both for
            #   query style maps (9th col gff) AND comma-sep strings.
            #   (disabled for now)
            # 'list'  : lambda v: v.split( ',' ),
            # 'csv'   : lambda v: v.split( ',' ),
            # i don't like how urlparses does sub-lists...
            # 'querystr' : lambda v: dict([ ( p.split( '=', 1 ) if '=' in p else ( p, True ) )
            #                              for p in v.split( ';', 1 ) ])
            # 'scifloat': #floating point which may be in scientific notation
            # always with the 1 base, biologists?
            # 'int1'  : ( lambda i: int( i ) - 1 ),
            # 'gffval': string or '.' for None
            # 'gffint': # int or '.' for None
            # 'gffphase': # 0, 1, 2, or '.' for None
            # 'gffstrand': # -, +, ?, or '.' for None, etc.
        }

    def filter(self, line):
        line = super().filter(line)
        if line is None:
            return line
        columns = self.parse_columns_from_line(line)
        return self.filter_by_columns(columns)

    def parse_columns_from_line(self, line):
        """
        Returns a list of the desired, parsed columns.
        :param line: the line to parse
        :type line: str
        """
        # TODO: too much going on in this loop - the above should all be precomputed AMAP...
        all_columns = line.split(self.deliminator)
        # if no indeces were passed to init, return all columns
        selected_indeces = self.selected_column_indeces or list(range(len(all_columns)))
        parsed_columns = []
        for parser_index, column_index in enumerate(selected_indeces):
            parsed_columns.append(self.parse_column_at_index(all_columns, parser_index, column_index))
        return parsed_columns

    def parse_column_at_index(self, columns, parser_index, index):
        """
        Get the column type for the parser from `self.column_types` or `None`
        if the type is unavailable.
        """
        try:
            return self.parse_value(columns[index], self.get_column_type(parser_index))
        # if a selected index is not within columns, return None
        except IndexError:
            return None

    def parse_value(self, val, type):
        """
        Attempt to parse and return the given value based on the given type.

        :param val: the column value to parse (often a string)
        :param type: the string type 'name' used to find the appropriate parser
        :returns: the parsed value
            or `value` if no `type` found in `parsers`
            or `None` if there was a parser error (ValueError)
        """
        if type == "str" or type is None:
            return val
        try:
            return self.parsers[type](val)
        except KeyError:
            # no parser - return as string
            pass
        except ValueError:
            # bad value - return None
            return None
        return val

    def get_column_type(self, index):
        """
        Get the column type for the parser from `self.column_types` or `None`
        if the type is unavailable.
        :param index: the column index
        :returns: string name of type (e.g. 'float', 'int', etc.)
        """
        try:
            return self.column_types[index]
        except IndexError:
            return None

    def filter_by_columns(self, columns):
        for filter_fn in self.column_filters:
            if not filter_fn(columns):
                return None
        return columns


class DictDataProvider(ColumnarDataProvider):
    """
    Data provider that zips column_names and columns from the source's contents
    into a dictionary.

    A combination use of both `column_names` and `indeces` allows 'picking'
    key/value pairs from the source.

    .. note:: The subclass constructors are passed kwargs - so their
        params (limit, offset, etc.) are also applicable here.
    """

    settings = {
        "column_names": "list:str",
    }

    def __init__(self, source, column_names=None, **kwargs):
        """
        :param column_names: an ordered list of strings that will be used as the keys
            for each column in the returned dictionaries.
            The number of key, value pairs each returned dictionary has will
            be as short as the number of column names provided.
        :type column_names:
        """
        # TODO: allow passing in a map instead of name->index { 'name1': index1, ... }
        super().__init__(source, **kwargs)
        self.column_names = column_names or []

    def __iter__(self):
        parent_gen = super().__iter__()
        for column_values in parent_gen:
            map = dict(zip(self.column_names, column_values))
            yield map

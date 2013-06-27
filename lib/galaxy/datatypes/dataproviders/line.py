"""
Dataproviders that iterate over lines from their sources.
"""

import collections
import os
import re

import base

_TODO = """
line offsets (skip to some place in a file) needs to work more efficiently than simply iterating till we're there
    capture tell() when provider is done
        def stop( self ): self.endpoint = source.tell(); raise StopIteration()
a lot of the hierarchy here could be flattened since we're implementing pipes
"""

import logging
log = logging.getLogger( __name__ )


# ----------------------------------------------------------------------------- text
class FilteredLineDataProvider( base.LimitedOffsetDataProvider ):
    """
    Data provider that yields lines of data from it's source allowing
    optional control over which line to start on and how many lines
    to return.
    """
    DEFAULT_COMMENT_CHAR = '#'
    settings = {
        'string_lines'  : 'bool',
        'provide_blank' : 'bool',
        'comment_char'  : 'str',
    }

    def __init__( self, source, strip_lines=True, provide_blank=False, comment_char=DEFAULT_COMMENT_CHAR, **kwargs ):
        """
        :param strip_lines: remove whitespace from the beginning an ending
            of each line (or not).
            Optional: defaults to True
        :type strip_lines: bool

        :param provide_blank: are empty lines considered valid and provided?
            Optional: defaults to False
        :type provide_blank: bool

        :param comment_char: character(s) that indicate a line isn't data (a comment)
            and should not be provided.
            Optional: defaults to '#'
        :type comment_char: str
        """
        super( FilteredLineDataProvider, self ).__init__( source, **kwargs )
        self.strip_lines = strip_lines
        self.provide_blank = provide_blank
        self.comment_char = comment_char

    def filter( self, line ):
        """
        Determines whether to provide line or not.

        :param line: the incoming line from the source
        :type line: str
        :returns: a line or `None`
        """
        line = super( FilteredLineDataProvider, self ).filter( line )
        if line != None:
            # is this the proper order?
            if self.strip_lines:
                line = line.strip()
            if not self.provide_blank and line == '':
                return None
            elif line.startswith( self.comment_char ):
                return None

        return line


class RegexLineDataProvider( FilteredLineDataProvider ):
    """
    Data provider that yields only those lines of data from it's source
    that do (or do not when `invert` is True) match one or more of the given list
    of regexs.

    .. note:: the regex matches are effectively OR'd (if **any** regex matches
    the line it is considered valid and will be provided).
    """
    settings = {
        'regex_list'    : 'list:str',
        'invert'        : 'bool',
    }

    def __init__( self, source, regex_list=None, invert=False, **kwargs ):
        """
        :param regex_list: list of strings or regular expression strings that will
            be `match`ed to each line
            Optional: defaults to `None` (no matching)
        :type regex_list: list (of str)

        :param invert: if `True` will provide only lines that **do not match**.
            Optional: defaults to False
        :type invert: bool
        """
        super( RegexLineDataProvider, self ).__init__( source, **kwargs )

        self.regex_list = regex_list if isinstance( regex_list, list ) else []
        self.compiled_regex_list = [ re.compile( regex ) for regex in self.regex_list ]
        self.invert = invert
        #NOTE: no support for flags

    def filter( self, line ):
        line = super( RegexLineDataProvider, self ).filter( line )
        if line != None and self.compiled_regex_list:
            line = self.filter_by_regex( line )
        return line

    def filter_by_regex( self, line ):
        matches = any([ regex.match( line ) for regex in self.compiled_regex_list ])
        if self.invert:
            return line if not matches else None
        return line if matches else None


# ============================================================================= MICELLAINEOUS OR UNIMPLEMENTED
# ----------------------------------------------------------------------------- block data providers
class BlockDataProvider( base.LimitedOffsetDataProvider ):
    """
    Class that uses formats where multiple lines combine to describe a single
    datum. The data output will be a list of either map/dicts or sub-arrays.

    Uses FilteredLineDataProvider as it's source (kwargs **not** passed).

    e.g. Fasta, GenBank, MAF, hg log
    Note: mem intensive (gathers list of lines before output)
    """
    def __init__( self, source, new_block_delim_fn, block_filter_fn=None, **kwargs ):
        """
        :param new_block_delim_fn: T/F function to determine whether a given line
            is the start of a new block.
        :type new_block_delim_fn: function

        :param block_filter_fn: function that determines if a block is valid and
            will be provided.
            Optional: defaults to `None` (no filtering)
        :type block_filter_fn: function
        """
        # composition - not inheritance
        #TODO: don't pass any?
        line_provider = FilteredLineDataProvider( source )
        super( BlockDataProvider, self ).__init__( line_provider, **kwargs )

        self.new_block_delim_fn = new_block_delim_fn
        self.block_filter_fn = block_filter_fn
        self.init_new_block()
        # ...well, this is kinda lame - but prevents returning first empty block
        #TODO: maybe better way in iter
        self.is_inside_block = False

    def init_new_block( self ):
        """
        Set up internal data for next block.
        """
        # called in __init__ and after yielding the prev. block
        self.block_lines = collections.deque([])
        self.block = {}

    def __iter__( self ):
        """
        Overridden to provide last block.
        """
        parent_gen = super( BlockDataProvider, self ).__iter__()
        for block in parent_gen:
            yield block

        last_block = self.filter_block( self.assemble_current_block() )
        if last_block != None and self.num_data_returned < self.limit:
            self.num_data_returned += 1
            yield last_block

    def filter( self, line ):
        """
        Line filter here being used to aggregate/assemble lines into a block
        and determine whether the line indicates a new block.

        :param line: the incoming line from the source
        :type line: str
        :returns: a block or `None`
        """
        line = super( BlockDataProvider, self ).filter( line )
        if line == None:
            return None

        if self.is_new_block( line ):
            # if we're already in a block, return the prev. block and add the line to a new block
            #TODO: maybe better way in iter
            if self.is_inside_block:
                filtered_block = self.filter_block( self.assemble_current_block() )
                self.init_new_block()
                self.add_line_to_block( line )

                # return an assembled block datum if it passed the filter
                if filtered_block != None:
                    return filtered_block

            else:
                self.is_inside_block = True

        self.add_line_to_block( line )
        return None

    def is_new_block( self, line ):
        """
        Returns True if the given line indicates the start of a new block
        (and the current block should be provided) or False if not.
        """
        if self.new_block_delim_fn:
            return self.new_block_delim_fn( line )
        return False

    # NOTE:
    #   some formats have one block attr per line
    #   some formats rely on having access to multiple lines to make sensible data
    # So, building the block from the lines can happen in either:
    #   add_line_to_block AND/OR assemble_current_block
    def add_line_to_block( self, line ):
        """
        Integrate the given line into the current block.

        Called per line.
        """
        # here either:
        #   consume the line (using it to add attrs to self.block)
        #   save the line (appending to self.block_lines) for use in assemble_current_block
        self.block_lines.append( line )

    def assemble_current_block( self ):
        """
        Build the current data into a block.

        Called per block (just before providing).
        """
        # empty block_lines and assemble block
        # NOTE: we don't want to have mem == 2*data here so - careful
        return list( ( self.block_lines.popleft() for i in xrange( len( self.block_lines ) ) ) )

    def filter_block( self, block ):
        """
        Is the current block a valid/desired datum.

        Called per block (just before providing).
        """
        if self.block_filter_fn:
            return self.block_filter_fn( block )
        return block


# ----------------------------------------------------------------------------- hierarchal/tree data providers
class HierarchalDataProvider( BlockDataProvider ):
    """
    Class that uses formats where a datum may have a parent or children
    data.

    e.g. XML, HTML, GFF3, Phylogenetic
    """
    def __init__( self, source, **kwargs ):
        #TODO: (and defer to better (than I can write) parsers for each subtype)
        raise NotImplementedError( 'Abstract class' )
        super( HierarchalDataProvider, self ).__init__( source, **kwargs )

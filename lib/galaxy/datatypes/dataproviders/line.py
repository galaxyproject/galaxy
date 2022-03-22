"""
Dataproviders that iterate over lines from their sources.
"""
import collections
import logging
import re

from . import base

log = logging.getLogger(__name__)

_TODO = """
line offsets (skip to some place in a file) needs to work more efficiently than simply iterating till we're there
    capture tell() when provider is done
        def stop( self ): self.endpoint = source.tell(); raise StopIteration()
a lot of the hierarchy here could be flattened since we're implementing pipes
"""


class FilteredLineDataProvider(base.LimitedOffsetDataProvider):
    """
    Data provider that yields lines of data from its source allowing
    optional control over which line to start on and how many lines
    to return.
    """

    DEFAULT_COMMENT_CHAR = "#"
    settings = {
        "strip_lines": "bool",
        "strip_newlines": "bool",
        "provide_blank": "bool",
        "comment_char": "str",
    }

    def __init__(
        self,
        source,
        strip_lines=True,
        strip_newlines=False,
        provide_blank=False,
        comment_char=DEFAULT_COMMENT_CHAR,
        **kwargs,
    ):
        """
        :param strip_lines: remove whitespace from the beginning an ending
            of each line (or not).
            Optional: defaults to True
        :type strip_lines: bool

        :param strip_newlines: remove newlines only
            (only functions when ``strip_lines`` is false)
            Optional: defaults to False
        :type strip_lines: bool

        :param provide_blank: are empty lines considered valid and provided?
            Optional: defaults to False
        :type provide_blank: bool

        :param comment_char: character(s) that indicate a line isn't data (a comment)
            and should not be provided.
            Optional: defaults to '#'
        :type comment_char: str
        """
        super().__init__(source, **kwargs)
        self.strip_lines = strip_lines
        self.strip_newlines = strip_newlines
        self.provide_blank = provide_blank
        self.comment_char = comment_char

    def filter(self, line):
        """
        Determines whether to provide line or not.

        :param line: the incoming line from the source
        :type line: str
        :returns: a line or `None`
        """
        if line is not None:
            # ??: shouldn't it strip newlines regardless, if not why not use on of the base.dprovs
            if self.strip_lines:
                line = line.strip()
            elif self.strip_newlines:
                line = line.strip("\n")
            if not self.provide_blank and line == "":
                return None
            elif self.comment_char and line.startswith(self.comment_char):
                return None

        return super().filter(line)


class RegexLineDataProvider(FilteredLineDataProvider):
    """
    Data provider that yields only those lines of data from its source
    that do (or do not when `invert` is True) match one or more of the given list
    of regexs.

    .. note:: the regex matches are effectively OR'd (if **any** regex matches
        the line it is considered valid and will be provided).
    """

    settings = {
        "regex_list": "list:escaped",
        "invert": "bool",
    }

    def __init__(self, source, regex_list=None, invert=False, **kwargs):
        """
        :param regex_list: list of strings or regular expression strings that will
            be `match`ed to each line
            Optional: defaults to `None` (no matching)
        :type regex_list: list (of str)

        :param invert: if `True` will provide only lines that **do not match**.
            Optional: defaults to False
        :type invert: bool
        """
        super().__init__(source, **kwargs)

        self.regex_list = regex_list if isinstance(regex_list, list) else []
        self.compiled_regex_list = [re.compile(regex) for regex in self.regex_list]
        self.invert = invert
        # NOTE: no support for flags

    def filter(self, line):
        # NOTE: filter_fn will occur BEFORE any matching
        line = super().filter(line)
        if line is not None and self.compiled_regex_list:
            line = self.filter_by_regex(line)
        return line

    def filter_by_regex(self, line):
        matches = any(regex.match(line) for regex in self.compiled_regex_list)
        if self.invert:
            return line if not matches else None
        return line if matches else None


# ============================================================================= MICELLAINEOUS OR UNIMPLEMENTED
# ----------------------------------------------------------------------------- block data providers
class BlockDataProvider(base.LimitedOffsetDataProvider):
    """
    Class that uses formats where multiple lines combine to describe a single
    datum. The data output will be a list of either map/dicts or sub-arrays.

    Uses FilteredLineDataProvider as its source (kwargs **not** passed).

    e.g. Fasta, GenBank, MAF, hg log
    Note: mem intensive (gathers list of lines before output)
    """

    def __init__(self, source, new_block_delim_fn=None, block_filter_fn=None, **kwargs):
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
        # TODO: not a fan of this:
        (filter_fn, limit, offset) = (kwargs.pop("filter_fn", None), kwargs.pop("limit", None), kwargs.pop("offset", 0))
        line_provider = FilteredLineDataProvider(source, **kwargs)
        super().__init__(line_provider, filter_fn=filter_fn, limit=limit, offset=offset)

        self.new_block_delim_fn = new_block_delim_fn
        self.block_filter_fn = block_filter_fn
        self.init_new_block()

    def init_new_block(self):
        """
        Set up internal data for next block.
        """
        # called in __init__ and after yielding the prev. block
        self.block_lines = collections.deque([])

    def __iter__(self):
        """
        Overridden to provide last block.
        """
        parent_gen = super().__iter__()
        yield from parent_gen

        last_block = self.handle_last_block()
        if last_block is not None:
            self.num_data_returned += 1
            yield last_block

    def filter(self, line):
        """
        Line filter here being used to aggregate/assemble lines into a block
        and determine whether the line indicates a new block.

        :param line: the incoming line from the source
        :type line: str
        :returns: a block or `None`
        """
        line = super().filter(line)
        # TODO: HACK
        self.num_data_read -= 1
        if line is None:
            return None

        block_to_return = None
        if self.is_new_block(line):
            # if we're already in a block, return the prev. block and add the line to a new block
            if self.block_lines:
                block_to_return = self.assemble_current_block()
                block_to_return = self.filter_block(block_to_return)
                self.num_data_read += 1

                self.init_new_block()

        self.add_line_to_block(line)
        return block_to_return

    def is_new_block(self, line):
        """
        Returns True if the given line indicates the start of a new block
        (and the current block should be provided) or False if not.
        """
        if self.new_block_delim_fn:
            return self.new_block_delim_fn(line)
        return True

    # NOTE:
    #   some formats have one block attr per line
    #   some formats rely on having access to multiple lines to make sensible data
    # So, building the block from the lines can happen in either:
    #   add_line_to_block AND/OR assemble_current_block
    def add_line_to_block(self, line):
        """
        Integrate the given line into the current block.

        Called per line.
        """
        # here either:
        #   consume the line (using it to add attrs to self.block)
        #   save the line (appending to self.block_lines) for use in assemble_current_block
        self.block_lines.append(line)

    def assemble_current_block(self):
        """
        Build the current data into a block.

        Called per block (just before providing).
        """
        # empty block_lines and assemble block
        return list(self.block_lines.popleft() for i in range(len(self.block_lines)))

    def filter_block(self, block):
        """
        Is the current block a valid/desired datum.

        Called per block (just before providing).
        """
        if self.block_filter_fn:
            return self.block_filter_fn(block)
        return block

    def handle_last_block(self):
        """
        Handle any blocks remaining after the main loop.
        """
        if self.limit is not None and self.num_data_returned >= self.limit:
            return None

        last_block = self.assemble_current_block()
        self.num_data_read += 1

        last_block = self.filter_block(last_block)
        if last_block is not None:
            self.num_valid_data_read += 1

        return last_block

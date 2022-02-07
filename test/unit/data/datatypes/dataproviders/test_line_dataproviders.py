"""
Unit tests for base DataProviders.
.. seealso:: galaxy.datatypes.dataproviders.base
"""
import logging
import unittest
from typing import Type

from galaxy.datatypes.dataproviders import (
    base,
    line,
)
from . import test_base_dataproviders

log = logging.getLogger(__name__)


# TODO: TestCase hierarchy is a bit of mess here.
class Test_FilteredLineDataProvider(test_base_dataproviders.Test_FilteredDataProvider):
    provider_class: Type[base.DataProvider] = line.FilteredLineDataProvider
    default_file_contents = """
            # this should be stripped out
            One
            # as should blank lines

            # preceding/trailing whitespace too
                Two
            Three
        """

    def parses_default_content_as(self):
        return ["One", "Two", "Three"]

    def test_counters(self):
        """should count: lines read, lines that passed the filter, lines returned"""
        (contents, provider, data) = self.contents_provider_and_data()
        self.assertCounters(provider, 7, 3, 3)

    def test_filter_fn(self):
        """should filter out lines using filter_fn and set counters properly
        based on filter
        """

        def filter_ts(string):
            if string.lower().startswith("t"):
                return None
            return string

        (contents, provider, data) = self.contents_provider_and_data(filter_fn=filter_ts)
        self.assertCounters(provider, 7, 1, 1)

    def test_limit_with_offset(self):
        def limit_offset_combo(limit, offset, data_should_be, read, valid, returned):
            (contents, provider, data) = self.contents_provider_and_data(limit=limit, offset=offset)
            self.assertEqual(data, data_should_be)
            # self.assertCounters( provider, read, valid, returned )

        result_data = self.parses_default_content_as()
        test_data = [
            (0, 0, [], 0, 0, 0),
            (1, 0, result_data[:1], 1, 1, 1),
            (2, 0, result_data[:2], 2, 2, 2),
            (3, 0, result_data[:3], 3, 3, 3),
            (1, 1, result_data[1:2], 1, 1, 1),
            (2, 1, result_data[1:3], 2, 2, 2),
            (3, 1, result_data[1:3], 2, 2, 2),
            (1, 2, result_data[2:3], 1, 1, 1),
            (2, 2, result_data[2:3], 1, 1, 1),
            (3, 2, result_data[2:3], 1, 1, 1),
        ]
        for test in test_data:
            log.debug("limit_offset_combo: %s", ", ".join(str(e) for e in test))
            limit_offset_combo(*test)

    def test_provide_blank(self):
        """should return blank lines if ``provide_blank`` is true."""
        (contents, provider, data) = self.contents_provider_and_data(provide_blank=True)
        self.assertEqual(data, ["One", "", "Two", "Three"])
        self.assertCounters(provider, 7, 4, 4)

    def test_strip_lines(self):
        """should return unstripped lines if ``strip_lines`` is false."""
        (contents, provider, data) = self.contents_provider_and_data(strip_lines=False)
        self.assertEqual(data, ["One\n", "\n", "    Two\n", "Three\n"])
        self.assertCounters(provider, 7, 4, 4)

    def test_comment_char(self):
        """should return unstripped lines if ``strip_lines`` is false."""
        (contents, provider, data) = self.contents_provider_and_data(comment_char="T")
        self.assertEqual(
            data,
            ["# this should be stripped out", "One", "# as should blank lines", "# preceding/trailing whitespace too"],
        )
        self.assertCounters(provider, 7, 4, 4)


class Test_RegexLineDataProvider(Test_FilteredLineDataProvider):
    provider_class = line.RegexLineDataProvider
    default_file_contents = """
            # this should be stripped out
            One
            # as should blank lines

            # preceding/trailing whitespace too
                Two
            Three
        """

    def test_regex(self):
        """should return lines matching regex (AFTER strip, comments, blanks)."""
        (contents, provider, data) = self.contents_provider_and_data(regex_list=[r"^O"])
        self.assertEqual(data, ["One"])
        self.assertCounters(provider, 7, 1, 1)

    def test_regex_list(self):
        """should return regex matches using more than one regex by ORing them."""
        (contents, provider, data) = self.contents_provider_and_data(regex_list=[r"^O", r"T"])
        self.assertEqual(data, ["One", "Two", "Three"])
        self.assertCounters(provider, 7, 3, 3)

    def test_inverse(self):
        """should return inverse matches when ``invert`` is true."""
        (contents, provider, data) = self.contents_provider_and_data(regex_list=[r"^O"], invert=True)
        self.assertEqual(data, ["Two", "Three"])
        self.assertCounters(provider, 7, 2, 2)

    def test_regex_no_match(self):
        """should return empty if no regex matches."""
        (contents, provider, data) = self.contents_provider_and_data(regex_list=[r"^Z"])
        self.assertEqual(data, [])
        self.assertCounters(provider, 7, 0, 0)

    def test_regex_w_limit_offset(self):
        """regex should play well with limit and offset"""
        (contents, provider, data) = self.contents_provider_and_data(regex_list=[r"^T"], limit=1)
        self.assertEqual(data, ["Two"])
        # TODO: once again, valid data, returned data is off
        self.assertCounters(provider, 6, 1, 1)

        (contents, provider, data) = self.contents_provider_and_data(regex_list=[r"^T"], limit=1, offset=1)
        self.assertEqual(data, ["Three"])
        self.assertCounters(provider, 7, 2, 1)


class Test_BlockDataProvider(test_base_dataproviders.Test_FilteredDataProvider):
    provider_class = line.BlockDataProvider
    default_file_contents = """
        One
            ABCD
        Two
            ABCD
            EFGH
        Three
    """

    def parses_default_content_as(self):
        return [["One"], ["ABCD"], ["Two"], ["ABCD"], ["EFGH"], ["Three"]]

    # TODO: well, this is ham-handed...
    def test_stringio(self):
        pass

    def test_iterators(self):
        pass

    def test_readlines(self):
        pass

    def test_file(self):
        """should work with files"""
        (contents, provider, data) = self.contents_provider_and_data()
        self.assertEqual(data, self.parses_default_content_as())
        self.assertTrue(isinstance(provider.source, line.FilteredLineDataProvider))
        self.assertTrue(hasattr(provider.source.source, "read"))
        # provider should call close on file
        self.assertTrue(provider.source.source.closed)

    def test_counters(self):
        """should count: lines read, lines that passed the filter, lines returned"""
        (contents, provider, data) = self.contents_provider_and_data()
        self.assertCounters(provider, 6, 6, 6)

    def test_filter_fn(self):
        """should filter out lines using filter_fn and set counters properly
        based on filter
        """

        def filter_ts(string):
            if string.lower().startswith("t"):
                return None
            return string

        (contents, provider, data) = self.contents_provider_and_data(filter_fn=filter_ts)
        # no block fns here, so will parse as lines
        self.assertEqual(data, [["One"], ["ABCD"], ["ABCD"], ["EFGH"]])
        self.assertCounters(provider, 4, 4, 4)

    def test_new_block_delim_fn(self):
        """should return blocks based on ``new_block_delim_fn``"""

        def is_not_indented(line):
            strip_diff = len(line) - len(line.lstrip())
            return strip_diff == 0

        # in order to use indentation as a delimiter, we need to strip the newlines only
        (contents, provider, data) = self.contents_provider_and_data(
            strip_lines=False, strip_newlines=True, new_block_delim_fn=is_not_indented
        )
        self.assertEqual(data, [["One", "    ABCD"], ["Two", "    ABCD", "    EFGH"], ["Three"]])
        self.assertCounters(provider, 3, 3, 3)

    def test_block_filter_fn(self):
        """should return blocks only blocks that pass ``block_filter_fn``"""

        def is_not_indented(line):
            strip_diff = len(line) - len(line.lstrip())
            return strip_diff == 0

        # def empty_block( block ):
        #    if len( block ) <= 1:
        #        return None
        #    return block

        def no_tw(block):
            if block[0].startswith("Tw"):
                return None
            return block

        (contents, provider, data) = self.contents_provider_and_data(
            strip_lines=False, strip_newlines=True, new_block_delim_fn=is_not_indented, block_filter_fn=no_tw
        )
        self.assertEqual(data, [["One", "    ABCD"], ["Three"]])
        self.assertCounters(provider, 3, 2, 2)

    def test_hack_block_filter_fn(self):
        """should allow other aggregating/mod use in filter_fn

        Although, it would be better to subclass and override assemble_current_block
        """

        def is_not_indented(line):
            strip_diff = len(line) - len(line.lstrip())
            return strip_diff == 0

        def empty_block(block):
            if len(block) <= 1:
                return None
            return {"header": block[0].strip(), "data": [b.strip() for b in block[1:] if b.strip()]}

        (contents, provider, data) = self.contents_provider_and_data(
            strip_lines=False, strip_newlines=True, new_block_delim_fn=is_not_indented, block_filter_fn=empty_block
        )
        self.assertEqual(data, [{"header": "One", "data": ["ABCD"]}, {"header": "Two", "data": ["ABCD", "EFGH"]}])
        self.assertCounters(provider, 3, 2, 2)

    def test_block_filter_fn_w_limit_offset(self):
        """should allow both block fns and limit, offset"""

        def is_not_indented(line):
            strip_diff = len(line) - len(line.lstrip())
            return strip_diff == 0

        def empty_block(block):
            if len(block) <= 1:
                return None
            return block

        (contents, provider, data) = self.contents_provider_and_data(
            strip_lines=False,
            strip_newlines=True,
            new_block_delim_fn=is_not_indented,
            block_filter_fn=empty_block,
            limit=1,
        )
        self.assertEqual(data, [["One", "    ABCD"]])
        self.assertCounters(provider, 1, 1, 1)
        (contents, provider, data) = self.contents_provider_and_data(
            strip_lines=False,
            strip_newlines=True,
            new_block_delim_fn=is_not_indented,
            block_filter_fn=empty_block,
            limit=2,
            offset=1,
        )
        self.assertEqual(data, [["Two", "    ABCD", "    EFGH"]])
        self.assertCounters(provider, 3, 2, 1)

    def test_simple_example(self):
        """ """
        file_contents = """
            >One
            ABCD

            # this comment (and the blank line above) won't be included
            >Two
            ABCD
            EFGH
            """

        def fasta_header(line):
            return line.startswith(">")

        def id_seq(block):
            return {"id": block[0][1:], "seq": ("".join(block[1:]))}

        (contents, provider, data) = self.contents_provider_and_data(
            contents=file_contents, new_block_delim_fn=fasta_header, block_filter_fn=id_seq
        )
        self.assertEqual(data, [{"id": "One", "seq": "ABCD"}, {"id": "Two", "seq": "ABCDEFGH"}])
        self.assertCounters(provider, 2, 2, 2)


if __name__ == "__main__":
    unittest.main()

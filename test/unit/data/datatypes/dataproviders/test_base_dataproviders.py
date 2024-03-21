"""
Unit tests for base DataProviders.
.. seealso:: galaxy.datatypes.dataproviders.base
"""

import os
import tempfile
from io import StringIO
from typing import Type

from galaxy.datatypes.dataproviders import (
    base,
    exceptions,
)
from galaxy.util import clean_multiline_string
from galaxy.util.unittest import TestCase

# TODO: fix imports there after dist and retry
# TODO: fix off by ones in FilteredDataProvider counters
# currently because of dataproviders.dataset importing galaxy.model this doesn't work


class TempFileCache:
    """
    Creates and caches tempfiles with/based-on the given contents.
    """

    def __init__(self):
        self._content_dict = {}

    def create_tmpfile(self, contents):
        if contents not in self._content_dict:
            # create a named tmp and write contents to it, return filename
            with tempfile.NamedTemporaryFile(delete=False, mode="w+") as tmpfile:
                tmpfile.write(contents)
                tmpfile_name = tmpfile.name
            self._content_dict[contents] = tmpfile_name
        return self._content_dict[contents]

    def clear(self):
        for tmpfile in self._content_dict.values():
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)
        self._content_dict = {}


class BaseTestCase(TestCase):
    default_file_contents = """
            One
            Two
            Three
        """
    tmpfiles: TempFileCache

    @classmethod
    def setUpClass(cls):
        cls.tmpfiles = TempFileCache()

    @classmethod
    def tearDownClass(cls):
        cls.tmpfiles.clear()

    def format_tmpfile_contents(self, contents=None):
        contents = contents or self.default_file_contents
        contents = clean_multiline_string(contents)
        return contents

    def parses_default_content_as(self):
        return ["One\n", "Two\n", "Three\n"]


class Test_BaseDataProvider(BaseTestCase):
    provider_class: Type[base.DataProvider] = base.DataProvider

    def contents_provider_and_data(self, filename=None, contents=None, source=None, *provider_args, **provider_kwargs):
        # to remove boiler plate
        # returns file content string, provider used, and data list
        if not filename:
            contents = self.format_tmpfile_contents(contents)
            filename = self.tmpfiles.create_tmpfile(contents)
        # TODO: if filename, contents == None
        if not source:
            source = open(filename)
        provider = self.provider_class(source, *provider_args, **provider_kwargs)
        data = list(provider)
        return (contents, provider, data)

    def test_iterators(self):
        source = (str(x) for x in range(1, 10))
        provider = self.provider_class(source)
        data = list(provider)
        assert data == [str(x) for x in range(1, 10)]

        source = (str(x) for x in range(1, 10))
        provider = self.provider_class(source)
        data = list(provider)
        assert data == [str(x) for x in range(1, 10)]

        source = (str(x) for x in range(1, 10))
        provider = self.provider_class(source)
        data = list(provider)
        assert data == [str(x) for x in range(1, 10)]

    def test_validate_source(self):
        """validate_source should throw an error if the source doesn't have attr '__iter__'"""

        def non_iterator_dprov(source):
            return self.provider_class(source)

        # two objects without __iter__ method: build in function and int
        with self.assertRaises(exceptions.InvalidDataProviderSource):
            non_iterator_dprov(sum)
        with self.assertRaises(exceptions.InvalidDataProviderSource):
            non_iterator_dprov(40)

    def test_writemethods(self):
        """should throw an error if any write methods are called"""
        source = (str(x) for x in range(1, 10))
        provider = self.provider_class(source)

        # should throw error
        def call_method(provider, method_name, *args):
            method = getattr(provider, method_name)
            return method(*args)

        with self.assertRaises(NotImplementedError):
            call_method(provider, "truncate", 20)
        with self.assertRaises(NotImplementedError):
            call_method(provider, "write", "bler")
        with self.assertRaises(NotImplementedError):
            call_method(provider, "writelines", ["one", "two"])

    def test_readlines(self):
        """readlines should return all the data in list form"""
        source = (str(x) for x in range(1, 10))
        provider = self.provider_class(source)
        data = provider.readlines()
        assert data == [str(x) for x in range(1, 10)]

    def test_stringio(self):
        """should work with StringIO"""
        contents = clean_multiline_string(
            """
            One
            Two
            Three
        """
        )
        source = StringIO(contents)
        provider = self.provider_class(source)
        data = list(provider)
        # provider should call close on file
        assert data == self.parses_default_content_as()
        assert source.closed

    def test_file(self):
        """should work with files"""
        (contents, provider, data) = self.contents_provider_and_data()
        assert data == self.parses_default_content_as()
        # provider should call close on file
        assert hasattr(provider.source, "read")
        assert provider.source.closed


class Test_FilteredDataProvider(Test_BaseDataProvider):
    provider_class: Type[base.DataProvider] = base.FilteredDataProvider

    def assertCounters(self, provider, read, valid, returned):
        assert provider.num_data_read == read
        assert provider.num_valid_data_read == valid
        assert provider.num_data_returned == returned

    def test_counters(self):
        """should count: lines read, lines that passed the filter, lines returned"""
        (contents, provider, data) = self.contents_provider_and_data()
        self.assertCounters(provider, 3, 3, 3)

    def test_filter_fn(self):
        """should filter out lines using filter_fn and set counters properly
        based on filter
        """

        def filter_ts(string):
            if string.lower().startswith("t"):
                return None
            return string

        (contents, provider, data) = self.contents_provider_and_data(filter_fn=filter_ts)
        self.assertCounters(provider, 3, 1, 1)


class Test_LimitedOffsetDataProvider(Test_FilteredDataProvider):
    provider_class: Type[base.DataProvider] = base.LimitedOffsetDataProvider

    def test_offset_1(self):
        """when offset is 1, should skip first"""
        (contents, provider, data) = self.contents_provider_and_data(offset=1)
        assert data == self.parses_default_content_as()[1:]
        self.assertCounters(provider, 3, 3, 2)

    def test_offset_all(self):
        """when offset >= num lines, should return empty list"""
        (contents, provider, data) = self.contents_provider_and_data(offset=4)
        assert data == []
        self.assertCounters(provider, 3, 3, 0)

    def test_offset_none(self):
        """when offset is 0, should return all"""
        (contents, provider, data) = self.contents_provider_and_data(offset=0)
        assert data == self.parses_default_content_as()
        self.assertCounters(provider, 3, 3, 3)

    def test_offset_negative(self):
        """when offset is negative, should return all"""
        (contents, provider, data) = self.contents_provider_and_data(offset=-1)
        assert data == self.parses_default_content_as()
        self.assertCounters(provider, 3, 3, 3)

    def test_limit_1(self):
        """when limit is one, should return first"""
        (contents, provider, data) = self.contents_provider_and_data(limit=1)
        assert data == self.parses_default_content_as()[:1]
        self.assertCounters(provider, 1, 1, 1)

    def test_limit_all(self):
        """when limit >= num lines, should return all"""
        (contents, provider, data) = self.contents_provider_and_data(limit=4)
        assert data == self.parses_default_content_as()
        self.assertCounters(provider, 3, 3, 3)

    def test_limit_zero(self):
        """when limit >= num lines, should return empty list"""
        (contents, provider, data) = self.contents_provider_and_data(limit=0)
        assert data == []
        self.assertCounters(provider, 0, 0, 0)

    def test_limit_none(self):
        """when limit is None, should return all"""
        (contents, provider, data) = self.contents_provider_and_data(limit=None)
        assert data == self.parses_default_content_as()
        self.assertCounters(provider, 3, 3, 3)

    # TODO: somehow re-use tmpfile here
    def test_limit_with_offset(self):
        def limit_offset_combo(limit, offset, data_should_be, read, valid, returned):
            (contents, provider, data) = self.contents_provider_and_data(limit=limit, offset=offset)
            assert data == data_should_be
            # self.assertCounters(provider, read, valid, returned)

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
            limit_offset_combo(*test)

    def test_limit_with_offset_and_filter(self):
        def limit_offset_combo(limit, offset, data_should_be, read, valid, returned):
            def only_ts(string):
                if not string.lower().startswith("t"):
                    return None
                return string

            (contents, provider, data) = self.contents_provider_and_data(limit=limit, offset=offset, filter_fn=only_ts)
            assert data == data_should_be
            # self.assertCounters(provider, read, valid, returned)

        result_data = [c for c in self.parses_default_content_as() if c.lower().startswith("t")]
        test_data = [
            (0, 0, [], 0, 0, 0),
            (1, 0, result_data[:1], 1, 1, 1),
            (2, 0, result_data[:2], 2, 2, 2),
            (3, 0, result_data[:3], 2, 2, 2),
            (1, 1, result_data[1:2], 1, 1, 1),
            (2, 1, result_data[1:3], 1, 1, 1),
            (1, 2, result_data[2:3], 0, 0, 0),
        ]
        for test in test_data:
            limit_offset_combo(*test)


class Test_MultiSourceDataProvider(BaseTestCase):
    provider_class: Type[base.DataProvider] = base.MultiSourceDataProvider

    def contents_and_tmpfile(self, contents=None):
        # TODO: hmmmm...
        contents = contents or self.default_file_contents
        contents = clean_multiline_string(contents)
        return (contents, self.tmpfiles.create_tmpfile(contents))

    def test_multiple_sources(self):
        # clean the following contents, write them to tmpfiles, open them,
        #   and pass as a list to the provider
        contents = [
            """
                One
                Two
                Three
                Four
                Five
            """,
            """
                Six
                Seven
                Eight
                Nine
                Ten
            """,
            """
                Eleven
                Twelve! (<-- http://youtu.be/JZshZp-cxKg)
            """,
        ]
        contents = [clean_multiline_string(c) for c in contents]
        source_list = [open(self.tmpfiles.create_tmpfile(c)) for c in contents]

        provider = self.provider_class(source_list)
        data = list(provider)
        assert "".join(data) == "".join(contents)

    def test_multiple_compound_sources(self):
        # clean the following contents, write them to tmpfiles, open them,
        #   and pass as a list to the provider
        contents = [
            """
                One
                Two
                Three
                Four
                Five
            """,
            """
                Six
                Seven
                Eight
                Nine
                Ten
            """,
            """
                Eleven
                Twelve! (<-- http://youtu.be/JZshZp-cxKg)
            """,
        ]
        contents = [clean_multiline_string(c) for c in contents]
        source_list_f = [open(self.tmpfiles.create_tmpfile(c)) for c in contents]

        def no_Fs(string):
            return None if string.startswith("F") else string

        def no_youtube(string):
            return None if ("youtu.be" in string) else string

        source_list = [
            base.LimitedOffsetDataProvider(source_list_f[0], filter_fn=no_Fs, limit=2, offset=1),
            base.LimitedOffsetDataProvider(source_list_f[1], limit=1, offset=3),
            base.FilteredDataProvider(source_list_f[2], filter_fn=no_youtube),
        ]
        provider = self.provider_class(source_list)
        data = list(provider)
        assert "".join(data) == "Two\nThree\nNine\nEleven\n"

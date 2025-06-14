"""Tool test parsing to dicts logic."""

import os
from typing import (
    Any,
    List,
)

from pytest import skip

from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.tool_util.verify.parse import parse_tool_test_descriptions
from galaxy.util import (
    galaxy_directory,
    in_packages,
)
from galaxy.util.unittest import TestCase
from .util import dict_verify_each

# Not the whole response, just some keys and such to test...
SIMPLE_CONSTRUCTS_EXPECTATIONS_0 = [
    (["inputs", "booltest"], [True]),
    (["inputs", "inttest"], ["12456"]),
    (["inputs", "floattest"], ["6.789"]),
    (["inputs", "p1|p1use"], [True]),
    (["inputs", "files_0|file"], ["simple_line.txt"]),
    (["outputs", 0, "name"], "out_file1"),
    (["required_files", 0, 0], "simple_line.txt"),
    (["required_files", 0, 1, "value"], "simple_line.txt"),
]
# this test case covers specifying boolean parameters by string truevalue/falsevalue
SIMPLE_CONSTRUCTS_EXPECTATIONS_1 = [
    (["inputs", "booltest"], [True]),
    (["inputs", "p1|p1use"], [True]),
    (["inputs", "files_0|file"], ["simple_line.txt"]),
    (["outputs", 0, "name"], "out_file1"),
]
SECTION_EXPECTATIONS = [
    (["inputs", "int|inttest"], ["12456"]),
    (["inputs", "float|floattest"], ["6.789"]),
]
MIN_REPEAT_EXPECTATIONS = [
    (["inputs", "queries_0|input"], ["simple_line.txt"]),
    (["inputs", "queries_1|input"], ["simple_line.txt"]),
    (["inputs", "queries2_0|input2"], ["simple_line_alternative.txt"]),
]
DBKEY_FILTER_INPUT_EXPECTATIONS = [
    (["inputs", "inputs"], ["simple_line.txt"]),
    (["inputs", "index"], ["hg19_value"]),
    (["required_files", 0, 1, "dbkey"], "hg19"),
    (["required_data_tables", 0], "test_fasta_indexes"),
]
COLLECTION_TYPE_SOURCE_EXPECTATIONS = [
    (["inputs", "input_collect", "model_class"], "TestCollectionDef"),
    (["inputs", "input_collect", "collection_type"], "list"),
]
BIGWIG_TO_WIG_EXPECTATIONS = [
    (["inputs", "chrom"], "chr21"),
]
RECORD_TWO_FILES_EXPECTATIONS = [
    (["inputs", "f1", "model_class"], "TestCollectionDef"),
    (["inputs", "f1", "collection_type"], "record"),
    (["inputs", "f1", "fields", 0, "type"], "File"),
    (["inputs", "f1", "fields", 0, "name"], "parent"),
    (["inputs", "f1", "fields", 1, "type"], "File"),
]


class TestTestParsing(TestCase):
    def _parse_tests(self):
        return parse_tool_test_descriptions(self.tool_source)

    def _init_tool_for_path(self, path):
        tool_source = get_tool_source(path)
        self.tool_source = tool_source

    def test_maxseconds_not_filled_with_default(self):
        self._init_tool_for_path(functional_test_tool_path("simple_constructs.xml"))
        test_dicts = list(self._parse_tests())
        assert test_dicts[0].maxseconds is None
        assert "maxseconds" not in test_dicts[0].to_dict()

    def test_maxseconds_parsed(self):
        self._init_tool_for_path(functional_test_tool_path("maxseconds.xml"))
        test_def = next(iter(self._parse_tests()))
        assert test_def.maxseconds == 5
        test_dict = test_def.to_dict()
        print(test_dict)
        assert "maxseconds" in test_dict
        assert test_dict["maxseconds"] == 5

    def test_simple_state_parsing(self):
        self._init_tool_for_path(functional_test_tool_path("simple_constructs.xml"))
        test_dicts = self._parse_tests()
        self._verify_each(test_dicts[0].to_dict(), SIMPLE_CONSTRUCTS_EXPECTATIONS_0)
        self._verify_each(test_dicts[1].to_dict(), SIMPLE_CONSTRUCTS_EXPECTATIONS_1)

    def test_section_state_parsing(self):
        self._init_tool_for_path(functional_test_tool_path("section.xml"))
        test_dicts = self._parse_tests()
        # without and with section tags in the tests...
        self._verify_each(test_dicts[0].to_dict(), SECTION_EXPECTATIONS)
        self._verify_each(test_dicts[1].to_dict(), SECTION_EXPECTATIONS)

    def test_repeat_state_parsing(self):
        self._init_tool_for_path(functional_test_tool_path("min_repeat.xml"))
        test_dicts = self._parse_tests()
        # without and with section tags in the tests...
        self._verify_each(test_dicts[0].to_dict(), MIN_REPEAT_EXPECTATIONS)

    def test_dynamic_options_data_table_parsing(self):
        self._init_tool_for_path(functional_test_tool_path("dbkey_filter_input.xml"))
        test_dicts = self._parse_tests()
        self._verify_each(test_dicts[0].to_dict(), DBKEY_FILTER_INPUT_EXPECTATIONS)

    def test_collection_type_source_parsing(self):
        self._init_tool_for_path(functional_test_tool_path("collection_type_source.xml"))
        test_dicts = self._parse_tests()
        self._verify_each(test_dicts[0].to_dict(), COLLECTION_TYPE_SOURCE_EXPECTATIONS)

    def test_unqualified_access_disabled_in_24_2(self):
        self._init_tool_for_path(functional_test_tool_path("deprecated/simple_constructs_24_2.xml"))
        test_dicts = self._parse_tests()
        test_0 = test_dicts[0].to_dict()
        assert test_0["error"] is True

    def test_field_collection_inputs(self):
        self._init_tool_for_path(functional_test_tool_path("collection_record_test_two_files.xml"))
        test_dicts = self._parse_tests()
        test_0 = test_dicts[0].to_dict()
        self._verify_each(test_0, RECORD_TWO_FILES_EXPECTATIONS)

    def test_bigwigtowig_converter(self):
        # defines
        if in_packages():
            skip(
                "skipping this mode for now - we need a framework test tool that skips names and just specifies arguments"
            )
        tool_path = os.path.join(
            galaxy_directory(), "lib", "galaxy", "datatypes", "converters", "bigwig_to_wig_converter.xml"
        )
        self._init_tool_for_path(tool_path)
        test_dicts = self._parse_tests()
        self._verify_each(test_dicts[1].to_dict(), BIGWIG_TO_WIG_EXPECTATIONS)

    def _verify_each(self, target_dict: dict, expectations: List[Any]):
        exception = target_dict.get("exception")
        assert not exception, f"Test failed to generate with exception {exception}"
        dict_verify_each(target_dict, expectations)

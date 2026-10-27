import threading

import pytest

import galaxy.tools
from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.tool_util.verify.parse import parse_tool_test_descriptions

TOOL_WITH_TESTS = """<tool id="${tool_id}" name="Test Tool" version="$version" profile="$profile">
    <command>echo "$param1" &gt; $out1</command>
    <inputs>
        <param type="text" name="param1" value="" />
    </inputs>
    <outputs>
        <data name="out1" format="txt" />
    </outputs>
    <tests>
        <test>
            <param name="param1" value="hello" />
            <output name="out1">
                <assert_contents>
                    <has_text text="hello" />
                </assert_contents>
            </output>
        </test>
    </tests>
</tool>
"""


class TestToolTestsParsing(UsesTools):
    def setup_method(self):
        self.setup_app()

    def teardown_method(self):
        self.tear_down_app()

    @pytest.fixture
    def parse_calls(self, monkeypatch):
        calls = []

        def counting_parse(*args, **kwds):
            calls.append(args)
            return parse_tool_test_descriptions(*args, **kwds)

        monkeypatch.setattr(galaxy.tools, "parse_tool_test_descriptions", counting_parse)
        return calls

    @pytest.mark.parametrize("profile", ["16.01", "24.2"])
    def test_tests_parsed_on_first_access(self, parse_calls, profile):
        tool = self._init_tool(TOOL_WITH_TESTS, profile=profile)
        assert parse_calls == []

        tests = tool.tests
        assert tests is not None
        assert len(tests) == 1
        assert tests[0].inputs == {"param1": "hello"}
        assert tests[0].error is False

        assert tool.tests is not None
        assert len(parse_calls) == 1

    def test_access_during_first_parse_returns_tests(self, monkeypatch):
        tool = self._init_tool(TOOL_WITH_TESTS)
        first_parse_started = threading.Event()
        release_first_parse = threading.Event()
        calls = []

        def slow_first_parse(*args, **kwds):
            calls.append(args)
            if len(calls) == 1:
                first_parse_started.set()
                release_first_parse.wait(10)
            return parse_tool_test_descriptions(*args, **kwds)

        monkeypatch.setattr(galaxy.tools, "parse_tool_test_descriptions", slow_first_parse)
        first_result = []
        first_access = threading.Thread(target=lambda: first_result.append(tool.tests))
        first_access.start()
        try:
            assert first_parse_started.wait(10)
            concurrent_tests = tool.tests
        finally:
            release_first_parse.set()
            first_access.join(10)

        assert concurrent_tests is not None
        assert len(concurrent_tests) == 1
        assert first_result[0] is not None
        assert len(first_result[0]) == 1

    def test_failing_test_parse_raises_on_every_access(self, monkeypatch):
        tool = self._init_tool(TOOL_WITH_TESTS)

        def failing_parse(*args, **kwds):
            raise Exception("broken tests")

        monkeypatch.setattr(galaxy.tools, "parse_tool_test_descriptions", failing_parse)
        for _ in range(2):
            with pytest.raises(Exception, match="broken tests"):
                _ = tool.tests

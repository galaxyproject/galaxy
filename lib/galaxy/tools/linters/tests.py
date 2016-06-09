"""This module contains a linting functions for tool tests."""
from ..lint_util import is_datasource


# Misspelled so as not be picked up by nosetests.
def lint_tsts(tool_xml, lint_ctx):
    tests = tool_xml.findall("./tests/test")
    datasource = is_datasource(tool_xml)

    if not tests and not datasource:
        lint_ctx.warn("No tests found, most tools should define test cases.")
    elif datasource:
        lint_ctx.info("No tests found, that should be OK for data_sources.")

    num_valid_tests = 0
    for test in tests:
        has_test = False
        if "expect_failure" in test.attrib or "expect_exit_code" in test.attrib:
            has_test = True
        if len(test.findall("assert_stdout")) > 0:
            has_test = True
        if len(test.findall("assert_stdout")) > 0:
            has_test = True

        outputs = test.findall("output") + test.findall("output_collection")
        if len(outputs) > 0:
            has_test = True
        if not has_test:
            lint_ctx.warn("No outputs or expectations defined for tests, this test is likely invalid.")
        else:
            num_valid_tests += 1

    if num_valid_tests or datasource:
        lint_ctx.valid("%d test(s) found.", num_valid_tests)
    else:
        lint_ctx.warn("No valid test(s) found.")

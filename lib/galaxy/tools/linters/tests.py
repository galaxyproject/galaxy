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
        if len(test.findall("assert_command")) > 0:
            has_test = True

        output_data_names, output_collection_names = _collect_output_names(tool_xml)
        found_output_test = False
        for output in test.findall("output"):
            found_output_test = True
            name = output.attrib.get("name", None)
            if not name:
                lint_ctx.warn("Found output tag without a name defined.")
            else:
                if name not in output_data_names:
                    lint_ctx.warn("Found output tag with unknown name [%s], valid names [%s]" % (name, output_data_names))

        for output_collection in test.findall("output_collection"):
            found_output_test = True
            name = output_collection.attrib.get("name", None)
            if not name:
                lint_ctx.warn("Found output_collection tag without a name defined.")
            else:
                if name not in output_collection_names:
                    lint_ctx.warn("Found output_collection tag with unknown name [%s], valid names [%s]" % (name, output_collection_names))

        has_test = has_test or found_output_test
        if not has_test:
            lint_ctx.warn("No outputs or expectations defined for tests, this test is likely invalid.")
        else:
            num_valid_tests += 1

    if num_valid_tests or datasource:
        lint_ctx.valid("%d test(s) found.", num_valid_tests)
    else:
        lint_ctx.warn("No valid test(s) found.")


def _collect_output_names(tool_xml):
    output_data_names = []
    output_collection_names = []

    outputs = tool_xml.findall("./outputs")
    if len(outputs) == 1:
        for output in list(outputs[0]):
            name = output.attrib.get("name", None)
            if not name:
                continue
            if output.tag == "data":
                output_data_names.append(name)
            elif output.tag == "collection":
                output_collection_names.append(name)

    return output_data_names, output_collection_names

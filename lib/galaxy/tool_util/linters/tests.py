"""This module contains a linting functions for tool tests."""
from ._util import is_datasource


# Misspelled so as not be picked up by nosetests.
def lint_tsts(tool_xml, lint_ctx):
    # determine line to report for general problems with tests
    try:
        tests_line = tool_xml.find("./tests").sourceline
        tests_path = tool_xml.getpath(tool_xml.find("./tests"))
    except AttributeError:
        tests_line = 1
        tests_path = None
    try:
        tests_line = tool_xml.find("./tool").sourceline
        tests_path = tool_xml.getpath(tool_xml.find("./tool"))
    except AttributeError:
        pass
    tests = tool_xml.findall("./tests/test")
    datasource = is_datasource(tool_xml)
    if not tests and not datasource:
        lint_ctx.warn("No tests found, most tools should define test cases.", line=tests_line, xpath=tests_path)
    elif datasource:
        lint_ctx.info("No tests found, that should be OK for data_sources.", line=tests_line, xpath=tests_path)

    num_valid_tests = 0
    for test_idx, test in enumerate(tests, start=1):
        has_test = False
        test_expect = ("expect_failure", "expect_exit_code", "expect_num_outputs")
        for te in test_expect:
            if te in test.attrib:
                has_test = True
                break
        test_assert = ("assert_stdout", "assert_stderr", "assert_command")
        for ta in test_assert:
            if len(test.findall(ta)) > 0:
                has_test = True
                break

        # really simple test that test parameters are also present in the inputs
        for param in test.findall("param"):
            name = param.attrib.get("name", None)
            if not name:
                lint_ctx.error(f"Test {test_idx}: Found test param tag without a name defined.", line=param.sourceline, xpath=tool_xml.getpath(param))
                continue
            name = name.split("|")[-1]
            xpaths = [f"@name='{name}'",
                      f"@argument='{name}'",
                      f"@argument='-{name}'",
                      f"@argument='--{name}'"]
            if "_" in name:
                xpaths += [f"@argument='-{name.replace('_', '-')}'",
                           f"@argument='--{name.replace('_', '-')}'"]
            found = False
            for xp in xpaths:
                inxpath = f".//inputs//param[{xp}]"
                inparam = tool_xml.findall(inxpath)
                if len(inparam) > 0:
                    found = True
                    break
            if not found:
                lint_ctx.error(f"Test {test_idx}: Test param {name} not found in the inputs", line=param.sourceline, xpath=tool_xml.getpath(param))

        output_data_names, output_collection_names = _collect_output_names(tool_xml)
        found_output_test = False
        for output in test.findall("output"):
            found_output_test = True
            name = output.attrib.get("name", None)
            if not name:
                lint_ctx.warn(f"Test {test_idx}: Found output tag without a name defined.", line=output.sourceline, xpath=tool_xml.getpath(output))
            else:
                if name not in output_data_names:
                    lint_ctx.error(f"Test {test_idx}: Found output tag with unknown name [{name}], valid names [{output_data_names}]", line=output.sourceline, xpath=tool_xml.getpath(output))

        for output_collection in test.findall("output_collection"):
            found_output_test = True
            name = output_collection.attrib.get("name", None)
            if not name:
                lint_ctx.warn(f"Test {test_idx}: Found output_collection tag without a name defined.", line=output_collection.sourceline, xpath=tool_xml.getpath(output_collection))
            else:
                if name not in output_collection_names:
                    lint_ctx.warn(f"Test {test_idx}: Found output_collection tag with unknown name [{name}], valid names [{output_collection_names}]", line=output_collection.sourceline, xpath=tool_xml.getpath(output_collection))

        has_test = has_test or found_output_test
        if not has_test:
            lint_ctx.warn("Test {test_idx}: No outputs or expectations defined for tests, this test is likely invalid.", line=test.sourceline, xpath=tool_xml.getpath(test))
        else:
            num_valid_tests += 1

    if "expect_failure" in test.attrib and found_output_test:
        lint_ctx.error(f"Test {test_idx}: Cannot specify outputs in a test expecting failure.")

    if num_valid_tests or datasource:
        lint_ctx.valid(f"{num_valid_tests} test(s) found.", line=tests_line, xpath=tool_xml.getpath(test))
    else:
        lint_ctx.warn("No valid test(s) found.", line=tests_line, xpath=tool_xml.getpath(test))


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

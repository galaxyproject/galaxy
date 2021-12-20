"""This module contains a linting functions for tool tests."""
from inspect import Parameter, signature

from ._util import is_datasource
from ..verify import asserts


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
    if not tests:
        if not datasource:
            lint_ctx.warn("No tests found, most tools should define test cases.", line=tests_line, xpath=tests_path)
        elif datasource:
            lint_ctx.info("No tests found, that should be OK for data_sources.", line=tests_line, xpath=tests_path)
        return

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
            assertions = test.findall(ta)
            if len(assertions) == 0:
                continue
            if len(assertions) > 1:
                lint_ctx.error("Test {test_idx}: More than one {ta} found. Only the first is considered.")
            has_test = True
            _check_asserts(test_idx, assertions, lint_ctx)
        _check_asserts(test_idx, test.findall(".//assert_contents"), lint_ctx)

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
        for output in test.findall("output") + test.findall("output_collection"):
            found_output_test = True
            name = output.attrib.get("name", None)
            if output.tag == "output":
                valid_names = output_data_names
            else:
                valid_names = output_collection_names
            if not name:
                lint_ctx.error(f"Test {test_idx}: Found {output.tag} tag without a name defined.", line=output.sourceline, xpath=tool_xml.getpath(output))
            else:
                if name not in valid_names:
                    lint_ctx.error(f"Test {test_idx}: Found {output.tag} tag with unknown name [{name}], valid names [{valid_names}]", line=output.sourceline, xpath=tool_xml.getpath(output))

        if "expect_failure" in test.attrib and found_output_test:
            lint_ctx.error(f"Test {test_idx}: Cannot specify outputs in a test expecting failure.")
            continue

        has_test = has_test or found_output_test
        if not has_test:
            lint_ctx.warn(f"Test {test_idx}: No outputs or expectations defined for tests, this test is likely invalid.", line=test.sourceline, xpath=tool_xml.getpath(test))
        else:
            num_valid_tests += 1

    if num_valid_tests or datasource:
        lint_ctx.valid(f"{num_valid_tests} test(s) found.", line=tests_line, xpath=tests_path)
    else:
        lint_ctx.warn("No valid test(s) found.", line=tests_line, xpath=tests_path)


def _check_asserts(test_idx, assertions, lint_ctx):
    """
    assertions is a list of assert_contents, assert_stdout, assert_stderr, assert_command
    in practice only for the first case the list may be longer than one
    """
    for assertion in assertions:
        for i, a in enumerate(assertion.iter()):
            if i == 0:  # skip root note itself
                continue
            assert_function_name = "assert_" + a.tag
            if assert_function_name not in asserts.assertion_functions:
                lint_ctx.error(f"Test {test_idx}: unknown assertion {a.tag}")
                continue
            assert_function_sig = signature(asserts.assertion_functions[assert_function_name])
            # check type of the attributes (int, float ...)
            for attrib in a.attrib:
                if attrib not in assert_function_sig.parameters:
                    lint_ctx.error(f"Test {test_idx}: unknown attribute {attrib} for {a.tag}")
                    continue
                if assert_function_sig.parameters[attrib].annotation is not Parameter.empty:
                    try:
                        assert_function_sig.parameters[attrib].annotation(a.attrib[attrib])
                    except ValueError:
                        lint_ctx.error(f"Test {test_idx}: attribute {attrib} for {a.tag} needs to be {assert_function_sig.parameters[attrib].annotation.__name__} got {a.attrib[attrib]}")
            # check missing required attributes
            for p in assert_function_sig.parameters:
                if p in ["output", "output_bytes", "verify_assertions_function", "children"]:
                    continue
                if assert_function_sig.parameters[p].default is Parameter.empty and p not in a.attrib:
                    lint_ctx.error(f"Test {test_idx}: missing attribute {p} for {a.tag}")
            # has_n_lines, has_n_columns, and has_size need to specify n/value, min, or max
            if a.tag in ["has_n_lines", "has_n_columns"]:
                if "n" not in a.attrib and "min" not in a.attrib and "max" not in a.attrib:
                    lint_ctx.error(f"Test {test_idx}: {a.tag} needs to specify 'n', 'min', or 'max'")
            if a.tag == "has_size":
                if "value" not in a.attrib and "min" not in a.attrib and "max" not in a.attrib:
                    lint_ctx.error(f"Test {test_idx}: {a.tag} needs to specify 'n', 'min', or 'max'")


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

"""This module contains a linting functions for tool tests."""
import typing
from inspect import (
    Parameter,
    signature,
)

from galaxy.util import asbool
from ._util import is_datasource
from ..verify import asserts


def check_compare_attribs(element, lint_ctx, test_idx):
    COMPARE_COMPATIBILITY = {
        "sort": ["diff", "re_match", "re_match_multiline"],
        "lines_diff": ["diff", "re_match", "contains"],
        "decompress": ["diff"],
        "delta": ["sim_size"],
        "delta_frac": ["sim_size"],
    }
    compare = element.get("compare", "diff")
    for attrib in COMPARE_COMPATIBILITY:
        if attrib in element.attrib and compare not in COMPARE_COMPATIBILITY[attrib]:
            lint_ctx.error(
                f'Test {test_idx}: Attribute {attrib} is incompatible with compare="{compare}".', node=element
            )


def lint_tests(tool_xml, lint_ctx):
    # determine node to report for general problems with tests
    tests = tool_xml.findall("./tests/test")
    general_node = tool_xml.find("./tests")
    if general_node is None:
        general_node = tool_xml.getroot()
    datasource = is_datasource(tool_xml)
    if not tests:
        if not datasource:
            lint_ctx.warn("No tests found, most tools should define test cases.", node=general_node)
        elif datasource:
            lint_ctx.info("No tests found, that should be OK for data_sources.", node=general_node)
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
                lint_ctx.error(f"Test {test_idx}: More than one {ta} found. Only the first is considered.", node=test)
            has_test = True
            _check_asserts(test_idx, assertions, lint_ctx)
        _check_asserts(test_idx, test.findall(".//assert_contents"), lint_ctx)

        # check if expect_num_outputs is set if there are outputs with filters
        filter = tool_xml.findall("./outputs//filter")
        if len(filter) > 0 and "expect_num_outputs" not in test.attrib:
            lint_ctx.warn("Test should specify 'expect_num_outputs' if outputs have filters", node=test)

        # really simple test that test parameters are also present in the inputs
        for param in test.findall("param"):
            name = param.attrib.get("name", None)
            if not name:
                lint_ctx.error(f"Test {test_idx}: Found test param tag without a name defined.", node=param)
                continue
            name = name.split("|")[-1]
            xpaths = [f"@name='{name}'", f"@argument='{name}'", f"@argument='-{name}'", f"@argument='--{name}'"]
            if "_" in name:
                xpaths += [f"@argument='-{name.replace('_', '-')}'", f"@argument='--{name.replace('_', '-')}'"]
            found = False
            for xp in xpaths:
                inxpath = f".//inputs//param[{xp}]"
                inparam = tool_xml.findall(inxpath)
                if len(inparam) > 0:
                    found = True
                    break
            if not found:
                lint_ctx.error(f"Test {test_idx}: Test param {name} not found in the inputs", node=param)

        output_data_or_collection = _collect_output_names(tool_xml)
        found_output_test = False
        for output in test.findall("output") + test.findall("output_collection"):
            found_output_test = True
            name = output.attrib.get("name", None)
            if not name:
                lint_ctx.error(f"Test {test_idx}: Found {output.tag} tag without a name defined.", node=output)
                continue
            if name not in output_data_or_collection:
                lint_ctx.error(
                    f"Test {test_idx}: Found {output.tag} tag with unknown name [{name}], valid names {list(output_data_or_collection)}",
                    node=output,
                )
                continue

            if output.tag == "output":
                check_compare_attribs(output, lint_ctx, test_idx)
            elements = output.findall("./element")
            if elements:
                for element in elements:
                    check_compare_attribs(element, lint_ctx, test_idx)

            # check that
            # - test/output corresponds to outputs/data and
            # - test/collection to outputs/output_collection
            corresponding_output = output_data_or_collection[name]
            if output.tag == "output" and corresponding_output.tag != "data":
                lint_ctx.error(
                    f"Test {test_idx}: test output {name} does not correspond to a 'data' output, but a '{corresponding_output.tag}'",
                    node=output,
                )
            elif output.tag == "output_collection" and corresponding_output.tag != "collection":
                lint_ctx.error(
                    f"Test {test_idx}: test collection output '{name}' does not correspond to a 'output_collection' output, but a '{corresponding_output.tag}'",
                    node=output,
                )

            # check that discovered data is tested sufficiently
            discover_datasets = corresponding_output.find(".//discover_datasets")
            if discover_datasets is not None:
                if output.tag == "output":
                    if "count" not in output.attrib and output.find("./discovered_dataset") is None:
                        lint_ctx.error(
                            f"Test {test_idx}: test output '{name}' must have a 'count' attribute and/or 'discovered_dataset' children",
                            node=output,
                        )
                else:
                    if "count" not in output.attrib and len(elements) == 0:
                        lint_ctx.error(
                            f"Test {test_idx}: test collection '{name}' must have a 'count' attribute or 'element' children",
                            node=output,
                        )
                    if corresponding_output.get("type", "") in ["list:list", "list:paired"]:
                        nested_elements = output.find("./element/element")
                        element_with_count = output.find("./element[@count]")
                        if nested_elements is None and element_with_count is None:
                            lint_ctx.error(
                                f"Test {test_idx}: test collection '{name}' must contain nested 'element' tags and/or element childen with a 'count' attribute",
                                node=output,
                            )

        if "expect_failure" in test.attrib and asbool(test.attrib["expect_failure"]):
            if found_output_test:
                lint_ctx.error(f"Test {test_idx}: Cannot specify outputs in a test expecting failure.", node=test)
                continue
            if "expect_num_outputs" in test.attrib:
                lint_ctx.error(
                    f"Test {test_idx}: Cannot make assumptions on the number of outputs in a test expecting failure.",
                    node=test,
                )
                continue

        has_test = has_test or found_output_test
        if not has_test:
            lint_ctx.warn(
                f"Test {test_idx}: No outputs or expectations defined for tests, this test is likely invalid.",
                node=test,
            )
        else:
            num_valid_tests += 1

    if num_valid_tests or datasource:
        lint_ctx.valid(f"{num_valid_tests} test(s) found.", node=general_node)
    else:
        lint_ctx.warn("No valid test(s) found.", node=general_node)


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
                lint_ctx.error(f"Test {test_idx}: unknown assertion '{a.tag}'", node=a)
                continue
            assert_function_sig = signature(asserts.assertion_functions[assert_function_name])
            # check type of the attributes (int, float ...)
            for attrib in a.attrib:
                if attrib not in assert_function_sig.parameters:
                    lint_ctx.error(f"Test {test_idx}: unknown attribute '{attrib}' for '{a.tag}'", node=a)
                    continue
                annotation = assert_function_sig.parameters[attrib].annotation
                annotation = _handle_optionals(annotation)
                if annotation is not Parameter.empty:
                    try:
                        annotation(a.attrib[attrib])
                    except TypeError:
                        raise Exception(f"Faild to instantiate {attrib} for {assert_function_name}")
                    except ValueError:
                        lint_ctx.error(
                            f"Test {test_idx}: attribute '{attrib}' for '{a.tag}' needs to be '{annotation.__name__}' got '{a.attrib[attrib]}'",
                            node=a,
                        )
            # check missing required attributes
            for p in assert_function_sig.parameters:
                if p in ["output", "output_bytes", "verify_assertions_function", "children"]:
                    continue
                if assert_function_sig.parameters[p].default is Parameter.empty and p not in a.attrib:
                    lint_ctx.error(f"Test {test_idx}: missing attribute '{p}' for '{a.tag}'", node=a)
            # has_n_lines, has_n_columns, and has_size need to specify n/value, min, or max
            if a.tag in ["has_n_lines", "has_n_columns"]:
                if "n" not in a.attrib and "min" not in a.attrib and "max" not in a.attrib:
                    lint_ctx.error(f"Test {test_idx}: '{a.tag}' needs to specify 'n', 'min', or 'max'", node=a)
            if a.tag == "has_size":
                if "value" not in a.attrib and "min" not in a.attrib and "max" not in a.attrib:
                    lint_ctx.error(f"Test {test_idx}: '{a.tag}' needs to specify 'value', 'min', or 'max'", node=a)


def _handle_optionals(annotation):
    as_dict = annotation.__dict__
    if "__origin__" in as_dict and as_dict["__origin__"] == typing.Union:
        return as_dict["__args__"][0]
    return annotation


def _collect_output_names(tool_xml):
    """
    determine dict mapping the names of data and collection outputs to the
    corresponding nodes
    """
    output_data_or_collection = {}
    outputs = tool_xml.findall("./outputs")
    if len(outputs) == 1:
        for output in list(outputs[0]):
            name = output.attrib.get("name", None)
            if not name:
                continue
            output_data_or_collection[name] = output
    return output_data_or_collection

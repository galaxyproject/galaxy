"""This module contains a linting functions for tool tests."""

from io import StringIO
from typing import (
    Iterator,
    List,
    Tuple,
    TYPE_CHECKING,
)

from packaging.version import Version

from galaxy.tool_util.lint import Linter
from galaxy.tool_util.parameters import validate_test_cases_for_tool_source
from galaxy.tool_util_models.assertions import assertion_list
from galaxy.util import asbool
from ._util import is_datasource

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource
    from galaxy.util.etree import Element

lint_tool_types = ["default", "data_source", "manage_data"]


class TestsMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        root = tool_xml.find("./tests")
        if root is None:
            root = tool_xml.getroot()
        if len(tests) == 0 and not is_datasource(tool_xml):
            lint_ctx.warn("No tests found, most tools should define test cases.", linter=cls.name(), node=root)


class TestsMissingDatasource(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        root = tool_xml.find("./tests")
        if root is None:
            root = tool_xml.getroot()
        if len(tests) == 0 and is_datasource(tool_xml):
            lint_ctx.info("No tests found, that should be OK for data_sources.", linter=cls.name(), node=root)


class TestsAssertsMultiple(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            # TODO same would be nice also for assert_contents
            for ta in ("assert_stdout", "assert_stderr", "assert_command"):
                if len(test.findall(ta)) > 1:
                    lint_ctx.error(
                        f"Test {test_idx}: More than one {ta} found. Only the first is considered.",
                        linter=cls.name(),
                        node=test,
                    )


class TestsAssertsHasNQuant(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for a in test.xpath(
                ".//*[self::assert_contents or self::assert_stdout or self::assert_stderr or self::assert_command]//*"
            ):
                if a.tag not in ["has_n_lines", "has_n_columns"]:
                    continue
                if not (set(a.attrib) & {"n", "min", "max"}):
                    lint_ctx.error(
                        f"Test {test_idx}: '{a.tag}' needs to specify 'n', 'min', or 'max'", linter=cls.name(), node=a
                    )


class TestsAssertsHasSizeQuant(Linter):
    """
    has_size needs at least one of size (or value), min, max
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for a in test.xpath(
                ".//*[self::assert_contents or self::assert_stdout or self::assert_stderr or self::assert_command]//*"
            ):
                if a.tag != "has_size":
                    continue
                if len(set(a.attrib) & {"value", "size", "min", "max"}) == 0:
                    lint_ctx.error(
                        f"Test {test_idx}: '{a.tag}' needs to specify 'size', 'min', or 'max'",
                        linter=cls.name(),
                        node=a,
                    )


class TestsAssertsHasSizeOrValueQuant(Linter):
    """
    has_size should not have size and value
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for a in test.xpath(
                ".//*[self::assert_contents or self::assert_stdout or self::assert_stderr or self::assert_command]//*"
            ):
                if a.tag != "has_size":
                    continue
                if "value" in a.attrib and "size" in a.attrib:
                    lint_ctx.error(
                        f"Test {test_idx}: '{a.tag}' must not specify 'value' and 'size'",
                        linter=cls.name(),
                        node=a,
                    )


class TestsAssertionValidation(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        try:
            raw_tests_dict = tool_source.parse_tests_to_dict()
        except Exception:
            lint_ctx.warn("Failed to parse test dictionaries from tool - cannot lint assertions")
            return
        assert "tests" in raw_tests_dict
        for test_idx, test in enumerate(raw_tests_dict["tests"], start=1):
            # TODO: validate command, command_version, element tests. What about children?
            for output in test["outputs"]:
                asserts_raw = output.get("attributes", {}).get("assert_list") or []
                to_yaml_assertions = []
                for raw_assert in asserts_raw:
                    to_yaml_assertions.append({"that": raw_assert["tag"], **raw_assert.get("attributes", {})})
                try:
                    assertion_list.model_validate(to_yaml_assertions)
                except Exception as e:
                    error_str = _cleanup_pydantic_error(e)
                    lint_ctx.warn(
                        f"Test {test_idx}: failed to validate assertions. Validation errors are [{error_str}]",
                        linter=cls.name(),
                    )


class TestsCaseValidation(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        profile = tool_source.parse_profile()
        lint_log = lint_ctx.warn if Version(profile) < Version("24.2") else lint_ctx.error

        try:
            validation_results = validate_test_cases_for_tool_source(tool_source, use_latest_profile=True)
        except Exception as e:
            lint_log(
                f"Serious problem parsing tool source or tests - cannot validate test cases. The exception is [{e}]",
                linter=cls.name(),
            )
            return
        for test_idx, validation_result in enumerate(validation_results, start=1):
            error = validation_result.validation_error
            if error:
                error_str = _cleanup_pydantic_error(error)
                lint_log(
                    f"Test {test_idx}: failed to validate test parameters against inputs - tests won't run on a modern Galaxy tool profile version. Validation errors are [{error_str}]",
                    linter=cls.name(),
                )


def _cleanup_pydantic_error(error) -> str:
    full_validation_error = f"{error}"
    new_error = StringIO("")
    for line in full_validation_error.splitlines():
        # this repeated over and over isn't useful in the context of how we're building the dynamic models,
        # tool authors should not be looking up pydantic docs on models they cannot even really inspect
        if line.strip().startswith("For further information visit https://errors.pydantic"):
            continue
        else:
            new_error.write(f"{line}\n")
    return new_error.getvalue().strip()


class TestsExpectNumOutputs(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            # check if expect_num_outputs is set if there are outputs with filters
            # (except for tests with expect_failure .. which can't have test outputs)
            has_no_filter = (
                tool_xml.find("./outputs/data/filter") is None and tool_xml.find("./outputs/collection/filter") is None
            )
            if not (
                has_no_filter or "expect_num_outputs" in test.attrib or asbool(test.attrib.get("expect_failure", False))
            ):
                lint_ctx.warn(
                    f"Test {test_idx}: should specify 'expect_num_outputs' if outputs have filters",
                    linter=cls.name(),
                    node=test,
                )


class TestsParamInInputs(Linter):
    """
    really simple linter that test parameters are also present in the inputs
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for param in test.findall("param"):
                name = param.attrib.get("name", None)
                if not name:
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
                    lint_ctx.error(
                        f"Test {test_idx}: Test param {name} not found in the inputs", linter=cls.name(), node=param
                    )


class TestsOutputName(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            # note output_collections are covered by xsd, but output is not required to have one by xsd
            for output in test.findall("output"):
                if not output.attrib.get("name", None):
                    lint_ctx.error(
                        f"Test {test_idx}: Found {output.tag} tag without a name defined.",
                        linter=cls.name(),
                        node=output,
                    )


class TestsOutputDefined(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output") + test.findall("output_collection"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    lint_ctx.error(
                        f"Test {test_idx}: Found {output.tag} tag with unknown name [{name}], valid names {list(output_data_or_collection)}",
                        linter=cls.name(),
                        node=output,
                    )


class TestsOutputCorresponding(Linter):
    """
    Linter checking if test/output corresponds to outputs/data
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output") + test.findall("output_collection"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    continue

                # - test/collection to outputs/output_collection
                corresponding_output = output_data_or_collection[name]
                if output.tag == "output" and corresponding_output.tag != "data":
                    lint_ctx.error(
                        f"Test {test_idx}: test output {name} does not correspond to a 'data' output, but a '{corresponding_output.tag}'",
                        linter=cls.name(),
                        node=output,
                    )


class TestsOutputCollectionCorresponding(Linter):
    """
    Linter checking if test/collection corresponds to outputs/output_collection
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output") + test.findall("output_collection"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    continue

                # - test/collection to outputs/output_collection
                corresponding_output = output_data_or_collection[name]
                if output.tag == "output_collection" and corresponding_output.tag != "collection":
                    lint_ctx.error(
                        f"Test {test_idx}: test collection output '{name}' does not correspond to a 'output_collection' output, but a '{corresponding_output.tag}'",
                        linter=cls.name(),
                        node=output,
                    )


class TestsOutputCompareAttrib(Linter):
    """
    Linter checking compatibility of output attributes with the value
    of the compare attribute
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        COMPARE_COMPATIBILITY = {
            "sort": ["diff", "re_match", "re_match_multiline"],
            "lines_diff": ["diff", "re_match", "contains"],
            "decompress": ["diff"],
            "delta": ["sim_size"],
            "delta_frac": ["sim_size"],
            "metric": ["image_diff"],
            "eps": ["image_diff"],
        }
        for test_idx, test in enumerate(tests, start=1):
            for output in test.xpath(".//*[self::output or self::element or self::discovered_dataset]"):
                compare = output.get("compare", "diff")
                for attrib in COMPARE_COMPATIBILITY:
                    if attrib in output.attrib and compare not in COMPARE_COMPATIBILITY[attrib]:
                        lint_ctx.error(
                            f'Test {test_idx}: Attribute {attrib} is incompatible with compare="{compare}".',
                            linter=cls.name(),
                            node=output,
                        )


class TestsOutputCheckDiscovered(Linter):
    """
    Linter checking that discovered elements of outputs are tested with
    a count attribute or listing some discovered_dataset
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    continue

                # - test/collection to outputs/output_collection
                corresponding_output = output_data_or_collection[name]
                discover_datasets = corresponding_output.find(".//discover_datasets")
                if discover_datasets is None:
                    continue
                if "count" not in output.attrib and output.find("./discovered_dataset") is None:
                    lint_ctx.error(
                        f"Test {test_idx}: test output '{name}' must have a 'count' attribute and/or 'discovered_dataset' children",
                        linter=cls.name(),
                        node=output,
                    )


class TestsOutputCollectionCheckDiscovered(Linter):
    """
    Linter checking that discovered elements of output collections
    are tested with a count attribute or listing some elements
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output_collection"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    continue
                # - test/collection to outputs/output_collection
                corresponding_output = output_data_or_collection[name]
                discover_datasets = corresponding_output.find(".//discover_datasets")
                if discover_datasets is None:
                    continue
                if "count" not in output.attrib and output.find("./element") is None:
                    lint_ctx.error(
                        f"Test {test_idx}: test collection '{name}' must have a 'count' attribute or 'element' children",
                        linter=cls.name(),
                        node=output,
                    )


class TestsOutputCollectionCheckDiscoveredNested(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output_data_or_collection = _collect_output_names(tool_xml)
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            for output in test.findall("output_collection"):
                name = output.attrib.get("name", None)
                if not name:
                    continue
                if name not in output_data_or_collection:
                    continue

                # - test/collection to outputs/output_collection
                corresponding_output = output_data_or_collection[name]
                if corresponding_output.find(".//discover_datasets") is None:
                    continue
                if corresponding_output.get("type", "") in ["list:list", "list:paired"]:
                    nested_elements = output.find("./element/element")
                    element_with_count = output.find("./element[@count]")
                    if nested_elements is None and element_with_count is None:
                        lint_ctx.error(
                            f"Test {test_idx}: test collection '{name}' must contain nested 'element' tags and/or element children with a 'count' attribute",
                            linter=cls.name(),
                            node=output,
                        )


class TestsOutputFailing(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            if not asbool(test.attrib.get("expect_failure", False)):
                continue
            if test.find("output") is not None or test.find("output_collection") is not None:
                lint_ctx.error(
                    f"Test {test_idx}: Cannot specify outputs in a test expecting failure.",
                    linter=cls.name(),
                    node=test,
                )


class TestsExpectNumOutputsFailing(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in enumerate(tests, start=1):
            if not asbool(test.attrib.get("expect_failure", False)):
                continue
            if test.find("output") is not None or test.find("output_collection") is not None:
                continue
            if "expect_num_outputs" in test.attrib:
                lint_ctx.error(
                    f"Test {test_idx}: Cannot make assumptions on the number of outputs in a test expecting failure.",
                    linter=cls.name(),
                    node=test,
                )


class TestsHasExpectations(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tests = tool_xml.findall("./tests/test")
        for test_idx, test in _iter_tests(tests, valid=False):
            lint_ctx.warn(
                f"Test {test_idx}: No outputs or expectations defined for tests, this test is likely invalid.",
                linter=cls.name(),
                node=test,
            )


class TestsNoValid(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        general_node = tool_xml.find("./tests")
        if general_node is None:
            general_node = tool_xml.getroot()
        tests = tool_xml.findall("./tests/test")
        if not tests:
            return
        num_valid_tests = len(list(_iter_tests(tests, valid=True)))
        if num_valid_tests or is_datasource(tool_xml):
            lint_ctx.valid(f"{num_valid_tests} test(s) found.", linter=cls.name(), node=general_node)


class TestsValid(Linter):
    """ """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        general_node = tool_xml.find("./tests")
        if general_node is None:
            general_node = tool_xml.getroot()
        tests = tool_xml.findall("./tests/test")
        if not tests:
            return
        num_valid_tests = len(list(_iter_tests(tests, valid=True)))
        if not (num_valid_tests or is_datasource(tool_xml)):
            lint_ctx.warn("No valid test(s) found.", linter=cls.name(), node=general_node)


def _iter_tests(tests: List["Element"], valid: bool) -> Iterator[Tuple[int, "Element"]]:
    for test_idx, test in enumerate(tests, start=1):
        is_valid = False
        is_valid |= bool(set(test.attrib) & {"expect_failure", "expect_exit_code", "expect_num_outputs"})
        for ta in ("assert_stdout", "assert_stderr", "assert_command"):
            if test.find(ta) is not None:
                is_valid = True
        found_output_test = test.find("output") is not None or test.find("output_collection") is not None
        if asbool(test.attrib.get("expect_failure", False)):
            if found_output_test or "expect_num_outputs" in test.attrib:
                continue
        is_valid |= found_output_test
        if is_valid == valid:
            yield (test_idx, test)


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

"""This module contains a linting functions for tool outputs."""

import ast
from typing import TYPE_CHECKING

from packaging.version import Version

from galaxy.tool_util.lint import Linter
from ._util import is_valid_cheetah_placeholder
from ..parser.output_collection_def import NAMED_PATTERNS

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser import ToolSource
    from galaxy.util.etree import (
        Element,
        ElementTree,
    )


class OutputsMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        tool_node = tool_xml.find("./outputs")
        if tool_node is None:
            tool_node = tool_xml.getroot()
        if len(tool_xml.findall("./outputs")) == 0:
            lint_ctx.warn(
                "Tool contains no outputs section, most tools should produce outputs.",
                linter=cls.name(),
                node=tool_node,
            )


class OutputsOutput(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        output = tool_xml.find("./outputs/output")
        if output is not None:
            lint_ctx.warn(
                "Avoid the use of 'output' and replace by 'data' or 'collection'", linter=cls.name(), node=output
            )


class OutputsNameInvalidCheetah(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for output in tool_xml.findall("./outputs/data[@name]") + tool_xml.findall("./outputs/collection[@name]"):
            if not is_valid_cheetah_placeholder(output.attrib["name"]):
                lint_ctx.warn(
                    f'Tool output name [{output.attrib["name"]}] is not a valid Cheetah placeholder.',
                    linter=cls.name(),
                    node=output,
                )


class OutputsNameDuplicated(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        names = set()
        for output in tool_xml.findall("./outputs/data[@name]") + tool_xml.findall("./outputs/collection[@name]"):
            name = output.attrib["name"]
            if name in names:
                lint_ctx.error(f"Tool output [{name}] has duplicated name", linter=cls.name(), node=output)
            names.add(name)


class OutputsFilterExpression(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for filter in tool_xml.findall("./outputs/*/filter"):
            try:
                ast.parse(filter.text, mode="eval")
            except Exception as e:
                lint_ctx.warn(
                    f"Filter '{filter.text}' is no valid expression: {str(e)}",
                    linter=cls.name(),
                    node=filter,
                )


class OutputsLabelDuplicatedFilter(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        labels = set()
        for output in tool_xml.findall("./outputs/data") + tool_xml.findall("./outputs/collection"):
            name = output.attrib.get("name", "")
            label = output.attrib.get("label", "${tool.name} on ${on_string}")
            if label in labels and output.find("./filter") is not None:
                lint_ctx.warn(
                    f"Tool output [{name}] uses duplicated label '{label}', double check if filters imply disjoint cases",
                    linter=cls.name(),
                    node=output,
                )
            labels.add(label)


class OutputsLabelDuplicatedNoFilter(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        labels = set()
        for output in tool_xml.findall("./outputs/data[@name]") + tool_xml.findall("./outputs/collection[@name]"):
            name = output.attrib.get("name", "")
            label = output.attrib.get("label", "${tool.name} on ${on_string}")
            if label in labels and output.find("./filter") is None:
                lint_ctx.warn(f"Tool output [{name}] uses duplicated label '{label}'", linter=cls.name(), node=output)
            labels.add(label)


class OutputsCollectionType(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for output in tool_xml.findall("./outputs/collection"):
            if "type" not in output.attrib:
                lint_ctx.warn("Collection output with undefined 'type' found.", linter=cls.name(), node=output)


class OutputsNumber(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        outputs = tool_xml.findall("./outputs")
        if len(outputs) == 0:
            return
        num_outputs = len(outputs[0].findall("./data")) + len(outputs[0].findall("./collection"))
        lint_ctx.info(f"{num_outputs} outputs found.", linter=cls.name(), node=outputs[0])


class OutputsFormatInput(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        def _report(output: "Element"):
            message = f"Using format='input' on {output.tag} is deprecated. Use the format_source attribute."
            if Version(str(profile)) <= Version("16.01"):
                lint_ctx.warn(message, linter=cls.name(), node=output)
            else:
                lint_ctx.error(message, linter=cls.name(), node=output)

        profile = tool_source.parse_profile()
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for output in tool_xml.findall("./outputs/data") + tool_xml.findall("./outputs/collection"):
            fmt = output.attrib.get("format")
            if fmt == "input":
                _report(output)
            for sub in output:
                fmt = sub.attrib.get("format", sub.attrib.get("ext"))
                if fmt == "input":
                    _report(output)


class OutputsFormat(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for output in tool_xml.findall("./outputs/data") + tool_xml.findall("./outputs/collection"):
            format_set = False
            if _check_format(output):
                format_set = True
            if output.tag == "data":
                if "auto_format" in output.attrib and output.attrib["auto_format"]:
                    format_set = True

            elif output.tag == "collection":
                if "structured_like" in output.attrib and "inherit_format" in output.attrib:
                    format_set = True
            for sub in output:
                if _check_pattern(sub) or _has_tool_provided_metadata(tool_xml):
                    format_set = True
                elif _check_format(sub):
                    format_set = True

            if not format_set:
                lint_ctx.warn(
                    f"Tool {output.tag} output {output.attrib.get('name', 'with missing name')} doesn't define an output format.",
                    linter=cls.name(),
                    node=output,
                )


class OutputsFormatSourceIncomp(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        def _check_and_report(node):
            if "format_source" in node.attrib and ("ext" in node.attrib or "format" in node.attrib):
                lint_ctx.warn(
                    f"Tool {node.tag} output '{node.attrib.get('name', 'with missing name')}' should use either format_source or format/ext",
                    linter=cls.name(),
                    node=node,
                )

        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for output in tool_xml.findall("./outputs/data") + tool_xml.findall("./outputs/collection"):
            _check_and_report(output)
            for sub in output:
                _check_and_report(sub)


def _check_format(node):
    """
    check if format/ext/format_source attribute is set in a given node
    issue a warning if the value is input
    return true (node defines format/ext) / false (else)
    """
    if "format_source" in node.attrib:
        return True
    if node.find(".//action[@type='format']") is not None:
        return True
    # if allowed (e.g. for discover_datasets), ext takes precedence over format
    fmt = node.attrib.get("format", node.attrib.get("ext"))
    return fmt is not None


def _check_pattern(node):
    """
    check if
    - pattern attribute is set and defines the extension or
    - from_tool_provided_metadata is true
    """
    if node.tag != "discover_datasets":
        return False
    if "pattern" not in node.attrib:
        return False
    pattern = node.attrib["pattern"]
    regex_pattern = NAMED_PATTERNS.get(pattern, pattern)
    # TODO error on wrong pattern or non-regexp
    if "(?P<ext>" in regex_pattern:
        return True


def _has_tool_provided_metadata(tool_xml: "ElementTree") -> bool:
    outputs = tool_xml.find("./outputs")
    if outputs is not None:
        if "provided_metadata_file" in outputs.attrib or "provided_metadata_style" in outputs.attrib:
            return True
    command = tool_xml.find("./command")
    if command is not None:
        if "galaxy.json" in command.text:
            return True
    config = tool_xml.find("./configfiles/configfile[@filename='galaxy.json']")
    if config is not None:
        return True
    return False

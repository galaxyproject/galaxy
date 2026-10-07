"""This module contains a linting functions for tool outputs."""

import ast
import re
from typing import (
    NamedTuple,
    TYPE_CHECKING,
)

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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        if (output := tool_xml.find("./outputs/output")) is not None:
            lint_ctx.warn(
                "Avoid the use of 'output' and replace by 'data' or 'collection'", linter=cls.name(), node=output
            )


class OutputsNameInvalidCheetah(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for output in tool_xml.findall("./outputs/data[@name]") + tool_xml.findall("./outputs/collection[@name]"):
            if not is_valid_cheetah_placeholder(output.attrib["name"]):
                lint_ctx.warn(
                    f"Tool output name [{output.attrib['name']}] is not a valid Cheetah placeholder.",
                    linter=cls.name(),
                    node=output,
                )


class OutputsNameDuplicated(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for filter in tool_xml.findall("./outputs/*/filter"):
            try:
                ast.parse(filter.text.strip(), mode="eval")
            except Exception as e:
                lint_ctx.warn(
                    f"Filter '{filter.text}' is no valid expression: {str(e)}",
                    linter=cls.name(),
                    node=filter,
                )


class OutputsLabelDuplicatedFilter(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        for output in tool_xml.findall("./outputs/collection"):
            if "type" not in output.attrib:
                lint_ctx.warn("Collection output with undefined 'type' found.", linter=cls.name(), node=output)


class OutputsNumber(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        def _report(output: "Element") -> None:
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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
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
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        def _check_and_report(node: "Element") -> None:
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


class OutputsStructuredLikeReference(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        input_references = _InputReferences(tool_xml)
        profile = Version(tool_source.parse_profile())
        for output in tool_xml.findall("./outputs/collection[@structured_like]"):
            _check_structured_like_reference(
                lint_ctx, cls.name(), output, output.attrib["structured_like"], input_references, profile
            )


class OutputsFormatSourceReference(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return
        input_references = _InputReferences(tool_xml)
        for output in (
            tool_xml.findall("./outputs/data[@format_source]")
            + tool_xml.findall("./outputs/collection[@format_source]")
            + tool_xml.findall("./outputs/collection/data[@format_source]")
        ):
            _check_format_source_reference(
                lint_ctx, cls.name(), output, output.attrib["format_source"], input_references
            )


# Same single-selector shape resolve_format_source accepts, e.g. input_collection['forward'].
ELEMENT_SELECTOR = re.compile(r"^([^\[\]]*)\[[^\[\]]*\]$")


class _InputReference(NamedTuple):
    qualified: str
    legacy: str
    param_type: str | None
    in_repeat: bool

    @property
    def is_collection(self) -> bool:
        return self.param_type == "data_collection"

    @property
    def name(self) -> str:
        return self.qualified.rsplit("|", 1)[-1]


class _InputReferences:
    """Input parameter paths as runtime keys them, with repeat indices normalized to ``_0``.

    ``qualified`` includes every conditional, section and repeat. ``legacy`` is the alias
    ``visit_input_values`` also records, which omits only the innermost conditional or
    section name.
    """

    def __init__(self, tool_xml: "ElementTree") -> None:
        self.references: list[_InputReference] = []
        self.repeat_names: set[str] = set()
        inputs = tool_xml.find("./inputs")
        if inputs is not None:
            self._visit(inputs, [], [], False)

    def _visit(self, element: "Element", qualified: list[str], legacy: list[str], in_repeat: bool) -> None:
        for child in element:
            name = child.attrib.get("name")
            if child.tag == "param":
                name = _param_name(child)
                if name:
                    self.references.append(
                        _InputReference(
                            "|".join(qualified + [name]),
                            "|".join(legacy + [name]),
                            child.attrib.get("type"),
                            in_repeat,
                        )
                    )
            elif child.tag in ("conditional", "section"):
                if name:
                    self._visit(child, qualified + [name], qualified, in_repeat)
            elif child.tag == "repeat":
                if name:
                    self.repeat_names.add(name)
                    path = qualified + [f"{name}_0"]
                    self._visit(child, path, path, True)
            elif child.tag == "when":
                self._visit(child, qualified, legacy, in_repeat)

    def normalize(self, reference: str) -> str:
        segments = []
        for segment in reference.split("|"):
            base, _, index = segment.rpartition("_")
            if index.isdigit() and base in self.repeat_names:
                segment = f"{base}_0"
            segments.append(segment)
        return "|".join(segments)

    def qualified(self, reference: str) -> list[_InputReference]:
        return [r for r in self.references if r.qualified == reference]

    def candidates(self, reference: str) -> list[str]:
        name = reference.rsplit("|", 1)[-1]
        return sorted({r.qualified for r in self.references if r.name == name})


def _param_name(param: "Element") -> str | None:
    name: str | None = param.attrib.get("name")
    if not name:
        argument: str | None = param.attrib.get("argument")
        if argument:
            name = argument.lstrip("-").replace("-", "_")
    return name


def _check_format_source_reference(
    lint_ctx: "LintContext",
    linter_name: str,
    node: "Element",
    ref_value: str,
    input_references: _InputReferences,
) -> None:
    path = ref_value
    if selector_match := ELEMENT_SELECTOR.match(ref_value):
        path = selector_match.group(1)
    selector = ref_value[len(path) :]
    normalized = input_references.normalize(path)
    matches = input_references.qualified(normalized)
    if not matches:
        matches = [r for r in input_references.references if r.legacy == normalized]
        if matches and node.tag == "collection" and node.find("discover_datasets") is not None:
            # Discovered elements resolve format_source against the job's input associations,
            # which are keyed by qualified name only.
            qualified_names = " or ".join(f"'{name}{selector}'" for name in sorted({r.qualified for r in matches}))
            lint_ctx.error(
                f"Output '{_output_name(node)}' uses unqualified format_source='{ref_value}', which discovered "
                f"elements cannot resolve. Use the qualified name {qualified_names}.",
                linter=linter_name,
                node=node,
            )
            return
        _warn_unqualified(lint_ctx, linter_name, node, ref_value, "format_source", matches, selector)
    if not matches:
        _error_unmatched(
            lint_ctx, linter_name, node, ref_value, "format_source", input_references, normalized, selector
        )
    elif selector_match and not any(r.is_collection for r in matches):
        lint_ctx.error(
            f"Output '{_output_name(node)}' selects an element with format_source='{ref_value}' "
            f"but '{path}' is not a collection input.",
            linter=linter_name,
            node=node,
        )


def _check_structured_like_reference(
    lint_ctx: "LintContext",
    linter_name: str,
    node: "Element",
    ref_value: str,
    input_references: _InputReferences,
    profile: Version,
) -> None:
    # A reference must resolve both when mapping over (execute.py sliced_input_collection_structure:
    # qualified paths only, no repeats, a bare name at any depth before profile 26.0) and when not
    # (collection_prototype: qualified paths or the legacy alias). Only a bare name whose legacy
    # alias matches satisfies both before profile 26.0.
    normalized = input_references.normalize(ref_value)
    matches = input_references.qualified(normalized)
    if not matches and "|" not in ref_value and profile < Version("26.0"):
        matches = [r for r in input_references.references if r.legacy == ref_value]
        _warn_unqualified(lint_ctx, linter_name, node, ref_value, "structured_like", matches, "")
    if not matches:
        _error_unmatched(lint_ctx, linter_name, node, ref_value, "structured_like", input_references, normalized, "")
    elif all(r.in_repeat for r in matches):
        lint_ctx.error(
            f"Output '{_output_name(node)}' references structured_like='{ref_value}' inside a repeat, "
            "which cannot be resolved when mapping over collections.",
            linter=linter_name,
            node=node,
        )
    elif not any(r.param_type in ("data", "data_collection") for r in matches):
        lint_ctx.error(
            f"Output '{_output_name(node)}' references structured_like='{ref_value}' which is not a dataset or collection input.",
            linter=linter_name,
            node=node,
        )


def _output_name(node: "Element") -> str:
    name: str = node.attrib.get("name", "unknown")
    return name


def _warn_unqualified(
    lint_ctx: "LintContext",
    linter_name: str,
    node: "Element",
    ref_value: str,
    attr_name: str,
    matches: list[_InputReference],
    selector: str,
) -> None:
    qualified_names = sorted({r.qualified for r in matches})
    if len(qualified_names) == 1:
        lint_ctx.warn(
            f"Output '{_output_name(node)}' uses unqualified {attr_name}='{ref_value}'. "
            f"Use the qualified name '{qualified_names[0]}{selector}'.",
            linter=linter_name,
            node=node,
        )
    elif len(qualified_names) > 1:
        lint_ctx.warn(
            f"Output '{_output_name(node)}' uses ambiguous unqualified {attr_name}='{ref_value}' "
            f"matching multiple inputs: {', '.join(qualified_names)}. Use a qualified name.",
            linter=linter_name,
            node=node,
        )


def _error_unmatched(
    lint_ctx: "LintContext",
    linter_name: str,
    node: "Element",
    ref_value: str,
    attr_name: str,
    input_references: _InputReferences,
    normalized: str,
    selector: str,
) -> None:
    candidates = input_references.candidates(normalized)
    suggestion = f" Did you mean '{candidates[0]}{selector}'?" if len(candidates) == 1 else ""
    lint_ctx.error(
        f"Output '{_output_name(node)}' references {attr_name}='{ref_value}' which does not match any input parameter."
        f"{suggestion}",
        linter=linter_name,
        node=node,
    )


def _has_tool_provided_metadata(tool_xml: "ElementTree") -> bool:
    if (outputs := tool_xml.find("./outputs")) is not None:
        if "provided_metadata_file" in outputs.attrib or "provided_metadata_style" in outputs.attrib:
            return True
    if (command := tool_xml.find("./command")) is not None:
        if "galaxy.json" in command.text:
            return True
    config = tool_xml.find("./configfiles/configfile[@filename='galaxy.json']")
    if config is not None:
        return True
    return False

import re
from typing import (
    NamedTuple,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from galaxy.util.etree import (
        Element,
        ElementTree,
    )


def is_datasource(tool_xml):
    """Returns true if the tool is a datasource tool"""
    return tool_xml.getroot().attrib.get("tool_type", "") in ["data_source", "data_source_async"]


def is_valid_cheetah_placeholder(name):
    """Returns true if name is a valid Cheetah placeholder"""
    return re.match(r"^[a-zA-Z_]\w*$", name) is not None


class InputReference(NamedTuple):
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


class InputReferences:
    """Input parameter paths as runtime keys them, with repeat indices normalized to ``_0``.

    ``qualified`` includes every conditional, section and repeat. ``legacy`` is the alias
    ``visit_input_values`` also records, which omits only the innermost conditional or
    section name.
    """

    def __init__(self, tool_xml: "ElementTree") -> None:
        self.references: list[InputReference] = []
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
                        InputReference(
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

    def qualified(self, reference: str) -> list[InputReference]:
        return [r for r in self.references if r.qualified == reference]

    def legacy(self, reference: str) -> list[InputReference]:
        return [r for r in self.references if r.legacy == reference]

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

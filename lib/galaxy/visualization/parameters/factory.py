"""Build typed parameter models from visualization plugin XML.

``input_models_for_visualization`` mirrors ``input_models_for_tool_source`` from
the tool parameter machinery, but produces the smaller, flat visualization model:
a ``settings`` list plus the single top-level ``tracks`` repeat.
"""

from typing import (
    Any,
)
from xml.etree.ElementTree import (
    Element,
    parse as parse_xml,
)

from .models import (
    BooleanParameterModel,
    ColorParameterModel,
    ConditionalParameterModel,
    DataColumnParameterModel,
    DataJsonParameterModel,
    DataParameterModel,
    DataTableParameterModel,
    FloatParameterModel,
    IntegerParameterModel,
    LabelValue,
    SelectParameterModel,
    TextParameterModel,
    VisualizationParameterBundleModel,
    VisualizationWhen,
)
from .source import (
    as_float,
    as_int,
    flag,
    input_elements,
    text,
    value_of,
    wrapped_children,
)


class VisualizationParameterParsingException(ValueError):
    """Raised when a visualization input declaration cannot be parsed."""


# Synonyms accepted for an input ``<type>``.
TYPE_ALIASES = {
    "string": "text",
}


def input_models_for_visualization(root: Element) -> VisualizationParameterBundleModel:
    """Parse a ``<visualization>`` element into a parameter bundle."""
    return VisualizationParameterBundleModel(
        settings=[_parse_input(elem) for elem in input_elements(root.find("settings"))],
        tracks=[_parse_input(elem) for elem in input_elements(root.find("tracks"))],
    )


def input_models_for_visualization_path(path: str) -> VisualizationParameterBundleModel:
    return input_models_for_visualization(parse_xml(path).getroot())


def _common_kwargs(elem: Element) -> dict[str, Any]:
    name = text(elem, "name")
    if not name:
        raise VisualizationParameterParsingException("Visualization input requires a <name>.")
    return {
        "name": name,
        "label": text(elem, "label"),
        "help": text(elem, "help"),
        "optional": flag(elem, "optional"),
    }


def _parse_options(elem: Element) -> list[LabelValue]:
    options = []
    for option in wrapped_children(elem, "data"):
        options.append(LabelValue(label=text(option, "label") or "", value=text(option, "value") or ""))
    return options


def _parse_input(elem: Element) -> Any:
    input_type = text(elem, "type") or "text"
    input_type = TYPE_ALIASES.get(input_type, input_type)
    common = _common_kwargs(elem)
    if input_type == "boolean":
        return BooleanParameterModel(**common, value=_optional_bool(elem))
    if input_type == "color":
        return ColorParameterModel(**common, value=value_of(elem))
    if input_type == "integer":
        return IntegerParameterModel(
            **common, value=as_int(elem, "value"), min=as_int(elem, "min"), max=as_int(elem, "max")
        )
    if input_type == "float":
        return FloatParameterModel(
            **common, value=as_float(elem, "value"), min=as_float(elem, "min"), max=as_float(elem, "max")
        )
    if input_type == "text":
        return TextParameterModel(**common, value=value_of(elem))
    if input_type == "textarea":
        return TextParameterModel(**common, value=value_of(elem), area=True)
    if input_type == "select":
        return SelectParameterModel(
            **common, value=value_of(elem), options=_parse_options(elem), multiple=flag(elem, "multiple")
        )
    if input_type == "data":
        return DataParameterModel(**common, extension=text(elem, "extension"))
    if input_type == "data_column":
        return DataColumnParameterModel(**common, is_number=flag(elem, "is_number"))
    if input_type == "data_json":
        return DataJsonParameterModel(**common, url=text(elem, "url"))
    if input_type == "data_table":
        tables = [t.text.strip() for t in wrapped_children(elem, "tables") if t.text]
        return DataTableParameterModel(**common, tables=tables)
    if input_type == "conditional":
        return _parse_conditional(elem, common)
    raise VisualizationParameterParsingException(f"Unknown visualization input type '{input_type}'.")


def _optional_bool(elem: Element):
    value = text(elem, "value")
    return None if value is None else value.strip().lower() in ("true", "yes", "on", "1")


def _parse_conditional(elem: Element, common: dict[str, Any]) -> ConditionalParameterModel:
    test_elem = elem.find("test_param")
    if test_elem is None:
        raise VisualizationParameterParsingException(f"Conditional input '{common['name']}' requires a <test_param>.")
    test_type = text(test_elem, "type") or "select"
    test_common = {
        "name": text(test_elem, "name") or common["name"],
        "label": text(test_elem, "label"),
        "help": text(test_elem, "help"),
    }
    if test_type == "boolean":
        test_parameter: Any = BooleanParameterModel(**test_common, value=_optional_bool(test_elem))
    elif test_type == "select":
        test_parameter = SelectParameterModel(
            **test_common, value=value_of(test_elem), options=_parse_options(test_elem)
        )
    else:
        raise VisualizationParameterParsingException(
            f"Conditional test_param '{test_common['name']}' must be boolean or select, not '{test_type}'."
        )

    whens = []
    for case in wrapped_children(elem, "cases"):
        case_value = text(case, "value")
        inputs = []
        for input_elem in wrapped_children(case, "inputs"):
            parameter = _parse_input(input_elem)
            if isinstance(parameter, ConditionalParameterModel):
                raise VisualizationParameterParsingException(
                    f"Visualization conditionals are flat: '{parameter.name}' may not be nested inside "
                    f"a case of '{common['name']}'."
                )
            inputs.append(parameter)
        whens.append(VisualizationWhen(value=_coerce_case_value(case_value, test_type), inputs=inputs))
    return ConditionalParameterModel(**common, test_parameter=test_parameter, whens=whens)


def _coerce_case_value(value, test_type: str):
    if test_type == "boolean" and value is not None:
        return value.strip().lower() in ("true", "yes", "on", "1")
    return value

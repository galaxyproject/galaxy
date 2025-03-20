#!/usr/bin/env python

# how to use this function...
# PYTHONPATH=lib python lib/galaxy/tool_util/verify/codegen.py

import argparse
import inspect
import os
from shutil import move
from typing import (
    cast,
    List,
    Optional,
    Union,
)

import lxml.etree as ET
from jinja2 import Environment
from typing_extensions import (
    Annotated,
    get_args,
    get_origin,
    Literal,
)

from galaxy.tool_util.verify.asserts import assertion_module_and_functions
from galaxy.tool_util.verify.asserts._types import AssertionParameter as AssertionParameterAnnotation
from galaxy.util.commands import shell

models_path = os.path.join(os.path.dirname(__file__), "assertion_models.py")
galaxy_xsd_path = os.path.join(os.path.dirname(__file__), "..", "xsd", "galaxy.xsd")

Children = Literal["allowed", "required", "forbidden"]

DESCRIPTION = """This script synchronizes dynamic code artifacts against models in Galaxy.

Right now this just synchronizes Galaxy's XSD file against documentation in Galaxy's assertion modules but
in the future it will also build Pydantic models for these functions.
"""

assert_models_template = """
'''This module is auto-generated, please do not modify.'''
import typing
import re

from typing_extensions import (
    Annotated,
    Literal,
)

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
    RootModel,
    StrictFloat,
    StrictInt,
)

BYTES_PATTERN = re.compile(r"^(0|[1-9][0-9]*)([kKMGTPE]i?)?$")


class AssertionModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )


def check_bytes(v: typing.Any) -> typing.Any:
    if isinstance(v, str):
        assert BYTES_PATTERN.match(v), "Not valid bytes string"
    return v


def check_center_of_mass(v: typing.Any):
    assert isinstance(v, str)
    split_parts = v.split(",")
    assert len(split_parts) == 2
    for part in split_parts:
        assert float(part.strip())
    return v


def check_regex(v: typing.Any):
    assert isinstance(v, str)
    try:
        re.compile(typing.cast(str, v))
    except re.error:
        raise AssertionError(f"Invalid regular expression {v}")
    return v


def check_non_negative_if_set(v: typing.Any):
    if v is not None:
        try:
            assert float(v) >= 0
        except TypeError:
            raise AssertionError(f"Invalid type found {v}")
    return v


def check_non_negative_if_int(v: typing.Any):
    if v is not None and isinstance(v, int):
        assert typing.cast(int, v) >= 0
    return v


{% for assertion in assertions %}
{% for parameter in assertion.parameters %}
{{assertion.name}}_{{ parameter.name }}_description = '''{{ parameter.description }}'''
{% endfor %}

class base_{{assertion.name}}_model(AssertionModel):
    '''base model for {{assertion.name}} describing attributes.'''
{% for parameter in assertion.parameters %}
{% if not parameter.is_deprecated %}
    {{ parameter.name }}: {{ parameter.type_str }} = Field(
        {{ parameter.field_default_str }},
        description={{ assertion.name }}_{{ parameter.name }}_description,
    )
{% endif %}
{% endfor %}
{% if assertion.children in ["required", "allowed"] %}
    children: typing.Optional["assertion_list"] = None
    asserts: typing.Optional["assertion_list"] = None

{% if assertion.children == "required" %}
    @model_validator(mode='before')
    @classmethod
    def validate_children(self, data: typing.Any):
        if isinstance(data, dict) and 'children' not in data and 'asserts' not in data:
            raise ValueError("At least one of 'children' or 'asserts' must be specified for this assertion type.")
        return data
{% endif %}
{% endif %}


class base_{{assertion.name}}_model_relaxed(AssertionModel):
    '''base model for {{assertion.name}} describing attributes.'''
{% for parameter in assertion.parameters %}
{% if not parameter.is_deprecated %}
    {{ parameter.name }}: {{ parameter.lax_type_str }} = Field(
        {{ parameter.field_default_str }},
        description={{ assertion.name }}_{{ parameter.name }}_description,
    )
{% endif %}
{% endfor %}
{% if assertion.children in ["required", "allowed"] %}
    children: typing.Optional["assertion_list"] = None
    asserts: typing.Optional["assertion_list"] = None

{% if assertion.children == "required" %}
    @model_validator(mode='before')
    @classmethod
    def validate_children(self, data: typing.Any):
        if isinstance(data, dict) and 'children' not in data and 'asserts' not in data:
            raise ValueError("At least one of 'children' or 'asserts' must be specified for this assertion type.")
        return data
{% endif %}
{% endif %}


class {{assertion.name}}_model(base_{{assertion.name}}_model):
    r\"\"\"{{ assertion.docstring }}\"\"\"
    that: Literal["{{assertion.name}}"] = "{{assertion.name}}"

class {{assertion.name}}_model_nested(AssertionModel):
    r\"\"\"Nested version of this assertion model.\"\"\"
    {{assertion.name}}: base_{{assertion.name}}_model

class {{assertion.name}}_model_relaxed(base_{{assertion.name}}_model_relaxed):
    r\"\"\"{{ assertion.docstring }}\"\"\"
    that: Literal["{{assertion.name}}"] = "{{assertion.name}}"
{% endfor %}

any_assertion_model_flat = Annotated[typing.Union[
{% for assertion in assertions %}
    {{assertion.name}}_model,
{% endfor %}
], Field(discriminator="that")]

any_assertion_model_nested = typing.Union[
{% for assertion in assertions %}
    {{assertion.name}}_model_nested,
{% endfor %}
]

any_assertion_model_flat_relaxed = Annotated[typing.Union[
{% for assertion in assertions %}
    {{assertion.name}}_model_relaxed,
{% endfor %}
], Field(discriminator="that")]

assertion_list = RootModel[typing.List[typing.Union[any_assertion_model_flat, any_assertion_model_nested]]]

# used to model what the XML conversion should look like - not meant to be consumed outside of
# of Galaxy internals / linting.
relaxed_assertion_list = RootModel[typing.List[any_assertion_model_flat_relaxed]]

class assertion_dict(AssertionModel):
{% for assertion in assertions %}
    {{assertion.name}}: typing.Optional[base_{{assertion.name}}_model] = None
{% endfor %}


assertions = typing.Union[assertion_list, assertion_dict]
"""


def get_default_args(func):
    signature = inspect.signature(func)
    return {k: v.default for k, v in signature.parameters.items()}


def main():
    assertions = []
    for function_name, (module_and_function, assertion_function) in assertion_module_and_functions.items():
        if not function_name.startswith("assert_"):
            continue
        name = function_name[len("assert_") :]
        docstring = inspect.cleandoc(assertion_function.__doc__ or "")
        annotations = assertion_function.__annotations__
        default_args = get_default_args(assertion_function)
        parameters = []
        children: Children = "forbidden"
        for parameter_name, parameter_type in annotations.items():
            if parameter_name == "return":
                continue
            elif parameter_name == "children":
                if default_args.get("children", inspect._empty) is not inspect._empty:
                    children = "allowed"
                else:
                    children = "required"
                continue
            elif parameter_name in ["output", "output_bytes", "verify_assertions_function"]:
                continue

            default_value = default_args.get(parameter_name)
            parameters.append(AssertionParameter(parameter_name, parameter_type, default_value))
        assertion = Assertion(name, docstring, parameters, children, module_and_function)
        assertions.append(assertion)
    rewrite_galaxy_xsd(assertions)
    write_assertion_models(assertions)


def _expand_template(template_str: str, assertions) -> str:
    template = Environment().from_string(template_str)
    return template.render(assertions=assertions)


def write_assertion_models(assertions):
    models_file_contents = _expand_template(assert_models_template, assertions)
    with open(models_path, "w") as f:
        f.write(models_file_contents)
    shell(["isort", models_path])
    shell(["black", models_path])


def get_annotation(text: str, nsmap):
    annotation = ET.Element("{http://www.w3.org/2001/XMLSchema}annotation")
    documentation = ET.Element("{http://www.w3.org/2001/XMLSchema}documentation")
    documentation.text = ET.CDATA(text)
    documentation.attrib["{http://www.w3.org/XML/1998/namespace}lang"] = "en"
    annotation.append(documentation)
    return annotation


def parameter_xsd_element(assertion_parameter, nsmap):
    el = ET.Element("{http://www.w3.org/2001/XMLSchema}attribute", nsmap=nsmap)
    el.attrib["name"] = assertion_parameter.name
    el.attrib["type"] = assertion_parameter.xml_type_str
    el.attrib["use"] = "required" if not assertion_parameter.has_default_value else "optional"
    annotation = get_annotation(assertion_parameter.description, nsmap)
    el.append(annotation)
    return el


def xsd_element(assertion, nsmap):
    el = ET.Element("{http://www.w3.org/2001/XMLSchema}element", nsmap=nsmap)
    el.attrib["name"] = assertion.name
    annotation = get_annotation(assertion.docstring + "\n\n$attribute_list::5", nsmap)
    complexType = ET.Element("{http://www.w3.org/2001/XMLSchema}complexType", nsmap=nsmap)
    if assertion.children != "forbidden":
        sequence = ET.Element("{http://www.w3.org/2001/XMLSchema}sequence", nsmap=nsmap)
        group = ET.Element("{http://www.w3.org/2001/XMLSchema}group", nsmap=nsmap)
        group.attrib["ref"] = "TestAssertion"
        group.attrib["minOccurs"] = "0" if assertion.children == "allowed" else "1"
        group.attrib["maxOccurs"] = "unbounded"
        sequence.append(group)
        complexType.append(sequence)
    for parameter in assertion.parameters:
        complexType.append(parameter_xsd_element(parameter, nsmap))
    el.append(annotation)
    el.append(complexType)
    return el


def xsd_elements(assertions, nsmap):
    elements = []
    for assertion in assertions:
        elements.append(ET.Comment(f" XSD doc for element auto-generated from {assertion.module_and_function}"))
        elements.append(xsd_element(assertion, nsmap))
    return elements


def rewrite_galaxy_xsd(assertions):
    with open(galaxy_xsd_path, "rb") as f:
        contents = f.read()
    parser = ET.XMLParser(strip_cdata=False)
    root = ET.fromstring(contents, parser=parser)
    raw_element = root.find(
        ".//{http://www.w3.org/2001/XMLSchema}group[@name='TestAssertion']/{http://www.w3.org/2001/XMLSchema}choice"
    )
    assert raw_element
    element = cast(ET._Element, raw_element)
    for el in element.iterchildren():
        element.remove(el)
    element.append(ET.Comment("The following block and all children are auto-generated - please do not modify."))
    for xsd_element in xsd_elements(assertions, root.nsmap):
        xsd_element.tail = "\n      "
        element.append(xsd_element)
    xml_new = ET.tostring(root).decode("utf-8")
    with open(galaxy_xsd_path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(xml_new)
        f.write("\n")
    ret_code = shell(["xmllint", "--format", "--output", "galaxy-tmp.xsd", galaxy_xsd_path])
    assert ret_code == 0
    move("galaxy-tmp.xsd", galaxy_xsd_path)


class AssertionParameter:

    def __init__(self, name: str, type: str, default_value):
        self.name = name
        self.type = type
        self.default_value = default_value

    @property
    def description(self) -> str:
        type = self.type
        if hasattr(type, "__metadata__"):
            return type.__metadata__[0].doc
        else:
            return ""

    @property
    def type_str(self) -> str:
        raw_type_str = as_type_str(self.type, strict=True)
        validators = self.validators[:]
        if self.xml_type_str == "Bytes":
            validators.append("check_bytes")
            validators.append("check_non_negative_if_int")
        if len(validators) > 0:
            validation_str = ",".join([f"BeforeValidator({v})" for v in validators])
            return f"Annotated[{raw_type_str}, {validation_str}]"

        return raw_type_str

    @property
    def lax_type_str(self) -> str:
        raw_type_str = as_type_str(self.type, strict=False)
        validators = self.validators[:]
        if self.xml_type_str == "Bytes":
            validators.append("check_bytes")
            validators.append("check_non_negative_if_int")
        if len(validators) > 0:
            validation_str = ",".join([f"BeforeValidator({v})" for v in validators])
            return f"Annotated[{raw_type_str}, {validation_str}]"

        return raw_type_str

    @property
    def xml_type_str(self) -> str:
        return as_xml_type(self.type)

    @property
    def field_default_str(self) -> str:
        if not self.has_default_value:
            return "..."
        elif isinstance(self.default_value, str):
            return f'''"{self.default_value}"'''
        else:
            return str(self.default_value)

    @property
    def has_default_value(self) -> bool:
        return self.default_value is not inspect._empty

    @property
    def is_deprecated(self) -> bool:
        assertion_parameter = self._get_type_annotation()
        if assertion_parameter is not None:
            return assertion_parameter.deprecated

        return False

    @property
    def validators(self) -> List[str]:
        assertion_parameter = self._get_type_annotation()
        if assertion_parameter is not None:
            return assertion_parameter.validators

        return []

    def _get_type_annotation(self) -> Optional[AssertionParameterAnnotation]:
        target_type = self.type
        if get_origin(target_type) is Annotated:
            args = get_args(target_type)
            if len(args) > 1:
                return cast(AssertionParameterAnnotation, args[1])

        return None


def _is_none_type(target_type):
    return target_type is type(None)


def _non_optional_types(union_type):
    return [t for t in get_args(union_type) if not _is_none_type(t)]


def as_xml_type(target_type) -> str:
    if get_origin(target_type) is Annotated:
        args = get_args(target_type)
        if len(args) > 1:
            assertion_parameter = args[1]
            if assertion_parameter.xml_type:
                return assertion_parameter.xml_type

        return as_xml_type(args[0])
    elif get_origin(target_type) is Union:
        types = _non_optional_types(target_type)
        if len(types) == 2:
            non_str_types = [t for t in types if t is not str]
            if len(non_str_types) == 1 and non_str_types[0] is bool:
                return "xs:boolean"
            elif len(non_str_types) == 1 and non_str_types[0] is int:
                return "xs:integer"
            elif len(non_str_types) == 1 and non_str_types[0] is float:
                return "xs:float"

    return "xs:string"


def as_type_str(target_type, strict=True):
    if get_origin(target_type) is Annotated:
        args = get_args(target_type)
        if len(args) > 1:
            if args[1].json_type and strict:
                return args[1].json_type

        return as_type_str(args[0])
    elif get_origin(target_type) is Union:
        is_optional = any(_is_none_type(t) for t in get_args(target_type))
        types_as_str = ", ".join(map(as_type_str, _non_optional_types(target_type)))
        union_type = f"typing.Union[{types_as_str}]"
        if is_optional:
            return f"typing.Optional[{union_type}]"
        else:
            return union_type
    elif target_type is str:
        return "str"
    elif target_type is int:
        return "int"
    elif target_type is float:
        return "float"
    elif target_type is bool:
        return "bool"
    else:
        return str(target_type)


class Assertion:

    def __init__(
        self,
        name: str,
        docstring: str,
        parameters: List[AssertionParameter],
        children: Children,
        module_and_function: str,
    ):
        self.name = name
        self.parameters = parameters
        self.docstring = docstring
        self.children = children
        self.module_and_function = module_and_function


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    return parser


if __name__ == "__main__":
    main()

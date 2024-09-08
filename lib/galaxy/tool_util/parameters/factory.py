from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Union,
)

from galaxy.tool_util.parser.cwl import CwlInputSource
from galaxy.tool_util.parser.interface import (
    InputSource,
    PageSource,
    PagesSource,
    ToolSource,
)
from galaxy.util import string_as_bool
from .models import (
    BaseUrlParameterModel,
    BooleanParameterModel,
    ColorParameterModel,
    cond_test_parameter_default_value,
    ConditionalParameterModel,
    ConditionalWhen,
    CwlBooleanParameterModel,
    CwlDirectoryParameterModel,
    CwlFileParameterModel,
    CwlFloatParameterModel,
    CwlIntegerParameterModel,
    CwlNullParameterModel,
    CwlStringParameterModel,
    CwlUnionParameterModel,
    DataCollectionParameterModel,
    DataColumnParameterModel,
    DataParameterModel,
    DirectoryUriParameterModel,
    DrillDownParameterModel,
    FloatParameterModel,
    GenomeBuildParameterModel,
    GroupTagParameterModel,
    HiddenParameterModel,
    IntegerParameterModel,
    LabelValue,
    RepeatParameterModel,
    RulesParameterModel,
    SectionParameterModel,
    SelectParameterModel,
    TextParameterModel,
    ToolParameterBundle,
    ToolParameterBundleModel,
    ToolParameterT,
)


class ParameterDefinitionError(Exception):
    pass


class UnknownParameterTypeError(ParameterDefinitionError):
    pass


def get_color_value(input_source: InputSource) -> str:
    return input_source.get("value", "#000000")


def _from_input_source_galaxy(input_source: InputSource) -> ToolParameterT:
    input_type = input_source.parse_input_type()
    if input_type == "param":
        param_type = input_source.get("type")
        if param_type == "integer":
            optional = input_source.parse_optional()
            value = input_source.get("value")
            int_value: Optional[int]
            if value:
                int_value = int(value)
            elif optional:
                int_value = None
            elif value == "" or value is None:
                # A truly required parameter: https://github.com/galaxyproject/galaxy/pull/16966/files
                int_value = None
            else:
                raise ParameterDefinitionError()
            return IntegerParameterModel(name=input_source.parse_name(), optional=optional, value=int_value)
        elif param_type == "boolean":
            nullable = input_source.parse_optional()
            checked = input_source.get_bool("checked", None if nullable else False)
            return BooleanParameterModel(
                name=input_source.parse_name(),
                optional=nullable,
                value=checked,
            )
        elif param_type == "text":
            optional = input_source.parse_optional()
            return TextParameterModel(
                name=input_source.parse_name(),
                optional=optional,
            )
        elif param_type == "float":
            optional = input_source.parse_optional()
            value = input_source.get("value")
            float_value: Optional[float]
            if value:
                float_value = float(value)
            elif optional:
                float_value = None
            else:
                raise ParameterDefinitionError()
            return FloatParameterModel(
                name=input_source.parse_name(),
                optional=optional,
                value=float_value,
            )
        elif param_type == "hidden":
            optional = input_source.parse_optional()
            value = input_source.get("value")
            return HiddenParameterModel(
                name=input_source.parse_name(),
                optional=optional,
                value=value,
            )
        elif param_type == "color":
            optional = input_source.parse_optional()
            return ColorParameterModel(
                name=input_source.parse_name(),
                optional=optional,
                value=get_color_value(input_source),
            )
        elif param_type == "rules":
            return RulesParameterModel(
                name=input_source.parse_name(),
            )
        elif param_type == "data":
            optional = input_source.parse_optional()
            multiple = input_source.get_bool("multiple", False)
            return DataParameterModel(
                name=input_source.parse_name(),
                optional=optional,
                multiple=multiple,
            )
        elif param_type == "data_collection":
            optional = input_source.parse_optional()
            default_value = input_source.parse_default()
            return DataCollectionParameterModel(
                name=input_source.parse_name(),
                optional=optional,
                value=default_value,
            )
        elif param_type == "select":
            # Function... example in devteam cummeRbund.
            optional = input_source.parse_optional()
            dynamic_options_config = input_source.parse_dynamic_options()
            is_static = dynamic_options_config is None
            multiple = input_source.get_bool("multiple", False)
            options: Optional[List[LabelValue]] = None
            if is_static:
                options = []
                for option_label, option_value, selected in input_source.parse_static_options():
                    options.append(LabelValue(label=option_label, value=option_value, selected=selected))
            return SelectParameterModel(
                name=input_source.parse_name(),
                optional=optional,
                options=options,
                multiple=multiple,
            )
        elif param_type == "drill_down":
            multiple = input_source.get_bool("multiple", False)
            hierarchy = input_source.get("hierarchy", "exact")
            dynamic_options = input_source.parse_drill_down_dynamic_options()
            static_options = None
            if dynamic_options is None:
                static_options = input_source.parse_drill_down_static_options()
            return DrillDownParameterModel(
                name=input_source.parse_name(),
                multiple=multiple,
                hierarchy=hierarchy,
                options=static_options,
            )
        elif param_type == "data_column":
            multiple = input_source.get_bool("multiple", False)
            optional = input_source.parse_optional()
            return DataColumnParameterModel(
                name=input_source.parse_name(),
                multiple=multiple,
                optional=optional,
            )
        elif param_type == "group_tag":
            multiple = input_source.get_bool("multiple", False)
            optional = input_source.parse_optional()
            return GroupTagParameterModel(
                name=input_source.parse_name(),
                optional=optional,
                multiple=multiple,
            )
        elif param_type == "baseurl":
            return BaseUrlParameterModel(
                name=input_source.parse_name(),
            )
        elif param_type == "genomebuild":
            optional = input_source.parse_optional()
            multiple = input_source.get_bool("multiple", False)
            return GenomeBuildParameterModel(
                name=input_source.parse_name(),
                optional=optional,
                multiple=multiple,
            )
        elif param_type == "directory_uri":
            return DirectoryUriParameterModel(
                name=input_source.parse_name(),
            )
        else:
            raise UnknownParameterTypeError(f"Unknown Galaxy parameter type {param_type}")
    elif input_type == "conditional":
        test_param_input_source = input_source.parse_test_input_source()
        test_parameter = cast(
            Union[BooleanParameterModel, SelectParameterModel], _from_input_source_galaxy(test_param_input_source)
        )
        whens = []
        default_test_value = cond_test_parameter_default_value(test_parameter)
        for value, case_inputs_sources in input_source.parse_when_input_sources():
            if isinstance(test_parameter, BooleanParameterModel):
                # TODO: investigate truevalue/falsevalue when...
                typed_value = string_as_bool(value)
            else:
                typed_value = value

            tool_parameter_models = input_models_for_page(case_inputs_sources)
            is_default_when = False
            if typed_value == default_test_value:
                is_default_when = True
            whens.append(
                ConditionalWhen(
                    discriminator=typed_value, parameters=tool_parameter_models, is_default_when=is_default_when
                )
            )
        return ConditionalParameterModel(
            name=input_source.parse_name(),
            test_parameter=test_parameter,
            whens=whens,
        )
    elif input_type == "repeat":
        name = input_source.get("name")
        # title = input_source.get("title")
        # help = input_source.get("help", None)
        instance_sources = input_source.parse_nested_inputs_source()
        instance_tool_parameter_models = input_models_for_page(instance_sources)
        min_raw = input_source.get("min", None)
        max_raw = input_source.get("max", None)
        min = int(min_raw) if min_raw is not None else None
        max = int(max_raw) if max_raw is not None else None
        return RepeatParameterModel(
            name=name,
            parameters=instance_tool_parameter_models,
            min=min,
            max=max,
        )
    elif input_type == "section":
        name = input_source.get("name")
        instance_sources = input_source.parse_nested_inputs_source()
        instance_tool_parameter_models = input_models_for_page(instance_sources)
        return SectionParameterModel(
            name=name,
            parameters=instance_tool_parameter_models,
        )
    else:
        raise Exception(
            f"Cannot generate tool parameter model for supplied tool source - unknown input_type {input_type}"
        )


def _simple_cwl_type_to_model(simple_type: str, input_source: CwlInputSource):
    if simple_type == "int":
        return CwlIntegerParameterModel(
            name=input_source.parse_name(),
        )
    elif simple_type == "float":
        return CwlFloatParameterModel(
            name=input_source.parse_name(),
        )
    elif simple_type == "null":
        return CwlNullParameterModel(
            name=input_source.parse_name(),
        )
    elif simple_type == "string":
        return CwlStringParameterModel(
            name=input_source.parse_name(),
        )
    elif simple_type == "boolean":
        return CwlBooleanParameterModel(
            name=input_source.parse_name(),
        )
    elif simple_type == "org.w3id.cwl.cwl.File":
        return CwlFileParameterModel(
            name=input_source.parse_name(),
        )
    elif simple_type == "org.w3id.cwl.cwl.Directory":
        return CwlDirectoryParameterModel(
            name=input_source.parse_name(),
        )
    raise NotImplementedError(
        f"Cannot generate tool parameter model for this CWL artifact yet - contains unknown type {simple_type}."
    )


def _from_input_source_cwl(input_source: CwlInputSource) -> ToolParameterT:
    schema_salad_field = input_source.field
    if schema_salad_field is None:
        raise NotImplementedError("Cannot generate tool parameter model for this CWL artifact yet.")
    if "type" not in schema_salad_field:
        raise NotImplementedError("Cannot generate tool parameter model for this CWL artifact yet.")
    schema_salad_type = schema_salad_field["type"]
    if isinstance(schema_salad_type, str):
        return _simple_cwl_type_to_model(schema_salad_type, input_source)
    elif isinstance(schema_salad_type, list):
        return CwlUnionParameterModel(
            name=input_source.parse_name(),
            parameters=[_simple_cwl_type_to_model(t, input_source) for t in schema_salad_type],
        )
    else:
        raise NotImplementedError("Cannot generate tool parameter model for this CWL artifact yet.")


def input_models_from_json(json: List[Dict[str, Any]]) -> ToolParameterBundle:
    return ToolParameterBundleModel(parameters=json)


def tool_parameter_bundle_from_json(json: Dict[str, Any]) -> ToolParameterBundleModel:
    return ToolParameterBundleModel(**json)


def input_models_for_tool_source(tool_source: ToolSource) -> ToolParameterBundleModel:
    pages = tool_source.parse_input_pages()
    return ToolParameterBundleModel(parameters=input_models_for_pages(pages))


def input_models_for_pages(pages: PagesSource) -> List[ToolParameterT]:
    input_models = []
    if pages.inputs_defined:
        for page_source in pages.page_sources:
            input_models.extend(input_models_for_page(page_source))

    return input_models


def input_models_for_page(page_source: PageSource) -> List[ToolParameterT]:
    input_models = []
    for input_source in page_source.parse_input_sources():
        input_type = input_source.parse_input_type()
        if input_type == "display":
            # not a real input... just skip this. Should this be handled in the parser layer better?
            continue
        tool_parameter_model = from_input_source(input_source)
        input_models.append(tool_parameter_model)
    return input_models


def from_input_source(input_source: InputSource) -> ToolParameterT:
    tool_parameter: ToolParameterT
    if isinstance(input_source, CwlInputSource):
        tool_parameter = _from_input_source_cwl(input_source)
    else:
        tool_parameter = _from_input_source_galaxy(input_source)
    return tool_parameter

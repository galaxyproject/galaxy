from typing import (
    Any,
    cast,
    Optional,
    Union,
)

from gxformat2.normalized import NormalizedNativeWorkflow

from galaxy.tool_util.parameters import (
    SelectParameterModel,
    ToolParameterT,
)
from galaxy.tool_util_models import ParsedTool
from ._types import (
    GetToolInfo,
    NativeWorkflowDict,
    ToolInputs,
)
from ._util import (
    StepLike,
    coerce_select_value,
    is_connected_or_runtime,
    is_replacement_param,
    step_input_connections,
    step_tool_id,
    step_tool_state,
    step_tool_version,
)
from ._walker import (
    SKIP_VALUE,
    walk_native_state,
)


def validate_native_step_against(step: StepLike, parsed_tool: ToolInputs):
    tool_state = step_tool_state(step)
    input_connections = step_input_connections(step)

    def merge_and_validate(tool_input: ToolParameterT, value: Any, state_path: str):
        parameter_type = tool_input.parameter_type

        # Merge: inject ConnectedValue for connected params
        if state_path in input_connections and not isinstance(value, dict):
            value = {"__class__": "ConnectedValue"}

        # ConnectedValue/RuntimeValue: valid for any parameter type
        if is_connected_or_runtime(value):
            return SKIP_VALUE

        if parameter_type in [
            "gx_text",
            "gx_color",
            "gx_hidden",
            "gx_genomebuild",
            "gx_group_tag",
            "gx_baseurl",
            "gx_directory_uri",
        ]:
            pass
        elif parameter_type == "gx_integer":
            if value is not None and value != "null" and not is_replacement_param(value):
                try:
                    int(value)
                except (ValueError, TypeError):
                    raise Exception(f"Invalid integer data found {value}")
        elif parameter_type == "gx_float":
            if value is not None and value != "null" and not is_replacement_param(value):
                try:
                    float(value)
                except (ValueError, TypeError):
                    raise Exception(f"Invalid float data found {value}")
        elif parameter_type == "gx_boolean":
            pass
        elif parameter_type in ["gx_data", "gx_data_collection"]:
            if isinstance(value, dict):
                assert "__class__" in value
                assert value["__class__"] in ["RuntimeValue", "ConnectedValue"]
            else:
                assert value in [None, "null"]
        elif parameter_type == "gx_select":
            if value is not None and value != "null":
                select = cast(SelectParameterModel, tool_input)
                options = select.options
                if options is not None:
                    valid_values = [o.value for o in options]
                    if select.multiple and isinstance(value, list):
                        invalid = [v for v in value if coerce_select_value(v) not in valid_values]
                        if invalid:
                            raise Exception(f"Invalid select option(s) found {invalid}")
                    else:
                        if coerce_select_value(value) not in valid_values:
                            raise Exception(f"Invalid select option found {value}")
        elif parameter_type in ["gx_data_column", "gx_drill_down"]:
            pass
        elif parameter_type == "gx_rules":
            pass
        else:
            raise NotImplementedError(f"Unhandled parameter type ({parameter_type})")

        return SKIP_VALUE

    walk_native_state(
        input_connections,
        parsed_tool.inputs,
        tool_state,
        merge_and_validate,
        check_unknown_keys=True,
        allow_root_level_duplicates=True,
    )


# -- Public utilities --


def validate_step_native(step: StepLike, get_tool_info: GetToolInfo):
    parsed_tool = get_parsed_tool_for_native_step(step, get_tool_info)
    if parsed_tool is not None:
        validate_native_step_against(step, parsed_tool)


def get_parsed_tool_for_native_step(step: StepLike, get_tool_info: GetToolInfo) -> Optional[ParsedTool]:
    tool_id = step_tool_id(step)
    if not tool_id:
        return None
    tool_version = step_tool_version(step)
    return get_tool_info.get_tool_info(tool_id, tool_version)


def validate_workflow_native(
    workflow: "Union[NormalizedNativeWorkflow, NativeWorkflowDict]", get_tool_info: GetToolInfo
):
    if isinstance(workflow, NormalizedNativeWorkflow):
        for step in workflow.steps.values():
            if step.is_subworkflow_step and step.subworkflow:
                validate_workflow_native(step.subworkflow, get_tool_info)
            else:
                validate_step_native(step, get_tool_info)
    else:
        for step_def in workflow["steps"].values():
            if step_def.get("type") == "subworkflow" and "subworkflow" in step_def:
                validate_workflow_native(step_def["subworkflow"], get_tool_info)
            else:
                validate_step_native(step_def, get_tool_info)


def native_tool_state(step: StepLike) -> dict:
    return step_tool_state(step)


def native_connections_for(step: StepLike, parameter: ToolParameterT, prefix: Optional[str]):
    parameter_name = parameter.name
    state_path = parameter_name if prefix is None else f"{prefix}|{parameter_name}"
    connections = step_input_connections(step)
    return connections.get(state_path)

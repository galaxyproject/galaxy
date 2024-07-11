from galaxy.tool_util.workflow_state.convert import (
    convert_state_to_format2,
    Format2InputsDictT,
)
from galaxy.workflow.gx_validator import GET_TOOL_INFO
from .test_workflow_validation import base_package_workflow_as_dict


def convert_state(native_step_dict: dict) -> Format2InputsDictT:
    return convert_state_to_format2(native_step_dict, GET_TOOL_INFO)


def test_simple_convert():
    workflow_dict = base_package_workflow_as_dict("test_workflow_1.ga")
    cat_step = workflow_dict["steps"]["2"]
    format2_pair = convert_state(cat_step)

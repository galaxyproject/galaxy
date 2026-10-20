"""Tests for :func:`galaxy.tools.parameters.visit_input_values`."""

from typing import (
    Any,
    cast,
)

from galaxy.tools.parameters import (
    params_to_strings,
    ToolInputsT,
    visit_input_values,
)
from galaxy.tools.parameters.basic import (
    DataToolParameter,
    SelectToolParameter,
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    ConditionalWhen,
)
from galaxy.tools.parameters.workflow_utils import ConnectedValue
from galaxy.util import XML
from galaxy.util.bunch import Bunch


def _job_resource_conditional() -> Conditional:
    """Mirror the ``__job_resource`` conditional the job configuration injects into tools."""
    conditional = Conditional("__job_resource")
    conditional.test_param = SelectToolParameter(
        None,
        XML("""
            <param name="__job_resource__select" type="select" label="Job Resource Parameters">
                <option value="no">Use default job resource parameters</option>
                <option value="yes">Specify job resource parameters</option>
            </param>
            """),
    )
    conditional.cases = [
        cast(ConditionalWhen, Bunch(value="no", inputs={})),
        cast(ConditionalWhen, Bunch(value="yes", inputs={})),
    ]
    return conditional


def _inputs_with_job_resource() -> ToolInputsT:
    return cast(
        ToolInputsT,
        {
            "input1": DataToolParameter(None, XML('<param name="input1" type="data"/>'), trans=None),
            "__job_resource": _job_resource_conditional(),
        },
    )


def _connect_input1(input, prefixed_name, **kwargs):
    if prefixed_name == "input1":
        return ConnectedValue()


def test_missing_conditional_gets_default_case():
    # A workflow imported without fill_defaults carries no state for conditionals the tool
    # gained after the workflow was saved, such as the injected __job_resource group.
    inputs = _inputs_with_job_resource()
    state: dict[str, Any] = {"input1": None}

    visit_input_values(inputs, state, _connect_input1)

    assert isinstance(state["input1"], ConnectedValue)
    assert state["__job_resource"] == {"__job_resource__select": "no", "__current_case__": 0}
    # Saving the step state afterwards must not raise (issue #24267).
    encoded = params_to_strings(inputs, state, None, nested=True)
    assert encoded["__job_resource"] == {"__job_resource__select": "no", "__current_case__": 0}


def test_present_conditional_selector_is_kept():
    inputs = _inputs_with_job_resource()
    state: dict[str, Any] = {"input1": None, "__job_resource": {"__job_resource__select": "yes"}}

    visit_input_values(inputs, state, _connect_input1)

    assert state["__job_resource"] == {"__job_resource__select": "yes", "__current_case__": 1}


def test_missing_conditional_with_dynamic_selector_is_not_seeded():
    # Without a transaction a dynamic select has no initial value, as for the upload
    # tool's files_metadata conditional when tool parameters are reordered (meta.py).
    conditional = Conditional("files_metadata")
    conditional.test_param = SelectToolParameter(
        None,
        XML("""<param name="file_type" type="select" dynamic_options="get_file_types()"/>"""),
    )
    conditional.cases = [cast(ConditionalWhen, Bunch(value="auto", inputs={}))]
    inputs = cast(ToolInputsT, {"files_metadata": conditional})
    state: dict[str, Any] = {}

    visit_input_values(inputs, state, lambda input, value, prefixed_name, **kwargs: None)

    assert state["files_metadata"] == {"__current_case__": -1}

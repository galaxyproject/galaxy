"""
Modules used in building workflows
"""

import json
import logging
import math
import re
from collections import defaultdict
from typing import (
    Any,
    cast,
    Dict,
    get_args,
    Iterable,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)

from typing_extensions import TypedDict

from galaxy import (
    exceptions,
    model,
)
from galaxy.exceptions import (
    ToolInputsNotReadyException,
    ToolMissingException,
)
from galaxy.job_execution.actions.post import ActionBox
from galaxy.model import (
    Job,
    PostJobAction,
    Workflow,
    WorkflowInvocationStep,
    WorkflowStep,
    WorkflowStepConnection,
)
from galaxy.model.base import ensure_object_added_to_session
from galaxy.model.dataset_collections import matching
from galaxy.schema.invocation import (
    CancelReason,
    FailureReason,
    InvocationCancellationReviewFailed,
    InvocationFailureDatasetFailed,
    InvocationFailureExpressionEvaluationFailed,
    InvocationFailureOutputNotFound,
    InvocationFailureWhenNotBoolean,
    InvocationFailureWorkflowParameterInvalid,
)
from galaxy.tool_util.cwl.util import set_basename_and_derived_properties
from galaxy.tool_util.parser import get_input_source
from galaxy.tool_util.parser.output_objects import ToolExpressionOutput
from galaxy.tools import (
    DatabaseOperationTool,
    DefaultToolState,
    get_safe_version,
)
from galaxy.tools.execute import (
    execute,
    MappingParameters,
    PartialJobExecution,
)
from galaxy.tools.execution_helpers import filter_output
from galaxy.tools.expressions import do_eval
from galaxy.tools.parameters import (
    check_param,
    params_to_incoming,
    visit_input_values,
)
from galaxy.tools.parameters.basic import (
    BaseDataToolParameter,
    BooleanToolParameter,
    DataCollectionToolParameter,
    DataToolParameter,
    FloatToolParameter,
    HiddenToolParameter,
    IntegerToolParameter,
    parameter_types,
    raw_to_galaxy,
    SelectToolParameter,
    TextToolParameter,
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    ConditionalWhen,
    Repeat,
)
from galaxy.tools.parameters.history_query import HistoryQuery
from galaxy.tools.parameters.options import ParameterOption
from galaxy.tools.parameters.populate_model import populate_model
from galaxy.tools.parameters.workflow_utils import (
    ConnectedValue,
    is_runtime_value,
    NO_REPLACEMENT,
    NoReplacement,
    runtime_to_json,
    workflow_building_modes,
)
from galaxy.tools.parameters.wrapped import make_dict_copy
from galaxy.util import (
    listify,
    unicodify,
)
from galaxy.util.bunch import Bunch
from galaxy.util.json import safe_loads
from galaxy.util.rules_dsl import RuleSet
from galaxy.util.template import fill_template
from galaxy.util.tool_shed.common_util import get_tool_shed_url_from_tool_shed_registry
from galaxy.workflow.workflow_parameter_input_definitions import get_default_parameter

if TYPE_CHECKING:
    from galaxy.schema.invocation import InvocationMessageUnion
    from galaxy.workflow.run import WorkflowProgress


log = logging.getLogger(__name__)

# Key into Tool state to describe invocation-specific runtime properties.
RUNTIME_STEP_META_STATE_KEY = "__STEP_META_STATE__"
# Key into step runtime state dict describing invocation-specific post job
# actions (i.e. PJA specified at runtime on top of the workflow-wide defined
# ones.
RUNTIME_POST_JOB_ACTIONS_KEY = "__POST_JOB_ACTIONS__"

INPUT_PARAMETER_TYPES = Literal["text", "integer", "float", "boolean", "color", "directory_uri"]
POSSIBLE_PARAMETER_TYPES: Tuple[INPUT_PARAMETER_TYPES] = get_args(INPUT_PARAMETER_TYPES)


class OptionDict(TypedDict):
    label: str
    value: str
    selected: bool


class ConditionalStepWhen(BooleanToolParameter):
    pass


def to_cwl(value, hda_references, step):
    element_identifier = None
    if isinstance(value, model.HistoryDatasetCollectionAssociation):
        value = value.collection
    if isinstance(value, model.DatasetCollectionElement):
        element_identifier = value.element_identifier
        value = value.element_object
    if isinstance(value, model.HistoryDatasetAssociation):
        # I think the following two checks are needed but they may
        # not be needed.
        if not value.dataset.in_ready_state():
            why = f"dataset [{value.id}] is needed for valueFrom expression and is non-ready"
            raise DelayedWorkflowEvaluation(why=why)
        if not value.is_ok:
            raise FailWorkflowEvaluation(
                why=InvocationFailureDatasetFailed(
                    reason=FailureReason.dataset_failed, hda_id=value.id, workflow_step_id=step.id
                )
            )
        if value.ext == "expression.json":
            with open(value.get_file_name()) as f:
                # OUR safe_loads won't work, will not load numbers, etc...
                return json.load(f)
        else:
            hda_references.append(value)
            properties = {
                "class": "File",
                "location": "step_input://%d" % len(hda_references),
                "format": value.extension,
            }
            set_basename_and_derived_properties(
                properties, value.dataset.created_from_basename or element_identifier or value.name
            )
            return properties
    elif isinstance(value, model.DatasetCollection):
        if value.collection_type == "list":
            return [to_cwl(dce, hda_references=hda_references, step=step) for dce in value.dataset_elements]
        else:
            # Could be record or nested lists
            rval = {}
            for element in value.elements:
                rval[element.element_identifier] = to_cwl(
                    element.element_object, hda_references=hda_references, step=step
                )
            return rval
    elif isinstance(value, list):
        return [to_cwl(v, hda_references=hda_references, step=step) for v in value]
    elif is_runtime_value(value):
        return None
    elif isinstance(value, dict):
        # Nested tool state, such as conditionals
        return {k: to_cwl(v, hda_references=hda_references, step=step) for k, v in value.items()}
    else:
        return value


def from_cwl(value, hda_references, progress: "WorkflowProgress"):
    # TODO: turn actual files into HDAs here ... somehow I suppose. Things with
    # file:// locations for instance.
    if isinstance(value, dict) and "class" in value and "location" in value:
        if value["class"] == "File":
            # This is going to re-file -> HDA this each iteration I think, not a good
            # implementation.
            return progress.raw_to_galaxy(value)
        assert value["location"].startswith("step_input://"), f"Invalid location {value}"
        return hda_references[int(value["location"][len("step_input://") :]) - 1]
    elif isinstance(value, dict):
        raise NotImplementedError()
    else:
        return value


def evaluate_value_from_expressions(progress, step, execution_state, extra_step_state):
    when_expression = step.when_expression
    value_from_expressions = {}

    if execution_state:
        for key in execution_state.inputs.keys():
            step_input = step.inputs_by_name.get(key)
            if step_input and step_input.value_from is not None:
                value_from_expressions[key] = step_input.value_from

    if not value_from_expressions and when_expression is None:
        return {}

    hda_references: List[model.HistoryDatasetAssociation] = []

    step_state = {}
    for key, value in extra_step_state.items():
        step_state[key] = to_cwl(value, hda_references=hda_references, step=step)
    if execution_state:
        for key, value in execution_state.inputs.items():
            step_state[key] = to_cwl(value, hda_references=hda_references, step=step)

    if when_expression is not None:
        if when_expression == "${inputs.when}":
            # Fallback for workflows defined on 23.0
            when_expression = "$(inputs.when)"
        try:
            as_cwl_value = do_eval(
                when_expression,
                step_state,
            )
        except Exception:
            # Exception contains script and traceback, which could be helpful for debugging workflows,
            # but both could conceivably contain secrets.
            # CWL has a secret hint that should cause values to be sanitized,
            # but Galaxy does not, so we can't really display anything here at this point.
            # In any case I believe the CWL secret hint can be bypassed if the value is passed on
            # to another step input that doesn't have the secret set.
            # Complicated stuff, ignore for now.
            raise FailWorkflowEvaluation(
                InvocationFailureExpressionEvaluationFailed(
                    reason=FailureReason.expression_evaluation_failed, workflow_step_id=step.id
                )
            )
        when_value = from_cwl(as_cwl_value, hda_references=hda_references, progress=progress)
        if not isinstance(when_value, bool):
            raise FailWorkflowEvaluation(
                InvocationFailureWhenNotBoolean(
                    reason=FailureReason.when_not_boolean,
                    workflow_step_id=step.id,
                    details=f"Type is: {when_value.__class__.__name__}",
                )
            )
        return when_value


class WorkflowModule:
    label: str
    type: str
    name: str

    def __init__(self, trans, content_id=None, **kwds):
        self.trans = trans
        self.content_id = content_id
        self.state = DefaultToolState()

    # ---- Creating modules from various representations ---------------------

    @classmethod
    def from_dict(Class, trans, d, **kwds):
        module = Class(trans, **kwds)
        input_connections = d.get("input_connections", {})
        module.recover_state(d.get("tool_state"), input_connections=input_connections, **kwds)
        module.label = d.get("label")
        return module

    @classmethod
    def from_workflow_step(Class, trans, step, **kwds):
        module = Class(trans, **kwds)
        module.recover_state(step.tool_inputs, from_tool_form=False)
        module.label = step.label
        return module

    # ---- Saving in various forms ------------------------------------------

    def save_to_step(self, step, detached: bool = False) -> None:
        step.type = self.type
        step.tool_inputs = self.get_state()

    # ---- General attributes -----------------------------------------------

    def get_type(self):
        return self.type

    def get_name(self):
        return self.name

    def get_version(self):
        return None

    def get_content_id(self):
        """If this component has an identifier external to the step (such
        as a tool or another workflow) return the identifier for that content.
        """
        return None

    def get_tooltip(self, static_path=""):
        return None

    # ---- Configuration time -----------------------------------------------

    def get_state(self, nested=True):
        """Return a serializable representation of the persistable state of
        the step.
        """
        if inputs := self.get_inputs():
            try:
                return self.state.encode(Bunch(inputs=inputs), self.trans.app, nested=nested)
            except ValueError:
                log.warning("Tool state invalid for workflow module", exc_info=True)
                # Always preferable to save unmodified and continue, I think ... we're explicit about alterations when retrieving any workflow,
                # and it is what we do if we don't have the tool installed (assuming this is a tool).
                pass
        return self.state.inputs

    def get_export_state(self):
        return self.get_state(nested=True)

    def get_tool_state(self):
        return self.get_state(nested=False)

    def recover_state(self, state, **kwds):
        """Recover tool state (as self.state and self.state.inputs) from dictionary describing
        configuration state (potentially from persisted step state).

        Sub-classes should supply a `default_state` method which contains the
        initial state `dict` with key, value pairs for all available attributes.

        Input parameter state may be a typed dictionary or a tool state dictionary generated by
        the web client (if from_tool_form in kwds is True).

        If classes need to distinguish between typed clean dictionary representations
        of state and the state generated for tool form (with extra nesting logic in the
        state for conditionals, un-typed string parameters, etc...) they should
        override the step_state_to_tool_state method to make this transformation.
        """
        from_tool_form = kwds.get("from_tool_form", False)
        if not from_tool_form:
            # I've never seen state here be none except for unit tests so 'or {}' below may only be
            # needed due to test bugs. Doesn't hurt anything though.
            state = self.step_state_to_tool_state(state or {})

        self.state = DefaultToolState()
        if inputs := self.get_inputs():
            self.state.decode(state, Bunch(inputs=inputs), self.trans.app)
        else:
            self.state.inputs = safe_loads(state) or {}

    def step_state_to_tool_state(self, state):
        return state

    def get_errors(self, **kwargs):
        """This returns a step related error message as string or None"""
        return None

    def get_inputs(self):
        """This returns inputs displayed in the workflow editor"""
        return {}

    def get_all_inputs(self, data_only=False, connectable_only=False):
        return []

    def get_data_inputs(self):
        """Get configure time data input descriptions."""
        return self.get_all_inputs(data_only=True)

    def get_all_outputs(self, data_only=False):
        return []

    def get_data_outputs(self):
        return self.get_all_outputs(data_only=True)

    def get_post_job_actions(self, incoming):
        return {}

    def check_and_update_state(self):
        """
        If the state is not in sync with the current implementation of the
        module, try to update. Returns a list of messages to be displayed
        """

    def add_dummy_datasets(self, connections=None, steps=None):
        """Replace connected inputs with placeholder/dummy values."""

    def get_config_form(self, step=None):
        """Serializes input parameters of a module into input dictionaries."""
        return {"title": self.name, "inputs": [param.to_dict(self.trans) for param in self.get_inputs().values()]}

    # ---- Run time ---------------------------------------------------------

    def get_runtime_state(self) -> DefaultToolState:
        raise TypeError("Abstract method")

    def get_runtime_inputs(self, step, connections: Optional[Iterable[WorkflowStepConnection]] = None):
        """Used internally by modules and when displaying inputs in workflow
        editor and run workflow templates.
        """
        return {}

    def compute_runtime_state(self, trans, step=None, step_updates=None, replace_default_values=False):
        """Determine the runtime state (potentially different from self.state
        which describes configuration state). This (again unlike self.state) is
        currently always a `DefaultToolState` object.

        If `step_updates` is `None`, this is likely for rendering the run form
        for instance and no runtime properties are available and state must be
        solely determined by the default runtime state described by the step.

        If `step_updates` are available they describe the runtime properties
        supplied by the workflow runner.
        """
        state = self.get_runtime_state()
        if replace_default_values and step:
            state.inputs = step.state.inputs
        step_errors = {}

        if step is not None:

            def update_value(input, context, prefixed_name, **kwargs):
                step_input = step.get_input(prefixed_name)
                if step_input is None:
                    return NO_REPLACEMENT

                if replace_default_values and step_input.default_value_set:
                    input_value = step_input.default_value
                    if isinstance(input, BaseDataToolParameter):
                        input_value = raw_to_galaxy(trans.app, trans.history, input_value)
                    return input_value

                return NO_REPLACEMENT

            visit_input_values(
                self.get_runtime_inputs(step, connections=step.output_connections),
                state.inputs,
                update_value,
                no_replacement_value=NO_REPLACEMENT,
            )

        if step_updates:

            def update_value(input, context, prefixed_name, **kwargs):
                if prefixed_name in step_updates:
                    value, error = check_param(trans, input, step_updates.get(prefixed_name), context)
                    if error is not None:
                        step_errors[prefixed_name] = error
                    return value
                return NO_REPLACEMENT

            visit_input_values(
                self.get_runtime_inputs(step), state.inputs, update_value, no_replacement_value=NO_REPLACEMENT
            )

        return state, step_errors

    def encode_runtime_state(self, step, runtime_state: DefaultToolState):
        """Takes the computed runtime state and serializes it during run request creation."""
        return runtime_state.encode(Bunch(inputs=self.get_runtime_inputs(step)), self.trans.app)

    def decode_runtime_state(self, step, runtime_state):
        """Takes the serialized runtime state and decodes it when running the workflow."""
        state = DefaultToolState()
        state.decode(runtime_state, Bunch(inputs=self.get_runtime_inputs(step)), self.trans.app)
        return state

    def execute(
        self, trans, progress: "WorkflowProgress", invocation_step, use_cached_job: bool = False
    ) -> Optional[bool]:
        """Execute the given workflow invocation step.

        Use the supplied workflow progress object to track outputs, find
        inputs, etc....

        Return a False if there is additional processing required to
        on subsequent workflow scheduling runs, None or True means the workflow
        step executed properly.
        """
        raise TypeError("Abstract method")

    def do_invocation_step_action(self, step, action):
        """Update or set the workflow invocation state action - generic
        extension point meant to allows users to interact with interactive
        workflow modules. The action object returned from this method will
        be attached to the WorkflowInvocationStep and be available the next
        time the workflow scheduler visits the workflow.
        """
        raise exceptions.RequestParameterInvalidException(
            "Attempting to perform invocation step action on module that does not support actions."
        )

    def recover_mapping(self, invocation_step, progress):
        """Re-populate progress object with information about connections
        from previously executed steps recorded via invocation_steps.
        """
        outputs = {}

        for output_dataset_assoc in invocation_step.output_datasets:
            outputs[output_dataset_assoc.output_name] = output_dataset_assoc.dataset

        for output_dataset_collection_assoc in invocation_step.output_dataset_collections:
            outputs[output_dataset_collection_assoc.output_name] = output_dataset_collection_assoc.dataset_collection

        progress.set_step_outputs(invocation_step, outputs, already_persisted=True)

    def get_informal_replacement_parameters(self, step) -> List[str]:
        """Return a list of informal replacement parameters.

        If replacement is handled via formal workflow inputs - do not include it in this list.
        """

        return []

    def compute_collection_info(self, progress: "WorkflowProgress", step, all_inputs):
        """
        Use get_all_inputs (if implemented) to determine collection mapping for execution.
        """
        collections_to_match = self._find_collections_to_match(progress, step, all_inputs)
        # Have implicit collections...
        collection_info = self.trans.app.dataset_collection_manager.match_collections(collections_to_match)
        if collection_info:
            if progress.subworkflow_collection_info:
                # We've mapped over a subworkflow. Slices of the invocation might be conditional
                # and progress.subworkflow_collection_info.when_values holds the appropriate when_values
                collection_info.when_values = progress.subworkflow_collection_info.when_values
            else:
                # The invocation is not mapped over, but it might still be conditional.
                # Multiplication and linking should be handled by slice_collection()
                collection_info.when_values = progress.when_values
        return collection_info or progress.subworkflow_collection_info

    def _find_collections_to_match(self, progress: "WorkflowProgress", step, all_inputs) -> matching.CollectionsToMatch:
        collections_to_match = matching.CollectionsToMatch()
        dataset_collection_type_descriptions = self.trans.app.dataset_collection_manager.collection_type_descriptions

        for input_dict in all_inputs:
            name = input_dict["name"]
            data = progress.replacement_for_input(self.trans, step, input_dict)
            can_map_over = hasattr(data, "collection")  # and data.collection.allow_implicit_mapping

            if not can_map_over:
                continue

            is_data_param = input_dict["input_type"] == "dataset"
            is_data_collection_param = input_dict["input_type"] == "dataset_collection"
            if is_data_param or is_data_collection_param:
                multiple = input_dict["multiple"]
                if is_data_param:
                    if multiple:
                        # multiple="true" data input, acts like "list" collection_type.
                        effective_input_collection_type = ["list"]
                    else:
                        collections_to_match.add(name, data)
                        continue
                else:
                    effective_input_collection_type = input_dict.get("collection_types")
                    if not effective_input_collection_type:
                        if progress.subworkflow_structure:
                            effective_input_collection_type = [
                                progress.subworkflow_structure.collection_type_description.collection_type
                            ]
                        elif input_dict.get("collection_type"):
                            effective_input_collection_type = [input_dict.get("collection_type")]
                type_list = []
                if progress.subworkflow_structure:
                    # If we have progress.subworkflow_structure were mapping a subworkflow invocation over a higher-dimension input
                    # e.g an outer list:list over an inner list. Whatever we do, the inner workflow cannot reduce the outer list.
                    # This is what we're setting up here.
                    type_list = progress.subworkflow_structure.collection_type_description.collection_type.split(":")
                    leaf_type = type_list.pop(0)
                    if type_list and type_list[-1] == effective_input_collection_type:
                        effective_input_collection_type = [":".join(type_list[:-1])] if ":".join(type_list[:-1]) else []
                history_query = HistoryQuery.from_collection_types(
                    effective_input_collection_type,
                    dataset_collection_type_descriptions,
                )
                subcollection_type_description = history_query.can_map_over(data) or None
                if subcollection_type_description:
                    subcollection_type_list = subcollection_type_description.collection_type.split(":")
                    for collection_type in reversed(subcollection_type_list):
                        if type_list:
                            leaf_type = type_list.pop(0)
                            assert collection_type == leaf_type
                    if type_list:
                        subcollection_type_description = dataset_collection_type_descriptions.for_collection_type(
                            ":".join(type_list)
                        )
                    collections_to_match.add(name, data, subcollection_type=subcollection_type_description)
                elif is_data_param and progress.subworkflow_structure:
                    collections_to_match.add(name, data, subcollection_type=subcollection_type_description)
                continue

            if data is not NO_REPLACEMENT:
                collections_to_match.add(name, data)
                continue

        known_input_names = {input_dict["name"] for input_dict in all_inputs}

        if step.when_expression:
            for step_input in step.inputs:
                step_input_name = step_input.name
                input_in_execution_state = step_input_name not in known_input_names
                if input_in_execution_state:
                    maybe_collection = progress.replacement_for_connection(
                        step.input_connections_by_name[step_input_name][0]
                    )
                    if hasattr(maybe_collection, "collection"):
                        # Is that always right ?
                        collections_to_match.add(step_input_name, maybe_collection)

        return collections_to_match


class SubWorkflowModule(WorkflowModule):
    # Two step improvements to build runtime inputs for subworkflow modules
    # - First pass verify nested workflow doesn't have an RuntimeInputs
    # - Second pass actually turn RuntimeInputs into inputs if possible.
    type = "subworkflow"
    name = "Subworkflow"
    _modules: Optional[List[Any]] = None
    subworkflow: Workflow

    def __init__(self, trans, content_id=None, **kwds):
        super().__init__(trans, content_id, **kwds)
        self.post_job_actions: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(Class, trans, d, **kwds):
        module = super().from_dict(trans, d, **kwds)
        if "subworkflow" in d:
            detached = kwds.get("detached", False)
            assert not detached  # dry run requires content_id
            module.subworkflow = d["subworkflow"]
        elif "content_id" in d:
            module.subworkflow = trans.app.workflow_manager.get_owned_workflow(trans, d["content_id"])
        else:
            raise Exception("Step associated subworkflow could not be found.")
        return module

    @classmethod
    def from_workflow_step(Class, trans, step, **kwds):
        module = super().from_workflow_step(trans, step, **kwds)
        module.subworkflow = step.subworkflow
        return module

    def save_to_step(self, step, detached=False):
        step.type = self.type
        step.subworkflow = self.subworkflow
        ensure_object_added_to_session(step, object_in_session=self.subworkflow)

    def get_name(self):
        if hasattr(self.subworkflow, "name"):
            return self.subworkflow.name
        return self.name

    def get_all_inputs(self, data_only=False, connectable_only=False):
        """Get configure time data input descriptions."""
        # Filter subworkflow steps and get inputs
        inputs = []
        if hasattr(self.subworkflow, "input_steps"):
            for step in self.subworkflow.input_steps:
                name = step.label
                if not name:
                    step_module = module_factory.from_workflow_step(self.trans, step)
                    name = f"{step.order_index}:{step_module.get_name()}"
                input = dict(
                    input_subworkflow_step_id=step.order_index,
                    name=name,
                    label=name,
                    multiple=False,
                    extensions=["data"],
                    input_type=step.input_type,
                )
                step_type = step.type
                if step_type == "data_collection_input":
                    input["collection_type"] = step.tool_inputs.get("collection_type") if step.tool_inputs else None
                if step_type == "parameter_input":
                    input["type"] = step.tool_inputs["parameter_type"]
                input["optional"] = step.tool_inputs.get("optional", False)
                inputs.append(input)
        return inputs

    def get_modules(self):
        if self._modules is None:
            self._modules = [module_factory.from_workflow_step(self.trans, step) for step in self.subworkflow.steps]
        return self._modules

    @property
    def version_changes(self):
        version_changes = []
        for m in self.get_modules():
            if hasattr(m, "version_changes"):
                version_changes.extend(m.version_changes)
        return version_changes

    def check_and_update_state(self):
        states = (m.check_and_update_state() for m in self.get_modules())
        # TODO: key ("Step N:") is not currently consumed in UI
        return {f"Step {i + 1}": upgrade_message for i, upgrade_message in enumerate(states) if upgrade_message} or None

    def get_errors(self, **kwargs):
        errors1 = (module.get_errors(include_tool_id=True) for module in self.get_modules())
        errors2 = [e for e in errors1 if e]
        if any(errors2):
            return errors2
        return None

    def get_all_outputs(self, data_only=False):
        outputs = []
        self.post_job_actions = {}
        if hasattr(self.subworkflow, "workflow_outputs"):
            from galaxy.managers.workflows import WorkflowContentsManager

            workflow_contents_manager = WorkflowContentsManager(self.trans.app, self.trans.app.trs_proxy)
            subworkflow_dict = workflow_contents_manager._workflow_to_dict_editor(
                trans=self.trans,
                stored=self.subworkflow.stored_workflow,
                workflow=self.subworkflow,
                tooltip=False,
                is_subworkflow=True,
            )
            for order_index in sorted(subworkflow_dict["steps"]):
                step = subworkflow_dict["steps"][order_index]
                data_outputs = step["outputs"]
                for workflow_output in step["workflow_outputs"]:
                    label = workflow_output["label"]
                    if not label:
                        label = f"{order_index}:{workflow_output['output_name']}"
                    workflow_output_uuid = workflow_output.get("uuid") or object()
                    for data_output in data_outputs:
                        data_output_uuid = data_output.get("uuid") or object()
                        if (
                            data_output["name"] == workflow_output["output_name"]
                            or data_output_uuid == workflow_output_uuid
                        ):
                            change_datatype_action = step["post_job_actions"].get(
                                f"ChangeDatatypeAction{data_output['name']}"
                            )
                            if change_datatype_action:
                                self.post_job_actions[f"ChangeDatatypeAction{label}"] = change_datatype_action
                            data_output["name"] = label
                            # That's the right data_output
                            break
                    else:
                        # This can happen when importing workflows with missing tools.
                        # We can't raise an exception here, as that would prevent loading
                        # the workflow.
                        # This is also listed when opening such a workflow in the workflow editor.
                        log.warning(
                            f"Workflow output '{workflow_output['output_name']}' defined, but not listed among data outputs"
                        )
                        continue

                    outputs.append(data_output)
        return outputs

    def get_post_job_actions(self, incoming):
        return self.post_job_actions

    def get_content_id(self):
        return self.trans.security.encode_id(self.subworkflow.id)

    def execute(
        self, trans, progress: "WorkflowProgress", invocation_step: WorkflowInvocationStep, use_cached_job: bool = False
    ) -> Optional[bool]:
        """Execute the given workflow step in the given workflow invocation.
        Use the supplied workflow progress object to track outputs, find
        inputs, etc...
        """
        step = invocation_step.workflow_step
        all_inputs = self.get_all_inputs()
        collection_info = self.compute_collection_info(progress, step, all_inputs)

        if collection_info:
            iteration_elements_iter = collection_info.slice_collections()
        else:
            if progress.when_values:
                # If we have more than one item in when_values it must have come from an expression.json
                # collection, so we'd have a collection_info instance ... I think.
                assert len(progress.when_values) == 1, "Got more than 1 when value, this shouldn't be possible"
            iteration_elements_iter = [(None, progress.when_values[0] if progress.when_values else None)]

        when_values: List[Union[bool, None]] = []
        for iteration_elements, when_value in iteration_elements_iter:
            if when_value is False or not step.when_expression:
                # We're skipping this step (when==False) or we keep
                # the current when_value if there is no explicit when_expression on this step.
                when_values.append(when_value)
            else:
                # Got a conditional step and we could potentially run it,
                # so we have to build the step state and evaluate the expression
                extra_step_state = {}
                for step_input in step.inputs:
                    step_input_name = step_input.name
                    if iteration_elements and step_input_name in iteration_elements:  # noqa: B023
                        value = iteration_elements[step_input_name]  # noqa: B023
                    else:
                        value = progress.replacement_for_connection(step_input.connections[0], is_data=True)
                    extra_step_state[step_input_name] = value

                when_values.append(
                    evaluate_value_from_expressions(
                        progress, step, execution_state={}, extra_step_state=extra_step_state
                    )
                )
        if collection_info:
            collection_info.when_values = when_values

        subworkflow_invoker = progress.subworkflow_invoker(
            trans,
            step,
            use_cached_job=use_cached_job,
            subworkflow_collection_info=collection_info,
            when_values=when_values,
        )
        subworkflow_invoker.invoke()
        subworkflow = subworkflow_invoker.workflow
        subworkflow_progress = subworkflow_invoker.progress
        outputs = {}
        for workflow_output in subworkflow.workflow_outputs:
            workflow_output_label = (
                workflow_output.label or f"{workflow_output.workflow_step.order_index}:{workflow_output.output_name}"
            )
            try:
                replacement = subworkflow_progress.get_replacement_workflow_output(workflow_output)
            except KeyError:
                raise FailWorkflowEvaluation(
                    why=InvocationFailureOutputNotFound(
                        reason=FailureReason.output_not_found,
                        workflow_step_id=workflow_output.workflow_step_id,
                        output_name=workflow_output.output_name,
                        dependent_workflow_step_id=step.id,
                    )
                )
            outputs[workflow_output_label] = replacement
        progress.set_step_outputs(invocation_step, outputs)
        return None

    def get_runtime_state(self):
        state = DefaultToolState()
        state.inputs = {}
        return state

    def get_runtime_inputs(self, step, connections: Optional[Iterable[WorkflowStepConnection]] = None):
        inputs = {}
        for step in self.subworkflow.steps:
            if step.type == "tool":
                assert isinstance(step.module, ToolModule)
                tool = step.module.tool
                if tool is None:
                    raise ToolMissingException("Tool in subworkflow missing.", tool_id=step.module.tool_id)
                tool_inputs = step.module.state

                def callback(input, prefixed_name, prefixed_label, value=None, **kwds):
                    # All data parameters are represented as runtime values, skip them
                    # here.
                    if input.type in ["data", "data_collection"]:
                        return

                    if is_runtime_value(value) and runtime_to_json(value)["__class__"] != "ConnectedValue":
                        input_name = f"{step.order_index}|{prefixed_name}"  # noqa: B023
                        inputs[input_name] = InputProxy(input, input_name)

                visit_input_values(tool.inputs, tool_inputs.inputs, callback)

        return inputs

    def get_informal_replacement_parameters(self, step) -> List[str]:
        """Return a list of replacement parameters."""
        replacement_parameters = set()

        formal_parameters = set()
        for step in self.subworkflow.input_steps:
            if step.label:
                formal_parameters.add(step.label)

        for subworkflow_step in self.subworkflow.steps:
            module = subworkflow_step.module
            assert module

            for replacement_parameter in module.get_informal_replacement_parameters(subworkflow_step):
                if replacement_parameter not in formal_parameters:
                    replacement_parameters.add(replacement_parameter)

        return list(replacement_parameters)


class InputProxy:
    """Provide InputParameter-interfaces over inputs but renamed for workflow context."""

    def __init__(self, input, prefixed_name):
        self.input = input
        self.prefixed_name = prefixed_name

    @property
    def name(self):
        return self.prefixed_name

    @property
    def label(self):
        return self.prefixed_name

    def to_dict(self, *args, **kwds):
        as_dict = self.input.to_dict(*args, **kwds)
        as_dict["name"] = self.prefixed_name
        return as_dict


def optional_param(optional=None):
    bool_source = dict(name="optional", label="Optional", type="boolean", checked=optional)
    optional_value = BooleanToolParameter(None, bool_source)
    return optional_value


def format_param(trans, formats):
    formats_val = "" if not formats else ",".join(formats)
    source = dict(
        type="text",
        label="Format(s)",
        name="format",
        value=formats_val,
        optional=True,
        options=formats,
        help="Leave empty to auto-generate filtered list at runtime based on connections.",
    )
    source["options"] = [{"value": v, "label": v} for v in trans.app.datatypes_registry.datatypes_by_extension.keys()]
    format_value = TextToolParameter(None, source)
    return format_value


class InputModuleState(TypedDict, total=False):
    optional: bool
    format: List[str]
    tag: str


class InputModule(WorkflowModule):
    default_optional = False

    def get_runtime_state(self):
        state = DefaultToolState()
        state.inputs = dict(input=NO_REPLACEMENT)
        return state

    def get_all_inputs(self, data_only=False, connectable_only=False):
        return []

    def execute(
        self, trans, progress: "WorkflowProgress", invocation_step, use_cached_job: bool = False
    ) -> Optional[bool]:
        invocation = invocation_step.workflow_invocation
        step = invocation_step.workflow_step
        input_value = step.state.inputs["input"]
        if input_value is NO_REPLACEMENT:
            default_value = step.get_input_default_value(NO_REPLACEMENT)
            if default_value is not NO_REPLACEMENT:
                input_value = raw_to_galaxy(trans.app, trans.history, default_value)

        step_outputs = dict(output=input_value)

        # Web controller may set copy_inputs_to_history, API controller always sets
        # inputs.
        if progress.copy_inputs_to_history:
            for input_dataset_hda in list(step_outputs.values()):
                content_type = input_dataset_hda.history_content_type
                if content_type == "dataset":
                    new_hda = input_dataset_hda.copy()
                    invocation.history.add_dataset(new_hda)
                    step_outputs["input_ds_copy"] = new_hda
                elif content_type == "dataset_collection":
                    new_hdca = input_dataset_hda.copy()
                    invocation.history.add_dataset_collection(new_hdca)
                    step_outputs["input_ds_copy"] = new_hdca
                else:
                    raise Exception("Unknown history content encountered")
        # If coming from UI - we haven't registered invocation inputs yet,
        # so do that now so dependent steps can be recalculated. In the future
        # everything should come in from the API and this can be eliminated.
        if not invocation.has_input_for_step(step.id):
            content = next(iter(step_outputs.values()))
            if content and content is not NO_REPLACEMENT:
                invocation.add_input(content, step.id)
        progress.set_outputs_for_input(invocation_step, step_outputs)
        return None

    def recover_mapping(self, invocation_step: WorkflowInvocationStep, progress: "WorkflowProgress"):
        super().recover_mapping(invocation_step, progress)
        progress.set_outputs_for_input(
            invocation_step, progress.outputs.get(invocation_step.workflow_step_id), already_persisted=True
        )

    def get_export_state(self):
        return self._parse_state_into_dict()

    def _parse_state_into_dict(self):
        inputs = self.state.inputs
        rval: InputModuleState = {}
        if "optional" in inputs:
            optional = bool(inputs["optional"])
        else:
            optional = self.default_optional
        rval["optional"] = optional
        if "format" in inputs:
            formats: Optional[List[str]] = listify(inputs["format"])
        else:
            formats = None
        if formats:
            rval["format"] = formats
        if "tag" in inputs:
            tag = inputs["tag"]
        else:
            tag = None
        rval["tag"] = tag
        return rval

    def step_state_to_tool_state(self, state):
        state = safe_loads(state)
        if "format" in state:
            formats = state["format"]
            if formats:
                formats = ",".join(listify(formats))
                state["format"] = formats
        state = json.dumps(state)
        return state

    def save_to_step(self, step, detached=False):
        step.type = self.type
        step.tool_inputs = self._parse_state_into_dict()


class InputDataModule(InputModule):
    type = "data_input"
    name = "Input dataset"

    def get_all_outputs(self, data_only=False):
        parameter_def = self._parse_state_into_dict()
        format_def = parameter_def.get("format")
        optional = parameter_def["optional"]
        if format_def is None:
            extensions = ["input"]
        else:
            extensions = listify(format_def)
        return [dict(name="output", extensions=extensions, optional=optional)]

    def get_filter_set(self, connections=None):
        filter_set = set()  # Use a set to ensure unique extensions
        if connections:
            for oc in connections:
                for ic in oc.input_step.module.get_data_inputs():
                    if "extensions" in ic and ic["extensions"] != "input" and ic["name"] == oc.input_name:
                        filter_set.update(ic["extensions"])
        if not filter_set:
            filter_set = {"data"}
        return ", ".join(sorted(filter_set))

    def get_runtime_inputs(self, step, connections: Optional[Iterable[WorkflowStepConnection]] = None):
        parameter_def = self._parse_state_into_dict()
        optional = parameter_def["optional"]
        tag = parameter_def["tag"]
        formats = parameter_def.get("format")
        if not formats:
            formats = self.get_filter_set(connections)
        else:
            formats = ",".join(listify(formats))
        data_src = dict(
            name="input", label=self.label, multiple=False, type="data", format=formats, tag=tag, optional=optional
        )
        default_unset = object()
        default = step.get_input_default_value(default_unset)
        if default is not default_unset:
            data_src["default"] = default
        input_param = DataToolParameter(None, data_src, self.trans)
        return dict(input=input_param)

    def get_inputs(self):
        parameter_def = self._parse_state_into_dict()
        tag = parameter_def["tag"]
        tag_source = dict(
            name="tag",
            label="Tag filter",
            type="text",
            optional="true",
            value=tag,
            help="Tags to automatically filter inputs",
        )
        input_tag = TextToolParameter(None, tag_source)
        optional = parameter_def["optional"]
        inputs = {}
        inputs["optional"] = optional_param(optional)
        inputs["format"] = format_param(self.trans, parameter_def.get("format"))
        inputs["tag"] = input_tag
        return inputs


class InputDataCollectionModule(InputModule):
    type = "data_collection_input"
    name = "Input dataset collection"
    default_collection_type = "list"
    collection_type = default_collection_type

    def get_inputs(self):
        parameter_def = self._parse_state_into_dict()
        collection_type = parameter_def["collection_type"]
        tag = parameter_def["tag"]
        optional = parameter_def["optional"]
        collection_type_source = dict(
            name="collection_type", label="Collection type", type="text", value=collection_type
        )
        collection_type_source["options"] = [
            {"value": "list", "label": "List of Datasets"},
            {"value": "paired", "label": "Dataset Pair"},
            {"value": "list:paired", "label": "List of Dataset Pairs"},
        ]
        input_collection_type = TextToolParameter(None, collection_type_source)
        tag_source = dict(
            name="tag",
            label="Tag filter",
            type="text",
            optional="true",
            value=tag,
            help="Tags to automatically filter inputs",
        )
        input_tag = TextToolParameter(None, tag_source)
        inputs = {}
        inputs["collection_type"] = input_collection_type
        inputs["optional"] = optional_param(optional)
        inputs["format"] = format_param(self.trans, parameter_def.get("format"))
        inputs["tag"] = input_tag
        return inputs

    def get_runtime_inputs(self, step, connections: Optional[Iterable[WorkflowStepConnection]] = None):
        parameter_def = self._parse_state_into_dict()
        collection_type = parameter_def["collection_type"]
        optional = parameter_def["optional"]
        tag = parameter_def["tag"]
        collection_param_source = dict(
            name="input",
            label=self.label,
            type="data_collection",
            collection_type=collection_type,
            tag=tag,
            optional=optional,
        )
        if formats := parameter_def.get("format"):
            collection_param_source["format"] = ",".join(listify(formats))
        input_param = DataCollectionToolParameter(None, collection_param_source, self.trans)
        return dict(input=input_param)

    def get_all_outputs(self, data_only=False):
        parameter_def = self._parse_state_into_dict()
        format_def = parameter_def.get("format")
        optional = parameter_def["optional"]
        if format_def is None:
            extensions = ["input"]
        else:
            extensions = listify(format_def)
        return [
            dict(
                name="output",
                extensions=extensions,
                collection=True,
                collection_type=parameter_def.get("collection_type", self.default_collection_type),
                optional=optional,
            )
        ]

    def _parse_state_into_dict(self):
        state_as_dict = super()._parse_state_into_dict()
        if "collection_type" in (inputs := self.state.inputs):
            collection_type = inputs["collection_type"]
        else:
            collection_type = self.default_collection_type
        state_as_dict["collection_type"] = collection_type
        return state_as_dict


class InputParameterModule(WorkflowModule):
    POSSIBLE_PARAMETER_TYPES = POSSIBLE_PARAMETER_TYPES
    type = "parameter_input"
    name = "Input parameter"
    default_parameter_type = "text"
    default_optional = False
    default_default_value = None
    parameter_type = default_parameter_type
    optional = default_optional
    default_value = default_default_value

    def get_inputs(self):
        parameter_def = self._parse_state_into_dict()
        parameter_type = parameter_def["parameter_type"]
        select_source = dict(name="parameter_type", label="Parameter type", type="select", value=parameter_type)
        select_source["options"] = [
            {"value": "text", "label": "Text"},
            {"value": "integer", "label": "Integer"},
            {"value": "float", "label": "Float"},
            {"value": "boolean", "label": "Boolean (True or False)"},
            {"value": "color", "label": "Color"},
            {"value": "directory_uri", "label": "Directory URI"},
        ]
        input_parameter_type = SelectToolParameter(None, select_source)
        # encode following loop in description above instead
        for i, option in enumerate(input_parameter_type.static_options):
            option = list(option)
            if option[1] == parameter_type:
                # item 0 is option description, item 1 is value, item 2 is "selected"
                option[2] = True
                input_parameter_type.static_options[i] = tuple(option)

        parameter_type_cond = Conditional("parameter_definition")
        parameter_type_cond.test_param = input_parameter_type
        cases = []

        for param_type in POSSIBLE_PARAMETER_TYPES:
            default_parameter = get_default_parameter(param_type)

            optional_value = optional_param()
            optional_cond = Conditional("optional")
            optional_cond.test_param = optional_value

            when_this_type = ConditionalWhen()
            when_this_type.value = param_type
            when_this_type.inputs = {}
            when_this_type.inputs["optional"] = optional_cond

            specify_default_source = dict(
                name="specify_default",
                label="Specify a default value",
                type="boolean",
            )
            specify_default = BooleanToolParameter(None, specify_default_source)
            specify_default_cond = Conditional("specify_default")
            specify_default_cond.test_param = specify_default

            when_specify_default_true = ConditionalWhen()
            when_specify_default_true.value = "true"
            when_specify_default_true.inputs = {}
            when_specify_default_true.inputs["default"] = default_parameter

            when_specify_default_false = ConditionalWhen()
            when_specify_default_false.value = "false"
            when_specify_default_false.inputs = {}

            specify_default_cond_cases = [when_specify_default_true, when_specify_default_false]
            specify_default_cond.cases = specify_default_cond_cases

            when_true = ConditionalWhen()
            when_true.value = "true"
            when_true.inputs = {"default": specify_default_cond}

            when_false = ConditionalWhen()
            when_false.value = "false"
            # This is only present for backwards compatibility,
            # We don't need this conditional since you can set
            # a default value for optional and required parameters.
            # TODO: version the state and upgrade it to a simpler version
            when_false.inputs = {"default": specify_default_cond}

            optional_cases = [when_true, when_false]
            optional_cond.cases = optional_cases

            def regex_validator_definition():
                add_validators_repeat = Repeat("validators")
                add_validators_repeat.title = "Add validator to restrict valid input"
                add_validators_repeat.min = 0
                add_validators_repeat.max = math.inf
                add_validators_repeat.inputs = {
                    "regex_match": TextToolParameter(
                        None,
                        {
                            "optional": False,
                            "name": "regex_match",
                            "label": "Specify regular expression",
                            "help": "Provided [regular expression](gxhelp://programming.python.reg.ex) must match input value for input to be valid",
                            "help_format": "markdown",
                        },
                    ),
                    "regex_doc": TextToolParameter(
                        None,
                        {
                            "optional": False,
                            "name": "regex_doc",
                            "label": "Specify a message",
                            "help": "This message will be shown if the regular does not match the input",
                        },
                    ),
                }

                return add_validators_repeat

            if param_type == "text":

                specify_multiple_source = dict(
                    name="multiple",
                    label="Allow multiple selection",
                    help="Only applies when connected to multi-select parameter(s)",
                    type="boolean",
                )

                specify_multiple = BooleanToolParameter(None, specify_multiple_source)

                # Insert multiple option as first option, which is determined by dictionary insert order
                when_this_type.inputs = {
                    "multiple": specify_multiple,
                    "validators": regex_validator_definition(),
                    **when_this_type.inputs,
                }

                restrict_how_source: Dict[str, Union[str, List[Dict[str, Union[str, bool]]]]] = dict(
                    name="how", label="Restrict Text Values?", type="select"
                )
                restrict_how_source["options"] = [
                    {
                        "value": "none",
                        "label": "Do not specify restrictions (default).",
                    },
                    {
                        "value": "onConnections",
                        "label": "Attempt restriction based on connections.",
                    },
                    {
                        "value": "staticRestrictions",
                        "label": "Provide list of all possible values.",
                    },
                    {
                        "value": "staticSuggestions",
                        "label": "Provide list of suggested values.",
                    },
                ]
                restrictions_cond = Conditional("restrictions")
                restrictions_how = SelectToolParameter(None, restrict_how_source)
                restrictions_cond.test_param = restrictions_how

                when_restrict_none = ConditionalWhen()
                when_restrict_none.value = "none"
                when_restrict_none.inputs = {}

                when_restrict_connections = ConditionalWhen()
                when_restrict_connections.value = "onConnections"
                when_restrict_connections.inputs = {}

                when_restrict_static_restrictions = ConditionalWhen()
                when_restrict_static_restrictions.value = "staticRestrictions"
                when_restrict_static_restrictions.inputs = {}

                when_restrict_static_suggestions = ConditionalWhen()
                when_restrict_static_suggestions.value = "staticSuggestions"
                when_restrict_static_suggestions.inputs = {}

                # Repeats don't work - so use common separated list for now.

                # Use both restrictions and suggestions as each other's default so value preserved.
                restrictions_list = parameter_def.get("restrictions") or parameter_def.get("suggestions")
                if restrictions_list is None:
                    restrictions_list = []
                restriction_values = self._parameter_option_def_to_tool_form_str(restrictions_list)
                restrictions_source = dict(
                    name="restrictions",
                    label="Restricted Values",
                    value=restriction_values,
                    help="Comma-separated list of all permitted values",
                )
                restrictions = TextToolParameter(None, restrictions_source)

                suggestions_source = dict(
                    name="suggestions",
                    label="Suggested Values",
                    value=restriction_values,
                    help="Comma-separated list of some potential values",
                )
                suggestions = TextToolParameter(None, suggestions_source)

                when_restrict_static_restrictions.inputs["restrictions"] = restrictions
                when_restrict_static_suggestions.inputs["suggestions"] = suggestions

                restrictions_cond_cases = [
                    when_restrict_none,
                    when_restrict_connections,
                    when_restrict_static_restrictions,
                    when_restrict_static_suggestions,
                ]
                restrictions_cond.cases = restrictions_cond_cases
                when_this_type.inputs["restrictions"] = restrictions_cond

            if param_type == "integer":
                when_this_type.inputs["min"] = IntegerToolParameter(
                    None,
                    {
                        "name": "min",
                        "optional": True,
                        "value": parameter_def.get("min", ""),
                        "label": "Set a minimum value for this input",
                    },
                )
                when_this_type.inputs["max"] = IntegerToolParameter(
                    None,
                    {
                        "name": "max",
                        "optional": True,
                        "value": parameter_def.get("max", ""),
                        "label": "Set a maximum value for this input",
                    },
                )
            if param_type == "float":
                when_this_type.inputs["min"] = FloatToolParameter(
                    None,
                    {
                        "name": "min",
                        "optional": True,
                        "value": parameter_def.get("min", ""),
                        "label": "Set a minimum value for this input",
                    },
                )
                when_this_type.inputs["max"] = FloatToolParameter(
                    None,
                    {
                        "name": "max",
                        "optional": True,
                        "value": parameter_def.get("max", ""),
                        "label": "Set a maximum value for this input",
                    },
                )
            if param_type == "directory_uri":
                when_this_type.inputs["validators"] = regex_validator_definition()

            cases.append(when_this_type)

        parameter_type_cond.cases = cases
        return {"parameter_definition": parameter_type_cond}

    def get_config_form(self, step=None):
        """Serializes input parameters of a module into input dictionaries."""
        group_inputs: List[Dict[str, Any]] = []
        populate_model(self.trans, self.get_inputs(), self.state.inputs, group_inputs)
        return {"title": self.name, "inputs": group_inputs}

    def restrict_options(self, step, connections: Iterable[WorkflowStepConnection], default_value):
        try:
            static_options: List[List[ParameterOption]] = []
            # Retrieve possible runtime options for 'select' type inputs
            for connection in connections:
                # Well this isn't a great assumption...
                assert connection.input_step
                module = connection.input_step.module
                assert isinstance(module, (ToolModule, SubWorkflowModule))
                if isinstance(module, ToolModule):
                    assert module.tool
                    tool_inputs = module.tool.inputs  # may not be set, but we're catching the Exception below.

                    def callback(input, prefixed_name, context, **kwargs):
                        if prefixed_name == connection.input_name and hasattr(input, "get_options"):  # noqa: B023
                            static_options.append(input.get_options(self.trans, context))

                    visit_input_values(tool_inputs, module.state.inputs, callback)
                elif isinstance(module, SubWorkflowModule):
                    subworkflow_input_name = connection.input_name
                    for step in module.subworkflow.input_steps:
                        if step.input_type == "parameter" and step.label == subworkflow_input_name:
                            static_options.append(
                                step.module.get_runtime_inputs(step, connections=step.output_connections)[
                                    "input"
                                ].static_options
                            )

            options: Optional[List[OptionDict]] = None
            if static_options and len(static_options) == 1:
                # If we are connected to a single option, just use it as is so order is preserved cleanly and such.
                options = [
                    {"label": o[0], "value": o[1], "selected": bool(default_value and o[1] == default_value)}
                    for o in static_options[0]
                ]
            elif static_options:
                # Intersection based on values of multiple option connections.
                intxn_vals = set.intersection(*({option.value for option in options} for options in static_options))
                intxn_opts = {option for options in static_options for option in options if option.value in intxn_vals}
                collapsed_labels = defaultdict(set)  # Collapse labels with same values
                for option in intxn_opts:
                    collapsed_labels[option.value].add(option.name)
                options = [
                    {
                        "label": ", ".join(labels),
                        "value": value,
                        "selected": bool(default_value and value == default_value),
                    }
                    for value, labels in collapsed_labels.items()
                ]
                options.sort(key=lambda x: x["label"])

            return options
        except Exception:
            log.debug("Failed to generate options for text parameter, falling back to free text.", exc_info=True)

    def get_runtime_inputs(self, step, connections: Optional[Iterable[WorkflowStepConnection]] = None):
        parameter_def = self._parse_state_into_dict()
        parameter_type = parameter_def["parameter_type"]
        optional = parameter_def["optional"]
        default_value_set = "default" in parameter_def
        default_value = parameter_def.get("default", self.default_default_value)
        if parameter_type not in ["text", "boolean", "integer", "float", "color", "directory_uri"]:
            raise ValueError("Invalid parameter type for workflow parameters encountered.")

        # Optional parameters for tool input source definition.
        parameter_kwds: Dict[str, Union[str, List[Dict[str, Any]]]] = {}
        if "multiple" in parameter_def:
            parameter_kwds["multiple"] = parameter_def["multiple"]

        is_text = parameter_type == "text"
        restricted_inputs = False

        # Really is just an attempt - tool module may not be available (small problem), get_options may really depend on other
        # values we are not setting, so this isn't great. Be sure to just fallback to text in this case.
        attemptRestrictOnConnections = is_text and parameter_def.get("restrictOnConnections") and connections
        if attemptRestrictOnConnections:
            connections = cast(Iterable[WorkflowStepConnection], connections)
            restricted_options = self.restrict_options(step, connections=connections, default_value=default_value)
            if restricted_options is not None:
                restricted_inputs = True
                parameter_kwds["options"] = restricted_options

        def _parameter_def_list_to_options(parameter_value):
            options = []
            for item in parameter_value:
                option = {}
                if isinstance(item, dict):
                    value = item["value"]
                    option["value"] = value
                    if "label" in item:
                        option["label"] = item["label"]
                    else:
                        option["label"] = value
                else:
                    option["value"] = item
                    option["label"] = item
                options.append(option)
            return options

        if is_text and not restricted_inputs and parameter_def.get("restrictions"):
            restriction_values = parameter_def.get("restrictions")
            parameter_kwds["options"] = _parameter_def_list_to_options(restriction_values)
            restricted_inputs = True

        if parameter_def.get("validators"):
            parameter_kwds["validators"] = parameter_def["validators"]

        client_parameter_type = parameter_type
        if restricted_inputs:
            client_parameter_type = "select"

        parameter_class = parameter_types[client_parameter_type]

        if default_value_set:
            if client_parameter_type == "select":
                parameter_kwds["selected"] = default_value
            else:
                parameter_kwds["value"] = default_value
            if parameter_type == "boolean":
                parameter_kwds["checked"] = default_value

        if is_text and parameter_def.get("suggestions") is not None:
            suggestion_values = parameter_def.get("suggestions")
            parameter_kwds["options"] = _parameter_def_list_to_options(suggestion_values)

        input_source_dict = dict(
            name="input", label=self.label, type=client_parameter_type, optional=optional, **parameter_kwds
        )
        input_source = get_input_source(input_source_dict, trusted=False)
        input = parameter_class(None, input_source)
        return dict(input=input)

    def get_runtime_state(self):
        state = DefaultToolState()
        state.inputs = dict(input=NO_REPLACEMENT)
        return state

    def get_all_outputs(self, data_only=False):
        if data_only:
            return []

        parameter_def = self._parse_state_into_dict()
        return [
            dict(
                name="output",
                label=self.label,
                type=parameter_def.get("parameter_type"),
                optional=parameter_def["optional"],
                multiple=parameter_def.get("multiple", False),
                parameter=True,
            )
        ]

    def execute(
        self, trans, progress: "WorkflowProgress", invocation_step, use_cached_job: bool = False
    ) -> Optional[bool]:
        step = invocation_step.workflow_step
        if step.id in progress.inputs_by_step_id:
            input_value = progress.inputs_by_step_id[step.id]
        else:
            input_value = step.state.inputs["input"]
        if input_value is NO_REPLACEMENT:
            default_value = step.get_input_default_value(NO_REPLACEMENT)
            # TODO: look at parameter type and infer if value should be a dictionary
            # instead. Guessing only field parameter types in CWL branch would have
            # default as dictionary like this.
            if not isinstance(default_value, dict):
                default_value = {"value": default_value}
            input_value = default_value.get("value", NO_REPLACEMENT)
        input_param = self.get_runtime_inputs(self)["input"]
        # TODO: raise DelayedWorkflowEvaluation if replacement not ready ? Need test
        try:
            input_param.validate(input_value, trans)
        except ValueError as e:
            raise FailWorkflowEvaluation(
                why=InvocationFailureWorkflowParameterInvalid(
                    reason=FailureReason.workflow_parameter_invalid, workflow_step_id=step.id, details=str(e)
                )
            )
        step_outputs = dict(output=input_value)
        progress.set_outputs_for_input(invocation_step, step_outputs)
        return None

    def step_state_to_tool_state(self, state):
        state = safe_loads(state)
        default_set, default_value = False, None
        if "default" in state:
            default_set = True
            default_value = state["default"]
        multiple = state.get("multiple")
        source_validators = state.get("validators")
        restrictions = state.get("restrictions")
        restrictOnConnections = state.get("restrictOnConnections")
        suggestions = state.get("suggestions")
        restrictions_how = "none"
        if restrictions is not None:
            restrictions_how = "staticRestrictions"
        if suggestions is not None:
            restrictions_how = "staticSuggestions"
        elif restrictOnConnections:
            restrictions_how = "onConnections"

        state = {
            "parameter_definition": {
                "parameter_type": state["parameter_type"],
                "optional": {"optional": str(state.get("optional", False))},
            }
        }
        if multiple is not None:
            state["parameter_definition"]["multiple"] = multiple
        if source_validators is not None:
            form_validators = []
            # the form definition can change from Galaxy to Galaxy fairly freely, but the source validators are persisted
            # and need to be consistent - here we convert the persisted/YAML tool definition version to the "tool form" version.
            for source_validator in source_validators:
                source_type = source_validator["type"]
                if source_type == "regex":
                    form_validators.append(
                        {
                            "regex_doc": source_validator.get("message"),
                            "regex_match": source_validator.get("expression"),
                        }
                    )
                elif source_type == "in_range":
                    state["parameter_definition"]["min"] = source_validator.get("min")
                    state["parameter_definition"]["max"] = source_validator.get("max")
            state["parameter_definition"]["validators"] = form_validators
        state["parameter_definition"]["restrictions"] = {}
        state["parameter_definition"]["restrictions"]["how"] = restrictions_how

        if restrictions_how == "staticRestrictions":
            state["parameter_definition"]["restrictions"]["restrictions"] = self._parameter_option_def_to_tool_form_str(
                restrictions
            )
        if restrictions_how == "staticSuggestions":
            state["parameter_definition"]["restrictions"]["suggestions"] = self._parameter_option_def_to_tool_form_str(
                suggestions
            )
        if default_set:
            state["parameter_definition"]["optional"]["specify_default"] = {}
            state["parameter_definition"]["optional"]["specify_default"]["specify_default"] = True
            state["parameter_definition"]["optional"]["specify_default"]["default"] = default_value
        state = json.dumps(state)
        return state

    def _parameter_option_def_to_tool_form_str(self, parameter_def):
        return ",".join(f"{o['value']}:{o['label']}" if isinstance(o, dict) else o for o in parameter_def)

    def get_export_state(self):
        export_state = self._parse_state_into_dict()
        return export_state

    def _parse_state_into_dict(self):
        inputs = self.state.inputs
        rval = {}
        # 19.0X tool state...
        if "parameter_type" in inputs:
            rval.update({"parameter_type": inputs["parameter_type"], "optional": False})
        # expanded tool state...
        elif "parameter_definition" in inputs:
            parameters_def = inputs["parameter_definition"]
            if "optional" in parameters_def:
                optional_state = parameters_def["optional"]
                optional = bool(optional_state["optional"])
                if "specify_default" in optional_state and bool(optional_state["specify_default"]["specify_default"]):
                    rval["default"] = optional_state["specify_default"]["default"]
            else:
                optional = False
            if "multiple" in parameters_def:
                rval["multiple"] = parameters_def["multiple"]
            source_validators = []
            if "min" in parameters_def or "max" in parameters_def:
                min = parameters_def.get("min")
                max = parameters_def.get("max")
                source_validators.append(
                    {
                        "min": min,
                        "max": max,
                        "negate": False,
                        "type": "in_range",
                    }
                )

            if "validators" in parameters_def:
                form_validators = parameters_def["validators"]
                # convert the current tool form structure to the persisted YAML-definition style
                for form_validator in form_validators:
                    source_validators.append(
                        {
                            "message": form_validator["regex_doc"],
                            "expression": form_validator["regex_match"],
                            "negate": False,
                            "type": "regex",
                        }
                    )
            rval["validators"] = source_validators
            restrictions_cond_values = parameters_def.get("restrictions")
            if restrictions_cond_values:

                def _string_to_parameter_def_option(str_value):
                    items = []
                    for option_part in str_value.split(","):
                        option_part = option_part.strip()
                        if ":" not in option_part:
                            items.append(option_part)
                        else:
                            value, label = option_part.split(":", 1)
                            items.append({"value": value, "label": label})
                    return items

                # how better be in here.
                how = restrictions_cond_values["how"]
                if how == "none":
                    pass
                elif how == "onConnections":
                    rval["restrictOnConnections"] = True
                elif how == "staticRestrictions":
                    restriction_values = restrictions_cond_values["restrictions"]
                    rval.update({"restrictions": _string_to_parameter_def_option(restriction_values)})
                elif how == "staticSuggestions":
                    suggestion_values = restrictions_cond_values["suggestions"]
                    rval.update({"suggestions": _string_to_parameter_def_option(suggestion_values)})
                else:
                    log.warning("Unknown restriction conditional type encountered for workflow parameter.")

            rval.update({"parameter_type": parameters_def["parameter_type"], "optional": optional})
        else:
            rval.update({"parameter_type": self.default_parameter_type, "optional": self.default_optional})
        return rval

    def save_to_step(self, step, detached=False):
        step.type = self.type
        step.tool_inputs = self._parse_state_into_dict()


class PauseModule(WorkflowModule):
    """Initially this module will unconditionally pause a workflow - will aim
    to allow conditional pausing later on.
    """

    type = "pause"
    name = "Pause for dataset review"

    def get_all_inputs(self, data_only=False, connectable_only=False):
        input = dict(
            name="input",
            label="Dataset for Review",
            multiple=False,
            extensions="input",
            input_type="dataset",
        )
        return [input] if not data_only else []

    def get_all_outputs(self, data_only=False):
        return [dict(name="output", label="Reviewed Dataset", extensions=["input"])]

    def get_runtime_state(self):
        state = DefaultToolState()
        state.inputs = {}
        return state

    def execute(
        self, trans, progress: "WorkflowProgress", invocation_step, use_cached_job: bool = False
    ) -> Optional[bool]:
        step = invocation_step.workflow_step
        progress.mark_step_outputs_delayed(step, why="executing pause step")
        return None

    def recover_mapping(self, invocation_step, progress):
        if invocation_step:
            step = invocation_step.workflow_step
            action = invocation_step.action
            if action:
                connection = step.input_connections_by_name["input"][0]
                replacement = progress.replacement_for_connection(connection)
                progress.set_step_outputs(invocation_step, {"output": replacement})
                return
            elif action is False:
                raise CancelWorkflowEvaluation(
                    why=InvocationCancellationReviewFailed(
                        reason=CancelReason.cancelled_on_review, workflow_step_id=step.id
                    )
                )
        delayed_why = "workflow paused at this step waiting for review"
        raise DelayedWorkflowEvaluation(why=delayed_why)

    def do_invocation_step_action(self, step, action):
        """Update or set the workflow invocation state action - generic
        extension point meant to allows users to interact with interactive
        workflow modules. The action object returned from this method will
        be attached to the WorkflowInvocationStep and be available the next
        time the workflow scheduler visits the workflow.
        """
        return bool(action)


class ToolModule(WorkflowModule):
    type = "tool"
    name = "Tool"

    def __init__(self, trans, tool_id, tool_version=None, exact_tools=True, tool_uuid=None, **kwds):
        super().__init__(trans, content_id=tool_id, **kwds)
        self.tool_id = tool_id
        self.tool_version = str(tool_version) if tool_version else None
        self.tool_uuid = tool_uuid
        self.tool = None
        if getattr(trans.app, "toolbox", None):
            self.tool = trans.app.toolbox.get_tool(
                tool_id, tool_version=tool_version, exact=exact_tools, tool_uuid=tool_uuid
            )
        if self.tool:
            current_tool_version = str(self.tool.version)
            if exact_tools and self.tool_version and self.tool_version != current_tool_version:
                safe_version = get_safe_version(self.tool, self.tool_version)
                if safe_version:
                    self.tool = trans.app.toolbox.get_tool(
                        tool_id, tool_version=safe_version, exact=True, tool_uuid=tool_uuid
                    )
                else:
                    log.info(
                        f"Exact tool specified during workflow module creation for [{tool_id}] but couldn't find correct version [{tool_version}]."
                    )
                    self.tool = None
        self.post_job_actions = {}
        self.runtime_post_job_actions = {}
        self.workflow_outputs = []
        self.version_changes = []

    # ---- Creating modules from various representations ---------------------

    @classmethod
    def from_dict(Class, trans, d, **kwds):
        tool_id = d.get("content_id") or d.get("tool_id")
        tool_version = d.get("tool_version")
        if tool_version:
            tool_version = str(tool_version)
        tool_uuid = d.get("tool_uuid", None)
        if tool_id is None and tool_uuid is None:
            tool_representation = d.get("tool_representation")
            if tool_representation:
                create_request = {
                    "representation": tool_representation,
                }
                if not trans.user_is_admin:
                    raise exceptions.AdminRequiredException("Only admin users can create tools dynamically.")
                dynamic_tool = trans.app.dynamic_tool_manager.create_tool(trans, create_request, allow_load=False)
                tool_uuid = dynamic_tool.uuid
        if tool_id is None and tool_uuid is None:
            raise exceptions.RequestParameterInvalidException(f"No content id could be located for for step [{d}]")
        module = super().from_dict(trans, d, tool_id=tool_id, tool_version=tool_version, tool_uuid=tool_uuid, **kwds)
        module.post_job_actions = d.get("post_job_actions", {})
        module.workflow_outputs = d.get("workflow_outputs", [])
        if module.tool:
            message = ""
            if tool_id != module.tool_id:
                message += f"The tool (id '{tool_id}') specified in this step is not available. Using the tool with id {module.tool_id} instead."
            if d.get("tool_version", "Unspecified") != module.get_version():
                message += f"{tool_id}: using version '{module.get_version()}' instead of version '{d.get('tool_version', 'Unspecified')}' specified in this workflow."
            if message:
                log.debug(message)
                module.version_changes.append(message)
        return module

    @classmethod
    def from_workflow_step(Class, trans, step, **kwds):
        tool_version = step.tool_version
        tool_uuid = step.tool_uuid
        kwds["exact_tools"] = False
        module = super().from_workflow_step(
            trans, step, tool_id=step.tool_id, tool_version=tool_version, tool_uuid=tool_uuid, **kwds
        )
        module.workflow_outputs = step.workflow_outputs
        module.post_job_actions = {}
        for pja in step.post_job_actions:
            module.post_job_actions[pja.action_type] = pja
        if module.tool:
            message = ""
            if (
                step.tool_id
                and step.tool_id != module.tool.id
                or step.tool_version
                and step.tool_version != module.tool.version
            ):  # This means the exact version of the tool is not installed. We inform the user.
                old_tool_shed = step.tool_id.split("/repos/")[0]
                if (
                    old_tool_shed not in module.tool.id
                ):  # Only display the following warning if the tool comes from a different tool shed
                    old_tool_shed_url = get_tool_shed_url_from_tool_shed_registry(trans.app, old_tool_shed)
                    if (
                        not old_tool_shed_url
                    ):  # a tool from a different tool_shed has been found, but the original tool shed has been deactivated
                        old_tool_shed_url = f"http://{old_tool_shed}"  # let's just assume it's either http, or a http is forwarded to https.
                    old_url = f"{old_tool_shed_url}/view/{module.tool.repository_owner}/{module.tool.repository_name}/"
                    new_url = f"{module.tool.sharable_url}/{module.tool.changeset_revision}/"
                    new_tool_shed_url = new_url.split("/view")[0]
                    message += f'The tool \'{module.tool.name}\', version {tool_version} by the owner {module.tool.repository_owner} installed from <a href="{old_url}" target="_blank">{old_tool_shed_url}</a> is not available. '
                    message += f'A derivation of this tool installed from <a href="{new_url}" target="_blank">{new_tool_shed_url}</a> will be used instead. '
            if step.tool_version and (
                step.tool_version != module.tool.version and not get_safe_version(module.tool, step.tool_version)
            ):
                message += f"<span title=\"tool id '{step.tool_id}'\">Using version '{module.tool.version}' instead of version '{step.tool_version}' specified in this workflow. "
            if message:
                log.debug(message)
                module.version_changes.append(message)
        else:
            log.warning(f"The tool '{step.tool_id}' is missing. Cannot build workflow module.")
        return module

    # ---- Saving in various forms ------------------------------------------

    def save_to_step(self, step, detached=False):
        super().save_to_step(step, detached=detached)
        step.tool_id = self.tool_id
        if self.tool:
            step.tool_version = self.get_version()
        else:
            step.tool_version = self.tool_version
        if tool_uuid := getattr(self, "tool_uuid", None):
            step.dynamic_tool = self.trans.app.dynamic_tool_manager.get_tool_by_uuid(tool_uuid)
        if not detached:
            for k, v in self.post_job_actions.items():
                pja = self.__to_pja(k, v, step)
                self.trans.sa_session.add(pja)

    # ---- General attributes ------------------------------------------------

    def get_name(self):
        return self.tool.name if self.tool else self.tool_id

    def get_content_id(self):
        return self.tool.id if self.tool else self.tool_id

    def get_version(self):
        return self.tool.version if self.tool else self.tool_version

    def get_tooltip(self, static_path=None):
        if self.tool and self.tool.raw_help and self.tool.raw_help.format == "restructuredtext":
            host_url = self.trans.url_builder("/")
            static_path = self.trans.url_builder(static_path) if static_path else ""
            return self.tool.help.render(host_url=host_url, static_path=static_path)

    # ---- Configuration time -----------------------------------------------

    def get_errors(self, include_tool_id=False, **kwargs):
        if not self.tool:
            if include_tool_id:
                return f"{self.tool_id} is not installed"
            else:
                return "Tool is not installed"

    def get_inputs(self):
        return self.tool.inputs if self.tool else {}

    def get_all_inputs(self, data_only=False, connectable_only=False):
        if data_only and connectable_only:
            raise Exception("Must specify at most one of data_only and connectable_only as True.")

        inputs = []
        if self.tool:

            def callback(input, prefixed_name, prefixed_label, value=None, **kwargs):
                visible = not hasattr(input, "hidden") or not input.hidden
                input_type = input.type
                is_data = isinstance(input, DataToolParameter) or isinstance(input, DataCollectionToolParameter)
                is_connectable = is_runtime_value(value) and runtime_to_json(value)["__class__"] == "ConnectedValue"
                if data_only:
                    skip = not visible or not is_data
                elif connectable_only:
                    skip = not visible or not (is_data or is_connectable)
                elif isinstance(input, HiddenToolParameter):
                    skip = False
                else:
                    skip = not visible
                if not skip:
                    if isinstance(input, DataToolParameter):
                        inputs.append(
                            dict(
                                name=prefixed_name,
                                label=prefixed_label,
                                multiple=input.multiple,
                                extensions=input.extensions,
                                optional=input.optional,
                                input_type="dataset",
                            )
                        )
                    elif isinstance(input, DataCollectionToolParameter):
                        inputs.append(
                            dict(
                                name=prefixed_name,
                                label=prefixed_label,
                                multiple=input.multiple,
                                input_type="dataset_collection",
                                collection_types=input.collection_types,
                                optional=input.optional,
                                extensions=input.extensions,
                            )
                        )
                    else:
                        inputs.append(
                            dict(
                                name=prefixed_name,
                                label=prefixed_label,
                                multiple=False,
                                input_type="parameter",
                                optional=getattr(input, "optional", False),
                                type=input_type,
                            )
                        )

            visit_input_values(self.tool.inputs, self.state.inputs, callback)
        return inputs

    def get_all_outputs(self, data_only=False):
        data_outputs = []
        if self.tool:
            for name, tool_output in self.tool.outputs.items():
                if filter_output(self.tool, tool_output, self.state.inputs):
                    continue
                extra_kwds = {}
                if isinstance(tool_output, ToolExpressionOutput):
                    extra_kwds["parameter"] = True
                if tool_output.collection:
                    extra_kwds["collection"] = True
                    collection_type = tool_output.structure.collection_type
                    if not collection_type and tool_output.structure.collection_type_from_rules:
                        rule_param = tool_output.structure.collection_type_from_rules
                        if rule_param in self.state.inputs:
                            rules = self.state.inputs[rule_param]
                            if rules:
                                rule_set = RuleSet(rules)
                                collection_type = rule_set.collection_type
                    extra_kwds["collection_type"] = collection_type
                    extra_kwds["collection_type_source"] = tool_output.structure.collection_type_source
                    formats = ["input"]  # TODO: fix
                elif tool_output.format_source is not None:
                    formats = ["input"]  # default to special name "input" which remove restrictions on connections
                else:
                    formats = [tool_output.format]
                for change_format_model in tool_output.change_format:
                    format = change_format_model["format"]
                    if format and format not in formats:
                        formats.append(format)
                if tool_output.label:
                    try:
                        params = make_dict_copy(self.state.inputs)
                        params["on_string"] = "input dataset(s)"
                        params["tool"] = self.tool
                        extra_kwds["label"] = fill_template(
                            tool_output.label, context=params, python_template_version=self.tool.python_template_version
                        )
                    except Exception:
                        pass
                data_outputs.append(
                    dict(name=name, extensions=formats, type=tool_output.output_type, optional=False, **extra_kwds)
                )
        return data_outputs

    def get_config_form(self, step=None):
        if self.tool:
            self.add_dummy_datasets(connections=step and step.input_connections)
            incoming: Dict[str, str] = {}
            params_to_incoming(incoming, self.tool.inputs, self.state.inputs, self.trans.app)
            return self.tool.to_json(self.trans, incoming, workflow_building_mode=True)

    def check_and_update_state(self):
        if self.tool:
            return self.tool.check_and_update_param_values(self.state.inputs, self.trans, workflow_building_mode=True)

    def add_dummy_datasets(self, connections=None, steps=None):
        if self.tool:
            if connections:
                # Store connections by input name
                input_connections_by_name = {conn.input_name: conn for conn in connections}
            else:
                input_connections_by_name = {}

            # Any input needs to have value RuntimeValue or obtain the value from connected steps
            def callback(input, prefixed_name, context, **kwargs):
                input_type = input.type
                is_data = input_type in ["data", "data_collection"]
                if (
                    is_data
                    and connections is not None
                    and steps is not None
                    and self.trans.workflow_building_mode is workflow_building_modes.USE_HISTORY
                ):
                    if prefixed_name in input_connections_by_name:
                        return ConnectedValue()
                    else:
                        return input.get_initial_value(self.trans, context)
                elif (is_data and connections is None) or prefixed_name in input_connections_by_name:
                    return ConnectedValue()

            visit_input_values(self.tool.inputs, self.state.inputs, callback)
        else:
            raise ToolMissingException(f"Tool {self.tool_id} missing. Cannot add dummy datasets.", tool_id=self.tool_id)

    def get_post_job_actions(self, incoming):
        return ActionBox.handle_incoming(incoming)

    # ---- Run time ---------------------------------------------------------

    def recover_state(self, state, **kwds):
        """Recover state `dict` from simple dictionary describing configuration
        state (potentially from persisted step state).

        Sub-classes should supply a `default_state` method which contains the
        initial state `dict` with key, value pairs for all available attributes.
        """
        super().recover_state(state, **kwds)
        if kwds.get("fill_defaults", False) and self.tool:
            self.compute_runtime_state(self.trans, step=None, step_updates=None)
            self.augment_tool_state_for_input_connections(**kwds)
            self.tool.check_and_update_param_values(self.state.inputs, self.trans, workflow_building_mode=True)

    def augment_tool_state_for_input_connections(self, **kwds):
        """Update tool state to accommodate specified input connections.

        Top-level and conditional inputs will automatically get populated with connected
        data outputs at runtime, but if there are not enough repeat instances in the tool
        state - the runtime replacement code will never visit the input elements it needs
        to in order to connect the data parameters to the tool state. This code then
        populates the required repeat instances in the tool state in order for these
        instances to be visited and inputs properly connected at runtime. I believe
        this should be run before check_and_update_param_values in recover_state so non-data
        parameters are properly populated with default values. The need to populate
        defaults is why this is done here instead of at runtime - but this might also
        be needed at runtime at some point (for workflows installed before their corresponding
        tools?).

        See the test case test_inputs_to_steps for an example of a workflow test
        case that exercises this code.
        """

        # Ensure any repeats defined only by input_connections are populated.
        input_connections = kwds.get("input_connections", {})
        expected_replacement_keys = input_connections.keys()

        def augment(expected_replacement_key, inputs_states):
            if self.tool is None:
                raise ToolMissingException(
                    f"Tool {self.tool_id} missing. Cannot augment tool state for input connections.",
                    tool_id=self.tool_id,
                )
            if "|" not in expected_replacement_key:
                return

            prefix, rest = expected_replacement_key.split("|", 1)
            if "_" not in prefix:
                return

            repeat_name, index = prefix.rsplit("_", 1)
            if not index.isdigit():
                return

            index = int(index)
            repeat = self.tool.inputs[repeat_name]
            if repeat.type != "repeat":
                return

            if repeat_name not in inputs_states:
                inputs_states[repeat_name] = []

            repeat_values = inputs_states[repeat_name]
            repeat_instance_state = None
            while index >= len(repeat_values):
                repeat_instance_state = {"__index__": len(repeat_values)}
                repeat_values.append(repeat_instance_state)

            if repeat_instance_state:
                # TODO: untest branch - no test case for nested repeats yet...
                augment(rest, repeat_instance_state)

        for expected_replacement_key in expected_replacement_keys:
            inputs_states = self.state.inputs
            augment(expected_replacement_key, inputs_states)

    def get_runtime_state(self):
        state = DefaultToolState()
        state.inputs = self.state.inputs
        return state

    def get_runtime_inputs(self, step, connections: Optional[Iterable[WorkflowStepConnection]] = None):
        return self.get_inputs()

    def compute_runtime_state(self, trans, step=None, step_updates=None, replace_default_values=False):
        # Warning: This method destructively modifies existing step state.
        if self.tool:
            step_errors = {}
            state = self.state
            state, step_errors = super().compute_runtime_state(
                trans, step, step_updates, replace_default_values=replace_default_values
            )
            if step_updates:
                self.runtime_post_job_actions = step_updates.get(RUNTIME_POST_JOB_ACTIONS_KEY, {})
                step_metadata_runtime_state = self.__step_meta_runtime_state()
                if step_metadata_runtime_state:
                    state.inputs[RUNTIME_STEP_META_STATE_KEY] = step_metadata_runtime_state
            return state, step_errors
        else:
            raise ToolMissingException(
                f"Tool {self.tool_id} missing. Cannot compute runtime state.", tool_id=self.tool_id
            )

    def decode_runtime_state(self, step, runtime_state):
        """Take runtime state from persisted invocation and convert it
        into a DefaultToolState object for use during workflow invocation.
        """
        if self.tool:
            state = super().decode_runtime_state(step, runtime_state)
            if RUNTIME_STEP_META_STATE_KEY in runtime_state:
                self.__restore_step_meta_runtime_state(json.loads(runtime_state[RUNTIME_STEP_META_STATE_KEY]))
            return state
        else:
            raise ToolMissingException(
                f"Tool {self.tool_id} missing. Cannot recover runtime state.", tool_id=self.tool_id
            )

    def execute(
        self,
        trans,
        progress: "WorkflowProgress",
        invocation_step: "WorkflowInvocationStep",
        use_cached_job: bool = False,
    ) -> Optional[bool]:
        invocation = invocation_step.workflow_invocation
        step = invocation_step.workflow_step
        tool = trans.app.toolbox.get_tool(step.tool_id, tool_version=step.tool_version, tool_uuid=step.tool_uuid)
        if not tool.is_workflow_compatible:
            # TODO: why do we even create an invocation, seems like something we could check on submit?
            message = f"Specified tool [{tool.id}] in step {step.order_index + 1} is not workflow-compatible."
            raise exceptions.MessageException(message)
        self.state, _ = self.compute_runtime_state(
            trans, step, step_updates=progress.param_map.get(step.id), replace_default_values=True
        )
        step.state = self.state
        tool_state = step.state
        assert tool_state is not None
        tool_inputs = tool.inputs.copy()
        # Not strictly needed - but keep Tool state clean by stripping runtime
        # metadata parameters from it.
        if RUNTIME_STEP_META_STATE_KEY in tool_state.inputs:
            del tool_state.inputs[RUNTIME_STEP_META_STATE_KEY]

        all_inputs = self.get_all_inputs()

        all_inputs_by_name = {}
        for input_dict in all_inputs:
            all_inputs_by_name[input_dict["name"]] = input_dict
        collection_info = self.compute_collection_info(progress, step, all_inputs)

        param_combinations = []
        if collection_info:
            iteration_elements_iter = collection_info.slice_collections()
        else:
            if progress.when_values:
                assert len(progress.when_values) == 1, "Got more than 1 when value, this shouldn't be possible"
            iteration_elements_iter = [(None, progress.when_values[0] if progress.when_values else None)]

        resource_parameters = invocation.resource_parameters
        for iteration_elements, when_value in iteration_elements_iter:
            execution_state = tool_state.copy()
            # TODO: Move next step into copy()
            execution_state.inputs = make_dict_copy(execution_state.inputs)

            expected_replacement_keys = set(step.input_connections_by_name.keys())
            found_replacement_keys = set()

            # Connect up
            def callback(input, prefixed_name: str, **kwargs):
                input_dict = all_inputs_by_name[prefixed_name]

                replacement: Union[model.Dataset, NoReplacement] = NO_REPLACEMENT
                if iteration_elements and prefixed_name in iteration_elements:  # noqa: B023
                    replacement = iteration_elements[prefixed_name]  # noqa: B023
                else:
                    replacement = progress.replacement_for_input(trans, step, input_dict)

                if replacement is not NO_REPLACEMENT:
                    if not isinstance(input, BaseDataToolParameter):
                        # Probably a parameter that can be replaced
                        dataset_instance: Optional[model.DatasetInstance] = None
                        if isinstance(replacement, model.DatasetCollectionElement):
                            dataset_instance = replacement.hda
                        elif isinstance(replacement, model.DatasetInstance):
                            dataset_instance = replacement
                        if dataset_instance and dataset_instance.extension == "expression.json":
                            with open(dataset_instance.get_file_name()) as f:
                                replacement = json.load(f)
                    found_replacement_keys.add(prefixed_name)  # noqa: B023

                    # bool cast should be fine, can only have true/false on ConditionalStepWhen
                    # also terrible of course and it's not needed for API requests
                    if isinstance(input, ConditionalStepWhen) and bool(replacement) is False:
                        raise SkipWorkflowStepEvaluation

                return replacement

            try:
                # Replace DummyDatasets with historydatasetassociations
                visit_input_values(
                    tool_inputs,
                    execution_state.inputs,
                    callback,
                    no_replacement_value=NO_REPLACEMENT,
                    replace_optional_connections=True,
                )
            except KeyError as k:
                message = f"Error due to input mapping of '{unicodify(k)}' in tool '{tool.id}'.  A common cause of this is conditional outputs that cannot be determined until runtime, please review workflow step {step.order_index + 1}."
                raise exceptions.MessageException(message)

            if step.when_expression and when_value is not False:
                extra_step_state = {}
                for step_input in step.inputs:
                    step_input_name = step_input.name
                    input_in_execution_state = step_input_name not in execution_state.inputs
                    if input_in_execution_state:
                        if step_input_name in all_inputs_by_name:
                            if iteration_elements and step_input_name in iteration_elements:  # noqa: B023
                                value = iteration_elements[step_input_name]  # noqa: B023
                            else:
                                value = progress.replacement_for_input(trans, step, all_inputs_by_name[step_input_name])
                            # TODO: only do this for values... is everything with a default
                            # this way a field parameter? I guess not?
                            extra_step_state[step_input_name] = value
                        # Might be needed someday...
                        # elif step_input.default_value_set:
                        #    extra_step_state[step_input_name] = step_input.default_value
                        else:
                            if iteration_elements and step_input_name in iteration_elements:  # noqa: B023
                                value = iteration_elements[step_input_name]  # noqa: B023
                            else:
                                value = progress.replacement_for_connection(step_input.connections[0], is_data=True)
                            extra_step_state[step_input_name] = value

                if when_value is not False:
                    when_value = evaluate_value_from_expressions(
                        progress, step, execution_state=execution_state, extra_step_state=extra_step_state
                    )
            if when_value is not None:
                # Track this more formally ?
                execution_state.inputs["__when_value__"] = when_value

            unmatched_input_connections = expected_replacement_keys - found_replacement_keys
            if unmatched_input_connections:
                log.warning(f"Failed to use input connections for inputs [{unmatched_input_connections}]")

            param_combinations.append(execution_state.inputs)

        complete = False
        completed_jobs: Dict[int, Optional[Job]] = tool.completed_jobs(
            trans,
            use_cached_job,
            param_combinations,
        )
        try:
            mapping_params = MappingParameters(tool_state.inputs, param_combinations)
            if use_cached_job:
                mapping_params.param_template["__use_cached_job__"] = use_cached_job
            max_num_jobs = progress.maximum_jobs_to_schedule_or_none

            validate_outputs = False
            for pja in step.post_job_actions:
                if pja.action_type == "ValidateOutputsAction":
                    validate_outputs = True

            execution_tracker = execute(
                trans=self.trans,
                tool=tool,
                mapping_params=mapping_params,
                history=invocation.history,
                collection_info=collection_info,
                workflow_invocation_uuid=invocation.uuid.hex if invocation.uuid else None,
                invocation_step=invocation_step,
                max_num_jobs=max_num_jobs,
                validate_outputs=validate_outputs,
                job_callback=lambda job: self._handle_post_job_actions(
                    step, job, progress.effective_replacement_dict()
                ),
                completed_jobs=completed_jobs,
                workflow_resource_parameters=resource_parameters,
            )
            complete = True
        except PartialJobExecution as pje:
            execution_tracker = pje.execution_tracker

        except ToolInputsNotReadyException:
            delayed_why = f"tool [{tool.id}] inputs are not ready, this special tool requires inputs to be ready"
            raise DelayedWorkflowEvaluation(why=delayed_why)

        progress.record_executed_job_count(len(execution_tracker.successful_jobs))
        step_outputs: Dict[str, Union[model.HistoryDatasetCollectionAssociation, model.HistoryDatasetAssociation]] = {}
        if collection_info:
            step_outputs.update(execution_tracker.implicit_collections)
        else:
            step_outputs.update(execution_tracker.output_datasets)
            step_outputs.update(execution_tracker.output_collections)
        progress.set_step_outputs(invocation_step, step_outputs, already_persisted=not invocation_step.is_new)

        if collection_info:
            step_inputs = mapping_params.param_template
            step_inputs.update(collection_info.collections)

            self._handle_mapped_over_post_job_actions(
                step, step_inputs, step_outputs, progress.effective_replacement_dict()
            )
            if progress.when_values == [False] and not progress.subworkflow_collection_info:
                # Step skipped entirely. We hide the output to avoid confusion.
                # Could be revisited if we have a nice visual way to say these are skipped ?
                for output in step_outputs.values():
                    if isinstance(output, (model.HistoryDatasetAssociation, model.HistoryDatasetCollectionAssociation)):
                        output.visible = False

        if execution_tracker.execution_errors:
            # TODO: formalize into InvocationFailure ?
            message = f"Failed to create {len(execution_tracker.execution_errors)} job(s) for workflow step {step.order_index + 1}: {str(execution_tracker.execution_errors[0])}"
            for error in execution_tracker.execution_errors:
                # try first to raise a structured invocation error message
                if isinstance(error, exceptions.ToolInputsNotOKException) and error.src == "hda":
                    raise FailWorkflowEvaluation(
                        why=InvocationFailureDatasetFailed(
                            reason=FailureReason.dataset_failed,
                            hda_id=error.id,
                            workflow_step_id=step.id,
                        )
                    )
            raise exceptions.MessageException(message)

        return complete

    def _effective_post_job_actions(self, step):
        effective_post_job_actions = step.post_job_actions[:]
        for key, value in self.runtime_post_job_actions.items():
            effective_post_job_actions.append(self.__to_pja(key, value, None))
        return effective_post_job_actions

    def _handle_mapped_over_post_job_actions(self, step, step_inputs, step_outputs, replacement_dict):
        effective_post_job_actions = self._effective_post_job_actions(step)
        for pja in effective_post_job_actions:
            if pja.action_type in ActionBox.mapped_over_output_actions:
                ActionBox.execute_on_mapped_over(
                    self.trans, self.trans.sa_session, pja, step_inputs, step_outputs, replacement_dict
                )

    def _handle_post_job_actions(self, step, job, replacement_dict):
        # Create new PJA associations with the created job, to be run on completion.
        # PJA Parameter Replacement (only applies to immediate actions-- rename specifically, for now)
        # Pass along replacement dict with the execution of the PJA so we don't have to modify the object.

        # Combine workflow and runtime post job actions into the effective post
        # job actions for this execution.
        effective_post_job_actions = self._effective_post_job_actions(step)
        for pja in effective_post_job_actions:
            if pja.action_type in ActionBox.immediate_actions or isinstance(self.tool, DatabaseOperationTool):
                ActionBox.execute(self.trans.app, self.trans.sa_session, pja, job, replacement_dict)
            else:
                if job.id:
                    pjaa = model.PostJobActionAssociation(pja, job_id=job.id)
                else:
                    pjaa = model.PostJobActionAssociation(pja, job=job)
                self.trans.sa_session.add(pjaa)

    def __restore_step_meta_runtime_state(self, step_runtime_state):
        if RUNTIME_POST_JOB_ACTIONS_KEY in step_runtime_state:
            self.runtime_post_job_actions = step_runtime_state[RUNTIME_POST_JOB_ACTIONS_KEY]

    def __step_meta_runtime_state(self):
        """Build a dictionary a of meta-step runtime state (state about how
        the workflow step - not the tool state) to be serialized with the Tool
        state.
        """
        return {RUNTIME_POST_JOB_ACTIONS_KEY: self.runtime_post_job_actions}

    def __to_pja(self, key, value, step):
        if "output_name" in value:
            output_name = value["output_name"]
        else:
            output_name = None
        if "action_arguments" in value:
            action_arguments = value["action_arguments"]
        else:
            action_arguments = None
        return PostJobAction(value["action_type"], step, output_name, action_arguments)

    def get_informal_replacement_parameters(self, step: WorkflowStep) -> List[str]:
        """Return a list of replacement parameters."""
        replacement_parameters = set()
        for pja in step.post_job_actions:
            if action_arguments := pja.action_arguments:
                for argument in action_arguments.values():
                    for match in re.findall(r"\$\{(.+?)\}", unicodify(argument)):
                        replacement_parameters.add(match)

        return list(replacement_parameters)


class WorkflowModuleFactory:
    def __init__(self, module_types: Dict[str, Type[WorkflowModule]]):
        self.module_types = module_types

    def from_dict(self, trans, d, **kwargs) -> WorkflowModule:
        """
        Return module initialized from the data in dictionary `d`.
        """
        type = d["type"]
        assert (
            type in self.module_types
        ), f"Unexpected workflow step type [{type}] not found in [{self.module_types.keys()}]"
        return self.module_types[type].from_dict(trans, d, **kwargs)

    def from_workflow_step(self, trans, step: WorkflowStep, **kwargs) -> WorkflowModule:
        """
        Return module initialized from the WorkflowStep object `step`.
        """
        type = step.type
        assert type
        return self.module_types[type].from_workflow_step(trans, step, **kwargs)


module_types = dict(
    data_input=InputDataModule,
    data_collection_input=InputDataCollectionModule,
    parameter_input=InputParameterModule,
    pause=PauseModule,
    tool=ToolModule,
    subworkflow=SubWorkflowModule,
)
module_factory = WorkflowModuleFactory(module_types)


def load_module_sections(trans):
    """Get abstract description of the workflow modules this Galaxy instance
    is configured with.
    """
    module_sections = {}

    if trans.app.config.enable_beta_workflow_modules:
        module_sections["experimental"] = {
            "name": "experimental",
            "title": "Experimental",
            "modules": [
                {"name": "pause", "title": "Pause Workflow for Dataset Review", "description": "Pause for Review"}
            ],
        }

    return module_sections


class DelayedWorkflowEvaluation(Exception):
    def __init__(self, why=None):
        self.why = why


class CancelWorkflowEvaluation(Exception):
    def __init__(self, why: "InvocationMessageUnion"):
        self.why = why


class FailWorkflowEvaluation(Exception):
    def __init__(self, why: "InvocationMessageUnion"):
        self.why = why


class SkipWorkflowStepEvaluation(Exception):
    pass


class WorkflowModuleInjector:
    """Injects workflow step objects from the ORM with appropriate module and
    module generated/influenced state."""

    def __init__(self, trans, allow_tool_state_corrections=False):
        self.trans = trans
        self.allow_tool_state_corrections = allow_tool_state_corrections

    def inject(self, step: WorkflowStep, step_args=None, steps=None, allow_tool_state_corrections=False, **kwargs):
        """Pre-condition: `step` is an ORM object coming from the database, if
        supplied `step_args` is the representation of the inputs for that step
        supplied via web form.

        Post-condition: The supplied `step` has new non-persistent attributes
        useful during workflow invocation. These include 'upgrade_messages',
        'state', 'input_connections_by_name', and 'module'.

        If step_args is provided from a web form this is applied to generate
        'state' else it is just obtained from the database.
        """
        step.upgrade_messages = {}

        # Make connection information available on each step by input name.
        step.setup_input_connections_by_name()

        # Populate module.
        module = step.module = module_factory.from_workflow_step(self.trans, step, **kwargs)

        # Any connected input needs to have value DummyDataset (these
        # are not persisted so we need to do it every time)
        module.add_dummy_datasets(connections=step.input_connections, steps=steps)

        # Populate subworkflow components
        if step.type == "subworkflow":
            subworkflow_param_map = step_args or {}
            unjsonified_subworkflow_param_map = {}
            for key, value in subworkflow_param_map.items():
                unjsonified_subworkflow_param_map[int(key)] = value

            subworkflow = step.subworkflow
            assert subworkflow
            populate_module_and_state(
                self.trans,
                subworkflow,
                param_map=unjsonified_subworkflow_param_map,
                allow_tool_state_corrections=allow_tool_state_corrections,
            )

    def inject_all(self, workflow: Workflow, param_map=None, ignore_tool_missing_exception=False, **kwargs):
        param_map = param_map or {}
        for step in workflow.steps:
            step_args = param_map.get(step.id, {})
            try:
                self.inject(step, steps=workflow.steps, step_args=step_args, **kwargs)
            except ToolMissingException:
                if not ignore_tool_missing_exception:
                    raise

    def compute_runtime_state(self, step: WorkflowStep, step_args=None):
        assert step.module, "module must be injected before computing runtime state"
        state, step_errors = step.module.compute_runtime_state(self.trans, step, step_args)
        step.state = state

        # Fix any missing parameters
        step.upgrade_messages = step.module.check_and_update_state()

        return step_errors


def populate_module_and_state(
    trans, workflow: Workflow, param_map, allow_tool_state_corrections=False, module_injector=None
):
    """Used by API but not web controller, walks through a workflow's steps
    and populates transient module and state attributes on each.
    """
    if module_injector is None:
        module_injector = WorkflowModuleInjector(trans, allow_tool_state_corrections)
    module_injector.inject_all(workflow, param_map=param_map)
    for step in workflow.steps:
        step_args = param_map.get(step.id, {})
        step_errors = module_injector.compute_runtime_state(step, step_args=step_args)
        if step_errors:
            raise exceptions.MessageException(
                "Error computing workflow step runtime state", err_data={step.order_index: step_errors}
            )
        if step.upgrade_messages:
            if allow_tool_state_corrections:
                log.debug('Workflow step "%i" had upgrade messages: %s', step.id, step.upgrade_messages)
            else:
                raise exceptions.MessageException(
                    "Workflow step has upgrade messages", err_data={step.order_index: step.upgrade_messages}
                )

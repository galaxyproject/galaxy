"""
Modules used in building workflows
"""
import logging
import re
from json import loads
from xml.etree.ElementTree import (
    Element,
    XML
)

from galaxy import (
    exceptions,
    model,
    web
)
from galaxy.dataset_collections import matching
from galaxy.exceptions import ToolMissingException
from galaxy.jobs.actions.post import ActionBox
from galaxy.model import PostJobAction
from galaxy.tools import (
    DefaultToolState,
    ToolInputsNotReadyException
)
from galaxy.tools.execute import execute, MappingParameters, PartialJobExecution
from galaxy.tools.parameters import (
    check_param,
    params_to_incoming,
    visit_input_values
)
from galaxy.tools.parameters.basic import (
    BooleanToolParameter,
    ConnectedValue,
    DataCollectionToolParameter,
    DataToolParameter,
    is_runtime_value,
    parameter_types,
    runtime_to_json,
    SelectToolParameter,
    TextToolParameter,
    workflow_building_modes
)
from galaxy.tools.parameters.history_query import HistoryQuery
from galaxy.tools.parameters.wrapped import make_dict_copy
from galaxy.util.bunch import Bunch
from galaxy.util.json import safe_loads
from galaxy.util.odict import odict
from galaxy.util.rules_dsl import RuleSet
from galaxy.util.template import fill_template
from tool_shed.util import common_util

log = logging.getLogger(__name__)

# Key into Tool state to describe invocation-specific runtime properties.
RUNTIME_STEP_META_STATE_KEY = "__STEP_META_STATE__"
# Key into step runtime state dict describing invocation-specific post job
# actions (i.e. PJA specified at runtime on top of the workflow-wide defined
# ones.
RUNTIME_POST_JOB_ACTIONS_KEY = "__POST_JOB_ACTIONS__"


class NoReplacement(object):

    def __str__(self):
        return "NO_REPLACEMENT singleton"


NO_REPLACEMENT = NoReplacement()


class WorkflowModule(object):

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
        module.recover_state(step.tool_inputs)
        module.label = step.label
        return module

    # ---- Saving in various forms ------------------------------------------

    def save_to_step(self, step):
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
        """ If this component has an identifier external to the step (such
        as a tool or another workflow) return the identifier for that content.
        """
        return None

    def get_tooltip(self, static_path=''):
        return None

    # ---- Configuration time -----------------------------------------------

    def get_state(self, nested=True):
        """ Return a serializable representation of the persistable state of
        the step.
        """
        inputs = self.get_inputs()
        if inputs:
            return self.state.encode(Bunch(inputs=inputs), self.trans.app, nested=nested)
        else:
            return self.state.inputs

    def recover_state(self, state, **kwds):
        """ Recover state `dict` from simple dictionary describing configuration
        state (potentially from persisted step state).

        Sub-classes should supply a `default_state` method which contains the
        initial state `dict` with key, value pairs for all available attributes.
        """
        self.state = DefaultToolState()
        inputs = self.get_inputs()
        if inputs:
            self.state.decode(state, Bunch(inputs=inputs), self.trans.app)
        else:
            self.state.inputs = safe_loads(state) or {}

    def get_errors(self, **kwargs):
        """ This returns a step related error message as string or None """
        return None

    def get_inputs(self):
        """ This returns inputs displayed in the workflow editor """
        return {}

    def get_all_inputs(self, data_only=False, connectable_only=False):
        return []

    def get_data_inputs(self):
        """ Get configure time data input descriptions. """
        return self.get_all_inputs(data_only=True)

    def get_all_outputs(self, data_only=False):
        return []

    def get_data_outputs(self):
        return self.get_all_outputs(data_only=True)

    def get_post_job_actions(self, incoming):
        return []

    def check_and_update_state(self):
        """
        If the state is not in sync with the current implementation of the
        module, try to update. Returns a list of messages to be displayed
        """
        pass

    def add_dummy_datasets(self, connections=None, steps=None):
        """ Replace connected inputs with placeholder/dummy values. """
        pass

    def get_config_form(self, step=None):
        """ Serializes input parameters of a module into input dictionaries. """
        return {
            'title' : self.name,
            'inputs': [param.to_dict(self.trans) for param in self.get_inputs().values()]
        }

    # ---- Run time ---------------------------------------------------------

    def get_runtime_state(self):
        raise TypeError("Abstract method")

    def get_runtime_inputs(self, **kwds):
        """ Used internally by modules and when displaying inputs in workflow
        editor and run workflow templates.
        """
        return {}

    def compute_runtime_state(self, trans, step=None, step_updates=None):
        """ Determine the runtime state (potentially different from self.state
        which describes configuration state). This (again unlike self.state) is
        currently always a `DefaultToolState` object.

        If `step` is not `None`, it will be used to search for default values
        defined in workflow input steps.

        If `step_updates` is `None`, this is likely for rendering the run form
        for instance and no runtime properties are available and state must be
        solely determined by the default runtime state described by the step.

        If `step_updates` are available they describe the runtime properties
        supplied by the workflow runner.
        """
        state = self.get_runtime_state()
        step_errors = {}

        if step is not None:

            def update_value(input, context, prefixed_name, **kwargs):
                step_input = step.get_input(prefixed_name)
                if step_input is None:
                    return NO_REPLACEMENT

                if step_input.default_value_set:
                    return step_input.default_value

                return NO_REPLACEMENT

            visit_input_values(self.get_runtime_inputs(), state.inputs, update_value, no_replacement_value=NO_REPLACEMENT)

        if step_updates:

            def update_value(input, context, prefixed_name, **kwargs):
                if prefixed_name in step_updates:
                    value, error = check_param(trans, input, step_updates.get(prefixed_name), context)
                    if error is not None:
                        step_errors[prefixed_name] = error
                    return value
                return NO_REPLACEMENT

            visit_input_values(self.get_runtime_inputs(), state.inputs, update_value, no_replacement_value=NO_REPLACEMENT)

        return state, step_errors

    def encode_runtime_state(self, runtime_state):
        """ Takes the computed runtime state and serializes it during run request creation. """
        return runtime_state.encode(Bunch(inputs=self.get_runtime_inputs()), self.trans.app)

    def decode_runtime_state(self, runtime_state):
        """ Takes the serialized runtime state and decodes it when running the workflow. """
        state = DefaultToolState()
        state.decode(runtime_state, Bunch(inputs=self.get_runtime_inputs()), self.trans.app)
        return state

    def execute(self, trans, progress, invocation_step, use_cached_job=False):
        """ Execute the given workflow invocation step.

        Use the supplied workflow progress object to track outputs, find
        inputs, etc....

        Return a False if there is additional processing required to
        on subsequent workflow scheduling runs, None or True means the workflow
        step executed properly.
        """
        raise TypeError("Abstract method")

    def do_invocation_step_action(self, step, action):
        """ Update or set the workflow invocation state action - generic
        extension point meant to allows users to interact with interactive
        workflow modules. The action object returned from this method will
        be attached to the WorkflowInvocationStep and be available the next
        time the workflow scheduler visits the workflow.
        """
        raise exceptions.RequestParameterInvalidException("Attempting to perform invocation step action on module that does not support actions.")

    def recover_mapping(self, invocation_step, progress):
        """ Re-populate progress object with information about connections
        from previously executed steps recorded via invocation_steps.
        """
        outputs = {}

        for output_dataset_assoc in invocation_step.output_datasets:
            outputs[output_dataset_assoc.output_name] = output_dataset_assoc.dataset

        for output_dataset_collection_assoc in invocation_step.output_dataset_collections:
            outputs[output_dataset_collection_assoc.output_name] = output_dataset_collection_assoc.dataset_collection

        progress.set_step_outputs(invocation_step, outputs, already_persisted=True)

    def get_replacement_parameters(self, step):
        """Return a list of replacement parameters."""

        return []

    def compute_collection_info(self, progress, step, all_inputs):
        """Use get_all_inputs (if implemented) to determine collection mapping for execution.

        Hopefully this can be reused for Tool and Subworkflow modules.
        """

        collections_to_match = self._find_collections_to_match(
            progress, step, all_inputs
        )
        # Have implicit collections...
        if collections_to_match.has_collections():
            collection_info = self.trans.app.dataset_collections_service.match_collections(
                collections_to_match
            )
        else:
            collection_info = None

        return collection_info

    def _find_collections_to_match(self, progress, step, all_inputs):
        collections_to_match = matching.CollectionsToMatch()
        dataset_collection_type_descriptions = self.trans.app.dataset_collections_service.collection_type_descriptions

        for input_dict in all_inputs:
            name = input_dict["name"]
            data = progress.replacement_for_input(step, input_dict)
            can_map_over = hasattr(data, "collection")  # and data.collection.allow_implicit_mapping

            if not can_map_over:
                continue

            is_data_param = input_dict["input_type"] == "dataset"
            if is_data_param:
                multiple = input_dict["multiple"]
                if multiple:
                    # multiple="true" data input, acts like "list" collection_type.
                    # just need to figure out subcollection_type_description
                    history_query = HistoryQuery.from_collection_types(
                        ['list'],
                        dataset_collection_type_descriptions,
                    )
                    subcollection_type_description = history_query.can_map_over(data)
                    if subcollection_type_description:
                        collections_to_match.add(name, data, subcollection_type=subcollection_type_description)
                else:
                    collections_to_match.add(name, data)
                continue

            is_data_collection_param = input_dict["input_type"] == "dataset_collection"
            if is_data_collection_param:
                history_query = HistoryQuery.from_collection_types(
                    input_dict.get("collection_types", None),
                    dataset_collection_type_descriptions,
                )
                subcollection_type_description = history_query.can_map_over(data)
                if subcollection_type_description:
                    collections_to_match.add(name, data, subcollection_type=subcollection_type_description.collection_type)
                continue

            if data is not NO_REPLACEMENT:
                collections_to_match.add(name, data)
                continue

        return collections_to_match


class SubWorkflowModule(WorkflowModule):
    # Two step improvements to build runtime inputs for subworkflow modules
    # - First pass verify nested workflow doesn't have an RuntimeInputs
    # - Second pass actually turn RuntimeInputs into inputs if possible.
    type = "subworkflow"
    name = "Subworkflow"

    @classmethod
    def from_dict(Class, trans, d, **kwds):
        module = super(SubWorkflowModule, Class).from_dict(trans, d, **kwds)
        if "subworkflow" in d:
            module.subworkflow = d["subworkflow"]
        elif "content_id" in d:
            from galaxy.managers.workflows import WorkflowsManager
            module.subworkflow = WorkflowsManager(trans.app).get_owned_workflow(trans, d["content_id"])
        else:
            raise Exception("Step associated subworkflow could not be found.")
        return module

    @classmethod
    def from_workflow_step(Class, trans, step, **kwds):
        module = super(SubWorkflowModule, Class).from_workflow_step(trans, step, **kwds)
        module.subworkflow = step.subworkflow
        return module

    def save_to_step(self, step):
        step.type = self.type
        step.subworkflow = self.subworkflow

    def get_name(self):
        if hasattr(self.subworkflow, 'name'):
            return self.subworkflow.name
        return self.name

    def get_all_inputs(self, data_only=False, connectable_only=False):
        """ Get configure time data input descriptions. """
        # Filter subworkflow steps and get inputs
        step_to_input_type = {
            "data_input": "dataset",
            "data_collection_input": "dataset_collection",
            "parameter_input": "parameter",
        }
        inputs = []
        if hasattr(self.subworkflow, 'input_steps'):
            for step in self.subworkflow.input_steps:
                name = step.label
                if not name:
                    step_module = module_factory.from_workflow_step(self.trans, step)
                    name = "%s:%s" % (step.order_index, step_module.get_name())
                step_type = step.type
                assert step_type in step_to_input_type
                input = dict(
                    input_subworkflow_step_id=step.order_index,
                    name=name,
                    label=name,
                    multiple=False,
                    extensions=["data"],
                    input_type=step_to_input_type[step_type],
                )
                if step.type == 'data_collection_input':
                    input['collection_type'] = step.tool_inputs.get('collection_type') if step.tool_inputs else None
                inputs.append(input)
        return inputs

    def get_modules(self):
        return [module_factory.from_workflow_step(self.trans, step) for step in self.subworkflow.steps]

    def get_errors(self, **kwargs):
        errors = (module.get_errors(include_tool_id=True) for module in self.get_modules())
        errors = [e for e in errors if e]
        if any(errors):
            return errors
        return None

    def get_all_outputs(self, data_only=False):
        outputs = []
        if hasattr(self.subworkflow, 'workflow_outputs'):
            from galaxy.managers.workflows import WorkflowContentsManager
            workflow_contents_manager = WorkflowContentsManager(self.trans.app)
            subworkflow_dict = workflow_contents_manager._workflow_to_dict_editor(trans=self.trans,
                                                                                  stored=self.subworkflow.stored_workflow,
                                                                                  workflow=self.subworkflow,
                                                                                  tooltip=False,
                                                                                  is_subworkflow=True)
            for order_index in sorted(subworkflow_dict['steps']):
                step = subworkflow_dict['steps'][order_index]
                data_outputs = step['outputs']
                for workflow_output in step['workflow_outputs']:
                    label = workflow_output['label']
                    if not label:
                        label = "%s:%s" % (order_index, workflow_output['output_name'])
                    workflow_output_uuid = workflow_output.get('uuid') or object()
                    for data_output in data_outputs:
                        data_output_uuid = data_output.get('uuid') or object()
                        if data_output['name'] == workflow_output['output_name'] or data_output_uuid == workflow_output_uuid:
                            data_output['label'] = label
                            data_output['name'] = label
                            # That's the right data_output
                            break
                    else:
                        # This can happen when importing workflows with missing tools.
                        # We can't raise an exception here, as that would prevent loading
                        # the workflow.
                        log.error("Workflow output '%s' defined, but not listed among data outputs" % workflow_output['output_name'])
                        continue
                    outputs.append(data_output)
        return outputs

    def get_content_id(self):
        return self.trans.security.encode_id(self.subworkflow.id)

    def execute(self, trans, progress, invocation_step, use_cached_job=False):
        """ Execute the given workflow step in the given workflow invocation.
        Use the supplied workflow progress object to track outputs, find
        inputs, etc...
        """
        step = invocation_step.workflow_step
        subworkflow_invoker = progress.subworkflow_invoker(trans, step, use_cached_job=use_cached_job)
        subworkflow_invoker.invoke()
        subworkflow = subworkflow_invoker.workflow
        subworkflow_progress = subworkflow_invoker.progress
        outputs = {}
        for workflow_output in subworkflow.workflow_outputs:
            workflow_output_label = workflow_output.label or "%s:%s" % (workflow_output.workflow_step.order_index, workflow_output.output_name)
            replacement = subworkflow_progress.get_replacement_workflow_output(workflow_output)
            outputs[workflow_output_label] = replacement
        progress.set_step_outputs(invocation_step, outputs)
        return None

    def get_runtime_state(self):
        state = DefaultToolState()
        state.inputs = dict()
        return state

    def get_runtime_inputs(self, connections=None):
        inputs = {}
        for step in self.subworkflow.steps:
            if step.type == "tool":
                tool = step.module.tool
                tool_inputs = step.module.state

                def callback(input, prefixed_name, prefixed_label, value=None, **kwds):
                    # All data parameters are represented as runtime values, skip them
                    # here.
                    if input.type in ['data', 'data_collection']:
                        return

                    if is_runtime_value(value):
                        input_name = "%d|%s" % (step.order_index, prefixed_name)
                        inputs[input_name] = InputProxy(input, input_name)

                visit_input_values(tool.inputs, tool_inputs.inputs, callback)

        return inputs

    def get_replacement_parameters(self, step):
        """Return a list of replacement parameters."""
        replacement_parameters = set()
        for subworkflow_step in self.subworkflow.steps:
            module = subworkflow_step.module
            for replacement_parameter in module.get_replacement_parameters(subworkflow_step):
                replacement_parameters.add(replacement_parameter)

        return list(replacement_parameters)


class InputProxy(object):
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


class InputModule(WorkflowModule):

    def get_runtime_state(self):
        state = DefaultToolState()
        state.inputs = dict(input=None)
        return state

    def get_all_inputs(self, data_only=False, connectable_only=False):
        return []

    def execute(self, trans, progress, invocation_step, use_cached_job=False):
        invocation = invocation_step.workflow_invocation
        step = invocation_step.workflow_step
        step_outputs = dict(output=step.state.inputs['input'])

        # Web controller may set copy_inputs_to_history, API controller always sets
        # inputs.
        if invocation.copy_inputs_to_history:
            for input_dataset_hda in list(step_outputs.values()):
                content_type = input_dataset_hda.history_content_type
                if content_type == "dataset":
                    new_hda = input_dataset_hda.copy()
                    invocation.history.add_dataset(new_hda)
                    step_outputs['input_ds_copy'] = new_hda
                elif content_type == "dataset_collection":
                    new_hdca = input_dataset_hda.copy()
                    invocation.history.add_dataset_collection(new_hdca)
                    step_outputs['input_ds_copy'] = new_hdca
                else:
                    raise Exception("Unknown history content encountered")
        # If coming from UI - we haven't registered invocation inputs yet,
        # so do that now so dependent steps can be recalculated. In the future
        # everything should come in from the API and this can be eliminated.
        if not invocation.has_input_for_step(step.id):
            content = next(iter(step_outputs.values()))
            if content:
                invocation.add_input(content, step.id)
        progress.set_outputs_for_input(invocation_step, step_outputs)

    def recover_mapping(self, invocation_step, progress):
        progress.set_outputs_for_input(invocation_step)


class InputDataModule(InputModule):
    type = "data_input"
    name = "Input dataset"

    def get_all_outputs(self, data_only=False):
        return [dict(name='output', extensions=['input'])]

    def get_filter_set(self, connections=None):
        filter_set = []
        if connections:
            for oc in connections:
                for ic in oc.input_step.module.get_data_inputs():
                    if 'extensions' in ic and ic['extensions'] != 'input' and ic['name'] == oc.input_name:
                        filter_set += ic['extensions']
        if not filter_set:
            filter_set = ['data']
        return ', '.join(filter_set)

    def get_runtime_inputs(self, connections=None):
        return dict(input=DataToolParameter(None, Element("param", name="input", label=self.label, multiple=False, type="data", format=self.get_filter_set(connections)), self.trans))


class InputDataCollectionModule(InputModule):
    type = "data_collection_input"
    name = "Input dataset collection"
    default_collection_type = "list"
    collection_type = default_collection_type

    def get_inputs(self):
        collection_type = self.state.inputs.get("collection_type", self.default_collection_type)
        input_collection_type = TextToolParameter(None, XML(
            '''
            <param name="collection_type" label="Collection type" type="text" value="%s">
                <option value="list">List of Datasets</option>
                <option value="paired">Dataset Pair</option>
                <option value="list:paired">List of Dataset Pairs</option>
            </param>
            ''' % collection_type))
        return dict(collection_type=input_collection_type)

    def get_runtime_inputs(self, **kwds):
        collection_type = self.state.inputs.get("collection_type", self.default_collection_type)
        input_element = Element("param", name="input", label=self.label, type="data_collection", collection_type=collection_type)
        return dict(input=DataCollectionToolParameter(None, input_element, self.trans))

    def get_all_outputs(self, data_only=False):
        return [
            dict(
                name='output',
                extensions=['input_collection'],
                collection=True,
                collection_type=self.state.inputs.get('collection_type', self.default_collection_type)
            )
        ]


class InputParameterModule(WorkflowModule):
    type = "parameter_input"
    name = "Input parameter"
    default_parameter_type = "text"
    default_optional = False
    parameter_type = default_parameter_type
    optional = default_optional

    def get_inputs(self):
        # TODO: Use an external xml or yaml file to load the parameter definition
        parameter_type = self.state.inputs.get("parameter_type", self.default_parameter_type)
        optional = self.state.inputs.get("optional", self.default_optional)
        input_parameter_type = SelectToolParameter(None, XML(
            '''
            <param name="parameter_type" label="Parameter type" type="select">
                <option value="text">Text</option>
                <option value="integer">Integer</option>
                <option value="float">Float</option>
                <option value="boolean">Boolean (True or False)</option>
                <option value="color">Color</option>
            </param>
            '''))
        for i, option in enumerate(input_parameter_type.static_options):
            option = list(option)
            if option[1] == parameter_type:
                # item 0 is option description, item 1 is value, item 2 is "selected"
                option[2] = True
                input_parameter_type.static_options[i] = tuple(option)
        return odict([("parameter_type", input_parameter_type),
                      ("optional", BooleanToolParameter(None, Element("param", name="optional", label="Optional", type="boolean", value=optional)))])

    def get_runtime_inputs(self, **kwds):
        parameter_type = self.state.inputs.get("parameter_type", self.default_parameter_type)
        optional = self.state.inputs.get("optional", self.default_optional)
        if parameter_type not in ["text", "boolean", "integer", "float", "color"]:
            raise ValueError("Invalid parameter type for workflow parameters encountered.")
        parameter_class = parameter_types[parameter_type]
        parameter_kwds = {}
        if parameter_type in ["integer", "float"]:
            parameter_kwds["value"] = str(0)

        # TODO: Use a dict-based description from YAML tool source
        element = Element("param", name="input", label=self.label, type=parameter_type, optional=str(optional), **parameter_kwds)
        input = parameter_class(None, element)
        return dict(input=input)

    def get_runtime_state(self):
        state = DefaultToolState()
        state.inputs = dict(input=None)
        return state

    def get_all_outputs(self, data_only=False):
        if data_only:
            return []

        return [dict(
            name='output',
            label=self.label,
            type=self.state.inputs.get('parameter_type', self.parameter_type),
            parameter=True,
        )]

    def execute(self, trans, progress, invocation_step, use_cached_job=False):
        step = invocation_step.workflow_step
        step_outputs = dict(output=step.state.inputs['input'])
        progress.set_outputs_for_input(invocation_step, step_outputs)


class PauseModule(WorkflowModule):
    """ Initially this module will unconditionally pause a workflow - will aim
    to allow conditional pausing later on.
    """
    type = "pause"
    name = "Pause for dataset review"

    def get_all_inputs(self, data_only=False, connectable_only=False):
        input = dict(
            name="input",
            label="Dataset for Review",
            multiple=False,
            extensions='input',
            input_type="dataset",
        )
        return [input] if not data_only else []

    def get_all_outputs(self, data_only=False):
        return [dict(name="output", label="Reviewed Dataset", extensions=['input'])]

    def get_runtime_state(self):
        state = DefaultToolState()
        state.inputs = dict()
        return state

    def execute(self, trans, progress, invocation_step, use_cached_job=False):
        step = invocation_step.workflow_step
        progress.mark_step_outputs_delayed(step, why="executing pause step")

    def recover_mapping(self, invocation_step, progress):
        if invocation_step:
            step = invocation_step.workflow_step
            action = invocation_step.action
            if action:
                connection = step.input_connections_by_name["input"][0]
                replacement = progress.replacement_for_connection(connection)
                progress.set_step_outputs(invocation_step, {'output': replacement})
                return
            elif action is False:
                raise CancelWorkflowEvaluation()
        delayed_why = "workflow paused at this step waiting for review"
        raise DelayedWorkflowEvaluation(why=delayed_why)

    def do_invocation_step_action(self, step, action):
        """ Update or set the workflow invocation state action - generic
        extension point meant to allows users to interact with interactive
        workflow modules. The action object returned from this method will
        be attached to the WorkflowInvocationStep and be available the next
        time the workflow scheduler visits the workflow.
        """
        return bool(action)


class ToolModule(WorkflowModule):

    type = "tool"
    name = "Tool"

    def __init__(self, trans, tool_id, tool_version=None, exact_tools=True, **kwds):
        super(ToolModule, self).__init__(trans, content_id=tool_id, **kwds)
        self.tool_id = tool_id
        self.tool_version = tool_version
        self.tool = trans.app.toolbox.get_tool(tool_id, tool_version=tool_version, exact=exact_tools)
        if self.tool and tool_version and exact_tools and str(self.tool.version) != str(tool_version):
            log.info("Exact tool specified during workflow module creation for [%s] but couldn't find correct version [%s]." % (tool_id, tool_version))
            self.tool = None
        self.post_job_actions = {}
        self.runtime_post_job_actions = {}
        self.workflow_outputs = []
        self.version_changes = []

    # ---- Creating modules from various representations ---------------------

    @classmethod
    def from_dict(Class, trans, d, **kwds):
        tool_id = d.get('content_id') or d.get('tool_id')
        if tool_id is None:
            raise exceptions.RequestParameterInvalidException("No tool id could be located for step [%s]." % d)
        tool_version = d.get('tool_version')
        if tool_version:
            tool_version = str(tool_version)
        module = super(ToolModule, Class).from_dict(trans, d, tool_id=tool_id, tool_version=tool_version, **kwds)
        module.post_job_actions = d.get('post_job_actions', {})
        module.workflow_outputs = d.get('workflow_outputs', [])
        if module.tool:
            message = ""
            if tool_id != module.tool_id:
                message += "The tool (id '%s') specified in this step is not available. Using the tool with id %s instead." % (tool_id, module.tool_id)
            if d.get('tool_version', 'Unspecified') != module.get_version():
                message += "%s: using version '%s' instead of version '%s' specified in this workflow." % (tool_id, module.get_version(), d.get('tool_version', 'Unspecified'))
            if message:
                log.debug(message)
                module.version_changes.append(message)
        return module

    @classmethod
    def from_workflow_step(Class, trans, step, **kwds):
        tool_id = trans.app.toolbox.get_tool_id(step.tool_id) or step.tool_id
        tool_version = step.tool_version
        module = super(ToolModule, Class).from_workflow_step(trans, step, tool_id=tool_id, tool_version=tool_version, **kwds)
        module.workflow_outputs = step.workflow_outputs
        module.post_job_actions = {}
        for pja in step.post_job_actions:
            module.post_job_actions[pja.action_type] = pja
        if module.tool:
            message = ""
            if step.tool_id != module.tool_id:  # This means the exact version of the tool is not installed. We inform the user.
                old_tool_shed = step.tool_id.split("/repos/")[0]
                if old_tool_shed not in tool_id:  # Only display the following warning if the tool comes from a different tool shed
                    old_tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, old_tool_shed)
                    if not old_tool_shed_url:  # a tool from a different tool_shed has been found, but the original tool shed has been deactivated
                        old_tool_shed_url = "http://" + old_tool_shed  # let's just assume it's either http, or a http is forwarded to https.
                    old_url = old_tool_shed_url + "/view/%s/%s/" % (module.tool.repository_owner, module.tool.repository_name)
                    new_url = module.tool.sharable_url + '/%s/' % module.tool.changeset_revision
                    new_tool_shed_url = new_url.split("/view")[0]
                    message += "The tool \'%s\', version %s by the owner %s installed from <a href=\"%s\" target=\"_blank\">%s</a> is not available. " % (module.tool.name, tool_version, module.tool.repository_owner, old_url, old_tool_shed_url)
                    message += "A derivation of this tool installed from <a href=\"%s\" target=\"_blank\">%s</a> will be used instead. " % (new_url, new_tool_shed_url)
            if step.tool_version and (step.tool_version != module.tool.version):
                message += "<span title=\"tool id '%s'\">Using version '%s' instead of version '%s' specified in this workflow. " % (tool_id, module.tool.version, step.tool_version)
            if message:
                log.debug(message)
                module.version_changes.append(message)
        else:
            log.warning("The tool '%s' is missing. Cannot build workflow module." % tool_id)
        return module

    # ---- Saving in various forms ------------------------------------------

    def save_to_step(self, step):
        super(ToolModule, self).save_to_step(step)
        step.tool_id = self.tool_id
        step.tool_version = self.get_version()
        for k, v in self.post_job_actions.items():
            pja = self.__to_pja(k, v, step)
            self.trans.sa_session.add(pja)

    # ---- General attributes ------------------------------------------------

    def get_name(self):
        return self.tool.name if self.tool else self.tool_id

    def get_content_id(self):
        return self.tool_id

    def get_version(self):
        return self.tool.version if self.tool else self.tool_version

    def get_tooltip(self, static_path=''):
        if self.tool and self.tool.help:
            return self.tool.help.render(host_url=web.url_for('/'), static_path=static_path)

    # ---- Configuration time -----------------------------------------------

    def get_errors(self, include_tool_id=False, **kwargs):
        if not self.tool:
            if include_tool_id:
                return "%s is not installed" % self.tool_id
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
                visible = not hasattr(input, 'hidden') or not input.hidden
                input_type = input.type
                is_data = isinstance(input, DataToolParameter) or isinstance(input, DataCollectionToolParameter)
                is_connectable = is_runtime_value(value) and runtime_to_json(value)["__class__"] == "ConnectedValue"
                if data_only:
                    skip = not visible or not is_data
                elif connectable_only:
                    skip = not visible or not (is_data or is_connectable)
                else:
                    skip = not visible
                if not skip:
                    if isinstance(input, DataToolParameter):
                        inputs.append(dict(
                            name=prefixed_name,
                            label=prefixed_label,
                            multiple=input.multiple,
                            extensions=input.extensions,
                            input_type="dataset", ))
                    elif isinstance(input, DataCollectionToolParameter):
                        inputs.append(dict(
                            name=prefixed_name,
                            label=prefixed_label,
                            multiple=input.multiple,
                            input_type="dataset_collection",
                            collection_types=input.collection_types,
                            extensions=input.extensions,
                        ))
                    else:
                        inputs.append(
                            dict(
                                name=prefixed_name,
                                label=prefixed_label,
                                multiple=False,
                                input_type="parameter",
                                type=input_type,
                            )
                        )

            visit_input_values(self.tool.inputs, self.state.inputs, callback)
        return inputs

    def get_all_outputs(self, data_only=False):
        data_outputs = []
        if self.tool:
            for name, tool_output in self.tool.outputs.items():
                extra_kwds = {}
                if tool_output.collection:
                    extra_kwds["collection"] = True
                    collection_type = tool_output.structure.collection_type
                    if not collection_type and tool_output.structure.collection_type_from_rules:
                        rule_param = tool_output.structure.collection_type_from_rules
                        if rule_param in self.state.inputs:
                            rule_json_str = self.state.inputs[rule_param]
                            if rule_json_str:  # initialized to None...
                                rules = rule_json_str
                                if rules:
                                    rule_set = RuleSet(rules)
                                    collection_type = rule_set.collection_type
                    extra_kwds["collection_type"] = collection_type
                    extra_kwds["collection_type_source"] = tool_output.structure.collection_type_source
                    formats = ['input']  # TODO: fix
                elif tool_output.format_source is not None:
                    formats = ['input']  # default to special name "input" which remove restrictions on connections
                else:
                    formats = [tool_output.format]
                for change_elem in tool_output.change_format:
                    for when_elem in change_elem.findall('when'):
                        format = when_elem.get('format', None)
                        if format and format not in formats:
                            formats.append(format)
                if tool_output.label:
                    try:
                        params = make_dict_copy(self.state.inputs)
                        params['on_string'] = 'input dataset(s)'
                        params['tool'] = self.tool
                        extra_kwds['label'] = fill_template(tool_output.label, context=params)
                    except Exception:
                        pass
                data_outputs.append(
                    dict(
                        name=name,
                        extensions=formats,
                        **extra_kwds
                    )
                )
        return data_outputs

    def get_config_form(self, step=None):
        if self.tool:
            self.add_dummy_datasets(connections=step and step.input_connections)
            incoming = {}
            params_to_incoming(incoming, self.tool.inputs, self.state.inputs, self.trans.app)
            return self.tool.to_json(self.trans, incoming, workflow_building_mode=True)

    def check_and_update_state(self):
        if self.tool:
            return self.tool.check_and_update_param_values(self.state.inputs, self.trans, workflow_building_mode=True)

    def add_dummy_datasets(self, connections=None, steps=None):
        if self.tool:
            if connections:
                # Store connections by input name
                input_connections_by_name = dict((conn.input_name, conn) for conn in connections)
            else:
                input_connections_by_name = {}

            # Any input needs to have value RuntimeValue or obtain the value from connected steps
            def callback(input, prefixed_name, context, **kwargs):
                input_type = input.type
                is_data = input_type in ['data', 'data_collection']
                if is_data and connections is not None and steps is not None and self.trans.workflow_building_mode is workflow_building_modes.USE_HISTORY:
                    if prefixed_name in input_connections_by_name:
                        connection = input_connections_by_name[prefixed_name]
                        output_step = next(output_step for output_step in steps if connection.output_step_id == output_step.id)
                        if output_step.type.startswith('data'):
                            output_inputs = output_step.module.get_runtime_inputs(connections=connections)
                            output_value = output_inputs['input'].get_initial_value(self.trans, context)
                            if input_type == "data" and isinstance(output_value, self.trans.app.model.HistoryDatasetCollectionAssociation):
                                return output_value.to_hda_representative()
                            return output_value
                        return ConnectedValue()
                    else:
                        return input.get_initial_value(self.trans, context)
                elif (is_data and connections is None) or prefixed_name in input_connections_by_name:
                    return ConnectedValue()
            visit_input_values(self.tool.inputs, self.state.inputs, callback)
        else:
            raise ToolMissingException("Tool %s missing. Cannot add dummy datasets." % self.tool_id,
                                       tool_id=self.tool_id)

    def get_post_job_actions(self, incoming):
        return ActionBox.handle_incoming(incoming)

    # ---- Run time ---------------------------------------------------------

    def recover_state(self, state, **kwds):
        """ Recover state `dict` from simple dictionary describing configuration
        state (potentially from persisted step state).

        Sub-classes should supply a `default_state` method which contains the
        initial state `dict` with key, value pairs for all available attributes.
        """
        super(ToolModule, self).recover_state(state, **kwds)
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

        def augment(expected_replacement_key, inputs, inputs_state):
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
                augment(rest, repeat.inputs, repeat_instance_state)

        for expected_replacement_key in expected_replacement_keys:
            inputs_states = self.state.inputs
            inputs = self.tool.inputs
            augment(expected_replacement_key, inputs, inputs_states)

    def get_runtime_state(self):
        state = DefaultToolState()
        state.inputs = self.state.inputs
        return state

    def get_runtime_inputs(self, **kwds):
        return self.get_inputs()

    def compute_runtime_state(self, trans, step=None, step_updates=None):
        # Warning: This method destructively modifies existing step state.
        if self.tool:
            step_errors = {}
            state = self.state
            self.runtime_post_job_actions = {}
            state, step_errors = super(ToolModule, self).compute_runtime_state(trans, step, step_updates)
            if step_updates:
                self.runtime_post_job_actions = step_updates.get(RUNTIME_POST_JOB_ACTIONS_KEY, {})
                step_metadata_runtime_state = self.__step_meta_runtime_state()
                if step_metadata_runtime_state:
                    state.inputs[RUNTIME_STEP_META_STATE_KEY] = step_metadata_runtime_state
            return state, step_errors
        else:
            raise ToolMissingException("Tool %s missing. Cannot compute runtime state." % self.tool_id,
                                       tool_id=self.tool_id)

    def decode_runtime_state(self, runtime_state):
        """ Take runtime state from persisted invocation and convert it
        into a DefaultToolState object for use during workflow invocation.
        """
        if self.tool:
            state = super(ToolModule, self).decode_runtime_state(runtime_state)
            if RUNTIME_STEP_META_STATE_KEY in runtime_state:
                self.__restore_step_meta_runtime_state(loads(runtime_state[RUNTIME_STEP_META_STATE_KEY]))
            return state
        else:
            raise ToolMissingException("Tool %s missing. Cannot recover runtime state." % self.tool_id,
                                       tool_id=self.tool_id)

    def execute(self, trans, progress, invocation_step, use_cached_job=False):
        invocation = invocation_step.workflow_invocation
        step = invocation_step.workflow_step
        tool = trans.app.toolbox.get_tool(step.tool_id, tool_version=step.tool_version)
        if not tool.is_workflow_compatible:
            message = "Specified tool [%s] in workflow is not workflow-compatible." % tool.id
            raise Exception(message)
        tool_state = step.state
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
            iteration_elements_iter = [None]

        resource_parameters = invocation.resource_parameters
        for iteration_elements in iteration_elements_iter:
            execution_state = tool_state.copy()
            # TODO: Move next step into copy()
            execution_state.inputs = make_dict_copy(execution_state.inputs)

            expected_replacement_keys = set(step.input_connections_by_name.keys())
            found_replacement_keys = set()

            # Connect up
            def callback(input, prefixed_name, **kwargs):
                input_dict = all_inputs_by_name[prefixed_name]

                replacement = NO_REPLACEMENT
                if iteration_elements and prefixed_name in iteration_elements:
                    if isinstance(input, DataToolParameter) and hasattr(iteration_elements[prefixed_name], 'dataset_instance'):
                        # Pull out dataset instance (=HDA) from element and set a temporary element_identifier attribute
                        # See https://github.com/galaxyproject/galaxy/pull/1693 for context.
                        replacement = iteration_elements[prefixed_name].dataset_instance
                        if hasattr(iteration_elements[prefixed_name], u'element_identifier') and iteration_elements[prefixed_name].element_identifier:
                            replacement.element_identifier = iteration_elements[prefixed_name].element_identifier
                    else:
                        # If collection - just use element model object.
                        replacement = iteration_elements[prefixed_name]
                else:
                    replacement = progress.replacement_for_input(step, input_dict)

                if replacement is not NO_REPLACEMENT:
                    found_replacement_keys.add(prefixed_name)

                return replacement

            try:
                # Replace DummyDatasets with historydatasetassociations
                visit_input_values(tool.inputs, execution_state.inputs, callback, no_replacement_value=NO_REPLACEMENT)
            except KeyError as k:
                message_template = "Error due to input mapping of '%s' in '%s'.  A common cause of this is conditional outputs that cannot be determined until runtime, please review your workflow."
                message = message_template % (tool.name, k.message)
                raise exceptions.MessageException(message)

            unmatched_input_connections = expected_replacement_keys - found_replacement_keys
            if unmatched_input_connections:
                log.warn("Failed to use input connections for inputs [%s]" % unmatched_input_connections)

            param_combinations.append(execution_state.inputs)

        complete = False
        completed_jobs = {}
        for i, param in enumerate(param_combinations):
            if use_cached_job:
                completed_jobs[i] = tool.job_search.by_tool_input(
                    trans=trans,
                    tool_id=tool.id,
                    tool_version=tool.version,
                    param=param,
                    param_dump=tool.params_to_strings(param, trans.app, nested=True),
                    job_state=None,
                )
            else:
                completed_jobs[i] = None
        try:
            mapping_params = MappingParameters(tool_state.inputs, param_combinations)
            max_num_jobs = progress.maximum_jobs_to_schedule_or_none
            execution_tracker = execute(
                trans=self.trans,
                tool=tool,
                mapping_params=mapping_params,
                history=invocation.history,
                collection_info=collection_info,
                workflow_invocation_uuid=invocation.uuid.hex,
                invocation_step=invocation_step,
                max_num_jobs=max_num_jobs,
                job_callback=lambda job: self._handle_post_job_actions(step, job, invocation.replacement_dict),
                completed_jobs=completed_jobs,
                workflow_resource_parameters=resource_parameters
            )
            complete = True
        except PartialJobExecution as pje:
            execution_tracker = pje.execution_tracker

        except ToolInputsNotReadyException:
            delayed_why = "tool [%s] inputs are not ready, this special tool requires inputs to be ready" % tool.id
            raise DelayedWorkflowEvaluation(why=delayed_why)

        progress.record_executed_job_count(len(execution_tracker.successful_jobs))
        if collection_info:
            step_outputs = dict(execution_tracker.implicit_collections)
        else:
            step_outputs = dict(execution_tracker.output_datasets)
            step_outputs.update(execution_tracker.output_collections)
        progress.set_step_outputs(invocation_step, step_outputs, already_persisted=not invocation_step.is_new)

        if collection_info:
            step_inputs = mapping_params.param_template
            step_inputs.update(collection_info.collections)

            self._handle_mapped_over_post_job_actions(step, step_inputs, step_outputs, invocation.replacement_dict)
        if execution_tracker.execution_errors:
            message = "Failed to create one or more job(s) for workflow step."
            raise Exception(message)

        return complete

    def recover_mapping(self, invocation_step, progress):
        outputs = {}

        for output_dataset_assoc in invocation_step.output_datasets:
            outputs[output_dataset_assoc.output_name] = output_dataset_assoc.dataset

        for output_dataset_collection_assoc in invocation_step.output_dataset_collections:
            outputs[output_dataset_collection_assoc.output_name] = output_dataset_collection_assoc.dataset_collection

        progress.set_step_outputs(invocation_step, outputs)

    def _effective_post_job_actions(self, step):
        effective_post_job_actions = step.post_job_actions[:]
        for key, value in self.runtime_post_job_actions.items():
            effective_post_job_actions.append(self.__to_pja(key, value, None))
        return effective_post_job_actions

    def _handle_mapped_over_post_job_actions(self, step, step_inputs, step_outputs, replacement_dict):
        effective_post_job_actions = self._effective_post_job_actions(step)
        for pja in effective_post_job_actions:
            if pja.action_type in ActionBox.mapped_over_output_actions:
                ActionBox.execute_on_mapped_over(self.trans, self.trans.sa_session, pja, step_inputs, step_outputs, replacement_dict)

    def _handle_post_job_actions(self, step, job, replacement_dict):
        # Create new PJA associations with the created job, to be run on completion.
        # PJA Parameter Replacement (only applies to immediate actions-- rename specifically, for now)
        # Pass along replacement dict with the execution of the PJA so we don't have to modify the object.

        # Combine workflow and runtime post job actions into the effective post
        # job actions for this execution.
        flush_required = False
        effective_post_job_actions = self._effective_post_job_actions(step)
        for pja in effective_post_job_actions:
            if pja.action_type in ActionBox.immediate_actions:
                ActionBox.execute(self.trans.app, self.trans.sa_session, pja, job, replacement_dict)
            else:
                pjaa = model.PostJobActionAssociation(pja, job_id=job.id)
                self.trans.sa_session.add(pjaa)
                flush_required = True
        if flush_required:
            self.trans.sa_session.flush()

    def __restore_step_meta_runtime_state(self, step_runtime_state):
        if RUNTIME_POST_JOB_ACTIONS_KEY in step_runtime_state:
            self.runtime_post_job_actions = step_runtime_state[RUNTIME_POST_JOB_ACTIONS_KEY]

    def __step_meta_runtime_state(self):
        """ Build a dictionary a of meta-step runtime state (state about how
        the workflow step - not the tool state) to be serialized with the Tool
        state.
        """
        return {RUNTIME_POST_JOB_ACTIONS_KEY: self.runtime_post_job_actions}

    def __to_pja(self, key, value, step):
        if 'output_name' in value:
            output_name = value['output_name']
        else:
            output_name = None
        if 'action_arguments' in value:
            action_arguments = value['action_arguments']
        else:
            action_arguments = None
        return PostJobAction(value['action_type'], step, output_name, action_arguments)

    def get_replacement_parameters(self, step):
        """Return a list of replacement parameters."""
        replacement_parameters = set()
        for pja in step.post_job_actions:
            for argument in pja.action_arguments.values():
                for match in re.findall(r'\$\{(.+?)\}', argument):
                    replacement_parameters.add(match)

        return list(replacement_parameters)


class WorkflowModuleFactory(object):

    def __init__(self, module_types):
        self.module_types = module_types

    def from_dict(self, trans, d, **kwargs):
        """
        Return module initialized from the data in dictionary `d`.
        """
        type = d['type']
        assert type in self.module_types, "Unexpected workflow step type [%s] not found in [%s]" % (type, self.module_types.keys())
        return self.module_types[type].from_dict(trans, d, **kwargs)

    def from_workflow_step(self, trans, step, **kwargs):
        """
        Return module initializd from the WorkflowStep object `step`.
        """
        type = step.type
        return self.module_types[type].from_workflow_step(trans, step, **kwargs)


def is_tool_module_type(module_type):
    return not module_type or module_type == "tool"


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
    """ Get abstract description of the workflow modules this Galaxy instance
    is configured with.
    """
    module_sections = {}
    module_sections['inputs'] = {
        "name": "inputs",
        "title": "Inputs",
        "modules": [
            {
                "name": "data_input",
                "title": "Input Dataset",
                "description": "Input dataset"
            },
            {
                "name": "data_collection_input",
                "title": "Input Dataset Collection",
                "description": "Input dataset collection"
            },
            {
                "name": "parameter_input",
                "title": "Parameter Input",
                "description": "Simple inputs used for workflow logic"
            },
        ],
    }

    if trans.app.config.enable_beta_workflow_modules:
        module_sections['experimental'] = {
            "name": "experimental",
            "title": "Experimental",
            "modules": [
                {
                    "name": "pause",
                    "title": "Pause Workflow for Dataset Review",
                    "description": "Pause for Review"
                }
            ],
        }

    return module_sections


class DelayedWorkflowEvaluation(Exception):

    def __init__(self, why=None):
        self.why = why


class CancelWorkflowEvaluation(Exception):
    pass


class WorkflowModuleInjector(object):
    """ Injects workflow step objects from the ORM with appropriate module and
    module generated/influenced state. """

    def __init__(self, trans, allow_tool_state_corrections=False):
        self.trans = trans
        self.allow_tool_state_corrections = allow_tool_state_corrections

    def inject(self, step, step_args=None, steps=None, **kwargs):
        """ Pre-condition: `step` is an ORM object coming from the database, if
        supplied `step_args` is the representation of the inputs for that step
        supplied via web form.

        Post-condition: The supplied `step` has new non-persistent attributes
        useful during workflow invocation. These include 'upgrade_messages',
        'state', 'input_connections_by_name', and 'module'.

        If step_args is provided from a web form this is applied to generate
        'state' else it is just obtained from the database.
        """
        step_errors = None
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
            populate_module_and_state(self.trans, subworkflow, param_map=unjsonified_subworkflow_param_map)

        state, step_errors = module.compute_runtime_state(self.trans, step, step_args)
        step.state = state

        # Fix any missing parameters
        step.upgrade_messages = module.check_and_update_state()

        return step_errors


def populate_module_and_state(trans, workflow, param_map, allow_tool_state_corrections=False, module_injector=None):
    """ Used by API but not web controller, walks through a workflow's steps
    and populates transient module and state attributes on each.
    """
    if module_injector is None:
        module_injector = WorkflowModuleInjector(trans, allow_tool_state_corrections)
    for step in workflow.steps:
        step_args = param_map.get(step.id, {})
        step_errors = module_injector.inject(step, step_args=step_args)
        if step_errors:
            raise exceptions.MessageException(step_errors, err_data={step.order_index: step_errors})
        if step.upgrade_messages:
            if allow_tool_state_corrections:
                log.debug('Workflow step "%i" had upgrade messages: %s', step.id, step.upgrade_messages)
            else:
                raise exceptions.MessageException(step.upgrade_messages, err_data={step.order_index: step.upgrade_messages})

""" Tool shed helper methods for dealing with workflows - only two methods are
utilized outside of this modules - generate_workflow_image and import_workflow.
"""
import json
import logging
import os

import galaxy.tools
import galaxy.tools.parameters
from galaxy.tools.repositories import ValidationContext
from galaxy.util.sanitize_html import sanitize_html
from galaxy.workflow.modules import (
    module_types,
    ToolModule,
    WorkflowModuleFactory
)
from galaxy.workflow.render import WorkflowCanvas
from galaxy.workflow.steps import attach_ordered_steps
from tool_shed.tools import tool_validator
from tool_shed.util import (
    encoding_util,
    metadata_util,
    repository_util
)

log = logging.getLogger(__name__)


class RepoToolModule(ToolModule):

    type = "tool"

    def __init__(self, trans, repository_id, changeset_revision, tools_metadata, tool_id):
        self.trans = trans
        self.tools_metadata = tools_metadata
        self.tool_id = tool_id
        self.tool = None
        self.errors = None
        self.tool_version = None
        if trans.webapp.name == 'tool_shed':
            # We're in the tool shed.
            with ValidationContext.from_app(trans.app) as validation_context:
                tv = tool_validator.ToolValidator(validation_context)
                for tool_dict in tools_metadata:
                    if self.tool_id in [tool_dict['id'], tool_dict['guid']]:
                        repository, self.tool, valid, message = tv.load_tool_from_changeset_revision(repository_id,
                                                                                                     changeset_revision,
                                                                                                     tool_dict['tool_config'])
                        if self.tool is None and message or not valid:
                            self.errors = 'unavailable'
                        break
        else:
            # We're in Galaxy.
            self.tool = trans.app.toolbox.get_tool(self.tool_id, tool_version=self.tool_version)
            if self.tool is None:
                self.errors = 'unavailable'
        self.post_job_actions = {}
        self.workflow_outputs = []
        self.state = None

    @classmethod
    def from_dict(Class, trans, step_dict, repository_id, changeset_revision, tools_metadata, secure=True):
        tool_id = step_dict['tool_id']
        module = Class(trans, repository_id, changeset_revision, tools_metadata, tool_id)
        module.state = galaxy.tools.DefaultToolState()
        if module.tool is not None:
            module.state.decode(step_dict["tool_state"], module.tool, module.trans.app)
        module.errors = step_dict.get("tool_errors", None)
        return module

    @classmethod
    def from_workflow_step(Class, trans, step, repository_id, changeset_revision, tools_metadata):
        module = Class(trans, repository_id, changeset_revision, tools_metadata, step.tool_id)
        module.state = galaxy.tools.DefaultToolState()
        module.recover_state(step.tool_inputs)
        module.errors = module.get_errors()
        return module

    def get_data_inputs(self):
        data_inputs = []

        def callback(input, prefixed_name, prefixed_label, **kwargs):
            if isinstance(input, galaxy.tools.parameters.basic.DataToolParameter):
                data_inputs.append(dict(name=prefixed_name,
                                        label=prefixed_label,
                                        extensions=input.extensions))
        if self.tool:
            try:
                galaxy.tools.parameters.visit_input_values(self.tool.inputs, self.state.inputs, callback)
            except Exception:
                # TODO have this actually use default parameters?  Fix at
                # refactor, needs to be discussed wrt: reproducibility though.
                log.exception("Tool parse failed for %s -- this indicates incompatibility of local tool version with expected version by the workflow.", self.tool.id)
        return data_inputs

    def get_data_outputs(self):
        data_outputs = []
        if self.tool:
            data_inputs = None
            for name, tool_output in self.tool.outputs.items():
                if tool_output.format_source is not None:
                    # Default to special name "input" which remove restrictions on connections
                    formats = ['input']
                    if data_inputs is None:
                        data_inputs = self.get_data_inputs()
                    # Find the input parameter referenced by format_source
                    for di in data_inputs:
                        # Input names come prefixed with conditional and repeat names separated by '|',
                        # so remove prefixes when comparing with format_source.
                        if di['name'] is not None and di['name'].split('|')[-1] == tool_output.format_source:
                            formats = di['extensions']
                else:
                    formats = [tool_output.format]
                for change_elem in tool_output.change_format:
                    for when_elem in change_elem.findall('when'):
                        format = when_elem.get('format', None)
                        if format and format not in formats:
                            formats.append(format)
                data_outputs.append(dict(name=name, extensions=formats))
        return data_outputs


class RepoWorkflowModuleFactory(WorkflowModuleFactory):

    def __init__(self, module_types):
        self.module_types = module_types

    def from_dict(self, trans, repository_id, changeset_revision, step_dict, tools_metadata, **kwd):
        """Return module initialized from the data in dictionary `step_dict`."""
        type = step_dict['type']
        assert type in self.module_types
        module_method_kwds = dict(**kwd)
        if type == "tool":
            module_method_kwds['repository_id'] = repository_id
            module_method_kwds['changeset_revision'] = changeset_revision
            module_method_kwds['tools_metadata'] = tools_metadata
        return self.module_types[type].from_dict(trans, step_dict, **module_method_kwds)

    def from_workflow_step(self, trans, repository_id, changeset_revision, tools_metadata, step):
        """Return module initialized from the WorkflowStep object `step`."""
        type = step.type
        module_method_kwds = dict()
        if type == "tool":
            module_method_kwds['repository_id'] = repository_id
            module_method_kwds['changeset_revision'] = changeset_revision
            module_method_kwds['tools_metadata'] = tools_metadata
        return self.module_types[type].from_workflow_step(trans, step, **module_method_kwds)


tool_shed_module_types = module_types.copy()
tool_shed_module_types['tool'] = RepoToolModule
module_factory = RepoWorkflowModuleFactory(tool_shed_module_types)


def generate_workflow_image(trans, workflow_name, repository_metadata_id=None, repository_id=None):
    """
    Return an svg image representation of a workflow dictionary created when the workflow was exported.  This method is called
    from both Galaxy and the tool shed.  When called from the tool shed, repository_metadata_id will have a value and repository_id
    will be None.  When called from Galaxy, repository_metadata_id will be None and repository_id will have a value.
    """
    workflow_name = encoding_util.tool_shed_decode(workflow_name)
    if trans.webapp.name == 'tool_shed':
        # We're in the tool shed.
        repository_metadata = metadata_util.get_repository_metadata_by_id(trans.app, repository_metadata_id)
        repository_id = trans.security.encode_id(repository_metadata.repository_id)
        changeset_revision = repository_metadata.changeset_revision
        metadata = repository_metadata.metadata
    else:
        # We're in Galaxy.
        repository = repository_util.get_tool_shed_repository_by_id(trans.app, repository_id)
        changeset_revision = repository.changeset_revision
        metadata = repository.metadata
    # metadata[ 'workflows' ] is a list of tuples where each contained tuple is
    # [ <relative path to the .ga file in the repository>, <exported workflow dict> ]
    for workflow_tup in metadata['workflows']:
        workflow_dict = workflow_tup[1]
        if workflow_dict['name'] == workflow_name:
            break
    if 'tools' in metadata:
        tools_metadata = metadata['tools']
    else:
        tools_metadata = []
    workflow, missing_tool_tups = get_workflow_from_dict(trans=trans,
                                                         workflow_dict=workflow_dict,
                                                         tools_metadata=tools_metadata,
                                                         repository_id=repository_id,
                                                         changeset_revision=changeset_revision)
    workflow_canvas = WorkflowCanvas()
    canvas = workflow_canvas.canvas
    # Store px width for boxes of each step.
    for step in workflow.steps:
        step.upgrade_messages = {}
        module = module_factory.from_workflow_step(trans, repository_id, changeset_revision, tools_metadata, step)
        tool_errors = module.type == 'tool' and not module.tool
        module_data_inputs = get_workflow_data_inputs(step, module)
        module_data_outputs = get_workflow_data_outputs(step, module, workflow.steps)
        module_name = get_workflow_module_name(module, missing_tool_tups)
        workflow_canvas.populate_data_for_step(
            step,
            module_name,
            module_data_inputs,
            module_data_outputs,
            tool_errors=tool_errors
        )
    workflow_canvas.add_steps(highlight_errors=True)
    workflow_canvas.finish()
    trans.response.set_content_type("image/svg+xml")
    return canvas.tostring()


def get_workflow_data_inputs(step, module):
    if module.type == 'tool':
        if module.tool:
            return module.get_data_inputs()
        else:
            data_inputs = []
            for wfsc in step.input_connections:
                data_inputs_dict = {}
                data_inputs_dict['extensions'] = ['']
                data_inputs_dict['name'] = wfsc.input_name
                data_inputs_dict['label'] = 'Unknown'
                data_inputs.append(data_inputs_dict)
            return data_inputs
    return module.get_data_inputs()


def get_workflow_data_outputs(step, module, steps):
    if module.type == 'tool':
        if module.tool:
            return module.get_data_outputs()
        else:
            data_outputs = []
            data_outputs_dict = {}
            data_outputs_dict['extensions'] = ['input']
            found = False
            for workflow_step in steps:
                for wfsc in workflow_step.input_connections:
                    if step.label == wfsc.output_step.label:
                        data_outputs_dict['name'] = wfsc.output_name
                        found = True
                        break
                if found:
                    break
            if not found:
                # We're at the last step of the workflow.
                data_outputs_dict['name'] = 'output'
            data_outputs.append(data_outputs_dict)
            return data_outputs
    return module.get_data_outputs()


def get_workflow_from_dict(trans, workflow_dict, tools_metadata, repository_id, changeset_revision):
    """
    Return an in-memory Workflow object from the dictionary object created when it was exported.  This method is called from
    both Galaxy and the tool shed to retrieve a Workflow object that can be displayed as an SVG image.  This method is also
    called from Galaxy to retrieve a Workflow object that can be used for saving to the Galaxy database.
    """
    trans.workflow_building_mode = True
    workflow = trans.model.Workflow()
    workflow.name = workflow_dict['name']
    workflow.has_errors = False
    steps = []
    # Keep ids for each step that we need to use to make connections.
    steps_by_external_id = {}
    # Keep track of tools required by the workflow that are not available in
    # the tool shed repository.  Each tuple in the list of missing_tool_tups
    # will be ( tool_id, tool_name, tool_version ).
    missing_tool_tups = []
    # First pass to build step objects and populate basic values
    for step_dict in workflow_dict['steps'].values():
        # Create the model class for the step
        step = trans.model.WorkflowStep()
        step.label = step_dict.get('label', None)
        step.position = step_dict['position']
        module = module_factory.from_dict(trans, repository_id, changeset_revision, step_dict, tools_metadata=tools_metadata)
        if module.type == 'tool' and module.tool is None:
            # A required tool is not available in the current repository.
            step.tool_errors = 'unavailable'
            missing_tool_tup = (step_dict['tool_id'], step_dict['name'], step_dict['tool_version'])
            if missing_tool_tup not in missing_tool_tups:
                missing_tool_tups.append(missing_tool_tup)
        module.save_to_step(step)
        if step.tool_errors:
            workflow.has_errors = True
        # Stick this in the step temporarily.
        step.temp_input_connections = step_dict['input_connections']
        if trans.webapp.name == 'galaxy':
            annotation = step_dict.get('annotation', '')
            if annotation:
                annotation = sanitize_html(annotation)
                new_step_annotation = trans.model.WorkflowStepAnnotationAssociation()
                new_step_annotation.annotation = annotation
                new_step_annotation.user = trans.user
                step.annotations.append(new_step_annotation)
        # Unpack and add post-job actions.
        post_job_actions = step_dict.get('post_job_actions', {})
        for pja_dict in post_job_actions.values():
            trans.model.PostJobAction(pja_dict['action_type'],
                                      step,
                                      pja_dict['output_name'],
                                      pja_dict['action_arguments'])
        steps.append(step)
        steps_by_external_id[step_dict['id']] = step
    # Second pass to deal with connections between steps.
    for step in steps:
        # Input connections.
        for input_name, conn_dict in step.temp_input_connections.items():
            if conn_dict:
                step_input = step.get_or_add_input(input_name)
                output_step = steps_by_external_id[conn_dict['id']]
                conn = trans.model.WorkflowStepConnection()
                conn.input_step_input = step_input
                conn.output_step = output_step
                conn.output_name = conn_dict['output_name']
        del step.temp_input_connections
    # Order the steps if possible.
    attach_ordered_steps(workflow, steps)
    # Return the in-memory Workflow object for display or later persistence to the Galaxy database.
    return workflow, missing_tool_tups


def get_workflow_module_name(module, missing_tool_tups):
    module_name = module.get_name()
    if module.type == 'tool' and module_name == 'unavailable':
        for missing_tool_tup in missing_tool_tups:
            missing_tool_id, missing_tool_name, missing_tool_version = missing_tool_tup
            if missing_tool_id == module.tool_id:
                module_name = '%s' % missing_tool_name
                break
    return module_name


def import_workflow(trans, repository, workflow_name):
    """Import a workflow contained in an installed tool shed repository into Galaxy (this method is called only from Galaxy)."""
    status = 'done'
    message = ''
    changeset_revision = repository.changeset_revision
    metadata = repository.metadata
    workflows = metadata.get('workflows', [])
    tools_metadata = metadata.get('tools', [])
    workflow_dict = None
    for workflow_data_tuple in workflows:
        # The value of workflow_data_tuple is ( relative_path_to_workflow_file, exported_workflow_dict ).
        relative_path_to_workflow_file, exported_workflow_dict = workflow_data_tuple
        if exported_workflow_dict['name'] == workflow_name:
            # If the exported workflow is available on disk, import it.
            if os.path.exists(relative_path_to_workflow_file):
                workflow_file = open(relative_path_to_workflow_file, 'rb')
                workflow_data = workflow_file.read()
                workflow_file.close()
                workflow_dict = json.loads(workflow_data)
            else:
                # Use the current exported_workflow_dict.
                workflow_dict = exported_workflow_dict
            break
    if workflow_dict:
        # Create workflow if possible.
        workflow, missing_tool_tups = get_workflow_from_dict(trans=trans,
                                                             workflow_dict=workflow_dict,
                                                             tools_metadata=tools_metadata,
                                                             repository_id=repository.id,
                                                             changeset_revision=changeset_revision)
        # Save the workflow in the Galaxy database.  Pass workflow_dict along to create annotation at this point.
        stored_workflow = save_workflow(trans, workflow, workflow_dict)
        # Use the latest version of the saved workflow.
        workflow = stored_workflow.latest_workflow
        if workflow_name:
            workflow.name = workflow_name
        # Provide user feedback and show workflow list.
        if workflow.has_errors:
            message += "Imported, but some steps in this workflow have validation errors. "
            status = "error"
        if workflow.has_cycles:
            message += "Imported, but this workflow contains cycles.  "
            status = "error"
        else:
            message += "Workflow <b>%s</b> imported successfully.  " % workflow.name
        if missing_tool_tups:
            name_and_id_str = ''
            for missing_tool_tup in missing_tool_tups:
                tool_id, tool_name, other = missing_tool_tup
                name_and_id_str += 'name: %s, id: %s' % (str(tool_id), str(tool_name))
            message += "The following tools required by this workflow are missing from this Galaxy instance: %s.  " % name_and_id_str
    else:
        workflow = None
        message += 'The workflow named %s is not included in the metadata for revision %s of repository %s' % \
            (str(workflow_name), str(changeset_revision), str(repository.name))
        status = 'error'
    return workflow, status, message


def save_workflow(trans, workflow, workflow_dict=None):
    """Use the received in-memory Workflow object for saving to the Galaxy database."""
    stored = trans.model.StoredWorkflow()
    stored.name = workflow.name
    workflow.stored_workflow = stored
    stored.latest_workflow = workflow
    stored.user = trans.user
    if workflow_dict and workflow_dict.get('annotation', ''):
        annotation = sanitize_html(workflow_dict['annotation'])
        new_annotation = trans.model.StoredWorkflowAnnotationAssociation()
        new_annotation.annotation = annotation
        new_annotation.user = trans.user
        stored.annotations.append(new_annotation)
    trans.sa_session.add(stored)
    trans.sa_session.flush()
    # Add a new entry to the Workflows menu.
    if trans.user.stored_workflow_menu_entries is None:
        trans.user.stored_workflow_menu_entries = []
    menuEntry = trans.model.StoredWorkflowMenuEntry()
    menuEntry.stored_workflow = stored
    trans.user.stored_workflow_menu_entries.append(menuEntry)
    trans.sa_session.flush()
    return stored

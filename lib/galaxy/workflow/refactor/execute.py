import logging
from typing import (
    Any,
    Dict,
)

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.basic import (
    ConnectedValue,
    contains_workflow_parameter,
    runtime_to_json,
)
from .schema import (
    AddInputAction,
    AddStepAction,
    ConnectAction,
    DisconnectAction,
    ExtractInputAction,
    ExtractUntypedParameter,
    FileDefaultsAction,
    FillStepDefaultsAction,
    InputReferenceByOrderIndex,
    OutputReferenceByOrderIndex,
    RefactorActionExecution,
    RefactorActionExecutionMessage,
    RefactorActionExecutionMessageTypeEnum,
    RefactorActions,
    RemoveUnlabeledWorkflowOutputs,
    step_reference_union,
    StepReferenceByLabel,
    UpdateAnnotationAction,
    UpdateCreatorAction,
    UpdateLicenseAction,
    UpdateNameAction,
    UpdateOutputLabelAction,
    UpdateReportAction,
    UpdateStepLabelAction,
    UpdateStepPositionAction,
    UpgradeAllStepsAction,
    UpgradeSubworkflowAction,
    UpgradeToolAction,
)
from ..modules import (
    InputParameterModule,
    NO_REPLACEMENT,
)

log = logging.getLogger(__name__)


class WorkflowRefactorExecutor:
    def __init__(self, raw_workflow_description, workflow, module_injector):
        # we mostly use the ga representation, but there may be cases where the
        # models/modules of existing workflow are more usable.
        self.raw_workflow_description = raw_workflow_description
        self.workflow = workflow
        self.module_injector = module_injector
        self.module_injector.inject_all(workflow, ignore_tool_missing_exception=True)

    def refactor(self, refactor_request: RefactorActions):
        action_executions = []
        for action in refactor_request.actions:
            # TODO: we need to regenerate a detached workflow from as_dict after
            # after each iteration here. Otherwise one set of changes might render
            # the workflow state out of sync. It is fine if you're just executing one
            # action at a time or just performing actions that use raw_workflow_description.
            action_type = action.action_type
            refactor_method_name = f"_apply_{action_type}"
            refactor_method = getattr(self, refactor_method_name, None)
            if refactor_method is None:
                raise RequestParameterInvalidException(f"Unknown workflow editing action encountered [{action_type}]")
            execution = RefactorActionExecution(
                action=action.dict(),
                messages=[],
            )
            refactor_method(action, execution)
            action_executions.append(execution)
        return action_executions

    def _apply_update_step_label(self, action: UpdateStepLabelAction, execution: RefactorActionExecution):
        step = self._find_step_for_action(action)
        step["label"] = action.label

    def _apply_update_step_position(self, action: UpdateStepPositionAction, execution: RefactorActionExecution):
        step = self._find_step_for_action(action)
        position_update = action.position_shift.to_dict()
        step["position"]["left"] = step["position"].get("left", 0) + position_update["left"]
        step["position"]["top"] = step["position"].get("top", 0) + position_update["top"]

    def _apply_update_output_label(self, action: UpdateOutputLabelAction, execution: RefactorActionExecution):
        output_reference = action.output
        output_step_dict = self._find_step(output_reference)
        output_name = output_reference.output_name
        for workflow_output_def in output_step_dict.get("workflow_outputs", []):
            if workflow_output_def["output_name"] == output_name:
                workflow_output_def["label"] = action.output_label

    def _apply_update_name(self, action: UpdateNameAction, execution: RefactorActionExecution):
        self._as_dict["name"] = action.name

    def _apply_update_annotation(self, action: UpdateAnnotationAction, execution: RefactorActionExecution):
        self._as_dict["annotation"] = action.annotation

    def _apply_update_license(self, action: UpdateLicenseAction, execution: RefactorActionExecution):
        self._as_dict["license"] = action.license

    def _apply_update_creator(self, action: UpdateCreatorAction, execution: RefactorActionExecution):
        self._as_dict["creator"] = action.creator

    def _apply_update_report(self, action: UpdateReportAction, execution: RefactorActionExecution):
        self._as_dict["report"] = {"markdown": action.report.markdown}

    def _apply_add_step(self, action: AddStepAction, execution: RefactorActionExecution):
        steps = self._as_dict["steps"]
        order_index = len(steps)
        step_dict = {
            "order_index": order_index,
            "id": "new_%d" % order_index,
            "type": action.type,
        }
        if action.tool_state:
            step_dict["tool_state"] = action.tool_state
        if action.label:
            step_dict["label"] = action.label
        if action.position:
            step_dict["position"] = action.position.to_dict()
        steps[order_index] = step_dict

    def _apply_add_input(self, action: AddInputAction, execution: RefactorActionExecution):
        input_type = action.type
        module_type = None

        tool_state: Dict[str, Any] = {}
        if input_type in ["data", "dataset"]:
            module_type = "data_input"
        elif input_type in ["data_collection", "dataset_collection"]:
            module_type = "data_collection_input"
            tool_state["collection_type"] = action.collection_type
        else:
            if input_type not in InputParameterModule.POSSIBLE_PARAMETER_TYPES:
                raise RequestParameterInvalidException(f"Invalid input type {input_type} encountered")
            module_type = "parameter_input"
            tool_state["parameter_type"] = input_type

        for action_key in ["restrictions", "suggestions", "optional", "default"]:
            value = getattr(action, action_key, None)
            if value is not None:
                tool_state[action_key] = value

        if action.restrict_on_connections is not None:
            tool_state["restrictOnConnections"] = action.restrict_on_connections

        add_step_kwds = {}
        if action.label:
            add_step_kwds["label"] = action.label

        add_step_action = AddStepAction(
            action_type="add_step", type=module_type, tool_state=tool_state, position=action.position, **add_step_kwds
        )
        self._apply_add_step(add_step_action, execution)

    def _apply_disconnect(self, action: DisconnectAction, execution: RefactorActionExecution):
        input_step_dict, input_name, output_step_dict, output_name = self._connection(action)
        output_order_index = output_step_dict["id"]  # wish this was order_index...
        # default name is name used for input's output terminal - following
        # format2 convention of allowing this be absent for clean references
        # to workflow inputs.
        all_input_connections = input_step_dict.get("input_connections")
        self.normalize_input_connections_to_list(all_input_connections, input_name)
        input_connections = all_input_connections[input_name]

        # multiple outputs attached to this inputs, just detach
        # that specific one.
        delete_index = None
        for connection_index, output in enumerate(input_connections):
            if output["id"] == output_order_index and output["output_name"] == output_name:
                delete_index = connection_index
                break
        if delete_index is None:
            raise RequestParameterInvalidException("Failed to locate connection to disconnect")
        del input_connections[delete_index]

    def _apply_connect(self, action: ConnectAction, execution: RefactorActionExecution):
        input_step_dict, input_name, output_step_dict, output_name = self._connection(action)
        output_order_index = output_step_dict["id"]  # wish this was order_index...
        all_input_connections = input_step_dict.get("input_connections")
        self.normalize_input_connections_to_list(all_input_connections, input_name, add_if_missing=True)
        input_connections = all_input_connections[input_name]
        input_connections.append(
            {
                "id": output_order_index,
                "output_name": output_name,
            }
        )

    def _apply_fill_defaults(self, action: FileDefaultsAction, execution: RefactorActionExecution):
        for _, step in self._iterate_over_step_pairs(execution):
            module = step.module
            if module.type != "tool":
                continue
            self._as_dict["steps"][step.order_index]["tool_state"] = step.module.get_tool_state()

    def _apply_fill_step_defaults(self, action: FillStepDefaultsAction, execution: RefactorActionExecution):
        step = self._find_step_with_module_for_action(action, execution)
        self._as_dict["steps"][step.order_index]["tool_state"] = step.module.get_tool_state()

    def _apply_extract_input(self, action: ExtractInputAction, execution: RefactorActionExecution):
        input_step_dict, input_name = self._input_from_action(action)
        step = self._step_with_module(input_step_dict["id"], execution)
        module = step.module
        inputs = module.get_all_inputs()

        input_def = None
        found_input_names = []
        for input in inputs:
            found_input_name = input["name"]
            found_input_names.append(found_input_name)
            if found_input_name == input_name:
                input_def = input
                break
        if input_def is None:
            raise RequestParameterInvalidException(
                f"Failed to find input with name {input_name} on step {input_step_dict['id']} - input names found {found_input_names}"
            )
        if input_def.get("multiple", False):
            raise RequestParameterInvalidException("Cannot extract input for multi-input inputs")

        module_input_type = input_def.get("input_type")
        # convert dataset, dataset_collection => data, data_collection for refactor API
        input_type = {
            "dataset": "data",
            "dataset_collection": "data_collection",
        }.get(module_input_type, module_input_type)

        input_action = AddInputAction(
            action_type="add_input",
            optional=input_def.get("optional"),
            type=input_type,
            label=action.label,
            position=action.position,
        )
        new_input_order_index = self._add_input_get_order_index(input_action, execution)
        connect_action = ConnectAction(
            action_type="connect",
            input=action.input,
            output=OutputReferenceByOrderIndex(order_index=new_input_order_index),
        )
        self._apply_connect(connect_action, execution)

    def _apply_extract_untyped_parameter(self, action: ExtractUntypedParameter, execution: RefactorActionExecution):
        untyped_parameter_name = action.name
        new_label = action.label or untyped_parameter_name
        target_value = "${%s}" % untyped_parameter_name

        target_tool_inputs = []
        rename_pjas = []

        for step_def, step in self._iterate_over_step_pairs(execution):
            module = step.module
            if module.type != "tool":
                continue

            # TODO: require a clean tool state for all tools to do this.
            tool = module.tool
            tool_inputs = module.state

            replace_tool_state = False

            def callback(input, prefixed_name, context, value=None, **kwargs):
                nonlocal replace_tool_state
                # data parameters cannot have untyped parameter values
                if input.type in ["data", "data_collection"]:
                    return NO_REPLACEMENT

                if not contains_workflow_parameter(value):
                    return NO_REPLACEMENT

                if value == target_value:
                    target_tool_inputs.append((step.order_index, input, prefixed_name))  # noqa: B023
                    replace_tool_state = True
                    return runtime_to_json(ConnectedValue())
                else:
                    return NO_REPLACEMENT

            visit_input_values(tool.inputs, tool_inputs.inputs, callback, no_replacement_value=NO_REPLACEMENT)
            if replace_tool_state:
                step_def["tool_state"] = step.module.get_tool_state()

        for post_job_action in self._iterate_over_rename_pjas():
            newname = post_job_action.get("action_arguments", {}).get("newname")
            if target_value in newname:
                rename_pjas.append(post_job_action)

        if len(target_tool_inputs) == 0 and len(rename_pjas) == 0:
            raise RequestParameterInvalidException(
                f"Failed to find {target_value} in the tool state or any workflow steps."
            )

        as_parameter_type = {
            "text": "text",
            "integer": "integer",
            "float": "float",
            "select": "text",
            "genomebuild": "text",
        }
        target_parameter_types = set()
        for _, tool_input, _ in target_tool_inputs:
            tool_input_type = tool_input.type
            if tool_input_type not in as_parameter_type:
                raise RequestParameterInvalidException(
                    "Extracting inputs for parameters on tool inputs of type {tool_input_type} is unsupported"
                )
            target_parameter_type = as_parameter_type[tool_input_type]
            target_parameter_types.add(target_parameter_type)

        if len(target_parameter_types) > 1:
            raise RequestParameterInvalidException(
                "Extracting inputs for parameters on conflicting tool input types (e.g. numeric and non-numeric) input types is unsupported"
            )

        if len(target_parameter_types) == 1:
            (target_parameter_type,) = target_parameter_types
        else:
            # only used in PJA, hence only used a string
            target_parameter_type = "text"

        for rename_pja in rename_pjas:
            # if name != label, got to rewrite this rename with new label.
            if untyped_parameter_name != new_label:
                action_arguments = rename_pja.get("action_arguments")
                old_newname = action_arguments["newname"]
                new_newname = old_newname.replace(target_value, "${%s}" % new_label)
                action_arguments["newname"] = new_newname

        optional = False
        input_action = AddInputAction(
            action_type="add_input",
            optional=optional,
            type=target_parameter_type,
            label=new_label,
            position=action.position,
        )
        new_input_order_index = self._add_input_get_order_index(input_action, execution)

        for order_index, _tool_input, prefixed_name in target_tool_inputs:
            connect_input = InputReferenceByOrderIndex(order_index=order_index, input_name=prefixed_name)
            connect_action = ConnectAction(
                action_type="connect",
                input=connect_input,
                output=OutputReferenceByOrderIndex(order_index=new_input_order_index),
            )
            self._apply_connect(connect_action, execution)

    def _apply_remove_unlabeled_workflow_outputs(
        self, action: RemoveUnlabeledWorkflowOutputs, execution: RefactorActionExecution
    ):
        for step in self._as_dict["steps"].values():
            new_outputs = []
            for workflow_output in step.get("workflow_outputs", []):
                if workflow_output.get("label") is None:
                    continue
                new_outputs.append(workflow_output)
            step["workflow_outputs"] = new_outputs

    def _apply_upgrade_subworkflow(self, action: UpgradeSubworkflowAction, execution: RefactorActionExecution):
        step_def = self._find_step(action.step)
        assert step_def["content_id"] is not None
        trans = self.module_injector.trans
        content_id = action.content_id
        if content_id is None:
            old_workflow = trans.app.workflow_manager.get_owned_workflow(trans, step_def["content_id"])
            stored_workflow = old_workflow.stored_workflow
            content_id = trans.security.encode_id(stored_workflow.latest_workflow.id)
        step_def["content_id"] = content_id
        step = self.workflow.steps[step_def["id"]]
        new_workflow = trans.app.workflow_manager.get_owned_workflow(trans, content_id)
        step.subworkflow = new_workflow
        self._inject_for_updated_step(step, execution)

        self._patch_step(execution, step, step_def)

    def _apply_upgrade_tool(self, action: UpgradeToolAction, execution: RefactorActionExecution):
        step_def = self._find_step(action.step)
        tool_id = step_def["content_id"]
        trans = self.module_injector.trans
        tool_version = action.tool_version
        if tool_version is None:
            latest_tool = trans.app.toolbox.get_tool(tool_id, get_all_versions=True)[-1]
            tool_version = latest_tool.version
            tool_id = latest_tool.id
        step = self.workflow.steps[step_def["id"]]
        step.tool_id = tool_id
        step.tool_version = tool_version
        self._inject_for_updated_step(step, execution)
        step_def["tool_version"] = tool_version
        step_def["tool_state"] = step.module.get_tool_state()
        if step_def.get("tool_id"):
            step_def["tool_id"] = step.module.get_content_id()
        if step_def.get("content_id"):
            step_def["content_id"] = step.module.get_content_id()
        self._patch_step(execution, step, step_def)

    def _apply_upgrade_all_steps(self, action: UpgradeAllStepsAction, execution: RefactorActionExecution):
        for step_order_index, step in self._as_dict["steps"].items():
            if step.get("type") == "subworkflow":
                step_action_s = UpgradeSubworkflowAction(
                    action_type="upgrade_subworkflow", step={"order_index": step_order_index}
                )
                self._apply_upgrade_subworkflow(step_action_s, execution)
            elif step.get("type") == "tool":
                step_action_t = UpgradeToolAction(action_type="upgrade_tool", step={"order_index": step_order_index})
                self._apply_upgrade_tool(step_action_t, execution)

    def _find_step(self, step_reference: step_reference_union):
        order_index = None
        if isinstance(step_reference, StepReferenceByLabel):
            label = step_reference.label
            if not label:
                raise RequestParameterInvalidException("Empty label provided.")
            for step_order_index, step in self._as_dict["steps"].items():
                if step["label"] == label:
                    order_index = step_order_index
                    break
        else:
            order_index = step_reference.order_index
        if order_index is None:
            raise RequestParameterInvalidException(f"Failed to resolve step_reference {step_reference}")
        if len(self._as_dict["steps"]) <= order_index:
            raise RequestParameterInvalidException(f"Failed to resolve step_reference {step_reference}")
        return self._as_dict["steps"][order_index]

    def _find_step_for_action(self, action):
        step_reference = action.step
        return self._find_step(step_reference)

    def _find_step_with_module_for_action(self, action, execution):
        step_reference = action.step
        step_def = self._find_step(step_reference)
        step = self.workflow.steps[step_def["id"]]
        return self._inject(step, execution)

    def _step_with_module(self, order_index, execution):
        step = self.workflow.steps[order_index]
        return self._inject(step, execution)

    def _iterate_over_step_pairs(self, execution):
        # walk over both the dict-ified steps and the model steps (ensuring)
        # module is attached.
        for order_index, step_def in self._as_dict["steps"].items():
            if order_index >= len(self.workflow.steps):
                # newly added step during refactoring, don't iterate over it...
                continue
            else:
                step = self._step_with_module(order_index, execution)
                yield step_def, step

    def _inject_for_updated_step(self, step, execution):
        step.clear_module_extras()
        return self._inject(step, execution)

    def _inject(self, step, execution):
        # compute runtime state, capture upgrade messages that result
        if not hasattr(step, "module"):
            self.module_injector.inject(step)
        self.module_injector.compute_runtime_state(step)
        if getattr(step, "upgrade_messages", None):
            for key, value in step.upgrade_messages.items():
                message = RefactorActionExecutionMessage(
                    message=value,
                    message_type=RefactorActionExecutionMessageTypeEnum.tool_state_adjustment,
                    input_name=key,
                    step_label=step.label,
                    order_index=step.order_index,
                )
                execution.messages.append(message)
        if getattr(step.module, "version_changes", None):
            for version_change in step.module.version_changes:
                message = RefactorActionExecutionMessage(
                    message=version_change,
                    message_type=RefactorActionExecutionMessageTypeEnum.tool_version_change,
                    step_label=step.label,
                    order_index=step.order_index,
                )
                execution.messages.append(message)

        return step

    def _iterate_over_rename_pjas(self):
        for _, step_def in self._as_dict["steps"].items():
            if step_def["type"] != "tool":
                continue
            post_job_actions = step_def.get("post_job_actions", [])
            for post_job_action in post_job_actions.values():
                if post_job_action["action_type"] == "RenameDatasetAction":
                    yield post_job_action

    def _add_input_get_order_index(self, input_action: AddInputAction, execution: RefactorActionExecution):
        self._apply_add_input(input_action, execution)
        return len(self._as_dict["steps"]) - 1

    def _input_from_action(self, action):
        input_reference = action.input
        input_step_dict = self._find_step(input_reference)
        input_name = input_reference.input_name
        return input_step_dict, input_name

    def _connection(self, action):
        input_step_dict, input_name = self._input_from_action(action)
        output_reference = action.output
        output_step_dict = self._find_step(output_reference)
        output_name = output_reference.output_name
        return input_step_dict, input_name, output_step_dict, output_name

    def _patch_step(self, execution, step, step_def):
        """
        patch a workflow step after upgrading the tool / subworkflow
        """
        # TODO: find workflow outputs that need to be dropped and report them
        upgrade_inputs = step.module.get_all_inputs()
        upgrade_outputs = step.module.get_all_outputs()
        upgrade_output_names = {u["name"] for u in upgrade_outputs}
        upgrade_order_index = step_def["id"]
        upgrade_label = step_def.get("label")
        all_input_connections = step_def.get("input_connections")
        inputs_to_delete = []
        for input_name, input_connections in all_input_connections.items():
            # try and find an input connection for each input
            matching_input = None
            for upgrade_input in upgrade_inputs:
                if upgrade_input["name"] == input_name:
                    matching_input = upgrade_input
                    break

            # In the future check parameter type, format, mapping status...
            if matching_input is None:
                inputs_to_delete.append(input_name)
                for input_connection in _listify_connections(input_connections):
                    message_text = (
                        f"Tool or subworkflow input '{input_name}' no longer available, dropping connection to it."
                    )
                    from_order_index = input_connection["id"]
                    from_step_label = self._as_dict["steps"].get(from_order_index, {}).get("label")
                    message = RefactorActionExecutionMessage(
                        message=message_text,
                        message_type=RefactorActionExecutionMessageTypeEnum.connection_drop_forced,
                        input_name=input_name,
                        step_label=upgrade_label,
                        order_index=upgrade_order_index,
                        output_name=input_connection["output_name"],
                        from_order_index=from_order_index,
                        from_step_label=from_step_label,
                    )
                    execution.messages.append(message)

        for input_name in inputs_to_delete:
            del all_input_connections[input_name]

        for _, step in self._as_dict["steps"].items():
            all_input_connections = step.get("input_connections")
            for input_name, input_connections in all_input_connections.items():
                rebuilt_valid_connections = []
                for input_connection in _listify_connections(input_connections):
                    include = False
                    if input_connection["id"] != upgrade_order_index:
                        include = True
                    else:
                        output_name = input_connection["output_name"]
                        if output_name in upgrade_output_names:
                            include = True
                        else:
                            # dropped outputs
                            message_text = f"Tool or subworkflow output '{output_name}' no longer available, dropping connection from it."
                            message = RefactorActionExecutionMessage(
                                message=message_text,
                                message_type=RefactorActionExecutionMessageTypeEnum.connection_drop_forced,
                                input_name=input_name,
                                step_label=step.get("label"),
                                order_index=step["id"],
                                output_name=output_name,
                                from_step_label=upgrade_label,
                                from_order_index=upgrade_order_index,
                            )
                            execution.messages.append(message)
                    if include:
                        rebuilt_valid_connections.append(input_connection)
                all_input_connections[input_name] = rebuilt_valid_connections

        workflow_outputs_to_delete = []
        for workflow_output in step_def.get("workflow_outputs", []):
            output_label = workflow_output.get("label")
            output_name = workflow_output["output_name"]
            if not output_label:
                continue

            if output_name not in upgrade_output_names:
                workflow_outputs_to_delete.append(workflow_output)
                message_text = f"Subworkflow output '{output_name}' no longer available, dropping corresponding workflow output label {output_label}."
                message = RefactorActionExecutionMessage(
                    message=message_text,
                    message_type=RefactorActionExecutionMessageTypeEnum.workflow_output_drop_forced,
                    step_label=upgrade_label,
                    order_index=upgrade_order_index,
                    output_name=workflow_output.get("output_name"),
                    output_label=output_label,
                )
                execution.messages.append(message)

    @staticmethod
    def normalize_input_connections_to_list(all_input_connections, input_name, add_if_missing=False):
        if add_if_missing and input_name not in all_input_connections:
            all_input_connections[input_name] = []
        input_connections = all_input_connections[input_name]
        all_input_connections[input_name] = _listify_connections(input_connections)

    @property
    def _as_dict(self):
        return self.raw_workflow_description.as_dict


def _listify_connections(input_connections):
    if not isinstance(input_connections, list):
        return [input_connections]
    return input_connections

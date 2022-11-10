import logging
import os
from typing import (
    Any,
    Dict,
)

from rocrate.model.computationalworkflow import (
    ComputationalWorkflow,
    WorkflowDescription,
)
from rocrate.model.contextentity import ContextEntity
from rocrate.model.softwareapplication import SoftwareApplication
from rocrate.rocrate import ROCrate

from galaxy.model import Workflow, WorkflowInvocation, WorkflowStep

logger = logging.getLogger(__name__)


class WorkflowRunCrateProfileBuilder:
    def __init__(self, model_store: Any):
        self.model_store = model_store
        self.invocation: WorkflowInvocation = model_store.included_invocations[0]
        self.workflow: Workflow = self.invocation.workflow
        self.input_type_to_param_type = {
            "parameter": "parameter-type#TODO",
            "dataset": "File",
            "dataset_collection": "collection#TODO",
        }

    def build_crate(self):
        crate = ROCrate()
        file_entities = self._add_files(crate)
        self._add_workflows(crate)
        self._add_actions(crate, file_entities)
        return crate

    def _add_files(self, crate: ROCrate) -> Dict[int, Any]:
        file_entities = {}
        for dataset, _ in self.model_store.included_datasets.values():
            if dataset.dataset.id in self.model_store.dataset_id_to_path:
                file_name, _ = self.model_store.dataset_id_to_path[dataset.dataset.id]
                name = dataset.name
                encoding_format = dataset.datatype.get_mime()
                properties = {
                    "name": name,
                    "encodingFormat": encoding_format,
                }
                file_entity = crate.add_file(
                    file_name,
                    dest_path=file_name,
                    properties=properties,
                )
                file_entities[dataset.dataset.id] = file_entity
        return file_entities

    def _add_workflows(self, crate: ROCrate):
        workflows_directory = self.model_store.workflows_directory

        if os.path.exists(workflows_directory):
            for filename in os.listdir(workflows_directory):
                is_computational_wf = not filename.endswith(".cwl")
                workflow_cls = ComputationalWorkflow if is_computational_wf else WorkflowDescription
                lang = "galaxy" if not filename.endswith(".cwl") else "cwl"
                dest_path = os.path.join("workflows", filename)

                crate.add_workflow(
                    source=os.path.join(workflows_directory, filename),
                    dest_path=dest_path,
                    main=is_computational_wf,
                    cls=workflow_cls,
                    lang=lang,
                )
            crate.mainEntity["name"] = self.workflow.name

    def _add_engine_run(self, crate: ROCrate):
        roc_engine = crate.add(SoftwareApplication(crate, properties={"name": "Galaxy workflow engine"}))
        roc_engine_run = crate.add(
            ContextEntity(
                crate,
                properties={
                    "@type": "OrganizeAction",
                    "name": f"Run of {roc_engine['name']}",
                    "startTime": self.invocation.create_time.isoformat(),
                },
            )
        )
        roc_engine_run["instrument"] = roc_engine
        # TODO: add engine Agent?
        self.roc_engine_run = roc_engine_run

    def _add_actions(self, crate: ROCrate, file_entities: Dict[int, Any]):

        input_formal_params = []
        for step in self.workflow.input_steps:
            formal_param = self._add_formal_parameter(crate, step)
            input_formal_params.append(formal_param)

        wf_input_values_ids = [{"@id": entity.id} for entity in input_formal_params]
        crate.mainEntity["input"] = wf_input_values_ids

        output_formal_params = []
        workflow_outputs = []
        for output_step in self.workflow.workflow_outputs:
            formal_param = self._add_formal_parameter(crate, step)
            output_formal_params.append(formal_param)

            output_obj = self.invocation.get_output_object(output_step.label)
            output_file_entity = file_entities.get(output_obj.dataset.id)
            if output_file_entity:
                logger.debug(f"[FOUND] label: {output_step.label} -> obj.id: {output_obj.id}")
                workflow_outputs.append(output_file_entity)

        wf_output_param_ids = [{"@id": entity.id} for entity in output_formal_params]
        crate.mainEntity["output"] = wf_output_param_ids
        wf_output_ids = [{"@id": output.id} for output in workflow_outputs]

        input_values = []
        for param in self.invocation.input_parameters:
            input_param_value = crate.add(
                ContextEntity(
                    crate,
                    properties={
                        "@type": "PropertyValue",
                        # "exampleOfWork": {"@id": "#verbose-param"},
                        "name": param.name,
                        "value": param.value,
                    },
                )
            )
            input_values.append(input_param_value)
        wf_input_values_ids = [{"@id": entity.id} for entity in input_values]

        input_param_value = crate.add(
            ContextEntity(
                crate,
                properties={
                    "@type": "CreateAction",
                    "name": self.workflow.name,
                    "object": wf_input_values_ids,
                    "result": wf_output_ids,
                },
            )
        )
        self.main_action = input_param_value

    def _add_formal_parameter(self, crate: ROCrate, step: WorkflowStep):
        return crate.add(
            ContextEntity(
                crate,
                properties={
                    "@type": "FormalParameter",
                    "additionalType": self.input_type_to_param_type[step.input_type],
                    "description": "TODO",  # ",".join(input_step.annotations),
                    "name": step.label,
                    "valueRequired": not step.input_optional,
                },
            )
        )

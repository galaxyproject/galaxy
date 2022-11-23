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

from galaxy.model import Workflow, WorkflowInvocation, WorkflowStep, JobParameter

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
            logger.info("dataset: %s" % (dataset.dataset.id,))
            logger.info("dataset_id_to_path: %s" % str(self.model_store.dataset_id_to_path))
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
                logger.info("FN:",file_name)
                logger.info("NAME:",name)
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
        for output_step in self.workflow.input_steps:
            formal_param = self._add_formal_parameter(crate, output_step)
            input_formal_params.append(formal_param)

        wf_input_values_ids = [{"@id": entity.id} for entity in input_formal_params]
        crate.mainEntity["input"] = wf_input_values_ids

        output_formal_params = []
        workflow_outputs = []
        input_values = []
        for output_step in self.invocation.steps:
            for job in output_step.jobs:
                for job_output in job.output_datasets:
                    formal_param = self._add_formal_output_parameter(crate, output_step.workflow_step)
                    output_formal_params.append(formal_param)
                    dataset_id = job_output.dataset.dataset.id
                    output_file_entity = file_entities.get(dataset_id)
                    workflow_outputs.append(output_file_entity)
                for param in job.parameters:
                    property_value = self._add_property_value(crate, param)
                    input_values.append(property_value)


        wf_output_param_ids = [{"@id": entity.id} for entity in output_formal_params]
        crate.mainEntity["output"] = wf_output_param_ids
        wf_output_ids = [{"@id": output.id} for output in workflow_outputs if output]
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
                    "description": step.annotations[0].annotation if step.annotations else "",
                    "name": step.label,
                    "valueRequired": not step.input_optional,
                },
            )
        )

    def _add_formal_output_parameter(self, crate: ROCrate, step: WorkflowStep):
        # TODO: add more details for output formal definitions?
        return crate.add(
            ContextEntity(
                crate,
                properties={
                    "@type": "FormalParameter",
                    "additionalType": "File",  # TODO: always a dataset/File?
                    "description": step.annotations[0].annotation if step.annotations else "",
                    "name": step.label,
                },
            )
        )

    def _add_property_value(self, crate: ROCrate, param: JobParameter):
        # TODO: 
        return crate.add(
                ContextEntity(
                    crate,
                    properties={
                        "@type": "PropertyValue",
                        "name": param.name,
                        "value": param.value,
                    },
                )
            )

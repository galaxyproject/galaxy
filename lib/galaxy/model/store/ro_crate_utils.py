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

from galaxy.model import (
    Workflow, WorkflowInvocation, WorkflowStep, 
    JobParameter, WorkflowRequestInputStepParameter,
    JobToInputDatasetAssociation, JobToOutputDatasetAssociation
)

logger = logging.getLogger(__name__)


class WorkflowRunCrateProfileBuilder:
    def __init__(self, model_store: Any):
        self.model_store = model_store
        self.invocation: WorkflowInvocation = model_store.included_invocations[0]
        self.workflow: Workflow = self.invocation.workflow
        # TODO: add more param types
        self.param_type_mapping = {
            "integer": "Integer",
            # "dataset": "File",
            # "dataset_collection": "collection#TODO",
        }
        self.ignored_parameter_type = [
            "queries",
            "input1",
            "__workflow_invocation_uuid__",
            "chromInfo",
            "dbkey",
            "__input_ext"
        ]

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
            logger.info("dataset name: %s" % (dataset.name))
            logger.info("dataset_id_to_path: %s" % str(self.model_store.dataset_id_to_path))
            if dataset.dataset.id in self.model_store.dataset_id_to_path:
                file_name, _ = self.model_store.dataset_id_to_path[dataset.dataset.id]
                if not file_name:
                    file_name = "datasets/dataset_"+str(dataset.dataset.id)
                name = dataset.name
                encoding_format = dataset.datatype.get_mime()
                properties = {
                    "name": name,
                    "encodingFormat": encoding_format,
                    "exampleOfWork": {"@id": dataset.dataset.uuid.urn},
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
        output_formal_params = []
        workflow_inputs = []
        workflow_outputs = []

        # TODO: Move PropertyValue creation to separate function?
        for param in self.invocation.input_step_parameters:
            property_value = self._add_property_value(crate, param)
            workflow_inputs.append(property_value)
            formal_param = self._add_formal_parameter(crate, param.workflow_step)
            input_formal_params.append(formal_param)

        for output_step in self.invocation.steps:
            for job in output_step.jobs:
                for job_input in job.input_datasets:
                    formal_param = self._add_formal_parameter_input(crate, job_input)
                    input_formal_params.append(formal_param)
                    dataset_id = job_input.dataset.dataset.id
                    input_file_entity = file_entities.get(dataset_id)
                    workflow_inputs.append(input_file_entity)
                for job_output in job.output_datasets:
                    formal_param = self._add_formal_parameter_output(crate, job_output)
                    output_formal_params.append(formal_param)
                    dataset_id = job_output.dataset.dataset.id
                    output_file_entity = file_entities.get(dataset_id)
                    workflow_outputs.append(output_file_entity)

        wf_input_param_ids = [{"@id": entity.id} for entity in input_formal_params]
        crate.mainEntity["input"] = wf_input_param_ids
        wf_input_ids = [{"@id": input.id} for input in workflow_inputs if input]
        wf_output_param_ids = [{"@id": entity.id} for entity in output_formal_params]
        crate.mainEntity["output"] = wf_output_param_ids
        wf_output_ids = [{"@id": output.id} for output in workflow_outputs if output]

        input_param_value = crate.add(
            ContextEntity(
                crate,
                properties={
                    "@type": "CreateAction",
                    "name": self.workflow.name,
                    "object": wf_input_ids,
                    "result": wf_output_ids,
                },
            )
        )
        self.main_action = input_param_value

    def _add_formal_parameter(self, crate: ROCrate, step: WorkflowStep):
        return crate.add(
            ContextEntity(
                crate,
                step.uuid.urn,
                properties={
                    "@type": "FormalParameter",
                    "additionalType": self.param_type_mapping[step.annotations[0].workflow_step.tool_inputs['parameter_type']],
                    "description": step.annotations[0].annotation if step.annotations else "",
                    "name": step.label,
                    "valueRequired": not step.input_optional,
                },
            )
        )

    def _add_formal_parameter_input(self, crate: ROCrate, input: JobToInputDatasetAssociation):
        # TODO: add more details for output formal definitions?
        return crate.add(
            ContextEntity(
                crate,
                input.dataset.dataset.uuid.urn,
                properties={
                    "@type": "FormalParameter",
                    "additionalType": "File",  # TODO: always a dataset/File?
                    # "description": step.annotations[0].annotation if step.annotations else "",
                    "name": input.name,
                },
            )
        )
        
    def _add_formal_parameter_output(self, crate: ROCrate, output: JobToOutputDatasetAssociation):
        # TODO: add more details for output formal definitions?
        return crate.add(
            ContextEntity(
                crate,
                output.dataset.dataset.uuid.urn,
                properties={
                    "@type": "FormalParameter",
                    "additionalType": "File",  # TODO: always a dataset/File?
                    # "description": step.annotations[0].annotation if step.annotations else "",
                    "name": output.name,
                },
            )
        )

    def _add_property_value(self, crate: ROCrate, param: WorkflowRequestInputStepParameter):
        # TODO: 
        return crate.add(
                ContextEntity(
                    crate,
                    str(param.workflow_step.output_connections[0].input_name)+"-pv",
                    properties={
                        "@type": "PropertyValue",
                        "name": param.workflow_step.output_connections[0].input_name,
                        "value": param.parameter_value,
                        "exampleOfWork": {"@id": param.workflow_step.uuid.urn},
                    },
                )
            )

import logging
import os
from typing import (
    Any,
    Dict,
    Optional,
)

from rocrate.model.computationalworkflow import (
    ComputationalWorkflow,
    WorkflowDescription,
)
from rocrate.model.contextentity import ContextEntity
from rocrate.model.softwareapplication import SoftwareApplication
from rocrate.rocrate import ROCrate

from galaxy.model import (
    JobParameter,
    JobToInputDatasetAssociation,
    JobToOutputDatasetAssociation,
    Workflow,
    WorkflowInvocation,
    WorkflowInvocationStep,
    WorkflowRequestInputStepParameter,
    WorkflowStep,
)

logger = logging.getLogger(__name__)


class WorkflowRunCrateProfileBuilder:
    def __init__(self, model_store: Any):
        self.model_store = model_store
        self.invocation: WorkflowInvocation = model_store.included_invocations[0]
        self.workflow: Workflow = self.invocation.workflow
        self.param_type_mapping = {
            "integer": "Integer",
            "text": "Text",
            "float": "Float",
            "boolean": "Boolean",
            "genomebuild": "File",
            "select": "DataType",
            "color": "Color",
            "group_tag": "DataType",
            "data_column": "Text",
            "hidden": "DataType",
            "hidden_data": "DataType",
            "baseurl": "URL",
            "file": "File",
            "ftpfile": "File",
            "data": "File",
            "data_collection": "Collection",
            "library_data": "File",
            "rules": "Text",
            "directory_uri": "URI",
            "drill_down": "Text",
            None: "None",
        }

        self.ignored_parameter_type = [
            "queries",
            "inputs",
            "input",
            "input1",
            "__workflow_invocation_uuid__",
            "chromInfo",
            "dbkey",
            "__input_ext",
        ]
        self.pv_entities: Dict[str, Any] = {}

    def build_crate(self):
        crate = ROCrate()
        file_entities = self._add_files(crate)
        self._add_collections(crate, file_entities)
        self._add_workflows(crate)
        self._add_engine_run(crate)
        self._add_actions(crate, file_entities)
        return crate

    def _add_files(self, crate: ROCrate) -> Dict[int, Any]:
        file_entities: Dict[int, Any] = {}
        for dataset, _ in self.model_store.included_datasets.values():
            if dataset.dataset.id in self.model_store.dataset_id_to_path:
                filename, _ = self.model_store.dataset_id_to_path[dataset.dataset.id]
                if not filename:
                    filename = f"datasets/dataset_{dataset.dataset.uuid}"
                name = dataset.name
                encoding_format = dataset.datatype.get_mime()
                properties = {
                    "name": name,
                    "encodingFormat": encoding_format,
                    "exampleOfWork": {"@id": dataset.dataset.uuid.urn},
                }
                file_entity = crate.add_file(
                    filename,
                    dest_path=filename,
                    properties=properties,
                )
                file_entities[dataset.dataset.id] = file_entity
        return file_entities

    def _add_collections(self, crate: ROCrate, file_entities: Dict[int, Any]) -> Dict[int, Any]:
        collection_entities: Dict[int, Any] = {}
        for collection in self.model_store.included_collections:
            name = collection.name
            dataset_ids = []
            for dataset in collection.dataset_instances:
                if dataset.dataset:
                    dataset_id = file_entities.get(dataset.dataset.id)
                    if dataset_id:
                        dataset_ids.append({"@id": dataset_id.id})

            properties = {
                "name": name,
                "@type": "Collection",
                "additionalType": collection.collection.collection_type,
                "hasPart": dataset_ids,
            }
            collection_entity = crate.add(
                ContextEntity(
                    crate,
                    collection.type_id,
                    properties=properties,
                )
            )
            collection_entities[collection.collection.id] = collection_entity

        crate.root_dataset["mentions"] = [{"@id": coll.id} for coll in collection_entities.values() if coll]
        return collection_entities

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

            crate.license = self.workflow.license or ""
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
        self.roc_engine_run = roc_engine_run

    def _add_actions(self, crate: ROCrate, file_entities: Dict[int, Any]):
        input_formal_params: Dict[int, Any] = {}
        output_formal_params = []
        workflow_inputs = []
        workflow_outputs = []

        for param in self.invocation.input_step_parameters:
            property_value = self._add_wf_property_value(crate, param)
            workflow_inputs.append(property_value)
            formal_param = self._add_formal_parameter(crate, param.workflow_step)
            input_formal_params[formal_param.id] = formal_param

        for output_step in self.invocation.steps:
            for job in output_step.jobs:
                for job_input in job.input_datasets:
                    formal_param = self._add_formal_parameter_input(crate, job_input)
                    input_formal_params[formal_param.id] = formal_param
                    dataset_id = job_input.dataset.dataset.id
                    input_file_entity = file_entities.get(dataset_id)
                    workflow_inputs.append(input_file_entity)
                for job_output in job.output_datasets:
                    formal_param = self._add_formal_parameter_output(crate, job_output)
                    output_formal_params.append(formal_param)
                    dataset_id = job_output.dataset.dataset.id
                    output_file_entity = file_entities.get(dataset_id)
                    workflow_outputs.append(output_file_entity)
                for param in job.parameters:
                    if param.name not in self.ignored_parameter_type and not param.name.startswith("__"):
                        property_value = self._add_job_property_value(crate, param)
                        workflow_inputs.append(property_value)
                        formal_param = self._add_formal_parameter(crate, output_step.workflow_step, param.name)
                        input_formal_params[formal_param.id] = formal_param
            if output_step.workflow_step.type == "parameter_input":
                property_value = self._add_param_property_value(crate, output_step)
                workflow_inputs.append(property_value)
                formal_param = self._add_formal_parameter(crate, output_step.workflow_step)
                input_formal_params[formal_param.id] = formal_param
            if output_step.workflow_step.type == "tool":
                for tool_input in output_step.workflow_step.tool_inputs.keys():
                    if tool_input not in self.ignored_parameter_type and not tool_input.startswith("__"):
                        property_value = self._add_tool_property_value(crate, output_step, tool_input)
                        workflow_inputs.append(property_value)
                        formal_param = self._add_formal_parameter(crate, output_step.workflow_step, tool_input)
                        input_formal_params[formal_param.id] = formal_param

        wf_input_param_ids = [{"@id": entity.id} for entity in input_formal_params.values()]
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
                    "instrument": {"@id": crate.mainEntity["@id"]},
                    "object": wf_input_ids,
                    "result": wf_output_ids,
                },
            )
        )
        self.main_action = input_param_value

    def _add_formal_parameter(self, crate: ROCrate, step: WorkflowStep, tool_input: Optional[str] = None):
        param_id = ""
        param_type = None
        if not tool_input:
            if step.output_connections:
                param_id = step.output_connections[0].input_name
            if step.annotations:
                param_type = step.annotations[0].workflow_step.tool_inputs.get("parameter_type")
            if step.tool_inputs:
                param_type = param_type or step.tool_inputs.get("parameter_type")
        else:
            param_id = tool_input

        return crate.add(
            ContextEntity(
                crate,
                f"{param_id}-param",
                properties={
                    "@type": "FormalParameter",
                    "additionalType": self.param_type_mapping[param_type],
                    "description": step.annotations[0].annotation if step.annotations else "",
                    "name": f"{step.label} parameter",
                    "valueRequired": not step.input_optional,
                },
            )
        )

    def _add_formal_parameter_input(self, crate: ROCrate, input: JobToInputDatasetAssociation):
        return crate.add(
            ContextEntity(
                crate,
                input.dataset.dataset.uuid.urn,
                properties={
                    "@type": "FormalParameter",
                    "additionalType": "File",  # TODO: always a dataset/File?
                    "description": input.dataset.annotations[0].annotation
                    if input.dataset.annotations
                    else input.dataset.info or "",
                    "name": input.name,
                },
            )
        )

    def _add_formal_parameter_output(self, crate: ROCrate, output: JobToOutputDatasetAssociation):
        return crate.add(
            ContextEntity(
                crate,
                output.dataset.dataset.uuid.urn,
                properties={
                    "@type": "FormalParameter",
                    "additionalType": "File",  # TODO: always a dataset/File?
                    "description": output.dataset.annotations[0].annotation
                    if output.dataset.annotations
                    else output.dataset.info or "",
                    "name": output.name,
                },
            )
        )

    def _add_job_property_value(self, crate: ROCrate, param: JobParameter):
        input_name = param.name
        if self.pv_entities.get(input_name):
            return
        job_pv = crate.add(
            ContextEntity(
                crate,
                f"{input_name}-pv",
                properties={
                    "@type": "PropertyValue",
                    "name": input_name,
                    "value": param.value,
                    "exampleOfWork": {"@id": f"#{input_name}-param"},
                },
            )
        )
        self.pv_entities[input_name] = job_pv
        return job_pv

    def _add_wf_property_value(self, crate: ROCrate, param: WorkflowRequestInputStepParameter):
        input_name = param.workflow_step.output_connections[0].input_name
        if self.pv_entities.get(input_name):
            return
        wf_pv = crate.add(
            ContextEntity(
                crate,
                f"{input_name}-pv",
                properties={
                    "@type": "PropertyValue",
                    "name": input_name,
                    "value": param.parameter_value,
                    "exampleOfWork": {"@id": f"#{input_name}-param"},
                },
            )
        )
        self.pv_entities[input_name] = wf_pv
        return wf_pv

    def _add_tool_property_value(self, crate: ROCrate, invocation_step: WorkflowInvocationStep, tool_input: str):
        if self.pv_entities.get(tool_input):
            return
        tool_pv = crate.add(
            ContextEntity(
                crate,
                f"{tool_input}-pv",
                properties={
                    "@type": "PropertyValue",
                    "name": tool_input,
                    "value": invocation_step.workflow_step.tool_inputs[tool_input],
                    "exampleOfWork": {"@id": f"#{tool_input}-param"},
                },
            )
        )
        self.pv_entities[tool_input] = tool_pv
        return tool_pv

    def _add_param_property_value(self, crate: ROCrate, invocation_step: WorkflowInvocationStep):
        input_name = invocation_step.workflow_step.output_connections[0].input_name
        if self.pv_entities.get(input_name):
            return
        param_pv = crate.add(
            ContextEntity(
                crate,
                f"{input_name}-pv",
                properties={
                    "@type": "PropertyValue",
                    "name": invocation_step.workflow_step.label,
                    "value": invocation_step.output_value.value,
                    "exampleOfWork": {"@id": f"#{input_name}-param"},
                },
            )
        )
        self.pv_entities[input_name] = param_pv
        return param_pv

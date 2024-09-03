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
from rocrate.model.file import File
from rocrate.model.softwareapplication import SoftwareApplication
from rocrate.rocrate import ROCrate

from galaxy.model import (
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    Workflow,
    WorkflowInvocation,
    WorkflowInvocationStep,
)

logger = logging.getLogger(__name__)


PROFILES_VERSION = "0.1"
WROC_PROFILE_VERSION = "1.0"

GALAXY_EXPORT_VERSION = "2.0"

ATTRS_FILENAME_HISTORY = "history_attrs.txt"
ATTRS_FILENAME_DATASETS = "datasets_attrs.txt"
ATTRS_FILENAME_JOBS = "jobs_attrs.txt"
ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS = "implicit_collection_jobs_attrs.txt"
ATTRS_FILENAME_COLLECTIONS = "collections_attrs.txt"
ATTRS_FILENAME_EXPORT = "export_attrs.txt"
ATTRS_FILENAME_LIBRARIES = "libraries_attrs.txt"
ATTRS_FILENAME_LIBRARY_FOLDERS = "library_folders_attrs.txt"
ATTRS_FILENAME_INVOCATIONS = "invocation_attrs.txt"


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
        self.workflow_entities: Dict[int, Any] = {}
        self.collection_entities: Dict[int, Any] = {}
        self.file_entities: Dict[int, Any] = {}
        self.param_entities: Dict[int, Any] = {}
        self.pv_entities: Dict[str, Any] = {}

    def build_crate(self):
        crate = ROCrate()
        self._add_workflows(crate)
        self._add_engine_run(crate)
        self._add_create_action(crate)
        self._add_collections(crate)
        self._add_files(crate)
        self._add_profiles(crate)
        self._add_parameters(crate)
        self._add_attrs_files(crate)
        return crate

    def _add_file(self, dataset: HistoryDatasetAssociation, properties: Dict[Any, Any], crate: ROCrate) -> File:
        if dataset.dataset.id in self.model_store.dataset_id_to_path:
            filename, _ = self.model_store.dataset_id_to_path[dataset.dataset.id]
            if not filename:
                # dataset was not serialized
                filename = f"datasets/dataset_{dataset.dataset.uuid}"
                source = None
            else:
                source = os.path.join(self.model_store.export_directory, filename)
            name = dataset.name
            encoding_format = dataset.datatype.get_mime()
            properties["name"] = name
            properties["encodingFormat"] = encoding_format
            file_entity = crate.add_file(
                source,
                dest_path=filename,
                properties=properties,
            )
            self.file_entities[dataset.dataset.id] = file_entity

            return file_entity

    def _add_files(self, crate: ROCrate):
        for wfda in self.invocation.input_datasets:
            if not self.file_entities.get(wfda.dataset.dataset.id):
                properties = {
                    "exampleOfWork": {"@id": f"#{wfda.dataset.dataset.uuid}"},
                }
                file_entity = self._add_file(wfda.dataset, properties, crate)
                dataset_formal_param = self._add_dataset_formal_parameter(wfda.dataset, crate)
                crate.mainEntity.append_to("input", dataset_formal_param)
                self.create_action.append_to("object", file_entity)

        for wfda in self.invocation.output_datasets:
            if not self.file_entities.get(wfda.dataset.dataset.id):
                properties = {
                    "exampleOfWork": {"@id": f"#{wfda.dataset.dataset.uuid}"},
                }
                file_entity = self._add_file(wfda.dataset, properties, crate)
                dataset_formal_param = self._add_dataset_formal_parameter(wfda.dataset, crate)
                crate.mainEntity.append_to("output", dataset_formal_param)
                self.create_action.append_to("result", file_entity)

    def _add_collection(self, hdca: HistoryDatasetCollectionAssociation, crate: ROCrate) -> ContextEntity:
        name = hdca.name
        dataset_ids = []
        for hda in hdca.dataset_instances:
            if hda.dataset:
                properties: Dict[Any, Any] = {}
                self._add_file(hda, properties, crate)
                dataset_id = self.file_entities.get(hda.dataset.id)
                if dataset_id:
                    if {"@id": dataset_id.id} not in dataset_ids:
                        dataset_ids.append({"@id": dataset_id.id})

        collection_properties = {
            "name": name,
            "@type": "Collection",
            "additionalType": self._get_collection_additional_type(hdca.collection.collection_type),
            "hasPart": dataset_ids,
            "exampleOfWork": {"@id": f"#{hdca.type_id}-param"},
        }
        collection_entity = crate.add(
            ContextEntity(
                crate,
                hdca.type_id,
                properties=collection_properties,
            )
        )
        self.collection_entities[hdca.collection.id] = collection_entity

        crate.root_dataset.append_to("mentions", collection_entity)

        return collection_entity

    def _get_collection_additional_type(self, collection_type: Optional[str]) -> str:
        if collection_type and "paired" in collection_type:
            return "https://training.galaxyproject.org/training-material/faqs/galaxy/collections_build_list_paired.html"
        return "https://training.galaxyproject.org/training-material/faqs/galaxy/collections_build_list.html"

    def _get_parameter_additional_type(self, parameter_type: Optional[str]) -> str:
        if parameter_type in self.param_type_mapping:
            return self.param_type_mapping[parameter_type]
        return "Text"

    def _add_collections(self, crate: ROCrate):
        for wfdca in self.invocation.input_dataset_collections:
            collection_entity = self._add_collection(wfdca.dataset_collection, crate)
            collection_formal_param = self._add_collection_formal_parameter(wfdca.dataset_collection, crate)
            crate.mainEntity.append_to("input", collection_formal_param)
            self.create_action.append_to("object", collection_entity)

        for wfdca in self.invocation.output_dataset_collections:
            collection_entity = self._add_collection(wfdca.dataset_collection, crate)
            collection_formal_param = self._add_collection_formal_parameter(wfdca.dataset_collection, crate)
            crate.mainEntity.append_to("output", collection_formal_param)
            self.create_action.append_to("result", collection_entity)

    def _add_workflows(self, crate: ROCrate):
        workflows_directory = self.model_store.workflows_directory

        if os.path.exists(workflows_directory):
            for filename in os.listdir(workflows_directory):
                is_main_wf = filename.endswith(".gxwf.yml")
                is_computational_wf = not filename.endswith(".cwl")
                workflow_cls = ComputationalWorkflow if is_computational_wf else WorkflowDescription
                lang = "galaxy" if not filename.endswith(".cwl") else "cwl"
                dest_path = os.path.join("workflows", filename)

                wf = crate.add_workflow(
                    source=os.path.join(workflows_directory, filename),
                    dest_path=dest_path,
                    main=is_main_wf,
                    cls=workflow_cls,
                    lang=lang,
                )
                self.workflow_entities[wf.id] = wf
                if lang == "cwl":
                    cwl_wf = wf

            crate.license = self.workflow.license or ""
            crate.mainEntity["name"] = self.workflow.name
            crate.mainEntity["subjectOf"] = cwl_wf

    def _add_create_action(self, crate: ROCrate):
        self.create_action = crate.add(
            ContextEntity(
                crate,
                properties={
                    "@type": "CreateAction",
                    "name": self.workflow.name,
                    "startTime": self.invocation.workflow.create_time.isoformat(),
                    "endTime": self.invocation.workflow.update_time.isoformat(),
                    "instrument": {"@id": crate.mainEntity["@id"]},
                },
            )
        )
        crate.root_dataset.append_to("mentions", self.create_action)

    def _add_engine_run(self, crate: ROCrate):
        roc_engine = crate.add(SoftwareApplication(crate, properties={"name": "Galaxy workflow engine"}))
        roc_engine_run = crate.add(
            ContextEntity(
                crate,
                properties={
                    "@type": "OrganizeAction",
                    "name": f"Run of {roc_engine['name']}",
                    "startTime": self.invocation.create_time.isoformat(),
                    "endTime": self.invocation.update_time.isoformat(),
                },
            )
        )
        roc_engine_run["instrument"] = roc_engine
        self.roc_engine_run = roc_engine_run

    def _add_attrs_files(self, crate: ROCrate):
        targets = [
            ATTRS_FILENAME_HISTORY,
            ATTRS_FILENAME_DATASETS,
            ATTRS_FILENAME_JOBS,
            ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS,
            ATTRS_FILENAME_COLLECTIONS,
            ATTRS_FILENAME_EXPORT,
            ATTRS_FILENAME_LIBRARIES,
            ATTRS_FILENAME_LIBRARY_FOLDERS,
            ATTRS_FILENAME_INVOCATIONS,
        ]
        for attrs in targets:
            attrs_path = os.path.join(self.model_store.export_directory, attrs)
            description = " ".join(attrs.split("_")[:-1])
            if os.path.exists(attrs_path):
                properties = {
                    "@type": "File",
                    "version": GALAXY_EXPORT_VERSION,
                    "description": f"{description} properties",
                    "encodingFormat": "application/json",
                }
                crate.add_file(
                    attrs_path,
                    dest_path=attrs,
                    properties=properties,
                )

        prov_target = f"{ATTRS_FILENAME_DATASETS}.provenance"
        provenance_attrs_path = os.path.join(self.model_store.export_directory, prov_target)
        description = " ".join(prov_target.split("_")[:-1])
        if os.path.exists(provenance_attrs_path):
            crate.add(
                ContextEntity(
                    crate,
                    prov_target,
                    properties={
                        "@type": "CreativeWork",
                        "version": GALAXY_EXPORT_VERSION,
                        "description": f"{description} provenance properties",
                        "encodingFormat": "application/json",
                    },
                )
            )

    def _add_profiles(self, crate: ROCrate):
        profiles = []
        for p in "process", "workflow":
            id_ = f"https://w3id.org/ro/wfrun/{p}/{PROFILES_VERSION}"
            profiles.append(
                crate.add(
                    ContextEntity(
                        crate,
                        id_,
                        properties={
                            "@type": "CreativeWork",
                            "name": f"{p.title()} Run Crate",
                            "version": PROFILES_VERSION,
                        },
                    )
                )
            )
        # FIXME: in the future, this could go out of sync with the wroc
        # profile added by ro-crate-py to the metadata descriptor
        wroc_profile_id = f"https://w3id.org/workflowhub/workflow-ro-crate/{WROC_PROFILE_VERSION}"
        profiles.append(
            crate.add(
                ContextEntity(
                    crate,
                    wroc_profile_id,
                    properties={
                        "@type": "CreativeWork",
                        "name": "Workflow RO-Crate",
                        "version": WROC_PROFILE_VERSION,
                    },
                )
            )
        )
        crate.root_dataset["conformsTo"] = profiles

    def _add_parameters(self, crate: ROCrate):
        for step in self.invocation.steps:
            if step.workflow_step.type == "parameter_input":
                property_value = self._add_step_parameter_pv(step, crate)
                formal_param = self._add_step_parameter_fp(step, crate)
                crate.mainEntity.append_to("input", formal_param)
                self.create_action.append_to("object", property_value)

    def _add_step_parameter_pv(self, step: WorkflowInvocationStep, crate: ROCrate):
        param_id = step.workflow_step.label
        return crate.add(
            ContextEntity(
                crate,
                f"{param_id}-pv",
                properties={
                    "@type": "PropertyValue",
                    "name": f"{param_id}",
                    "value": step.output_value.value,
                    "exampleOfWork": {"@id": f"#{param_id}-param"},
                },
            )
        )

    def _add_step_parameter_fp(self, step: WorkflowInvocationStep, crate: ROCrate):
        param_id = step.workflow_step.label
        param_type = step.workflow_step.tool_inputs["parameter_type"]
        return crate.add(
            ContextEntity(
                crate,
                f"{param_id}-param",
                properties={
                    "@type": "FormalParameter",
                    "additionalType": self._get_parameter_additional_type(param_type),
                    "description": self._get_association_description(step.workflow_step),
                    "name": f"{param_id}",
                    "valueRequired": str(not step.workflow_step.input_optional),
                },
            )
        )

    def _add_step_tool_pv(self, step: WorkflowInvocationStep, tool_input: str, crate: ROCrate):
        param_id = tool_input
        return crate.add(
            ContextEntity(
                crate,
                f"{param_id}-pv",
                properties={
                    "@type": "PropertyValue",
                    "name": f"{step.workflow_step.label}",
                    "value": step.workflow_step.tool_inputs[tool_input],
                    "exampleOfWork": {"@id": f"#{param_id}-param"},
                },
            )
        )

    def _add_step_tool_fp(self, step: WorkflowInvocationStep, tool_input: str, crate: ROCrate):
        param_id = tool_input
        param_type = "text"
        return ContextEntity(
            crate,
            f"{param_id}-param",
            properties={
                "@type": "FormalParameter",
                "additionalType": self._get_parameter_additional_type(param_type),
                "description": self._get_association_description(step.workflow_step),
                "name": f"{step.workflow_step.label}",
                "valueRequired": str(not step.workflow_step.input_optional),
            },
        )

    def _add_dataset_formal_parameter(self, hda: HistoryDatasetAssociation, crate: ROCrate):
        return crate.add(
            ContextEntity(
                crate,
                str(hda.dataset.uuid),
                properties={
                    "@type": "FormalParameter",
                    "additionalType": "File",
                    "description": self._get_association_description(hda),
                    "name": hda.name,
                },
            )
        )

    def _add_collection_formal_parameter(self, hdca: HistoryDatasetCollectionAssociation, crate: ROCrate):
        return crate.add(
            ContextEntity(
                crate,
                f"{hdca.type_id}-param",
                properties={
                    "@type": "FormalParameter",
                    "additionalType": "Collection",
                    "description": self._get_association_description(hdca),
                    "name": hdca.name,
                },
            )
        )

    def _get_association_description(self, association: Any) -> str:
        if hasattr(association, "annotations"):
            return association.annotations[0].annotation if association.annotations else ""
        elif hasattr(association, "info"):
            return association.info
        return ""

import logging
import os
from typing import (
    Any,
    Dict,
    List,
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
        # Cache for tools to avoid duplicating entities for the same tool
        self.tool_cache: Dict[str, ContextEntity] = {}

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
                dataset_formal_param = self._add_dataset_formal_parameter(wfda.dataset, crate)
                crate.mainEntity.append_to("input", dataset_formal_param)
                properties = {
                    "exampleOfWork": {"@id": dataset_formal_param.id},
                }
                file_entity = self._add_file(wfda.dataset, properties, crate)
                self.create_action.append_to("object", file_entity)

        for wfda in self.invocation.output_datasets:
            if not self.file_entities.get(wfda.dataset.dataset.id):
                dataset_formal_param = self._add_dataset_formal_parameter(wfda.dataset, crate)
                crate.mainEntity.append_to("output", dataset_formal_param)
                properties = {
                    "exampleOfWork": {"@id": dataset_formal_param.id},
                }
                file_entity = self._add_file(wfda.dataset, properties, crate)
                self.create_action.append_to("result", file_entity)

    def _add_collection(
        self, hdca: HistoryDatasetCollectionAssociation, crate: ROCrate, collection_formal_param: ContextEntity
    ) -> ContextEntity:
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
            "exampleOfWork": {"@id": collection_formal_param.id},
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
            collection_formal_param = self._add_collection_formal_parameter(wfdca.dataset_collection, crate)
            collection_entity = self._add_collection(wfdca.dataset_collection, crate, collection_formal_param)
            crate.mainEntity.append_to("input", collection_formal_param)
            self.create_action.append_to("object", collection_entity)

        for wfdca in self.invocation.output_dataset_collections:
            collection_formal_param = self._add_collection_formal_parameter(wfdca.dataset_collection, crate)
            collection_entity = self._add_collection(wfdca.dataset_collection, crate, collection_formal_param)
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

            # Adding multiple creators if available
            if self.workflow.creator_metadata:
                for creator_data in self.workflow.creator_metadata:
                    if creator_data.get("class") == "Person":
                        # Create the person entity
                        creator_entity = crate.add(
                            ContextEntity(
                                crate,
                                creator_data.get("identifier", ""),  # Default to empty string if identifier is missing
                                properties={
                                    "@type": "Person",
                                    "name": creator_data.get("name", ""),  # Default to empty string if name is missing
                                    "orcid": creator_data.get(
                                        "identifier", ""
                                    ),  # Assuming identifier is ORCID, or adjust as needed
                                    "url": creator_data.get("url", ""),  # Add URL if available, otherwise empty string
                                    "email": creator_data.get(
                                        "email", ""
                                    ),  # Add email if available, otherwise empty string
                                },
                            )
                        )
                        # Append the person creator entity to the mainEntity
                        crate.mainEntity.append_to("creator", creator_entity)

                    elif creator_data.get("class") == "Organization":
                        # Create the organization entity
                        organization_entity = crate.add(
                            ContextEntity(
                                crate,
                                creator_data.get(
                                    "url", ""
                                ),  # Use URL as identifier if available, otherwise empty string
                                properties={
                                    "@type": "Organization",
                                    "name": creator_data.get("name", ""),  # Default to empty string if name is missing
                                    "url": creator_data.get("url", ""),  # Add URL if available, otherwise empty string
                                },
                            )
                        )
                        # Append the organization entity to the mainEntity
                        crate.mainEntity.append_to("creator", organization_entity)

            # Add CWL workflow entity if exists
            crate.mainEntity["subjectOf"] = cwl_wf

        # Add tools used in the workflow
        self._add_tools(crate)
        self._add_steps(crate)

    def _add_steps(self, crate: ROCrate):
        """
        Add workflow steps (HowToStep) to the RO-Crate. These are unique for each tool occurrence.
        """
        step_entities: List[ContextEntity] = []
        # Initialize the position as a list with a single element to keep it mutable
        position = [1]
        self._add_steps_recursive(self.workflow.steps, crate, step_entities, position)
        return step_entities

    def _add_steps_recursive(self, steps, crate: ROCrate, step_entities, position):
        """
        Recursively add HowToStep entities from workflow steps, ensuring that
        the position index is maintained across subworkflows.
        """
        for step in steps:
            if step.type == "tool":
                # Create a unique HowToStep entity for each step
                step_id = f"step_{position[0]}"
                step_description = None
                if step.annotations:
                    annotations_list = [annotation.annotation for annotation in step.annotations if annotation]
                    step_description = " ".join(annotations_list) if annotations_list else None

                # Add HowToStep entity to the crate
                step_entity = crate.add(
                    ContextEntity(
                        crate,
                        step_id,
                        properties={
                            "@type": "HowToStep",
                            "position": position[0],
                            "name": step.tool_id,
                            "description": step_description,
                        },
                    )
                )

                # Append the HowToStep entity to the workflow steps list
                step_entities.append(step_entity)
                crate.mainEntity.append_to("step", step_entity)

                # Increment the position counter
                position[0] += 1

            # Handle subworkflows recursively
            elif step.type == "subworkflow":
                subworkflow = step.subworkflow
                if subworkflow:
                    self._add_steps_recursive(subworkflow.steps, crate, step_entities, position)

    def _add_tools(self, crate: ROCrate):
        tool_entities: List[ContextEntity] = []
        self._add_tools_recursive(self.workflow.steps, crate, tool_entities)

    def _add_tools_recursive(self, steps, crate: ROCrate, tool_entities):
        """
        Recursively add SoftwareApplication entities from workflow steps, reusing tools when necessary.
        """
        for step in steps:
            if step.type == "tool":
                tool_id = step.tool_id
                tool_version = step.tool_version

                # Cache key based on tool ID and version
                tool_key = f"{tool_id}:{tool_version}"

                # Check if tool entity is already in cache
                if tool_key in self.tool_cache:
                    tool_entity = self.tool_cache[tool_key]
                else:
                    # Create a new tool entity
                    tool_name = tool_id
                    tool_description = None
                    if step.annotations:
                        annotations_list = [annotation.annotation for annotation in step.annotations if annotation]
                        tool_description = " ".join(annotations_list) if annotations_list else None

                    # Add tool entity to the RO-Crate
                    tool_entity = crate.add(
                        ContextEntity(
                            crate,
                            tool_id,
                            properties={
                                "@type": "SoftwareApplication",
                                "name": tool_name,
                                "version": tool_version,
                                "description": tool_description,
                                "url": "https://toolshed.g2.bx.psu.edu",  # URL if relevant
                            },
                        )
                    )

                    # Store the tool entity in the cache
                    self.tool_cache[tool_key] = tool_entity

                # Append the tool entity to the workflow (instrument) and store it in the list
                tool_entities.append(tool_entity)
                crate.mainEntity.append_to("instrument", tool_entity)

            # Handle subworkflows recursively
            elif step.type == "subworkflow":
                subworkflow = step.subworkflow
                if subworkflow:
                    self._add_tools_recursive(subworkflow.steps, crate, tool_entities)

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
                property_value = self._add_step_parameter(step, crate)
                self.create_action.append_to("object", property_value)

    def _add_step_parameter(self, step: WorkflowInvocationStep, crate: ROCrate) -> ContextEntity:
        param_id = step.workflow_step.label
        assert step.workflow_step.tool_inputs
        param_type = step.workflow_step.tool_inputs["parameter_type"]
        formal_param = crate.add(
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
        crate.mainEntity.append_to("input", formal_param)
        return crate.add(
            ContextEntity(
                crate,
                f"{param_id}-pv",
                properties={
                    "@type": "PropertyValue",
                    "name": f"{param_id}",
                    "value": step.output_value.value,
                    "exampleOfWork": {"@id": formal_param.id},
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

    def _add_collection_formal_parameter(
        self, hdca: HistoryDatasetCollectionAssociation, crate: ROCrate
    ) -> ContextEntity:
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

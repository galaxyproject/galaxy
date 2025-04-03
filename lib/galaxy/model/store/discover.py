"""Utilities for discovering files to add to a model store.

Working with input "JSON" format used for Fetch API, galaxy.json
imports, etc... High-level utilities in this file can be used during
job output discovery or for persisting Galaxy model objects
corresponding to files in other contexts.
"""

import abc
import logging
import os
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    TYPE_CHECKING,
    Union,
)

from sqlalchemy.orm.scoping import ScopedSession

import galaxy.model
from galaxy import util
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model.dataset_collections import builder
from galaxy.model.tags import GalaxySessionlessTagHandler
from galaxy.objectstore import (
    ObjectStore,
    persist_extra_files,
)
from galaxy.util import (
    chunk_iterable,
    ExecutionTimer,
)
from galaxy.util.hash_util import HASH_NAME_MAP

if TYPE_CHECKING:
    from galaxy.job_execution.output_collect import (
        DatasetCollector,
        ToolMetadataDatasetCollector,
    )
    from galaxy.model.store import ModelExportStore

log = logging.getLogger(__name__)

UNSET = object()
DEFAULT_CHUNK_SIZE = 1000


class MaxDiscoveredFilesExceededError(ValueError):
    pass


CollectorT = Union["DatasetCollector", "ToolMetadataDatasetCollector"]


class ModelPersistenceContext(metaclass=abc.ABCMeta):
    """Class for creating datasets while finding files.

    This class implement the create_dataset method that takes care of populating metadata
    required for datasets and other potential model objects.
    """

    job_working_directory: str  # TODO: rename
    max_discovered_files = float("inf")
    discovered_file_count: int

    def get_job(self) -> Optional[galaxy.model.Job]:
        return getattr(self, "job", None)

    def create_dataset(
        self,
        ext,
        designation,
        visible,
        dbkey,
        name,
        filename=None,
        extra_files=None,
        metadata=None,
        metadata_source_name=None,
        info=None,
        library_folder=None,
        link_data=False,
        primary_data=None,
        init_from=None,
        dataset_attributes=None,
        tag_list=None,
        sources=None,
        hashes=None,
        created_from_basename=None,
        final_job_state="ok",
        creating_job_id=None,
        output_name=None,
        storage_callbacks=None,
        purged=False,
    ):
        tag_list = tag_list or []
        sources = sources or []
        hashes = hashes or []
        dataset_attributes = dataset_attributes or {}

        sa_session = self.sa_session

        # You can initialize a dataset or initialize from a dataset but not both.
        if init_from:
            assert primary_data is None
        if primary_data:
            assert init_from is None

        if metadata_source_name:
            assert init_from is None
        if init_from:
            assert metadata_source_name is None

        if primary_data is not None:
            primary_data.extension = ext
            primary_data.dbkey = dbkey
        else:
            if not library_folder:
                primary_data = galaxy.model.HistoryDatasetAssociation(
                    extension=ext,
                    designation=designation,
                    visible=visible,
                    dbkey=dbkey,
                    create_dataset=True,
                    flush=False,
                    sa_session=sa_session,
                    creating_job_id=creating_job_id,
                )
                self.persist_object(primary_data)

            else:
                ld = galaxy.model.LibraryDataset(folder=library_folder, name=name)
                ldda = galaxy.model.LibraryDatasetDatasetAssociation(
                    name=name,
                    extension=ext,
                    dbkey=dbkey,
                    # library_dataset=ld,
                    user=self.user,
                    create_dataset=True,
                    flush=False,
                    sa_session=sa_session,
                )
                ld.library_dataset_dataset_association = ldda

                self.add_library_dataset_to_folder(library_folder, ld)
                primary_data = ldda
        primary_data.state = final_job_state
        if final_job_state == galaxy.model.Job.states.ERROR and not self.get_implicit_collection_jobs_association_id():
            primary_data.visible = True

        if metadata:
            for key, value in metadata.items():
                metadata_element = primary_data.datatype.metadata_spec.get(key)
                if metadata_element and metadata_element.set_in_upload:
                    setattr(primary_data.metadata, key, value)

        for source_dict in sources:
            source = galaxy.model.DatasetSource()
            source.source_uri = source_dict["source_uri"]
            source.transform = source_dict.get("transform")
            primary_data.dataset.sources.append(source)

        for hash_dict in hashes:
            hash_object = galaxy.model.DatasetHash()
            hash_object.hash_function = hash_dict["hash_function"]
            hash_object.hash_value = hash_dict["hash_value"]
            primary_data.dataset.hashes.append(hash_object)

        if created_from_basename is not None:
            primary_data.created_from_basename = created_from_basename

        if tag_list:
            job = self.get_job()
            self.tag_handler.add_tags_from_list(job and job.user, primary_data, tag_list, flush=False)

        # If match specified a name use otherwise generate one from
        # designation.
        if name is not None:
            primary_data.name = name

        # Copy metadata from one of the inputs if requested.
        if metadata_source_name:
            metadata_source = self.metadata_source_provider.get_metadata_source(metadata_source_name)
            primary_data.init_meta(copy_from=metadata_source)
        elif init_from:
            metadata_source = init_from
            primary_data.init_meta(copy_from=init_from)
            # when coming from primary dataset - respect pattern of output - this makes sense
            primary_data.dbkey = dbkey
        else:
            primary_data.init_meta()

        if info is not None:
            primary_data.info = info

        if purged:
            primary_data.dataset.purged = True
            primary_data.purged = True
        if filename and not purged:
            if storage_callbacks is None:
                self.finalize_storage(
                    primary_data=primary_data,
                    dataset_attributes=dataset_attributes,
                    extra_files=extra_files,
                    filename=filename,
                    link_data=link_data,
                    output_name=output_name,
                    init_from=init_from,
                )
            else:
                storage_callbacks.append(
                    lambda: self.finalize_storage(
                        primary_data=primary_data,
                        dataset_attributes=dataset_attributes,
                        extra_files=extra_files,
                        filename=filename,
                        link_data=link_data,
                        output_name=output_name,
                        init_from=init_from,
                    )
                )
        return primary_data

    def finalize_storage(
        self, primary_data, dataset_attributes, extra_files, filename, link_data, output_name, init_from
    ):
        if primary_data.dataset.purged:
            # metadata won't be set, maybe we should do that, then purge ?
            primary_data.dataset.file_size = 0
            primary_data.dataset.total_size = 0
            return
        # Move data from temp location to dataset location
        if not link_data:
            dataset = primary_data.dataset
            object_store_id = self.override_object_store_id(output_name)
            if object_store_id:
                dataset.object_store_id = object_store_id
            self.object_store.update_from_file(dataset, file_name=filename, create=True)
        else:
            primary_data.link_to(filename)
        if extra_files:
            persist_extra_files(self.object_store, extra_files, primary_data)
            primary_data.set_size()
        else:
            # We are sure there are no extra files, so optimize things that follow by settting total size also.
            primary_data.set_size(no_extra_files=True)

        if init_from:
            self.permission_provider.copy_dataset_permissions(init_from, primary_data)
        else:
            self.permission_provider.set_default_hda_permissions(primary_data)

        # TODO: this might run set_meta after copying the file to the object store, which could be inefficient if job working directory is closer to the node.
        self.set_datasets_metadata(datasets=[primary_data], datasets_attributes=[dataset_attributes])

    @staticmethod
    def set_datasets_metadata(datasets, datasets_attributes=None):
        datasets_attributes = datasets_attributes or [{} for _ in datasets]
        for primary_data, dataset_attributes in zip(datasets, datasets_attributes):
            # add tool/metadata provided information
            if dataset_attributes:
                # TODO: discover_files should produce a match that encorporates this -
                # would simplify ToolProvidedMetadata interface and eliminate this
                # crap path.
                dataset_att_by_name = dict(ext="extension")
                for att_set in ["name", "info", "ext", "dbkey"]:
                    dataset_att_name = dataset_att_by_name.get(att_set, att_set)
                    setattr(
                        primary_data,
                        dataset_att_name,
                        dataset_attributes.get(att_set, getattr(primary_data, dataset_att_name)),
                    )

            try:
                metadata_dict = dataset_attributes.get("metadata", None)
                if metadata_dict:
                    if "dbkey" in dataset_attributes:
                        metadata_dict["dbkey"] = dataset_attributes["dbkey"]
                    # branch tested with tool_provided_metadata_3 / tool_provided_metadata_10
                    primary_data.metadata.from_JSON_dict(json_dict=metadata_dict)
                else:
                    primary_data.set_meta()
            except Exception:
                if primary_data.state == galaxy.model.HistoryDatasetAssociation.states.OK:
                    primary_data.state = galaxy.model.HistoryDatasetAssociation.states.FAILED_METADATA
                log.exception("Exception occured while setting metdata")

            try:
                primary_data.set_peek()
            except Exception:
                log.exception("Exception occured while setting dataset peek")

            primary_data.set_total_size()

    def populate_collection_elements(
        self,
        collection,
        root_collection_builder,
        discovered_files,
        name=None,
        metadata_source_name=None,
        final_job_state="ok",
        change_datatype_actions=None,
    ):
        # TODO: allow configurable sorting.
        #    <sort by="lexical" /> <!-- default -->
        #    <sort by="reverse_lexical" />
        #    <sort regex="example.(\d+).fastq" by="1:numerical" />
        #    <sort regex="part_(\d+)_sample_([^_]+).fastq" by="2:lexical,1:numerical" />
        if name is None:
            name = "unnamed output"
        if change_datatype_actions is None:
            change_datatype_actions = {}
        if self.flush_per_n_datasets and self.flush_per_n_datasets > 0:
            for chunk in chunk_iterable(discovered_files, size=self.flush_per_n_datasets):
                self._populate_elements(
                    chunk=chunk,
                    name=name,
                    root_collection_builder=root_collection_builder,
                    metadata_source_name=metadata_source_name,
                    final_job_state=final_job_state,
                    change_datatype_actions=change_datatype_actions,
                )
                if len(chunk) == self.flush_per_n_datasets:
                    # In most cases we don't need to flush, that happens in the caller.
                    # Only flush here for saving memory.
                    root_collection_builder.populate_partial()
                    self.flush()
        else:
            self._populate_elements(
                chunk=discovered_files,
                name=name,
                root_collection_builder=root_collection_builder,
                metadata_source_name=metadata_source_name,
                final_job_state=final_job_state,
                change_datatype_actions=change_datatype_actions,
            )

    def _populate_elements(
        self, chunk, name, root_collection_builder, metadata_source_name, final_job_state, change_datatype_actions
    ):
        element_datasets: Dict[str, List[Any]] = {
            "element_identifiers": [],
            "datasets": [],
            "tag_lists": [],
            "paths": [],
            "extra_files": [],
        }
        ext_override = change_datatype_actions.get(name)
        for discovered_file in chunk:
            filename = discovered_file.path
            create_dataset_timer = ExecutionTimer()
            fields_match = discovered_file.match
            if not fields_match:
                raise Exception(f"Problem parsing metadata fields for file {filename}")
            element_identifiers = fields_match.element_identifiers
            designation = fields_match.designation
            visible = fields_match.visible
            ext = ext_override or fields_match.ext
            ext = ext.lower()
            dbkey = fields_match.dbkey
            extra_files = fields_match.extra_files
            # galaxy.tools.parser.output_collection_def.INPUT_DBKEY_TOKEN
            if dbkey == "__input__":
                dbkey = self.input_dbkey

            # Create new primary dataset
            dataset_name = fields_match.name or designation

            link_data = discovered_file.match.link_data

            sources = discovered_file.match.sources
            hashes = discovered_file.match.hashes
            created_from_basename = discovered_file.match.created_from_basename
            effective_state = fields_match.effective_state
            if final_job_state == "ok" and effective_state != "ok":
                final_job_state = effective_state
            dataset = self.create_dataset(
                ext=ext,
                designation=designation,
                visible=visible,
                dbkey=dbkey,
                name=dataset_name,
                metadata_source_name=metadata_source_name,
                link_data=link_data,
                sources=sources,
                hashes=hashes,
                created_from_basename=created_from_basename,
                final_job_state=final_job_state,
            )
            log.debug(
                "(%s) Created dynamic collection dataset for path [%s] with element identifier [%s] for output [%s] %s",
                self.job_id(),
                filename,
                designation,
                name,
                create_dataset_timer,
            )
            element_datasets["element_identifiers"].append(element_identifiers)
            element_datasets["extra_files"].append(extra_files)
            element_datasets["datasets"].append(dataset)
            element_datasets["tag_lists"].append(discovered_file.match.tag_list)
            element_datasets["paths"].append(filename)

        self.add_tags_to_datasets(datasets=element_datasets["datasets"], tag_lists=element_datasets["tag_lists"])
        for element_identifiers, dataset in zip(element_datasets["element_identifiers"], element_datasets["datasets"]):
            current_builder = root_collection_builder
            for element_identifier in element_identifiers[:-1]:
                current_builder = current_builder.get_level(element_identifier)
            current_builder.add_dataset(element_identifiers[-1], dataset)

            # Associate new dataset with job
            element_identifier_str = ":".join(element_identifiers)
            association_name = f"__new_primary_file_{name}|{element_identifier_str}__"
            self.add_output_dataset_association(association_name, dataset)

        add_datasets_timer = ExecutionTimer()
        self.add_datasets_to_history(element_datasets["datasets"])
        self.update_object_store_with_datasets(
            datasets=element_datasets["datasets"],
            paths=element_datasets["paths"],
            extra_files=element_datasets["extra_files"],
            output_name=name,
        )
        log.debug(
            "(%s) Add dynamic collection datasets to history for output [%s] %s",
            self.job_id(),
            name,
            add_datasets_timer,
        )
        self.set_datasets_metadata(datasets=element_datasets["datasets"])

    def add_tags_to_datasets(self, datasets, tag_lists):
        if any(tag_lists):
            for dataset, tags in zip(datasets, tag_lists):
                self.tag_handler.add_tags_from_list(self.user, dataset, tags, flush=False)

    def update_object_store_with_datasets(self, datasets, paths, extra_files, output_name):
        for dataset, path, extra_file in zip(datasets, paths, extra_files):
            object_store_id = self.override_object_store_id(output_name)
            if object_store_id:
                dataset.dataset.object_store_id = object_store_id

            self.object_store.update_from_file(dataset.dataset, file_name=path, create=True)
            if extra_file:
                persist_extra_files(self.object_store, extra_file, dataset)
                dataset.set_size()
            else:
                dataset.set_size(no_extra_files=True)

    @property
    @abc.abstractmethod
    def tag_handler(self):
        """Return a galaxy.model.tags.TagHandler-like object for persisting tags."""

    @property
    @abc.abstractmethod
    def user(self):
        """If bound to a database, return the user the datasets should be created for.

        Return None otherwise.
        """

    @property
    @abc.abstractmethod
    def sa_session(self) -> Optional[ScopedSession]:
        """If bound to a database, return the SQL Alchemy session.

        Return None otherwise.
        """

    @property
    @abc.abstractmethod
    def permission_provider(self) -> "PermissionProvider":
        """If bound to a database, return the SQL Alchemy session.

        Return None otherwise.
        """

    def get_implicit_collection_jobs_association_id(self) -> Optional[str]:
        """No-op, no job context."""
        return None

    @property
    @abc.abstractmethod
    def job(self) -> Optional[galaxy.model.Job]:
        """Return associated job object if bound to a job finish context connected to a database."""

    def override_object_store_id(self, output_name: Optional[str] = None) -> Optional[str]:
        """Object store ID to assign to a dataset before populating its contents."""
        job = self.job
        if not job:
            return None
        default_object_store_id = job.object_store_id
        if not output_name:
            return default_object_store_id
        object_store_id_overrides: Dict[str, str] = job.object_store_id_overrides or {}
        return object_store_id_overrides.get(output_name, default_object_store_id)

    @property
    @abc.abstractmethod
    def metadata_source_provider(self) -> "MetadataSourceProvider":
        """Return associated MetadataSourceProvider object."""

    @property
    @abc.abstractmethod
    def object_store(self) -> ObjectStore:
        """Return object store to use for populating discovered dataset contents."""

    @property
    @abc.abstractmethod
    def flush_per_n_datasets(self) -> Optional[int]:
        pass

    @property
    def input_dbkey(self) -> str:
        return "?"

    @abc.abstractmethod
    def add_library_dataset_to_folder(self, library_folder, ld):
        """Add library dataset to persisted library folder."""

    @abc.abstractmethod
    def create_library_folder(self, parent_folder, name, description):
        """Create a library folder ready from supplied attributes for supplied parent."""

    @abc.abstractmethod
    def add_output_dataset_association(self, name, dataset):
        """If discovering outputs for a job, persist output dataset association."""

    @abc.abstractmethod
    def add_datasets_to_history(self, datasets, for_output_dataset=None):
        """Add datasets to the history this context points at."""

    def job_id(self):
        return ""

    @abc.abstractmethod
    def persist_object(self, obj):
        """Add the target to the persistence layer."""

    def persist_library_folder(self, library_folder: galaxy.model.LibraryFolder) -> None:  # noqa: B027
        """Add library folder to sessionless export. Noop for session export."""

    @abc.abstractmethod
    def flush(self):
        """If database bound, flush the persisted objects to ensure IDs."""

    def increment_discovered_file_count(self):
        self.discovered_file_count += 1
        if self.discovered_file_count > self.max_discovered_files:
            raise MaxDiscoveredFilesExceededError(
                f"Job generated more than maximum number ({self.max_discovered_files}) of output datasets"
            )


class PermissionProvider(metaclass=abc.ABCMeta):
    """Interface for working with permissions while importing datasets with ModelPersistenceContext."""

    @property
    def permissions(self):
        return UNSET

    def set_default_hda_permissions(self, primary_data):
        return

    @abc.abstractmethod
    def copy_dataset_permissions(self, init_from, primary_data):
        """Copy dataset permissions from supplied input dataset."""


class UnusedPermissionProvider(PermissionProvider):
    def copy_dataset_permissions(self, init_from, primary_data):
        """Throws NotImplementedError.

        This should only be called as part of job output collection where
        there should be a session available to initialize this from.
        """
        # TODO: what should this do in the sessionless context?
        return


class MetadataSourceProvider(metaclass=abc.ABCMeta):
    """Interface for working with fetching input dataset metadata with ModelPersistenceContext."""

    @abc.abstractmethod
    def get_metadata_source(self, input_name):
        """Get metadata for supplied input_name."""


class UnusedMetadataSourceProvider(MetadataSourceProvider):
    def get_metadata_source(self, input_name):
        """Throws NotImplementedError.

        This should only be called as part of job output collection where
        one can actually collect metadata from inputs, this is unused in the
        context of SessionlessModelPersistenceContext.
        """
        raise NotImplementedError()


class SessionlessModelPersistenceContext(ModelPersistenceContext):
    """A variant of ModelPersistenceContext that persists to an export store instead of database directly."""

    def __init__(self, object_store, export_store: "ModelExportStore", working_directory: str) -> None:
        self._permission_provider = UnusedPermissionProvider()
        self._metadata_source_provider = UnusedMetadataSourceProvider()
        self._object_store = object_store
        self.export_store = export_store
        self._flush_per_n_datasets = None
        self.discovered_file_count = 0
        self.max_discovered_files = float("inf")
        self.job_working_directory = working_directory  # TODO: rename...

    @property
    def tag_handler(self):
        return GalaxySessionlessTagHandler(self.sa_session, galaxy_session=None)

    @property
    def sa_session(self):
        return None

    @property
    def user(self):
        return None

    @property
    def job(self):
        return None

    @property
    def permission_provider(self) -> UnusedPermissionProvider:
        return self._permission_provider

    @property
    def metadata_source_provider(self) -> UnusedMetadataSourceProvider:
        return self._metadata_source_provider

    @property
    def object_store(self) -> ObjectStore:
        return self._object_store

    @property
    def flush_per_n_datasets(self) -> Optional[int]:
        return self._flush_per_n_datasets

    def add_tags_to_datasets(self, datasets, tag_lists):
        user = galaxy.model.User()
        if any(tag_lists):
            for dataset, tags in zip(datasets, tag_lists):
                self.tag_handler.add_tags_from_list(user, dataset, tags, flush=False)

    def add_library_dataset_to_folder(self, library_folder, ld):
        library_folder.datasets.append(ld)
        ld.order_id = library_folder.item_count
        library_folder.item_count += 1

    def get_library_folder(self, destination):
        folder = galaxy.model.LibraryFolder()
        folder.id = destination.get("library_folder_id")
        return folder

    def get_hdca(self, object_id):
        raise NotImplementedError()

    def create_hdca(self, name, structure):
        collection = galaxy.model.DatasetCollection(
            collection_type=structure.collection_type_description.collection_type, populated=False
        )
        return galaxy.model.HistoryDatasetCollectionAssociation(name=name, collection=collection)

    def create_library_folder(self, parent_folder, name, description):
        nested_folder = galaxy.model.LibraryFolder(
            name=name, description=description, order_id=parent_folder.item_count
        )
        parent_folder.item_count += 1
        parent_folder.folders.append(nested_folder)
        return nested_folder

    def persist_library_folder(self, library_folder: galaxy.model.LibraryFolder) -> None:
        self.export_store.export_library_folder(library_folder)

    def add_datasets_to_history(self, datasets, for_output_dataset=None):
        # Consider copying these datasets to for_output_dataset copied histories
        # somehow. Not sure it is worth the effort/complexity?
        for dataset in datasets:
            self.export_store.add_dataset(dataset)

    def persist_object(self, obj):
        """No-op right now for the sessionless variant of this.

        This works currently because either things are added to a target history with add_datasets_to_history
        or the parent LibraryFolder was added to the export store in persist_target_to_export_store.
        """

    def flush(self):
        """No-op for the sessionless variant of this, no database to flush."""

    def add_output_dataset_association(self, name, dataset):
        """No-op, no job context to persist this association for."""

    def get_implicit_collection_jobs_association_id(self):
        """No-op, no job context."""


def persist_target_to_export_store(target_dict, export_store, object_store, work_directory):
    replace_request_syntax_sugar(target_dict)
    model_persistence_context = SessionlessModelPersistenceContext(object_store, export_store, work_directory)

    assert "destination" in target_dict
    assert "elements" in target_dict
    destination = target_dict["destination"]
    elements = target_dict["elements"]

    assert "type" in destination
    destination_type = destination["type"]

    assert destination_type in ["library", "hdas", "hdca"]
    if destination_type == "library":
        name = get_required_item(destination, "name", "Must specify a library name")
        description = destination.get("description", "")
        synopsis = destination.get("synopsis", "")
        root_folder = galaxy.model.LibraryFolder(name=name, description="")
        library = galaxy.model.Library(
            name=name,
            description=description,
            synopsis=synopsis,
            root_folder=root_folder,
        )
        persist_elements_to_folder(model_persistence_context, elements, root_folder)
        export_store.export_library(library)
    elif destination_type == "hdas":
        persist_hdas(elements, model_persistence_context)
    elif destination_type == "hdca":
        name = get_required_item(target_dict, "name", "Must specify a HDCA name")
        collection_type = get_required_item(target_dict, "collection_type", "Must specify an HDCA collection_type")
        collection = galaxy.model.DatasetCollection(
            collection_type=collection_type,
        )
        hdca = galaxy.model.HistoryDatasetCollectionAssociation(
            name=name,
            collection=collection,
        )
        persist_elements_to_hdca(model_persistence_context, elements, hdca)
        export_store.add_dataset_collection(hdca)


def persist_elements_to_hdca(
    model_persistence_context: ModelPersistenceContext,
    elements,
    hdca,
    collector=None,
):
    discovered_files = []

    def add_to_discovered_files(elements, parent_identifiers=None):
        parent_identifiers = parent_identifiers or []
        for element in elements:
            if "elements" in element:
                add_to_discovered_files(element["elements"], parent_identifiers + [element["name"]])
            else:
                discovered_file = discovered_file_for_element(
                    element, model_persistence_context, parent_identifiers, collector=collector
                )
                discovered_files.append(discovered_file)

    add_to_discovered_files(elements)

    collection = hdca.collection
    collection_builder = builder.BoundCollectionBuilder(collection)
    model_persistence_context.populate_collection_elements(
        collection,
        collection_builder,
        discovered_files,
    )
    collection_builder.populate()


def persist_elements_to_folder(model_persistence_context, elements, library_folder):
    for element in elements:
        if "elements" in element:
            assert "name" in element
            name = element["name"]
            description = element.get("description")
            nested_folder = model_persistence_context.create_library_folder(library_folder, name, description)
            persist_elements_to_folder(model_persistence_context, element["elements"], nested_folder)
        else:
            discovered_file = discovered_file_for_element(element, model_persistence_context)
            fields_match = discovered_file.match
            designation = fields_match.designation
            visible = fields_match.visible
            ext = fields_match.ext
            dbkey = fields_match.dbkey
            link_data = discovered_file.match.link_data

            # Create new primary dataset
            name = fields_match.name or designation

            sources = fields_match.sources
            hashes = fields_match.hashes
            created_from_basename = fields_match.created_from_basename
            effective_state = fields_match.effective_state
            info, state = discovered_file.discovered_state(element, final_job_state=effective_state)
            model_persistence_context.create_dataset(
                ext=ext,
                designation=designation,
                visible=visible,
                dbkey=dbkey,
                name=name,
                filename=discovered_file.path,
                info=info,
                library_folder=library_folder,
                link_data=link_data,
                sources=sources,
                hashes=hashes,
                created_from_basename=created_from_basename,
                final_job_state=state,
            )


def persist_hdas(elements, model_persistence_context, final_job_state="ok"):
    # discover files as individual datasets for the target history
    datasets = []
    storage_callbacks: List[Callable] = []

    def collect_elements_for_history(elements):
        for element in elements:
            if "elements" in element:
                collect_elements_for_history(element["elements"])
            else:
                discovered_file = discovered_file_for_element(element, model_persistence_context)
                fields_match = discovered_file.match
                designation = fields_match.designation
                ext = fields_match.ext
                dbkey = fields_match.dbkey
                tag_list = element.get("tags")
                link_data = discovered_file.match.link_data

                # Create new primary dataset
                name = fields_match.name or designation

                hda_id = discovered_file.match.object_id

                primary_dataset = None
                if hda_id:
                    sa_session = (
                        model_persistence_context.sa_session or model_persistence_context.import_store.sa_session
                    )
                    primary_dataset = sa_session.get(galaxy.model.HistoryDatasetAssociation, hda_id)

                sources = fields_match.sources
                hashes = fields_match.hashes
                created_from_basename = fields_match.created_from_basename
                extra_files = fields_match.extra_files
                visible = fields_match.visible

                info, state = discovered_file.discovered_state(element, final_job_state)
                dataset = model_persistence_context.create_dataset(
                    ext=ext,
                    designation=designation,
                    visible=visible,
                    dbkey=dbkey,
                    name=name,
                    filename=discovered_file.path,
                    extra_files=extra_files,
                    metadata=element.get("metadata"),
                    info=info,
                    tag_list=tag_list,
                    link_data=link_data,
                    primary_data=primary_dataset,
                    sources=sources,
                    hashes=hashes,
                    created_from_basename=created_from_basename,
                    final_job_state=state,
                    storage_callbacks=storage_callbacks,
                )
                dataset.discovered = True
                if not hda_id:
                    datasets.append(dataset)

    collect_elements_for_history(elements)
    model_persistence_context.add_datasets_to_history(datasets)
    for callback in storage_callbacks:
        callback()

    def add_datasets_to_history(self, datasets, for_output_dataset=None):
        if for_output_dataset is not None:
            raise NotImplementedError()

        for dataset in datasets:
            self.export_store.add_dataset(dataset)

    def persist_object(self, obj):
        pass

    def flush(self):
        pass


def get_required_item(from_dict, key, message):
    if key not in from_dict:
        raise RequestParameterInvalidException(message)
    return from_dict[key]


def validate_and_normalize_target(obj):
    replace_request_syntax_sugar(obj)


def replace_request_syntax_sugar(obj):
    # For data libraries and hdas to make sense - allow items and items_from in place of elements
    # and elements_from. This is destructive and modifies the supplied request.
    if isinstance(obj, list):
        for el in obj:
            replace_request_syntax_sugar(el)
    elif isinstance(obj, dict):
        if "items" in obj:
            obj["elements"] = obj["items"]
            del obj["items"]
        if "items_from" in obj:
            obj["elements_from"] = obj["items_from"]
            del obj["items_from"]
        for value in obj.values():
            replace_request_syntax_sugar(value)

        if "src" in obj or "filename" in obj:
            # item...
            new_hashes = []
            for key in HASH_NAME_MAP.keys():
                if key in obj:
                    new_hashes.append({"hash_function": key, "hash_value": obj[key]})
                    del obj[key]
                if key.lower() in obj:
                    new_hashes.append({"hash_function": key, "hash_value": obj[key.lower()]})
                    del obj[key.lower()]

            obj.setdefault("hashes", []).extend(new_hashes)


class DiscoveredFile(NamedTuple):
    path: str
    collector: Optional[CollectorT]
    match: "JsonCollectedDatasetMatch"

    def discovered_state(self, element: Dict[str, Any], final_job_state="ok") -> "DiscoveredResultState":
        info = element.get("info", None)
        return DiscoveredResultState(info, final_job_state)


class DiscoveredResultState(NamedTuple):
    info: Optional[str]
    state: str


class DiscoveredDeferredFile(NamedTuple):
    collector: Optional[CollectorT]
    match: "JsonCollectedDatasetMatch"

    def discovered_state(self, element: Dict[str, Any], final_job_state="ok") -> DiscoveredResultState:
        info = element.get("info", None)
        state = "deferred" if final_job_state == "ok" else final_job_state
        return DiscoveredResultState(info, state)

    @property
    def path(self):
        return None


DiscoveredResult = Union[DiscoveredFile, DiscoveredDeferredFile, "DiscoveredFileError"]


def discovered_file_for_element(
    dataset,
    model_persistence_context: ModelPersistenceContext,
    parent_identifiers=None,
    collector=None,
) -> DiscoveredResult:
    model_persistence_context.increment_discovered_file_count()
    parent_identifiers = parent_identifiers or []
    target_directory = discover_target_directory(
        getattr(collector, "directory", None), model_persistence_context.job_working_directory
    )
    filename = dataset.get("filename")
    error_message = dataset.get("error_message")
    if error_message is None:
        if dataset.get("state") == "deferred":
            return DiscoveredDeferredFile(
                collector, JsonCollectedDatasetMatch(dataset, collector, None, parent_identifiers=parent_identifiers)
            )

        # handle link_data_only here, verify filename is in directory if not linking...
        if not dataset.get("link_data_only"):
            path = os.path.join(target_directory, filename)
            if not util.in_directory(path, target_directory):
                raise Exception(
                    "Problem with tool configuration, attempting to pull in datasets from outside working directory."
                )
        else:
            path = filename
        return DiscoveredFile(
            path,
            collector,
            JsonCollectedDatasetMatch(dataset, collector, filename, path=path, parent_identifiers=parent_identifiers),
        )
    else:
        assert "error_message" in dataset
        return DiscoveredFileError(
            dataset["error_message"],
            collector,
            JsonCollectedDatasetMatch(dataset, collector, None, parent_identifiers=parent_identifiers),
        )


def discover_target_directory(dir_name, job_working_directory):
    if dir_name:
        directory = os.path.join(job_working_directory, dir_name)
        if not util.in_directory(directory, job_working_directory):
            raise Exception(
                "Problem with tool configuration, attempting to pull in datasets from outside working directory."
            )
        return directory
    else:
        return job_working_directory


class JsonCollectedDatasetMatch:
    def __init__(self, as_dict, collector: Optional[CollectorT], filename, path=None, parent_identifiers=None):
        parent_identifiers = parent_identifiers or []
        self.as_dict = as_dict
        self.collector = collector
        self.filename = filename
        self.path = path
        self._parent_identifiers = parent_identifiers

    @property
    def designation(self):
        # If collecting nested collection, grab identifier_0,
        # identifier_1, etc... and join on : to build designation.
        if element_identifiers := self.raw_element_identifiers:
            return ":".join(element_identifiers)
        elif "designation" in self.as_dict:
            return self.as_dict.get("designation")
        elif "name" in self.as_dict:
            return self.as_dict.get("name")
        else:
            return None

    @property
    def element_identifiers(self):
        return self._parent_identifiers + (self.raw_element_identifiers or [self.designation])

    @property
    def raw_element_identifiers(self):
        identifiers = []
        i = 0
        while True:
            key = "identifier_%d" % i
            if key in self.as_dict:
                identifiers.append(self.as_dict.get(key))
            else:
                break
            i += 1

        return identifiers

    @property
    def name(self):
        """Return name or None if not defined by the discovery pattern."""
        return self.as_dict.get("name")

    @property
    def dbkey(self) -> str:
        return self.as_dict.get("dbkey", self.collector and self.collector.default_dbkey or "?")

    @property
    def ext(self) -> str:
        return self.as_dict.get("ext", self.collector and self.collector.default_ext or "data")

    @property
    def visible(self) -> bool:
        try:
            return self.as_dict["visible"].lower() == "visible"
        except KeyError:
            if self.collector and self.collector.default_visible is not None:
                return self.collector.default_visible
            return True

    @property
    def link_data(self):
        return bool(self.as_dict.get("link_data_only", False))

    @property
    def tag_list(self):
        return self.as_dict.get("tags", [])

    @property
    def object_id(self):
        return self.as_dict.get("object_id", None)

    @property
    def sources(self):
        return self.as_dict.get("sources", [])

    @property
    def hashes(self):
        return self.as_dict.get("hashes", [])

    @property
    def created_from_basename(self):
        return self.as_dict.get("created_from_basename")

    @property
    def extra_files(self):
        return self.as_dict.get("extra_files")

    @property
    def effective_state(self):
        return self.as_dict.get("state") or "ok"


class RegexCollectedDatasetMatch(JsonCollectedDatasetMatch):
    def __init__(self, re_match, collector: Optional[CollectorT], filename, path=None):
        super().__init__(re_match.groupdict(), collector, filename, path=path)


class DiscoveredFileError(NamedTuple):
    error_message: str
    collector: Optional[CollectorT]
    match: JsonCollectedDatasetMatch
    path: Optional[str] = None

    def discovered_state(self, element: Dict[str, Any], final_job_state="ok") -> DiscoveredResultState:
        info = self.error_message
        return DiscoveredResultState(info, "error")

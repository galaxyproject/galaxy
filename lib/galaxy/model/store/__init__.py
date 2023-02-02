import abc
import contextlib
import datetime
import logging
import os
import shutil
import tarfile
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from json import (
    dump,
    dumps,
    load,
)
from tempfile import mkdtemp
from types import TracebackType
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)

from bdbag import bdbag_api as bdb
from boltons.iterutils import remap
from rocrate.model.computationalworkflow import (
    ComputationalWorkflow,
    WorkflowDescription,
)
from rocrate.rocrate import ROCrate
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.sql import expression
from typing_extensions import Protocol

from galaxy.datatypes.registry import Registry
from galaxy.exceptions import (
    MalformedContents,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.files import (
    ConfiguredFileSources,
    ProvidesUserFileSourcesUserContext,
)
from galaxy.files.uris import stream_url_to_file
from galaxy.model.mapping import GalaxyModelMapping
from galaxy.model.metadata import MetadataCollection
from galaxy.model.orm.util import (
    add_object_to_object_session,
    add_object_to_session,
    get_object_session,
)
from galaxy.model.tags import GalaxyTagHandler
from galaxy.objectstore import (
    BaseObjectStore,
    ObjectStore,
)
from galaxy.schema.bco import (
    BioComputeObjectCore,
    DescriptionDomain,
    DescriptionDomainUri,
    ErrorDomain,
    InputAndOutputDomain,
    InputAndOutputDomainUri,
    InputSubdomainItem,
    OutputSubdomainItem,
    ParametricDomain,
    ParametricDomainItem,
    PipelineStep,
    ProvenanceDomain,
    UsabilityDomain,
    XrefItem,
)
from galaxy.schema.bco.io_domain import Uri
from galaxy.schema.bco.util import (
    extension_domains,
    galaxy_execution_domain,
    get_contributors,
    write_to_file,
)
from galaxy.schema.schema import ModelStoreFormat
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import (
    FILENAME_VALID_CHARS,
    in_directory,
    safe_makedirs,
)
from galaxy.util.bunch import Bunch
from galaxy.util.compression_utils import CompressedFile
from galaxy.util.path import (
    safe_walk,
    StrPath,
)
from ._bco_convert_utils import (
    bco_workflow_version,
    SoftwarePrerequisteTracker,
)
from .ro_crate_utils import WorkflowRunCrateProfileBuilder
from ..custom_types import json_encoder
from ..item_attrs import (
    add_item_annotation,
    get_item_annotation_str,
)
from ... import model

if TYPE_CHECKING:
    from galaxy.managers.workflows import WorkflowContentsManager
    from galaxy.model import ImplicitCollectionJobs
    from galaxy.model.tags import GalaxyTagHandlerSession

log = logging.getLogger(__name__)

ObjectKeyType = Union[str, int]

ATTRS_FILENAME_HISTORY = "history_attrs.txt"
ATTRS_FILENAME_DATASETS = "datasets_attrs.txt"
ATTRS_FILENAME_JOBS = "jobs_attrs.txt"
ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS = "implicit_collection_jobs_attrs.txt"
ATTRS_FILENAME_COLLECTIONS = "collections_attrs.txt"
ATTRS_FILENAME_EXPORT = "export_attrs.txt"
ATTRS_FILENAME_LIBRARIES = "libraries_attrs.txt"
ATTRS_FILENAME_LIBRARY_FOLDERS = "library_folders_attrs.txt"
ATTRS_FILENAME_INVOCATIONS = "invocation_attrs.txt"
TRACEBACK = "traceback.txt"
GALAXY_EXPORT_VERSION = "2"

DICT_STORE_ATTRS_KEY_HISTORY = "history"
DICT_STORE_ATTRS_KEY_DATASETS = "datasets"
DICT_STORE_ATTRS_KEY_COLLECTIONS = "collections"
DICT_STORE_ATTRS_KEY_JOBS = "jobs"
DICT_STORE_ATTRS_KEY_IMPLICIT_COLLECTION_JOBS = "implicit_collection_jobs"
DICT_STORE_ATTRS_KEY_LIBRARIES = "libraries"
DICT_STORE_ATTRS_KEY_INVOCATIONS = "invocations"


JsonDictT = Dict[str, Any]


class StoreAppProtocol(Protocol):
    """Define the parts of a Galaxy-like app consumed by model store."""

    datatypes_registry: Registry
    object_store: BaseObjectStore
    security: IdEncodingHelper
    tag_handler: GalaxyTagHandler
    model: GalaxyModelMapping
    file_sources: ConfiguredFileSources
    workflow_contents_manager: "WorkflowContentsManager"


class ImportDiscardedDataType(Enum):
    # Don't allow discarded 'okay' datasets on import, datasets will be marked deleted.
    FORBID = "forbid"
    # Allow datasets to be imported as experimental DISCARDED datasets that are not deleted if file data unavailable.
    ALLOW = "allow"
    # Import all datasets as discarded regardless of whether file data is available in the store.
    FORCE = "force"


DEFAULT_DISCARDED_DATA_TYPE = ImportDiscardedDataType.FORBID


class ImportOptions:
    allow_edit: bool
    allow_library_creation: bool
    allow_dataset_object_edit: bool
    discarded_data: ImportDiscardedDataType

    def __init__(
        self,
        allow_edit: bool = False,
        allow_library_creation: bool = False,
        allow_dataset_object_edit: Optional[bool] = None,
        discarded_data: ImportDiscardedDataType = DEFAULT_DISCARDED_DATA_TYPE,
    ) -> None:
        self.allow_edit = allow_edit
        self.allow_library_creation = allow_library_creation
        if allow_dataset_object_edit is None:
            self.allow_dataset_object_edit = allow_edit
        else:
            self.allow_dataset_object_edit = allow_dataset_object_edit
        self.discarded_data = discarded_data


class SessionlessContext:
    def __init__(self) -> None:
        self.objects: Dict[Type, Dict] = defaultdict(dict)

    def flush(self) -> None:
        pass

    def add(self, obj: Union[model.DatasetInstance, model.RepresentById]) -> None:
        self.objects[obj.__class__][obj.id] = obj

    def query(self, model_class: Type) -> Bunch:
        def find(obj_id):
            return self.objects.get(model_class, {}).get(obj_id) or None

        def filter_by(*args, **kwargs):
            # TODO: Hack for history export archive, should support this too
            return Bunch(first=lambda: next(iter(self.objects.get(model_class, {None: None}))))

        return Bunch(find=find, get=find, filter_by=filter_by)


def replace_metadata_file(
    metadata: Dict[str, Any],
    dataset_instance: model.DatasetInstance,
    sa_session: Union[SessionlessContext, scoped_session],
) -> Dict[str, Any]:
    def remap_objects(p, k, obj):
        if isinstance(obj, dict) and "model_class" in obj and obj["model_class"] == "MetadataFile":
            metadata_file = model.MetadataFile(dataset=dataset_instance, uuid=obj["uuid"])
            sa_session.add(metadata_file)
            return (k, metadata_file)
        return (k, obj)

    return remap(metadata, remap_objects)


class ModelImportStore(metaclass=abc.ABCMeta):
    app: Optional[StoreAppProtocol]
    archive_dir: str

    def __init__(
        self,
        import_options: Optional[ImportOptions] = None,
        app: Optional[StoreAppProtocol] = None,
        user: Optional[model.User] = None,
        object_store: Optional[ObjectStore] = None,
        tag_handler: Optional["GalaxyTagHandlerSession"] = None,
    ) -> None:
        if object_store is None:
            if app is not None:
                object_store = app.object_store
        self.object_store = object_store
        self.app = app
        if app is not None:
            self.sa_session = app.model.session
            self.sessionless = False
        else:
            self.sa_session = SessionlessContext()
            self.sessionless = True
        self.user = user
        self.import_options = import_options or ImportOptions()
        self.dataset_state_serialized = True
        self.tag_handler = tag_handler
        if self.defines_new_history():
            self.import_history_encoded_id = self.new_history_properties().get("encoded_id")
        else:
            self.import_history_encoded_id = None

    @abc.abstractmethod
    def workflow_paths(self) -> Iterator[Tuple[str, str]]:
        ...

    @abc.abstractmethod
    def defines_new_history(self) -> bool:
        """Does this store define a new history to create."""

    @abc.abstractmethod
    def new_history_properties(self) -> Dict[str, Any]:
        """Dict of history properties if defines_new_history() is truthy."""

    @abc.abstractmethod
    def datasets_properties(self) -> List[Dict[str, Any]]:
        """Return a list of HDA properties."""

    def library_properties(self) -> List[Dict[str, Any]]:
        """Return a list of library properties."""
        return []

    @abc.abstractmethod
    def invocations_properties(self) -> List[Dict[str, Any]]:
        ...

    @abc.abstractmethod
    def collections_properties(self) -> List[Dict[str, Any]]:
        """Return a list of HDCA properties."""

    @abc.abstractmethod
    def jobs_properties(self) -> List[Dict[str, Any]]:
        """Return a list of jobs properties."""

    @abc.abstractmethod
    def implicit_collection_jobs_properties(self) -> List[Dict[str, Any]]:
        ...

    @property
    @abc.abstractmethod
    def object_key(self) -> str:
        """Key used to connect objects in metadata.

        Legacy exports used 'hid' but associated objects may not be from the same history
        and a history may contain multiple objects with the same 'hid'.
        """

    @property
    def file_source_root(self) -> Optional[str]:
        """Source of valid file data."""
        return None

    def trust_hid(self, obj_attrs: Dict[str, Any]) -> bool:
        """Trust HID when importing objects into a new History."""
        return (
            self.import_history_encoded_id is not None
            and obj_attrs.get("history_encoded_id") == self.import_history_encoded_id
        )

    @contextlib.contextmanager
    def target_history(
        self, default_history: Optional[model.History] = None, legacy_history_naming: bool = True
    ) -> Iterator[Optional[model.History]]:
        new_history = None

        if self.defines_new_history():
            history_properties = self.new_history_properties()
            history_name = history_properties.get("name")
            if history_name and legacy_history_naming:
                history_name = f"imported from archive: {history_name}"
            elif history_name:
                pass  # history_name = history_name
            else:
                history_name = "unnamed imported history"

            # Create history.
            new_history = model.History(name=history_name, user=self.user)
            new_history.importing = True
            hid_counter = history_properties.get("hid_counter")
            genome_build = history_properties.get("genome_build")

            # TODO: This seems like it shouldn't be imported, try to test and verify we can calculate this
            # and get away without it. -John
            if hid_counter:
                new_history.hid_counter = hid_counter
            if genome_build:
                new_history.genome_build = genome_build

            self._session_add(new_history)
            self._flush()

            if self.user:
                add_item_annotation(self.sa_session, self.user, new_history, history_properties.get("annotation"))

            history: Optional[model.History] = new_history
        else:
            history = default_history

        yield history

        if new_history is not None:
            # Done importing.
            new_history.importing = False
            self._flush()

    def perform_import(
        self, history: Optional[model.History] = None, new_history: bool = False, job: Optional[model.Job] = None
    ) -> "ObjectImportTracker":
        object_import_tracker = ObjectImportTracker()

        datasets_attrs = self.datasets_properties()
        collections_attrs = self.collections_properties()

        self._import_datasets(object_import_tracker, datasets_attrs, history, new_history, job)
        self._import_dataset_copied_associations(object_import_tracker, datasets_attrs)
        self._import_libraries(object_import_tracker)
        self._import_collection_instances(object_import_tracker, collections_attrs, history, new_history)
        self._import_collection_implicit_input_associations(object_import_tracker, collections_attrs)
        self._import_collection_copied_associations(object_import_tracker, collections_attrs)
        self._reassign_hids(object_import_tracker, history)
        self._import_jobs(object_import_tracker, history)
        self._import_implicit_collection_jobs(object_import_tracker)
        self._import_workflow_invocations(object_import_tracker, history)
        self._flush()
        return object_import_tracker

    def _attach_dataset_hashes(
        self,
        dataset_or_file_attrs: Dict[str, Any],
        dataset_instance: model.DatasetInstance,
    ) -> None:
        if "hashes" in dataset_or_file_attrs:
            for hash_attrs in dataset_or_file_attrs["hashes"]:
                hash_obj = model.DatasetHash()
                hash_obj.hash_value = hash_attrs["hash_value"]
                hash_obj.hash_function = hash_attrs["hash_function"]
                hash_obj.extra_files_path = hash_attrs["extra_files_path"]
                dataset_instance.dataset.hashes.append(hash_obj)

    def _attach_dataset_sources(
        self,
        dataset_or_file_attrs: Dict[str, Any],
        dataset_instance: model.DatasetInstance,
    ) -> None:
        if "sources" in dataset_or_file_attrs:
            for source_attrs in dataset_or_file_attrs["sources"]:
                source_obj = model.DatasetSource()
                source_obj.source_uri = source_attrs["source_uri"]
                source_obj.transform = source_attrs["transform"]
                source_obj.extra_files_path = source_attrs["extra_files_path"]
                for hash_attrs in source_attrs["hashes"]:
                    hash_obj = model.DatasetSourceHash()
                    hash_obj.hash_value = hash_attrs["hash_value"]
                    hash_obj.hash_function = hash_attrs["hash_function"]
                    source_obj.hashes.append(hash_obj)

                dataset_instance.dataset.sources.append(source_obj)

    def _import_datasets(
        self,
        object_import_tracker: "ObjectImportTracker",
        datasets_attrs: List[Dict[str, Any]],
        history: Optional[model.History],
        new_history: bool,
        job: Optional[model.Job],
    ) -> None:
        object_key = self.object_key

        def handle_dataset_object_edit(dataset_instance, dataset_attrs):
            if "dataset" in dataset_attrs:
                assert self.import_options.allow_dataset_object_edit
                dataset_attributes = [
                    "state",
                    "deleted",
                    "purged",
                    "external_filename",
                    "_extra_files_path",
                    "file_size",
                    "object_store_id",
                    "total_size",
                    "created_from_basename",
                    "uuid",
                ]

                for attribute in dataset_attributes:
                    if attribute in dataset_attrs["dataset"]:
                        setattr(dataset_instance.dataset, attribute, dataset_attrs["dataset"][attribute])
                self._attach_dataset_hashes(dataset_attrs["dataset"], dataset_instance)
                self._attach_dataset_sources(dataset_attrs["dataset"], dataset_instance)
                if "id" in dataset_attrs["dataset"] and self.import_options.allow_edit:
                    dataset_instance.dataset.id = dataset_attrs["dataset"]["id"]
                if job:
                    dataset_instance.dataset.job_id = job.id

        for dataset_attrs in datasets_attrs:
            if "state" not in dataset_attrs:
                self.dataset_state_serialized = False

            if "id" in dataset_attrs and self.import_options.allow_edit and not self.sessionless:
                dataset_instance: model.DatasetInstance = self.sa_session.query(
                    getattr(model, dataset_attrs["model_class"])
                ).get(dataset_attrs["id"])
                attributes = [
                    "name",
                    "extension",
                    "info",
                    "blurb",
                    "peek",
                    "designation",
                    "visible",
                    "metadata",
                    "tool_version",
                    "validated_state",
                    "validated_state_message",
                ]
                for attribute in attributes:
                    if attribute in dataset_attrs:
                        value = dataset_attrs[attribute]
                        if attribute == "metadata":
                            value = replace_metadata_file(value, dataset_instance, self.sa_session)
                        setattr(dataset_instance, attribute, value)

                handle_dataset_object_edit(dataset_instance, dataset_attrs)
            else:
                metadata_deferred = dataset_attrs.get("metadata_deferred", False)
                metadata = dataset_attrs.get("metadata")
                if metadata is None and not metadata_deferred:
                    raise MalformedContents("metadata_deferred must be true if no metadata found in dataset attributes")
                if metadata is None:
                    metadata = {"dbkey": "?"}

                model_class = dataset_attrs.get("model_class", "HistoryDatasetAssociation")
                if model_class == "HistoryDatasetAssociation":
                    # Create dataset and HDA.
                    dataset_instance = model.HistoryDatasetAssociation(
                        name=dataset_attrs["name"],
                        extension=dataset_attrs["extension"],
                        info=dataset_attrs["info"],
                        blurb=dataset_attrs["blurb"],
                        peek=dataset_attrs["peek"],
                        designation=dataset_attrs["designation"],
                        visible=dataset_attrs["visible"],
                        deleted=dataset_attrs.get("deleted", False),
                        dbkey=metadata["dbkey"],
                        tool_version=metadata.get("tool_version"),
                        metadata_deferred=metadata_deferred,
                        history=history,
                        create_dataset=True,
                        flush=False,
                        sa_session=self.sa_session,
                    )
                    dataset_instance._metadata = metadata
                elif model_class == "LibraryDatasetDatasetAssociation":
                    # Create dataset and LDDA.
                    dataset_instance = model.LibraryDatasetDatasetAssociation(
                        name=dataset_attrs["name"],
                        extension=dataset_attrs["extension"],
                        info=dataset_attrs["info"],
                        blurb=dataset_attrs["blurb"],
                        peek=dataset_attrs["peek"],
                        designation=dataset_attrs["designation"],
                        visible=dataset_attrs["visible"],
                        deleted=dataset_attrs.get("deleted", False),
                        dbkey=metadata["dbkey"],
                        tool_version=metadata.get("tool_version"),
                        metadata_deferred=metadata_deferred,
                        user=self.user,
                        create_dataset=True,
                        flush=False,
                        sa_session=self.sa_session,
                    )
                else:
                    raise Exception("Unknown dataset instance type encountered")
                metadata = replace_metadata_file(metadata, dataset_instance, self.sa_session)
                if self.sessionless:
                    dataset_instance._metadata_collection = MetadataCollection(
                        dataset_instance, session=self.sa_session
                    )
                    dataset_instance._metadata = metadata
                else:
                    dataset_instance.metadata = metadata
                self._attach_raw_id_if_editing(dataset_instance, dataset_attrs)

                # Older style...
                if "uuid" in dataset_attrs:
                    dataset_instance.dataset.uuid = dataset_attrs["uuid"]
                if "dataset_uuid" in dataset_attrs:
                    dataset_instance.dataset.uuid = dataset_attrs["dataset_uuid"]

                self._session_add(dataset_instance)

                if model_class == "HistoryDatasetAssociation":
                    hda = cast(model.HistoryDatasetAssociation, dataset_instance)
                    # don't use add_history to manage HID handling across full import to try to preserve
                    # HID structure.
                    hda.history = history
                    if new_history and self.trust_hid(dataset_attrs):
                        hda.hid = dataset_attrs["hid"]
                    else:
                        object_import_tracker.requires_hid.append(hda)
                else:
                    pass
                    # ldda = cast(model.LibraryDatasetDatasetAssociation, dataset_instance)
                    # ldda.user = self.user

                file_source_root = self.file_source_root

                # If dataset is in the dictionary - we will assert this dataset is tied to the Galaxy instance
                # and the import options are configured for allowing editing the dataset (e.g. for metadata setting).
                # Otherwise, we will check for "file" information instead of dataset information - currently this includes
                # "file_name", "extra_files_path".
                if "dataset" in dataset_attrs:
                    handle_dataset_object_edit(dataset_instance, dataset_attrs)
                else:
                    file_name = dataset_attrs.get("file_name")
                    if file_name:
                        assert file_source_root
                        # Do security check and move/copy dataset data.
                        archive_path = os.path.abspath(os.path.join(file_source_root, file_name))
                        if os.path.islink(archive_path):
                            raise MalformedContents(f"Invalid dataset path: {archive_path}")

                        temp_dataset_file_name = os.path.realpath(archive_path)

                        if not in_directory(temp_dataset_file_name, file_source_root):
                            raise MalformedContents(f"Invalid dataset path: {temp_dataset_file_name}")

                    has_good_source = False
                    file_metadata = dataset_attrs.get("file_metadata") or {}
                    if "sources" in file_metadata:
                        for source_attrs in file_metadata["sources"]:
                            extra_files_path = source_attrs["extra_files_path"]
                            if extra_files_path is None:
                                has_good_source = True

                    discarded_data = self.import_options.discarded_data
                    dataset_state = dataset_attrs.get("state", dataset_instance.states.OK)
                    if dataset_state == dataset_instance.states.DEFERRED:
                        dataset_instance._state = dataset_instance.states.DEFERRED
                        dataset_instance.deleted = False
                        dataset_instance.purged = False
                        dataset_instance.dataset.state = dataset_instance.states.DEFERRED
                        dataset_instance.dataset.deleted = False
                        dataset_instance.dataset.purged = False
                    elif (
                        not file_name
                        or not os.path.exists(temp_dataset_file_name)
                        or discarded_data is ImportDiscardedDataType.FORCE
                    ):
                        is_discarded = not has_good_source
                        target_state = (
                            dataset_instance.states.DISCARDED if is_discarded else dataset_instance.states.DEFERRED
                        )
                        dataset_instance._state = target_state
                        deleted = is_discarded and (discarded_data == ImportDiscardedDataType.FORBID)
                        dataset_instance.deleted = deleted
                        dataset_instance.purged = deleted
                        dataset_instance.dataset.state = target_state
                        dataset_instance.dataset.deleted = deleted
                        dataset_instance.dataset.purged = deleted
                    else:
                        dataset_instance.state = dataset_state
                        if not self.object_store:
                            raise Exception(f"self.object_store is missing from {self}.")
                        self.object_store.update_from_file(
                            dataset_instance.dataset, file_name=temp_dataset_file_name, create=True
                        )

                        # Import additional files if present. Histories exported previously might not have this attribute set.
                        dataset_extra_files_path = dataset_attrs.get("extra_files_path", None)
                        if dataset_extra_files_path:
                            assert file_source_root
                            dir_name = dataset_instance.dataset.extra_files_path_name
                            dataset_extra_files_path = os.path.join(file_source_root, dataset_extra_files_path)
                            for root, _dirs, files in safe_walk(dataset_extra_files_path):
                                extra_dir = os.path.join(
                                    dir_name, root.replace(dataset_extra_files_path, "", 1).lstrip(os.path.sep)
                                )
                                extra_dir = os.path.normpath(extra_dir)
                                for extra_file in files:
                                    source = os.path.join(root, extra_file)
                                    if not in_directory(source, file_source_root):
                                        raise MalformedContents(f"Invalid dataset path: {source}")
                                    self.object_store.update_from_file(
                                        dataset_instance.dataset,
                                        extra_dir=extra_dir,
                                        alt_name=extra_file,
                                        file_name=source,
                                        create=True,
                                    )
                        dataset_instance.dataset.set_total_size()  # update the filesize record in the database

                    if dataset_instance.deleted:
                        dataset_instance.dataset.deleted = True
                    self._attach_dataset_hashes(file_metadata, dataset_instance)
                    self._attach_dataset_sources(file_metadata, dataset_instance)
                    if "created_from_basename" in file_metadata:
                        dataset_instance.dataset.created_from_basename = file_metadata["created_from_basename"]

                if model_class == "HistoryDatasetAssociation" and self.user:
                    add_item_annotation(self.sa_session, self.user, dataset_instance, dataset_attrs["annotation"])
                    tag_list = dataset_attrs.get("tags")
                    if tag_list:
                        if not self.tag_handler:
                            raise Exception(f"Missing self.tag_handler on {self}.")
                        self.tag_handler.set_tags_from_list(
                            user=self.user, item=dataset_instance, new_tags_list=tag_list, flush=False
                        )

                if self.app:
                    # If dataset instance is discarded or deferred, don't attempt to regenerate
                    # metadata for it.
                    if dataset_instance.state == dataset_instance.states.OK:
                        regenerate_kwds: Dict[str, Any] = {}
                        if job:
                            regenerate_kwds["user"] = job.user
                            regenerate_kwds["session_id"] = job.session_id
                        elif history:
                            user = history.user
                            regenerate_kwds["user"] = user
                            if user is None:
                                regenerate_kwds["session_id"] = history.galaxy_sessions[0].galaxy_session.id
                            else:
                                regenerate_kwds["session_id"] = None
                        else:
                            # Need a user to run library jobs to generate metadata...
                            pass
                        if not self.import_options.allow_edit:
                            # external import, metadata files need to be regenerated (as opposed to extended metadata dataset import)
                            if self.app.datatypes_registry.set_external_metadata_tool:
                                self.app.datatypes_registry.set_external_metadata_tool.regenerate_imported_metadata_if_needed(
                                    dataset_instance, history, **regenerate_kwds
                                )
                            else:
                                # Try to set metadata directly. @mvdbeek thinks we should only record the datasets
                                try:
                                    if dataset_instance.has_metadata_files:
                                        dataset_instance.datatype.set_meta(dataset_instance)
                                except Exception:
                                    log.debug(f"Metadata setting failed on {dataset_instance}", exc_info=True)
                                    dataset_instance.dataset.state = dataset_instance.dataset.states.FAILED_METADATA

                if model_class == "HistoryDatasetAssociation":
                    if not isinstance(dataset_instance, model.HistoryDatasetAssociation):
                        raise Exception(
                            "Mismatch between model class and Python class, "
                            f"expected HistoryDatasetAssociation, got a {type(dataset_instance)}: {dataset_instance}"
                        )
                    if object_key in dataset_attrs:
                        object_import_tracker.hdas_by_key[dataset_attrs[object_key]] = dataset_instance
                    else:
                        assert "id" in dataset_attrs
                        object_import_tracker.hdas_by_id[dataset_attrs["id"]] = dataset_instance
                else:
                    if not isinstance(dataset_instance, model.LibraryDatasetDatasetAssociation):
                        raise Exception(
                            "Mismatch between model class and Python class, "
                            f"expected LibraryDatasetDatasetAssociation, got a {type(dataset_instance)}: {dataset_instance}"
                        )
                    if object_key in dataset_attrs:
                        object_import_tracker.lddas_by_key[dataset_attrs[object_key]] = dataset_instance
                    else:
                        assert "id" in dataset_attrs
                        object_import_tracker.lddas_by_key[dataset_attrs["id"]] = dataset_instance

    def _import_libraries(self, object_import_tracker: "ObjectImportTracker") -> None:
        object_key = self.object_key

        def import_folder(folder_attrs, root_folder=None):
            if root_folder:
                library_folder = root_folder
            else:
                name = folder_attrs["name"]
                description = folder_attrs["description"]
                genome_build = folder_attrs["genome_build"]
                deleted = folder_attrs["deleted"]
                library_folder = model.LibraryFolder(name=name, description=description, genome_build=genome_build)
                library_folder.deleted = deleted

            self._session_add(library_folder)

            for sub_folder_attrs in folder_attrs.get("folders", []):
                sub_folder = import_folder(sub_folder_attrs)
                library_folder.add_folder(sub_folder)

            for ld_attrs in folder_attrs.get("datasets", []):
                ld = model.LibraryDataset(
                    folder=library_folder, name=ld_attrs["name"], info=ld_attrs["info"], order_id=ld_attrs["order_id"]
                )
                if "ldda" in ld_attrs:
                    ldda = object_import_tracker.lddas_by_key[ld_attrs["ldda"][object_key]]
                    ld.library_dataset_dataset_association = ldda
                self._session_add(ld)

            self.sa_session.flush()
            return library_folder

        libraries_attrs = self.library_properties()
        for library_attrs in libraries_attrs:
            if (
                library_attrs["model_class"] == "LibraryFolder"
                and library_attrs.get("id")
                and not self.sessionless
                and self.import_options.allow_edit
            ):
                library_folder = self.sa_session.query(model.LibraryFolder).get(library_attrs["id"])
                import_folder(library_attrs, root_folder=library_folder)
            else:
                assert self.import_options.allow_library_creation
                name = library_attrs["name"]
                description = library_attrs["description"]
                synopsis = library_attrs["synopsis"]
                library = model.Library(name=name, description=description, synopsis=synopsis)
                self._session_add(library)
                object_import_tracker.libraries_by_key[library_attrs[object_key]] = library

            if "root_folder" in library_attrs:
                library.root_folder = import_folder(library_attrs["root_folder"])

    def _import_collection_instances(
        self,
        object_import_tracker: "ObjectImportTracker",
        collections_attrs: List[Dict[str, Any]],
        history: Optional[model.History],
        new_history: bool,
    ) -> None:
        object_key = self.object_key

        def import_collection(collection_attrs):
            def materialize_elements(dc):
                if "elements" not in collection_attrs:
                    return

                elements_attrs = collection_attrs["elements"]
                for element_attrs in elements_attrs:
                    dce = model.DatasetCollectionElement(
                        collection=dc,
                        element=model.DatasetCollectionElement.UNINITIALIZED_ELEMENT,
                        element_index=element_attrs["element_index"],
                        element_identifier=element_attrs["element_identifier"],
                    )
                    if "encoded_id" in element_attrs:
                        object_import_tracker.dces_by_key[element_attrs["encoded_id"]] = dce
                    if "hda" in element_attrs:
                        hda_attrs = element_attrs["hda"]
                        if object_key in hda_attrs:
                            hda_key = hda_attrs[object_key]
                            hdas_by_key = object_import_tracker.hdas_by_key
                            if hda_key in hdas_by_key:
                                hda = hdas_by_key[hda_key]
                            else:
                                raise KeyError(
                                    f"Failed to find exported hda with key [{hda_key}] of type [{object_key}] in [{hdas_by_key}]"
                                )
                        else:
                            hda_id = hda_attrs["id"]
                            hdas_by_id = object_import_tracker.hdas_by_id
                            if hda_id not in hdas_by_id:
                                raise Exception(f"Failed to find HDA with id [{hda_id}] in [{hdas_by_id}]")
                            hda = hdas_by_id[hda_id]
                        dce.hda = hda
                    elif "child_collection" in element_attrs:
                        dce.child_collection = import_collection(element_attrs["child_collection"])
                    else:
                        raise Exception("Unknown collection element type encountered.")
                dc.element_count = len(elements_attrs)

            if "id" in collection_attrs and self.import_options.allow_edit and not self.sessionless:
                dc = self.sa_session.query(model.DatasetCollection).get(collection_attrs["id"])
                attributes = [
                    "collection_type",
                    "populated_state",
                    "populated_state_message",
                    "element_count",
                ]
                for attribute in attributes:
                    if attribute in collection_attrs:
                        setattr(dc, attribute, collection_attrs.get(attribute))
                materialize_elements(dc)
            else:
                # create collection
                dc = model.DatasetCollection(collection_type=collection_attrs["type"])
                dc.populated_state = collection_attrs["populated_state"]
                dc.populated_state_message = collection_attrs.get("populated_state_message")
                self._attach_raw_id_if_editing(dc, collection_attrs)
                materialize_elements(dc)

            self._session_add(dc)
            return dc

        history_sa_session = get_object_session(history)
        for collection_attrs in collections_attrs:
            if "collection" in collection_attrs:
                dc = import_collection(collection_attrs["collection"])
                if "id" in collection_attrs and self.import_options.allow_edit and not self.sessionless:
                    hdca = self.sa_session.query(model.HistoryDatasetCollectionAssociation).get(collection_attrs["id"])
                    # TODO: edit attributes...
                else:
                    hdca = model.HistoryDatasetCollectionAssociation(
                        collection=dc,
                        visible=True,
                        name=collection_attrs["display_name"],
                        implicit_output_name=collection_attrs.get("implicit_output_name"),
                    )
                    self._attach_raw_id_if_editing(hdca, collection_attrs)

                    add_object_to_session(hdca, history_sa_session)
                    hdca.history = history
                    if new_history and self.trust_hid(collection_attrs):
                        hdca.hid = collection_attrs["hid"]
                    else:
                        object_import_tracker.requires_hid.append(hdca)

                self._session_add(hdca)
                if object_key in collection_attrs:
                    object_import_tracker.hdcas_by_key[collection_attrs[object_key]] = hdca
                else:
                    assert "id" in collection_attrs
                    object_import_tracker.hdcas_by_id[collection_attrs["id"]] = hdca
            else:
                import_collection(collection_attrs)

    def _attach_raw_id_if_editing(
        self,
        obj: Union[model.DatasetInstance, model.RepresentById],
        attrs: Dict[str, Any],
    ) -> None:
        if self.sessionless and "id" in attrs and self.import_options.allow_edit:
            obj.id = attrs["id"]

    def _import_collection_implicit_input_associations(
        self, object_import_tracker: "ObjectImportTracker", collections_attrs: List[Dict[str, Any]]
    ) -> None:
        object_key = self.object_key

        for collection_attrs in collections_attrs:
            if "id" in collection_attrs:
                # Existing object, not a new one, this property is immutable via model stores currently.
                continue

            hdca = object_import_tracker.hdcas_by_key[collection_attrs[object_key]]
            if "implicit_input_collections" in collection_attrs:
                implicit_input_collections = collection_attrs["implicit_input_collections"]
                for implicit_input_collection in implicit_input_collections:
                    name = implicit_input_collection["name"]
                    input_collection_identifier = implicit_input_collection["input_dataset_collection"]
                    if input_collection_identifier in object_import_tracker.hdcas_by_key:
                        input_dataset_collection = object_import_tracker.hdcas_by_key[input_collection_identifier]
                        hdca.add_implicit_input_collection(name, input_dataset_collection)

    def _import_dataset_copied_associations(
        self, object_import_tracker: "ObjectImportTracker", datasets_attrs: List[Dict[str, Any]]
    ) -> None:
        object_key = self.object_key

        # Re-establish copied_from_history_dataset_association relationships so history extraction
        # has a greater chance of working in this history, for reproducibility.
        for dataset_attrs in datasets_attrs:
            if "id" in dataset_attrs:
                # Existing object, not a new one, this property is not immutable via model stores currently.
                continue

            dataset_key = dataset_attrs[object_key]
            if dataset_key not in object_import_tracker.hdas_by_key:
                continue

            hda = object_import_tracker.hdas_by_key[dataset_key]
            copied_from_chain = dataset_attrs.get("copied_from_history_dataset_association_id_chain", [])
            copied_from_object_key = _copied_from_object_key(copied_from_chain, object_import_tracker.hdas_by_key)
            if not copied_from_object_key:
                continue

            # Re-establish the chain if we can.
            if copied_from_object_key in object_import_tracker.hdas_by_key:
                hda.copied_from_history_dataset_association = object_import_tracker.hdas_by_key[copied_from_object_key]
            else:
                # We're at the end of the chain and this HDA was copied from an HDA
                # outside the history. So when we find this job and are looking for inputs/outputs
                # attach to this node... unless we've already encountered another dataset
                # copied from that jobs output... in that case we are going to cheat and
                # say this dataset was copied from that one. It wasn't in the original Galaxy
                # instance but I think it is fine to pretend in order to create a DAG here.
                hda_copied_from_sinks = object_import_tracker.hda_copied_from_sinks
                if copied_from_object_key in hda_copied_from_sinks:
                    hda.copied_from_history_dataset_association = object_import_tracker.hdas_by_key[
                        hda_copied_from_sinks[copied_from_object_key]
                    ]
                else:
                    hda_copied_from_sinks[copied_from_object_key] = dataset_key

    def _import_collection_copied_associations(
        self, object_import_tracker: "ObjectImportTracker", collections_attrs: List[Dict[str, Any]]
    ) -> None:
        object_key = self.object_key

        # Re-establish copied_from_history_dataset_collection_association relationships so history extraction
        # has a greater chance of working in this history, for reproducibility. Very similar to HDA code above
        # see comments there.
        for collection_attrs in collections_attrs:
            if "id" in collection_attrs:
                # Existing object, not a new one, this property is immutable via model stores currently.
                continue

            dataset_collection_key = collection_attrs[object_key]
            if dataset_collection_key not in object_import_tracker.hdcas_by_key:
                continue

            hdca = object_import_tracker.hdcas_by_key[dataset_collection_key]
            copied_from_chain = collection_attrs.get("copied_from_history_dataset_collection_association_id_chain", [])
            copied_from_object_key = _copied_from_object_key(copied_from_chain, object_import_tracker.hdcas_by_key)
            if not copied_from_object_key:
                continue

            # Re-establish the chain if we can, again see comments for hdas above for this to make more
            # sense.
            hdca_copied_from_sinks = object_import_tracker.hdca_copied_from_sinks
            if copied_from_object_key in object_import_tracker.hdcas_by_key:
                hdca.copied_from_history_dataset_collection_association = object_import_tracker.hdcas_by_key[
                    copied_from_object_key
                ]
            else:
                if copied_from_object_key in hdca_copied_from_sinks:
                    hdca.copied_from_history_dataset_collection_association = object_import_tracker.hdcas_by_key[
                        hdca_copied_from_sinks[copied_from_object_key]
                    ]
                else:
                    hdca_copied_from_sinks[copied_from_object_key] = dataset_collection_key

    def _reassign_hids(self, object_import_tracker: "ObjectImportTracker", history: Optional[model.History]) -> None:
        # assign HIDs for newly created objects that didn't match original history
        requires_hid = object_import_tracker.requires_hid
        requires_hid_len = len(requires_hid)
        if requires_hid_len > 0 and not self.sessionless:
            if not history:
                raise Exception("Optional history is required here.")
            for obj in requires_hid:
                history.stage_addition(obj)
            history.add_pending_items()

    def _import_workflow_invocations(
        self, object_import_tracker: "ObjectImportTracker", history: Optional[model.History]
    ) -> None:
        #
        # Create jobs.
        #
        object_key = self.object_key

        for workflow_key, workflow_path in self.workflow_paths():
            workflows_directory = os.path.join(self.archive_dir, "workflows")
            if not self.app:
                raise Exception(f"Missing require self.app in {self}.")
            workflow = self.app.workflow_contents_manager.read_workflow_from_path(
                self.app, self.user, workflow_path, allow_in_directory=workflows_directory
            )
            object_import_tracker.workflows_by_key[workflow_key] = workflow

        invocations_attrs = self.invocations_properties()
        for invocation_attrs in invocations_attrs:
            assert not self.import_options.allow_edit
            imported_invocation = model.WorkflowInvocation()
            imported_invocation.user = self.user
            imported_invocation.history = history
            workflow_key = invocation_attrs["workflow"]
            if workflow_key not in object_import_tracker.workflows_by_key:
                raise Exception(f"Failed to find key {workflow_key} in {object_import_tracker.workflows_by_key.keys()}")
            workflow = object_import_tracker.workflows_by_key[workflow_key]
            imported_invocation.workflow = workflow
            state = invocation_attrs["state"]
            if state in model.WorkflowInvocation.non_terminal_states:
                state = model.WorkflowInvocation.states.CANCELLED
            imported_invocation.state = state
            restore_times(imported_invocation, invocation_attrs)

            self._session_add(imported_invocation)
            self._flush()

            def attach_workflow_step(imported_object, attrs):
                order_index = attrs["order_index"]
                imported_object.workflow_step = workflow.step_by_index(order_index)  # noqa: B023

            for step_attrs in invocation_attrs["steps"]:
                imported_invocation_step = model.WorkflowInvocationStep()
                imported_invocation_step.workflow_invocation = imported_invocation
                attach_workflow_step(imported_invocation_step, step_attrs)
                restore_times(imported_invocation_step, step_attrs)
                imported_invocation_step.action = step_attrs["action"]

                # TODO: ensure terminal...
                imported_invocation_step.state = step_attrs["state"]

                if "job" in step_attrs:
                    job = object_import_tracker.jobs_by_key[step_attrs["job"][object_key]]
                    imported_invocation_step.job = job
                elif "implicit_collection_jobs" in step_attrs:
                    icj = object_import_tracker.implicit_collection_jobs_by_key[
                        step_attrs["implicit_collection_jobs"][object_key]
                    ]
                    imported_invocation_step.implicit_collection_jobs = icj

                # TODO: handle step outputs...
                output_dicts = step_attrs["outputs"]
                step_outputs = []
                for output_dict in output_dicts:
                    step_output = model.WorkflowInvocationStepOutputDatasetAssociation()
                    step_output.output_name = output_dict["output_name"]
                    dataset_link_attrs = output_dict["dataset"]
                    if dataset_link_attrs:
                        dataset = object_import_tracker.find_hda(dataset_link_attrs[object_key])
                        assert dataset
                        step_output.dataset = dataset

                    step_outputs.append(step_output)

                imported_invocation_step.output_datasets = step_outputs

                output_collection_dicts = step_attrs["output_collections"]
                step_output_collections = []
                for output_collection_dict in output_collection_dicts:
                    step_output_collection = model.WorkflowInvocationStepOutputDatasetCollectionAssociation()
                    step_output_collection.output_name = output_collection_dict["output_name"]
                    dataset_collection_link_attrs = output_collection_dict["dataset_collection"]
                    if dataset_collection_link_attrs:
                        dataset_collection = object_import_tracker.find_hdca(dataset_collection_link_attrs[object_key])
                        assert dataset_collection
                        step_output_collection.dataset_collection = dataset_collection

                    step_output_collections.append(step_output_collection)

                imported_invocation_step.output_dataset_collections = step_output_collections

            input_parameters = []
            for input_parameter_attrs in invocation_attrs["input_parameters"]:
                input_parameter = model.WorkflowRequestInputParameter()
                input_parameter.value = input_parameter_attrs["value"]
                input_parameter.name = input_parameter_attrs["name"]
                input_parameter.type = input_parameter_attrs["type"]
                input_parameter.workflow_invocation = imported_invocation
                self._session_add(input_parameter)
                input_parameters.append(input_parameter)

            # invocation_attrs["input_parameters"] = input_parameters

            step_states = []
            for step_state_attrs in invocation_attrs["step_states"]:
                step_state = model.WorkflowRequestStepState()
                step_state.value = step_state_attrs["value"]
                attach_workflow_step(step_state, step_state_attrs)
                step_state.workflow_invocation = imported_invocation
                self._session_add(step_state)
                step_states.append(step_state)

            input_step_parameters = []
            for input_step_parameter_attrs in invocation_attrs["input_step_parameters"]:
                input_step_parameter = model.WorkflowRequestInputStepParameter()
                input_step_parameter.parameter_value = input_step_parameter_attrs["parameter_value"]
                attach_workflow_step(input_step_parameter, input_step_parameter_attrs)
                input_step_parameter.workflow_invocation = imported_invocation
                self._session_add(input_step_parameter)
                input_step_parameters.append(input_step_parameter)

            input_datasets = []
            for input_dataset_attrs in invocation_attrs["input_datasets"]:
                input_dataset = model.WorkflowRequestToInputDatasetAssociation()
                attach_workflow_step(input_dataset, input_dataset_attrs)
                input_dataset.workflow_invocation = imported_invocation
                input_dataset.name = input_dataset_attrs["name"]
                dataset_link_attrs = input_dataset_attrs["dataset"]
                if dataset_link_attrs:
                    dataset = object_import_tracker.find_hda(dataset_link_attrs[object_key])
                    assert dataset
                    input_dataset.dataset = dataset
                self._session_add(input_dataset)
                input_datasets.append(input_dataset)

            input_dataset_collections = []
            for input_dataset_collection_attrs in invocation_attrs["input_dataset_collections"]:
                input_dataset_collection = model.WorkflowRequestToInputDatasetCollectionAssociation()
                attach_workflow_step(input_dataset_collection, input_dataset_collection_attrs)
                input_dataset_collection.workflow_invocation = imported_invocation
                input_dataset_collection.name = input_dataset_collection_attrs["name"]
                dataset_collection_link_attrs = input_dataset_collection_attrs["dataset_collection"]
                if dataset_collection_link_attrs:
                    dataset_collection = object_import_tracker.find_hdca(dataset_collection_link_attrs[object_key])
                    assert dataset_collection
                    input_dataset_collection.dataset_collection = dataset_collection

                self._session_add(input_dataset_collection)
                input_dataset_collections.append(input_dataset_collection)

            output_dataset_collections = []
            for output_dataset_collection_attrs in invocation_attrs["output_dataset_collections"]:
                output_dataset_collection = model.WorkflowInvocationOutputDatasetCollectionAssociation()
                output_dataset_collection.workflow_invocation = imported_invocation
                attach_workflow_step(output_dataset_collection, output_dataset_collection_attrs)
                workflow_output = output_dataset_collection_attrs["workflow_output"]
                label = workflow_output.get("label")
                workflow_output = workflow.workflow_output_for(label)
                output_dataset_collection.workflow_output = workflow_output
                self._session_add(output_dataset_collection)
                output_dataset_collections.append(output_dataset_collection)

            output_datasets = []
            for output_dataset_attrs in invocation_attrs["output_datasets"]:
                output_dataset = model.WorkflowInvocationOutputDatasetAssociation()
                output_dataset.workflow_invocation = imported_invocation
                attach_workflow_step(output_dataset, output_dataset_attrs)
                workflow_output = output_dataset_attrs["workflow_output"]
                label = workflow_output.get("label")
                workflow_output = workflow.workflow_output_for(label)
                output_dataset.workflow_output = workflow_output
                self._session_add(output_dataset)
                output_datasets.append(output_dataset)

            output_values = []
            for output_value_attrs in invocation_attrs["output_values"]:
                output_value = model.WorkflowInvocationOutputValue()
                output_value.workflow_invocation = imported_invocation
                output_value.value = output_value_attrs["value"]
                attach_workflow_step(output_value, output_value_attrs)
                workflow_output = output_value_attrs["workflow_output"]
                label = workflow_output.get("label")
                workflow_output = workflow.workflow_output_for(label)
                output_value.workflow_output = workflow_output
                self._session_add(output_value)
                output_values.append(output_value)

            if object_key in invocation_attrs:
                object_import_tracker.invocations_by_key[invocation_attrs[object_key]] = imported_invocation

    def _import_jobs(self, object_import_tracker: "ObjectImportTracker", history: Optional[model.History]) -> None:
        self._flush()
        object_key = self.object_key

        _find_hda = object_import_tracker.find_hda
        _find_hdca = object_import_tracker.find_hdca
        _find_dce = object_import_tracker.find_dce

        #
        # Create jobs.
        #
        jobs_attrs = self.jobs_properties()
        # Create each job.
        history_sa_session = get_object_session(history)
        for job_attrs in jobs_attrs:
            if "id" in job_attrs and not self.sessionless:
                # only thing we allow editing currently is associations for incoming jobs.
                assert self.import_options.allow_edit
                job = self.sa_session.query(model.Job).get(job_attrs["id"])
                self._connect_job_io(job, job_attrs, _find_hda, _find_hdca, _find_dce)  # type: ignore[attr-defined]
                self._set_job_attributes(job, job_attrs, force_terminal=False)  # type: ignore[attr-defined]
                # Don't edit job
                continue

            imported_job = model.Job()
            imported_job.id = job_attrs.get("id")
            imported_job.user = self.user
            add_object_to_session(imported_job, history_sa_session)
            imported_job.history = history
            imported_job.imported = True
            imported_job.tool_id = job_attrs["tool_id"]
            imported_job.tool_version = job_attrs["tool_version"]
            self._set_job_attributes(imported_job, job_attrs, force_terminal=True)  # type: ignore[attr-defined]

            restore_times(imported_job, job_attrs)
            self._session_add(imported_job)

            # Connect jobs to input and output datasets.
            params = self._normalize_job_parameters(imported_job, job_attrs, _find_hda, _find_hdca, _find_dce)  # type: ignore[attr-defined]
            for name, value in params.items():
                # Transform parameter values when necessary.
                imported_job.add_parameter(name, dumps(value))

            self._connect_job_io(imported_job, job_attrs, _find_hda, _find_hdca, _find_dce)  # type: ignore[attr-defined]

            if object_key in job_attrs:
                object_import_tracker.jobs_by_key[job_attrs[object_key]] = imported_job

    def _import_implicit_collection_jobs(self, object_import_tracker: "ObjectImportTracker") -> None:
        object_key = self.object_key

        implicit_collection_jobs_attrs = self.implicit_collection_jobs_properties()
        for icj_attrs in implicit_collection_jobs_attrs:
            icj = model.ImplicitCollectionJobs()
            icj.populated_state = icj_attrs["populated_state"]

            icj.jobs = []
            for order_index, job in enumerate(icj_attrs["jobs"]):
                icja = model.ImplicitCollectionJobsJobAssociation()
                add_object_to_object_session(icja, icj)
                icja.implicit_collection_jobs = icj
                if job in object_import_tracker.jobs_by_key:
                    job_instance = object_import_tracker.jobs_by_key[job]
                    add_object_to_object_session(icja, job_instance)
                    icja.job = job_instance
                icja.order_index = order_index
                icj.jobs.append(icja)
                self._session_add(icja)

            object_import_tracker.implicit_collection_jobs_by_key[icj_attrs[object_key]] = icj

            self._session_add(icj)

    def _session_add(self, obj: Union[model.DatasetInstance, model.RepresentById]) -> None:
        self.sa_session.add(obj)

    def _flush(self) -> None:
        self.sa_session.flush()


def _copied_from_object_key(
    copied_from_chain: List[ObjectKeyType],
    objects_by_key: Union[
        Dict[ObjectKeyType, model.HistoryDatasetAssociation],
        Dict[ObjectKeyType, model.HistoryDatasetCollectionAssociation],
    ],
) -> Optional[ObjectKeyType]:
    if len(copied_from_chain) == 0:
        return None

    # Okay this gets fun, we need the last thing in the chain to reconnect jobs
    # from outside the history to inputs/outputs in this history but there may
    # be cycles in the chain that lead outside the original history, so just eliminate
    # all IDs not from this history except the last one.
    filtered_copied_from_chain = []
    for i, copied_from_key in enumerate(copied_from_chain):
        filter_id = (i != len(copied_from_chain) - 1) and (copied_from_key not in objects_by_key)
        if not filter_id:
            filtered_copied_from_chain.append(copied_from_key)

    copied_from_chain = filtered_copied_from_chain
    if len(copied_from_chain) == 0:
        return None

    copied_from_object_key = copied_from_chain[0]
    return copied_from_object_key


class ObjectImportTracker:
    """Keep track of new and existing imported objects.

    Needed to re-establish connections and such in multiple passes.
    """

    libraries_by_key: Dict[ObjectKeyType, model.Library]
    hdas_by_key: Dict[ObjectKeyType, model.HistoryDatasetAssociation]
    hdas_by_id: Dict[int, model.HistoryDatasetAssociation]
    hdcas_by_key: Dict[ObjectKeyType, model.HistoryDatasetCollectionAssociation]
    hdcas_by_id: Dict[int, model.HistoryDatasetCollectionAssociation]
    dces_by_key: Dict[ObjectKeyType, model.DatasetCollectionElement]
    dces_by_id: Dict[int, model.DatasetCollectionElement]
    lddas_by_key: Dict[ObjectKeyType, model.LibraryDatasetDatasetAssociation]
    hda_copied_from_sinks: Dict[ObjectKeyType, ObjectKeyType]
    hdca_copied_from_sinks: Dict[ObjectKeyType, ObjectKeyType]
    jobs_by_key: Dict[ObjectKeyType, model.Job]
    requires_hid: List[Union[model.HistoryDatasetAssociation, model.HistoryDatasetCollectionAssociation]]

    def __init__(self) -> None:
        self.libraries_by_key = {}
        self.hdas_by_key = {}
        self.hdas_by_id = {}
        self.hdcas_by_key = {}
        self.hdcas_by_id = {}
        self.dces_by_key = {}
        self.dces_by_id = {}
        self.lddas_by_key = {}
        self.hda_copied_from_sinks = {}
        self.hdca_copied_from_sinks = {}
        self.jobs_by_key = {}
        self.invocations_by_key: Dict[str, model.WorkflowInvocation] = {}
        self.implicit_collection_jobs_by_key: Dict[str, "ImplicitCollectionJobs"] = {}
        self.workflows_by_key: Dict[str, model.Workflow] = {}
        self.requires_hid = []

        self.new_history: Optional[model.History] = None

    def find_hda(
        self, input_key: ObjectKeyType, hda_id: Optional[int] = None
    ) -> Optional[model.HistoryDatasetAssociation]:
        hda = None
        if input_key in self.hdas_by_key:
            hda = self.hdas_by_key[input_key]
        elif isinstance(input_key, int) and input_key in self.hdas_by_id:
            # TODO: untangle this, I don't quite understand why we hdas_by_key and hdas_by_id
            hda = self.hdas_by_id[input_key]
        if input_key in self.hda_copied_from_sinks:
            hda = self.hdas_by_key[self.hda_copied_from_sinks[input_key]]
        return hda

    def find_hdca(self, input_key: ObjectKeyType) -> Optional[model.HistoryDatasetCollectionAssociation]:
        hdca = None
        if input_key in self.hdcas_by_key:
            hdca = self.hdcas_by_key[input_key]
        elif isinstance(input_key, int) and input_key in self.hdcas_by_id:
            hdca = self.hdcas_by_id[input_key]
        if input_key in self.hdca_copied_from_sinks:
            hdca = self.hdcas_by_key[self.hdca_copied_from_sinks[input_key]]
        return hdca

    def find_dce(self, input_key: ObjectKeyType) -> Optional[model.DatasetCollectionElement]:
        dce = None
        if input_key in self.dces_by_key:
            dce = self.dces_by_key[input_key]
        elif isinstance(input_key, int) and input_key in self.dces_by_id:
            dce = self.dces_by_id[input_key]
        return dce


class FileTracebackException(Exception):
    def __init__(self, traceback: str, *args, **kwargs) -> None:
        self.traceback = traceback


def get_import_model_store_for_directory(
    archive_dir: str, **kwd
) -> Union["DirectoryImportModelStore1901", "DirectoryImportModelStoreLatest"]:
    traceback_file = os.path.join(archive_dir, TRACEBACK)
    if not os.path.isdir(archive_dir):
        raise Exception(
            f"Could not find import model store for directory [{archive_dir}] (full path [{os.path.abspath(archive_dir)}])"
        )
    if os.path.exists(os.path.join(archive_dir, ATTRS_FILENAME_EXPORT)):
        if os.path.exists(traceback_file):
            with open(traceback_file) as tb:
                raise FileTracebackException(traceback=tb.read())
        return DirectoryImportModelStoreLatest(archive_dir, **kwd)
    else:
        return DirectoryImportModelStore1901(archive_dir, **kwd)


class DictImportModelStore(ModelImportStore):
    object_key = "encoded_id"

    def __init__(
        self,
        store_as_dict: Dict[str, Any],
        **kwd,
    ) -> None:
        self._store_as_dict = store_as_dict
        super().__init__(**kwd)
        self.archive_dir = ""

    def defines_new_history(self) -> bool:
        return DICT_STORE_ATTRS_KEY_HISTORY in self._store_as_dict

    def new_history_properties(self) -> Dict[str, Any]:
        return self._store_as_dict.get(DICT_STORE_ATTRS_KEY_HISTORY) or {}

    def datasets_properties(
        self,
    ) -> List[Dict[str, Any]]:
        return self._store_as_dict.get(DICT_STORE_ATTRS_KEY_DATASETS) or []

    def collections_properties(self) -> List[Dict[str, Any]]:
        return self._store_as_dict.get(DICT_STORE_ATTRS_KEY_COLLECTIONS) or []

    def library_properties(
        self,
    ) -> List[Dict[str, Any]]:
        return self._store_as_dict.get(DICT_STORE_ATTRS_KEY_LIBRARIES) or []

    def jobs_properties(self) -> List[Dict[str, Any]]:
        return self._store_as_dict.get(DICT_STORE_ATTRS_KEY_JOBS) or []

    def implicit_collection_jobs_properties(self) -> List[Dict[str, Any]]:
        return self._store_as_dict.get(DICT_STORE_ATTRS_KEY_IMPLICIT_COLLECTION_JOBS) or []

    def invocations_properties(self) -> List[Dict[str, Any]]:
        return self._store_as_dict.get(DICT_STORE_ATTRS_KEY_INVOCATIONS) or []

    def workflow_paths(self) -> Iterator[Tuple[str, str]]:
        return
        yield


def get_import_model_store_for_dict(
    as_dict: Dict[str, Any],
    **kwd,
) -> DictImportModelStore:
    return DictImportModelStore(as_dict, **kwd)


class BaseDirectoryImportModelStore(ModelImportStore):
    @abc.abstractmethod
    def _normalize_job_parameters(
        self,
        imported_job: model.Job,
        job_attrs: Dict[str, Any],
        _find_hda: Callable,
        _find_hdca: Callable,
        _find_dce: Callable,
    ) -> Dict[str, Any]:
        ...

    @abc.abstractmethod
    def _connect_job_io(
        self,
        imported_job: model.Job,
        job_attrs: Dict[str, Any],
        _find_hda: Callable,
        _find_hdca: Callable,
        _find_dce: Callable,
    ) -> None:
        ...

    @property
    def file_source_root(self) -> str:
        return self.archive_dir

    def defines_new_history(self) -> bool:
        new_history_attributes = os.path.join(self.archive_dir, ATTRS_FILENAME_HISTORY)
        return os.path.exists(new_history_attributes)

    def new_history_properties(self) -> Dict[str, Any]:
        new_history_attributes = os.path.join(self.archive_dir, ATTRS_FILENAME_HISTORY)
        history_properties = load(open(new_history_attributes))
        return history_properties

    def datasets_properties(self) -> List[Dict[str, Any]]:
        datasets_attrs_file_name = os.path.join(self.archive_dir, ATTRS_FILENAME_DATASETS)
        datasets_attrs = load(open(datasets_attrs_file_name))
        provenance_file_name = f"{datasets_attrs_file_name}.provenance"

        if os.path.exists(provenance_file_name):
            provenance_attrs = load(open(provenance_file_name))
            datasets_attrs += provenance_attrs

        return datasets_attrs

    def collections_properties(self) -> List[Dict[str, Any]]:
        return self._read_list_if_exists(ATTRS_FILENAME_COLLECTIONS)

    def library_properties(
        self,
    ) -> List[Dict[str, Any]]:
        libraries_attrs = self._read_list_if_exists(ATTRS_FILENAME_LIBRARIES)
        libraries_attrs.extend(self._read_list_if_exists(ATTRS_FILENAME_LIBRARY_FOLDERS))
        return libraries_attrs

    def jobs_properties(
        self,
    ) -> List[Dict[str, Any]]:
        return self._read_list_if_exists(ATTRS_FILENAME_JOBS)

    def implicit_collection_jobs_properties(self) -> List[Dict[str, Any]]:
        implicit_collection_jobs_attrs_file_name = os.path.join(
            self.archive_dir, ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS
        )
        try:
            return load(open(implicit_collection_jobs_attrs_file_name))
        except FileNotFoundError:
            return []

    def invocations_properties(
        self,
    ) -> List[Dict[str, Any]]:
        return self._read_list_if_exists(ATTRS_FILENAME_INVOCATIONS)

    def workflow_paths(self) -> Iterator[Tuple[str, str]]:
        workflows_directory = os.path.join(self.archive_dir, "workflows")
        if not os.path.exists(workflows_directory):
            return

        for name in os.listdir(workflows_directory):
            if name.endswith(".ga") or name.endswith(".abstract.cwl") or name.endswith(".html"):
                continue
            assert name.endswith(".gxwf.yml")
            workflow_key = name[0 : -len(".gxwf.yml")]
            yield workflow_key, os.path.join(workflows_directory, name)

    def _set_job_attributes(
        self, imported_job: model.Job, job_attrs: Dict[str, Any], force_terminal: bool = False
    ) -> None:
        ATTRIBUTES = (
            "info",
            "exit_code",
            "traceback",
            "job_messages",
            "tool_stdout",
            "tool_stderr",
            "job_stdout",
            "job_stderr",
        )
        for attribute in ATTRIBUTES:
            value = job_attrs.get(attribute)
            if value is not None:
                setattr(imported_job, attribute, value)
        if "stdout" in job_attrs:
            imported_job.tool_stdout = job_attrs.get("stdout")
            imported_job.tool_stderr = job_attrs.get("stderr")
        raw_state = job_attrs.get("state")
        if force_terminal and raw_state and raw_state not in model.Job.terminal_states:
            raw_state = model.Job.states.ERROR
        if raw_state:
            imported_job.set_state(raw_state)

    def _read_list_if_exists(self, file_name: str, required: bool = False) -> List[Dict[str, Any]]:
        file_name = os.path.join(self.archive_dir, file_name)
        if os.path.exists(file_name):
            attrs = load(open(file_name))
        else:
            if required:
                raise Exception("Failed to find file [%s] in model store archive" % file_name)
            attrs = []
        return attrs


def restore_times(
    model_object: Union[model.Job, model.WorkflowInvocation, model.WorkflowInvocationStep], attrs: Dict[str, Any]
) -> None:
    try:
        model_object.create_time = datetime.datetime.strptime(attrs["create_time"], "%Y-%m-%dT%H:%M:%S.%f")
    except Exception:
        pass
    try:
        model_object.update_time = datetime.datetime.strptime(attrs["update_time"], "%Y-%m-%dT%H:%M:%S.%f")
    except Exception:
        pass


class DirectoryImportModelStore1901(BaseDirectoryImportModelStore):
    object_key = "hid"

    def __init__(self, archive_dir: str, **kwd) -> None:
        archive_dir = os.path.realpath(archive_dir)
        # BioBlend previous to 17.01 exported histories with an extra subdir.
        if not os.path.exists(os.path.join(archive_dir, ATTRS_FILENAME_HISTORY)):
            for d in os.listdir(archive_dir):
                if os.path.isdir(os.path.join(archive_dir, d)):
                    archive_dir = os.path.join(archive_dir, d)
                    break
        self.archive_dir = archive_dir
        super().__init__(**kwd)

    def _connect_job_io(
        self,
        imported_job: model.Job,
        job_attrs: Dict[str, Any],
        _find_hda: Callable,
        _find_hdca: Callable,
        _find_dce: Callable,
    ) -> None:
        for output_key in job_attrs["output_datasets"]:
            output_hda = _find_hda(output_key)
            if output_hda:
                if not self.dataset_state_serialized:
                    # dataset state has not been serialized, get state from job
                    output_hda.state = imported_job.state
                imported_job.add_output_dataset(output_hda.name, output_hda)

        if "input_mapping" in job_attrs:
            for input_name, input_key in job_attrs["input_mapping"].items():
                input_hda = _find_hda(input_key)
                if input_hda:
                    imported_job.add_input_dataset(input_name, input_hda)

    def _normalize_job_parameters(
        self,
        imported_job: model.Job,
        job_attrs: Dict[str, Any],
        _find_hda: Callable,
        _find_hdca: Callable,
        _find_dce: Callable,
    ) -> Dict[str, Any]:
        def remap_objects(p, k, obj):
            if isinstance(obj, dict) and obj.get("__HistoryDatasetAssociation__", False):
                imported_hda = _find_hda(obj[self.object_key])
                if imported_hda:
                    return (k, {"src": "hda", "id": imported_hda.id})
            return (k, obj)

        params = job_attrs["params"]
        params = remap(params, remap_objects)
        return params

    def trust_hid(self, obj_attrs: Dict[str, Any]) -> bool:
        # We didn't do object tracking so we pretty much have to trust the HID and accept
        # that it will be wrong a lot.
        return True


class DirectoryImportModelStoreLatest(BaseDirectoryImportModelStore):
    object_key = "encoded_id"

    def __init__(self, archive_dir: str, **kwd) -> None:
        archive_dir = os.path.realpath(archive_dir)
        self.archive_dir = archive_dir
        super().__init__(**kwd)

    def _connect_job_io(
        self,
        imported_job: model.Job,
        job_attrs: Dict[str, Any],
        _find_hda: Callable,
        _find_hdca: Callable,
        _find_dce: Callable,
    ) -> None:
        if imported_job.command_line is None:
            imported_job.command_line = job_attrs.get("command_line")

        if "input_dataset_mapping" in job_attrs:
            for input_name, input_keys in job_attrs["input_dataset_mapping"].items():
                input_keys = input_keys or []
                for input_key in input_keys:
                    input_hda = _find_hda(input_key)
                    if input_hda:
                        imported_job.add_input_dataset(input_name, input_hda)

        if "input_dataset_collection_mapping" in job_attrs:
            for input_name, input_keys in job_attrs["input_dataset_collection_mapping"].items():
                input_keys = input_keys or []
                for input_key in input_keys:
                    input_hdca = _find_hdca(input_key)
                    if input_hdca:
                        imported_job.add_input_dataset_collection(input_name, input_hdca)

        if "input_dataset_collection_element_mapping" in job_attrs:
            for input_name, input_keys in job_attrs["input_dataset_collection_element_mapping"].items():
                input_keys = input_keys or []
                for input_key in input_keys:
                    input_dce = _find_dce(input_key)
                    if input_dce:
                        imported_job.add_input_dataset_collection_element(input_name, input_dce)

        if "output_dataset_mapping" in job_attrs:
            for output_name, output_keys in job_attrs["output_dataset_mapping"].items():
                output_keys = output_keys or []
                for output_key in output_keys:
                    output_hda = _find_hda(output_key)
                    if output_hda:
                        if not self.dataset_state_serialized:
                            # dataset state has not been serialized, get state from job
                            output_hda.state = imported_job.state
                        imported_job.add_output_dataset(output_name, output_hda)

        if "output_dataset_collection_mapping" in job_attrs:
            for output_name, output_keys in job_attrs["output_dataset_collection_mapping"].items():
                output_keys = output_keys or []
                for output_key in output_keys:
                    output_hdca = _find_hdca(output_key)
                    if output_hdca:
                        imported_job.add_output_dataset_collection(output_name, output_hdca)

    def _normalize_job_parameters(
        self,
        imported_job: model.Job,
        job_attrs: Dict[str, Any],
        _find_hda: Callable,
        _find_hdca: Callable,
        _find_dce: Callable,
    ) -> Dict[str, Any]:
        def remap_objects(p, k, obj):
            if isinstance(obj, dict) and "src" in obj and obj["src"] in ["hda", "hdca", "dce"]:
                if obj["src"] == "hda":
                    imported_hda = _find_hda(obj["id"])
                    if imported_hda:
                        new_id = imported_hda.id
                    else:
                        new_id = None
                elif obj["src"] == "hdca":
                    imported_hdca = _find_hdca(obj["id"])
                    if imported_hdca:
                        new_id = imported_hdca.id
                    else:
                        new_id = None
                elif obj["src"] == "dce":
                    imported_dce = _find_dce(obj["id"])
                    if imported_dce:
                        new_id = imported_dce.id
                    else:
                        new_id = None
                else:
                    raise NotImplementedError()
                new_obj = obj.copy()
                if not new_id and self.import_options.allow_edit:
                    # We may not have exported all job parameters, such as dces,
                    # but we shouldn't set the object_id to none in that case.
                    new_id = obj["id"]
                new_obj["id"] = new_id
                return (k, new_obj)

            return (k, obj)

        params = job_attrs["params"]
        params = remap(params, remap_objects)
        return cast(Dict[str, Any], params)


class BagArchiveImportModelStore(DirectoryImportModelStoreLatest):
    def __init__(self, bag_archive: str, **kwd) -> None:
        archive_dir = tempfile.mkdtemp()
        bdb.extract_bag(bag_archive, output_path=archive_dir)
        # Why this line though...?
        archive_dir = os.path.join(archive_dir, os.listdir(archive_dir)[0])
        bdb.revert_bag(archive_dir)
        super().__init__(archive_dir, **kwd)


class ModelExportStore(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def export_history(
        self, history: model.History, include_hidden: bool = False, include_deleted: bool = False
    ) -> None:
        """Export history to store."""

    @abc.abstractmethod
    def export_library(
        self, library: model.Library, include_hidden: bool = False, include_deleted: bool = False
    ) -> None:
        """Export library to store."""

    @abc.abstractmethod
    def export_library_folder(
        self, library_folder: model.LibraryFolder, include_hidden: bool = False, include_deleted: bool = False
    ) -> None:
        """Export library folder to store."""

    @abc.abstractmethod
    def export_workflow_invocation(self, workflow_invocation, include_hidden=False, include_deleted=False):
        """Export workflow invocation to store."""

    @abc.abstractmethod
    def add_dataset_collection(
        self, collection: Union[model.DatasetCollection, model.HistoryDatasetCollectionAssociation]
    ):
        """Add Dataset Collection or HDCA to export store."""

    @abc.abstractmethod
    def add_dataset(self, dataset: model.DatasetInstance, include_files: bool = True):
        """
        Add HDA to export store.

        ``include_files`` controls whether file contents are exported as well.
        """

    @abc.abstractmethod
    def __enter__(self):
        """Export store should be used as context manager."""

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Export store should be used as context manager."""


class DirectoryModelExportStore(ModelExportStore):
    app: Optional[StoreAppProtocol]
    file_sources: Optional[ConfiguredFileSources]

    def __init__(
        self,
        export_directory: StrPath,
        app: Optional[StoreAppProtocol] = None,
        file_sources: Optional[ConfiguredFileSources] = None,
        for_edit: bool = False,
        serialize_dataset_objects: Optional[bool] = None,
        export_files: Optional[str] = None,
        strip_metadata_files: bool = True,
        serialize_jobs: bool = True,
        user_context=None,
    ) -> None:
        """
        :param export_directory: path to export directory. Will be created if it does not exist.
        :param app: Galaxy App or app-like object. Must be provided if `for_edit` and/or `serialize_dataset_objects` are True
        :param for_edit: Allow modifying existing HDA and dataset metadata during import.
        :param serialize_dataset_objects: If True will encode IDs using the host secret. Defaults `for_edit`.
        :param export_files: How files should be exported, can be 'symlink', 'copy' or None, in which case files
                             will not be serialized.
        :param serialize_jobs: Include job data in model export. Not needed for set_metadata script.
        """
        if not os.path.exists(export_directory):
            os.makedirs(export_directory)

        sessionless = False
        if app is not None:
            self.app = app
            security = app.security
            sessionless = False
            if file_sources is None:
                file_sources = app.file_sources
        else:
            sessionless = True
            security = IdEncodingHelper(id_secret="randomdoesntmatter")

        self.user_context = ProvidesUserFileSourcesUserContext(user_context)
        self.file_sources = file_sources
        self.serialize_jobs = serialize_jobs
        self.sessionless = sessionless
        self.security = security

        self.export_directory = export_directory
        self.serialization_options = model.SerializationOptions(
            for_edit=for_edit,
            serialize_dataset_objects=serialize_dataset_objects,
            strip_metadata_files=strip_metadata_files,
            serialize_files_handler=self,
        )
        self.export_files = export_files
        self.included_datasets: Dict[model.DatasetInstance, Tuple[model.DatasetInstance, bool]] = {}
        self.included_collections: List[Union[model.DatasetCollection, model.HistoryDatasetCollectionAssociation]] = []
        self.included_libraries: List[model.Library] = []
        self.included_library_folders: List[model.LibraryFolder] = []
        self.included_invocations: List[model.WorkflowInvocation] = []
        self.collection_datasets: Set[int] = set()
        self.collections_attrs: List[Union[model.DatasetCollection, model.HistoryDatasetCollectionAssociation]] = []
        self.dataset_id_to_path: Dict[int, Tuple[Optional[str], Optional[str]]] = {}

        self.job_output_dataset_associations: Dict[int, Dict[str, model.DatasetInstance]] = {}

    @property
    def workflows_directory(self) -> str:
        return os.path.join(self.export_directory, "workflows")

    def serialize_files(self, dataset: model.DatasetInstance, as_dict: JsonDictT) -> None:
        if self.export_files is None:
            return None

        add: Callable[[str, str], None]
        if self.export_files == "symlink":
            add = os.symlink
        elif self.export_files == "copy":

            def add(src, dest):
                if os.path.isdir(src):
                    shutil.copytree(src, dest)
                else:
                    shutil.copyfile(src, dest)

        else:
            raise Exception(f"Unknown export_files parameter type encountered {self.export_files}")

        export_directory = self.export_directory

        _, include_files = self.included_datasets[dataset]
        if not include_files:
            return

        file_name, extra_files_path = None, None
        try:
            _file_name = dataset.file_name
            if os.path.exists(_file_name):
                file_name = _file_name
        except ObjectNotFound:
            pass

        if dataset.extra_files_path_exists():
            extra_files_path = dataset.extra_files_path
        else:
            pass

        dir_name = "datasets"
        dir_path = os.path.join(export_directory, dir_name)
        dataset_hid = as_dict["hid"]
        assert dataset_hid, as_dict

        if dataset.dataset.id in self.dataset_id_to_path:
            file_name, extra_files_path = self.dataset_id_to_path[dataset.dataset.id]
            if file_name is not None:
                as_dict["file_name"] = file_name
            if extra_files_path is not None:
                as_dict["extra_files_path"] = extra_files_path
            return

        if file_name:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            target_filename = get_export_dataset_filename(as_dict["name"], as_dict["extension"], dataset_hid)
            arcname = os.path.join(dir_name, target_filename)

            src = file_name
            dest = os.path.join(export_directory, arcname)
            add(src, dest)
            as_dict["file_name"] = arcname

        if extra_files_path:
            try:
                file_list = os.listdir(extra_files_path)
            except OSError:
                file_list = []

            if len(file_list):
                arcname = os.path.join(dir_name, f"extra_files_path_{dataset_hid}")
                add(extra_files_path, os.path.join(export_directory, arcname))
                as_dict["extra_files_path"] = arcname
            else:
                as_dict["extra_files_path"] = ""

        self.dataset_id_to_path[dataset.dataset.id] = (as_dict.get("file_name"), as_dict.get("extra_files_path"))

    def exported_key(
        self,
        obj: Union[model.DatasetInstance, model.RepresentById],
    ) -> Union[str, int]:
        return self.serialization_options.get_identifier(self.security, obj)

    def __enter__(self) -> "DirectoryModelExportStore":
        return self

    def push_metadata_files(self):
        for dataset in self.included_datasets:
            for metadata_element in dataset.metadata.values():
                if isinstance(metadata_element, model.MetadataFile):
                    metadata_element.update_from_file(metadata_element.file_name)

    def export_job(self, job: model.Job, tool=None, include_job_data=True):
        self.export_jobs([job], include_job_data=include_job_data)
        tool_source = getattr(tool, "tool_source", None)
        if tool_source:
            with open(os.path.join(self.export_directory, "tool.xml"), "w") as out:
                out.write(tool_source.to_string())

    def export_jobs(
        self,
        jobs: Iterable[model.Job],
        jobs_attrs: Optional[List[Dict[str, Any]]] = None,
        include_job_data: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Export jobs.

        ``include_job_data`` determines whether datasets associated with jobs should be exported as well.
        This should generally be ``True``, except when re-exporting a job (to store the generated command line)
        when running the set_meta script.
        """
        jobs_attrs = jobs_attrs or []
        for job in jobs:
            job_attrs = job.serialize(self.security, self.serialization_options)

            if include_job_data:
                # -- Get input, output datasets. --

                input_dataset_mapping: Dict[str, List[Union[str, int]]] = {}
                output_dataset_mapping: Dict[str, List[Union[str, int]]] = {}
                input_dataset_collection_mapping: Dict[str, List[Union[str, int]]] = {}
                input_dataset_collection_element_mapping: Dict[str, List[Union[str, int]]] = {}
                output_dataset_collection_mapping: Dict[str, List[Union[str, int]]] = {}
                implicit_output_dataset_collection_mapping: Dict[str, List[Union[str, int]]] = {}

                for assoc in job.input_datasets:
                    # Optional data inputs will not have a dataset.
                    if assoc.dataset:
                        name = assoc.name
                        if name not in input_dataset_mapping:
                            input_dataset_mapping[name] = []

                        input_dataset_mapping[name].append(self.exported_key(assoc.dataset))
                        if include_job_data:
                            self.add_dataset(assoc.dataset)

                for assoc in job.output_datasets:
                    # Optional data inputs will not have a dataset.
                    if assoc.dataset:
                        name = assoc.name
                        if name not in output_dataset_mapping:
                            output_dataset_mapping[name] = []

                        output_dataset_mapping[name].append(self.exported_key(assoc.dataset))
                        if include_job_data:
                            self.add_dataset(assoc.dataset)

                for assoc in job.input_dataset_collections:
                    # Optional data inputs will not have a dataset.
                    if assoc.dataset_collection:
                        name = assoc.name
                        if name not in input_dataset_collection_mapping:
                            input_dataset_collection_mapping[name] = []

                        input_dataset_collection_mapping[name].append(self.exported_key(assoc.dataset_collection))
                        if include_job_data:
                            self.export_collection(assoc.dataset_collection)

                for assoc in job.input_dataset_collection_elements:
                    if assoc.dataset_collection_element:
                        name = assoc.name
                        if name not in input_dataset_collection_element_mapping:
                            input_dataset_collection_element_mapping[name] = []

                        input_dataset_collection_element_mapping[name].append(
                            self.exported_key(assoc.dataset_collection_element)
                        )
                        if include_job_data:
                            if assoc.dataset_collection_element.is_collection:
                                self.export_collection(assoc.dataset_collection_element.element_object)
                            else:
                                self.add_dataset(assoc.dataset_collection_element.element_object)

                for assoc in job.output_dataset_collection_instances:
                    # Optional data outputs will not have a dataset.
                    # These are implicit outputs, we don't need to export them
                    if assoc.dataset_collection_instance:
                        name = assoc.name
                        if name not in output_dataset_collection_mapping:
                            output_dataset_collection_mapping[name] = []

                        output_dataset_collection_mapping[name].append(
                            self.exported_key(assoc.dataset_collection_instance)
                        )

                for assoc in job.output_dataset_collections:
                    if assoc.dataset_collection:
                        name = assoc.name

                        if name not in implicit_output_dataset_collection_mapping:
                            implicit_output_dataset_collection_mapping[name] = []

                        implicit_output_dataset_collection_mapping[name].append(
                            self.exported_key(assoc.dataset_collection)
                        )
                        if include_job_data:
                            self.export_collection(assoc.dataset_collection)

                job_attrs["input_dataset_mapping"] = input_dataset_mapping
                job_attrs["input_dataset_collection_mapping"] = input_dataset_collection_mapping
                job_attrs["input_dataset_collection_element_mapping"] = input_dataset_collection_element_mapping
                job_attrs["output_dataset_mapping"] = output_dataset_mapping
                job_attrs["output_dataset_collection_mapping"] = output_dataset_collection_mapping
                job_attrs["implicit_output_dataset_collection_mapping"] = implicit_output_dataset_collection_mapping

            jobs_attrs.append(job_attrs)

        jobs_attrs_filename = os.path.join(self.export_directory, ATTRS_FILENAME_JOBS)
        with open(jobs_attrs_filename, "w") as jobs_attrs_out:
            jobs_attrs_out.write(json_encoder.encode(jobs_attrs))
        return jobs_attrs

    def export_history(
        self, history: model.History, include_hidden: bool = False, include_deleted: bool = False
    ) -> None:
        app = self.app
        assert app, "exporting histories requires being bound to a session and Galaxy app object"
        export_directory = self.export_directory

        history_attrs = history.serialize(app.security, self.serialization_options)
        history_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_HISTORY)
        with open(history_attrs_filename, "w") as history_attrs_out:
            dump(history_attrs, history_attrs_out)

        sa_session = app.model.session

        # Write collections' attributes (including datasets list) to file.
        query = (
            sa_session.query(model.HistoryDatasetCollectionAssociation)
            .filter(model.HistoryDatasetCollectionAssociation.history == history)
            .filter(model.HistoryDatasetCollectionAssociation.deleted == expression.false())
        )
        collections = query.all()

        for collection in collections:
            # filter this ?
            if not collection.populated:
                break
            if collection.state != "ok":
                break

            self.export_collection(collection, include_deleted=include_deleted)

        # Write datasets' attributes to file.
        actions_backref = model.Dataset.actions  # type: ignore[attr-defined]
        query = (
            sa_session.query(model.HistoryDatasetAssociation)
            .filter(model.HistoryDatasetAssociation.history == history)
            .join(model.Dataset)
            .options(joinedload(model.HistoryDatasetAssociation.dataset).joinedload(actions_backref))
            .order_by(model.HistoryDatasetAssociation.hid)
            .filter(model.Dataset.purged == expression.false())
        )
        datasets = query.all()
        for dataset in datasets:
            dataset.annotation = get_item_annotation_str(sa_session, history.user, dataset)
            add_dataset = (dataset.visible or include_hidden) and (not dataset.deleted or include_deleted)
            if dataset.id in self.collection_datasets:
                add_dataset = True

            if dataset not in self.included_datasets:
                self.add_dataset(dataset, include_files=add_dataset)

    def export_library(
        self, library: model.Library, include_hidden: bool = False, include_deleted: bool = False
    ) -> None:
        self.included_libraries.append(library)
        root_folder = library.root_folder
        self.export_library_folder_contents(root_folder, include_hidden=include_hidden, include_deleted=include_deleted)

    def export_library_folder(self, library_folder: model.LibraryFolder, include_hidden=False, include_deleted=False):
        self.included_library_folders.append(library_folder)
        self.export_library_folder_contents(
            library_folder, include_hidden=include_hidden, include_deleted=include_deleted
        )

    def export_library_folder_contents(
        self, library_folder: model.LibraryFolder, include_hidden: bool = False, include_deleted: bool = False
    ) -> None:
        for library_dataset in library_folder.datasets:
            ldda = library_dataset.library_dataset_dataset_association
            add_dataset = (not ldda.visible or not include_hidden) and (not ldda.deleted or include_deleted)
            self.add_dataset(ldda, add_dataset)
        for folder in library_folder.folders:
            self.export_library_folder_contents(folder, include_hidden=include_hidden, include_deleted=include_deleted)

    def export_workflow_invocation(
        self, workflow_invocation: model.WorkflowInvocation, include_hidden: bool = False, include_deleted: bool = False
    ) -> None:
        self.included_invocations.append(workflow_invocation)
        for input_dataset in workflow_invocation.input_datasets:
            self.add_dataset(input_dataset.dataset)
        for output_dataset in workflow_invocation.output_datasets:
            self.add_dataset(output_dataset.dataset)
        for input_dataset_collection in workflow_invocation.input_dataset_collections:
            self.export_collection(input_dataset_collection.dataset_collection)
        for output_dataset_collection in workflow_invocation.output_dataset_collections:
            self.export_collection(output_dataset_collection.dataset_collection)
        for workflow_invocation_step in workflow_invocation.steps:
            for assoc in workflow_invocation_step.output_datasets:
                self.add_dataset(assoc.dataset)
            for assoc in workflow_invocation_step.output_dataset_collections:
                self.export_collection(assoc.dataset_collection)

    def add_job_output_dataset_associations(
        self, job_id: int, name: str, dataset_instance: model.DatasetInstance
    ) -> None:
        job_output_dataset_associations = self.job_output_dataset_associations
        if job_id not in job_output_dataset_associations:
            job_output_dataset_associations[job_id] = {}
        job_output_dataset_associations[job_id][name] = dataset_instance

    def export_collection(
        self,
        collection: Union[model.DatasetCollection, model.HistoryDatasetCollectionAssociation],
        include_deleted: bool = False,
        include_hidden: bool = False,
    ) -> None:
        self.add_dataset_collection(collection)

        # export datasets for this collection
        has_collection = (
            collection.collection if isinstance(collection, model.HistoryDatasetCollectionAssociation) else collection
        )
        for collection_dataset in has_collection.dataset_instances:
            # ignoring include_hidden since the datasets will default to hidden for this collection.
            if collection_dataset.deleted and not include_deleted:
                include_files = False
            else:
                include_files = True

            self.add_dataset(collection_dataset, include_files=include_files)
            self.collection_datasets.add(collection_dataset.id)

    def add_dataset_collection(
        self, collection: Union[model.DatasetCollection, model.HistoryDatasetCollectionAssociation]
    ) -> None:
        self.collections_attrs.append(collection)
        self.included_collections.append(collection)

    def add_dataset(self, dataset: model.DatasetInstance, include_files: bool = True) -> None:
        self.included_datasets[dataset] = (dataset, include_files)

    def _finalize(self) -> None:
        export_directory = self.export_directory

        datasets_attrs = []
        provenance_attrs = []
        for dataset, include_files in self.included_datasets.values():
            if include_files:
                datasets_attrs.append(dataset)
            else:
                provenance_attrs.append(dataset)

        def to_json(attributes):
            return json_encoder.encode([a.serialize(self.security, self.serialization_options) for a in attributes])

        datasets_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_DATASETS)
        with open(datasets_attrs_filename, "w") as datasets_attrs_out:
            datasets_attrs_out.write(to_json(datasets_attrs))

        with open(f"{datasets_attrs_filename}.provenance", "w") as provenance_attrs_out:
            provenance_attrs_out.write(to_json(provenance_attrs))

        libraries_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_LIBRARIES)
        with open(libraries_attrs_filename, "w") as libraries_attrs_out:
            libraries_attrs_out.write(to_json(self.included_libraries))

        library_folders_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_LIBRARY_FOLDERS)
        with open(library_folders_attrs_filename, "w") as library_folder_attrs_out:
            library_folder_attrs_out.write(to_json(self.included_library_folders))

        collections_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_COLLECTIONS)
        with open(collections_attrs_filename, "w") as collections_attrs_out:
            collections_attrs_out.write(to_json(self.collections_attrs))

        jobs_attrs = []
        for job_id, job_output_dataset_associations in self.job_output_dataset_associations.items():
            output_dataset_mapping: Dict[str, List[Union[str, int]]] = {}
            for name, dataset in job_output_dataset_associations.items():
                if name not in output_dataset_mapping:
                    output_dataset_mapping[name] = []
                output_dataset_mapping[name].append(self.exported_key(dataset))
            jobs_attrs.append({"id": job_id, "output_dataset_mapping": output_dataset_mapping})

        if self.serialize_jobs:
            #
            # Write jobs attributes file.
            #

            # Get all jobs associated with included HDAs.
            jobs_dict: Dict[str, model.Job] = {}
            implicit_collection_jobs_dict = {}

            def record_job(job):
                if not job:
                    # No viable job.
                    return

                jobs_dict[job.id] = job
                icja = job.implicit_collection_jobs_association
                if icja:
                    implicit_collection_jobs = icja.implicit_collection_jobs
                    implicit_collection_jobs_dict[implicit_collection_jobs.id] = implicit_collection_jobs

            def record_associated_jobs(obj):
                # Get the job object.
                job = None
                for assoc in getattr(obj, "creating_job_associations", []):
                    # For mapped over jobs obj could be DatasetCollection, which has no creating_job_association
                    job = assoc.job
                    break
                record_job(job)

            for hda, _include_files in self.included_datasets.values():
                # Get the associated job, if any. If this hda was copied from another,
                # we need to find the job that created the original hda
                if not isinstance(hda, (model.HistoryDatasetAssociation, model.LibraryDatasetDatasetAssociation)):
                    raise Exception(
                        f"Expected a HistoryDatasetAssociation or LibraryDatasetDatasetAssociation, but got a {type(hda)}: {hda}"
                    )
                job_hda = hda
                while getattr(
                    job_hda, "copied_from_history_dataset_association", None
                ):  # should this check library datasets as well?
                    job_hda = job_hda.copied_from_history_dataset_association  # type: ignore[union-attr]
                if not job_hda.creating_job_associations:
                    # No viable HDA found.
                    continue

                record_associated_jobs(job_hda)

            for hdca in self.included_collections:
                record_associated_jobs(hdca)

            self.export_jobs(jobs_dict.values(), jobs_attrs=jobs_attrs)

            for invocation in self.included_invocations:
                for step in invocation.steps:
                    for job in step.jobs:
                        record_job(job)
                    if step.implicit_collection_jobs:
                        implicit_collection_jobs = step.implicit_collection_jobs
                        implicit_collection_jobs_dict[implicit_collection_jobs.id] = implicit_collection_jobs

            # Get jobs' attributes.

            icjs_attrs = []
            for icj in implicit_collection_jobs_dict.values():
                icj_attrs = icj.serialize(self.security, self.serialization_options)
                icjs_attrs.append(icj_attrs)

            icjs_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS)
            with open(icjs_attrs_filename, "w") as icjs_attrs_out:
                icjs_attrs_out.write(json_encoder.encode(icjs_attrs))

        invocations_attrs = []

        for invocation in self.included_invocations:
            invocation_attrs = invocation.serialize(self.security, self.serialization_options)

            workflows_directory = self.workflows_directory
            safe_makedirs(workflows_directory)

            workflow = invocation.workflow
            workflow_key = self.serialization_options.get_identifier(self.security, workflow)
            history = invocation.history
            assert invocation_attrs
            invocation_attrs["workflow"] = workflow_key

            if not self.app:
                raise Exception(f"Missing self.app in {self}.")
            self.app.workflow_contents_manager.store_workflow_artifacts(
                workflows_directory, workflow_key, workflow, user=history.user, history=history
            )
            invocations_attrs.append(invocation_attrs)

        invocations_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_INVOCATIONS)
        with open(invocations_attrs_filename, "w") as invocations_attrs_out:
            dump(invocations_attrs, invocations_attrs_out)

        export_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_EXPORT)
        with open(export_attrs_filename, "w") as export_attrs_out:
            dump({"galaxy_export_version": GALAXY_EXPORT_VERSION}, export_attrs_out)

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> bool:
        if exc_type is None:
            self._finalize()
        # http://effbot.org/zone/python-with-statement.htm
        # Ignores TypeError exceptions
        return isinstance(exc_val, TypeError)


class WriteCrates:
    included_invocations: List[model.WorkflowInvocation]
    export_directory: StrPath
    included_datasets: Dict[model.DatasetInstance, Tuple[model.DatasetInstance, bool]]
    dataset_id_to_path: Dict[int, Tuple[Optional[str], Optional[str]]]

    @property
    @abc.abstractmethod
    def workflows_directory(self) -> str:
        ...

    def _generate_markdown_readme(self) -> str:
        markdown_parts: List[str] = []
        if self._is_single_invocation_export():
            invocation = self.included_invocations[0]
            name = invocation.workflow.name
            create_time = invocation.create_time
            markdown_parts.append("# Galaxy Workflow Invocation Export")
            markdown_parts.append("")
            markdown_parts.append(f"This crate describes the invocation of workflow {name} executed at {create_time}.")
        else:
            markdown_parts.append("# Galaxy Dataset Export")

        return "\n".join(markdown_parts)

    def _is_single_invocation_export(self) -> bool:
        return len(self.included_invocations) == 1

    def _init_crate(self) -> ROCrate:
        is_invocation_export = self._is_single_invocation_export()
        if is_invocation_export:
            invocation_crate_builder = WorkflowRunCrateProfileBuilder(self)
            return invocation_crate_builder.build_crate()

        ro_crate = ROCrate()
        markdown_path = os.path.join(self.export_directory, "README.md")
        with open(markdown_path, "w") as f:
            f.write(self._generate_markdown_readme())

        properties = {
            "name": "README.md",
            "encodingFormat": "text/markdown",
            "about": {"@id": "./"},
        }
        ro_crate.add_file(
            markdown_path,
            dest_path="README.md",
            properties=properties,
        )

        for dataset, _ in self.included_datasets.values():
            if dataset.dataset.id in self.dataset_id_to_path:
                file_name, _ = self.dataset_id_to_path[dataset.dataset.id]
                name = dataset.name
                encoding_format = dataset.datatype.get_mime()
                properties = {
                    "name": name,
                    "encodingFormat": encoding_format,
                }
                ro_crate.add_file(
                    file_name,
                    dest_path=file_name,
                    properties=properties,
                )

        workflows_directory = self.workflows_directory
        if os.path.exists(workflows_directory):
            for filename in os.listdir(workflows_directory):
                is_computational_wf = not filename.endswith(".cwl")
                workflow_cls = ComputationalWorkflow if is_computational_wf else WorkflowDescription
                lang = "galaxy" if not filename.endswith(".cwl") else "cwl"
                dest_path = os.path.join("workflows", filename)
                is_main_entity = is_invocation_export and is_computational_wf
                ro_crate.add_workflow(
                    source=os.path.join(workflows_directory, filename),
                    dest_path=dest_path,
                    main=is_main_entity,
                    cls=workflow_cls,
                    lang=lang,
                )

        found_workflow_licenses = set()
        for workflow_invocation in self.included_invocations:
            workflow = workflow_invocation.workflow
            license = workflow.license
            if license:
                found_workflow_licenses.add(license)
        if len(found_workflow_licenses) == 1:
            ro_crate.license = next(iter(found_workflow_licenses))

        # TODO: license per workflow
        # TODO: API options to license workflow outputs seprately
        # TODO: Export report as PDF and stick it in here
        return ro_crate


class WorkflowInvocationOnlyExportStore(DirectoryModelExportStore):
    def export_history(self, history: model.History, include_hidden: bool = False, include_deleted: bool = False):
        """Export history to store."""
        raise NotImplementedError()

    def export_library(self, history, include_hidden=False, include_deleted=False):
        """Export library to store."""
        raise NotImplementedError()

    @property
    def only_invocation(self) -> model.WorkflowInvocation:
        assert len(self.included_invocations) == 1
        return self.included_invocations[0]


@dataclass
class BcoExportOptions:
    galaxy_url: str
    galaxy_version: str
    merge_history_metadata: bool = False
    override_environment_variables: Optional[Dict[str, str]] = None
    override_empirical_error: Optional[Dict[str, str]] = None
    override_algorithmic_error: Optional[Dict[str, str]] = None
    override_xref: Optional[List[XrefItem]] = None


class BcoModelExportStore(WorkflowInvocationOnlyExportStore):
    def __init__(self, uri, export_options: BcoExportOptions, **kwds):
        temp_output_dir = tempfile.mkdtemp()
        self.temp_output_dir = temp_output_dir
        if "://" in str(uri):
            self.out_file = os.path.join(temp_output_dir, "out")
            self.file_source_uri = uri
            export_directory = os.path.join(temp_output_dir, "export")
        else:
            self.out_file = uri
            self.file_source_uri = None
            export_directory = temp_output_dir
        self.export_options = export_options
        super().__init__(export_directory, **kwds)

    def _finalize(self):
        super()._finalize()
        core_biocompute_object, object_id = self._core_biocompute_object_and_object_id()
        write_to_file(object_id, core_biocompute_object, self.out_file)
        if self.file_source_uri:
            file_source_path = self.file_sources.get_file_source_path(self.file_source_uri)
            file_source = file_source_path.file_source
            assert os.path.exists(self.out_file)
            file_source.write_from(file_source_path.path, self.out_file, user_context=self.user_context)

    def _core_biocompute_object_and_object_id(self) -> Tuple[BioComputeObjectCore, str]:
        assert self.app  # need app.security to do anything...
        export_options = self.export_options
        workflow_invocation = self.only_invocation
        history = workflow_invocation.history
        workflow = workflow_invocation.workflow
        stored_workflow = workflow.stored_workflow

        def get_dataset_url(encoded_dataset_id: str):
            return f"{export_options.galaxy_url}api/datasets/{encoded_dataset_id}/display"

        # pull in the creator_metadata info from workflow if it exists
        contributors = get_contributors(workflow.creator_metadata)
        provenance_domain = ProvenanceDomain(
            name=workflow.name,
            version=bco_workflow_version(workflow),
            review=[],
            contributors=contributors,
            license=workflow.license or "",
            created=workflow_invocation.create_time.isoformat(),
            modified=workflow_invocation.update_time.isoformat(),
        )

        keywords = []
        for tag in stored_workflow.tags:
            keywords.append(tag.user_tname)
        if export_options.merge_history_metadata:
            for tag in history.tags:
                if tag.user_tname not in keywords:
                    keywords.append(tag.user_tname)

        # metrics = {}  ... TODO
        pipeline_steps: List[PipelineStep] = []
        software_prerequisite_tracker = SoftwarePrerequisteTracker()
        input_subdomain_items: List[InputSubdomainItem] = []
        output_subdomain_items: List[OutputSubdomainItem] = []
        for step in workflow_invocation.steps:
            workflow_step = step.workflow_step
            software_prerequisite_tracker.register_step(workflow_step)
            if workflow_step.type == "tool":
                workflow_outputs_list = set()
                output_list: List[DescriptionDomainUri] = []
                input_list: List[DescriptionDomainUri] = []
                for wo in workflow_step.workflow_outputs:
                    workflow_outputs_list.add(wo.output_name)
                for job in step.jobs:
                    for job_input in job.input_datasets:
                        if hasattr(job_input.dataset, "dataset_id"):
                            encoded_dataset_id = self.app.security.encode_id(job_input.dataset.dataset_id)
                            url = get_dataset_url(encoded_dataset_id)
                            input_uri_obj = DescriptionDomainUri(
                                # TODO: that should maybe be a step prefix + element identifier where appropriate.
                                filename=job_input.dataset.name,
                                uri=url,
                                access_time=job_input.dataset.create_time.isoformat(),
                            )
                            input_list.append(input_uri_obj)

                    for job_output in job.output_datasets:
                        if hasattr(job_output.dataset, "dataset_id"):
                            encoded_dataset_id = self.app.security.encode_id(job_output.dataset.dataset_id)
                            url = get_dataset_url(encoded_dataset_id)
                            output_obj = DescriptionDomainUri(
                                filename=job_output.dataset.name,
                                uri=url,
                                access_time=job_output.dataset.create_time.isoformat(),
                            )
                            output_list.append(output_obj)

                            if job_output.name in workflow_outputs_list:
                                output = OutputSubdomainItem(
                                    mediatype=job_output.dataset.extension,
                                    uri=InputAndOutputDomainUri(
                                        filename=job_output.dataset.name,
                                        uri=url,
                                        access_time=job_output.dataset.create_time.isoformat(),
                                    ),
                                )
                                output_subdomain_items.append(output)
                step_index = workflow_step.order_index
                step_name = workflow_step.label or workflow_step.tool_id
                pipeline_step = PipelineStep(
                    step_number=step_index,
                    name=step_name,
                    description=workflow_step.annotations[0].annotation if workflow_step.annotations else "",
                    version=workflow_step.tool_version,
                    prerequisite=[],
                    input_list=input_list,
                    output_list=output_list,
                )
                pipeline_steps.append(pipeline_step)

            if workflow_step.type == "data_input" and step.output_datasets:
                for output_assoc in step.output_datasets:
                    encoded_dataset_id = self.app.security.encode_id(output_assoc.dataset_id)
                    url = get_dataset_url(encoded_dataset_id)
                    input_obj = InputSubdomainItem(
                        uri=Uri(
                            uri=url,
                            filename=workflow_step.label,
                            access_time=workflow_step.update_time.isoformat(),
                        ),
                    )
                    input_subdomain_items.append(input_obj)

            if workflow_step.type == "data_collection_input" and step.output_dataset_collections:
                for output_dataset_collection_association in step.output_dataset_collections:
                    encoded_dataset_id = self.app.security.encode_id(
                        output_dataset_collection_association.dataset_collection_id
                    )
                    url = f"{export_options.galaxy_url}api/dataset_collections/{encoded_dataset_id}/download"
                    input_obj = InputSubdomainItem(
                        uri=Uri(
                            uri=url,
                            filename=workflow_step.label,
                            access_time=workflow_step.update_time.isoformat(),
                        ),
                    )
                    input_subdomain_items.append(input_obj)

        usability_domain_str: List[str] = []
        for a in stored_workflow.annotations:
            usability_domain_str.append(a.annotation)
        if export_options.merge_history_metadata:
            for h in history.annotations:
                usability_domain_str.append(h.annotation)

        parametric_domain_items: List[ParametricDomainItem] = []
        for inv_step in workflow_invocation.steps:
            try:
                for k, v in inv_step.workflow_step.tool_inputs.items():
                    param, value, step = k, v, inv_step.workflow_step.order_index
                    parametric_domain_items.append(
                        ParametricDomainItem(param=str(param), value=str(value), step=str(step))
                    )
            except Exception:
                continue

        encoded_workflow_id = self.app.security.encode_id(workflow.id)
        execution_domain = galaxy_execution_domain(
            export_options.galaxy_url,
            f"{export_options.galaxy_url}api/workflows?encoded_workflow_id={encoded_workflow_id}",
            software_prerequisite_tracker.software_prerequisites,
            export_options.override_environment_variables,
        )
        extension_domain = extension_domains(export_options.galaxy_url, export_options.galaxy_version)
        error_domain = ErrorDomain(
            empirical_error=export_options.override_empirical_error or {},
            algorithmic_error=export_options.override_algorithmic_error or {},
        )
        usability_domain = UsabilityDomain(__root__=usability_domain_str)
        description_domain = DescriptionDomain(
            keywords=keywords,
            xref=export_options.override_xref or [],
            platform=["Galaxy"],
            pipeline_steps=pipeline_steps,
        )
        parametric_domain = ParametricDomain(__root__=parametric_domain_items)
        io_domain = InputAndOutputDomain(
            input_subdomain=input_subdomain_items,
            output_subdomain=output_subdomain_items,
        )
        core = BioComputeObjectCore(
            description_domain=description_domain,
            error_domain=error_domain,
            execution_domain=execution_domain,
            extension_domain=extension_domain,
            io_domain=io_domain,
            parametric_domain=parametric_domain,
            provenance_domain=provenance_domain,
            usability_domain=usability_domain,
        )
        encoded_invocation_id = self.app.security.encode_id(workflow_invocation.id)
        url = f"{export_options.galaxy_url}api/invocations/{encoded_invocation_id}"
        return core, url


class ROCrateModelExportStore(DirectoryModelExportStore, WriteCrates):
    def __init__(self, crate_directory: StrPath, **kwds) -> None:
        self.crate_directory = crate_directory
        super().__init__(crate_directory, export_files="symlink", **kwds)

    def _finalize(self) -> None:
        super()._finalize()
        ro_crate = self._init_crate()
        ro_crate.write(self.crate_directory)


class ROCrateArchiveModelExportStore(DirectoryModelExportStore, WriteCrates):
    file_source_uri: Optional[StrPath]
    out_file: StrPath

    def __init__(self, uri: StrPath, **kwds) -> None:
        temp_output_dir = tempfile.mkdtemp()
        self.temp_output_dir = temp_output_dir
        if "://" in str(uri):
            self.out_file = os.path.join(temp_output_dir, "out")
            self.file_source_uri = uri
            export_directory = os.path.join(temp_output_dir, "export")
        else:
            self.out_file = uri
            self.file_source_uri = None
            export_directory = temp_output_dir
        super().__init__(export_directory, **kwds)

    def _finalize(self) -> None:
        super()._finalize()
        ro_crate = self._init_crate()
        ro_crate.write(self.export_directory)
        out_file_name = str(self.out_file)
        if out_file_name.endswith(".zip"):
            out_file = out_file_name[: -len(".zip")]
        else:
            out_file = out_file_name
        rval = shutil.make_archive(out_file, "zip", self.export_directory)
        if not self.file_source_uri:
            shutil.move(rval, self.out_file)
        else:
            if not self.file_sources:
                raise Exception(f"Need self.file_sources but {type(self)} is missing it: {self.file_sources}.")
            file_source_path = self.file_sources.get_file_source_path(self.file_source_uri)
            file_source = file_source_path.file_source
            assert os.path.exists(rval), rval
            file_source.write_from(file_source_path.path, rval, user_context=self.user_context)
        shutil.rmtree(self.temp_output_dir)


class TarModelExportStore(DirectoryModelExportStore):
    file_source_uri: Optional[StrPath]
    out_file: StrPath

    def __init__(self, uri: StrPath, gzip: bool = True, **kwds) -> None:
        self.gzip = gzip
        temp_output_dir = tempfile.mkdtemp()
        self.temp_output_dir = temp_output_dir
        if "://" in str(uri):
            self.out_file = os.path.join(temp_output_dir, "out")
            self.file_source_uri = uri
            export_directory = os.path.join(temp_output_dir, "export")
        else:
            self.out_file = uri
            self.file_source_uri = None
            export_directory = temp_output_dir
        super().__init__(export_directory, **kwds)

    def _finalize(self) -> None:
        super()._finalize()
        tar_export_directory(self.export_directory, self.out_file, self.gzip)
        if self.file_source_uri:
            if not self.file_sources:
                raise Exception(f"Need self.file_sources but {type(self)} is missing it: {self.file_sources}.")
            file_source_path = self.file_sources.get_file_source_path(self.file_source_uri)
            file_source = file_source_path.file_source
            assert os.path.exists(self.out_file)
            file_source.write_from(file_source_path.path, self.out_file, user_context=self.user_context)
        shutil.rmtree(self.temp_output_dir)


class BagDirectoryModelExportStore(DirectoryModelExportStore):
    def __init__(self, out_directory: str, **kwds) -> None:
        self.out_directory = out_directory
        super().__init__(out_directory, **kwds)

    def _finalize(self) -> None:
        super()._finalize()
        bdb.make_bag(self.out_directory)


class BagArchiveModelExportStore(BagDirectoryModelExportStore):
    file_source_uri: Optional[StrPath]

    def __init__(self, uri: StrPath, bag_archiver: str = "tgz", **kwds) -> None:
        # bag_archiver in tgz, zip, tar
        self.bag_archiver = bag_archiver
        temp_output_dir = tempfile.mkdtemp()
        self.temp_output_dir = temp_output_dir
        if "://" in str(uri):
            # self.out_file = os.path.join(temp_output_dir, "out")
            self.file_source_uri = uri
            export_directory = os.path.join(temp_output_dir, "export")
        else:
            self.out_file = uri
            self.file_source_uri = None
            export_directory = temp_output_dir
        super().__init__(export_directory, **kwds)

    def _finalize(self) -> None:
        super()._finalize()
        rval = bdb.archive_bag(self.export_directory, self.bag_archiver)
        if not self.file_source_uri:
            shutil.move(rval, self.out_file)
        else:
            if not self.file_sources:
                raise Exception(f"Need self.file_sources but {type(self)} is missing it: {self.file_sources}.")
            file_source_path = self.file_sources.get_file_source_path(self.file_source_uri)
            file_source = file_source_path.file_source
            assert os.path.exists(rval)
            file_source.write_from(file_source_path.path, rval, user_context=self.user_context)
        shutil.rmtree(self.temp_output_dir)


def get_export_store_factory(
    app,
    download_format: str,
    export_files=None,
    bco_export_options: Optional[BcoExportOptions] = None,
    user_context=None,
) -> Callable[[StrPath], ModelExportStore]:
    export_store_class: Union[
        Type[TarModelExportStore],
        Type[BagArchiveModelExportStore],
        Type[ROCrateArchiveModelExportStore],
        Type[BcoModelExportStore],
    ]
    export_store_class_kwds = {
        "app": app,
        "export_files": export_files,
        "serialize_dataset_objects": False,
        "user_context": user_context,
    }
    if download_format in ["tar.gz", "tgz"]:
        export_store_class = TarModelExportStore
        export_store_class_kwds["gzip"] = True
    elif download_format in ["tar"]:
        export_store_class = TarModelExportStore
        export_store_class_kwds["gzip"] = False
    elif download_format == "rocrate.zip":
        export_store_class = ROCrateArchiveModelExportStore
    elif download_format == "bco.json":
        export_store_class = BcoModelExportStore
        export_store_class_kwds["export_options"] = bco_export_options
    elif download_format.startswith("bag."):
        bag_archiver = download_format[len("bag.") :]
        if bag_archiver not in ["zip", "tar", "tgz"]:
            raise RequestParameterInvalidException(f"Unknown download format [{download_format}]")
        export_store_class = BagArchiveModelExportStore
        export_store_class_kwds["bag_archiver"] = bag_archiver
    else:
        raise RequestParameterInvalidException(f"Unknown download format [{download_format}]")
    return lambda path: export_store_class(path, **export_store_class_kwds)


def tar_export_directory(export_directory: StrPath, out_file: StrPath, gzip: bool) -> None:
    tarfile_mode = "w"
    if gzip:
        tarfile_mode += ":gz"

    with tarfile.open(out_file, tarfile_mode, dereference=True) as store_archive:
        for export_path in os.listdir(export_directory):
            store_archive.add(os.path.join(export_directory, export_path), arcname=export_path)


def get_export_dataset_filename(name: str, ext: str, hid: int) -> str:
    """
    Builds a filename for a dataset using its name an extension.
    """
    base = "".join(c in FILENAME_VALID_CHARS and c or "_" for c in name)
    return f"{base}_{hid}.{ext}"


def imported_store_for_metadata(
    directory: str, object_store: Optional[ObjectStore] = None
) -> BaseDirectoryImportModelStore:
    import_options = ImportOptions(allow_dataset_object_edit=True, allow_edit=True)
    import_model_store = get_import_model_store_for_directory(
        directory, import_options=import_options, object_store=object_store
    )
    import_model_store.perform_import()
    return import_model_store


def source_to_import_store(
    source: Union[str, dict],
    app: StoreAppProtocol,
    import_options: Optional[ImportOptions],
    model_store_format: Optional[ModelStoreFormat] = None,
    user_context=None,
) -> ModelImportStore:
    galaxy_user = user_context.user if user_context else None
    if isinstance(source, dict):
        if model_store_format is not None:
            raise Exception(
                "Can only specify a model_store_format as an argument to source_to_import_store in conjuction with URIs"
            )
        model_import_store: ModelImportStore = get_import_model_store_for_dict(
            source,
            import_options=import_options,
            app=app,
            user=galaxy_user,
        )
    else:
        source_uri: str = str(source)
        delete = False
        tag_handler = app.tag_handler.create_tag_handler_session()
        if source_uri.startswith("file://"):
            source_uri = source_uri[len("file://") :]
        if "://" in source_uri:
            user_context = ProvidesUserFileSourcesUserContext(user_context)
            source_uri = stream_url_to_file(
                source_uri, app.file_sources, prefix="gx_import_model_store", user_context=user_context
            )
            delete = True
        target_path = source_uri
        if target_path.endswith(".json"):
            with open(target_path) as f:
                store_dict = load(f)
            assert isinstance(store_dict, dict)
            model_import_store = get_import_model_store_for_dict(
                store_dict,
                import_options=import_options,
                app=app,
                user=galaxy_user,
            )
        elif os.path.isdir(target_path):
            model_import_store = get_import_model_store_for_directory(
                target_path, import_options=import_options, app=app, user=galaxy_user, tag_handler=tag_handler
            )
        else:
            model_store_format = model_store_format or ModelStoreFormat.TGZ
            if ModelStoreFormat.is_compressed(model_store_format):
                try:
                    temp_dir = mkdtemp()
                    target_dir = CompressedFile(target_path).extract(temp_dir)
                finally:
                    if delete:
                        os.remove(target_path)
                model_import_store = get_import_model_store_for_directory(
                    target_dir, import_options=import_options, app=app, user=galaxy_user, tag_handler=tag_handler
                )
            elif ModelStoreFormat.is_bag(model_store_format):
                model_import_store = BagArchiveImportModelStore(
                    target_path, import_options=import_options, app=app, user=galaxy_user
                )
            else:
                # TODO: rocrate.zip is not supported here...
                raise Exception(f"Unknown model_store_format type encountered {model_store_format}")

    return model_import_store


def payload_to_source_uri(payload) -> str:
    if payload.store_content_uri:
        source_uri = payload.store_content_uri
    else:
        store_dict = payload.store_dict
        assert isinstance(store_dict, dict)
        temp_dir = mkdtemp()
        import_json = os.path.join(temp_dir, "import_store.json")
        with open(import_json, "w") as f:
            dump(store_dict, f)
        source_uri = f"file://{import_json}"
    return source_uri

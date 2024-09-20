import abc
import contextlib
import datetime
import os
import shutil
import tarfile
import tempfile
from collections import defaultdict
from json import (
    dump,
    dumps,
    load,
)
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Union,
)

from bdbag import bdbag_api as bdb
from boltons.iterutils import remap
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import expression

from galaxy.exceptions import MalformedContents, ObjectNotFound
from galaxy.model.metadata import MetadataCollection
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import FILENAME_VALID_CHARS
from galaxy.util import in_directory
from galaxy.util.bunch import Bunch
from galaxy.util.path import safe_walk
from ..custom_types import json_encoder
from ..item_attrs import add_item_annotation, get_item_annotation_str
from ... import model


ObjectKeyType = Union[str, int]

ATTRS_FILENAME_HISTORY = 'history_attrs.txt'
ATTRS_FILENAME_DATASETS = 'datasets_attrs.txt'
ATTRS_FILENAME_JOBS = 'jobs_attrs.txt'
ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS = 'implicit_collection_jobs_attrs.txt'
ATTRS_FILENAME_COLLECTIONS = 'collections_attrs.txt'
ATTRS_FILENAME_EXPORT = 'export_attrs.txt'
ATTRS_FILENAME_LIBRARIES = 'libraries_attrs.txt'
TRACEBACK = 'traceback.txt'
GALAXY_EXPORT_VERSION = "2"


class ImportOptions:

    def __init__(self, allow_edit=False, allow_library_creation=False, allow_dataset_object_edit=None):
        self.allow_edit = allow_edit
        self.allow_library_creation = allow_library_creation
        if allow_dataset_object_edit is None:
            allow_dataset_object_edit = allow_edit
        self.allow_dataset_object_edit = allow_dataset_object_edit


class SessionlessContext:

    def __init__(self):
        self.objects = defaultdict(dict)

    def flush(self):
        pass

    def add(self, obj):
        self.objects[obj.__class__][obj.id] = obj

    def query(self, model_class):

        def find(obj_id):
            return self.objects.get(model_class, {}).get(obj_id) or None

        def filter_by(*args, **kwargs):
            # TODO: Hack for history export archive, should support this too
            return Bunch(first=lambda: next(iter(self.objects.get(model_class, {None: None}))))

        return Bunch(find=find, get=find, filter_by=filter_by)


def replace_metadata_file(metadata: Dict[str, Any], dataset_instance: model.DatasetInstance):

    def remap_objects(p, k, obj):
        if isinstance(obj, dict) and "model_class" in obj and obj["model_class"] == "MetadataFile":
            return (k, model.MetadataFile(dataset=dataset_instance, uuid=obj["uuid"]))
        return (k, obj)

    return remap(metadata, remap_objects)


class ModelImportStore(metaclass=abc.ABCMeta):

    def __init__(self, import_options=None, app=None, user=None, object_store=None, tag_handler=None):
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
    def collections_properties(self) -> List[Dict[str, Any]]:
        """Return a list of HDCA properties."""

    @abc.abstractmethod
    def jobs_properties(self) -> List[Dict[str, Any]]:
        """Return a list of jobs properties."""

    @abc.abstractproperty
    def object_key(self) -> str:
        """Key used to connect objects in metadata.

        Legacy exports used 'hid' but associated objects may not be from the same history
        and a history may contain multiple objects with the same 'hid'.
        """

    @property
    def file_source_root(self) -> Optional[str]:
        """Source of valid file data."""
        return None

    def trust_hid(self, obj_attrs) -> bool:
        """Trust HID when importing objects into a new History."""

    @contextlib.contextmanager
    def target_history(self, default_history=None):
        new_history = None

        if self.defines_new_history():
            history_properties = self.new_history_properties()
            history_name = history_properties.get('name')
            if history_name:
                history_name = f'imported from archive: {history_name}'
            else:
                history_name = 'unnamed imported history'

            # Create history.
            new_history = model.History(name=history_name,
                                        user=self.user)
            new_history.importing = True
            hid_counter = history_properties.get('hid_counter')
            genome_build = history_properties.get('genome_build')

            # TODO: This seems like it shouldn't be imported, try to test and verify we can calculate this
            # and get away without it. -John
            if hid_counter:
                new_history.hid_counter = hid_counter
            if genome_build:
                new_history.genome_build = genome_build

            self._session_add(new_history)
            self._flush()

            if self.user:
                add_item_annotation(self.sa_session, self.user, new_history, history_properties.get('annotation'))

            history = new_history
        else:
            history = default_history

        yield history

        if new_history is not None:
            # Done importing.
            new_history.importing = False
            self._flush()

    def perform_import(self, history=None, new_history=False, job=None):
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
        self._flush()

    def _attach_dataset_hashes(self, dataset_or_file_attrs, dataset_instance):
        if "hashes" in dataset_or_file_attrs:
            for hash_attrs in dataset_or_file_attrs["hashes"]:
                hash_obj = model.DatasetHash()
                hash_obj.hash_value = hash_attrs["hash_value"]
                hash_obj.hash_function = hash_attrs["hash_function"]
                hash_obj.extra_files_path = hash_attrs["extra_files_path"]
                dataset_instance.dataset.hashes.append(hash_obj)

    def _attach_dataset_sources(self, dataset_or_file_attrs, dataset_instance):
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

    def _import_datasets(self, object_import_tracker, datasets_attrs, history, new_history, job):
        object_key = self.object_key

        for dataset_attrs in datasets_attrs:

            if 'state' not in dataset_attrs:
                self.dataset_state_serialized = False

            def handle_dataset_object_edit(dataset_instance):
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
                    if 'id' in dataset_attrs["dataset"] and self.import_options.allow_edit:
                        dataset_instance.dataset.id = dataset_attrs["dataset"]['id']
                    if job:
                        dataset_instance.dataset.job_id = job.id

            if 'id' in dataset_attrs and self.import_options.allow_edit and not self.sessionless:
                dataset_instance = self.sa_session.query(getattr(model, dataset_attrs['model_class'])).get(dataset_attrs["id"])
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
                        value = dataset_attrs.get(attribute)
                        if attribute == "metadata":
                            value = replace_metadata_file(value, dataset_instance)
                        setattr(dataset_instance, attribute, value)

                handle_dataset_object_edit(dataset_instance)
            else:
                metadata = dataset_attrs['metadata']

                model_class = dataset_attrs.get("model_class", "HistoryDatasetAssociation")
                dataset_instance: model.DatasetInstance
                if model_class == "HistoryDatasetAssociation":
                    # Create dataset and HDA.
                    dataset_instance = model.HistoryDatasetAssociation(name=dataset_attrs['name'],
                                                                       extension=dataset_attrs['extension'],
                                                                       info=dataset_attrs['info'],
                                                                       blurb=dataset_attrs['blurb'],
                                                                       peek=dataset_attrs['peek'],
                                                                       designation=dataset_attrs['designation'],
                                                                       visible=dataset_attrs['visible'],
                                                                       deleted=dataset_attrs.get('deleted', False),
                                                                       dbkey=metadata['dbkey'],
                                                                       tool_version=metadata.get('tool_version'),
                                                                       history=history,
                                                                       create_dataset=True,
                                                                       flush=False,
                                                                       sa_session=self.sa_session)
                    dataset_instance._metadata = metadata
                elif model_class == "LibraryDatasetDatasetAssociation":
                    # Create dataset and LDDA.
                    dataset_instance = model.LibraryDatasetDatasetAssociation(name=dataset_attrs['name'],
                                                                              extension=dataset_attrs['extension'],
                                                                              info=dataset_attrs['info'],
                                                                              blurb=dataset_attrs['blurb'],
                                                                              peek=dataset_attrs['peek'],
                                                                              designation=dataset_attrs['designation'],
                                                                              visible=dataset_attrs['visible'],
                                                                              deleted=dataset_attrs.get('deleted', False),
                                                                              dbkey=metadata['dbkey'],
                                                                              tool_version=metadata.get('tool_version'),
                                                                              user=self.user,
                                                                              create_dataset=True,
                                                                              flush=False,
                                                                              sa_session=self.sa_session)
                else:
                    raise Exception("Unknown dataset instance type encountered")
                if self.sessionless:
                    dataset_instance._metadata_collection = MetadataCollection(dataset_instance, session=self.sa_session)
                    metadata = replace_metadata_file(metadata, dataset_instance)
                dataset_instance._metadata = metadata
                self._attach_raw_id_if_editing(dataset_instance, dataset_attrs)

                # Older style...
                if self.import_options.allow_edit:
                    if 'uuid' in dataset_attrs:
                        dataset_instance.dataset.uuid = dataset_attrs["uuid"]
                    if 'dataset_uuid' in dataset_attrs:
                        dataset_instance.dataset.uuid = dataset_attrs["dataset_uuid"]

                self._session_add(dataset_instance)

                if model_class == "HistoryDatasetAssociation":
                    hda = cast(model.HistoryDatasetAssociation, dataset_instance)
                    # don't use add_history to manage HID handling across full import to try to preserve
                    # HID structure.
                    hda.history = history
                    if new_history and self.trust_hid(dataset_attrs):
                        hda.hid = dataset_attrs['hid']
                    else:
                        object_import_tracker.requires_hid.append(hda)

                file_source_root = self.file_source_root

                # If dataset is in the dictionary - we will assert this dataset is tied to the Galaxy instance
                # and the import options are configured for allowing editing the dataset (e.g. for metadata setting).
                # Otherwise, we will check for "file" information instead of dataset information - currently this includes
                # "file_name", "extra_files_path".
                if 'dataset' in dataset_attrs:
                    handle_dataset_object_edit(dataset_instance)
                else:
                    file_name = dataset_attrs.get('file_name')
                    if file_name:
                        assert file_source_root
                        # Do security check and move/copy dataset data.
                        archive_path = os.path.abspath(os.path.join(file_source_root, file_name))
                        if os.path.islink(archive_path):
                            raise MalformedContents(f"Invalid dataset path: {archive_path}")

                        temp_dataset_file_name = \
                            os.path.realpath(archive_path)

                        if not in_directory(temp_dataset_file_name, file_source_root):
                            raise MalformedContents(f"Invalid dataset path: {temp_dataset_file_name}")

                    if not file_name or not os.path.exists(temp_dataset_file_name):
                        dataset_instance.state = dataset_instance.states.DISCARDED
                        dataset_instance.deleted = True
                        dataset_instance.purged = True
                        dataset_instance.dataset.deleted = True
                        dataset_instance.dataset.purged = True
                    else:
                        dataset_instance.state = dataset_attrs.get('state', dataset_instance.states.OK)
                        self.object_store.update_from_file(dataset_instance.dataset, file_name=temp_dataset_file_name, create=True)

                        # Import additional files if present. Histories exported previously might not have this attribute set.
                        dataset_extra_files_path = dataset_attrs.get('extra_files_path', None)
                        if dataset_extra_files_path:
                            assert file_source_root
                            dir_name = dataset_instance.dataset.extra_files_path_name
                            dataset_extra_files_path = os.path.join(file_source_root, dataset_extra_files_path)
                            for root, _dirs, files in safe_walk(dataset_extra_files_path):
                                extra_dir = os.path.join(dir_name, root.replace(dataset_extra_files_path, '', 1).lstrip(os.path.sep))
                                extra_dir = os.path.normpath(extra_dir)
                                for extra_file in files:
                                    source = os.path.join(root, extra_file)
                                    if not in_directory(source, file_source_root):
                                        raise MalformedContents(f"Invalid dataset path: {source}")
                                    self.object_store.update_from_file(
                                        dataset_instance.dataset, extra_dir=extra_dir,
                                        alt_name=extra_file, file_name=source,
                                        create=True)
                        dataset_instance.dataset.set_total_size()  # update the filesize record in the database

                    if dataset_instance.deleted:
                        dataset_instance.dataset.deleted = True
                    file_metadata = dataset_attrs.get("file_metadata") or {}
                    self._attach_dataset_hashes(file_metadata, dataset_instance)
                    self._attach_dataset_sources(file_metadata, dataset_instance)
                    if "created_from_basename" in file_metadata:
                        dataset_instance.dataset.created_from_basename = file_metadata["created_from_basename"]

                if model_class == "HistoryDatasetAssociation" and self.user:
                    add_item_annotation(self.sa_session, self.user, dataset_instance, dataset_attrs['annotation'])
                    tag_list = dataset_attrs.get('tags')
                    if tag_list:
                        self.tag_handler.set_tags_from_list(user=self.user, item=dataset_instance, new_tags_list=tag_list, flush=False)

                if self.app:
                    self.app.datatypes_registry.set_external_metadata_tool.regenerate_imported_metadata_if_needed(
                        dataset_instance, history, job
                    )

                if model_class == "HistoryDatasetAssociation":
                    if object_key in dataset_attrs:
                        object_import_tracker.hdas_by_key[dataset_attrs[object_key]] = dataset_instance
                    else:
                        assert 'id' in dataset_attrs
                        object_import_tracker.hdas_by_id[dataset_attrs['id']] = dataset_instance
                else:
                    if object_key in dataset_attrs:
                        object_import_tracker.lddas_by_key[dataset_attrs[object_key]] = dataset_instance
                    else:
                        assert 'id' in dataset_attrs
                        object_import_tracker.lddas_by_key[dataset_attrs['id']] = dataset_instance

    def _import_libraries(self, object_import_tracker):
        object_key = self.object_key

        def import_folder(folder_attrs, root_folder=None):
            if root_folder:
                library_folder = root_folder
            else:
                name = folder_attrs['name']
                description = folder_attrs['description']
                genome_build = folder_attrs['genome_build']
                deleted = folder_attrs['deleted']
                library_folder = model.LibraryFolder(
                    name=name,
                    description=description,
                    genome_build=genome_build
                )
                library_folder.deleted = deleted

            self._session_add(library_folder)

            for sub_folder_attrs in folder_attrs.get("folders", []):
                sub_folder = import_folder(sub_folder_attrs)
                library_folder.add_folder(sub_folder)

            for ld_attrs in folder_attrs.get("datasets", []):
                ld = model.LibraryDataset(
                    folder=library_folder,
                    name=ld_attrs['name'],
                    info=ld_attrs['info'],
                    order_id=ld_attrs['order_id']
                )
                if 'ldda' in ld_attrs:
                    ldda = object_import_tracker.lddas_by_key[ld_attrs["ldda"][object_key]]
                    ld.library_dataset_dataset_association = ldda
                self._session_add(ld)

            self.sa_session.flush()
            return library_folder

        libraries_attrs = self.library_properties()
        for library_attrs in libraries_attrs:
            if library_attrs['model_class'] == 'LibraryFolder' and library_attrs.get('id') and not self.sessionless and self.import_options.allow_edit:
                library_folder = self.sa_session.query(model.LibraryFolder).get(self.app.security.decode_id(library_attrs['id']))
                import_folder(library_attrs, root_folder=library_folder)
            else:
                assert self.import_options.allow_library_creation
                name = library_attrs['name']
                description = library_attrs['description']
                synopsis = library_attrs['synopsis']
                library = model.Library(name=name, description=description, synopsis=synopsis)
                self._session_add(library)
                object_import_tracker.libraries_by_key[library_attrs[object_key]] = library

            if 'root_folder' in library_attrs:
                library.root_folder = import_folder(library_attrs['root_folder'])

    def _import_collection_instances(self, object_import_tracker, collections_attrs, history, new_history):
        object_key = self.object_key

        def import_collection(collection_attrs):
            def materialize_elements(dc):
                if "elements" not in collection_attrs:
                    return

                elements_attrs = collection_attrs['elements']
                for element_attrs in elements_attrs:
                    dce = model.DatasetCollectionElement(collection=dc,
                                                         element=model.DatasetCollectionElement.UNINITIALIZED_ELEMENT,
                                                         element_index=element_attrs['element_index'],
                                                         element_identifier=element_attrs['element_identifier'])
                    if 'encoded_id' in element_attrs:
                        object_import_tracker.dces_by_key[element_attrs['encoded_id']] = dce
                    if 'hda' in element_attrs:
                        hda_attrs = element_attrs['hda']
                        if object_key in hda_attrs:
                            hda_key = hda_attrs[object_key]
                            hdas_by_key = object_import_tracker.hdas_by_key
                            if hda_key in hdas_by_key:
                                hda = hdas_by_key[hda_key]
                            else:
                                raise KeyError(f"Failed to find exported hda with key [{hda_key}] of type [{object_key}] in [{hdas_by_key}]")
                        else:
                            hda_id = hda_attrs["id"]
                            hdas_by_id = object_import_tracker.hdas_by_id
                            if hda_id not in hdas_by_id:
                                raise Exception(f"Failed to find HDA with id [{hda_id}] in [{hdas_by_id}]")
                            hda = hdas_by_id[hda_id]
                        dce.hda = hda
                    elif 'child_collection' in element_attrs:
                        dce.child_collection = import_collection(element_attrs['child_collection'])
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
                dc = model.DatasetCollection(collection_type=collection_attrs['type'])
                dc.populated_state = collection_attrs["populated_state"]
                dc.populated_state_message = collection_attrs.get('populated_state_message')
                self._attach_raw_id_if_editing(dc, collection_attrs)
                materialize_elements(dc)

            self._session_add(dc)
            return dc

        for collection_attrs in collections_attrs:
            if 'collection' in collection_attrs:
                dc = import_collection(collection_attrs["collection"])
                if 'id' in collection_attrs and self.import_options.allow_edit and not self.sessionless:
                    hdca = self.sa_session.query(model.HistoryDatasetCollectionAssociation).get(collection_attrs["id"])
                    # TODO: edit attributes...
                else:
                    hdca = model.HistoryDatasetCollectionAssociation(collection=dc,
                                                                     visible=True,
                                                                     name=collection_attrs['display_name'],
                                                                     implicit_output_name=collection_attrs.get("implicit_output_name"))
                    self._attach_raw_id_if_editing(hdca, collection_attrs)

                    hdca.history = history
                    if new_history and self.trust_hid(collection_attrs):
                        hdca.hid = collection_attrs['hid']
                    else:
                        object_import_tracker.requires_hid.append(hdca)

                self._session_add(hdca)
                if object_key in collection_attrs:
                    object_import_tracker.hdcas_by_key[collection_attrs[object_key]] = hdca
                else:
                    assert 'id' in collection_attrs
                    object_import_tracker.hdcas_by_id[collection_attrs['id']] = hdca
            else:
                import_collection(collection_attrs)

    def _attach_raw_id_if_editing(self, obj, attrs):
        if self.sessionless and 'id' in attrs and self.import_options.allow_edit:
            obj.id = attrs['id']

    def _import_collection_implicit_input_associations(self, object_import_tracker, collections_attrs):
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

    def _import_dataset_copied_associations(self, object_import_tracker, datasets_attrs):
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
                    hda.copied_from_history_dataset_association = object_import_tracker.hdas_by_key[hda_copied_from_sinks[copied_from_object_key]]
                else:
                    hda_copied_from_sinks[copied_from_object_key] = dataset_key

    def _import_collection_copied_associations(self, object_import_tracker, collections_attrs):
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
                hdca.copied_from_history_dataset_collection_association = object_import_tracker.hdcas_by_key[copied_from_object_key]
            else:
                if copied_from_object_key in hdca_copied_from_sinks:
                    hdca.copied_from_history_dataset_association = object_import_tracker.hdcas_by_key[hdca_copied_from_sinks[copied_from_object_key]]
                else:
                    hdca_copied_from_sinks[copied_from_object_key] = dataset_collection_key

    def _reassign_hids(self, object_import_tracker, history):
        # assign HIDs for newly created objects that didn't match original history
        requires_hid = object_import_tracker.requires_hid
        requires_hid_len = len(requires_hid)
        if requires_hid_len > 0 and not self.sessionless:
            for obj in requires_hid:
                history.stage_addition(obj)
            history.add_pending_items()

    def _import_jobs(self, object_import_tracker, history):
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
        for job_attrs in jobs_attrs:
            if 'id' in job_attrs and not self.sessionless:
                # only thing we allow editing currently is associations for incoming jobs.
                assert self.import_options.allow_edit
                job = self.sa_session.query(model.Job).get(job_attrs["id"])
                self._connect_job_io(job, job_attrs, _find_hda, _find_hdca, _find_dce)
                self._set_job_attributes(job, job_attrs, force_terminal=False)
                # Don't edit job
                continue

            imported_job = model.Job()
            imported_job.id = job_attrs.get('id')
            imported_job.user = self.user
            imported_job.history = history
            imported_job.imported = True
            imported_job.tool_id = job_attrs['tool_id']
            imported_job.tool_version = job_attrs['tool_version']
            self._set_job_attributes(imported_job, job_attrs, force_terminal=True)

            try:
                imported_job.create_time = datetime.datetime.strptime(job_attrs["create_time"], "%Y-%m-%dT%H:%M:%S.%f")
                imported_job.update_time = datetime.datetime.strptime(job_attrs["update_time"], "%Y-%m-%dT%H:%M:%S.%f")
            except Exception:
                pass
            self._session_add(imported_job)

            # Connect jobs to input and output datasets.
            params = self._normalize_job_parameters(imported_job, job_attrs, _find_hda, _find_hdca, _find_dce)
            for name, value in params.items():
                # Transform parameter values when necessary.
                imported_job.add_parameter(name, dumps(value))

            self._connect_job_io(imported_job, job_attrs, _find_hda, _find_hdca, _find_dce)

            if object_key in job_attrs:
                object_import_tracker.jobs_by_key[job_attrs[object_key]] = imported_job

    def _import_implicit_collection_jobs(self, object_import_tracker):
        implicit_collection_jobs_attrs = self.implicit_collection_jobs_properties()
        for icj_attrs in implicit_collection_jobs_attrs:
            icj = model.ImplicitCollectionJobs()
            icj.populated_state = icj_attrs["populated_state"]

            icj.jobs = []
            for order_index, job in enumerate(icj_attrs["jobs"]):
                icja = model.ImplicitCollectionJobsJobAssociation()
                icja.implicit_collection_jobs = icj
                if job in object_import_tracker.jobs_by_key:
                    icja.job = object_import_tracker.jobs_by_key[job]
                icja.order_index = order_index
                icj.jobs.append(icja)
                self._session_add(icja)

            self._session_add(icj)

    def _session_add(self, obj):
        self.sa_session.add(obj)

    def _flush(self):
        self.sa_session.flush()


def _copied_from_object_key(copied_from_chain, objects_by_key):
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

    def __init__(self):
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
        self.requires_hid = []

    def find_hda(self, input_key: ObjectKeyType, hda_id: Optional[int] = None) -> Optional[model.HistoryDatasetAssociation]:
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

    def __init__(self, traceback, *args, **kwargs):
        self.traceback = traceback


def get_import_model_store_for_directory(archive_dir, **kwd):
    traceback_file = os.path.join(archive_dir, TRACEBACK)
    if not os.path.isdir(archive_dir):
        raise Exception(f"Could not find import model store for directory [{archive_dir}] (full path [{os.path.abspath(archive_dir)}])")
    if os.path.exists(os.path.join(archive_dir, ATTRS_FILENAME_EXPORT)):
        if os.path.exists(traceback_file):
            with open(traceback_file) as tb:
                raise FileTracebackException(traceback=tb.read())
        return DirectoryImportModelStoreLatest(archive_dir, **kwd)
    else:
        return DirectoryImportModelStore1901(archive_dir, **kwd)


class BaseDirectoryImportModelStore(ModelImportStore):

    @property
    def file_source_root(self):
        return self.archive_dir

    def defines_new_history(self):
        new_history_attributes = os.path.join(self.archive_dir, ATTRS_FILENAME_HISTORY)
        return os.path.exists(new_history_attributes)

    def new_history_properties(self):
        new_history_attributes = os.path.join(self.archive_dir, ATTRS_FILENAME_HISTORY)
        history_properties = load(open(new_history_attributes))
        return history_properties

    def datasets_properties(self):
        datasets_attrs_file_name = os.path.join(self.archive_dir, ATTRS_FILENAME_DATASETS)
        datasets_attrs = load(open(datasets_attrs_file_name))
        provenance_file_name = f"{datasets_attrs_file_name}.provenance"

        if os.path.exists(provenance_file_name):
            provenance_attrs = load(open(provenance_file_name))
            datasets_attrs += provenance_attrs

        return datasets_attrs

    def collections_properties(self):
        collections_attrs_file_name = os.path.join(self.archive_dir, ATTRS_FILENAME_COLLECTIONS)
        if os.path.exists(collections_attrs_file_name):
            collections_attrs = load(open(collections_attrs_file_name))
        else:
            collections_attrs = []
        return collections_attrs

    def library_properties(self):
        libraries_attrs_file_name = os.path.join(self.archive_dir, ATTRS_FILENAME_LIBRARIES)
        if os.path.exists(libraries_attrs_file_name):
            libraries_attrs = load(open(libraries_attrs_file_name))
        else:
            libraries_attrs = []
        return libraries_attrs

    def jobs_properties(self):
        jobs_attr_file_name = os.path.join(self.archive_dir, ATTRS_FILENAME_JOBS)
        try:
            return load(open(jobs_attr_file_name))
        except FileNotFoundError:
            return []

    def implicit_collection_jobs_properties(self):
        implicit_collection_jobs_attrs_file_name = os.path.join(self.archive_dir, ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS)
        try:
            return load(open(implicit_collection_jobs_attrs_file_name))
        except FileNotFoundError:
            return []

    def _set_job_attributes(self, imported_job, job_attrs, force_terminal=False):
        ATTRIBUTES = (
            'info',
            'exit_code',
            'traceback',
            'job_messages',
            'tool_stdout',
            'tool_stderr',
            'job_stdout',
            'job_stderr'
        )
        for attribute in ATTRIBUTES:
            value = job_attrs.get(attribute)
            if value is not None:
                setattr(imported_job, attribute, value)
        if 'stdout' in job_attrs:
            imported_job.tool_stdout = job_attrs.get('stdout')
            imported_job.tool_stderr = job_attrs.get('stderr')
        raw_state = job_attrs.get('state')
        if force_terminal and raw_state and raw_state not in model.Job.terminal_states:
            raw_state = model.Job.states.ERROR
        imported_job.set_state(raw_state)


class DirectoryImportModelStore1901(BaseDirectoryImportModelStore):
    object_key = 'hid'

    def __init__(self, archive_dir, **kwd):
        super().__init__(**kwd)
        archive_dir = os.path.realpath(archive_dir)

        # Bioblend previous to 17.01 exported histories with an extra subdir.
        if not os.path.exists(os.path.join(archive_dir, ATTRS_FILENAME_HISTORY)):
            for d in os.listdir(archive_dir):
                if os.path.isdir(os.path.join(archive_dir, d)):
                    archive_dir = os.path.join(archive_dir, d)
                    break

        self.archive_dir = archive_dir

    def _connect_job_io(self, imported_job, job_attrs, _find_hda, _find_hdca, _find_dce):
        for output_key in job_attrs['output_datasets']:
            output_hda = _find_hda(output_key)
            if output_hda:
                if not self.dataset_state_serialized:
                    # dataset state has not been serialized, get state from job
                    output_hda.state = imported_job.state
                imported_job.add_output_dataset(output_hda.name, output_hda)

        if 'input_mapping' in job_attrs:
            for input_name, input_key in job_attrs['input_mapping'].items():
                input_hda = _find_hda(input_key)
                if input_hda:
                    imported_job.add_input_dataset(input_name, input_hda)

    def _normalize_job_parameters(self, imported_job, job_attrs, _find_hda, _find_hdca, _find_dce):
        def remap_objects(p, k, obj):
            if isinstance(obj, dict) and obj.get('__HistoryDatasetAssociation__', False):
                imported_hda = _find_hda(obj[self.object_key])
                if imported_hda:
                    return (k, {"src": "hda", "id": imported_hda.id})
            return (k, obj)

        params = job_attrs['params']
        params = remap(params, remap_objects)
        return params

    def trust_hid(self, obj_attrs):
        # We didn't do object tracking so we pretty much have to trust the HID and accept
        # that it will be wrong a lot.
        return True


class DirectoryImportModelStoreLatest(BaseDirectoryImportModelStore):
    object_key = 'encoded_id'

    def __init__(self, archive_dir, **kwd):
        super().__init__(**kwd)
        archive_dir = os.path.realpath(archive_dir)
        self.archive_dir = archive_dir
        if self.defines_new_history():
            self.import_history_encoded_id = self.new_history_properties().get("encoded_id")
        else:
            self.import_history_encoded_id = None

    def _connect_job_io(self, imported_job, job_attrs, _find_hda, _find_hdca, _find_dce):
        if imported_job.command_line is None:
            imported_job.command_line = job_attrs.get('command_line')

        if 'input_dataset_mapping' in job_attrs:
            for input_name, input_keys in job_attrs['input_dataset_mapping'].items():
                input_keys = input_keys or []
                for input_key in input_keys:
                    input_hda = _find_hda(input_key)
                    if input_hda:
                        imported_job.add_input_dataset(input_name, input_hda)

        if 'input_dataset_collection_mapping' in job_attrs:
            for input_name, input_keys in job_attrs['input_dataset_collection_mapping'].items():
                input_keys = input_keys or []
                for input_key in input_keys:
                    input_hdca = _find_hdca(input_key)
                    if input_hdca:
                        imported_job.add_input_dataset_collection(input_name, input_hdca)

        if 'input_dataset_collection_element_mapping' in job_attrs:
            for input_name, input_keys in job_attrs['input_dataset_collection_element_mapping'].items():
                input_keys = input_keys or []
                for input_key in input_keys:
                    input_dce = _find_dce(input_key)
                    if input_dce:
                        imported_job.add_input_dataset_collection_element(input_name, input_dce)

        if 'output_dataset_mapping' in job_attrs:
            for output_name, output_keys in job_attrs['output_dataset_mapping'].items():
                output_keys = output_keys or []
                for output_key in output_keys:
                    output_hda = _find_hda(output_key)
                    if output_hda:
                        if not self.dataset_state_serialized:
                            # dataset state has not been serialized, get state from job
                            output_hda.state = imported_job.state
                        imported_job.add_output_dataset(output_name, output_hda)

        if 'output_dataset_collection_mapping' in job_attrs:
            for output_name, output_keys in job_attrs['output_dataset_collection_mapping'].items():
                output_keys = output_keys or []
                for output_key in output_keys:
                    output_hdca = _find_hdca(output_key)
                    if output_hdca:
                        imported_job.add_output_dataset_collection(output_name, output_hdca)

    def trust_hid(self, obj_attrs):
        return self.import_history_encoded_id and obj_attrs.get("history_encoded_id") == self.import_history_encoded_id

    def _normalize_job_parameters(self, imported_job, job_attrs, _find_hda, _find_hdca, _find_dce):
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

        params = job_attrs['params']
        params = remap(params, remap_objects)
        return params


class BagArchiveImportModelStore(DirectoryImportModelStoreLatest):

    def __init__(self, bag_archive, **kwd):
        archive_dir = tempfile.mkdtemp()
        bdb.extract_bag(bag_archive, output_path=archive_dir)
        # Why this line though...?
        archive_dir = os.path.join(archive_dir, os.listdir(archive_dir)[0])
        bdb.revert_bag(archive_dir)
        super().__init__(archive_dir, **kwd)


class ModelExportStore(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def export_history(self, history: model.History, include_hidden: bool = False, include_deleted: bool = False):
        """Export history to store."""

    @abc.abstractmethod
    def add_dataset_collection(self, collection: Union[model.DatasetCollection, model.HistoryDatasetCollectionAssociation]):
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

    def __init__(self, export_directory, app=None, for_edit=False, serialize_dataset_objects=None, export_files=None, strip_metadata_files=True, serialize_jobs=True):
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
        else:
            sessionless = True
            security = IdEncodingHelper(id_secret="randomdoesntmatter")

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
        self.included_datasets = {}
        self.included_collections = []
        self.included_libraries = []
        self.included_library_folders = []
        self.collection_datasets = {}
        self.collections_attrs = []
        self.dataset_id_to_path = {}

        self.job_output_dataset_associations = {}

    def serialize_files(self, dataset, as_dict):
        if self.export_files is None:
            return None
        elif self.export_files == "symlink":
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

        dir_name = 'datasets'
        dir_path = os.path.join(export_directory, dir_name)
        dataset_hid = as_dict['hid']
        assert dataset_hid, as_dict

        if dataset.dataset.id in self.dataset_id_to_path:
            file_name, extra_files_path = self.dataset_id_to_path[dataset.dataset.id]
            if file_name is not None:
                as_dict['file_name'] = file_name
            if extra_files_path is not None:
                as_dict['extra_files_path'] = extra_files_path
            return

        if file_name:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            target_filename = get_export_dataset_filename(as_dict['name'], as_dict['extension'], dataset_hid)
            arcname = os.path.join(dir_name, target_filename)

            src = file_name
            dest = os.path.join(export_directory, arcname)
            add(src, dest)
            as_dict['file_name'] = arcname

        if extra_files_path:
            try:
                file_list = os.listdir(extra_files_path)
            except OSError:
                file_list = []

            if len(file_list):
                arcname = os.path.join(dir_name, f'extra_files_path_{dataset_hid}')
                add(extra_files_path, os.path.join(export_directory, arcname))
                as_dict['extra_files_path'] = arcname
            else:
                as_dict['extra_files_path'] = ''

        self.dataset_id_to_path[dataset.dataset.id] = (as_dict.get("file_name"), as_dict.get("extra_files_path"))

    def exported_key(self, obj):
        return self.serialization_options.get_identifier(self.security, obj)

    def __enter__(self):
        return self

    def export_job(self, job: model.Job, tool=None, include_job_data=True):
        self.export_jobs([job], include_job_data=include_job_data)
        tool_source = getattr(tool, 'tool_source', None)
        if tool_source:
            with open(os.path.join(self.export_directory, 'tool.xml'), 'w') as out:
                out.write(tool_source.to_string())

    def export_jobs(self, jobs: List[model.Job], jobs_attrs=None, include_job_data=True):
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

                input_dataset_mapping: Dict[str, List[model.DatasetInstance]] = {}
                output_dataset_mapping: Dict[str, List[model.DatasetInstance]] = {}
                input_dataset_collection_mapping: Dict[str, List[model.DatasetCollectionInstance]] = {}
                input_dataset_collection_element_mapping: Dict[str, List[model.DatasetCollectionElement]] = {}
                output_dataset_collection_mapping: Dict[str, List[model.DatasetCollectionInstance]] = {}
                implicit_output_dataset_collection_mapping: Dict[str, List[model.DatasetCollection]] = {}

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

                        input_dataset_collection_element_mapping[name].append(self.exported_key(assoc.dataset_collection_element))
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

                        output_dataset_collection_mapping[name].append(self.exported_key(assoc.dataset_collection_instance))

                for assoc in job.output_dataset_collections:
                    if assoc.dataset_collection:
                        name = assoc.name

                        if name not in implicit_output_dataset_collection_mapping:
                            implicit_output_dataset_collection_mapping[name] = []

                        implicit_output_dataset_collection_mapping[name].append(self.exported_key(assoc.dataset_collection))
                        if include_job_data:
                            self.export_collection(assoc.dataset_collection)

                job_attrs['input_dataset_mapping'] = input_dataset_mapping
                job_attrs['input_dataset_collection_mapping'] = input_dataset_collection_mapping
                job_attrs['input_dataset_collection_element_mapping'] = input_dataset_collection_element_mapping
                job_attrs['output_dataset_mapping'] = output_dataset_mapping
                job_attrs['output_dataset_collection_mapping'] = output_dataset_collection_mapping
                job_attrs['implicit_output_dataset_collection_mapping'] = implicit_output_dataset_collection_mapping

            jobs_attrs.append(job_attrs)

        jobs_attrs_filename = os.path.join(self.export_directory, ATTRS_FILENAME_JOBS)
        with open(jobs_attrs_filename, 'w') as jobs_attrs_out:
            jobs_attrs_out.write(json_encoder.encode(jobs_attrs))
        return jobs_attrs

    def export_history(self, history, include_hidden=False, include_deleted=False):
        app = self.app
        export_directory = self.export_directory

        history_attrs = history.serialize(app.security, self.serialization_options)
        history_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_HISTORY)
        with open(history_attrs_filename, 'w') as history_attrs_out:
            dump(history_attrs, history_attrs_out)

        sa_session = app.model.session

        # Write collections' attributes (including datasets list) to file.
        query = (sa_session.query(model.HistoryDatasetCollectionAssociation)
                 .filter(model.HistoryDatasetCollectionAssociation.history == history)
                 .filter(model.HistoryDatasetCollectionAssociation.deleted == expression.false()))
        collections = query.all()

        for collection in collections:
            # filter this ?
            if not collection.populated:
                break
            if collection.state != 'ok':
                break

            self.add_dataset_collection(collection)

            # export jobs for these datasets
            for collection_dataset in collection.dataset_instances:
                if collection_dataset.deleted and not include_deleted:
                    include_files = False
                else:
                    include_files = True

                self.add_dataset(collection_dataset, include_files=include_files)
                self.collection_datasets[collection_dataset.id] = True

        # Write datasets' attributes to file.
        query = (sa_session.query(model.HistoryDatasetAssociation)
                 .filter(model.HistoryDatasetAssociation.history == history)
                 .join(model.Dataset)
                 .options(joinedload("dataset").joinedload("actions"))
                 .order_by(model.HistoryDatasetAssociation.hid)
                 .filter(model.Dataset.purged == expression.false()))
        datasets = query.all()
        for dataset in datasets:
            dataset.annotation = get_item_annotation_str(sa_session, history.user, dataset)
            add_dataset = (dataset.visible or include_hidden) and (not dataset.deleted or include_deleted)
            if dataset.id in self.collection_datasets:
                add_dataset = True

            if dataset not in self.included_datasets:
                self.add_dataset(dataset, include_files=add_dataset)

    def export_library(self, library, include_hidden=False, include_deleted=False):
        self.included_libraries.append(library)
        root_folder = getattr(library, 'root_folder', library)
        self.included_library_folders.append(root_folder)
        self.export_library_folder(root_folder, include_hidden=include_hidden, include_deleted=include_deleted)

    def export_library_folder(self, library_folder, include_hidden=False, include_deleted=False):
        for library_dataset in library_folder.datasets:
            ldda = library_dataset.library_dataset_dataset_association
            add_dataset = (not ldda.visible or not include_hidden) and (not ldda.deleted or include_deleted)
            self.add_dataset(ldda, add_dataset)
        for folder in library_folder.folders:
            self.export_library_folder(folder, include_hidden=include_hidden, include_deleted=include_deleted)

    def add_job_output_dataset_associations(self, job_id, name, dataset_instance):
        job_output_dataset_associations = self.job_output_dataset_associations
        if job_id not in job_output_dataset_associations:
            job_output_dataset_associations[job_id] = {}
        job_output_dataset_associations[job_id][name] = dataset_instance

    def export_collection(self, collection: Union[model.DatasetCollection, model.HistoryDatasetCollectionAssociation], include_deleted: bool = False):
        self.add_dataset_collection(collection)

        # export datasets for this collection
        has_collection = collection.collection if isinstance(collection, model.HistoryDatasetCollectionAssociation) else collection
        for collection_dataset in has_collection.dataset_instances:
            if collection_dataset.deleted and not include_deleted:
                include_files = False
            else:
                include_files = True

            self.add_dataset(collection_dataset, include_files=include_files)
            self.collection_datasets[collection_dataset.id] = True

    def add_dataset_collection(self, collection: Union[model.DatasetCollection, model.HistoryDatasetCollectionAssociation]):
        self.collections_attrs.append(collection)
        self.included_collections.append(collection)

    def add_dataset(self, dataset: model.DatasetInstance, include_files: bool = True):
        self.included_datasets[dataset] = (dataset, include_files)

    def _finalize(self):
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
        with open(datasets_attrs_filename, 'w') as datasets_attrs_out:
            datasets_attrs_out.write(to_json(datasets_attrs))

        with open(f"{datasets_attrs_filename}.provenance", 'w') as provenance_attrs_out:
            provenance_attrs_out.write(to_json(provenance_attrs))

        libraries_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_LIBRARIES)
        with open(libraries_attrs_filename, 'w') as libraries_attrs_out:
            libraries_attrs_out.write(to_json(self.included_libraries))

        collections_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_COLLECTIONS)
        with open(collections_attrs_filename, 'w') as collections_attrs_out:
            collections_attrs_out.write(to_json(self.collections_attrs))

        jobs_attrs = []
        for job_id, job_output_dataset_associations in self.job_output_dataset_associations.items():
            output_dataset_mapping = {}
            for name, dataset in job_output_dataset_associations.items():
                if name not in output_dataset_mapping:
                    output_dataset_mapping[name] = []
                output_dataset_mapping[name].append(self.exported_key(dataset))
            jobs_attrs.append({"id": job_id, 'output_dataset_mapping': output_dataset_mapping})

        if self.serialize_jobs:

            #
            # Write jobs attributes file.
            #

            # Get all jobs associated with included HDAs.
            jobs_dict = {}
            implicit_collection_jobs_dict = {}

            def record_associated_jobs(obj):
                # Get the job object.
                job = None
                for assoc in getattr(obj, 'creating_job_associations', []):
                    # For mapped over jobs obj could be DatasetCollection, which has no creating_job_association
                    job = assoc.job
                    break
                if not job:
                    # No viable job.
                    return

                jobs_dict[job.id] = job
                icja = job.implicit_collection_jobs_association
                if icja:
                    implicit_collection_jobs = icja.implicit_collection_jobs
                    implicit_collection_jobs_dict[implicit_collection_jobs.id] = implicit_collection_jobs

            for hda, _ in self.included_datasets.values():
                # Get the associated job, if any. If this hda was copied from another,
                # we need to find the job that created the original hda
                job_hda = hda
                while job_hda.copied_from_history_dataset_association:  # should this check library datasets as well?
                    job_hda = job_hda.copied_from_history_dataset_association
                if not job_hda.creating_job_associations:
                    # No viable HDA found.
                    continue

                record_associated_jobs(job_hda)

            for hdca in self.included_collections:
                record_associated_jobs(hdca)

            self.export_jobs(jobs_dict.values(), jobs_attrs=jobs_attrs)
            # Get jobs' attributes.

            icjs_attrs = []
            for icj in implicit_collection_jobs_dict.values():
                icj_attrs = icj.serialize(self.security, self.serialization_options)
                icjs_attrs.append(icj_attrs)

            icjs_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS)
            with open(icjs_attrs_filename, 'w') as icjs_attrs_out:
                icjs_attrs_out.write(json_encoder.encode(icjs_attrs))

        export_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_EXPORT)
        with open(export_attrs_filename, 'w') as export_attrs_out:
            dump({"galaxy_export_version": GALAXY_EXPORT_VERSION}, export_attrs_out)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._finalize()
        # http://effbot.org/zone/python-with-statement.htm
        # Ignores TypeError exceptions
        return isinstance(exc_val, TypeError)


class TarModelExportStore(DirectoryModelExportStore):

    def __init__(self, out_file, gzip=True, **kwds):
        self.gzip = gzip
        self.out_file = out_file
        temp_output_dir = tempfile.mkdtemp()
        super().__init__(temp_output_dir, **kwds)

    def _finalize(self):
        super()._finalize()
        tar_export_directory(self.export_directory, self.out_file, self.gzip)
        shutil.rmtree(self.export_directory)


class BagDirectoryModelExportStore(DirectoryModelExportStore):

    def __init__(self, out_directory, **kwds):
        self.out_directory = out_directory
        super().__init__(out_directory, **kwds)

    def _finalize(self):
        super()._finalize()
        bdb.make_bag(self.out_directory)


class BagArchiveModelExportStore(BagDirectoryModelExportStore):

    def __init__(self, out_file, bag_archiver="tgz", **kwds):
        # bag_archiver in tgz, zip, tar
        self.bag_archiver = bag_archiver
        self.out_file = out_file
        temp_output_dir = tempfile.mkdtemp()
        super().__init__(temp_output_dir, **kwds)

    def _finalize(self):
        super()._finalize()
        rval = bdb.archive_bag(self.export_directory, self.bag_archiver)
        shutil.move(rval, self.out_file)
        shutil.rmtree(self.export_directory)


def tar_export_directory(export_directory, out_file, gzip):
    tarfile_mode = "w"
    if gzip:
        tarfile_mode += ":gz"

    with tarfile.open(out_file, tarfile_mode, dereference=True) as history_archive:
        for export_path in os.listdir(export_directory):
            history_archive.add(os.path.join(export_directory, export_path), arcname=export_path)


def get_export_dataset_filename(name, ext, hid):
    """
    Builds a filename for a dataset using its name an extension.
    """
    base = ''.join(c in FILENAME_VALID_CHARS and c or '_' for c in name)
    return f"{base}_{hid}.{ext}"


def imported_store_for_metadata(directory, object_store=None):
    import_options = ImportOptions(allow_dataset_object_edit=True, allow_edit=True)
    import_model_store = get_import_model_store_for_directory(directory, import_options=import_options, object_store=object_store)
    import_model_store.perform_import()
    return import_model_store

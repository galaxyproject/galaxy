import abc
import contextlib
import datetime
import os
import shutil
import tarfile
import tempfile
from json import dump, dumps, load
from uuid import uuid4

import six
from bdbag import bdbag_api as bdb
from boltons.iterutils import remap
from sqlalchemy.orm import eagerload_all
from sqlalchemy.sql import expression

from galaxy.exceptions import MalformedContents, ObjectNotFound
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import FILENAME_VALID_CHARS
from galaxy.util import in_directory
from galaxy.util.bunch import Bunch
from galaxy.version import VERSION_MAJOR
from ..item_attrs import add_item_annotation, get_item_annotation_str
from ... import model

ATTRS_FILENAME_HISTORY = 'history_attrs.txt'
ATTRS_FILENAME_DATASETS = 'datasets_attrs.txt'
ATTRS_FILENAME_JOBS = 'jobs_attrs.txt'
ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS = 'implicit_collection_jobs_attrs.txt'
ATTRS_FILENAME_COLLECTIONS = 'collections_attrs.txt'
ATTRS_FILENAME_EXPORT = 'export_attrs.txt'
ATTRS_FILENAME_LIBRARIES = 'libraries_attrs.txt'


class ImportOptions(object):

    def __init__(self, allow_edit=False, allow_library_creation=False, allow_dataset_object_edit=None):
        self.allow_edit = allow_edit
        self.allow_library_creation = allow_library_creation
        if allow_dataset_object_edit is None:
            allow_dataset_object_edit = allow_edit
        self.allow_dataset_object_edit = allow_dataset_object_edit


class SessionlessContext(object):

    def __init__(self):
        self.objects = []

    def flush(self):
        pass

    def add(self, obj):
        self.objects.append(obj)

    def query(self, model_class):

        def find(obj_id):
            for obj in self.objects:
                if isinstance(obj, model_class) and obj.id == obj_id:
                    return obj
            return None

        return Bunch(find=find)


@six.add_metaclass(abc.ABCMeta)
class ModelImportStore(object):

    def __init__(self, import_options=None, app=None, user=None, object_store=None):
        if object_store is None:
            if app is not None:
                object_store = app.object_store
        self.object_store = object_store
        self.app = app
        if app is not None:
            self.sa_session = app.model.context.current
            self.sessionless = False
        else:
            self.sa_session = SessionlessContext()
            self.sessionless = True
        self.user = user
        self.import_options = import_options or ImportOptions()

    @abc.abstractmethod
    def defines_new_history(self):
        """Does this store define a new history to create."""

    @abc.abstractmethod
    def new_history_properties(self):
        """Dict of history properties if defines_new_history() is truthy."""

    @abc.abstractmethod
    def datasets_properties(self):
        """Return a list of HDA properties."""

    def library_properties(self):
        """Return a list of library properties."""
        return []

    @abc.abstractmethod
    def collections_properties(self):
        """Return a list of HDCA properties."""

    @abc.abstractmethod
    def jobs_properties(self):
        """Return a list of jobs properties."""

    @abc.abstractproperty
    def object_key(self):
        """Key used to connect objects in metadata.

        Legacy exports used 'hid' but associated objects may not be from the same history
        and a history may contain multiple objects with the same 'hid'.
        """

    @abc.abstractproperty
    def trust_hid(self, obj_attrs):
        """Trust HID when importing objects into a new History."""

    @contextlib.contextmanager
    def target_history(self, default_history=None):
        new_history = None

        if self.defines_new_history():
            history_properties = self.new_history_properties()
            history_name = history_properties.get('name')
            if history_name:
                history_name = 'imported from archive: %s' % history_name
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

    def _import_datasets(self, object_import_tracker, datasets_attrs, history, new_history, job):
        object_key = self.object_key

        for dataset_attrs in datasets_attrs:

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
                        "uuid"
                    ]

                    for attribute in dataset_attributes:
                        if attribute in dataset_attrs["dataset"]:
                            setattr(dataset_instance.dataset, attribute, dataset_attrs["dataset"][attribute])
                    if "hashes" in dataset_attrs["dataset"]:
                        for hash_attrs in dataset_attrs["dataset"]["hashes"]:
                            hash_obj = model.DatasetHash()
                            hash_obj.hash_value = hash_attrs["hash_value"]
                            hash_obj.hash_function = hash_attrs["hash_function"]
                            hash_obj.extra_files_path = hash_attrs["extra_files_path"]
                            dataset_instance.dataset.hashes.append(hash_obj)

                    if 'id' in dataset_attrs["dataset"] and self.import_options.allow_edit:
                        dataset_instance.dataset.id = dataset_attrs["dataset"]['id']

            if 'id' in dataset_attrs and self.import_options.allow_edit and not self.sessionless:
                hda = self.sa_session.query(model.HistoryDatasetAssociation).get(dataset_attrs["id"])
                attributes = [
                    "name",
                    "extension",
                    "info",
                    "blurb",
                    "peek",
                    "designation",
                    "visible",
                    "metadata",
                ]
                for attribute in attributes:
                    if attribute in dataset_attrs:
                        value = dataset_attrs[attribute]
                        if attribute == "metadata":
                            def remap_objects(p, k, obj):
                                if isinstance(obj, dict) and "model_class" in obj and obj["model_class"] == "MetadataFile":
                                    return (k, model.MetadataFile(dataset=hda, uuid=obj["uuid"]))
                                return (k, obj)

                            value = remap(value, remap_objects)

                        setattr(hda, attribute, value)

                handle_dataset_object_edit(hda)
                self._flush()
            else:
                metadata = dataset_attrs['metadata']

                model_class = dataset_attrs.get("model_class", "HistoryDatasetAssociation")
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
                                                                       metadata=metadata,
                                                                       history=history,
                                                                       create_dataset=True,
                                                                       flush=False,
                                                                       sa_session=self.sa_session)
                elif model_class == "LibraryDatasetDatasetAssociation":
                    # Create dataset and HDA.
                    dataset_instance = model.LibraryDatasetDatasetAssociation(name=dataset_attrs['name'],
                                                                              extension=dataset_attrs['extension'],
                                                                              info=dataset_attrs['info'],
                                                                              blurb=dataset_attrs['blurb'],
                                                                              peek=dataset_attrs['peek'],
                                                                              designation=dataset_attrs['designation'],
                                                                              visible=dataset_attrs['visible'],
                                                                              deleted=dataset_attrs.get('deleted', False),
                                                                              dbkey=metadata['dbkey'],
                                                                              metadata=metadata,
                                                                              create_dataset=True,
                                                                              sa_session=self.sa_session)
                else:
                    raise Exception("Unknown dataset instance type encountered")
                self._attach_raw_id_if_editing(dataset_instance, dataset_attrs)

                # Older style...
                if 'uuid' in dataset_attrs:
                    dataset_instance.dataset.uuid = dataset_attrs["uuid"]
                if 'dataset_uuid' in dataset_attrs:
                    dataset_instance.dataset.uuid = dataset_attrs["dataset_uuid"]

                self._session_add(dataset_instance)
                self._flush()

                if model_class == "HistoryDatasetAssociation":
                    # don't use add_history to manage HID handling across full import to try to preserve
                    # HID structure.
                    dataset_instance.history = history
                    if new_history and self.trust_hid(dataset_attrs):
                        dataset_instance.hid = dataset_attrs['hid']
                    else:
                        object_import_tracker.requires_hid.append(dataset_instance)

                self._flush()
                if 'dataset' in dataset_attrs:
                    handle_dataset_object_edit(dataset_instance)
                else:
                    file_name = dataset_attrs.get('file_name')
                    if file_name:
                        # Do security check and move/copy dataset data.
                        archive_path = os.path.abspath(os.path.join(self.archive_dir, file_name))
                        if os.path.islink(archive_path):
                            raise MalformedContents("Invalid dataset path: %s" % archive_path)

                        temp_dataset_file_name = \
                            os.path.realpath(archive_path)

                        if not in_directory(temp_dataset_file_name, self.archive_dir):
                            raise MalformedContents("Invalid dataset path: %s" % temp_dataset_file_name)

                    if not file_name or not os.path.exists(temp_dataset_file_name):
                        dataset_instance.state = dataset_instance.states.DISCARDED
                        dataset_instance.deleted = True
                        dataset_instance.purged = True
                        dataset_instance.dataset.deleted = True
                        dataset_instance.dataset.purged = True
                    else:
                        dataset_instance.state = dataset_instance.states.OK
                        self.object_store.update_from_file(dataset_instance.dataset, file_name=temp_dataset_file_name, create=True)

                        # Import additional files if present. Histories exported previously might not have this attribute set.
                        dataset_extra_files_path = dataset_attrs.get('extra_files_path', None)
                        if dataset_extra_files_path:
                            try:
                                file_list = os.listdir(os.path.join(self.archive_dir, dataset_extra_files_path))
                            except OSError:
                                file_list = []

                            if file_list:
                                for extra_file in file_list:
                                    self.object_store.update_from_file(
                                        dataset_instance.dataset, extra_dir='dataset_%s_files' % dataset_instance.dataset.id,
                                        alt_name=extra_file, file_name=os.path.join(self.archive_dir, dataset_extra_files_path, extra_file),
                                        create=True)
                        dataset_instance.dataset.set_total_size()  # update the filesize record in the database

                    if dataset_instance.deleted:
                        dataset_instance.dataset.deleted = True

                if model_class == "HistoryDatasetAssociation" and self.user:
                    add_item_annotation(self.sa_session, self.user, dataset_instance, dataset_attrs['annotation'])
                    tag_list = dataset_attrs.get('tags')
                    if tag_list:
                        tag_handler = model.tags.GalaxyTagHandler(sa_session=self.sa_session)
                        tag_handler.set_tags_from_list(user=self.user, item=dataset_instance, new_tags_list=tag_list)

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
                    object_import_tracker.lddas_by_key[dataset_attrs[object_key]] = dataset_instance

    def _import_libraries(self, object_import_tracker):
        object_key = self.object_key

        libraries_attrs = self.library_properties()
        for library_attrs in libraries_attrs:
            assert self.import_options.allow_library_creation
            name = library_attrs['name']
            description = library_attrs['description']
            synopsis = library_attrs['synopsis']
            library = model.Library(name=name, description=description, synopsis=synopsis)
            self._session_add(library)

            def import_folder(folder_attrs):
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
                self._flush()

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

                self._flush()

                return library_folder

            if 'root_folder' in library_attrs:
                library.root_folder = import_folder(library_attrs['root_folder'])

            object_import_tracker.libraries_by_key[library_attrs[object_key]] = library

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
                    if 'hda' in element_attrs:
                        hda_attrs = element_attrs['hda']
                        if object_key in hda_attrs:
                            hda_key = hda_attrs[object_key]
                            hdas_by_key = object_import_tracker.hdas_by_key
                            if hda_key in hdas_by_key:
                                hda = hdas_by_key[hda_key]
                            else:
                                raise KeyError("Failed to find exported hda with key [%s] of type [%s] in [%s]" % (hda_key, object_key, hdas_by_key))
                        else:
                            hda_id = hda_attrs["id"]
                            hdas_by_id = object_import_tracker.hdas_by_id
                            if hda_id not in hdas_by_id:
                                raise Exception("Failed to find HDA with id [%s] in [%s]" % (hda_id, hdas_by_id))
                            hda = hdas_by_id[hda_id]
                        dce.hda = hda
                    elif 'child_collection' in element_attrs:
                        dce.child_collection = import_collection(element_attrs['child_collection'])
                    else:
                        raise Exception("Unknown collection element type encountered.")

                    self._session_add(dce)

            if "id" in collection_attrs and self.import_options.allow_edit and not self.sessionless:
                dc = self.sa_session.query(model.DatasetCollection).get(collection_attrs["id"])
                attributes = [
                    "collection_type",
                    "populated_state",
                    "element_count",
                ]
                for attribute in attributes:
                    if attribute in collection_attrs:
                        setattr(dc, attribute, collection_attrs[attribute])
                materialize_elements(dc)
            else:
                # create collection
                dc = model.DatasetCollection(collection_type=collection_attrs['type'])
                dc.populated_state = collection_attrs["populated_state"]
                self._attach_raw_id_if_editing(dc, collection_attrs)
                # TODO: element_count...
                materialize_elements(dc)

            self._session_add(dc)
            return dc

        for collection_attrs in collections_attrs:
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
                # instance but I think it is find to pretend in order to create a DAG here.
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
            base = history._next_hid(n=requires_hid_len)
            for i, obj in enumerate(requires_hid):
                obj.hid = base + i
        self._flush()

    def _import_jobs(self, object_import_tracker, history):
        object_key = self.object_key

        def _find_hda(input_key):
            hda = None
            if input_key in object_import_tracker.hdas_by_key:
                hda = object_import_tracker.hdas_by_key[input_key]
            if input_key in object_import_tracker.hda_copied_from_sinks:
                hda = object_import_tracker.hdas_by_key[object_import_tracker.hda_copied_from_sinks[input_key]]
            return hda

        def _find_hdca(input_key):
            hdca = None
            if input_key in object_import_tracker.hdcas_by_key:
                hdca = object_import_tracker.hdcas_by_key[input_key]
            if input_key in object_import_tracker.hdca_copied_from_sinks:
                hdca = object_import_tracker.hdca_copied_from_sinks[input_key]
            return hdca

        #
        # Create jobs.
        #
        jobs_attrs = self.jobs_properties()
        # Create each job.
        for job_attrs in jobs_attrs:
            if 'id' in job_attrs:
                # only thing we allow editing currently is associations for incoming jobs.
                assert self.import_options.allow_edit
                assert not self.sessionless
                job = self.sa_session.query(model.Job).get(job_attrs["id"])
                self._connect_job_io(job, job_attrs, _find_hda, _find_hdca)
                self._flush()
                continue

            imported_job = model.Job()
            imported_job.user = self.user
            imported_job.history = history
            imported_job.imported = True
            imported_job.tool_id = job_attrs['tool_id']
            imported_job.tool_version = job_attrs['tool_version']
            raw_state = job_attrs['state']
            if raw_state not in model.Job.terminal_states:
                raw_state = model.Job.states.ERROR
            imported_job.set_state(raw_state)
            imported_job.info = job_attrs.get('info', None)
            imported_job.exit_code = job_attrs.get('exit_code', None)
            imported_job.traceback = job_attrs.get('traceback', None)
            if 'stdout' in job_attrs:
                # Pre 19.05 export.
                imported_job.tool_stdout = job_attrs.get('stdout', None)
                imported_job.tool_stderr = job_attrs.get('stderr', None)
            else:
                # Post 19.05 export with separated I/O
                imported_job.tool_stdout = job_attrs.get('tool_stdout', None)
                imported_job.job_stdout = job_attrs.get('job_stdout', None)
                imported_job.tool_stderr = job_attrs.get('tool_stderr', None)
                imported_job.job_stderr = job_attrs.get('job_stderr', None)

            imported_job.command_line = job_attrs.get('command_line', None)
            try:
                imported_job.create_time = datetime.datetime.strptime(job_attrs["create_time"], "%Y-%m-%dT%H:%M:%S.%f")
                imported_job.update_time = datetime.datetime.strptime(job_attrs["update_time"], "%Y-%m-%dT%H:%M:%S.%f")
            except Exception:
                pass
            self._session_add(imported_job)
            self._flush()

            # Connect jobs to input and output datasets.
            params = self._normalize_job_parameters(imported_job, job_attrs, _find_hda, _find_hdca)
            for name, value in params.items():
                # Transform parameter values when necessary.
                imported_job.add_parameter(name, dumps(value))

            self._connect_job_io(imported_job, job_attrs, _find_hda, _find_hdca)
            self._flush()

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
                icja.job = object_import_tracker.jobs_by_key[job]
                icja.order_index = order_index
                icj.jobs.append(icja)
                self._session_add(icja)

            self._session_add(icj)
            self._flush()

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


class ObjectImportTracker(object):
    """Keep track of new and existing imported objects.

    Needed to re-establish connections and such in multiple passes.
    """

    def __init__(self):
        self.libraries_by_key = {}
        self.hdas_by_key = {}
        self.hdas_by_id = {}
        self.hdcas_by_key = {}
        self.hdcas_by_id = {}
        self.lddas_by_key = {}
        self.hda_copied_from_sinks = {}
        self.hdca_copied_from_sinks = {}
        self.jobs_by_key = {}
        self.requires_hid = []


def get_import_model_store_for_directory(archive_dir, **kwd):
    assert os.path.isdir(archive_dir)
    if os.path.exists(os.path.join(archive_dir, ATTRS_FILENAME_EXPORT)):
        return DirectoryImportModelStoreLatest(archive_dir, **kwd)
    else:
        return DirectoryImportModelStore1901(archive_dir, **kwd)


class BaseDirectoryImportModelStore(ModelImportStore):

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
        provenance_file_name = datasets_attrs_file_name + ".provenance"

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
        jobs_attrs = load(open(jobs_attr_file_name))
        return jobs_attrs

    def implicit_collection_jobs_properties(self):
        implicit_collection_jobs_attrs_file_name = os.path.join(self.archive_dir, ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS)
        if os.path.exists(implicit_collection_jobs_attrs_file_name):
            implicit_collection_jobs_attrs = load(open(implicit_collection_jobs_attrs_file_name))
        else:
            implicit_collection_jobs_attrs = []
        return implicit_collection_jobs_attrs


class DirectoryImportModelStore1901(BaseDirectoryImportModelStore):
    object_key = 'hid'

    def __init__(self, archive_dir, **kwd):
        super(DirectoryImportModelStore1901, self).__init__(**kwd)
        archive_dir = os.path.realpath(archive_dir)

        # Bioblend previous to 17.01 exported histories with an extra subdir.
        if not os.path.exists(os.path.join(archive_dir, ATTRS_FILENAME_HISTORY)):
            for d in os.listdir(archive_dir):
                if os.path.isdir(os.path.join(archive_dir, d)):
                    archive_dir = os.path.join(archive_dir, d)
                    break

        self.archive_dir = archive_dir

    def _connect_job_io(self, imported_job, job_attrs, _find_hda, _find_hdca):
        for output_key in job_attrs['output_datasets']:
            output_hda = _find_hda(output_key)
            if output_hda:
                imported_job.add_output_dataset(output_hda.name, output_hda)

        if 'input_mapping' in job_attrs:
            for input_name, input_key in job_attrs['input_mapping'].items():
                input_hda = _find_hda(input_key)
                if input_hda:
                    imported_job.add_input_dataset(input_name, input_hda)

    def _normalize_job_parameters(self, imported_job, job_attrs, _find_hda, _find_hdca):
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
        super(DirectoryImportModelStoreLatest, self).__init__(**kwd)
        archive_dir = os.path.realpath(archive_dir)
        self.archive_dir = archive_dir
        if self.defines_new_history():
            self.import_history_encoded_id = self.new_history_properties().get("encoded_id")
        else:
            self.import_history_encoded_id = None

    def _connect_job_io(self, imported_job, job_attrs, _find_hda, _find_hdca):

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

        if 'output_dataset_mapping' in job_attrs:
            for output_name, output_keys in job_attrs['output_dataset_mapping'].items():
                output_keys = output_keys or []
                for output_key in output_keys:
                    output_hda = _find_hda(output_key)
                    if output_hda:
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

    def _normalize_job_parameters(self, imported_job, job_attrs, _find_hda, _find_hdca):
        def remap_objects(p, k, obj):
            if isinstance(obj, dict) and "src" in obj and obj["src"] in ["hda", "hdca"]:
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
                else:
                    raise NotImplementedError()
                new_obj = obj.copy()
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
        super(BagArchiveImportModelStore, self).__init__(archive_dir, **kwd)


@six.add_metaclass(abc.ABCMeta)
class ModelExportStore(object):

    @abc.abstractmethod
    def export_history(self, history, include_hidden=False, include_deleted=False):
        """Export history to store."""

    @abc.abstractmethod
    def add_dataset_collection(self, collection):
        """Add HDCA to export store."""

    @abc.abstractmethod
    def add_dataset(self, dataset, include_files=True):
        """Add HDA to export store."""

    @abc.abstractmethod
    def __enter__(self):
        """Export store should be used as context manager."""

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Export store should be used as context manager."""


class DirectoryModelExportStore(ModelExportStore):

    def __init__(self, export_directory, app=None, for_edit=False, serialize_dataset_objects=None, export_files=None, strip_metadata_files=True):
        """
        :param export_directory: path to export directory. Will be created if it does not exist.
        :param app: Galaxy App or app-like object. Must be provided if `for_edit` and/or `serialize_dataset_objects` are True
        :param for_edit: Allow modifying existing HDA and dataset metadata during import.
        :param serialize_dataset_objects: If True will encode IDs using the host secret. Defaults `for_edit`.
        :param export_files: How files should be exported, can be 'symlink', 'copy' or None, in which case files
                             will not be serialized.
        """
        if not os.path.exists(export_directory):
            os.makedirs(export_directory)

        if app is not None:
            self.app = app
            security = app.security
            sessionless = False
        else:
            sessionless = True
            security = IdEncodingHelper(id_secret="randomdoesntmatter")

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

        export_directory = self.export_directory

        _, include_files = self.included_datasets[dataset.id]
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
                arcname = os.path.join(dir_name, 'extra_files_path_%s' % dataset_hid)
                add(extra_files_path, os.path.join(export_directory, arcname))
                as_dict['extra_files_path'] = arcname
            else:
                as_dict['extra_files_path'] = ''

        self.dataset_id_to_path[dataset.dataset.id] = (as_dict.get("file_name"), as_dict.get("extra_files_path"))

    def exported_key(self, obj):
        return self.serialization_options.get_identifier(self.security, obj)

    def __enter__(self):
        return self

    def export_history(self, history, include_hidden=False, include_deleted=False):
        app = self.app
        export_directory = self.export_directory

        history_attrs = history.serialize(app.security, self.serialization_options)
        history_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_HISTORY)
        with open(history_attrs_filename, 'w') as history_attrs_out:
            dump(history_attrs, history_attrs_out)

        sa_session = app.model.context.current

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
                 .join("dataset")
                 .options(eagerload_all("dataset.actions"))
                 .order_by(model.HistoryDatasetAssociation.hid)
                 .filter(model.Dataset.purged == expression.false()))
        datasets = query.all()
        for dataset in datasets:
            dataset.annotation = get_item_annotation_str(sa_session, history.user, dataset)
            add_dataset = (not dataset.visible or not include_hidden) and (not dataset.deleted or include_deleted)
            if dataset.id in self.collection_datasets:
                add_dataset = True

            if dataset.id not in self.included_datasets:
                self.add_dataset(dataset, include_files=add_dataset)

    def export_library(self, library, include_hidden=False, include_deleted=False):
        self.included_libraries.append(library)
        self.included_library_folders.append(library.root_folder)

        def collect_datasets(library_folder):
            for library_dataset in library_folder.datasets:
                ldda = library_dataset.library_dataset_dataset_association
                add_dataset = (not ldda.visible or not include_hidden) and (not ldda.deleted or include_deleted)
                # TODO: competing IDs here between ldda and hdas - fix this!
                self.included_datasets[ldda.id] = (ldda, add_dataset)
            for folder in library_folder.folders:
                collect_datasets(folder)

        collect_datasets(library.root_folder)

    def add_job_output_dataset_associations(self, job_id, name, dataset_instance):
        job_output_dataset_associations = self.job_output_dataset_associations
        if job_id not in job_output_dataset_associations:
            job_output_dataset_associations[job_id] = {}
        job_output_dataset_associations[job_id][name] = dataset_instance

    def add_dataset_collection(self, collection):
        self.collections_attrs.append(collection)
        self.included_collections.append(collection)

    def add_dataset(self, dataset, include_files=True):
        dataset_id = dataset.id
        if dataset_id is None:
            # Better be a sessionless export, just assign a random ID
            # won't be able to de-duplicate datasets. This could be fixed
            # by using object identity or attaching something to the object
            # like temp_id used in serialization.
            assert self.sessionless
            dataset_id = uuid4().hex

        self.included_datasets[dataset_id] = (dataset, include_files)

    def _finalize(self):
        export_directory = self.export_directory

        datasets_attrs = []
        provenance_attrs = []
        for dataset_id, (dataset, include_files) in self.included_datasets.items():
            if include_files:
                datasets_attrs.append(dataset)
            else:
                provenance_attrs.append(dataset)

        datasets_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_DATASETS)
        with open(datasets_attrs_filename, 'w') as datasets_attrs_out:
            dump(list(map(lambda d: d.serialize(self.security, self.serialization_options), datasets_attrs)), datasets_attrs_out)

        with open(datasets_attrs_filename + ".provenance", 'w') as provenance_attrs_out:
            dump(list(map(lambda d: d.serialize(self.security, self.serialization_options), provenance_attrs)), provenance_attrs_out)

        libraries_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_LIBRARIES)
        with open(libraries_attrs_filename, 'w') as librariess_attrs_out:
            dump(list(map(lambda d: d.serialize(self.security, self.serialization_options), self.included_libraries)), librariess_attrs_out)

        collections_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_COLLECTIONS)
        with open(collections_attrs_filename, 'w') as collections_attrs_out:
            dump(list(map(lambda d: d.serialize(self.security, self.serialization_options), self.collections_attrs)), collections_attrs_out)

        #
        # Write jobs attributes file.
        #

        # Get all jobs associated with included HDAs.
        jobs_dict = {}
        implicit_collection_jobs_dict = {}

        def record_associated_jobs(obj):
            # Get the job object.
            job = None
            for assoc in obj.creating_job_associations:
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

        for hda_id, (hda, include_files) in self.included_datasets.items():
            # Get the associated job, if any. If this hda was copied from another,
            # we need to find the job that created the origial hda
            job_hda = hda
            while job_hda.copied_from_history_dataset_association:  # should this check library datasets as well?
                job_hda = job_hda.copied_from_history_dataset_association
            if not job_hda.creating_job_associations:
                # No viable HDA found.
                continue

            record_associated_jobs(job_hda)

        for hdca in self.included_collections:
            record_associated_jobs(hdca)

        # Get jobs' attributes.
        jobs_attrs = []
        for id, job in jobs_dict.items():
            # Don't attempt to serialize jobs for editing... yet at least.
            if self.serialization_options.for_edit:
                continue

            job_attrs = job.serialize(self.security, self.serialization_options)

            # -- Get input, output datasets. --

            input_dataset_mapping = {}
            output_dataset_mapping = {}
            input_dataset_collection_mapping = {}
            output_dataset_collection_mapping = {}
            implicit_output_dataset_collection_mapping = {}

            for assoc in job.input_datasets:
                # Optional data inputs will not have a dataset.
                if assoc.dataset:
                    name = assoc.name
                    if name not in input_dataset_mapping:
                        input_dataset_mapping[name] = []

                    input_dataset_mapping[name].append(self.exported_key(assoc.dataset))

            for assoc in job.output_datasets:
                # Optional data inputs will not have a dataset.
                if assoc.dataset:
                    name = assoc.name
                    if name not in output_dataset_mapping:
                        output_dataset_mapping[name] = []

                    output_dataset_mapping[name].append(self.exported_key(assoc.dataset))

            for assoc in job.input_dataset_collections:
                # Optional data inputs will not have a dataset.
                if assoc.dataset_collection:
                    name = assoc.name
                    if name not in input_dataset_collection_mapping:
                        input_dataset_collection_mapping[name] = []

                    input_dataset_collection_mapping[name].append(self.exported_key(assoc.dataset_collection))

            for assoc in job.output_dataset_collection_instances:
                # Optional data outputs will not have a dataset.
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

            job_attrs['input_dataset_mapping'] = input_dataset_mapping
            job_attrs['input_dataset_collection_mapping'] = input_dataset_collection_mapping
            job_attrs['output_dataset_mapping'] = output_dataset_mapping
            job_attrs['output_dataset_collection_mapping'] = output_dataset_collection_mapping
            job_attrs['implicit_output_dataset_collection_mapping'] = implicit_output_dataset_collection_mapping

            jobs_attrs.append(job_attrs)

        for job_id, job_output_dataset_associations in self.job_output_dataset_associations.items():
            output_dataset_mapping = {}
            for name, dataset in job_output_dataset_associations.items():
                if name not in output_dataset_mapping:
                    output_dataset_mapping[name] = []
                output_dataset_mapping[name].append(self.exported_key(dataset))
            jobs_attrs.append({"id": job_id, 'output_dataset_mapping': output_dataset_mapping})

        icjs_attrs = []
        for icj_id, icj in implicit_collection_jobs_dict.items():
            icj_attrs = icj.serialize(self.security, self.serialization_options)
            icjs_attrs.append(icj_attrs)

        jobs_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_JOBS)
        with open(jobs_attrs_filename, 'w') as jobs_attrs_out:
            dump(jobs_attrs, jobs_attrs_out)

        icjs_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS)
        with open(icjs_attrs_filename, 'w') as icjs_attrs_out:
            dump(icjs_attrs, icjs_attrs_out)

        export_attrs_filename = os.path.join(export_directory, ATTRS_FILENAME_EXPORT)
        with open(export_attrs_filename, 'w') as export_attrs_out:
            dump({"galaxy_version": VERSION_MAJOR}, export_attrs_out)

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
        super(TarModelExportStore, self).__init__(temp_output_dir, **kwds)

    def _finalize(self):
        super(TarModelExportStore, self)._finalize()
        tar_export_directory(self.export_directory, self.out_file, self.gzip)
        shutil.rmtree(self.export_directory)


class BagDirectoryModelExportStore(DirectoryModelExportStore):

    def __init__(self, out_directory, **kwds):
        self.out_directory = out_directory
        super(BagDirectoryModelExportStore, self).__init__(out_directory, **kwds)

    def _finalize(self):
        super(BagDirectoryModelExportStore, self)._finalize()
        bdb.make_bag(self.out_directory)


class BagArchiveModelExportStore(BagDirectoryModelExportStore):

    def __init__(self, out_file, bag_archiver="tgz", **kwds):
        # bag_archiver in tgz, zip, tar
        self.bag_archiver = bag_archiver
        self.out_file = out_file
        temp_output_dir = tempfile.mkdtemp()
        super(BagArchiveModelExportStore, self).__init__(temp_output_dir, **kwds)

    def _finalize(self):
        super(BagArchiveModelExportStore, self)._finalize()
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
    return base + "_%s.%s" % (hid, ext)

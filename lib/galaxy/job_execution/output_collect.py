""" Code allowing tools to define extra files associated with an output datset.
"""

import logging
import operator
import os
import re
from tempfile import NamedTemporaryFile
from typing import (
    Callable,
    Dict,
    List,
    Optional,
    Union,
)

from sqlalchemy.orm.scoping import ScopedSession

from galaxy.model import (
    DatasetInstance,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    Job,
    JobToOutputDatasetAssociation,
    LibraryDatasetDatasetAssociation,
)
from galaxy.model.dataset_collections import builder
from galaxy.model.dataset_collections.structure import UninitializedTree
from galaxy.model.dataset_collections.type_description import COLLECTION_TYPE_DESCRIPTION_FACTORY
from galaxy.model.store.discover import (
    discover_target_directory,
    DiscoveredFile,
    JsonCollectedDatasetMatch,
    MetadataSourceProvider as AbstractMetadataSourceProvider,
    ModelPersistenceContext,
    PermissionProvider as AbstractPermissionProvider,
    persist_elements_to_folder,
    persist_elements_to_hdca,
    persist_hdas,
    RegexCollectedDatasetMatch,
    SessionlessModelPersistenceContext,
    UNSET,
)
from galaxy.objectstore import (
    ObjectStore,
    persist_extra_files,
)
from galaxy.tool_util.parser.output_collection_def import (
    DEFAULT_DATASET_COLLECTOR_DESCRIPTION,
    INPUT_DBKEY_TOKEN,
    ToolProvidedMetadataDatasetCollection,
)
from galaxy.tool_util.parser.output_objects import (
    ToolOutput,
    ToolOutputCollection,
)
from galaxy.tool_util.provided_metadata import BaseToolProvidedMetadata
from galaxy.util import (
    shrink_and_unicodify,
    unicodify,
)

DATASET_ID_TOKEN = "DATASET_ID"

log = logging.getLogger(__name__)


# PermissionProvider and MetadataSourceProvider are abstractions over input data used to
# collect and produce dynamic outputs.
class PermissionProvider(AbstractPermissionProvider):
    def __init__(self, inp_data, security_agent, job):
        self._job = job
        self._security_agent = security_agent
        self._inp_data = inp_data
        self._user = job.user
        self._permissions = None

    @property
    def permissions(self):
        if self._permissions is None:
            inp_data = self._inp_data
            existing_datasets = [inp for inp in inp_data.values() if inp]
            if existing_datasets:
                permissions = self._security_agent.guess_derived_permissions_for_datasets(existing_datasets)
            else:
                # No valid inputs, we will use history defaults
                permissions = self._security_agent.history_get_default_permissions(self._job.history)
            self._permissions = permissions

        return self._permissions

    def set_default_hda_permissions(self, primary_data):
        if (permissions := self.permissions) is not UNSET:
            self._security_agent.set_all_dataset_permissions(primary_data.dataset, permissions, new=True, flush=False)

    def copy_dataset_permissions(self, init_from, primary_data):
        self._security_agent.copy_dataset_permissions(init_from.dataset, primary_data.dataset, flush=False)


class MetadataSourceProvider(AbstractMetadataSourceProvider):
    def __init__(self, inp_data):
        self._inp_data = inp_data

    def get_metadata_source(self, input_name):
        return self._inp_data[input_name]


def collect_dynamic_outputs(
    job_context,
    output_collections,
):
    # unmapped outputs do not correspond to explicit outputs of the tool, they were inferred entirely
    # from the tool provided metadata (e.g. galaxy.json).
    for unnamed_output_dict in job_context.tool_provided_metadata.get_unnamed_outputs():
        assert "destination" in unnamed_output_dict
        assert "elements" in unnamed_output_dict
        destination = unnamed_output_dict["destination"]
        elements = unnamed_output_dict["elements"]

        assert "type" in destination
        destination_type = destination["type"]
        assert destination_type in ["library_folder", "hdca", "hdas"]

        # three destination types we need to handle here - "library_folder" (place discovered files in a library folder),
        # "hdca" (place discovered files in a history dataset collection), and "hdas" (place discovered files in a history
        # as stand-alone datasets).
        if destination_type == "library_folder":
            # populate a library folder (needs to have already been created)
            library_folder = job_context.get_library_folder(destination)
            persist_elements_to_folder(job_context, elements, library_folder)
            job_context.persist_library_folder(library_folder)
        elif destination_type == "hdca":
            # create or populate a dataset collection in the history
            assert "collection_type" in unnamed_output_dict
            object_id = destination.get("object_id")
            if object_id:
                hdca = job_context.get_hdca(object_id)
            else:
                name = unnamed_output_dict.get("name", "unnamed collection")
                collection_type = unnamed_output_dict["collection_type"]
                collection_type_description = COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(collection_type)
                structure = UninitializedTree(collection_type_description)
                hdca = job_context.create_hdca(name, structure)
                output_collections[name] = hdca
                job_context.add_dataset_collection(hdca)
            error_message = unnamed_output_dict.get("error_message")
            if error_message:
                hdca.collection.handle_population_failed(error_message)
            else:
                persist_elements_to_hdca(job_context, elements, hdca, collector=DEFAULT_DATASET_COLLECTOR)
        elif destination_type == "hdas":
            persist_hdas(elements, job_context, final_job_state=job_context.final_job_state)

    for name, has_collection in output_collections.items():
        output_collection_def = job_context.output_collection_def(name)
        if not output_collection_def:
            continue

        if not output_collection_def.dynamic_structure:
            continue

        # Could be HDCA for normal jobs or a DC for mapping
        # jobs.
        if hasattr(has_collection, "collection"):
            collection = has_collection.collection
        else:
            collection = has_collection

        # We are adding dynamic collections, which may be precreated, but their actually state is still new!
        collection.populated_state = collection.populated_states.NEW

        try:
            collection_builder = builder.BoundCollectionBuilder(collection)
            dataset_collectors = [
                dataset_collector(description) for description in output_collection_def.dataset_collector_descriptions
            ]
            output_name = output_collection_def.name
            filenames = job_context.find_files(output_name, collection, dataset_collectors)
            job_context.populate_collection_elements(
                collection,
                collection_builder,
                filenames,
                name=output_collection_def.name,
                metadata_source_name=output_collection_def.metadata_source,
                final_job_state=job_context.final_job_state,
                change_datatype_actions=job_context.change_datatype_actions,
            )
            collection_builder.populate()
        except Exception:
            log.exception("Problem gathering output collection.")
            collection.handle_population_failed("Problem building datasets for collection.")

        job_context.add_dataset_collection(has_collection)


class BaseJobContext(ModelPersistenceContext):
    max_discovered_files: Union[int, float]
    tool_provided_metadata: BaseToolProvidedMetadata
    job_working_directory: str

    def add_dataset_collection(self, collection):
        pass

    def find_files(self, output_name, collection, dataset_collectors) -> list:
        discovered_files = []
        for discovered_file in discover_files(
            output_name, self.tool_provided_metadata, dataset_collectors, self.job_working_directory, collection
        ):
            self.increment_discovered_file_count()
            discovered_files.append(discovered_file)
        return discovered_files

    def get_job_id(self):
        return None  # overwritten in subclasses


class JobContext(BaseJobContext):
    def __init__(
        self,
        tool,
        tool_provided_metadata: BaseToolProvidedMetadata,
        job,
        job_working_directory,
        permission_provider,
        metadata_source_provider,
        input_dbkey,
        object_store,
        final_job_state,
        max_discovered_files: Optional[int],
        flush_per_n_datasets=None,
    ):
        self.tool = tool
        self._metadata_source_provider = metadata_source_provider
        self._permission_provider = permission_provider
        self._input_dbkey = input_dbkey
        self.app = tool.app
        self._sa_session = tool.sa_session
        self._job = job
        self.job_working_directory = job_working_directory
        self.tool_provided_metadata = tool_provided_metadata
        self._object_store = object_store
        self.final_job_state = final_job_state
        self._flush_per_n_datasets = flush_per_n_datasets
        self.max_discovered_files = float("inf") if max_discovered_files is None else max_discovered_files
        self.discovered_file_count = 0
        self._tag_handler = None

    @property
    def change_datatype_actions(self):
        return self.job.get_change_datatype_actions()

    @property
    def tag_handler(self):
        if self._tag_handler is None:
            self._tag_handler = self.app.tag_handler.create_tag_handler_session(self.job.galaxy_session)
        return self._tag_handler

    @property
    def work_context(self):
        from galaxy.work.context import WorkRequestContext

        return WorkRequestContext(self.app, user=self.user, galaxy_session=self.job.galaxy_session)

    @property
    def sa_session(self) -> ScopedSession:
        return self._sa_session

    @property
    def permission_provider(self) -> PermissionProvider:
        return self._permission_provider

    @property
    def metadata_source_provider(self) -> MetadataSourceProvider:
        return self._metadata_source_provider

    @property
    def job(self) -> Job:
        return self._job

    @property
    def flush_per_n_datasets(self) -> Optional[int]:
        return self._flush_per_n_datasets

    @property
    def input_dbkey(self) -> str:
        return self._input_dbkey

    @property
    def object_store(self) -> ObjectStore:
        return self._object_store

    @property
    def user(self):
        if self.job:
            user = self.job.user
        else:
            user = None
        return user

    def persist_object(self, obj):
        self.sa_session.add(obj)

    def flush(self):
        self.sa_session.commit()

    def get_library_folder(self, destination):
        app = self.app
        library_folder_manager = app.library_folder_manager
        folder_id = destination.get("library_folder_id")
        decoded_folder_id = app.security.decode_id(folder_id) if isinstance(folder_id, str) else folder_id
        library_folder = library_folder_manager.get(self.work_context, decoded_folder_id)
        return library_folder

    def get_hdca(self, object_id):
        hdca = self.sa_session.query(HistoryDatasetCollectionAssociation).get(int(object_id))
        return hdca

    def create_library_folder(self, parent_folder, name, description):
        assert parent_folder.id
        library_folder_manager = self.app.library_folder_manager
        nested_folder = library_folder_manager.create(self.work_context, parent_folder.id, name, description)
        return nested_folder

    def create_hdca(self, name, structure):
        history = self.job.history
        trans = self.work_context
        collection_manager = self.app.dataset_collection_manager
        hdca = collection_manager.precreate_dataset_collection_instance(trans, history, name, structure=structure)
        return hdca

    def add_output_dataset_association(self, name, dataset):
        assoc = JobToOutputDatasetAssociation(name, dataset)
        assoc.job = self.job
        self.sa_session.add(assoc)

    def add_library_dataset_to_folder(self, library_folder, ld):
        trans = self.work_context
        ldda = ld.library_dataset_dataset_association
        trans.sa_session.add(ldda)

        trans = self.work_context
        trans.app.security_agent.copy_library_permissions(trans, library_folder, ld)
        trans.sa_session.add(ld)
        trans.sa_session.commit()

        # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
        trans.app.security_agent.copy_library_permissions(trans, ld, ldda)
        # Copy the current user's DefaultUserPermissions to the new LibraryDatasetDatasetAssociation.dataset
        trans.app.security_agent.set_all_dataset_permissions(
            ldda.dataset, trans.app.security_agent.user_get_default_permissions(trans.user), flush=False, new=True
        )
        library_folder.add_library_dataset(ld, genome_build=ldda.dbkey)
        trans.sa_session.add(library_folder)
        trans.sa_session.commit()

        trans.sa_session.add(ld)
        trans.sa_session.commit()

    def add_datasets_to_history(self, datasets, for_output_dataset=None):
        sa_session = self.sa_session
        self.job.history.stage_addition(datasets)
        pending_histories = {self.job.history}
        if for_output_dataset is not None:
            # Need to update all associated output hdas, i.e. history was
            # shared with job running
            for copied_dataset in for_output_dataset.dataset.history_associations:
                if copied_dataset == for_output_dataset:
                    continue
                for dataset in datasets:
                    new_data = dataset.copy()
                    copied_dataset.history.stage_addition(new_data)
                    pending_histories.add(copied_dataset.history)
                    sa_session.add(new_data)
        for history in pending_histories:
            history.add_pending_items()

    def output_collection_def(self, name):
        tool = self.tool
        if name not in tool.output_collections:
            return None
        output_collection_def = tool.output_collections[name]
        return output_collection_def

    def output_def(self, name):
        tool = self.tool
        if name not in tool.outputs:
            return None
        output_collection_def = tool.outputs[name]
        return output_collection_def

    def job_id(self):
        return self.job.id

    def get_job_id(self):
        return self.job.id

    def get_implicit_collection_jobs_association_id(self):
        return self.job.implicit_collection_jobs_association and self.job.implicit_collection_jobs_association.id


class SessionlessJobContext(SessionlessModelPersistenceContext, BaseJobContext):
    def __init__(
        self,
        metadata_params,
        tool_provided_metadata: BaseToolProvidedMetadata,
        object_store,
        export_store,
        import_store,
        working_directory,
        final_job_state,
        max_discovered_files: Optional[int],
    ):
        # TODO: use a metadata source provider... (pop from inputs and add parameter)
        super().__init__(object_store, export_store, working_directory)
        self.metadata_params = metadata_params
        self.tool_provided_metadata = tool_provided_metadata
        self.import_store = import_store
        self.final_job_state = final_job_state
        self.max_discovered_files = float("inf") if max_discovered_files is None else max_discovered_files
        self.discovered_file_count = 0

    @property
    def change_datatype_actions(self):
        return self.metadata_params.get("change_datatype_actions", {})

    def output_collection_def(self, name):
        tool_as_dict = self.metadata_params["tool"]
        output_collection_defs = tool_as_dict["output_collections"]
        if name not in output_collection_defs:
            return False

        output_collection_def_dict = output_collection_defs[name]
        output_collection_def = ToolOutputCollection.from_dict(name, output_collection_def_dict)
        return output_collection_def

    def output_def(self, name):
        tool_as_dict = self.metadata_params["tool"]
        output_defs = tool_as_dict["outputs"]
        if name not in output_defs:
            return None

        output_def_dict = output_defs[name]
        output_def = ToolOutput.from_dict(name, output_def_dict)
        return output_def

    def job_id(self):
        return "non-session bound job"

    def get_hdca(self, object_id):
        hdca = self.import_store.sa_session.query(HistoryDatasetCollectionAssociation).find(int(object_id))
        if hdca:
            self.export_store.add_dataset_collection(hdca)
            for collection_dataset in hdca.dataset_instances:
                include_files = True
                self.export_store.add_dataset(collection_dataset, include_files=include_files)
                self.export_store.collection_datasets.add(collection_dataset.id)

        return hdca

    def add_dataset_collection(self, collection):
        self.export_store.add_dataset_collection(collection)
        for collection_dataset in collection.dataset_instances:
            include_files = True
            self.export_store.add_dataset(collection_dataset, include_files=include_files)
            self.export_store.collection_datasets.add(collection_dataset.id)

    def add_output_dataset_association(self, name, dataset_instance):
        self.export_store.add_job_output_dataset_associations(self.get_job_id(), name, dataset_instance)

    def get_job_id(self):
        return self.metadata_params["job_id_tag"]

    def get_implicit_collection_jobs_association_id(self):
        return self.metadata_params.get("implicit_collection_jobs_association_id")


def collect_primary_datasets(job_context: Union[JobContext, SessionlessJobContext], output, input_ext):
    job_working_directory = job_context.job_working_directory

    # Loop through output file names, looking for generated primary
    # datasets in form specified by discover dataset patterns or in tool provided metadata.
    new_outdata_name = None
    primary_datasets: Dict[str, Dict[str, Union[HistoryDatasetAssociation, LibraryDatasetDatasetAssociation]]] = {}
    storage_callbacks: List[Callable] = []
    for name, outdata in output.items():
        primary_output_assigned = False
        dataset_collectors = [DEFAULT_DATASET_COLLECTOR]
        output_def = job_context.output_def(name)
        if output_def is not None:
            dataset_collectors = [
                dataset_collector(description) for description in output_def.dataset_collector_descriptions
            ]
        filenames = {}
        for discovered_file in discover_files(
            name, job_context.tool_provided_metadata, dataset_collectors, job_working_directory, outdata
        ):
            job_context.increment_discovered_file_count()
            filenames[discovered_file.path] = discovered_file
        for filename_index, (filename, discovered_file) in enumerate(filenames.items()):
            extra_file_collector = discovered_file.collector
            fields_match = discovered_file.match
            if not fields_match:
                # Before I guess pop() would just have thrown an IndexError
                raise Exception(f"Problem parsing metadata fields for file {filename}")
            designation = fields_match.designation
            ext = fields_match.ext
            if ext == "input":
                ext = input_ext
            dbkey = fields_match.dbkey
            if dbkey == INPUT_DBKEY_TOKEN:
                dbkey = job_context.input_dbkey
            if filename_index == 0 and extra_file_collector.assign_primary_output:
                new_outdata_name = fields_match.name or f"{outdata.name} ({designation})"
                outdata.change_datatype(ext)
                outdata.dbkey = dbkey
                outdata.designation = designation
                outdata.dataset.external_filename = None  # resets filename_override
                # Move data from temp location to dataset location
                if not outdata.dataset.purged:
                    job_context.object_store.update_from_file(outdata.dataset, file_name=filename, create=True)
                primary_output_assigned = True
                continue
            if name not in primary_datasets:
                primary_datasets[name] = {}
            visible = fields_match.visible
            # Create new primary dataset
            new_primary_name = fields_match.name or f"{outdata.name} ({designation})"
            info = outdata.info

            # TODO: should be able to disambiguate files in different directories...
            new_primary_filename = os.path.split(filename)[-1]
            new_primary_datasets_attributes = job_context.tool_provided_metadata.get_new_dataset_meta_by_basename(
                name, new_primary_filename
            )
            extra_files = None
            if new_primary_datasets_attributes:
                extra_files_path = new_primary_datasets_attributes.get("extra_files", None)
                if extra_files_path:
                    extra_files = os.path.join(job_working_directory, extra_files_path)
            primary_data = job_context.create_dataset(
                ext,
                designation,
                visible,
                dbkey,
                new_primary_name,
                filename,
                extra_files=extra_files,
                info=info,
                init_from=outdata,
                dataset_attributes=new_primary_datasets_attributes,
                creating_job_id=job_context.get_job_id() if job_context else None,
                storage_callbacks=storage_callbacks,
                purged=outdata.dataset.purged,
            )
            # Associate new dataset with job
            job_context.add_output_dataset_association(f"__new_primary_file_{name}|{designation}__", primary_data)
            job_context.add_datasets_to_history([primary_data], for_output_dataset=outdata)
            # Add dataset to return dict
            primary_datasets[name][designation] = primary_data
        if primary_output_assigned:
            outdata.name = new_outdata_name
            outdata.init_meta()
            if not outdata.dataset.purged:
                try:
                    outdata.set_meta()
                except Exception:
                    # We don't want to fail here on a single "bad" discovered dataset
                    log.debug("set meta failed for %s", outdata, exc_info=True)
                    outdata.state = HistoryDatasetAssociation.states.FAILED_METADATA
            outdata.set_peek()
            outdata.discovered = True
            sa_session = job_context.sa_session
            if sa_session:
                sa_session.add(outdata)

    # Move discovered outputs to storage and set metdata / peeks
    for callback in storage_callbacks:
        callback()
    return primary_datasets


def discover_files(output_name, tool_provided_metadata, extra_file_collectors, job_working_directory, matchable):
    extra_file_collectors = extra_file_collectors
    if extra_file_collectors and extra_file_collectors[0].discover_via == "tool_provided_metadata":
        # just load entries from tool provided metadata...
        assert len(extra_file_collectors) == 1
        extra_file_collector = extra_file_collectors[0]
        target_directory = discover_target_directory(extra_file_collector.directory, job_working_directory)
        for dataset in tool_provided_metadata.get_new_datasets(output_name):
            filename = dataset["filename"]
            path = os.path.join(target_directory, filename)
            yield DiscoveredFile(
                path,
                extra_file_collector,
                JsonCollectedDatasetMatch(dataset, extra_file_collector, filename, path=path),
            )
    else:
        for match, collector in walk_over_file_collectors(extra_file_collectors, job_working_directory, matchable):
            yield DiscoveredFile(match.path, collector, match)


def walk_over_file_collectors(extra_file_collectors, job_working_directory, matchable):
    for extra_file_collector in extra_file_collectors:
        assert extra_file_collector.discover_via == "pattern"
        for match in walk_over_extra_files(
            extra_file_collector.directory, extra_file_collector, job_working_directory, matchable
        ):
            yield match, extra_file_collector


def walk_over_extra_files(target_dir, extra_file_collector, job_working_directory, matchable, parent_paths=None):
    """
    Walks through all files in a given directory, and returns all files that
    match the given collector's match criteria. If the collector has the
    recurse flag enabled, will also recursively descend into child folders.
    """
    parent_paths = parent_paths or []

    def _walk(target_dir, extra_file_collector, job_working_directory, matchable, parent_paths):
        directory = discover_target_directory(target_dir, job_working_directory)
        if os.path.isdir(directory):
            for filename in os.listdir(directory):
                path = os.path.join(directory, filename)
                if os.path.isdir(path):
                    if extra_file_collector.recurse:
                        new_parent_paths = parent_paths[:]
                        new_parent_paths.append(filename)
                        # The current directory is already validated, so use that as the next job_working_directory when recursing
                        yield from _walk(
                            filename, extra_file_collector, directory, matchable, parent_paths=new_parent_paths
                        )
                else:
                    match = extra_file_collector.match(matchable, filename, path=path, parent_paths=parent_paths)
                    if match:
                        yield match

    yield from extra_file_collector.sort(
        _walk(target_dir, extra_file_collector, job_working_directory, matchable, parent_paths)
    )


def dataset_collector(dataset_collection_description):
    if dataset_collection_description is DEFAULT_DATASET_COLLECTOR_DESCRIPTION:
        # Use 'is' and 'in' operators, so lets ensure this is
        # treated like a singleton.
        return DEFAULT_DATASET_COLLECTOR
    else:
        if dataset_collection_description.discover_via == "pattern":
            return DatasetCollector(dataset_collection_description)
        else:
            return ToolMetadataDatasetCollector(dataset_collection_description)


class ToolMetadataDatasetCollector:
    def __init__(self, dataset_collection_description):
        self.discover_via = dataset_collection_description.discover_via
        self.default_dbkey = dataset_collection_description.default_dbkey
        self.default_ext = dataset_collection_description.default_ext
        self.default_visible = dataset_collection_description.default_visible
        self.directory = dataset_collection_description.directory
        self.assign_primary_output = dataset_collection_description.assign_primary_output


class DatasetCollector:
    def __init__(self, dataset_collection_description):
        self.discover_via = dataset_collection_description.discover_via
        # dataset_collection_description is an abstract description
        # built from the tool parsing module - see galaxy.tool_util.parser.output_collection_def
        self.sort_key = dataset_collection_description.sort_key
        self.sort_reverse = dataset_collection_description.sort_reverse
        self.sort_comp = dataset_collection_description.sort_comp
        self.pattern = dataset_collection_description.pattern
        self.default_dbkey = dataset_collection_description.default_dbkey
        self.default_ext = dataset_collection_description.default_ext
        self.default_visible = dataset_collection_description.default_visible
        self.directory = dataset_collection_description.directory
        self.assign_primary_output = dataset_collection_description.assign_primary_output
        self.recurse = dataset_collection_description.recurse
        self.match_relative_path = dataset_collection_description.match_relative_path

    def _pattern_for_dataset(self, dataset_instance=None):
        token_replacement = r"\d+"
        if dataset_instance:
            token_replacement = str(dataset_instance.id)
        return self.pattern.replace(DATASET_ID_TOKEN, token_replacement)

    def match(self, dataset_instance, filename, path=None, parent_paths=None):
        pattern = self._pattern_for_dataset(dataset_instance)
        if self.match_relative_path and parent_paths:
            filename = os.path.join(*parent_paths, filename)
        match_object = None
        if re_match := re.match(pattern, filename):
            match_object = RegexCollectedDatasetMatch(re_match, self, filename, path=path)
        return match_object

    def sort(self, matches):
        reverse = self.sort_reverse
        sort_key = self.sort_key
        sort_comp = self.sort_comp
        assert sort_key in ["filename", "dbkey", "name", "designation"]
        assert sort_comp in ["lexical", "numeric"]
        key = operator.attrgetter(sort_key)
        if sort_comp == "numeric":
            key = _compose(int, key)

        return sorted(matches, key=key, reverse=reverse)


def _compose(f, g):
    return lambda x: f(g(x))


DEFAULT_DATASET_COLLECTOR = DatasetCollector(DEFAULT_DATASET_COLLECTOR_DESCRIPTION)
DEFAULT_TOOL_PROVIDED_DATASET_COLLECTOR = ToolMetadataDatasetCollector(ToolProvidedMetadataDatasetCollection())


def read_exit_code_from(exit_code_file, id_tag):
    """Read exit code reported for a Galaxy job."""
    try:
        # This should be an 8-bit exit code, but read ahead anyway:
        exit_code_str = open(exit_code_file).read(32)
    except Exception:
        # By default, the exit code is 0, which typically indicates success.
        exit_code_str = "0"

    try:
        # Decode the exit code. If it's bogus, then just use 0.
        exit_code = int(exit_code_str)
    except ValueError:
        galaxy_id_tag = id_tag
        log.warning(f"({galaxy_id_tag}) Exit code '{exit_code_str}' invalid. Using 0.")
        exit_code = 0

    return exit_code


def default_exit_code_file(files_dir, id_tag):
    return os.path.join(files_dir, f"galaxy_{id_tag}.ec")


def collect_extra_files(
    object_store: ObjectStore,
    dataset: "DatasetInstance",
    job_working_directory: str,
    outputs_to_working_directory: bool = False,
):
    # TODO: should this use compute_environment to determine the extra files path ?
    assert dataset.dataset
    real_file_name = file_name = dataset.dataset.extra_files_path_name_from(object_store)
    if outputs_to_working_directory:
        # OutputsToWorkingDirectoryPathRewriter always rewrites extra files to uuid path,
        # so we have to collect from that path even if the real extra files path is dataset_N_files
        file_name = f"dataset_{dataset.dataset.uuid}_files"
    output_location = "outputs"
    temp_file_path = os.path.join(job_working_directory, output_location, file_name)
    if not os.path.exists(temp_file_path):
        # Fall back to working dir, remove in 23.2
        output_location = "working"
        temp_file_path = os.path.join(job_working_directory, output_location, file_name)
    if not os.path.exists(temp_file_path):
        # no outputs to working directory, but may still need to push form cache to backend
        temp_file_path = dataset.extra_files_path
    try:
        # This skips creation of directories - object store
        # automatically creates them.  However, empty directories will
        # not be created in the object store at all, which might be a
        # problem.
        persist_extra_files(
            object_store=object_store,
            src_extra_files_path=temp_file_path,
            primary_data=dataset,
            extra_files_path_name=real_file_name,
        )
    except Exception as e:
        log.debug("Error in collect_associated_files: %s", unicodify(e))

    # Handle composite datatypes of auto_primary_file type
    if dataset.datatype.composite_type == "auto_primary_file" and not dataset.has_data():
        try:
            with NamedTemporaryFile(mode="w") as temp_fh:
                temp_fh.write(dataset.datatype.generate_primary_file(dataset))
                temp_fh.flush()
                object_store.update_from_file(dataset.dataset, file_name=temp_fh.name, create=True)
                dataset.set_size()
        except Exception as e:
            log.warning(
                "Unable to generate primary composite file automatically for %s: %s", dataset.dataset.id, unicodify(e)
            )


def collect_shrinked_content_from_path(path):
    try:
        with open(path, "rb") as fh:
            return shrink_and_unicodify(fh.read().strip())
    except FileNotFoundError:
        return None

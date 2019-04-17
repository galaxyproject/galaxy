""" Code allowing tools to define extra files associated with an output datset.
"""
import logging
import operator
import os
import re

import galaxy.model
from galaxy.model.dataset_collections.structure import UninitializedTree
from galaxy.model.store.discover import (
    discover_target_directory,
    discovered_file_for_element,
    DiscoveredFile,
    JsonCollectedDatasetMatch,
    ModelPersistenceContext,
    persist_elements_to_folder,
    persist_hdas,
    RegexCollectedDatasetMatch,
    UNSET,
)
from galaxy.tools.parser.output_collection_def import (
    DEFAULT_DATASET_COLLECTOR_DESCRIPTION,
    INPUT_DBKEY_TOKEN,
    ToolProvidedMetadataDatasetCollection,
)
from galaxy.util import (
    ExecutionTimer,
    odict
)

DATASET_ID_TOKEN = "DATASET_ID"

log = logging.getLogger(__name__)


# PermissionProvider and MetadataSourceProvider are abstractions over input data used to
# collect and produce dynamic outputs.
class PermissionProvider(object):

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
        permissions = self.permissions
        if permissions is not UNSET:
            self._security_agent.set_all_dataset_permissions(primary_data.dataset, permissions, new=True, flush=False)

    def copy_dataset_permissions(self, init_from, primary_data):
        self._security_agent.copy_dataset_permissions(init_from.dataset, primary_data.dataset)


class MetadataSourceProvider(object):

    def __init__(self, inp_data):
        self._inp_data = inp_data

    def get_metadata_source(self, input_name):
        return self._inp_data[input_name]


def collect_dynamic_outputs(
    job_context,
    output_collections,
):
    tool = job_context.tool
    app = job_context.app
    sa_session = job_context.sa_session
    collections_service = app.dataset_collections_service
    job_working_directory = job_context.job_working_directory

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
        trans = job_context.work_context

        # three destination types we need to handle here - "library_folder" (place discovered files in a library folder),
        # "hdca" (place discovered files in a history dataset collection), and "hdas" (place discovered files in a history
        # as stand-alone datasets).
        if destination_type == "library_folder":
            # populate a library folder (needs to be already have been created)

            library_folder_manager = app.library_folder_manager
            library_folder = library_folder_manager.get(trans, app.security.decode_id(destination.get("library_folder_id")))
            persist_elements_to_folder(job_context, elements, library_folder)
        elif destination_type == "hdca":
            # create or populate a dataset collection in the history
            history = job_context.job.history
            assert "collection_type" in unnamed_output_dict
            object_id = destination.get("object_id")
            if object_id:
                hdca = sa_session.query(galaxy.model.HistoryDatasetCollectionAssociation).get(int(object_id))
            else:
                name = unnamed_output_dict.get("name", "unnamed collection")
                collection_type = unnamed_output_dict["collection_type"]
                collection_type_description = collections_service.collection_type_descriptions.for_collection_type(collection_type)
                structure = UninitializedTree(collection_type_description)
                hdca = collections_service.precreate_dataset_collection_instance(
                    trans, history, name, structure=structure
                )
            filenames = odict.odict()

            def add_to_discovered_files(elements, parent_identifiers=[]):
                for element in elements:
                    if "elements" in element:
                        add_to_discovered_files(element["elements"], parent_identifiers + [element["name"]])
                    else:
                        discovered_file = discovered_file_for_element(element, job_working_directory, parent_identifiers, collector=DEFAULT_DATASET_COLLECTOR)
                        filenames[discovered_file.path] = discovered_file

            add_to_discovered_files(elements)

            collection = hdca.collection
            collection_builder = collections_service.collection_builder_for(
                collection
            )
            job_context.populate_collection_elements(
                collection,
                collection_builder,
                filenames,
            )
            collection_builder.populate()
        elif destination_type == "hdas":
            persist_hdas(elements, job_context)

    for name, has_collection in output_collections.items():
        if name not in tool.output_collections:
            continue
        output_collection_def = tool.output_collections[name]
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

            collection_builder = collections_service.collection_builder_for(
                collection
            )
            dataset_collectors = [dataset_collector(description) for description in output_collection_def.dataset_collector_descriptions]
            output_name = output_collection_def.name
            filenames = job_context.find_files(output_name, collection, dataset_collectors)
            job_context.populate_collection_elements(
                collection,
                collection_builder,
                filenames,
                name=output_collection_def.name,
                metadata_source_name=output_collection_def.metadata_source,
            )
            collection_builder.populate()
        except Exception:
            log.exception("Problem gathering output collection.")
            collection.handle_population_failed("Problem building datasets for collection.")


class JobContext(ModelPersistenceContext):

    def __init__(self, tool, tool_provided_metadata, job, job_working_directory, permission_provider, metadata_source_provider, input_dbkey, object_store):
        self.tool = tool
        self.metadata_source_provider = metadata_source_provider
        self.permission_provider = permission_provider
        self.input_dbkey = input_dbkey
        self.app = tool.app
        self.sa_session = tool.sa_session
        self.job = job
        self.job_working_directory = job_working_directory
        self.tool_provided_metadata = tool_provided_metadata
        self.object_store = object_store

    @property
    def work_context(self):
        from galaxy.work.context import WorkRequestContext
        return WorkRequestContext(self.app, user=self.user)

    @property
    def user(self):
        if self.job:
            user = self.job.user
        else:
            user = None
        return user

    @property
    def tag_handler(self):
        return self.app.tag_handler

    def find_files(self, output_name, collection, dataset_collectors):
        filenames = odict.odict()
        for discovered_file in discover_files(output_name, self.tool_provided_metadata, dataset_collectors, self.job_working_directory, collection):
            filenames[discovered_file.path] = discovered_file
        return filenames

    def populate_collection_elements(self, collection, root_collection_builder, filenames, name=None, metadata_source_name=None):
        # TODO: allow configurable sorting.
        #    <sort by="lexical" /> <!-- default -->
        #    <sort by="reverse_lexical" />
        #    <sort regex="example.(\d+).fastq" by="1:numerical" />
        #    <sort regex="part_(\d+)_sample_([^_]+).fastq" by="2:lexical,1:numerical" />
        if name is None:
            name = "unnamed output"

        element_datasets = []
        for filename, discovered_file in filenames.items():
            create_dataset_timer = ExecutionTimer()
            fields_match = discovered_file.match
            if not fields_match:
                raise Exception("Problem parsing metadata fields for file %s" % filename)
            element_identifiers = fields_match.element_identifiers
            designation = fields_match.designation
            visible = fields_match.visible
            ext = fields_match.ext
            dbkey = fields_match.dbkey
            if dbkey == INPUT_DBKEY_TOKEN:
                dbkey = self.input_dbkey

            # Create new primary dataset
            dataset_name = fields_match.name or designation

            link_data = discovered_file.match.link_data
            tag_list = discovered_file.match.tag_list

            sources = discovered_file.match.sources
            hashes = discovered_file.match.hashes

            dataset = self.create_dataset(
                ext=ext,
                designation=designation,
                visible=visible,
                dbkey=dbkey,
                name=dataset_name,
                filename=filename,
                metadata_source_name=metadata_source_name,
                link_data=link_data,
                tag_list=tag_list,
                sources=sources,
                hashes=hashes,
            )
            log.debug(
                "(%s) Created dynamic collection dataset for path [%s] with element identifier [%s] for output [%s] %s",
                self.job.id,
                filename,
                designation,
                name,
                create_dataset_timer,
            )
            element_datasets.append((element_identifiers, dataset))

        sa_session = self.sa_session

        add_datasets_timer = ExecutionTimer()
        self.add_datasets_to_history([d for (ei, d) in element_datasets])
        log.debug(
            "(%s) Add dynamic collection datasets to history for output [%s] %s",
            self.job.id,
            name,
            add_datasets_timer,
        )

        for (element_identifiers, dataset) in element_datasets:
            current_builder = root_collection_builder
            for element_identifier in element_identifiers[:-1]:
                current_builder = current_builder.get_level(element_identifier)
            current_builder.add_dataset(element_identifiers[-1], dataset)

            # Associate new dataset with job
            element_identifier_str = ":".join(element_identifiers)
            association_name = '__new_primary_file_%s|%s__' % (name, element_identifier_str)
            self.add_output_dataset_association(association_name, dataset)

            dataset.raw_set_dataset_state('ok')

        sa_session.flush()

    def persist_object(self, obj):
        self.sa_session.add(obj)

    def flush(self):
        self.sa_session.flush()

    def create_library_folder(self, parent_folder, name, description):
        assert parent_folder.id
        library_folder_manager = self.app.library_folder_manager
        nested_folder = library_folder_manager.create(self.work_context, parent_folder.id, name, description)
        return nested_folder

    def add_output_dataset_association(self, name, dataset):
        assoc = galaxy.model.JobToOutputDatasetAssociation(name, dataset)
        assoc.job = self.job
        self.sa_session.add(assoc)

    def add_library_dataset_to_folder(self, library_folder, ld):
        trans = self.work_context
        ldda = ld.library_dataset_dataset_association
        trans.sa_session.add(ldda)

        trans = self.work_context
        trans.app.security_agent.copy_library_permissions(trans, library_folder, ld)
        trans.sa_session.add(ld)
        trans.sa_session.flush()

        # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
        trans.app.security_agent.copy_library_permissions(trans, ld, ldda)
        # Copy the current user's DefaultUserPermissions to the new LibraryDatasetDatasetAssociation.dataset
        trans.app.security_agent.set_all_dataset_permissions(ldda.dataset, trans.app.security_agent.user_get_default_permissions(trans.user))
        library_folder.add_library_dataset(ld, genome_build=ldda.dbkey)
        trans.sa_session.add(library_folder)
        trans.sa_session.flush()

        trans.sa_session.add(ld)
        trans.sa_session.flush()

    def add_datasets_to_history(self, datasets, for_output_dataset=None):
        sa_session = self.sa_session
        self.job.history.add_datasets(sa_session, datasets)
        if for_output_dataset is not None:
            # Need to update all associated output hdas, i.e. history was
            # shared with job running
            for copied_dataset in for_output_dataset.dataset.history_associations:
                if copied_dataset == for_output_dataset:
                    continue
                for dataset in datasets:
                    new_data = dataset.copy()
                    copied_dataset.history.add_dataset(new_data)
                    sa_session.add(new_data)
                    sa_session.flush()


def collect_primary_datasets(job_context, output, input_ext):
    tool = job_context.tool
    job_working_directory = job_context.job_working_directory
    sa_session = job_context.sa_session

    # Loop through output file names, looking for generated primary
    # datasets in form specified by discover dataset patterns or in tool provided metadata.
    primary_output_assigned = False
    new_outdata_name = None
    primary_datasets = {}
    for output_index, (name, outdata) in enumerate(output.items()):
        dataset_collectors = [DEFAULT_DATASET_COLLECTOR]
        if name in tool.outputs:
            dataset_collectors = [dataset_collector(description) for description in tool.outputs[name].dataset_collector_descriptions]
        filenames = odict.odict()
        for discovered_file in discover_files(name, job_context.tool_provided_metadata, dataset_collectors, job_working_directory, outdata):
            filenames[discovered_file.path] = discovered_file
        for filename_index, (filename, discovered_file) in enumerate(filenames.items()):
            extra_file_collector = discovered_file.collector
            fields_match = discovered_file.match
            if not fields_match:
                # Before I guess pop() would just have thrown an IndexError
                raise Exception("Problem parsing metadata fields for file %s" % filename)
            designation = fields_match.designation
            if filename_index == 0 and extra_file_collector.assign_primary_output and output_index == 0:
                new_outdata_name = fields_match.name or "%s (%s)" % (outdata.name, designation)
                # Move data from temp location to dataset location
                job_context.object_store.update_from_file(outdata.dataset, file_name=filename, create=True)
                primary_output_assigned = True
                continue
            if name not in primary_datasets:
                primary_datasets[name] = odict.odict()
            visible = fields_match.visible
            ext = fields_match.ext
            if ext == "input":
                ext = input_ext
            dbkey = fields_match.dbkey
            if dbkey == INPUT_DBKEY_TOKEN:
                dbkey = job_context.input_dbkey
            # Create new primary dataset
            new_primary_name = fields_match.name or "%s (%s)" % (outdata.name, designation)
            info = outdata.info

            # TODO: should be able to disambiguate files in different directories...
            new_primary_filename = os.path.split(filename)[-1]
            new_primary_datasets_attributes = job_context.tool_provided_metadata.get_new_dataset_meta_by_basename(name, new_primary_filename)

            primary_data = job_context.create_dataset(
                ext,
                designation,
                visible,
                dbkey,
                new_primary_name,
                filename,
                info=info,
                init_from=outdata,
                dataset_attributes=new_primary_datasets_attributes,
            )
            # Associate new dataset with job
            job_context.add_output_dataset_association('__new_primary_file_%s|%s__' % (name, designation), primary_data)

            if new_primary_datasets_attributes:
                extra_files_path = new_primary_datasets_attributes.get('extra_files', None)
                if extra_files_path:
                    extra_files_path_joined = os.path.join(job_working_directory, extra_files_path)
                    for root, dirs, files in os.walk(extra_files_path_joined):
                        extra_dir = os.path.join(primary_data.extra_files_path, root.replace(extra_files_path_joined, '', 1).lstrip(os.path.sep))
                        extra_dir = os.path.normpath(extra_dir)
                        for f in files:
                            job_context.object_store.update_from_file(
                                primary_data.dataset,
                                extra_dir=extra_dir,
                                alt_name=f,
                                file_name=os.path.join(root, f),
                                create=True,
                                preserve_symlinks=True
                            )
            job_context.add_datasets_to_history([primary_data], for_output_dataset=outdata)
            # Add dataset to return dict
            primary_datasets[name][designation] = primary_data
        if primary_output_assigned:
            outdata.name = new_outdata_name
            outdata.init_meta()
            outdata.set_meta()
            outdata.set_peek()
            sa_session.add(outdata)

    sa_session.flush()
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
            yield DiscoveredFile(path, extra_file_collector, JsonCollectedDatasetMatch(dataset, extra_file_collector, filename, path=path))
    else:
        for (match, collector) in walk_over_file_collectors(extra_file_collectors, job_working_directory, matchable):
            yield DiscoveredFile(match.path, collector, match)


def walk_over_file_collectors(extra_file_collectors, job_working_directory, matchable):
    for extra_file_collector in extra_file_collectors:
        assert extra_file_collector.discover_via == "pattern"
        for match in walk_over_extra_files(extra_file_collector.directory, extra_file_collector, job_working_directory, matchable):
            yield match, extra_file_collector


def walk_over_extra_files(target_dir, extra_file_collector, job_working_directory, matchable):
    """
    Walks through all files in a given directory, and returns all files that
    match the given collector's match criteria. If the collector has the
    recurse flag enabled, will also recursively descend into child folders.
    """
    matches = []
    directory = discover_target_directory(target_dir, job_working_directory)
    if os.path.isdir(directory):
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            if os.path.isdir(path) and extra_file_collector.recurse:
                # The current directory is already validated, so use that as the next job_working_directory when recursing
                for match in walk_over_extra_files(filename, extra_file_collector, directory, matchable):
                    yield match
            else:
                match = extra_file_collector.match(matchable, filename, path=path)
                if match:
                    matches.append(match)

    for match in extra_file_collector.sort(matches):
        yield match


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


class ToolMetadataDatasetCollector(object):

    def __init__(self, dataset_collection_description):
        self.discover_via = dataset_collection_description.discover_via
        self.default_dbkey = dataset_collection_description.default_dbkey
        self.default_ext = dataset_collection_description.default_ext
        self.default_visible = dataset_collection_description.default_visible
        self.directory = dataset_collection_description.directory
        self.assign_primary_output = dataset_collection_description.assign_primary_output


class DatasetCollector(object):

    def __init__(self, dataset_collection_description):
        self.discover_via = dataset_collection_description.discover_via
        # dataset_collection_description is an abstract description
        # built from the tool parsing module - see galaxy.tools.parser.output_colleciton_def
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

    def _pattern_for_dataset(self, dataset_instance=None):
        token_replacement = r'\d+'
        if dataset_instance:
            token_replacement = str(dataset_instance.id)
        return self.pattern.replace(DATASET_ID_TOKEN, token_replacement)

    def match(self, dataset_instance, filename, path=None):
        pattern = self._pattern_for_dataset(dataset_instance)
        re_match = re.match(pattern, filename)
        match_object = None
        if re_match:
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

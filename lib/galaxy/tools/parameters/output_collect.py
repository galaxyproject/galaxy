""" Code allowing tools to define extra files associated with an output datset.
"""
import glob
import json
import logging
import operator
import os
import re

from galaxy import jobs
from galaxy import util
from galaxy.tools.parser.output_collection_def import (
    DEFAULT_DATASET_COLLECTOR_DESCRIPTION,
    INPUT_DBKEY_TOKEN,
)
from galaxy.util import (
    ExecutionTimer,
    odict
)

DATASET_ID_TOKEN = "DATASET_ID"

log = logging.getLogger( __name__ )


def collect_dynamic_collections(
    tool,
    output_collections,
    job_working_directory,
    inp_data={},
    job=None,
    input_dbkey="?",
):
    collections_service = tool.app.dataset_collections_service
    job_context = JobContext(
        tool,
        job,
        job_working_directory,
        inp_data,
        input_dbkey,
    )

    for name, has_collection in output_collections.items():
        if name not in tool.output_collections:
            continue
        output_collection_def = tool.output_collections[ name ]
        if not output_collection_def.dynamic_structure:
            continue

        # Could be HDCA for normal jobs or a DC for mapping
        # jobs.
        if hasattr(has_collection, "collection"):
            collection = has_collection.collection
        else:
            collection = has_collection

        try:
            collection_builder = collections_service.collection_builder_for(
                collection
            )
            job_context.populate_collection_elements(
                collection,
                collection_builder,
                output_collection_def,
            )
            collection_builder.populate()
        except Exception:
            log.exception("Problem gathering output collection.")
            collection.handle_population_failed("Problem building datasets for collection.")


class JobContext( object ):

    def __init__( self, tool, job, job_working_directory, inp_data, input_dbkey ):
        self.inp_data = inp_data
        self.input_dbkey = input_dbkey
        self.app = tool.app
        self.sa_session = tool.sa_session
        self.job = job
        self.job_working_directory = job_working_directory

    @property
    def permissions( self ):
        inp_data = self.inp_data
        existing_datasets = [ inp for inp in inp_data.values() if inp ]
        if existing_datasets:
            permissions = self.app.security_agent.guess_derived_permissions_for_datasets( existing_datasets )
        else:
            # No valid inputs, we will use history defaults
            permissions = self.app.security_agent.history_get_default_permissions( self.job.history )
        return permissions

    def find_files( self, collection, dataset_collectors ):
        filenames = odict.odict()
        for path, extra_file_collector in walk_over_extra_files( dataset_collectors, self.job_working_directory, collection ):
            filenames[ path ] = extra_file_collector
        return filenames

    def populate_collection_elements( self, collection, root_collection_builder, output_collection_def ):
        # TODO: allow configurable sorting.
        #    <sort by="lexical" /> <!-- default -->
        #    <sort by="reverse_lexical" />
        #    <sort regex="example.(\d+).fastq" by="1:numerical" />
        #    <sort regex="part_(\d+)_sample_([^_]+).fastq" by="2:lexical,1:numerical" />
        dataset_collectors = map(dataset_collector, output_collection_def.dataset_collector_descriptions)
        filenames = self.find_files( collection, dataset_collectors )

        element_datasets = []
        for filename, extra_file_collector in filenames.items():
            create_dataset_timer = ExecutionTimer()
            fields_match = extra_file_collector.match( collection, os.path.basename( filename ) )
            if not fields_match:
                raise Exception( "Problem parsing metadata fields for file %s" % filename )
            element_identifiers = fields_match.element_identifiers
            designation = fields_match.designation
            visible = fields_match.visible
            ext = fields_match.ext
            dbkey = fields_match.dbkey
            if dbkey == INPUT_DBKEY_TOKEN:
                dbkey = self.input_dbkey

            # Create new primary dataset
            name = fields_match.name or designation

            dataset = self.create_dataset(
                ext=ext,
                designation=designation,
                visible=visible,
                dbkey=dbkey,
                name=name,
                filename=filename,
                metadata_source_name=output_collection_def.metadata_source,
            )
            log.debug(
                "(%s) Created dynamic collection dataset for path [%s] with element identifier [%s] for output [%s] %s",
                self.job.id,
                filename,
                designation,
                output_collection_def.name,
                create_dataset_timer,
            )
            element_datasets.append((element_identifiers, dataset))

        app = self.app
        sa_session = self.sa_session
        job = self.job

        if job:
            add_datasets_timer = ExecutionTimer()
            job.history.add_datasets(sa_session, [d for (ei, d) in element_datasets])
            log.debug(
                "(%s) Add dynamic collection datsets to history for output [%s] %s",
                self.job.id,
                output_collection_def.name,
                add_datasets_timer,
            )

        for (element_identifiers, dataset) in element_datasets:
            current_builder = root_collection_builder
            for element_identifier in element_identifiers[:-1]:
                current_builder = current_builder.get_level(element_identifier)
            current_builder.add_dataset( element_identifiers[-1], dataset )

            # Associate new dataset with job
            if job:
                element_identifier_str = ":".join(element_identifiers)
                # Below was changed from '__new_primary_file_%s|%s__' % ( name, designation )
                assoc = app.model.JobToOutputDatasetAssociation( '__new_primary_file_%s|%s__' % ( name, element_identifier_str ), dataset )
                assoc.job = self.job
            sa_session.add( assoc )

            dataset.raw_set_dataset_state('ok')

        sa_session.flush()

    def create_dataset(
        self,
        ext,
        designation,
        visible,
        dbkey,
        name,
        filename,
        metadata_source_name,
    ):
        app = self.app
        sa_session = self.sa_session

        primary_data = _new_hda(app, sa_session, ext, designation, visible, dbkey, self.permissions)

        # Copy metadata from one of the inputs if requested.
        metadata_source = None
        if metadata_source_name:
            metadata_source = self.inp_data[ metadata_source_name ]

        sa_session.flush()
        # Move data from temp location to dataset location
        app.object_store.update_from_file(primary_data.dataset, file_name=filename, create=True)
        primary_data.set_size()
        # If match specified a name use otherwise generate one from
        # designation.
        primary_data.name = name

        if metadata_source:
            primary_data.init_meta( copy_from=metadata_source )
        else:
            primary_data.init_meta()

        primary_data.set_meta()
        primary_data.set_peek()

        return primary_data


def collect_primary_datasets( tool, output, job_working_directory, input_ext, input_dbkey="?" ):
    app = tool.app
    sa_session = tool.sa_session
    new_primary_datasets = {}
    try:
        galaxy_json_path = os.path.join( job_working_directory, "working", jobs.TOOL_PROVIDED_JOB_METADATA_FILE )
        # LEGACY: Remove in 17.XX
        if not os.path.exists( galaxy_json_path ):
            # Maybe this is a legacy job, use the job working directory instead
            galaxy_json_path = os.path.join( job_working_directory, jobs.TOOL_PROVIDED_JOB_METADATA_FILE )
        json_file = open( galaxy_json_path, 'r' )
        for line in json_file:
            line = json.loads( line )
            if line.get( 'type' ) == 'new_primary_dataset':
                new_primary_datasets[ os.path.split( line.get( 'filename' ) )[-1] ] = line
    except Exception:
        # This should not be considered an error or warning condition, this file is optional
        pass
    # Loop through output file names, looking for generated primary
    # datasets in form of:
    #     'primary_associatedWithDatasetID_designation_visibility_extension(_DBKEY)'
    primary_output_assigned = False
    new_outdata_name = None
    primary_datasets = {}
    for output_index, ( name, outdata ) in enumerate( output.items() ):
        dataset_collectors = map(dataset_collector, tool.outputs[ name ].dataset_collector_descriptions) if name in tool.outputs else [ DEFAULT_DATASET_COLLECTOR ]
        filenames = odict.odict()
        if 'new_file_path' in app.config.collect_outputs_from:
            if DEFAULT_DATASET_COLLECTOR in dataset_collectors:
                # 'new_file_path' collection should be considered deprecated,
                # only use old-style matching (glob instead of regex and only
                # using default collector - if enabled).
                for filename in glob.glob(os.path.join(app.config.new_file_path, "primary_%i_*" % outdata.id) ):
                    filenames[ filename ] = DEFAULT_DATASET_COLLECTOR
        if 'job_working_directory' in app.config.collect_outputs_from:
            for path, extra_file_collector in walk_over_extra_files( dataset_collectors, job_working_directory, outdata ):
                filenames[ path ] = extra_file_collector
        for filename_index, ( filename, extra_file_collector ) in enumerate( filenames.items() ):
            fields_match = extra_file_collector.match( outdata, os.path.basename( filename ) )
            if not fields_match:
                # Before I guess pop() would just have thrown an IndexError
                raise Exception( "Problem parsing metadata fields for file %s" % filename )
            designation = fields_match.designation
            if filename_index == 0 and extra_file_collector.assign_primary_output and output_index == 0:
                new_outdata_name = fields_match.name or "%s (%s)" % ( outdata.name, designation )
                # Move data from temp location to dataset location
                app.object_store.update_from_file( outdata.dataset, file_name=filename, create=True )
                primary_output_assigned = True
                continue
            if name not in primary_datasets:
                primary_datasets[ name ] = odict.odict()
            visible = fields_match.visible
            ext = fields_match.ext
            if ext == "input":
                ext = input_ext
            dbkey = fields_match.dbkey
            if dbkey == INPUT_DBKEY_TOKEN:
                dbkey = input_dbkey
            # Create new primary dataset
            primary_data = _new_hda(app, sa_session, ext, designation, visible, dbkey)
            app.security_agent.copy_dataset_permissions( outdata.dataset, primary_data.dataset )
            sa_session.flush()
            # Move data from temp location to dataset location
            app.object_store.update_from_file(primary_data.dataset, file_name=filename, create=True)
            primary_data.set_size()
            # If match specified a name use otherwise generate one from
            # designation.
            primary_data.name = fields_match.name or "%s (%s)" % ( outdata.name, designation )
            primary_data.info = outdata.info
            primary_data.init_meta( copy_from=outdata )
            primary_data.dbkey = dbkey
            # Associate new dataset with job
            job = None
            for assoc in outdata.creating_job_associations:
                job = assoc.job
                break
            if job:
                assoc = app.model.JobToOutputDatasetAssociation( '__new_primary_file_%s|%s__' % ( name, designation ), primary_data )
                assoc.job = job
                sa_session.add( assoc )
                sa_session.flush()
            primary_data.state = outdata.state
            # add tool/metadata provided information
            new_primary_datasets_attributes = new_primary_datasets.get( os.path.split( filename )[-1], {} )
            if new_primary_datasets_attributes:
                dataset_att_by_name = dict( ext='extension' )
                for att_set in [ 'name', 'info', 'ext', 'dbkey' ]:
                    dataset_att_name = dataset_att_by_name.get( att_set, att_set )
                    setattr( primary_data, dataset_att_name, new_primary_datasets_attributes.get( att_set, getattr( primary_data, dataset_att_name ) ) )
                extra_files_path = new_primary_datasets_attributes.get( 'extra_files', None )
                if extra_files_path:
                    extra_files_path_joined = os.path.join( job_working_directory, extra_files_path )
                    for root, dirs, files in os.walk( extra_files_path_joined ):
                        extra_dir = os.path.join( primary_data.extra_files_path, root.replace( extra_files_path_joined, '', 1 ).lstrip( os.path.sep ) )
                        for f in files:
                            app.object_store.update_from_file(
                                primary_data.dataset,
                                extra_dir=extra_dir,
                                alt_name=f,
                                file_name=os.path.join( root, f ),
                                create=True,
                                dir_only=True,
                                preserve_symlinks=True
                            )
            metadata_dict = new_primary_datasets_attributes.get( 'metadata', None )
            if metadata_dict:
                if "dbkey" in new_primary_datasets_attributes:
                    metadata_dict["dbkey"] = new_primary_datasets_attributes["dbkey"]
                primary_data.metadata.from_JSON_dict( json_dict=metadata_dict )
            else:
                primary_data.set_meta()
            primary_data.set_peek()
            sa_session.add( primary_data )
            sa_session.flush()
            outdata.history.add_dataset( primary_data )
            # Add dataset to return dict
            primary_datasets[name][designation] = primary_data
            # Need to update all associated output hdas, i.e. history was
            # shared with job running
            for dataset in outdata.dataset.history_associations:
                if outdata == dataset:
                    continue
                new_data = primary_data.copy()
                dataset.history.add_dataset( new_data )
                sa_session.add( new_data )
                sa_session.flush()
        if primary_output_assigned:
            outdata.name = new_outdata_name
            outdata.init_meta()
            outdata.set_meta()
            outdata.set_peek()
            sa_session.add( outdata )
            sa_session.flush()
    return primary_datasets


def walk_over_extra_files( extra_file_collectors, job_working_directory, matchable ):
    for extra_file_collector in extra_file_collectors:
        matches = []
        directory = job_working_directory
        if extra_file_collector.directory:
            directory = os.path.join( directory, extra_file_collector.directory )
            if not util.in_directory( directory, job_working_directory ):
                raise Exception( "Problem with tool configuration, attempting to pull in datasets from outside working directory." )
        if not os.path.isdir( directory ):
            continue
        for filename in os.listdir( directory ):
            path = os.path.join( directory, filename )
            if not os.path.isfile( path ):
                continue
            match = extra_file_collector.match( matchable, filename, path=path )
            if match:
                matches.append(match)

        for match in extra_file_collector.sort(matches):
            yield match.path, extra_file_collector


def dataset_collector( dataset_collection_description ):
    if dataset_collection_description is DEFAULT_DATASET_COLLECTOR_DESCRIPTION:
        # Use 'is' and 'in' operators, so lets ensure this is
        # treated like a singleton.
        return DEFAULT_DATASET_COLLECTOR
    else:
        return DatasetCollector( dataset_collection_description )


class DatasetCollector( object ):

    def __init__( self, dataset_collection_description ):
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

    def pattern_for_dataset( self, dataset_instance=None ):
        token_replacement = r'\d+'
        if dataset_instance:
            token_replacement = str( dataset_instance.id )
        return self.pattern.replace( DATASET_ID_TOKEN, token_replacement )

    def match( self, dataset_instance, filename, path=None ):
        pattern = self.pattern_for_dataset( dataset_instance )
        re_match = re.match( pattern, filename )
        match_object = None
        if re_match:
            match_object = CollectedDatasetMatch( re_match, self, filename, path=path )
        return match_object

    def sort( self, matches ):
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


class CollectedDatasetMatch( object ):

    def __init__( self, re_match, collector, filename, path=None ):
        self.re_match = re_match
        self.collector = collector
        self.filename = filename
        self.path = path

    @property
    def designation( self ):
        re_match = self.re_match
        # If collecting nested collection, grap identifier_0,
        # identifier_1, etc... and join on : to build designation.
        element_identifiers = self.raw_element_identifiers
        if element_identifiers:
            return ":".join(element_identifiers)
        elif "designation" in re_match.groupdict():
            return re_match.group( "designation" )
        elif "name" in re_match.groupdict():
            return re_match.group( "name" )
        else:
            return None

    @property
    def element_identifiers( self ):
        return self.raw_element_identifiers or [self.designation]

    @property
    def raw_element_identifiers( self ):
        re_match = self.re_match
        identifiers = []
        i = 0
        while True:
            key = "identifier_%d" % i
            if key in re_match.groupdict():
                identifiers.append(re_match.group(key))
            else:
                break
            i += 1

        return identifiers

    @property
    def name( self ):
        """ Return name or None if not defined by the discovery pattern.
        """
        re_match = self.re_match
        name = None
        if "name" in re_match.groupdict():
            name = re_match.group( "name" )
        return name

    @property
    def dbkey( self ):
        try:
            return self.re_match.group( "dbkey" )
        except IndexError:
            return self.collector.default_dbkey

    @property
    def ext( self ):
        try:
            return self.re_match.group( "ext" )
        except IndexError:
            return self.collector.default_ext

    @property
    def visible( self ):
        try:
            return self.re_match.group( "visible" ).lower() == "visible"
        except IndexError:
            return self.collector.default_visible


UNSET = object()


def _new_hda(
    app,
    sa_session,
    ext,
    designation,
    visible,
    dbkey,
    permissions=UNSET,
):
    """Return a new unflushed HDA with dataset and permissions setup.
    """
    # Create new primary dataset
    primary_data = app.model.HistoryDatasetAssociation( extension=ext,
                                                        designation=designation,
                                                        visible=visible,
                                                        dbkey=dbkey,
                                                        create_dataset=True,
                                                        flush=False,
                                                        sa_session=sa_session )
    if permissions is not UNSET:
        app.security_agent.set_all_dataset_permissions( primary_data.dataset, permissions, new=True, flush=False )
    sa_session.add( primary_data )
    return primary_data


DEFAULT_DATASET_COLLECTOR = DatasetCollector(DEFAULT_DATASET_COLLECTOR_DESCRIPTION)

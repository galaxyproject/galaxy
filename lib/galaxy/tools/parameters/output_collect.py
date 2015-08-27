""" Code allowing tools to define extra files associated with an output datset.
"""
import os
import re
import glob
import json

from galaxy import jobs
from galaxy import util
from galaxy.util import odict

DATASET_ID_TOKEN = "DATASET_ID"
DEFAULT_EXTRA_FILENAME_PATTERN = r"primary_DATASET_ID_(?P<designation>[^_]+)_(?P<visible>[^_]+)_(?P<ext>[^_]+)(_(?P<dbkey>[^_]+))?"

import logging
log = logging.getLogger( __name__ )


def collect_dynamic_collections(
    tool,
    output_collections,
    job_working_directory,
    inp_data={},
    job=None,
):
    collections_service = tool.app.dataset_collections_service
    job_context = JobContext(
        tool,
        job,
        job_working_directory,
        inp_data,
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

    def __init__( self, tool, job, job_working_directory, inp_data ):
        self.inp_data = inp_data
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
        dataset_collectors = output_collection_def.dataset_collectors
        filenames = self.find_files( collection, dataset_collectors )

        for filename, extra_file_collector in filenames.iteritems():
            fields_match = extra_file_collector.match( collection, os.path.basename( filename ) )
            if not fields_match:
                raise Exception( "Problem parsing metadata fields for file %s" % filename )
            element_identifiers = fields_match.element_identifiers
            current_builder = root_collection_builder
            for element_identifier in element_identifiers[:-1]:
                current_builder = current_builder.get_level(element_identifier)
            designation = fields_match.designation
            visible = fields_match.visible
            ext = fields_match.ext
            dbkey = fields_match.dbkey
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
            current_builder.add_dataset( element_identifiers[-1], dataset )

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

        # Copy metadata from one of the inputs if requested.
        metadata_source = None
        if metadata_source_name:
            metadata_source = self.inp_data[ metadata_source_name ]

        # Create new primary dataset
        primary_data = app.model.HistoryDatasetAssociation( extension=ext,
                                                            designation=designation,
                                                            visible=visible,
                                                            dbkey=dbkey,
                                                            create_dataset=True,
                                                            sa_session=sa_session )
        app.security_agent.set_all_dataset_permissions( primary_data.dataset, self.permissions )
        sa_session.add( primary_data )
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

        # Associate new dataset with job
        if self.job:
            self.job.history.add_dataset( primary_data )

            assoc = app.model.JobToOutputDatasetAssociation( '__new_primary_file_%s|%s__' % ( name, designation ), primary_data )
            assoc.job = self.job
            sa_session.add( assoc )
            sa_session.flush()

        primary_data.state = 'ok'
        return primary_data


def collect_primary_datasets( tool, output, job_working_directory, input_ext ):
    app = tool.app
    sa_session = tool.sa_session
    new_primary_datasets = {}
    try:
        json_file = open( os.path.join( job_working_directory, jobs.TOOL_PROVIDED_JOB_METADATA_FILE ), 'r' )
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
        dataset_collectors = tool.outputs[ name ].dataset_collectors if name in tool.outputs else [ DEFAULT_DATASET_COLLECTOR ]
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
        for filename_index, ( filename, extra_file_collector ) in enumerate( filenames.iteritems() ):
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
                primary_datasets[ name ] = {}
            visible = fields_match.visible
            ext = fields_match.ext
            if ext == "input":
                ext = input_ext
            dbkey = fields_match.dbkey
            # Create new primary dataset
            primary_data = app.model.HistoryDatasetAssociation( extension=ext,
                                                                designation=designation,
                                                                visible=visible,
                                                                dbkey=dbkey,
                                                                create_dataset=True,
                                                                sa_session=sa_session )
            app.security_agent.copy_dataset_permissions( outdata.dataset, primary_data.dataset )
            sa_session.add( primary_data )
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
        directory = job_working_directory
        if extra_file_collector.directory:
            directory = os.path.join( directory, extra_file_collector.directory )
            if not util.in_directory( directory, job_working_directory ):
                raise Exception( "Problem with tool configuration, attempting to pull in datasets from outside working directory." )
        if not os.path.isdir( directory ):
            continue
        for filename in sorted( os.listdir( directory ) ):
            path = os.path.join( directory, filename )
            if not os.path.isfile( path ):
                continue
            if extra_file_collector.match( matchable, filename ):
                yield path, extra_file_collector

# XML can describe custom patterns, but these literals describe named
# patterns that will be replaced.
NAMED_PATTERNS = {
    "__default__": DEFAULT_EXTRA_FILENAME_PATTERN,
    "__name__": r"(?P<name>.*)",
    "__designation__": r"(?P<designation>.*)",
    "__name_and_ext__": r"(?P<name>.*)\.(?P<ext>[^\.]+)?",
    "__designation_and_ext__": r"(?P<designation>.*)\.(?P<ext>[^\._]+)?",
}


def dataset_collectors_from_elem( elem ):
    primary_dataset_elems = elem.findall( "discover_datasets" )
    if not primary_dataset_elems:
        return [ DEFAULT_DATASET_COLLECTOR ]
    else:
        return map( lambda elem: DatasetCollector( **elem.attrib ), primary_dataset_elems )


def dataset_collectors_from_list( discover_datasets_dicts ):
    return map( lambda kwds: DatasetCollector( **kwds ), discover_datasets_dicts )


class DatasetCollector( object ):

    def __init__( self, **kwargs ):
        pattern = kwargs.get( "pattern", "__default__" )
        if pattern in NAMED_PATTERNS:
            pattern = NAMED_PATTERNS.get( pattern )
        self.pattern = pattern
        self.default_dbkey = kwargs.get( "dbkey", None )
        self.default_ext = kwargs.get( "ext", None )
        self.default_visible = util.asbool( kwargs.get( "visible", None ) )
        self.directory = kwargs.get( "directory", None )
        self.assign_primary_output = util.asbool( kwargs.get( 'assign_primary_output', False ) )

    def pattern_for_dataset( self, dataset_instance=None ):
        token_replacement = r'\d+'
        if dataset_instance:
            token_replacement = str( dataset_instance.id )
        return self.pattern.replace( DATASET_ID_TOKEN, token_replacement )

    def match( self, dataset_instance, filename ):
        pattern = self.pattern_for_dataset( dataset_instance )
        re_match = re.match( pattern, filename )
        match_object = None
        if re_match:
            match_object = CollectedDatasetMatch( re_match, self )
        return match_object


class CollectedDatasetMatch( object ):

    def __init__( self, re_match, collector ):
        self.re_match = re_match
        self.collector = collector

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


DEFAULT_DATASET_COLLECTOR = DatasetCollector()

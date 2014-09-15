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
    primary_datasets = {}
    for name, outdata in output.items():
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
            for extra_file_collector in dataset_collectors:
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
                    if extra_file_collector.match( outdata, filename ):
                        filenames[ path ] = extra_file_collector
        for filename, extra_file_collector in filenames.iteritems():
            if not name in primary_datasets:
                primary_datasets[name] = {}
            fields_match = extra_file_collector.match( outdata, os.path.basename( filename ) )
            if not fields_match:
                # Before I guess pop() would just have thrown an IndexError
                raise Exception( "Problem parsing metadata fields for file %s" % filename )
            designation = fields_match.designation
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
            #add tool/metadata provided information
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
                            app.object_store.update_from_file( primary_data.dataset,
                                extra_dir=extra_dir,
                                alt_name=f,
                                file_name=os.path.join( root, f ),
                                create=True,
                                dir_only=True,
                                preserve_symlinks=True
                            )
                    # FIXME: 
                    # since these are placed into the job working dir, let the standard
                    # Galaxy cleanup methods handle this (for now?)
                    # there was an extra_files_path dir, attempt to remove it
                    #shutil.rmtree( extra_files_path_joined )
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
    return primary_datasets


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
        if "designation" in re_match.groupdict():
            return re_match.group( "designation" )
        elif "name" in re_match.groupdict():
            return re_match.group( "name" )
        else:
            return None

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

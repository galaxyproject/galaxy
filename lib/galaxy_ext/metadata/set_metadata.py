"""
Execute an external process to set_meta() on a provided list of pickled datasets.

This was formerly scripts/set_metadata.py and expects these arguments:

    %prog datatypes_conf.xml job_metadata_file metadata_in,metadata_kwds,metadata_out,metadata_results_code,output_filename_override,metadata_override... max_metadata_value_size

Galaxy should be importable on sys.path and output_filename_override should be
set to the path of the dataset on which metadata is being set
(output_filename_override could previously be left empty and the path would be
constructed automatically).
"""

import cPickle
import json
import logging
import os
import sys

# insert *this* galaxy before all others on sys.path
sys.path.insert( 1, os.path.abspath( os.path.join( os.path.dirname( __file__ ), os.pardir, os.pardir ) ) )

from sqlalchemy.orm import clear_mappers

import galaxy.model.mapping  # need to load this before we unpickle, in order to setup properties assigned by the mappers
from galaxy.model.custom_types import total_size
from galaxy.util import stringify_dictionary_keys

# ensure supported version
assert sys.version_info[:2] >= ( 2, 6 ) and sys.version_info[:2] <= ( 2, 7 ), 'Python version must be 2.6 or 2.7, this is: %s' % sys.version

logging.basicConfig()
log = logging.getLogger( __name__ )

galaxy.model.Job()  # this looks REAL stupid, but it is REQUIRED in order for SA to insert parameters into the classes defined by the mappers --> it appears that instantiating ANY mapper'ed class would suffice here


def set_meta_with_tool_provided( dataset_instance, file_dict, set_meta_kwds, datatypes_registry ):
    # This method is somewhat odd, in that we set the metadata attributes from tool,
    # then call set_meta, then set metadata attributes from tool again.
    # This is intentional due to interplay of overwrite kwd, the fact that some metadata
    # parameters may rely on the values of others, and that we are accepting the
    # values provided by the tool as Truth.
    extension = dataset_instance.extension
    if extension == "_sniff_":
        try:
            from galaxy.datatypes import sniff
            extension = sniff.handle_uploaded_dataset_file( dataset_instance.dataset.external_filename, datatypes_registry )
            # We need to both set the extension so it is available to set_meta
            # and record it in the metadata so it can be reloaded on the server
            # side and the model updated (see MetadataCollection.{from,to}_JSON_dict)
            dataset_instance.extension = extension
            # Set special metadata property that will reload this on server side.
            setattr( dataset_instance.metadata, "__extension__", extension )
        except Exception:
            # TODO: log this when metadata can log stuff...
            # https://trello.com/c/Nrwodu9d
            pass

    for metadata_name, metadata_value in file_dict.get( 'metadata', {} ).iteritems():
        setattr( dataset_instance.metadata, metadata_name, metadata_value )
    dataset_instance.datatype.set_meta( dataset_instance, **set_meta_kwds )
    for metadata_name, metadata_value in file_dict.get( 'metadata', {} ).iteritems():
        setattr( dataset_instance.metadata, metadata_name, metadata_value )


def set_metadata():
    # locate galaxy_root for loading datatypes
    galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
    galaxy.datatypes.metadata.MetadataTempFile.tmp_dir = tool_job_working_directory = os.path.abspath(os.getcwd())

    # This is ugly, but to transition from existing jobs without this parameter
    # to ones with, smoothly, it has to be the last optional parameter and we
    # have to sniff it.
    try:
        max_metadata_value_size = int(sys.argv[-1])
        sys.argv = sys.argv[:-1]
    except ValueError:
        max_metadata_value_size = 0
        # max_metadata_value_size is unspecified and should be 0

    # Set up datatypes registry
    datatypes_config = sys.argv.pop( 1 )
    datatypes_registry = galaxy.datatypes.registry.Registry()
    datatypes_registry.load_datatypes( root_dir=galaxy_root, config=datatypes_config )
    galaxy.model.set_datatypes_registry( datatypes_registry )

    job_metadata = sys.argv.pop( 1 )
    existing_job_metadata_dict = {}
    new_job_metadata_dict = {}
    if job_metadata != "None" and os.path.exists( job_metadata ):
        for line in open( job_metadata, 'r' ):
            try:
                line = stringify_dictionary_keys( json.loads( line ) )
                if line['type'] == 'dataset':
                    existing_job_metadata_dict[ line['dataset_id'] ] = line
                elif line['type'] == 'new_primary_dataset':
                    new_job_metadata_dict[ line[ 'filename' ] ] = line
            except:
                continue

    for filenames in sys.argv[1:]:
        fields = filenames.split( ',' )
        filename_in = fields.pop( 0 )
        filename_kwds = fields.pop( 0 )
        filename_out = fields.pop( 0 )
        filename_results_code = fields.pop( 0 )
        dataset_filename_override = fields.pop( 0 )
        # Need to be careful with the way that these parameters are populated from the filename splitting,
        # because if a job is running when the server is updated, any existing external metadata command-lines
        # will not have info about the newly added override_metadata file
        if fields:
            override_metadata = fields.pop( 0 )
        else:
            override_metadata = None
        set_meta_kwds = stringify_dictionary_keys( json.load( open( filename_kwds ) ) )  # load kwds; need to ensure our keywords are not unicode
        try:
            dataset = cPickle.load( open( filename_in ) )  # load DatasetInstance
            dataset.dataset.external_filename = dataset_filename_override
            files_path = os.path.abspath(os.path.join( tool_job_working_directory, "dataset_%s_files" % (dataset.dataset.id) ))
            dataset.dataset.external_extra_files_path = files_path
            if dataset.dataset.id in existing_job_metadata_dict:
                dataset.extension = existing_job_metadata_dict[ dataset.dataset.id ].get( 'ext', dataset.extension )
            # Metadata FileParameter types may not be writable on a cluster node, and are therefore temporarily substituted with MetadataTempFiles
            if override_metadata:
                override_metadata = json.load( open( override_metadata ) )
                for metadata_name, metadata_file_override in override_metadata:
                    if galaxy.datatypes.metadata.MetadataTempFile.is_JSONified_value( metadata_file_override ):
                        metadata_file_override = galaxy.datatypes.metadata.MetadataTempFile.from_JSON( metadata_file_override )
                    setattr( dataset.metadata, metadata_name, metadata_file_override )
            file_dict = existing_job_metadata_dict.get( dataset.dataset.id, {} )
            set_meta_with_tool_provided( dataset, file_dict, set_meta_kwds, datatypes_registry )
            if max_metadata_value_size:
                for k, v in dataset.metadata.items():
                    if total_size(v) > max_metadata_value_size:
                        log.info("Key %s too large for metadata, discarding" % k)
                        dataset.metadata.remove_key(k)
            dataset.metadata.to_JSON_dict( filename_out )  # write out results of set_meta
            json.dump( ( True, 'Metadata has been set successfully' ), open( filename_results_code, 'wb+' ) )  # setting metadata has succeeded
        except Exception as e:
            json.dump( ( False, str( e ) ), open( filename_results_code, 'wb+' ) )  # setting metadata has failed somehow

    for i, ( filename, file_dict ) in enumerate( new_job_metadata_dict.iteritems(), start=1 ):
        new_dataset_filename = os.path.join( tool_job_working_directory, "working", file_dict[ 'filename' ] )
        new_dataset = galaxy.model.Dataset( id=-i, external_filename=new_dataset_filename )
        extra_files = file_dict.get( 'extra_files', None )
        if extra_files is not None:
            new_dataset._extra_files_path = os.path.join( tool_job_working_directory, "working", extra_files )
        new_dataset.state = new_dataset.states.OK
        new_dataset_instance = galaxy.model.HistoryDatasetAssociation( id=-i, dataset=new_dataset, extension=file_dict.get( 'ext', 'data' ) )
        set_meta_with_tool_provided( new_dataset_instance, file_dict, set_meta_kwds, datatypes_registry )
        file_dict[ 'metadata' ] = json.loads( new_dataset_instance.metadata.to_JSON_dict() )  # storing metadata in external form, need to turn back into dict, then later jsonify
    if existing_job_metadata_dict or new_job_metadata_dict:
        with open( job_metadata, 'wb' ) as job_metadata_fh:
            for value in existing_job_metadata_dict.values() + new_job_metadata_dict.values():
                job_metadata_fh.write( "%s\n" % ( json.dumps( value ) ) )

    clear_mappers()

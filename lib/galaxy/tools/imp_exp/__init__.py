import datetime
import json
import logging
import os
import shutil
import tempfile
from json import dumps, loads

from sqlalchemy.orm import eagerload, eagerload_all
from sqlalchemy.sql import expression

from galaxy import model
from galaxy.exceptions import MalformedContents
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.web.framework.helpers import to_unicode

log = logging.getLogger(__name__)


class JobImportHistoryArchiveWrapper( object, UsesAnnotations ):
    """
        Class provides support for performing jobs that import a history from
        an archive.
    """
    def __init__( self, app, job_id ):
        self.app = app
        self.job_id = job_id
        self.sa_session = self.app.model.context

    def cleanup_after_job( self ):
        """ Set history, datasets, and jobs' attributes and clean up archive directory. """

        #
        # Helper methods.
        #

        def file_in_dir( file_path, a_dir ):
            """ Returns true if file is in directory. """
            abs_file_path = os.path.abspath( file_path )
            return os.path.split( abs_file_path )[0] == a_dir

        def read_file_contents( file_path ):
            """ Read contents of a file. """
            fp = open( file_path, 'rb' )
            buffsize = 1048576
            file_contents = ''
            try:
                while True:
                    file_contents += fp.read( buffsize )
                    if not file_contents or len( file_contents ) % buffsize != 0:
                        break
            except OverflowError:
                pass
            fp.close()
            return file_contents

        def get_tag_str( tag, value ):
            """ Builds a tag string for a tag, value pair. """
            if not value:
                return tag
            else:
                return tag + ":" + value

        #
        # Import history.
        #

        jiha = self.sa_session.query( model.JobImportHistoryArchive ).filter_by( job_id=self.job_id ).first()
        if jiha:
            try:
                archive_dir = jiha.archive_dir
                user = jiha.job.user

                #
                # Create history.
                #
                history_attr_file_name = os.path.join( archive_dir, 'history_attrs.txt')
                history_attr_str = read_file_contents( history_attr_file_name )
                history_attrs = loads( history_attr_str )

                # Create history.
                new_history = model.History( name='imported from archive: %s' % history_attrs['name'].encode( 'utf-8' ),
                                             user=user )
                new_history.importing = True
                new_history.hid_counter = history_attrs['hid_counter']
                new_history.genome_build = history_attrs['genome_build']
                self.sa_session.add( new_history )
                jiha.history = new_history
                self.sa_session.flush()

                # Add annotation, tags.
                if user:
                    self.add_item_annotation( self.sa_session, user, new_history, history_attrs[ 'annotation' ] )
                    """
                    TODO: figure out to how add tags to item.
                    for tag, value in history_attrs[ 'tags' ].items():
                        trans.app.tag_handler.apply_item_tags( trans, trans.user, new_history, get_tag_str( tag, value ) )
                    """

                #
                # Create datasets.
                #
                datasets_attrs_file_name = os.path.join( archive_dir, 'datasets_attrs.txt')
                datasets_attr_str = read_file_contents( datasets_attrs_file_name )
                datasets_attrs = loads( datasets_attr_str )

                if os.path.exists( datasets_attrs_file_name + ".provenance" ):
                    provenance_attr_str = read_file_contents( datasets_attrs_file_name + ".provenance" )
                    provenance_attrs = loads( provenance_attr_str )
                    datasets_attrs += provenance_attrs

                # Get counts of how often each dataset file is used; a file can
                # be linked to multiple dataset objects (HDAs).
                datasets_usage_counts = {}
                for dataset_attrs in datasets_attrs:
                    temp_dataset_file_name = \
                        os.path.abspath( os.path.join( archive_dir, dataset_attrs['file_name'] ) )
                    if ( temp_dataset_file_name not in datasets_usage_counts ):
                        datasets_usage_counts[ temp_dataset_file_name ] = 0
                    datasets_usage_counts[ temp_dataset_file_name ] += 1

                # Create datasets.
                for dataset_attrs in datasets_attrs:
                    metadata = dataset_attrs['metadata']

                    # Create dataset and HDA.
                    hda = model.HistoryDatasetAssociation( name=dataset_attrs['name'].encode( 'utf-8' ),
                                                           extension=dataset_attrs['extension'],
                                                           info=dataset_attrs['info'].encode( 'utf-8' ),
                                                           blurb=dataset_attrs['blurb'],
                                                           peek=dataset_attrs['peek'],
                                                           designation=dataset_attrs['designation'],
                                                           visible=dataset_attrs['visible'],
                                                           dbkey=metadata['dbkey'],
                                                           metadata=metadata,
                                                           history=new_history,
                                                           create_dataset=True,
                                                           sa_session=self.sa_session )
                    if 'uuid' in dataset_attrs:
                        hda.dataset.uuid = dataset_attrs["uuid"]
                    if dataset_attrs.get('exported', True) is False:
                        hda.state = hda.states.DISCARDED
                        hda.deleted = True
                        hda.purged = True
                    else:
                        hda.state = hda.states.OK
                    self.sa_session.add( hda )
                    self.sa_session.flush()
                    new_history.add_dataset( hda, genome_build=None )
                    hda.hid = dataset_attrs['hid']  # Overwrite default hid set when HDA added to history.
                    # TODO: Is there a way to recover permissions? Is this needed?
                    # permissions = trans.app.security_agent.history_get_default_permissions( new_history )
                    # trans.app.security_agent.set_all_dataset_permissions( hda.dataset, permissions )
                    self.sa_session.flush()
                    if dataset_attrs.get('exported', True) is True:
                        # Do security check and move/copy dataset data.
                        temp_dataset_file_name = \
                            os.path.realpath( os.path.abspath( os.path.join( archive_dir, dataset_attrs['file_name'] ) ) )
                        if not file_in_dir( temp_dataset_file_name, os.path.join( archive_dir, "datasets" ) ):
                            raise MalformedContents( "Invalid dataset path: %s" % temp_dataset_file_name )
                        if datasets_usage_counts[ temp_dataset_file_name ] == 1:
                            self.app.object_store.update_from_file( hda.dataset, file_name=temp_dataset_file_name, create=True )

                            # Import additional files if present. Histories exported previously might not have this attribute set.
                            dataset_extra_files_path = dataset_attrs.get( 'extra_files_path', None )
                            if dataset_extra_files_path:
                                try:
                                    file_list = os.listdir( os.path.join( archive_dir, dataset_extra_files_path ) )
                                except OSError:
                                    file_list = []

                                if file_list:
                                    for extra_file in file_list:
                                        self.app.object_store.update_from_file(
                                            hda.dataset, extra_dir='dataset_%s_files' % hda.dataset.id,
                                            alt_name=extra_file, file_name=os.path.join( archive_dir, dataset_extra_files_path, extra_file ),
                                            create=True )
                        else:
                            datasets_usage_counts[ temp_dataset_file_name ] -= 1
                            shutil.copyfile( temp_dataset_file_name, hda.file_name )
                        hda.dataset.set_total_size()  # update the filesize record in the database

                    # Set tags, annotations.
                    if user:
                        self.add_item_annotation( self.sa_session, user, hda, dataset_attrs[ 'annotation' ] )
                        # TODO: Set tags.
                        """
                        for tag, value in dataset_attrs[ 'tags' ].items():
                            trans.app.tag_handler.apply_item_tags( trans, trans.user, hda, get_tag_str( tag, value ) )
                            self.sa_session.flush()
                        """

                    # Although metadata is set above, need to set metadata to recover BAI for BAMs.
                    if hda.extension == 'bam':
                        self.app.datatypes_registry.set_external_metadata_tool.tool_action.execute_via_app(
                            self.app.datatypes_registry.set_external_metadata_tool, self.app, jiha.job.session_id,
                            new_history.id, jiha.job.user, incoming={ 'input1': hda }, overwrite=False
                        )

                #
                # Create jobs.
                #

                # Read jobs attributes.
                jobs_attr_file_name = os.path.join( archive_dir, 'jobs_attrs.txt')
                jobs_attr_str = read_file_contents( jobs_attr_file_name )

                # Decode jobs attributes.
                def as_hda( obj_dct ):
                    """ Hook to 'decode' an HDA; method uses history and HID to get the HDA represented by
                        the encoded object. This only works because HDAs are created above. """
                    if obj_dct.get( '__HistoryDatasetAssociation__', False ):
                            return self.sa_session.query( model.HistoryDatasetAssociation
                                                          ).filter_by( history=new_history, hid=obj_dct['hid'] ).first()
                    return obj_dct
                jobs_attrs = loads( jobs_attr_str, object_hook=as_hda )

                # Create each job.
                for job_attrs in jobs_attrs:
                    imported_job = model.Job()
                    imported_job.user = user
                    # TODO: set session?
                    # imported_job.session = trans.get_galaxy_session().id
                    imported_job.history = new_history
                    imported_job.imported = True
                    imported_job.tool_id = job_attrs[ 'tool_id' ]
                    imported_job.tool_version = job_attrs[ 'tool_version' ]
                    imported_job.set_state( job_attrs[ 'state' ] )
                    imported_job.info = job_attrs.get('info', None)
                    imported_job.exit_code = job_attrs.get('exit_code', None)
                    imported_job.traceback = job_attrs.get('traceback', None)
                    imported_job.stdout = job_attrs.get('stdout', None)
                    imported_job.stderr = job_attrs.get('stderr', None)
                    imported_job.command_line = job_attrs.get('command_line', None)
                    try:
                        imported_job.create_time = datetime.datetime.strptime(job_attrs["create_time"], "%Y-%m-%dT%H:%M:%S.%f")
                        imported_job.update_time = datetime.datetime.strptime(job_attrs["update_time"], "%Y-%m-%dT%H:%M:%S.%f")
                    except:
                        pass
                    self.sa_session.add( imported_job )
                    self.sa_session.flush()

                    class HistoryDatasetAssociationIDEncoder( json.JSONEncoder ):
                        """ Custom JSONEncoder for a HistoryDatasetAssociation that encodes an HDA as its ID. """
                        def default( self, obj ):
                            """ Encode an HDA, default encoding for everything else. """
                            if isinstance( obj, model.HistoryDatasetAssociation ):
                                return obj.id
                            return json.JSONEncoder.default( self, obj )

                    # Set parameters. May be useful to look at metadata.py for creating parameters.
                    # TODO: there may be a better way to set parameters, e.g.:
                    #   for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
                    #       job.add_parameter( name, value )
                    # to make this work, we'd need to flesh out the HDA objects. The code below is
                    # relatively similar.
                    for name, value in job_attrs[ 'params' ].items():
                        # Transform parameter values when necessary.
                        if isinstance( value, model.HistoryDatasetAssociation ):
                            # HDA input: use hid to find input.
                            input_hda = self.sa_session.query( model.HistoryDatasetAssociation ) \
                                            .filter_by( history=new_history, hid=value.hid ).first()
                            value = input_hda.id
                        # print "added parameter %s-->%s to job %i" % ( name, value, imported_job.id )
                        imported_job.add_parameter( name, dumps( value, cls=HistoryDatasetAssociationIDEncoder ) )

                    # TODO: Connect jobs to input datasets.

                    # Connect jobs to output datasets.
                    for output_hid in job_attrs[ 'output_datasets' ]:
                        # print "%s job has output dataset %i" % (imported_job.id, output_hid)
                        output_hda = self.sa_session.query( model.HistoryDatasetAssociation
                                                            ).filter_by(history=new_history, hid=output_hid ).first()
                        if output_hda:
                            imported_job.add_output_dataset( output_hda.name, output_hda )

                    # Connect jobs to input datasets.
                    if 'input_mapping' in job_attrs:
                        for input_name, input_hid in job_attrs[ 'input_mapping' ].items():
                            input_hda = self.sa_session.query( model.HistoryDatasetAssociation ) \
                                            .filter_by( history=new_history, hid=input_hid ).first()
                            if input_hda:
                                imported_job.add_input_dataset( input_name, input_hda )

                    self.sa_session.flush()

                # Done importing.
                new_history.importing = False
                self.sa_session.flush()

                # Cleanup.
                if os.path.exists( archive_dir ):
                    shutil.rmtree( archive_dir )
            except Exception as e:
                jiha.job.stderr += "Error cleaning up history import job: %s" % e
                self.sa_session.flush()
                raise


class JobExportHistoryArchiveWrapper( object, UsesAnnotations ):
    """
    Class provides support for performing jobs that export a history to an
    archive.
    """
    def __init__( self, job_id ):
        self.job_id = job_id

    def get_history_datasets( self, trans, history ):
        """
        Returns history's datasets.
        """
        query = ( trans.sa_session.query( trans.model.HistoryDatasetAssociation )
                  .filter( trans.model.HistoryDatasetAssociation.history == history )
                  .options( eagerload( "children" ) )
                  .join( "dataset" )
                  .options( eagerload_all( "dataset.actions" ) )
                  .order_by( trans.model.HistoryDatasetAssociation.hid )
                  .filter( trans.model.HistoryDatasetAssociation.deleted == expression.false() )
                  .filter( trans.model.Dataset.purged == expression.false() ) )
        return query.all()

    # TODO: should use db_session rather than trans in this method.
    def setup_job( self, trans, jeha, include_hidden=False, include_deleted=False ):
        """ Perform setup for job to export a history into an archive. Method generates
            attribute files for export, sets the corresponding attributes in the jeha
            object, and returns a command line for running the job. The command line
            includes the command, inputs, and options; it does not include the output
            file because it must be set at runtime. """

        #
        # Helper methods/classes.
        #

        def get_item_tag_dict( item ):
            """ Create dictionary of an item's tags. """
            tags = {}
            for tag in item.tags:
                tag_user_tname = to_unicode( tag.user_tname )
                tag_user_value = to_unicode( tag.user_value )
                tags[ tag_user_tname ] = tag_user_value
            return tags

        def prepare_metadata( metadata ):
            """ Prepare metatdata for exporting. """
            for name, value in list(metadata.items()):
                # Metadata files are not needed for export because they can be
                # regenerated.
                if isinstance( value, trans.app.model.MetadataFile ):
                    del metadata[ name ]
            return metadata

        class HistoryDatasetAssociationEncoder( json.JSONEncoder ):
            """ Custom JSONEncoder for a HistoryDatasetAssociation. """
            def default( self, obj ):
                """ Encode an HDA, default encoding for everything else. """
                if isinstance( obj, trans.app.model.HistoryDatasetAssociation ):
                    rval = {
                        "__HistoryDatasetAssociation__": True,
                        "create_time": obj.create_time.__str__(),
                        "update_time": obj.update_time.__str__(),
                        "hid": obj.hid,
                        "name": to_unicode( obj.name ),
                        "info": to_unicode( obj.info ),
                        "blurb": obj.blurb,
                        "peek": obj.peek,
                        "extension": obj.extension,
                        "metadata": prepare_metadata( dict( obj.metadata.items() ) ),
                        "parent_id": obj.parent_id,
                        "designation": obj.designation,
                        "deleted": obj.deleted,
                        "visible": obj.visible,
                        "file_name": obj.file_name,
                        "uuid": ( lambda uuid: str( uuid ) if uuid else None )( obj.dataset.uuid ),
                        "annotation": to_unicode( getattr( obj, 'annotation', '' ) ),
                        "tags": get_item_tag_dict( obj ),
                        "extra_files_path": obj.extra_files_path
                    }
                    if not obj.visible and not include_hidden:
                        rval['exported'] = False
                    elif obj.deleted and not include_deleted:
                        rval['exported'] = False
                    else:
                        rval['exported'] = True
                    return rval
                return json.JSONEncoder.default( self, obj )

        #
        # Create attributes/metadata files for export.
        #
        temp_output_dir = tempfile.mkdtemp()

        # Write history attributes to file.
        history = jeha.history
        history_attrs = {
            "create_time": history.create_time.__str__(),
            "update_time": history.update_time.__str__(),
            "name": to_unicode( history.name ),
            "hid_counter": history.hid_counter,
            "genome_build": history.genome_build,
            "annotation": to_unicode( self.get_item_annotation_str( trans.sa_session, history.user, history ) ),
            "tags": get_item_tag_dict( history ),
            "includes_hidden_datasets": include_hidden,
            "includes_deleted_datasets": include_deleted
        }
        history_attrs_filename = tempfile.NamedTemporaryFile( dir=temp_output_dir ).name
        history_attrs_out = open( history_attrs_filename, 'w' )
        history_attrs_out.write( dumps( history_attrs ) )
        history_attrs_out.close()
        jeha.history_attrs_filename = history_attrs_filename

        # Write datasets' attributes to file.
        datasets = self.get_history_datasets( trans, history )
        included_datasets = []
        datasets_attrs = []
        provenance_attrs = []
        for dataset in datasets:
            dataset.annotation = self.get_item_annotation_str( trans.sa_session, history.user, dataset )
            if (not dataset.visible and not include_hidden) or (dataset.deleted and not include_deleted):
                provenance_attrs.append( dataset )
            else:
                datasets_attrs.append( dataset )
                included_datasets.append( dataset )
        datasets_attrs_filename = tempfile.NamedTemporaryFile( dir=temp_output_dir ).name
        datasets_attrs_out = open( datasets_attrs_filename, 'w' )
        datasets_attrs_out.write( dumps( datasets_attrs, cls=HistoryDatasetAssociationEncoder ) )
        datasets_attrs_out.close()
        jeha.datasets_attrs_filename = datasets_attrs_filename

        provenance_attrs_out = open( datasets_attrs_filename + ".provenance", 'w' )
        provenance_attrs_out.write( dumps( provenance_attrs, cls=HistoryDatasetAssociationEncoder ) )
        provenance_attrs_out.close()

        #
        # Write jobs attributes file.
        #

        # Get all jobs associated with included HDAs.
        jobs_dict = {}
        for hda in included_datasets:
            # Get the associated job, if any. If this hda was copied from another,
            # we need to find the job that created the origial hda
            job_hda = hda
            while job_hda.copied_from_history_dataset_association:  # should this check library datasets as well?
                job_hda = job_hda.copied_from_history_dataset_association
            if not job_hda.creating_job_associations:
                # No viable HDA found.
                continue

            # Get the job object.
            job = None
            for assoc in job_hda.creating_job_associations:
                job = assoc.job
                break
            if not job:
                # No viable job.
                continue

            jobs_dict[ job.id ] = job

        # Get jobs' attributes.
        jobs_attrs = []
        for id, job in jobs_dict.items():
            job_attrs = {}
            job_attrs[ 'tool_id' ] = job.tool_id
            job_attrs[ 'tool_version' ] = job.tool_version
            job_attrs[ 'state' ] = job.state
            job_attrs[ 'info' ] = job.info
            job_attrs[ 'traceback' ] = job.traceback
            job_attrs[ 'command_line' ] = job.command_line
            job_attrs[ 'stderr' ] = job.stderr
            job_attrs[ 'stdout' ] = job.stdout
            job_attrs[ 'exit_code' ] = job.exit_code
            job_attrs[ 'create_time' ] = job.create_time.isoformat()
            job_attrs[ 'update_time' ] = job.update_time.isoformat()

            # Get the job's parameters
            try:
                params_objects = job.get_param_values( trans.app )
            except:
                # Could not get job params.
                continue

            params_dict = {}
            for name, value in params_objects.items():
                params_dict[ name ] = value
            job_attrs[ 'params' ] = params_dict

            # -- Get input, output datasets. --

            input_datasets = []
            input_mapping = {}
            for assoc in job.input_datasets:
                # Optional data inputs will not have a dataset.
                if assoc.dataset:
                    input_datasets.append( assoc.dataset.hid )
                    input_mapping[assoc.name] = assoc.dataset.hid
            job_attrs[ 'input_datasets' ] = input_datasets
            job_attrs[ 'input_mapping'] = input_mapping
            output_datasets = [ assoc.dataset.hid for assoc in job.output_datasets ]
            job_attrs[ 'output_datasets' ] = output_datasets

            jobs_attrs.append( job_attrs )

        jobs_attrs_filename = tempfile.NamedTemporaryFile( dir=temp_output_dir ).name
        jobs_attrs_out = open( jobs_attrs_filename, 'w' )
        jobs_attrs_out.write( dumps( jobs_attrs, cls=HistoryDatasetAssociationEncoder ) )
        jobs_attrs_out.close()
        jeha.jobs_attrs_filename = jobs_attrs_filename

        #
        # Create and return command line for running tool.
        #
        options = ""
        if jeha.compressed:
            options = "-G"
        return "%s %s %s %s" % ( options, history_attrs_filename,
                                 datasets_attrs_filename,
                                 jobs_attrs_filename )

    def cleanup_after_job( self, db_session ):
        """ Remove temporary directory and attribute files generated during setup for this job. """
        # Get jeha for job.
        jeha = db_session.query( model.JobExportHistoryArchive ).filter_by( job_id=self.job_id ).first()
        if jeha:
            for filename in [ jeha.history_attrs_filename, jeha.datasets_attrs_filename, jeha.jobs_attrs_filename ]:
                try:
                    os.remove( filename )
                except Exception as e:
                    log.debug( 'Failed to cleanup attributes file (%s): %s' % ( filename, e ) )
            temp_dir = os.path.split( jeha.history_attrs_filename )[0]
            try:
                shutil.rmtree( temp_dir )
            except Exception as e:
                log.debug( 'Error deleting directory containing attribute files (%s): %s' % ( temp_dir, e ) )

import os, shutil, logging, tempfile, simplejson
from galaxy import model
from galaxy.web.framework.helpers import to_unicode
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util.json import to_json_string
from galaxy.web.base.controller import UsesHistory

log = logging.getLogger(__name__)

def load_history_imp_exp_tools( toolbox ):
    """ Adds tools for importing/exporting histories to archives. """
    # Use same process as that used in load_external_metadata_tool; see that 
    # method for why create tool description files on the fly.
    tool_xml_text = """
        <tool id="__EXPORT_HISTORY__" name="Export History" version="0.1" tool_type="export_history">
          <type class="ExportHistoryTool" module="galaxy.tools"/>
          <action module="galaxy.tools.actions.history_imp_exp" class="ExportHistoryToolAction"/>
          <command>$__SET_EXPORT_HISTORY_COMMAND_LINE__</command>
          <inputs>
            <param name="__HISTORY_TO_EXPORT__" type="hidden"/>
            <param name="compress" type="boolean"/>
            <param name="__SET_EXPORT_HISTORY_COMMAND_LINE__" type="hidden"/>
          </inputs>
        </tool>
        """
    tmp_name = tempfile.NamedTemporaryFile()
    tmp_name.write( tool_xml_text )
    tmp_name.flush()
    history_exp_tool = toolbox.load_tool( tmp_name.name )
    toolbox.tools_by_id[ history_exp_tool.id ] = history_exp_tool
    log.debug( "Loaded history export tool: %s", history_exp_tool.id )

class JobExportHistoryArchiveWrapper( object, UsesHistory, UsesAnnotations ):
    """ Class provides support for performing jobs that export a history to an archive. """
    def __init__( self, job_id ):
        self.job_id = job_id
        
    # TODO: should use db_session rather than trans in this method.
    def setup_job( self, trans, jeha, include_hidden=False, include_deleted=False ):
        # jeha = job_export_history_archive for the job.
        """ Perform setup for job to export a history into an archive. Method generates 
            attribute files for export, sets the corresponding attributes in the jeha
            object, and returns a command line for running the job. """
            
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
            
        class HistoryDatasetAssociationEncoder( simplejson.JSONEncoder ):
            """ Custom JSONEncoder for a HistoryDatasetAssociation. """
            def default( self, obj ):
                """ Encode an HDA, default encoding for everything else. """
                if isinstance( obj, trans.app.model.HistoryDatasetAssociation ):
                    return {
                        "__HistoryDatasetAssociation__" : True,
                        "create_time" : obj.create_time.__str__(),
                        "update_time" : obj.update_time.__str__(),
                        "hid" : obj.hid,
                        "name" : to_unicode( obj.name ),
                        "info" : to_unicode( obj.info ),
                        "blurb" : obj.blurb,
                        "peek" : obj.peek,
                        "extension" : obj.extension,
                        "metadata" : dict( obj.metadata.items() ),
                        "parent_id" : obj.parent_id,
                        "designation" : obj.designation,
                        "deleted" : obj.deleted,
                        "visible" : obj.visible,
                        "file_name" : obj.file_name,
                        "annotation" : to_unicode( getattr( obj, 'annotation', '' ) ),
                        "tags" : get_item_tag_dict( obj ),
                    }       
                return simplejson.JSONEncoder.default( self, obj )
        
        #
        # Create attributes/metadata files for export.
        #   
        temp_output_dir = tempfile.mkdtemp()
    
        # Write history attributes to file.
        history = jeha.history
        history_attrs = {
            "create_time" : history.create_time.__str__(),
            "update_time" : history.update_time.__str__(),
            "name" : to_unicode( history.name ),
            "hid_counter" : history.hid_counter,
            "genome_build" : history.genome_build,
            "annotation" : to_unicode( self.get_item_annotation_str( trans.sa_session, history.user, history ) ),
            "tags" : get_item_tag_dict( history ),
            "includes_hidden_datasets" : include_hidden,
            "includes_deleted_datasets" : include_deleted
        }
        history_attrs_filename = tempfile.NamedTemporaryFile( dir=temp_output_dir ).name
        history_attrs_out = open( history_attrs_filename, 'w' )
        history_attrs_out.write( to_json_string( history_attrs ) )
        history_attrs_out.close()
        jeha.history_attrs_filename = history_attrs_filename
                            
        # Write datasets' attributes to file.
        datasets = self.get_history_datasets( trans, history )
        included_datasets = []
        datasets_attrs = []
        for dataset in datasets:
            if not dataset.visible and not include_hidden:
                continue
            if dataset.deleted and not include_deleted:
                continue
            dataset.annotation = self.get_item_annotation_str( trans.sa_session, history.user, dataset )
            datasets_attrs.append( dataset )
            included_datasets.append( dataset )
        datasets_attrs_filename = tempfile.NamedTemporaryFile( dir=temp_output_dir ).name
        datasets_attrs_out = open( datasets_attrs_filename, 'w' )
        datasets_attrs_out.write( to_json_string( datasets_attrs, cls=HistoryDatasetAssociationEncoder ) )
        datasets_attrs_out.close()
        jeha.datasets_attrs_filename = datasets_attrs_filename

        #
        # Write jobs attributes file.
        #

        # Get all jobs associated with included HDAs.
        jobs_dict = {}
        for hda in included_datasets:
            # Get the associated job, if any. If this hda was copied from another,
            # we need to find the job that created the origial hda
            job_hda = hda
            while job_hda.copied_from_history_dataset_association: #should this check library datasets as well?
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
    
            # Get input, output datasets.
            input_datasets = [ assoc.dataset.hid for assoc in job.input_datasets ]
            job_attrs[ 'input_datasets' ] = input_datasets
            output_datasets = [ assoc.dataset.hid for assoc in job.output_datasets ]
            job_attrs[ 'output_datasets' ] = output_datasets
    
            jobs_attrs.append( job_attrs )
    
        jobs_attrs_filename = tempfile.NamedTemporaryFile( dir=temp_output_dir ).name
        jobs_attrs_out = open( jobs_attrs_filename, 'w' )
        jobs_attrs_out.write( to_json_string( jobs_attrs, cls=HistoryDatasetAssociationEncoder ) )
        jobs_attrs_out.close()
        jeha.jobs_attrs_filename = jobs_attrs_filename
        
        #
        # Create and return command line for running tool.
        #
        options = ""
        if jeha.compressed:
            options = "-G"
        return "%s %s %s %s %s %s" % ( os.path.join( os.path.abspath( os.getcwd() ), "export_history.sh" ), \
                                       options, history_attrs_filename, datasets_attrs_filename, \
                                       jobs_attrs_filename, jeha.dataset.file_name )
                                    
    def cleanup_after_job( self, db_session ):
        """ Remove temporary directory and attribute files generated during setup for this job. """
        # Get jeha for job.
        jeha = db_session.query( model.JobExportHistoryArchive ).filter_by( job_id=self.job_id ).first()
        if jeha:
            for filename in [ jeha.history_attrs_filename, jeha.datasets_attrs_filename, jeha.jobs_attrs_filename ]:
                try:
                    os.remove( filename )
                except Exception, e:
                    log.debug( 'Failed to cleanup attributes file (%s): %s' % ( filename, e ) )
            temp_dir = os.path.split( jeha.history_attrs_filename )[0]
            try:
                shutil.rmtree( temp_dir )
            except Exception, e:
                log.debug( 'Error deleting directory containing attribute files (%s): %s' % ( temp_dir, e ) )
                
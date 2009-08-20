from __init__ import ToolAction
from galaxy.datatypes.metadata import JobExternalOutputMetadataWrapper

import logging
log = logging.getLogger( __name__ )

class SetMetadataToolAction( ToolAction ):
    """Tool action used for setting external metadata on an existing dataset"""
    
    def execute( self, tool, trans, incoming = {}, set_output_hid = False ):
        for name, value in incoming.iteritems():
            if isinstance( value, trans.app.model.HistoryDatasetAssociation ):
                dataset = value
                dataset_name = name
                break
            else:
                raise Exception( 'The dataset to set metadata on could not be determined.' )
                                
        # Create the job object
        job = trans.app.model.Job()
        job.session_id = trans.get_galaxy_session().id
        job.history_id = trans.history.id
        job.tool_id = tool.id
        try:
            # For backward compatibility, some tools may not have versions yet.
            job.tool_version = tool.version
        except:
            job.tool_version = "1.0.0"
        job.flush() #ensure job.id is available
        
        #add parameters to job_parameter table
        incoming[ '__ORIGINAL_DATASET_STATE__' ] = dataset.state #store original dataset state, so we can restore it. A seperate table might be better (no chance of 'loosing' the original state)? 
        external_metadata_wrapper = JobExternalOutputMetadataWrapper( job )
        cmd_line = external_metadata_wrapper.setup_external_metadata( dataset, exec_dir = None, tmp_dir = trans.app.config.new_file_path, dataset_files_path = trans.app.model.Dataset.file_path, output_fnames = None, config_root = None, datatypes_config = None, kwds = { 'overwrite' : True } )
        incoming[ '__SET_EXTERNAL_METADATA_COMMAND_LINE__' ] = cmd_line
        for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
            job.add_parameter( name, value )
        #add the dataset to job_to_input_dataset table
        job.add_input_dataset( dataset_name, dataset )
        #Need a special state here to show that metadata is being set and also allow the job to run
        #   i.e. if state was set to 'running' the set metadata job would never run, as it would wait for input (the dataset to set metadata on) to be in a ready state
        dataset.state = dataset.states.SETTING_METADATA
        trans.app.model.flush()
        
        # Queue the job for execution
        trans.app.job_queue.put( job.id, tool )
        trans.log_event( "Added set external metadata job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
        return []

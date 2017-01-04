import logging
from json import dumps

from galaxy.datatypes.metadata import JobExternalOutputMetadataWrapper
from galaxy.jobs.datasets import DatasetPath
from galaxy.util.odict import odict

from . import ToolAction

log = logging.getLogger( __name__ )


class SetMetadataToolAction( ToolAction ):
    """Tool action used for setting external metadata on an existing dataset"""

    def execute( self, tool, trans, incoming={}, set_output_hid=False, overwrite=True, history=None, job_params=None, **kwargs ):
        """
        Execute using a web transaction.
        """
        job, odict = self.execute_via_app( tool, trans.app, trans.get_galaxy_session().id,
                                           trans.history.id, trans.user, incoming, set_output_hid,
                                           overwrite, history, job_params )
        # FIXME: can remove this when logging in execute_via_app method.
        trans.log_event( "Added set external metadata job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
        return job, odict

    def execute_via_app( self, tool, app, session_id, history_id, user=None,
                         incoming={}, set_output_hid=False, overwrite=True,
                         history=None, job_params=None ):
        """
        Execute using application.
        """
        for name, value in incoming.items():
            if isinstance( value, app.model.HistoryDatasetAssociation ):
                dataset = value
                dataset_name = name
                type = 'hda'
                break
            elif isinstance( value, app.model.LibraryDatasetDatasetAssociation ):
                dataset = value
                dataset_name = name
                type = 'ldda'
                break
            else:
                raise Exception( 'The dataset to set metadata on could not be determined.' )

        sa_session = app.model.context

        # Create the job object
        job = app.model.Job()
        job.session_id = session_id
        job.history_id = history_id
        job.tool_id = tool.id
        if user:
            job.user_id = user.id
        if job_params:
            job.params = dumps( job_params )
        start_job_state = job.state  # should be job.states.NEW
        try:
            # For backward compatibility, some tools may not have versions yet.
            job.tool_version = tool.version
        except:
            job.tool_version = "1.0.1"
        job.state = job.states.WAITING  # we need to set job state to something other than NEW, or else when tracking jobs in db it will be picked up before we have added input / output parameters
        job.set_handler(tool.get_job_handler( job_params ))
        sa_session.add( job )
        sa_session.flush()  # ensure job.id is available

        # add parameters to job_parameter table
        # Store original dataset state, so we can restore it. A separate table might be better (no chance of 'losing' the original state)?
        incoming[ '__ORIGINAL_DATASET_STATE__' ] = dataset.state
        input_paths = [DatasetPath( dataset.id, real_path=dataset.file_name, mutable=False )]
        app.object_store.create(job, base_dir='job_work', dir_only=True, extra_dir=str(job.id))
        job_working_dir = app.object_store.get_filename(job, base_dir='job_work', dir_only=True, extra_dir=str(job.id))
        external_metadata_wrapper = JobExternalOutputMetadataWrapper( job )
        cmd_line = external_metadata_wrapper.setup_external_metadata( dataset,
                                                                      sa_session,
                                                                      exec_dir=None,
                                                                      tmp_dir=job_working_dir,
                                                                      dataset_files_path=app.model.Dataset.file_path,
                                                                      output_fnames=input_paths,
                                                                      config_root=app.config.root,
                                                                      config_file=app.config.config_file,
                                                                      datatypes_config=app.datatypes_registry.integrated_datatypes_configs,
                                                                      job_metadata=None,
                                                                      include_command=False,
                                                                      max_metadata_value_size=app.config.max_metadata_value_size,
                                                                      kwds={ 'overwrite' : overwrite } )
        incoming[ '__SET_EXTERNAL_METADATA_COMMAND_LINE__' ] = cmd_line
        for name, value in tool.params_to_strings( incoming, app ).items():
            job.add_parameter( name, value )
        # add the dataset to job_to_input_dataset table
        if type == 'hda':
            job.add_input_dataset( dataset_name, dataset )
        elif type == 'ldda':
            job.add_input_library_dataset( dataset_name, dataset )
        # Need a special state here to show that metadata is being set and also allow the job to run
        # i.e. if state was set to 'running' the set metadata job would never run, as it would wait for input (the dataset to set metadata on) to be in a ready state
        dataset._state = dataset.states.SETTING_METADATA
        job.state = start_job_state  # job inputs have been configured, restore initial job state
        sa_session.flush()

        # Queue the job for execution
        app.job_queue.put( job.id, tool.id )
        # FIXME: need to add event logging to app and log events there rather than trans.
        # trans.log_event( "Added set external metadata job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )

        # clear e.g. converted files
        dataset.datatype.before_setting_metadata( dataset )

        return job, odict()

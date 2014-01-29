import tempfile, os
from __init__ import ToolAction
from galaxy.util.odict import odict
from galaxy.tools.imp_exp import JobImportHistoryArchiveWrapper, JobExportHistoryArchiveWrapper

import logging
log = logging.getLogger( __name__ )

class ImportHistoryToolAction( ToolAction ):
    """Tool action used for importing a history to an archive. """

    def execute( self, tool, trans, incoming = {}, set_output_hid = False, overwrite = True, history=None, **kwargs ):
        #
        # Create job.
        #
        job = trans.app.model.Job()
        session = trans.get_galaxy_session()
        job.session_id = session and session.id
        if history:
            history_id = history.id
        elif trans.history:
            history_id = trans.history.id
        else:
            history_id = None
        job.history_id = history_id
        job.tool_id = tool.id
        job.user_id = trans.user.id
        start_job_state = job.state #should be job.states.NEW
        job.state = job.states.WAITING #we need to set job state to something other than NEW, or else when tracking jobs in db it will be picked up before we have added input / output parameters
        trans.sa_session.add( job )
        trans.sa_session.flush() #ensure job.id are available

        #
        # Setup job and job wrapper.
        #

        # Add association for keeping track of job, history relationship.

        # Use abspath because mkdtemp() does not, contrary to the documentation,
        # always return an absolute path.
        archive_dir = os.path.abspath( tempfile.mkdtemp() )
        jiha = trans.app.model.JobImportHistoryArchive( job=job, archive_dir=archive_dir )
        trans.sa_session.add( jiha )

        #
        # Add parameters to job_parameter table.
        #

        # Set additional parameters.
        incoming[ '__DEST_DIR__' ] = jiha.archive_dir
        for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
            job.add_parameter( name, value )

        job.state = start_job_state #job inputs have been configured, restore initial job state
        job.set_handler(tool.get_job_handler(None))
        trans.sa_session.flush()

        # Queue the job for execution
        trans.app.job_queue.put( job.id, tool.id )
        trans.log_event( "Added import history job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )

        return job, odict()

class ExportHistoryToolAction( ToolAction ):
    """Tool action used for exporting a history to an archive. """

    def execute( self, tool, trans, incoming = {}, set_output_hid = False, overwrite = True, history=None, **kwargs ):
        #
        # Get history to export.
        #
        history = None
        for name, value in incoming.iteritems():
            if isinstance( value, trans.app.model.History ):
                history_param_name = name
                history = value
                del incoming[ history_param_name ]
                break

        if not history:
            raise Exception( 'There is no history to export.' )

        #
        # Create the job and output dataset objects
        #
        job = trans.app.model.Job()
        session = trans.get_galaxy_session()
        job.session_id = session and session.id
        if history:
            history_id = history.id
        else:
            history_id = trans.history.id
        job.history_id = history_id
        job.tool_id = tool.id
        if trans.user:
            # If this is an actual user, run the job as that individual.  Otherwise we're running as guest.
            job.user_id = trans.user.id
        start_job_state = job.state #should be job.states.NEW
        job.state = job.states.WAITING #we need to set job state to something other than NEW, or else when tracking jobs in db it will be picked up before we have added input / output parameters
        trans.sa_session.add( job )

        # Create dataset that will serve as archive.
        archive_dataset = trans.app.model.Dataset()
        trans.sa_session.add( archive_dataset )

        trans.sa_session.flush() #ensure job.id and archive_dataset.id are available
        trans.app.object_store.create( archive_dataset ) # set the object store id, create dataset (if applicable)

        #
        # Setup job and job wrapper.
        #

        # Add association for keeping track of job, history, archive relationship.
        jeha = trans.app.model.JobExportHistoryArchive( job=job, history=history, \
                                                        dataset=archive_dataset, \
                                                        compressed=incoming[ 'compress' ] )
        trans.sa_session.add( jeha )

        job_wrapper = JobExportHistoryArchiveWrapper( job )
        cmd_line = job_wrapper.setup_job( trans, jeha, include_hidden=incoming[ 'include_hidden' ], \
                                            include_deleted=incoming[ 'include_deleted' ] )

        #
        # Add parameters to job_parameter table.
        #

        # Set additional parameters.
        incoming[ '__HISTORY_TO_EXPORT__' ] = history.id
        incoming[ '__EXPORT_HISTORY_COMMAND_INPUTS_OPTIONS__' ] = cmd_line
        for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
            job.add_parameter( name, value )

        job.state = start_job_state #job inputs have been configured, restore initial job state
        job.set_handler(tool.get_job_handler(None))
        trans.sa_session.flush()


        # Queue the job for execution
        trans.app.job_queue.put( job.id, tool.id )
        trans.log_event( "Added export history job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )

        return job, odict()

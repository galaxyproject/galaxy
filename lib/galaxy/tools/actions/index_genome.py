import tempfile
from __init__ import ToolAction
from galaxy.util.odict import odict
from galaxy.tools.genome_index import *

import logging
log = logging.getLogger( __name__ )

class GenomeIndexToolAction( ToolAction ):
    """Tool action used for exporting a history to an archive. """

    def execute( self, tool, trans, *args, **kwargs  ):
        #
        # Get genome to index.
        #
        incoming = kwargs['incoming']
        #
        # Create the job and output dataset objects
        #
        job = trans.app.model.Job()
        job.tool_id = tool.id
        job.user_id = incoming['user']
        start_job_state = job.state # should be job.states.NEW
        job.state = job.states.WAITING # we need to set job state to something other than NEW, or else when tracking jobs in db it will be picked up before we have added input / output parameters
        trans.sa_session.add( job )

        # Create dataset that will serve as archive.
        temp_dataset = trans.app.model.Dataset( state=trans.app.model.Dataset.states.NEW )
        trans.sa_session.add( temp_dataset )

        trans.sa_session.flush() # ensure job.id and archive_dataset.id are available
        trans.app.object_store.create( temp_dataset ) # set the object store id, create dataset (because galaxy likes having datasets)

        #
        # Setup job and job wrapper.
        #

        # Add association for keeping track of job, history, archive relationship.
        user = trans.sa_session.query( trans.app.model.User ).get( int( incoming['user'] ) )
        assoc = trans.app.model.GenomeIndexToolData( job=job, dataset=temp_dataset, fasta_path=incoming['path'], \
                                                        indexer=incoming['indexer'], user=user, \
                                                        deferred_job=kwargs['deferred'], transfer_job=kwargs['transfer'] )
        trans.sa_session.add( assoc )

        job_wrapper = GenomeIndexToolWrapper( job )
        cmd_line = job_wrapper.setup_job( assoc )
        #
        # Add parameters to job_parameter table.
        #

        # Set additional parameters.
        incoming[ '__GENOME_INDEX_COMMAND__' ] = cmd_line
        for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
            job.add_parameter( name, value )

        job.state = start_job_state # job inputs have been configured, restore initial job state
        trans.sa_session.flush()


        # Queue the job for execution
        trans.app.job_queue.put( job.id, tool )
        log.info( "Added genome index job to the job queue, id: %s" % str( job.id ) )

        return job, odict()
        

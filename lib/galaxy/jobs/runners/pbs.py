import os, logging, threading, time
from Queue import Queue, Empty

from galaxy import model
from paste.deploy.converters import asbool

import pkg_resources

try:
    pkg_resources.require( "pbs_python" )
    pbs = __import__( "pbs" )
except:
    pbs = None

log = logging.getLogger( __name__ )

pbs_template = """#!/bin/sh
GALAXY_LIB="%s"
if [ "$GALAXY_LIB" != "None" ]; then
    if [ -n "$PYTHONPATH" ]; then
        export PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"
    else
        export PYTHONPATH="$GALAXY_LIB"
    fi
fi
cd %s
%s
"""

pbs_symlink_template = """#!/bin/sh
GALAXY_LIB="%s"
if [ "$GALAXY_LIB" != "None" ]; then
    if [ -n "$PYTHONPATH" ]; then
        export PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"
    else
        export PYTHONPATH="$GALAXY_LIB"
    fi
fi
for dataset in %s; do
    dir=`dirname $dataset`
    file=`basename $dataset`
    [ ! -d $dir ] && mkdir -p $dir
    [ ! -e $dataset ] && ln -s %s/$file $dataset
done
cd %s
%s
"""

class PBSJobState( object ):
    def __init__( self ):
        """
        Encapsulates state related to a job that is being run via PBS and 
        that we need to monitor.
        """
        self.job_wrapper = None
        self.job_id = None
        self.old_state = None
        self.running = False
        self.job_file = None
        self.ofile = None
        self.efile = None
        self.runner_url = None

class PBSJobRunner( object ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Initialize this job runner and start the monitor thread"""
        # Check if PBS was importable, fail if not
        if pbs is None:
            raise Exception( "PBSJobRunner requires pbs-python which was not found" )
        self.app = app
        # 'watched' and 'queue' are both used to keep track of jobs to watch.
        # 'queue' is used to add new watched jobs, and can be called from
        # any thread (usually by the 'queue_job' method). 'watched' must only
        # be modified by the monitor thread, which will move items from 'queue'
        # to 'watched' and then manage the watched jobs.
        self.watched = []
        self.queue = Queue()
        # set the default server during startup
        self.default_pbs_server = None
        self.determine_pbs_server( 'pbs:///' )
        self.monitor_thread = threading.Thread( target=self.monitor )
        self.monitor_thread.start()
        log.debug( "ready" )

    def determine_pbs_server( self, url, rewrite = False ):
        """Determine what PBS server we are connecting to"""
        url_split = url.split("/")
        server = url_split[2]
        if server == "":
            if not self.default_pbs_server:
                self.default_pbs_server = pbs.pbs_default()
                log.debug( "Set default PBS server to %s" % self.default_pbs_server )
            server = self.default_pbs_server
            url_split[2] = server
        if server is None:
            raise Exception( "Could not find torque server" )
        if rewrite:
            return ( server, "/".join( url_split ) )
        else:
            return server

    def determine_pbs_queue( self, url ):
        """Determine what PBS queue we are submitting to"""
        url_split = url.split("/")
        queue = url_split[3]
        if queue == "":
            # None == server's default queue
            queue = None
        return queue

    def queue_job( self, job_wrapper ):
        """Create PBS script for a job and submit it to the PBS queue"""

        try:
            job_wrapper.prepare()
            command_line = job_wrapper.get_command_line()
        except:
            job_wrapper.fail( "failure preparing job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return

        runner_url = job_wrapper.tool.job_runner
        
        # This is silly, why would we queue a job with no command line?
        if not command_line:
            job_wrapper.finish( '', '' )
            return
        
        # Check for deletion before we change state
        if job_wrapper.get_state() == 'deleted':
            log.debug( "Job %s deleted by user before it entered the PBS queue" % job_wrapper.job_id )
            job_wrapper.cleanup()
            return

        # Change to queued state immediately
        job_wrapper.change_state( 'queued' )
        
        ( pbs_server_name, runner_url ) = self.determine_pbs_server( runner_url, rewrite = True )
        pbs_queue_name = self.determine_pbs_queue( runner_url )
        c = pbs.pbs_connect( pbs_server_name )
        if c <= 0:
            raise Exception( "Connection to PBS server for submit failed" )

        # define job attributes
        ofile = "%s/database/pbs/%s.o" % (os.getcwd(), job_wrapper.job_id)
        efile = "%s/database/pbs/%s.e" % (os.getcwd(), job_wrapper.job_id)

        # If an application server is set, we're staging
        if self.app.config.pbs_application_server:
            pbs_ofile = self.app.config.pbs_application_server + ':' + ofile
            pbs_efile = self.app.config.pbs_application_server + ':' + efile
            stagein = self.get_stage_in_out( job_wrapper.get_input_fnames() + job_wrapper.get_output_fnames(), symlink=True )
            stageout = self.get_stage_in_out( job_wrapper.get_output_fnames() )
            job_attrs = pbs.new_attropl(5)
            job_attrs[0].name = pbs.ATTR_o
            job_attrs[0].value = pbs_ofile
            job_attrs[1].name = pbs.ATTR_e
            job_attrs[1].value = pbs_efile
            job_attrs[2].name = pbs.ATTR_stagein
            job_attrs[2].value = stagein
            job_attrs[3].name = pbs.ATTR_stageout
            job_attrs[3].value = stageout
            job_attrs[4].name = pbs.ATTR_N
            job_attrs[4].value = "%s" % job_wrapper.job_id
            exec_dir = os.path.abspath( os.getcwd() )
        # If not, we're using NFS
        else:
            job_attrs = pbs.new_attropl(2)
            job_attrs[0].name = pbs.ATTR_o
            job_attrs[0].value = ofile
            job_attrs[1].name = pbs.ATTR_e
            job_attrs[1].value = efile
            exec_dir = os.getcwd()

        # write the job script
        if self.app.config.pbs_stage_path != '':
            script = pbs_symlink_template % (job_wrapper.galaxy_lib_dir, " ".join(job_wrapper.get_input_fnames() + job_wrapper.get_output_fnames()), self.app.config.pbs_stage_path, exec_dir, command_line)
        else:
            script = pbs_template % (job_wrapper.galaxy_lib_dir, exec_dir, command_line)
        job_file = "%s/database/pbs/%s.sh" % (os.getcwd(), job_wrapper.job_id)
        fh = file(job_file, "w")
        fh.write(script)
        fh.close()

        # job was deleted while we were preparing it
        if job_wrapper.get_state() == 'deleted':
            log.debug( "Job %s deleted by user before it entered the PBS queue" % job_wrapper.job_id )
            pbs.pbs_disconnect(c)
            self.cleanup( ( ofile, efile, job_file ) )
            job_wrapper.cleanup()
            return

        # submit
        galaxy_job_id = job_wrapper.job_id
        log.debug("(%s) submitting file %s" % ( galaxy_job_id, job_file ) )
        log.debug("(%s) command is: %s" % ( galaxy_job_id, command_line ) )
        job_id = pbs.pbs_submit(c, job_attrs, job_file, pbs_queue_name, None)
        pbs.pbs_disconnect(c)

        # check to see if it submitted
        if not job_id:
            errno, text = pbs.error()
            log.debug( "(%s) pbs_submit failed, PBS error %d: %s" % (galaxy_job_id, errno, text) )
            job_wrapper.fail( "Unable to run this job due to a cluster error" )
            return

        if pbs_queue_name is None:
            log.debug("(%s) queued in default queue as %s" % (galaxy_job_id, job_id) )
        else:
            log.debug("(%s) queued in %s queue as %s" % (galaxy_job_id, pbs_queue_name, job_id) )

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_runner( runner_url, job_id )

        # Store PBS related state information for job
        pbs_job_state = PBSJobState()
        pbs_job_state.job_wrapper = job_wrapper
        pbs_job_state.job_id = job_id
        pbs_job_state.ofile = ofile
        pbs_job_state.efile = efile
        pbs_job_state.job_file = job_file
        pbs_job_state.old_state = 'N'
        pbs_job_state.running = False
        pbs_job_state.runner_url = runner_url
        
        # Add to our 'queue' of jobs to monitor
        self.queue.put( pbs_job_state )

    def monitor( self ):
        """
        Watches jobs currently in the PBS queue and deals with state changes
        (queued to running) and job completion
        """
        while 1:
            # Take any new watched jobs and put them on the monitor list
            try:
                while 1: 
                    pbs_job_state = self.queue.get_nowait()
                    if pbs_job_state is self.STOP_SIGNAL:
                        # TODO: This is where any cleanup would occur
                        return
                    self.watched.append( pbs_job_state )
            except Empty:
                pass
            # Iterate over the list of watched jobs and check state
            self.check_watched_items()
            # Sleep a bit before the next state check
            time.sleep( 1 )
            
    def check_watched_items( self ):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []
        # reduce pbs load by batching status queries
        ( failures, states ) = self.check_all_jobs()
        for pbs_job_state in self.watched:
            job_id = pbs_job_state.job_id
            galaxy_job_id = pbs_job_state.job_wrapper.job_id
            old_state = pbs_job_state.old_state
            pbs_server_name = self.determine_pbs_server( pbs_job_state.runner_url )
            if pbs_server_name in failures:
                log.debug( "(%s/%s) Skipping state check because PBS server connection failed" % ( galaxy_job_id, job_id ) )
                new_watched.append( pbs_job_state )
                continue
            if states.has_key( job_id ):
                state = states[job_id]
                if state != old_state:
                    log.debug("(%s/%s) job state changed from %s to %s" % ( galaxy_job_id, job_id, old_state, state ) )
                if state == "R" and not pbs_job_state.running:
                    pbs_job_state.running = True
                    pbs_job_state.job_wrapper.change_state( "running" )
                pbs_job_state.old_state = state
                new_watched.append( pbs_job_state )
            else:
                try:
                    # recheck to make sure it wasn't a communication problem
                    self.check_single_job( pbs_server_name, job_id )
                    log.warning( "(%s/%s) job was not in state check list, but was found with individual state check" )
                    new_watched.append( pbs_job_state )
                except:
                    errno, text = pbs.error()
                    if errno != 15001:
                        log.info("(%s/%s) state check resulted in error (%d): %s" % (galaxy_job_id, job_id, errno, text) )
                        new_watched.append( pbs_job_state )
                    else:
                        log.debug("(%s/%s) job has left queue" % (galaxy_job_id, job_id) )
                        self.finish_job( pbs_job_state )
        # Replace the watch list with the updated version
        self.watched = new_watched
        
    def check_all_jobs( self ):
        """
        Returns a list of servers that failed to be contacted and a dict
        of "job_id : state" pairs.
        """
        servers = []
        failures = []
        states = {}
        for pbs_job_state in self.watched:
            pbs_server_name = self.determine_pbs_server( pbs_job_state.runner_url )
            if pbs_server_name not in servers:
                servers.append( pbs_server_name )
        for pbs_server_name in servers:
            c = pbs.pbs_connect( pbs_server_name )
            if c <= 0:
                log.debug("connection to PBS server %s for state check failed" % pbs_server_name )
                failures.append( pbs_server_name )
                continue
            stat_attrl = pbs.new_attrl(1)
            stat_attrl[0].name = 'job_state'
            jobs = pbs.pbs_statjob( c, None, stat_attrl, None )
            pbs.pbs_disconnect( c )
            for job in jobs:
                states[job.name] = job.attribs[0].value
        return( ( failures, states ) )

    def check_single_job( self, pbs_server_name, job_id ):
        """
        Returns the state of a single job, used to make sure a job is
        really dead.
        """
        c = pbs.pbs_connect( pbs_server_name )
        if c <= 0:
            log.debug("connection to PBS server %s for state check failed" % pbs_server_name )
            return None
        stat_attrl = pbs.new_attrl(1)
        stat_attrl[0].name = 'job_state'
        jobs = pbs.pbs_statjob( c, job_id, stat_attrl, None )
        pbs.pbs_disconnect( c )
        return jobs[0].attribs[0].value

    def finish_job( self, pbs_job_state ):
        """
        Get the output/error for a finished job, pass to `job_wrapper.finish`
        and cleanup all the PBS temporary files.
        """
        ofile = pbs_job_state.ofile
        efile = pbs_job_state.efile
        job_file = pbs_job_state.job_file
        # collect the output
        try:
            ofh = file(ofile, "r")
            efh = file(efile, "r")
            stdout = ofh.read()
            stderr = efh.read()
        except:
            stdout = ''
            stderr = 'Job output not returned by PBS: the output datasets were deleted while the job was running, the job was manually dequeued or there was a cluster error.'
            log.debug(stderr)

        try:
            pbs_job_state.job_wrapper.finish( stdout, stderr )
        except:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)

        # clean up the pbs files
        self.cleanup( ( ofile, efile, job_file ) )

    def cleanup( self, files ):
        if not asbool( self.app.config.get( 'debug', False ) ):
            for file in files:
                if os.access( file, os.R_OK ):
                    os.unlink( file )

    def put( self, job_wrapper ):
        """Add a job to the queue (by job identifier)"""
        self.queue_job( job_wrapper )
    
    def shutdown( self ):
        """Attempts to gracefully shut down the monitor thread"""
        log.info( "sending stop signal to worker threads" )
        self.queue.put( self.STOP_SIGNAL )
        log.info( "pbs job runner stopped" )

    def get_stage_in_out( self, fnames, symlink=False ):
        """Convenience function to create a stagein/stageout list"""
        stage = ''
        for fname in fnames:
            if os.access(fname, os.R_OK):
                if stage:
                    stage += ','
                # pathnames are now absolute
                if symlink and self.app.config.pbs_stage_path:
                    stage_name = os.path.join(self.app.config.pbs_stage_path, os.path.split(fname)[1])
                else:
                    stage_name = fname
                stage += "%s@%s:%s" % (stage_name, self.app.config.pbs_dataset_server, fname)
        return stage

    def stop_job( self, job ):
        """Attempts to delete a job from the PBS queue"""
        pbs_server_name = self.determine_pbs_server( str( job.job_runner_name ) )
        c = pbs.pbs_connect( pbs_server_name )
        if c <= 0:
            log.debug("(%s/%s) Connection to PBS server for job delete failed" % ( job.id, job.job_runner_external_id ) )
            return
        pbs.pbs_deljob( c, str( job.job_runner_external_id ), 'NULL' )
        pbs.pbs_disconnect( c )
        log.debug( "(%s/%s) Removed from PBS queue at user's request" % ( job.id, job.job_runner_external_id ) )

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        pbs_job_state = PBSJobState()
        pbs_job_state.ofile = "%s/database/pbs/%s.o" % (os.getcwd(), job.id)
        pbs_job_state.efile = "%s/database/pbs/%s.e" % (os.getcwd(), job.id)
        pbs_job_state.job_file = "%s/database/pbs/%s.sh" % (os.getcwd(), job.id)
        pbs_job_state.job_id = str( job.job_runner_external_id )
        pbs_job_state.runner_url = job_wrapper.tool.job_runner
        job_wrapper.command_line = job.command_line
        pbs_job_state.job_wrapper = job_wrapper
        if job.state == model.Job.states.RUNNING:
            log.debug( "(%s/%s) is still in running state, adding to the PBS queue" % ( job.id, job.job_runner_external_id ) )
            pbs_job_state.old_state = 'R'
            pbs_job_state.running = True
            self.queue.put( pbs_job_state )
        elif job.state == model.Job.states.QUEUED:
            log.debug( "(%s/%s) is still in PBS queued state, adding to the PBS queue" % ( job.id, job.job_runner_external_id ) )
            pbs_job_state.old_state = 'Q'
            pbs_job_state.running = False
            self.queue.put( pbs_job_state )

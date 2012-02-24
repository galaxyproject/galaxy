import os, logging, threading, time
from datetime import timedelta
from Queue import Queue, Empty

from galaxy import model
from galaxy.datatypes.data import nice_size
from galaxy.util.bunch import Bunch
from galaxy.jobs.runners import BaseJobRunner

from paste.deploy.converters import asbool

import pkg_resources

egg_message = """

The 'pbs' runner depends on 'pbs_python' which is not installed or not
configured properly.  Galaxy's "scramble" system should make this installation
simple, please follow the instructions found at:

    http://wiki.g2.bx.psu.edu/Admin/Config/Performance/Cluster

Additional errors may follow:
%s
"""

try:
    pkg_resources.require( "pbs_python" )
    pbs = __import__( "pbs" )
except Exception, e:
    raise Exception( egg_message % str( e ) )

log = logging.getLogger( __name__ )

__all__ = [ 'PBSJobRunner' ]

pbs_template = """#!/bin/sh
GALAXY_LIB="%s"
if [ "$GALAXY_LIB" != "None" ]; then
    if [ -n "$PYTHONPATH" ]; then
        export PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"
    else
        export PYTHONPATH="$GALAXY_LIB"
    fi
fi
%s
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
%s
cd %s
%s
"""

# From pbs' job.h
JOB_EXIT_STATUS = {
    0:  "job exec successful",
    -1: "job exec failed, before files, no retry",
    -2: "job exec failed, after files, no retry",
    -3: "job execution failed, do retry",
    -4: "job aborted on MOM initialization",
    -5: "job aborted on MOM init, chkpt, no migrate",
    -6: "job aborted on MOM init, chkpt, ok migrate",
    -7: "job restart failed",
    -8: "exec() of user command failed",
}

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
        self.check_count = 0
        self.stop_job = False

class PBSJobRunner( BaseJobRunner ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Initialize this job runner and start the monitor thread"""
        # Check if PBS was importable, fail if not
        if pbs is None:
            raise Exception( "PBSJobRunner requires pbs-python which was not found" )
        if app.config.pbs_application_server and app.config.outputs_to_working_directory:
            raise Exception( "pbs_application_server (file staging) and outputs_to_working_directory options are mutually exclusive" )
        self.app = app
        self.sa_session = app.model.context
        # 'watched' and 'queue' are both used to keep track of jobs to watch.
        # 'queue' is used to add new watched jobs, and can be called from
        # any thread (usually by the 'queue_job' method). 'watched' must only
        # be modified by the monitor thread, which will move items from 'queue'
        # to 'watched' and then manage the watched jobs.
        self.watched = []
        self.monitor_queue = Queue()
        # set the default server during startup
        self.default_pbs_server = None
        self.determine_pbs_server( 'pbs:///' )
        self.job_walltime = None
        if self.app.config.job_walltime is not None:
            h, m, s = [ int( v ) for v in self.app.config.job_walltime.split( ':' ) ]
            self.job_walltime = timedelta( 0, s, 0, 0, m, h )
        self.monitor_thread = threading.Thread( target=self.monitor )
        self.monitor_thread.start()
        self.work_queue = Queue()
        self.work_threads = []
        nworkers = app.config.cluster_job_queue_workers
        for i in range( nworkers ):
            worker = threading.Thread( target=self.run_next )
            worker.start()
            self.work_threads.append( worker )
        log.debug( "%d workers ready" % nworkers )

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
        try:
            return url.split('/')[3] or None
        except:
            return None

    def determine_pbs_options( self, url ):
        try:
            opts = url.split('/')[4].strip().lstrip('-').split(' -')
            assert opts != ['']
        except:
            return []
        rval = []
        for opt in opts:
            name, value = opt.split( None, 1 )
            if name == 'l':
                resource_attrs = value.split(',')
                for j, ( res, val ) in enumerate( [ a.split('=', 1) for a in resource_attrs ] ):
                    rval.append( dict( name = pbs.ATTR_l, value = val, resource = res ) )
            else:
                rval.append( dict( name = getattr( pbs, 'ATTR_' + name ), value = value ) )
        return rval

    def run_next( self ):
        """
        Run the next item in the queue (a job waiting to run or finish )
        """
        while 1:
            ( op, obj ) = self.work_queue.get()
            if op is self.STOP_SIGNAL:
                return
            try:
                if op == 'queue':
                    self.queue_job( obj )
                elif op == 'finish':
                    self.finish_job( obj )
                elif op == 'fail':
                    self.fail_job( obj )
            except:
                log.exception( "(%s) Uncaught exception %sing job" % ( getattr( obj, 'job_id', None ), op ) )

    def queue_job( self, job_wrapper ):
        """Create PBS script for a job and submit it to the PBS queue"""

        try:
            job_wrapper.prepare()
            command_line = self.build_command_line( job_wrapper, include_metadata=not( self.app.config.pbs_stage_path ) )
        except:
            job_wrapper.fail( "failure preparing job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return

        runner_url = job_wrapper.get_job_runner()
        
        # This is silly, why would we queue a job with no command line?
        if not command_line:
            job_wrapper.finish( '', '' )
            return
        
        # Check for deletion before we change state
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.debug( "Job %s deleted by user before it entered the PBS queue" % job_wrapper.job_id )
            if self.app.config.cleanup_job in ( "always", "onsuccess" ):
                job_wrapper.cleanup()
            return

        ( pbs_server_name, runner_url ) = self.determine_pbs_server( runner_url, rewrite = True )
        pbs_queue_name = self.determine_pbs_queue( runner_url )
        pbs_options = self.determine_pbs_options( runner_url )
        c = pbs.pbs_connect( pbs_server_name )
        if c <= 0:
            errno, text = pbs.error()
            job_wrapper.fail( "Unable to queue job for execution.  Resubmitting the job may succeed." )
            log.error( "Connection to PBS server for submit failed: %s: %s" % ( errno, text ) )
            return

        # define job attributes
        ofile = "%s/%s.o" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
        efile = "%s/%s.e" % (self.app.config.cluster_files_directory, job_wrapper.job_id)

        output_fnames = job_wrapper.get_output_fnames()
        
        # If an application server is set, we're staging
        if self.app.config.pbs_application_server:
            pbs_ofile = self.app.config.pbs_application_server + ':' + ofile
            pbs_efile = self.app.config.pbs_application_server + ':' + efile
            output_files = [ str( o ) for o in output_fnames ]
            stagein = self.get_stage_in_out( job_wrapper.get_input_fnames() + output_files, symlink=True )
            stageout = self.get_stage_in_out( output_files )
            attrs = [
                dict( name = pbs.ATTR_o, value = pbs_ofile ),
                dict( name = pbs.ATTR_e, value = pbs_efile ),
                dict( name = pbs.ATTR_stagein, value = stagein ),
                dict( name = pbs.ATTR_stageout, value = stageout ),
            ]
        # If not, we're using NFS
        else:
            attrs = [
                dict( name = pbs.ATTR_o, value = ofile ),
                dict( name = pbs.ATTR_e, value = efile ),
            ]

        # define PBS job options
        attrs.append( dict( name = pbs.ATTR_N, value = str( "%s_%s_%s" % ( job_wrapper.job_id, job_wrapper.tool.id, job_wrapper.user ) ) ) )
        job_attrs = pbs.new_attropl( len( attrs ) + len( pbs_options ) )
        for i, attr in enumerate( attrs + pbs_options ):
            job_attrs[i].name = attr['name']
            job_attrs[i].value = attr['value']
            if 'resource' in attr:
                job_attrs[i].resource = attr['resource']
        exec_dir = os.path.abspath( job_wrapper.working_directory )

        # write the job script
        if self.app.config.pbs_stage_path != '':
            script = pbs_symlink_template % ( job_wrapper.galaxy_lib_dir,
                                              " ".join( job_wrapper.get_input_fnames() + output_files ),
                                              self.app.config.pbs_stage_path,
                                              job_wrapper.get_env_setup_clause(),
                                              exec_dir,
                                              command_line )
        else:
            script = pbs_template % ( job_wrapper.galaxy_lib_dir,
                                      job_wrapper.get_env_setup_clause(),
                                      exec_dir,
                                      command_line )
        job_file = "%s/%s.sh" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
        fh = file(job_file, "w")
        fh.write(script)
        fh.close()

        # job was deleted while we were preparing it
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.debug( "Job %s deleted by user before it entered the PBS queue" % job_wrapper.job_id )
            pbs.pbs_disconnect(c)
            if self.app.config.cleanup_job in ( "always", "onsuccess" ):
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
            job_wrapper.fail( "Unable to run this job due to a cluster error, please retry it later" )
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
        self.monitor_queue.put( pbs_job_state )

    def monitor( self ):
        """
        Watches jobs currently in the PBS queue and deals with state changes
        (queued to running) and job completion
        """
        while 1:
            # Take any new watched jobs and put them on the monitor list
            try:
                while 1: 
                    pbs_job_state = self.monitor_queue.get_nowait()
                    if pbs_job_state is self.STOP_SIGNAL:
                        # TODO: This is where any cleanup would occur
                        return
                    self.watched.append( pbs_job_state )
            except Empty:
                pass
            # Iterate over the list of watched jobs and check state
            try:
                self.check_watched_items()
            except:
                log.exception( "Uncaught exception checking jobs" )
            # Sleep a bit before the next state check
            time.sleep( 1 )
            
    def check_watched_items( self ):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []
        # reduce pbs load by batching status queries
        ( failures, statuses ) = self.check_all_jobs()
        for pbs_job_state in self.watched:
            job_id = pbs_job_state.job_id
            galaxy_job_id = pbs_job_state.job_wrapper.job_id
            old_state = pbs_job_state.old_state
            pbs_server_name = self.determine_pbs_server( pbs_job_state.runner_url )
            if pbs_server_name in failures:
                log.debug( "(%s/%s) Skipping state check because PBS server connection failed" % ( galaxy_job_id, job_id ) )
                new_watched.append( pbs_job_state )
                continue
            try:
                status = statuses[job_id]
            except KeyError:
                try:
                    # Recheck to make sure it wasn't a communication problem
                    self.check_single_job( pbs_server_name, job_id )
                    log.warning( "(%s/%s) PBS job was not in state check list, but was found with individual state check" % ( galaxy_job_id, job_id ) )
                    new_watched.append( pbs_job_state )
                except:
                    errno, text = pbs.error()
                    if errno == 15001:
                        # 15001 == job not in queue
                        log.debug("(%s/%s) PBS job has left queue" % (galaxy_job_id, job_id) )
                        self.work_queue.put( ( 'finish', pbs_job_state ) )
                    else:
                        # Unhandled error, continue to monitor
                        log.info("(%s/%s) PBS state check resulted in error (%d): %s" % (galaxy_job_id, job_id, errno, text) )
                        new_watched.append( pbs_job_state )
                continue
            if status.job_state != old_state:
                log.debug("(%s/%s) PBS job state changed from %s to %s" % ( galaxy_job_id, job_id, old_state, status.job_state ) )
            if status.job_state == "R" and not pbs_job_state.running:
                pbs_job_state.running = True
                pbs_job_state.job_wrapper.change_state( model.Job.states.RUNNING )
            if status.job_state == "R" and ( pbs_job_state.check_count % 20 ) == 0:
                # Every 20th time the job status is checked, do limit checks (if configured)
                if self.app.config.output_size_limit > 0:
                    # Check the size of the job outputs
                    fail = False
                    for outfile, size in pbs_job_state.job_wrapper.check_output_sizes():
                        if size > self.app.config.output_size_limit:
                            pbs_job_state.fail_message = 'Job output grew too large (greater than %s), please try different job parameters or' \
                                % nice_size( self.app.config.output_size_limit )
                            log.warning( '(%s/%s) Dequeueing job due to output %s growing larger than %s limit' \
                                % ( galaxy_job_id, job_id, os.path.basename( outfile ), nice_size( self.app.config.output_size_limit ) ) )
                            pbs_job_state.stop_job = True
                            self.work_queue.put( ( 'fail', pbs_job_state ) )
                            fail = True
                            break
                    if fail:
                        continue
                if self.job_walltime is not None:
                    # Check the job's execution time
                    if status.get( 'resources_used', False ):
                        # resources_used may not be in the status for new jobs
                        h, m, s = [ int( i ) for i in status.resources_used.walltime.split( ':' ) ]
                        time_executing = timedelta( 0, s, 0, 0, m, h )
                        if time_executing > self.job_walltime:
                            pbs_job_state.fail_message = 'Job ran longer than maximum allowed execution time (%s), please try different job parameters or' \
                                % self.app.config.job_walltime
                            log.warning( '(%s/%s) Dequeueing job since walltime has been reached' \
                                % ( galaxy_job_id, job_id ) )
                            pbs_job_state.stop_job = True
                            self.work_queue.put( ( 'fail', pbs_job_state ) )
                            continue
            elif status.job_state == "C":
                # "keep_completed" is enabled in PBS, so try to check exit status
                try:
                    assert int( status.exit_status ) == 0
                    log.debug("(%s/%s) PBS job has completed successfully" % ( galaxy_job_id, job_id ) )
                except AssertionError:
                    pbs_job_state.fail_message = 'Job cannot be completed due to a cluster error, please retry it later'
                    log.error( '(%s/%s) PBS job failed: %s' % ( galaxy_job_id, job_id, JOB_EXIT_STATUS.get( int( status.exit_status ), 'Unknown error: %s' % status.exit_status ) ) )
                    self.work_queue.put( ( 'fail', pbs_job_state ) )
                    continue
                except AttributeError:
                    # No exit_status, can't verify proper completion so we just have to assume success.
                    log.debug("(%s/%s) PBS job has completed" % ( galaxy_job_id, job_id ) )
                self.work_queue.put( ( 'finish', pbs_job_state ) )
                continue
            pbs_job_state.old_state = status.job_state
            new_watched.append( pbs_job_state )
        # Replace the watch list with the updated version
        self.watched = new_watched
        
    def check_all_jobs( self ):
        """
        Returns a list of servers that failed to be contacted and a dict
        of "job_id : status" pairs (where status is a bunchified version
        of the API's structure.
        """
        servers = []
        failures = []
        statuses = {}
        for pbs_job_state in self.watched:
            pbs_server_name = self.determine_pbs_server( pbs_job_state.runner_url )
            if pbs_server_name not in servers:
                servers.append( pbs_server_name )
            pbs_job_state.check_count += 1
        for pbs_server_name in servers:
            c = pbs.pbs_connect( pbs_server_name )
            if c <= 0:
                log.debug("connection to PBS server %s for state check failed" % pbs_server_name )
                failures.append( pbs_server_name )
                continue
            stat_attrl = pbs.new_attrl(3)
            stat_attrl[0].name = pbs.ATTR_state
            stat_attrl[1].name = pbs.ATTR_used
            stat_attrl[2].name = pbs.ATTR_exitstat
            jobs = pbs.pbs_statjob( c, None, stat_attrl, None )
            pbs.pbs_disconnect( c )
            statuses.update( self.convert_statjob_to_bunches( jobs ) )
        return( ( failures, statuses ) )

    def convert_statjob_to_bunches( self, statjob_out ):
        statuses = {}
        for job in statjob_out:
            status = {}
            for attrib in job.attribs:
                if attrib.resource is None:
                    status[ attrib.name ] = attrib.value
                else:
                    if attrib.name not in status:
                        status[ attrib.name ] = Bunch()
                    status[ attrib.name ][ attrib.resource ] = attrib.value
            statuses[ job.name ] = Bunch( **status )
        return statuses

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
        stat_attrl[0].name = pbs.ATTR_state
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
            stdout = ofh.read( 32768 )
            stderr = efh.read( 32768 )
        except:
            stdout = ''
            stderr = 'Job output not returned by PBS: the output datasets were deleted while the job was running, the job was manually dequeued or there was a cluster error.'
            log.debug(stderr)

        try:
            pbs_job_state.job_wrapper.finish( stdout, stderr )
        except:
            log.exception("Job wrapper finish method failed")
            pbs_job_state.job_wrapper.fail("Unable to finish job", exception=True)

        # clean up the pbs files
        if self.app.config.cleanup_job == "always" or ( not stderr and self.app.config.cleanup_job == "onsuccess" ):
            self.cleanup( ( ofile, efile, job_file ) )

    def fail_job( self, pbs_job_state ):
        """
        Seperated out so we can use the worker threads for it.
        """
        if pbs_job_state.stop_job:
            self.stop_job( self.sa_session.query( self.app.model.Job ).get( pbs_job_state.job_wrapper.job_id ) )
        pbs_job_state.job_wrapper.fail( pbs_job_state.fail_message )
        if self.app.config.cleanup_job == "always":
            self.cleanup( ( pbs_job_state.ofile, pbs_job_state.efile, pbs_job_state.job_file ) )

    def cleanup( self, files ):
        for file in files:
            try:
                os.unlink( file )
            except Exception, e:
                log.warning( "Unable to cleanup: %s" % str( e ) )

    def put( self, job_wrapper ):
        """Add a job to the queue (by job identifier)"""
        # Change to queued state before handing to worker thread so the runner won't pick it up again
        job_wrapper.change_state( model.Job.states.QUEUED )
        self.work_queue.put( ( 'queue', job_wrapper ) )
    
    def shutdown( self ):
        """Attempts to gracefully shut down the monitor thread"""
        log.info( "sending stop signal to worker threads" )
        self.monitor_queue.put( self.STOP_SIGNAL )
        for i in range( len( self.work_threads ) ):
            self.work_queue.put( ( self.STOP_SIGNAL, None ) )
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
        pbs.pbs_deljob( c, str( job.job_runner_external_id ), '' )
        pbs.pbs_disconnect( c )
        log.debug( "(%s/%s) Removed from PBS queue before job completion" % ( job.id, job.job_runner_external_id ) )

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        pbs_job_state = PBSJobState()
        pbs_job_state.ofile = "%s/%s.o" % (self.app.config.cluster_files_directory, job.id)
        pbs_job_state.efile = "%s/%s.e" % (self.app.config.cluster_files_directory, job.id)
        pbs_job_state.job_file = "%s/%s.sh" % (self.app.config.cluster_files_directory, job.id)
        pbs_job_state.job_id = str( job.job_runner_external_id )
        pbs_job_state.runner_url = job_wrapper.get_job_runner()
        job_wrapper.command_line = job.command_line
        pbs_job_state.job_wrapper = job_wrapper
        if job.state == model.Job.states.RUNNING:
            log.debug( "(%s/%s) is still in running state, adding to the PBS queue" % ( job.id, job.job_runner_external_id ) )
            pbs_job_state.old_state = 'R'
            pbs_job_state.running = True
            self.monitor_queue.put( pbs_job_state )
        elif job.state == model.Job.states.QUEUED:
            log.debug( "(%s/%s) is still in PBS queued state, adding to the PBS queue" % ( job.id, job.job_runner_external_id ) )
            pbs_job_state.old_state = 'Q'
            pbs_job_state.running = False
            self.monitor_queue.put( pbs_job_state )

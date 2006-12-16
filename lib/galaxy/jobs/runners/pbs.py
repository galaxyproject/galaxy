import logging
import threading
import os
import random
import time
from Queue import Queue, Empty

from galaxy import model

import pkg_resources
pkg_resources.require( "pbs_python" )
pbs = __import__( "pbs" )


log = logging.getLogger( __name__ )

pbs_template = """#!/bin/sh
export PATH='%s'
export PYTHONPATH='%s'
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
        self.pbs_job_id = None
        self.old_state = None
        self.running = False
        self.job_file = None
        self.ofile = None
        self.efile = None

class PBSJobRunner( object ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Initialize this job runner and start the monitor thread"""
        self.app = app
        # 'watched' and 'queue' are both used to keep track of jobs to watch.
        # 'queue' is used to add new watched jobs, and can be called from
        # any thread (usually by the 'queue_job' method). 'watched' must only
        # be modified by the monitor thread, which will move items from 'queue'
        # to 'watched' and then manage the watched jobs.
        self.watched = []
        self.queue = Queue()
        self.determine_pbs_server()
        self.monitor_thread = threading.Thread( target=self.monitor )
        self.monitor_thread.start()
        log.debug( "ready" )

    def determine_pbs_server( self ):
        """Determine what PBS server we are connecting to"""
        if self.app.config.pbs_server:
            self.pbs_server = self.app.config.pbs_server
        else:
            self.pbs_server = pbs.pbs_default()
        if self.pbs_server is None:
            raise Exception( "Could not find torque server" )

    def queue_job( self, job_wrapper ):
        """Create PBS script for a job and submit it to the PBS queue"""
        command_line = job_wrapper.get_command_line()
        
        # This is silly, why would we queue a job with no command line?
        if not command_line:
            job_wrapper.finish( '', '' )
        
        # Change to queued state immediately
        job_wrapper.change_state( 'queued' )
        
        # random string for job name
        random.seed()
        job_name = ""
        for i in range(10):
            bit = random.randint(0,1)
            if bit == 0:
                bit = random.randint(97,122)
            else:
                bit = random.randint(65,90)
            job_name += chr(bit)

        conn = pbs.pbs_connect( self.pbs_server )
        if conn <= 0:
            raise Exception( "Connection to PBS server for submit failed" )

        # set up the job file
        script = pbs_template % (os.environ['PATH'], os.environ['PYTHONPATH'], os.getcwd(), command_line)
        job_file = "%s/database/pbs/%s.sh" % (os.getcwd(), job_name)
        fh = file(job_file, "w")
        fh.write(script)
        fh.close()

        # define job attributes
        ofile = "%s/database/pbs/%s.o" % (os.getcwd(), job_name)
        efile = "%s/database/pbs/%s.e" % (os.getcwd(), job_name)
        job_attrs = pbs.new_attropl(2)
        job_attrs[0].name = pbs.ATTR_o
        job_attrs[0].value = ofile
        job_attrs[1].name = pbs.ATTR_e
        job_attrs[1].value = efile

        # Attempt to queue
        if not( os.access(job_file, os.R_OK) and conn > 0 ):
            # FIXME: More information here?
            stderr = stdout = ''
                    
        log.debug("submitting file %s with output %s and error %s" % (job_file, ofile, efile) )
        log.debug("command is: %s" % command_line)
        job_id = pbs.pbs_submit(conn, job_attrs, job_file, None, None)
        log.debug("queued: %s" % job_id)
        pbs.pbs_disconnect(conn)

        if not job_id:
            stdout = ''
            stderr = "Job was not queued, PBS error %d: %s" % pbs.error()
            log.debug(stderr)

        # Get initial job state
        stat_attrl = pbs.new_attrl(1)
        stat_attrl[0].name = 'job_state'
        conn = pbs.pbs_connect( self.pbs_server )
        if conn > 0:
            jobs = pbs.pbs_statjob(conn, job_id, stat_attrl, 'NULL')
            pbs.pbs_disconnect(conn)
        else:
            log.info("(%s) WARNING: connection to PBS server for initial job state failed" % job_id)

        old_state = ""
        try:
            if (jobs[0].attribs[0].name == "job_state"):
                old_state = jobs[0].attribs[0].value
                log.debug("(%s) initial state is %s" % (job_id, old_state) )
        except:
            log.info("(%s) unable to retrieve initial state" % job_id)

        # ran immediately
        if old_state == "R":
            job_wrapper.change_state( "running" )
            running = True
            log.debug("(%s) job is now running" % job_id)

        # queued
        else:
            running = False
            
        # Store PBS related state information for job
        pbs_job_state = PBSJobState()
        pbs_job_state.job_wrapper = job_wrapper
        pbs_job_state.job_name = job_name
        pbs_job_state.job_id = job_id
        pbs_job_state.ofile = ofile
        pbs_job_state.efile = efile
        pbs_job_state.job_file = job_file
        pbs_job_state.old_state = old_state
        pbs_job_state.running = running
        
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
        for pbs_job_state in self.watched:
            job_id = pbs_job_state.job_id
            old_state = pbs_job_state.old_state
            running = pbs_job_state.running         
            conn = pbs.pbs_connect( self.pbs_server )
            if conn <= 0:
                log.debug("(%s) connection to PBS server for state check failed" % job_id)
            stat_attrl = pbs.new_attrl(1)
            stat_attrl[0].name = 'job_state'
            jobs = pbs.pbs_statjob(conn, pbs_job_state.job_id, stat_attrl, 'NULL')
            pbs.pbs_disconnect(conn)    
            if len( jobs ) < 1:
                log.debug("(%s) job has left queue" % job_id)
                self.finish_job( pbs_job_state )
            else:    
                try:
                    if (jobs[0].attribs[0].name == "job_state"):
                        state = jobs[0].attribs[0].value
                        if state != old_state:
                            log.debug("(%s) job state changed from %s to %s" % ( job_id, old_state, state ) )
                        if state == "R" and not running:
                            running = True
                            pbs_job_state.job_wrapper.change_state( "running" )
                            log.debug("(%s) job is now running" % job_id)
                        old_state = state
                    pbs_job_state.old_state = old_state
                    pbs_job_state.running = running
                except:
                    log.exception("(%s) unable to check state" % job_id)
                new_watched.append( pbs_job_state )
        # Replace the watch list with the updated version
        self.watched = new_watched
        
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
            stderr = 'Job output not returned by PBS.  Manually dequeued or cluster error?'
            log.debug(stderr)

        pbs_job_state.job_wrapper.finish( stdout, stderr )

        # clean up the job_file, ofile, efile
        if os.access(ofile, os.R_OK):
            os.unlink(ofile)
        if os.access(efile, os.R_OK):
            os.unlink(efile)
        if os.access(job_file, os.R_OK):
            os.unlink(job_file)
            
    def put( self, job_wrapper ):
        """Add a job to the queue (by job identifier)"""
        self.queue_job( job_wrapper )
    
    def shutdown( self ):
        """Attempts to gracefully shut down the monitor thread"""
        log.info( "sending stop signal to worker threads" )
        self.queue.put( self.STOP_SIGNAL )
        log.info( "pbs job runner stopped" )

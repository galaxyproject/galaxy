import util
import logging, threading, sys, os, time, subprocess, string, tempfile, re

import pkg_resources
pkg_resources.require( "PasteDeploy" )

from paste.deploy.converters import asbool

from Queue import Queue

log = logging.getLogger( __name__ )

# States for running a job. These are NOT the same as data states
JOB_WAIT, JOB_ERROR, JOB_OK = 'wait', 'error', 'ok'

class JobQueue( object ):
    """
    Job queue backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, nworkers, app ):
        """Start the job queue with 'nworkers' worker threads"""
        self.app = app
        self.queue = Queue()
        self.threads = []
        log.info( "starting workers" )
        for i in range( nworkers  ):
            worker = threading.Thread( target=self.run_next )
            worker.start()
            self.threads.append( worker )
        log.debug( "%d workers ready", nworkers )

    def run_next( self ):
        """Run the next job, waiting until one is available if neccesary"""
        while 1:
            job = self.queue.get()
            if job is self.STOP_SIGNAL:
                break
            try:
                # Run the job, requeue if not complete
                try:
                    param_dict = dict()
                    param_dict.update( job.incoming )
                    inp_data = {}
                    for name, id in job.inp_data_ids.items():
                        inp_data[name] = job.trans.app.model.Dataset.get( id )
                    out_data = {}
                    for name, id in job.out_data_ids.items():
                        out_data[name] = job.trans.app.model.Dataset.get( id )
                    for name, data in inp_data.items():
                        param_dict[name] = data.file_name
                    for name, data in out_data.items():
                        param_dict[name] = data.file_name
                    
                    #Add children to param_dict
                    pattern = re.compile('\$\{_CHILD___\w+___\w+}')
                    for found in pattern.findall(self.command):
                        found = found[2:-1].split("___")
                        if len(found) != 3: continue
                        try:
                            param_dict['_CHILD___'+found[1]+"___"+found[2]] = inp_data[found[1]].get_child_by_designation(found[2]).file_name
                        except Exception, e:
                            msg = 'commandline error, child substituion: child (%s) of parent (%s) not found -> %s' % (found[2], found[1], e)
                            raise Exception, msg
                    
                    # substituting parameters into the command
                    command_line = string.Template( self.command ).substitute( param_dict )
                except:
                    command_line = "Command Line Unavailable"
                    
                job_state = job()
                if job_state == JOB_WAIT: 
                    self.put( job )
                    #log.debug( "the job has been requeued" )
                elif job_state == JOB_ERROR:
                    log.info( "job ended with an error: "+command_line)
                else:
                    #log.debug( "job left the queue" )
                    pass
            except:
                job.fail("failure running job")
                log.exception( "failure running job: "+command_line )
            
    def put( self, job ):
        """Add a job to the queue (anything that is callable will work here"""
        job.queue = self
        self.queue.put( job )
    
    def shutdown( self ):
        """Attempts to gracefully shut down the worker threads"""
        log.info( "sending stop signal to worker threads" )
        for i in range( len( self.threads ) ):
            self.queue.put( self.STOP_SIGNAL )
        log.info( "job queue stopped" )

class Job( object ):
    """
    A galaxy job -- an external process that will update one or more 'data'
    """
    def __init__(self, trans, command, tool, inp_data_ids={}, out_data_ids={}, incoming={}):
        self.command = command
        self.inp_data_ids = inp_data_ids    
        self.out_data_ids = out_data_ids
        self.incoming = incoming
        self.tool = tool
        self.queue = None
        self.trans = trans
        
    def fail( self, message ):
        """
        Indicate job failure by setting state and message on all output 
        datasets.
        """
        for name, id in self.out_data_ids.items():
            dataset = self.queue.app.model.Dataset.get( id )
            dataset.refresh()
            if dataset:
                dataset.state = dataset.states.ERROR
                dataset.blurb = 'tool error'
                dataset.info = "ERROR: " + message
                dataset.flush()

    def __call__( self ):
        """Returns a state (code) for the run"""
        
        # refresh data
        inp_data = {}
        for name, id in self.inp_data_ids.items():
            inp_data[name] = self.queue.app.model.Dataset.get( id )
        out_data = {}
        for name, id in self.out_data_ids.items():
            out_data[name] = self.queue.app.model.Dataset.get( id )
        
        for idata in inp_data.values():
            # an error in the input data causes us to bail immediately
            if idata.state == idata.states.ERROR:
                self.fail( "error in input data %d" % idata.hid )
            elif idata.state == idata.states.FAKE:
                continue
            elif idata.state != idata.states.OK:
                # need to requeue
                return JOB_WAIT
        
        param_filename = None
        log.debug('job started')

        try:
            param_dict = dict()
            param_dict.update( self.incoming )

            for name, data in inp_data.items():
                param_dict[name] = data.file_name
            for name, data in out_data.items():
                param_dict[name] = data.file_name

            # temporary files for file based parameter transfer
            if "$param_file" in self.command:
                fd, param_filename = tempfile.mkstemp()
                os.close( fd )
                f = open( param_filename, "wt" )
                for key, value in param_dict.items():
                    # parameters can be strings or lists of strings, coerce to list
                    if type(value) != type([]):
                        value = [ value ]
                    for elem in value:
                        f.write( '%s=%s\n' % (key, elem) ) 
                f.close()
                param_dict['param_file'] = param_filename
            
            # custom pre-process setup
            try:
                code = self.tool.get_hook( 'exec_before_process' )
                if code:
                    code( self.queue.app, inp_data=inp_data, out_data=out_data, param_dict=param_dict, tool=self.tool )
            except Exception, e:
                raise Exception, 'before-process-filter error %s' % e

            if self.command:
                try:
                    #Add children to param_dict
                    pattern = re.compile('\$\{_CHILD___\w+___\w+}')
                    for found in pattern.findall(self.command):
                        found = found[2:-1].split("___")
                        if len(found) != 3: continue
                        try:
                            param_dict['_CHILD___'+found[1]+"___"+found[2]] = inp_data[found[1]].get_child_by_designation(found[2]).file_name
                        except Exception, e:
                            msg = 'commandline error, child substituion: child (%s) of parent (%s) not found -> %s' % (found[2], found[1], e)
                            raise Exception, msg
                    
                    # substituting parameters into the command
                    command_line = string.Template( self.command ).substitute( param_dict )
                except Exception, e:
                    # a more user friendly exception
                    msg = 'commandline error, substituting %s  into %s -> %s' % (param_dict, self.command, e)
                    raise Exception, msg

            # default data setup
            #for data in out_data.values():
            #    data.state = data.states.RUNNING
            #    data.blurb = "running"
            #    data.flush()

            # windows fix that for something that I don't fully understand
            # waiting for the stdout to close
            if os.sep == '\\':
                time.sleep(5)

            # set up for pbs (if we're using it
            if asbool(self.trans.app.config.use_pbs) and "/tools/data_source" not in command_line:
                log.debug("importing pbs module")
                import pkg_resources
                pkg_resources.require( "pbs_python" )
                import pbs, random
                from PBSQuery import PBSQuery
                pbs_server = pbs.pbs_default()
                if not pbs_server:
                    self.trans.app.config.use_pbs = False

            # data_source tools don't farm
            #if not self.app.config.use_pbs or re.search("/tools/data_source/", command_line):
            if (not asbool(self.trans.app.config.use_pbs)) or "/tools/data_source/" in command_line:

                for data in out_data.values():
                    data.state = data.states.RUNNING
                    data.blurb = "running"
                    data.flush()

                # start the subprocess
                if self.command:
                    log.debug('executing: %s' % command_line)
                    PIPE   = subprocess.PIPE
                    proc   = subprocess.Popen(args=command_line, shell=True, stdout=PIPE, stderr=PIPE)
                    stdout = proc.stdout.read() 
                    stderr = proc.stderr.read()
                    proc.stdout.close() 
                    proc.stderr.close()
                    log.debug('execution finished: %s' % command_line)
                else:
                    stderr = stdout = ''

            else: 

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

                # set up the job file
                script = "#!/bin/sh\nPATH='%s'\ncd %s\n%s\n" % (os.environ['PATH'], os.getcwd(), command_line)
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

                # get a handle
                conn = pbs.pbs_connect(pbs_server)

                # queue it
                if os.access(job_file, os.R_OK):
                    log.debug("submitting file %s with output %s and error %s" % (job_file, ofile, efile) )
                    log.debug("command is: %s" % command_line)
                    job_id = pbs.pbs_submit(conn, job_attrs, job_file, None, None)

                    # monitor
                    if job_id:
                        p = PBSQuery()
                        job_data = p.getjob(job_id)
                        old_state = job_data[job_id]["job_state"]
                        log.debug("initial state is %s" % old_state)
                        running = False
                        while True:
                            job_data = p.getjob(job_id)
                            if not job_data:
                                break
                            state = job_data[job_id]["job_state"]
                            if state != old_state:
                                log.debug("job state changed from %s to %s" % (old_state, state) )
                            if state == "R" and not running:
                                running = True
                                for data in out_data.values():
                                    data.state = data.states.RUNNING
                                    data.blurb = "running"
                                    data.flush()
                            old_state = state

                        # collect the output
                        ofh = file(ofile, "r")
                        efh = file(efile, "r")
                        stdout = ofh.read()
                        stderr = efh.read()

                    else:
                        stderr = stdout = ''

                else:
                    stderr = stdout = ''

                # clean up the job_file, ofile, efile
                os.unlink(ofile)
                os.unlink(efile)
                os.unlink(job_file)

            # default post job setup
            for data in out_data.values():
                data.state = data.states.OK
                data.blurb = 'done'
                data.peek  = 'no peek'
                data.info  = stdout + stderr
                if data.has_data():
                    data.set_peek()
                else:
                    if stderr: 
                        data.state = data.states.ERROR
                        data.blurb = "error"
                    else:
                        data.blurb = "empty"

            # custom post process setup
            try:
                code = self.tool.get_hook( 'exec_after_process' )
                if code:
                    code( self.queue.app, inp_data=inp_data, out_data=out_data, param_dict=param_dict, 
                          tool=self.tool, stdout=stdout, stderr=stderr )
            except Exception, e:
                raise Exception, 'post-process-filter error %s' % e

        except Exception, e:
            log.exception( e )
            self.fail( "ERROR: %s" % e )

        # store the data
        for data in out_data.values():
            data.flush()

        # remove temporary file
        if param_filename: 
            os.remove( param_filename )
        
        # remove 'fake' datasets 
        for data in inp_data.values():
            if data.state == data.states.FAKE:
                data.delete()
        self.queue.app.model.flush()
        
        log.debug('job ended: %s' % command_line)
        return JOB_OK

import logging
import subprocess
from Queue import Queue
import threading

import re

from galaxy import model
from galaxy.datatypes.data import nice_size
from galaxy.jobs.runners import ClusterJobState, ClusterJobRunner

import os, errno
from time import sleep

log = logging.getLogger( __name__ )

__all__ = [ 'LwrJobRunner' ]

import urllib 
import urllib2
import httplib
import mmap 
import tempfile
import time

import simplejson

class FileStager(object):
    
    def __init__(self, client, command_line, config_files, input_files, output_files, tool_dir, working_directory):
        self.client = client
        self.command_line = command_line
        self.config_files = config_files
        self.input_files = input_files
        self.output_files = output_files
        self.tool_dir = os.path.abspath(tool_dir)
        self.working_directory = working_directory

        self.file_renames = {}

        job_config = client.setup()

        self.new_working_directory = job_config['working_directory']
        self.new_outputs_directory = job_config['outputs_directory']
        self.remote_path_separator = job_config['path_separator']

        self.__initialize_referenced_tool_files()
        self.__upload_tool_files()
        self.__upload_input_files()
        self.__upload_working_directory_files()
        self.__initialize_output_file_renames()
        self.__initialize_task_output_file_renames()
        self.__initialize_config_file_renames()
        self.__rewrite_and_upload_config_files()
        self.__rewrite_command_line()

    def __initialize_referenced_tool_files(self):
        pattern = r"(%s%s\S+)" % (self.tool_dir, os.sep)
        referenced_tool_files = []
        referenced_tool_files += re.findall(pattern, self.command_line)
        if self.config_files != None:
            for config_file in self.config_files:
                referenced_tool_files += re.findall(pattern, self.__read(config_file))
        self.referenced_tool_files = referenced_tool_files

    def __upload_tool_files(self):
        for referenced_tool_file in self.referenced_tool_files:
            tool_upload_response = self.client.upload_tool_file(referenced_tool_file)
            self.file_renames[referenced_tool_file] = tool_upload_response['path']

    def __upload_input_files(self):
        for input_file in self.input_files:
            input_upload_response = self.client.upload_input(input_file)
            self.file_renames[input_file] = input_upload_response['path']
            # TODO: Determine if this is object store safe and what needs to be
            # done if it is not.
            files_path = "%s_files" % input_file[0:-len(".dat")]
            if os.path.exists(files_path):
                for extra_file in os.listdir(files_path):
                    extra_file_path = os.path.join(files_path, extra_file)
                    relative_path = os.path.basename(files_path)
                    extra_file_relative_path = os.path.join(relative_path, extra_file)
                    response = self.client.upload_extra_input(extra_file_path, extra_file_relative_path)
                    self.file_renames[extra_file_path] = response['path']

    def __upload_working_directory_files(self):
        # Task manager stages files into working directory, these need to be uploaded
        for working_directory_file in os.listdir(self.working_directory):
            path = os.path.join(self.working_directory, working_directory_file)
            working_file_response = self.client.upload_working_directory_file(path)
            self.file_renames[path] = working_file_response['path']

    def __initialize_output_file_renames(self):
        for output_file in self.output_files:
            self.file_renames[output_file] = r'%s%s%s' % (self.new_outputs_directory, 
                                                         self.remote_path_separator, 
                                                         os.path.basename(output_file))

    def __initialize_task_output_file_renames(self):
        for output_file in self.output_files:
            name = os.path.basename(output_file)
            self.file_renames[os.path.join(self.working_directory, name)] = r'%s%s%s' % (self.new_working_directory,
                                                                                         self.remote_path_separator,
                                                                                         name)

    def __initialize_config_file_renames(self):
        for config_file in self.config_files:
            self.file_renames[config_file] = r'%s%s%s' % (self.new_working_directory,
                                                         self.remote_path_separator,
                                                         os.path.basename(config_file))

    def __rewrite_paths(self, contents):
        new_contents = contents
        for local_path, remote_path in self.file_renames.iteritems():
            new_contents = new_contents.replace(local_path, remote_path)
        return new_contents

    def __rewrite_and_upload_config_files(self):
        for config_file in self.config_files:
            config_contents = self.__read(config_file)
            new_config_contents = self.__rewrite_paths(config_contents)
            self.client.upload_config_file(config_file, new_config_contents)

    def __rewrite_command_line(self):
        self.rewritten_command_line = self.__rewrite_paths(self.command_line)

    def get_rewritten_command_line(self):
        return self.rewritten_command_line

    def __read(self, path):
        input = open(path, "r")
        try:
            return input.read()
        finally:
            input.close()

        
        
class Client(object):
    """    
    """
    """    
    """
    def __init__(self, remote_host, job_id, private_key=None):
        if not remote_host.endswith("/"):
            remote_host = remote_host + "/"
        ## If we don't have an explicit private_key defined, check for
        ## one embedded in the URL. A URL of the form
        ## https://moo@cow:8913 will try to contact https://cow:8913
        ## with a private key of moo
        private_key_format = "https?://(.*)@.*/?"
        private_key_match= re.match(private_key_format, remote_host)
        if not private_key and private_key_match:
            private_key = private_key_match.group(1)
            remote_host = remote_host.replace("%s@" % private_key, '', 1)
        self.remote_host = remote_host
        self.job_id = job_id
        self.private_key = private_key

    def url_open(self, request, data):
        return urllib2.urlopen(request, data)
        
    def __build_url(self, command, args):
        if self.private_key:
            args["private_key"] = self.private_key
        data = urllib.urlencode(args)
        url = self.remote_host + command + "?" + data
        return url

    def __raw_execute(self, command, args = {}, data = None):
        url = self.__build_url(command, args)
        request = urllib2.Request(url=url, data=data)
        response = self.url_open(request, data)
        return response

    def __raw_execute_and_parse(self, command, args = {}, data = None):
        response = self.__raw_execute(command, args, data)
        return simplejson.loads(response.read())

    def __upload_file(self, action, path, name=None, contents = None):
        """ """
        input = open(path, 'rb')
        try:
            mmapped_input = mmap.mmap(input.fileno(), 0, access = mmap.ACCESS_READ)
            return self.__upload_contents(action, path, mmapped_input, name)
        finally:
            input.close()

    def __upload_contents(self, action, path, contents, name=None):
        if not name:
            name = os.path.basename(path)
        args = {"job_id" : self.job_id, "name" : name}
        return self.__raw_execute_and_parse(action, args, contents)
    
    def upload_tool_file(self, path):
        return self.__upload_file("upload_tool_file", path)

    def upload_input(self, path):
        return self.__upload_file("upload_input", path)

    def upload_extra_input(self, path, relative_name):
        return self.__upload_file("upload_extra_input", path, name=relative_name)

    def upload_config_file(self, path, contents):
        return self.__upload_contents("upload_config_file", path, contents)

    def upload_working_directory_file(self, path):
        return self.__upload_file("upload_working_directory_file", path)

    def _get_output_type(self, name):
        return self.__raw_execute_and_parse('get_output_type', {'name': name,
                                                                'job_id': self.job_id})

    def download_output(self, path, working_directory):
        """ """
        name = os.path.basename(path)
        output_type = self._get_output_type(name)
        response = self.__raw_execute('download_output', {'name' : name,
                                                          "job_id" : self.job_id,
                                                          'output_type': output_type})
        if output_type == 'direct':
            output = open(path, 'wb')
        elif output_type == 'task':
            output = open(os.path.join(working_directory, name), 'wb')
        else:
            raise Exception("No remote output found for dataset with path %s" % path)
        try:
            while True:
                buffer = response.read(1024)
                if buffer == "":
                    break
                output.write(buffer)
        finally:
            output.close()
    
    def launch(self, command_line):
        """ """
        return self.__raw_execute("launch", {"command_line" : command_line,
                                             "job_id" : self.job_id})

    def kill(self):
        return self.__raw_execute("kill", {"job_id" : self.job_id})
    
    def wait(self):
        """ """
        while True:
            complete = self.check_complete()
            if complete:
                return check_complete_response
            time.sleep(1)

    def raw_check_complete(self):
        check_complete_response = self.__raw_execute_and_parse("check_complete", {"job_id" : self.job_id })
        return check_complete_response

    def check_complete(self):
        return self.raw_check_complete()["complete"] == "true"

    def clean(self):
        self.__raw_execute("clean", { "job_id" : self.job_id })

    def setup(self):
        return self.__raw_execute_and_parse("setup", { "job_id" : self.job_id })



class LwrJobRunner( ClusterJobRunner ):
    """
    LWR Job Runner
    """
    runner_name = "LWRRunner"

    def __init__( self, app ):
        """Start the job runner """
        super( LwrJobRunner, self ).__init__( app )
        self._init_monitor_thread()
        log.info( "starting LWR workers" )
        self._init_worker_threads()

    def check_watched_item(self, job_state):
        try:
            client = self.get_client_from_state(job_state)
            complete = client.check_complete()
        except Exception:
            # An orphaned job was put into the queue at app startup, so remote server went down
            # either way we are done I guess.
            self.mark_as_finished(job_state)
            return None
        if complete:
            self.mark_as_finished(job_state)
            return None
        return job_state

    def queue_job(self, job_wrapper):
        stderr = stdout = command_line = ''

        runner_url = job_wrapper.get_job_runner_url()

        try:
            job_wrapper.prepare()
            if hasattr(job_wrapper, 'prepare_input_files_cmds') and job_wrapper.prepare_input_files_cmds is not None:
                for cmd in job_wrapper.prepare_input_files_cmds: # run the commands to stage the input files
                    #log.debug( 'executing: %s' % cmd )
                    if 0 != os.system(cmd):
                        raise Exception('Error running file staging command: %s' % cmd)
                job_wrapper.prepare_input_files_cmds = None # prevent them from being used in-line
            command_line = self.build_command_line( job_wrapper, include_metadata=False )
        except:
            job_wrapper.fail( "failure preparing job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return

        # If we were able to get a command line, run the job
        if not command_line:
            job_wrapper.finish( '', '' )
            return

        try:
            #log.debug( 'executing: %s' % command_line )
            client = self.get_client_from_wrapper(job_wrapper)
            output_files = self.get_output_files(job_wrapper)
            input_files = job_wrapper.get_input_fnames()
            working_directory = job_wrapper.working_directory
            file_stager = FileStager(client, command_line, job_wrapper.extra_filenames, input_files, output_files, job_wrapper.tool.tool_dir, working_directory)
            rebuilt_command_line = file_stager.get_rewritten_command_line()
            client.launch( rebuilt_command_line )
            job_wrapper.set_runner( runner_url, job_wrapper.job_id )
            job_wrapper.change_state( model.Job.states.RUNNING )

        except Exception, exc:
            job_wrapper.fail( "failure running job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return

        lwr_job_state = ClusterJobState()
        lwr_job_state.job_wrapper = job_wrapper
        lwr_job_state.job_id = job_wrapper.job_id
        lwr_job_state.old_state = True
        lwr_job_state.running = True
        lwr_job_state.runner_url = runner_url
        self.monitor_job(lwr_job_state)

    def get_output_files(self, job_wrapper):
        output_fnames = job_wrapper.get_output_fnames()
        return [ str( o ) for o in output_fnames ]


    def determine_lwr_url(self, url):
        lwr_url = url[ len( 'lwr://' ) : ]
        return  lwr_url 

    def get_client_from_wrapper(self, job_wrapper):
        job_id = job_wrapper.job_id
        if hasattr(job_wrapper, 'task_id'):
            job_id = "%s_%s" % (job_id, job_wrapper.task_id)
        return self.get_client( job_wrapper.get_job_runner_url(), job_id )

    def get_client_from_state(self, job_state):
        job_runner = job_state.runner_url
        job_id = job_state.job_id
        return self.get_client(job_runner, job_id)

    def get_client(self, job_runner, job_id):
        lwr_url = self.determine_lwr_url( job_runner )
        return Client(lwr_url, job_id)   

    def finish_job( self, job_state ):
        stderr = stdout = command_line = ''
        job_wrapper = job_state.job_wrapper
        try:
            client = self.get_client_from_state(job_state)

            run_results = client.raw_check_complete()
            log.debug('run_results %s' % run_results )
            stdout = run_results['stdout']
            stderr = run_results['stderr']

            if job_wrapper.get_state() not in [ model.Job.states.ERROR, model.Job.states.DELETED ]:
                output_files = self.get_output_files(job_wrapper)
                for output_file in output_files:
                    client.download_output(output_file, working_directory=job_wrapper.working_directory)
            client.clean()
            log.debug('execution finished: %s' % command_line)
        except Exception, exc:
            job_wrapper.fail( "failure running job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return
        #run the metadata setting script here
        #this is terminate-able when output dataset/job is deleted
        #so that long running set_meta()s can be canceled without having to reboot the server
        if job_wrapper.get_state() not in [ model.Job.states.ERROR, model.Job.states.DELETED ] and self.app.config.set_metadata_externally and job_wrapper.output_paths:
            external_metadata_script = job_wrapper.setup_external_metadata( output_fnames = job_wrapper.get_output_fnames(),
                                                                            set_extension = True,
                                                                            kwds = { 'overwrite' : False } ) #we don't want to overwrite metadata that was copied over in init_meta(), as per established behavior
            log.debug( 'executing external set_meta script for job %d: %s' % ( job_wrapper.job_id, external_metadata_script ) )
            external_metadata_proc = subprocess.Popen( args = external_metadata_script, 
                                         shell = True, 
                                         env = os.environ,
                                         preexec_fn = os.setpgrp )
            job_wrapper.external_output_metadata.set_job_runner_external_pid( external_metadata_proc.pid, self.sa_session )
            external_metadata_proc.wait()
            log.debug( 'execution of external set_meta finished for job %d' % job_wrapper.job_id )

        # Finish the job                
        try:
            job_wrapper.finish( stdout, stderr )
        except:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)

    def fail_job( self, job_state ):
        """
        Seperated out so we can use the worker threads for it.
        """
        self.stop_job( self.sa_session.query( self.app.model.Job ).get( job_state.job_wrapper.job_id ) )
        job_state.job_wrapper.fail( job_state.fail_message )

    def shutdown( self ):
        """Attempts to gracefully shut down the worker threads"""
        log.info( "sending stop signal to worker threads" )
        for i in range( len( self.threads ) ):
            self.queue.put( self.STOP_SIGNAL )
        log.info( "local job runner stopped" )

    def check_pid( self, pid ):
        try:
            os.kill( pid, 0 )
            return True
        except OSError, e:
            if e.errno == errno.ESRCH:
                log.debug( "check_pid(): PID %d is dead" % pid )
            else:
                log.warning( "check_pid(): Got errno %s when attempting to check PID %d: %s" %( errno.errorcode[e.errno], pid, e.strerror ) )
            return False

    def stop_job( self, job ):
        #if our local job has JobExternalOutputMetadata associated, then our primary job has to have already finished
        job_ext_output_metadata = job.get_external_output_metadata()
        if job_ext_output_metadata: 
            pid = job_ext_output_metadata[0].job_runner_external_pid #every JobExternalOutputMetadata has a pid set, we just need to take from one of them
            if pid in [ None, '' ]:
                log.warning( "stop_job(): %s: no PID in database for job, unable to stop" % job.id )
                return
            pid = int( pid )
            if not self.check_pid( pid ):
                log.warning( "stop_job(): %s: PID %d was already dead or can't be signaled" % ( job.id, pid ) )
                return
            for sig in [ 15, 9 ]:
                try:
                    os.killpg( pid, sig )
                except OSError, e:
                    log.warning( "stop_job(): %s: Got errno %s when attempting to signal %d to PID %d: %s" % ( job.id, errno.errorcode[e.errno], sig, pid, e.strerror ) )
                    return  # give up
                sleep( 2 )
                if not self.check_pid( pid ):
                    log.debug( "stop_job(): %s: PID %d successfully killed with signal %d" %( job.id, pid, sig ) )
                    return
                else:
                    log.warning( "stop_job(): %s: PID %d refuses to die after signaling TERM/KILL" %( job.id, pid ) )
        else:
            # Remote kill
            lwr_url = job.job_runner_name
            job_id = job.job_runner_external_id
            log.debug("Attempt remote lwr kill of job with url %s and id %s" % (lwr_url, job_id))
            client = self.get_client(lwr_url, job_id)
            client.kill()


    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_state = ClusterJobState()
        job_state.job_id = str( job.get_job_runner_external_id() )
        job_state.runner_url = job_wrapper.get_job_runner_url()
        job_wrapper.command_line = job.get_command_line()
        job_state.job_wrapper = job_wrapper
        if job.get_state() == model.Job.states.RUNNING:
            log.debug( "(LWR/%s) is still in running state, adding to the LWR queue" % ( job.get_id()) )
            job_state.old_state = True
            job_state.running = True
            self.monitor_queue.put( job_state )
        elif job.get_state() == model.Job.states.QUEUED:
            # LWR doesn't queue currently, so this indicates galaxy was shutoff while 
            # job was being staged. Not sure how to recover from that. 
            job_state.job_wrapper.fail( "This job was killed when Galaxy was restarted.  Please retry the job." )

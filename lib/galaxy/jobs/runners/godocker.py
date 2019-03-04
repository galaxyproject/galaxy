import json
import logging
import time
from datetime import datetime

import requests

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)


log = logging.getLogger(__name__)

__all__ = ('GodockerJobRunner', )


class Godocker(object):
    """
    API parameters
    """

    def __init__(self, server, login, apikey, noCert):
        self.token = None
        self.server = server
        self.login = login
        self.apikey = apikey
        self.noCert = noCert

    def setToken(self, token):
        self.token = token

    def http_post_request(self, query, data, header):
        """ post request with query """

        verify_ssl = not self.noCert
        try:
            url = self.server + query
            res = requests.post(url, data, headers=header, verify=verify_ssl)

        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            log.error('A transport error occurred in the GoDocker job runner:', e)
            return False

        return self.test_status_code(res)

    def http_get_request(self, query, header):
        """ get request with query, server and header required """

        # remove warnings if using --no-certificate
        requests.packages.urllib3.disable_warnings()
        verify_ssl = not self.noCert
        try:
            url = self.server + query
            res = requests.get(url, headers=header, verify=verify_ssl)

        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            log.error('A communication error occurred in the GoDocker job runner:', e)
            return False

        return self.test_status_code(res)

    def http_delete_request(self, query, header):
        """ delete request with query, server and header required """

        # remove warnings if using --no-certificate
        requests.packages.urllib3.disable_warnings()
        verify_ssl = not self.noCert
        try:
            url = self.server + query
            res = requests.delete(url, headers=header, verify=verify_ssl)

        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            log.error('A communication error occurred in the GoDocker job runner:', e)
            return False

        return self.test_status_code(res)

    def http_put_request(self, query, data, header):
        """ put request with query """

        # remove warnings if using --no-certificate
        requests.packages.urllib3.disable_warnings()
        verify_ssl = not self.noCert
        try:
            url = self.server + query
            res = requests.put(url, data, headers=header, verify=verify_ssl)

        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            log.error('A communication error occurred in the GoDocker job runner:', e)
            return False

        return self.test_status_code(res)

    def test_status_code(self, httpresult):
        """ exit if status code is 401 or 403 or 404 or 200"""
        if httpresult.status_code == 401:
            log.debug('Unauthorized : this server could not verify that you are authorized to access the document you requested.')

        elif httpresult.status_code == 403:
            log.debug('Forbidden : Access was denied to this resource. Not authorized to access this resource.')

        elif httpresult.status_code == 404:
            log.debug('Not Found : The resource could not be found.')

        elif httpresult.status_code == 200:
            return httpresult

        return False


class GodockerJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "GodockerJobRunner"

    def __init__(self, app, nworkers, **kwargs):
        """ 1: Get runner_param_specs from job_conf.xml
            2: Initialise job runner parent object
            3: Login to godocker and store the token
            4: Start the worker and monitor threads
        """
        runner_param_specs = dict(godocker_master=dict(map=str), user=dict(map=str), key=dict(map=str), godocker_project=dict(map=str))
        if 'runner_param_specs' not in kwargs:
            kwargs['runner_param_specs'] = dict()
        kwargs['runner_param_specs'].update(runner_param_specs)

        # Start the job runner parent object
        super(GodockerJobRunner, self).__init__(app, nworkers, **kwargs)

        # godocker API login call
        self.auth = self.login(self.runner_params["key"], self.runner_params["user"], self.runner_params["godocker_master"])

        if not self.auth:
            log.error("Authentication failure, GoDocker runner cannot be started")
        else:
            """ Following methods starts threads.
                These methods invoke threading.Thread(name,target)
                      which in turn invokes methods monitor() and run_next().
            """
            self._init_monitor_thread()
            self._init_worker_threads()

    def queue_job(self, job_wrapper):
        """ Create job script and submit it to godocker """
        if not self.prepare_job(job_wrapper, include_metadata=False, include_work_dir_outputs=True, modify_command_for_container=False):
            return

        job_destination = job_wrapper.job_destination
        """ Submit job to godocker """
        job_id = self.post_task(job_wrapper)
        if not job_id:
            log.error("Job creation failure.  No Response from GoDocker")
            job_wrapper.fail("Not submitted")
        else:
            log.debug("Starting queue_job for job " + job_id)
            # Create an object of AsynchronousJobState and add it to the monitor queue.
            ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper, job_id=job_id, job_destination=job_destination)
            self.monitor_queue.put(ajs)

    def check_watched_item(self, job_state):
        """ Get the job current status from GoDocker
                    using job_id and update the status in galaxy.
            If the job execution is successful, call
                    mark_as_finished() and return 'None' to galaxy.
            else if the job failed, call mark_as_failed()
                    and return 'None' to galaxy.
            else if the job is running or in pending state, simply
                    return the 'AsynchronousJobState object' (job_state).
        """
        ''' This function is called by check_watched_items() where
                    param job_state is an object of AsynchronousJobState.
            Expected return type of this function is None or
                    AsynchronousJobState object with updated running status.
        '''
        """ Get task from GoDocker """
        job_status_god = self.get_task(job_state.job_id)
        log.debug("Job ID: " + str(job_state.job_id) + " Job Status: " + str(job_status_god['status']['primary']))

        if job_status_god['status']['primary'] == "over":
            job_state.running = False
            job_state.job_wrapper.change_state(model.Job.states.OK)
            if self.create_log_file(job_state, job_status_god):
                self.mark_as_finished(job_state)
            else:
                self.mark_as_failed(job_state)
            '''The function mark_as_finished() executes:
                        self.work_queue.put((self.finish_job, job_state))
           *self.finish_job ->
            job_state.job_wrapper.finish( stdout, stderr, exit_code )
            job_state.job_wrapper.reclaim_ownership()
            job_state.cleanup()
           *self.work_queue.put( method , arg ) ->
            The run_next() method starts execution on starting worker threads.
            This run_next() method executes method(arg)
                        by using self.work_queue.get()
           *Possible outcomes of finish_job(job_state) ->
            job_state.job_wrapper.finish( stdout, stderr, exit_code )
            job_state.job_wrapper.fail( "Unable to finish job", exception=True)
           *Similar workflow is done for mark_as_failed() method.
            '''
            return None

        elif job_status_god['status']['primary'] == "running":
            job_state.running = True
            job_state.job_wrapper.change_state(model.Job.states.RUNNING)
            return job_state

        elif job_status_god['status']['primary'] == "pending":
            return job_state

        elif job_status_god['status']['exitcode'] not in [None, 0]:
            job_state.running = False
            job_state.job_wrapper.change_state(model.Job.states.ERROR)
            self.create_log_file(job_state, job_status_god)
            self.mark_as_failed(job_state)
            return None

        else:
            job_state.running = False
            self.create_log_file(job_state, job_status_god)
            self.mark_as_failed(job_state)
            return None

    def stop_job(self, job_wrapper):
        """ Attempts to delete a dispatched executing Job in GoDocker """
        '''This function is called by fail_job()
           where param job = self.sa_session.query( self.app.model.Job ).get( job_state.job_wrapper.job_id )
           No Return data expected
        '''
        job_id = job_wrapper.job_id
        log.debug("STOP JOB EXECUTION OF JOB ID: " + str(job_id))
        # Get task status from GoDocker.
        job_status_god = self.get_task_status(job_id)
        if job_status_god['status']['primary'] != "over":
            # Initiate a delete call,if the job is running in GoDocker.
            self.delete_task(job_id)
        return None

    def recover(self, job, job_wrapper):
        """ Recovers jobs stuck in the queued/running state when Galaxy started """
        """ This method is called by galaxy at the time of startup.
            Jobs in Running & Queued status in galaxy are put in the monitor_queue by creating an AsynchronousJobState object
        """
        job_id = job_wrapper.job_id
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper)
        ajs.job_id = str(job_id)
        ajs.job_destination = job_wrapper.job_destination
        job_wrapper.command_line = job.command_line
        ajs.job_wrapper = job_wrapper
        if job.state == model.Job.states.RUNNING:
            log.debug("(%s/%s) is still in running state, adding to the god queue" % (job.id, job.get_job_runner_external_id()))
            ajs.old_state = 'R'
            ajs.running = True
            self.monitor_queue.put(ajs)

        elif job.state == model.Job.states.QUEUED:
            log.debug("(%s/%s) is still in god queued state, adding to the god queue" % (job.id, job.get_job_runner_external_id()))
            ajs.old_state = 'Q'
            ajs.running = False
            self.monitor_queue.put(ajs)

    # Helper functions

    def create_log_file(self, job_state, job_status_god):
        """ Create log files in galaxy, namely error_file, output_file, exit_code_file
            Return true, if all the file creations are successful
        """
        path = None
        for vol in job_status_god['container']['volumes']:
            if vol['name'] == "go-docker":
                path = str(vol['path'])
        if path:
            god_output_file = path + "/god.log"
            god_error_file = path + "/god.err"
            try:
                # Read from GoDocker output_file and write it into galaxy output_file.
                f = open(god_output_file, "r")
                out_log = f.read()
                log_file = open(job_state.output_file, "w")
                log_file.write(out_log)
                log_file.close()
                f.close()
                # Read from GoDocker error_file and write it into galaxy error_file.
                f = open(god_error_file, "r")
                out_log = f.read()
                log_file = open(job_state.error_file, "w")
                log_file.write(out_log)
                log_file.close()
                f.close()
                # Read from GoDocker exit_code and write it into galaxy exit_code_file.
                out_log = str(job_status_god['status']['exitcode'])
                log_file = open(job_state.exit_code_file, "w")
                log_file.write(out_log)
                log_file.close()
                f.close()
                log.debug("CREATE OUTPUT FILE: " + str(job_state.output_file))
                log.debug("CREATE ERROR FILE: " + str(job_state.error_file))
                log.debug("CREATE EXIT CODE FILE: " + str(job_state.exit_code_file))
            except IOError as e:
                log.error('Could not access task log file %s' % str(e))
                log.debug("IO Error occurred when accessing the files.")
                return False
        return True

    # GoDocker API helper functions

    def login(self, apikey, login, server, noCert=False):
        """ Login to GoDocker and return the token
            Create Login model schema of GoDocker and call the http_post_request method.
        """
        log.debug("LOGIN TASK TO BE EXECUTED \n")
        log.debug("GODOCKER LOGIN: " + str(login))
        data = json.dumps({'user': login, 'apikey': apikey})
        # Create object of Godocker class
        g_auth = Godocker(server, login, apikey, noCert)
        auth = g_auth.http_post_request("/api/1.0/authenticate", data, {'Content-type': 'application/json', 'Accept': 'application/json'})
        if not auth:
            log.error("GoDocker authentication Error.")
        else:
            log.debug("GoDocker authentication successful.")
            token = auth.json()['token']
            g_auth.setToken(token)
        # Return the object of Godocker class
        return g_auth

    def post_task(self, job_wrapper):
        """ Sumbit job to GoDocker and return jobid
            Create Job model schema of GoDocker and call the http_post_request method.
        """
        # Get the params from <destination> tag in job_conf by using job_destination.params[param]
        if self.auth.token:
            job_destination = job_wrapper.job_destination
            try:
                docker_cpu = int(job_destination.params["docker_cpu"])
            except Exception:
                docker_cpu = 1
            try:
                docker_ram = int(job_destination.params["docker_memory"])
            except Exception:
                docker_ram = 1
            try:
                docker_image = self._find_container(job_wrapper).container_id
                log.debug("GoDocker runner using container %s.", docker_image)
            except Exception:
                log.error("Unable to find docker_image for job %s, failing." % job_wrapper.job_id)
                return False

            volumes = []
            labels = []
            tags_tab = ['galaxy', job_wrapper.tool.id]
            tasks_depends = []
            name = job_wrapper.tool.name
            description = "galaxy job"
            array = None
            project = None
            try:
                project = str(self.runner_params["godocker_project"])
            except KeyError:
                log.debug("godocker_project not defined, using default.")
            try:
                volume = job_destination.params["godocker_volumes"]
                volume = volume.split(",")
                for i in volume:
                    temp = dict({"name": i})
                    volumes.append(temp)
            except Exception:
                log.debug("godocker_volume not set, using default.")

            dt = datetime.now()
            # Enable galaxy venv in the docker containers
            try:
                if(job_destination.params["virtualenv"] == "true"):
                    GALAXY_VENV_TEMPLATE = """GALAXY_VIRTUAL_ENV="%s"; if [ "$GALAXY_VIRTUAL_ENV" != "None" -a -z "$VIRTUAL_ENV" -a -f "$GALAXY_VIRTUAL_ENV/bin/activate" ]; then . "$GALAXY_VIRTUAL_ENV/bin/activate"; fi;"""
                    venv = GALAXY_VENV_TEMPLATE % job_wrapper.galaxy_virtual_env
                    command = "#!/bin/bash\n" + "cd " + job_wrapper.working_directory + "\n" + venv + "\n" + job_wrapper.runner_command_line
                else:
                    command = "#!/bin/bash\n" + "cd " + job_wrapper.working_directory + "\n" + job_wrapper.runner_command_line
            except Exception:
                command = "#!/bin/bash\n" + "cd " + job_wrapper.working_directory + "\n" + job_wrapper.runner_command_line

            # GoDocker Job model schema
            job = {
                'date': time.mktime(dt.timetuple()),
                'meta': {
                    'name': name,
                    'description': description,
                    'tags': tags_tab
                },
                'requirements': {
                    'cpu': docker_cpu,
                    'ram': docker_ram,
                    'array': {'values': array},
                    'label': labels,
                    'tasks': tasks_depends,
                    'tmpstorage': None
                },
                'container': {
                    'image': str(docker_image),
                    'volumes': volumes,
                    'network': True,
                    'id': None,
                    'meta': None,
                    'stats': None,
                    'ports': [],
                    'root': False
                },
                'command': {
                    'interactive': False,
                    'cmd': command,
                },
                'status': {
                    'primary': None,
                    'secondary': None
                }
            }
            if project is not None:
                job['user'] = {"project": project}

            result = self.auth.http_post_request(
                "/api/1.0/task", json.dumps(job),
                {'Authorization': 'Bearer ' + self.auth.token, 'Content-type': 'application/json', 'Accept': 'application/json'}
            )
            # Return job_id
            return str(result.json()['id'])

    def get_task(self, job_id):
        """ Get job details from GoDocker and return the job.
            Pass job_id to the http_get_request method.
        """
        job = False
        if self.auth.token:
            result = self.auth.http_get_request("/api/1.0/task/" + str(job_id), {'Authorization': 'Bearer ' + self.auth.token})
            job = result.json()
        # Return the job
        return job

    def task_suspend(self, job_id):
        """ Suspend actively running job in galaxy.
            Pass job_id to the http_get_request method.
        """
        job = False
        if self.auth.token:
            result = self.auth.http_get_request("/api/1.0/task/" + str(job_id) + "/suspend", {'Authorization': 'Bearer ' + self.auth.token})
            job = result.json()
        # Return the job
        return job

    def get_task_status(self, job_id):
        """ Get job status from GoDocker and return the status of job.
            Pass job_id to http_get_request method.
        """
        job = False
        if self.auth.token:
            result = self.auth.http_get_request("/api/1.0/task/" + str(job_id) + "/status", {'Authorization': 'Bearer ' + self.auth.token})
            job = result.json()
        # Return task status
        return job

    def delete_task(self, job_id):
        """ Delete a suspended task in GoDocker.
            Pass job_id to http_delete_request method.
        """
        job = False
        if self.auth.token:
            result = self.auth.http_delete_request("/api/1.0/task/" + str(job_id), {'Authorization': 'Bearer ' + self.auth.token})
            job = result.json()
        # Return the job
        return job

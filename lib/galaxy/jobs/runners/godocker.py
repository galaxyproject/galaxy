import logging
import os
import json
import time
import inspect
import requests
from datetime import datetime

from galaxy import model
from galaxy.jobs.runners import AsynchronousJobState, AsynchronousJobRunner, GALAXY_VENV_TEMPLATE


log = logging.getLogger(__name__)

__all__ = ['GodockerJobRunner']

class Godocker(object):
    """
    API parameters 
    """
    def __init__(self, server, login, apikey,noCert):
        self.token = None
        self.server = server
        self.login = login
        self.apikey = apikey
        self.noCert = noCert

    def setToken(self, token):
        self.token = token

    def http_post_request(self, query, data, header):
        """ post request with query """

        #remove warnings if using --no-certificate
        requests.packages.urllib3.disable_warnings()
        verify_ssl = not self.noCert
        try:
            url= self.server+query
            res = requests.post(url, data, headers=header, verify=verify_ssl)
            print('Godocker Response:',res, "\n")

        except requests.exceptions.ConnectionError as e:
            print('A Connection error occurred:', e)
            if re.search("SSL3_GET_SERVER_CERTIFICATE", str(e)):
                print("Use the --no-certificate option if you trust the remote godocker server certificate.")
            return False

        except requests.exceptions.HTTPError as e:
            print('A HTTP error occurred:', e)
            return False

        return self.test_status_code(res)
        

    def http_get_request(self, query, header):
        """ get request with query, server and header required """

        #remove warnings if using --no-certificate
        requests.packages.urllib3.disable_warnings()
        verify_ssl = not self.noCert
        try:
            url= self.server+query
            res = requests.get(url, headers=header, verify=verify_ssl)

        except requests.exceptions.ConnectionError as e:
            print('A Connection error occurred:', e)
            return False

        except requests.exceptions.HTTPError as e:
            print('A HTTP error occurred:', e)
            return False

        return self.test_status_code(res)

    def http_delete_request(self, query, header):
        """ delete request with query, server and header required """

        #remove warnings if using --no-certificate
        requests.packages.urllib3.disable_warnings()
        verify_ssl = not self.noCert
        try:
            url= self.server+query
            res = requests.delete(url, headers=header, verify=verify_ssl)

        except requests.exceptions.ConnectionError as e:
            print('A Connection error occurred:', e)
            return False

        except requests.exceptions.HTTPError as e:
            print('A HTTP error occurred:', e)
            return False

        return self.test_status_code(res)

    def http_put_request(self, query, data, header):
        """ put request with query """

        #remove warnings if using --no-certificate
        requests.packages.urllib3.disable_warnings()
        verify_ssl = not self.noCert
        try:
            url= self.server+query
            res = requests.put(url, data, headers=header, verify=verify_ssl)

        except requests.exceptions.ConnectionError as e:
            print('A Connection error occurred:', e)
            return False

        except requests.exceptions.HTTPError as e:
            print('A HTTP error occurred:', e)
            return False

        return self.test_status_code(res)
        

    def test_status_code(self,httpresult):
        """ exit if status code is 401 or 403 or 404 or 200"""
        if httpresult.status_code == 401:
            print('Unauthorized : this server could not verify that you are authorized to access the document you requested.')

        elif httpresult.status_code == 403:
            print('Forbidden : Access was denied to this resource. Not authorized to access this resource.')

        elif httpresult.status_code == 404:
            print('Not Found : The resource could not be found.')

        elif httpresult.status_code == 200:
            return httpresult

        return False


class GodockerJobRunner(AsynchronousJobRunner):
    """
	Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "GodockerJobRunner"
    
    def __init__(self, app, nworkers, **kwargs):

    	log.debug("Loading app %s",app)
        #self.server = "https://godocker.genouest.org" #"https://docker-ui/genouest.org"
    	runner_param_specs = dict(
    		godocker_master = dict(map = str),
    		user = dict(map = str),
    		key = dict(map = str),
            godocker_project = dict(map = str)
        )
        if 'runner_param_specs' not in kwargs:
        	kwargs['runner_param_specs'] = dict()
        
        kwargs['runner_param_specs'].update(runner_param_specs)
        super(GodockerJobRunner, self).__init__(app, nworkers, **kwargs)
        
        log.debug("runner_params before godocker login: \n")
        log.debug(self.runner_params)
        # godocker API login call to be done here
        self.auth = self.login(self.runner_params["key"],self.runner_params["user"],self.runner_params["godocker_master"])
        log.debug("runner_params after godocker login: \n")
        log.debug(self.runner_params)
        
        if not self.auth:
            log.debug("Authentication failure!! Job cannot be started")
        else:
            """ Following methods starts threads.
                threading.Thread(name,target) invokes methods monitor() and run_next()
            """
            self._init_monitor_thread()
            self._init_worker_threads()


    def queue_job(self, job_wrapper):

    	#job_name = self.get_unique_job_name(job_wrapper)
        if not self.prepare_job(job_wrapper, include_metadata=False, include_work_dir_outputs=True, modify_command_for_container=False):
            return

        job_destination = job_wrapper.job_destination
        log.debug("JOB_WRAPPER")
        self.get_structure(job_wrapper)
        log.debug("END OF JOB_WRAPPER \n")
        log.debug(job_wrapper.output_paths)
       
        job_id = self.post_task(job_wrapper)
        log.debug("Job response from GoDocker")
        log.debug(job_id)
        log.debug(job_wrapper.working_directory)
        if not job_id:
            log.debug("Job creation faliure!! No Response from GoDocker")
        else:
            log.debug("Starting queue_job for job " + job_id)
            ajs = AsynchronousJobState(files_dir = job_wrapper.working_directory,job_wrapper = job_wrapper,job_id = job_id,job_destination = job_destination)
            self.monitor_queue.put(ajs)
        return None


    def check_watched_item(self, job_state):
        # Get the job current status from godocker using jobid
        ''' This function is called by check_watched_items()  where param job_state is an object of AsynchronousJobState
            Expected return type of this function is None or AsynchronousJobState object with updated running status
        '''
        log.debug("JOB ID: ")
        log.debug(job_state.job_id)
        job_status_god = self.get_task(job_state.job_id)
        #self.get_structure(job_state.job_wrapper)
        print("\n JOB STATUS FROM GODOCKER \n")
        #log.debug(job_status_god)
        #self.get_structure(job_status_god)
        #print("\nEND OF JOB STATUS\n")
        
        if job_status_god['status']['primary'] == "over":
            job_state.running = False
            job_state.job_wrapper.change_state(model.Job.states.OK)
            self.create_log_file(job_state,job_status_god)
            self.mark_as_finished(job_state)
            ''' This function executes: self.work_queue.put( ( self.finish_job, job_state ) )
                self.finish_job -> 
                                job_state.job_wrapper.finish( stdout, stderr, exit_code )
                                job_state.job_wrapper.reclaim_ownership()
                                job_state.cleanup()
                self.work_queue.put( method , arg ) -> 
                                                    The run_next() method starts execution on starting worker threads. 
                                                    This run_next() method executes method(arg) by self.work_queue.get()
                                                    Possible outcomes of finish_job(job_state) -> 
                                                                       job_state.job_wrapper.finish( stdout, stderr, exit_code )
                                                                       job_state.job_wrapper.fail( "Unable to finish job", exception=True)
            '''
            return None
        
        elif job_status_god['status']['primary'] == "running":
            job_state.running = True
            job_state.job_wrapper.change_state(model.Job.states.RUNNING)
            return job_state
        
        elif job_status_god['status']['primary'] == "pending":
            #job_state.job_wrapper.change_state(model.Job.states.WAITING or QUEUED)
            return job_state
       
        elif job_status_god['status']['exitcode'] not in [None,0]:
            job_state.running = False
            job_state.job_wrapper.change_state(model.Job.states.ERROR)
            self.create_log_file(job_state,job_status_god)
            self.mark_as_failed(job_state)
            return None
        
        else:
            job_state.running = False
            self.create_log_file(job_state,job_status_god)
            self.mark_as_failed(job_state)
            return None
        
        # Possible Job states: state["secondary"]= suspended | running | kill requested | suspend requested
        #Update the job status to galaxy here
        

    def stop_job(self,job):
    	#Call the godocker API here
        '''This function is called by fail_job() 
           where param job = self.sa_session.query( self.app.model.Job ).get( job_state.job_wrapper.job_id )
           No Return data expected 
        '''  
        log.debug(job)
        log.debug("STOP JOB EXECUTING")
        log.debug(job.id)
        log.debug(job.job_runner_external_id)
        self.get_structure(job)
        job_status_god = self.get_task_status(job.id)
        if job_status_god['status']['primary'] != "over":
            self.delete_task(job.id)
        return None
    
    def recover(self,job ,job_wrapper):
        log.debug("\nINSIDE RECOVER METHOD: JOB STRUCTURE\n")
        self.get_structure(job)
        log.debug("\nEND OF JOB STRCUTURE\n")
    	job_id = job_wrapper.job_id
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper)
        ajs.job_id = str( job_id )
        #god_job_state.runner_url = job_wrapper.get_job_runner_url()
        ajs.job_destination = job_wrapper.job_destination
        job_wrapper.command_line = job.command_line
        ajs.job_wrapper = job_wrapper
        if job.state == model.Job.states.RUNNING:
            log.debug( "(%s/%s) is still in running state, adding to the god queue" % ( job.id, job.get_job_runner_external_id() ) )
            ajs.old_state = 'R'
            ajs.running = True
            self.monitor_queue.put(ajs)

        elif job.state == model.Job.states.QUEUED:
            log.debug( "(%s/%s) is still in god queued state, adding to the god queue" % ( job.id, job.get_job_runner_external_id() ) )
            ajs.old_state = 'Q'
            ajs.running = False
            self.monitor_queue.put(ajs)
	
    #Helper functions
    def get_unique_job_name(self, job_wrapper):
        return "god-" + job_wrapper.get_id_tag()

    def create_log_file(self, job_state, job_status_god):
        log = ""
        path = None
        for vol in job_status_god['container']['volumes']:
            if vol['name']=="go-docker":
                path = str(vol['path'])
        if path:
            god_output_file = path+"/god.log"
            god_error_file = path+"/god.err"
            f = open(god_output_file,"r")
            out_log = f.read()
            log_file = open(job_state.output_file,"w")
            log_file.write(out_log)
            log_file.close()
            f.close()
            f = open(god_error_file,"r")
            out_log = f.read()
            log_file = open(job_state.error_file,"w")
            log_file.write(out_log)
            log_file.close()
            f.close()
            out_log = str(job_status_god['status']['exitcode'])
            log_file = open(job_state.exit_code_file,"w")
            log_file.write(out_log)
            log_file.close()
            f.close()
            print("\nPRINT OUTPUT FILE: ")
            print(job_state.output_file)
            print("\nPRINT ERROR FILE: ")
            print(job_state.error_file)
        return
        

    #GoDocker API helper functions

    def login(self,apikey,login,server,noCert = False):
        log.debug("LOGIN TASK TO BE EXECUTED \n")
        log.warn("GODOCKER LOGIN: "+str(login)+":"+str(apikey))
        data=json.dumps({'user': login, 'apikey': apikey})
        g_auth = Godocker(server,login,apikey,noCert)
        auth = g_auth.http_post_request("/api/1.0/authenticate",data,{'Content-type': 'application/json','Accept': 'application/json'})
        self.get_structure(auth)
        if not auth:
            print("Authentication Error!!")
        else:
            token = auth.json()['token']
            g_auth.setToken(token)
            log.debug(token)
        log.debug("END OF LOGIN TASK \n")
        return g_auth


    def post_task(self,job_wrapper):
        #Sumbit job to godocker
        #Auth.authenticate()
        if self.auth.token:
            log.debug("\n INSIDE JOB CREATION TEMPLATE \n")
            job_destination = job_wrapper.job_destination
            #docker_repo = job_destination.params["docker_repo_override"]
            #docker_owner = job_destination.params["docker_owner_override"]
            #docker_image = job_destination.params["docker_default_container_id"]
            #docker_tags = job_destination.params["docker_tag_override"]
            docker_image = self._find_container(job_wrapper).container_id
            log.debug("OSALLOU use image "+docker_image)
          
            docker_cpu = job_destination.params["docker_cpu"]
            docker_ram = job_destination.params["docker_memory"]

        
            #volume = "home"
            #docker_image="centos:latest"
            volumes=[]
            labels=[]
            #tags
            #tags_tab = docker_tags.split(",")
            tags_tab = ['galaxy',job_wrapper.tool.id]

            # manage depends
            tasks_depends = []
            name = job_wrapper.tool.name
            description= "example job"
            array = None
            log.debug(self.runner_params["godocker_project"])
            project = str(self.runner_params["godocker_project"])
            dt = datetime.now()
            command = "#!/bin/bash\n"+"cd "+job_wrapper.working_directory+"\n"+job_wrapper.runner_command_line
            log.debug("\n Command: ")
            log.debug(command)
            job = {
        'user' : {
            #'id' : user_infos['id'],
            #'uid' : user_infos['uid'],
            #'gid' : user_infos['gid'],
            'project' : project
        },
        'date': time.mktime(dt.timetuple()),
        'meta': {
            'name': name,
            'description': description,
            'tags': tags_tab
        },
        'requirements': {
            'cpu': int(docker_cpu), #cpu,
            'ram': int(docker_ram), #ram,
            'array': { 'values': array},
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
            'root': False #root
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
            log.debug("JOB TEMPLATE: ")
            log.debug(job)
            log.debug("END OF JOB TEMPLATE \n")
            log.debug("\n JOB POST TASK TO BE EXECUTED \n")
            result = self.auth.http_post_request(
                "/api/1.0/task", json.dumps(job),
                {'Authorization':'Bearer '+self.auth.token, 'Content-type': 'application/json', 'Accept':'application/json'}
            )
            #self.get_structure(result)
            log.debug(result.text)
            log.debug("Response from godocker: "+ str(result.json()['msg']) + " ID: " + str(result.json()['id']))
            log.debug("END OF JOB POST TASK\n")
            return str(result.json()['id'])

    def get_task(self,job_id):
        #Get job details
        job = False
        t = {"server":self.auth.server,"noCert":self.auth.noCert,"token":self.auth.token,"login":self.auth.login,"apikey":self.auth.apikey}
        log.debug(t)
        if self.auth.token:
            result = self.auth.http_get_request("/api/1.0/task/"+str(job_id),{'Authorization':'Bearer '+self.auth.token})
            job = result.json()
        return job

    def task_suspend(self,job_id):
        #Suspend actively running job
        job = False
        if self.auth.token:
            result = self.auth.http_get_request("/api/1.0/task/"+str(job_id)+"/suspend",{'Authorization':'Bearer '+self.auth.token})
            job = result.json()
        return job

    def get_task_status(self,job_id):
        #Get job status
        job = False
        t = {"server":self.auth.server,"noCert":self.auth.noCert,"token":self.auth.token,"login":self.auth.login,"apikey":self.auth.apikey}
        log.debug(t)
        if self.auth.token:
            log.debug("Authentication in process!!!")
            result = self.auth.http_get_request("/api/1.0/task/"+str(job_id)+"/status",{'Authorization':'Bearer '+self.auth.token})
            job = result.json()
        t = {"server":self.auth.server,"noCert":self.auth.noCert,"token":self.auth.token,"login":self.auth.login,"apikey":self.auth.apikey}
        log.debug(t)
        return job

    def delete_task(self,job_id):
        #Delete a job 
        job = False
        t ={"server":self.auth.server,"noCert":self.auth.noCert,"token":self.auth.token,"login":self.auth.login,"apikey":self.auth.apikey}
        log.debug(t)
        if self.auth.token:
            result = self.auth.http_delete_request("/api/1.0/task/"+str(job_id),{'Authorization':'Bearer '+self.auth.token})
            job = result.json()
        return job

    def get_structure(self,obj):
        log.debug("\n STRUCTURE \n")
        memb = inspect.getmembers(obj)
        for i in memb:
            log.debug(i)
        log.debug("\n END OF STRUCTURE \n")
        return


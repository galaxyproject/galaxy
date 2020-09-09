# Uploading a file to Galaxy

## What happens when you upload a file to Galaxy?

When you upload a file to Galaxy, a worker thread creates a job and enqueues it to do the upload. The following call graph documents what the worker thread actually does to create and enqueue the file upload job. All the files are in ./galaxy/lib. An irods object store is used in this instnce of Galaxy.

* In galaxy/web/framework/middleware/batch.py -> BatchMiddleware.__call__() -> self.application()
  * In galaxy/web/framework/middleware/request_id.py -> RequestIDMiddleware.__call__() -> self.app()
    * In galaxy/web/framework/middleware/xforwardedhost.py -> XForwardedHostMiddleware.__call__() -> self.app()
      * In galaxy/web/framework/middleware/translogger.py -> TransLogger.__call__() -> self.application()
        * In galaxy/web/framework/middleware/error.py -> ErrorMiddleware.__call__() ->  self.application()
          * In galaxy/web/framework/middleware/base.py -> WebApplication.__call__() -> handle_request() -> method()
            * In galaxy/web/framework/middleware/decorators.py -> expose_api() -> func()
              * In galaxy/webapps/galaxy/api/tools.py -> ToolsController.create() -> self._create() -> tool.handle_input()
                * In galaxy/tools/__init__.py -> handle_input() -> execute_job()
                  * In galaxy/tools/execute.py -> execute() -> execute_single_job() -> tool.handle_single_execution()
                    * In galaxy/tools/__init__.py -> handle_single_execution() -> self.execute() -> self.tool_action_execute()  
              * In galaxy/webapps/galaxy/api/tools.py -> ToolsController.create() -> self._create(), HistoryDatasetAssociation's to_dict() is called for each output dataset
                * to_dict() calls HistoryDatasetAssociations's get_size()
                  * get_size indirectly calls DataSet's _calculate_size()  
                    * _calculate_size() calls ObjectStore's size()
                      * size() indirectly calls irod's _size()
                        * _size() calls _construct_path() in irods
                        * _size() calls _in_cache() in irods
                        * _size() calls _get_cache_path() in irods
                        * _size() calls _exists() in irods
                        * _size() calls _get_size_in_irods() 

In order to avoid excessive indentation, self.tool_action_execute() call graph is documented separately.  

* In galaxy/tools/actions/upload.py -> BaseUploadToolAction.execute()  
  * upload_common.persist_uploads() -- Persist files to upload
  * self._setup_job()
    * upload_common.get_uploaded_datasets()
      * In upload_common.py -> new_upload()
        * __new_history_upload()
          * Create HistoryDatasetAssociation
    * upload_common.create_paramfile() -- dumps it into a tmp file
    * self._create_job() -> upload_common.create_job() -- create Job object, set various fields, enqueue the job (write it to job table in DB)
      * In galaxy/tools/actions/upload_common.py -> create_job()
        * trans.app.model.job()
          * session_id
          * user_id
          * library_folder_id
          * tool_id
          * tool_version
          * job_state
        * trans.sa_session.add(job) -- adds Job object to SqlAlchemy session to be flushed next (persisted to job table in DB) 
        * job.add_parameter() -- include the dumped param file above
        * job.add_output_dataset()
        * trans.sa_session.add(output_object) -- object_output is HistoryDatasetAssociation object
        * trans.sa_session.add(job)
        * trans.app.job_manager.enqueue(job, tool) -- Queue the job for execution  
          * tool.get_configured_job_handler()
          * Create queue call back partial function
          * Create message call back partial function
          * self.app.job_config.assign_handler(job, queue_callback, message_callback)

JobHandlerQueue's __monitor() continually iterates the waiting jobs, checking if each is ready to run, and dispatching it if so. 

* __monitor() -> __monitor_step() --> __handle_waiting_job()
  * If job is ready, call pop on JobWrapper (pass in job ID), then call put() on DefaultJobDispatcher (pass in what was popped)
    * In DefaultJobDispatcher's put(), get the job runner's name, and call put() on that job runner
      * In job runner's put(), call enqueue() on Job Wrapper (adds a job to the queue, indicates the job is ready to run)
        * In enqueue(): 
          * Create a galaxy.model.Job instance                        
          * Call _set_object_store_id()
            * For each job output dataset, set object store id via ObjectStorePopulator
              * This calls irods _create()
                * Calls irods _exists()
                  * Calls irods_construct_path()
                  * Calls irods _in_cache() 
                    * Calls _get_cache_path()
                  * Calls irods _data_object_exists()
                * Calls _push_to_irods()
            * JobWrapper calls _set_working_directory()
              * Calls _create_working_directory()
                * Calls object_store_get_filename()
                  * Calls irods _get_file_name()
                    * Calls irods _get_cache_path()
                    * Calls irods _in_cache()
                    * Calls irods _exists()
                    * Calls irods _puul_into_cache()
                        
In BaseJobRunner's run_next()

* Call get() on queue.Queue to get method (of type localJobRunner.queue_job) and arg (of type galaxy.job.JobWrapper)
  * Calls method on arg
    * Calls LocalJobRunner's _prepare_job_local()
      * Calls BaseJobRunner's prepare_job()
        * Calls LocalJobRunner's build_command_line()
          * Calls command_factory.py's build_command()
            * Calls __handle_metadata()
              * Calls JobWrapper's setup_external_metadata()
                * Calls object_store.to_dict()
                  * Calls irods to_dict()
                    * Calls CloudConfigMixin's _config_to_dict() 
              * Calls JobWrapper's PortableDirectoryMetadataGenerator's setup_external_metadata()
                * Calls Model's get_file_name()
                  * Calls dataset's get_file_name()
                    * Calls object_store's exists()
                      * Indirectly calls irod's _exists()
                    * Calls object_store's get_filename()   
                      * Indirectly calls irod's _get_filename() 
    * Call __command_line() to get the full path to 'galaxy_<JobID>.sh', then run the script
    * Get the job, change state to 'Running'.
    * Call LocalJobRunner's _finish_or_resubmit_job()
    * Calls JobWrapper's finish()
      * Calls JobWrapper's _finish_dataset()
        * Calls dataset.set_size()
          * Indirectly calls model's _clculate_size()
            * Calls object store's size()
              * Indirectly calls irod's _size()      
        * Calls JobWrapper's __update_output()
          * Calls object_store.update_from_file()
            * Indirectly clls irod's _update_from_file()
              * Calls irod's _create()
              * Calls irod's _exists()
              * Calls irod's _construct_path()
              * Calls irod's _get_cache_path()
              * Calls irod's _push_to_irods()

# Uploading file to Galaxy

## What happens when you upload a file to Galaxy?

When you upload a file to Galaxy, a worker thread creates a job and enqueues it to do the upload. The following call graph documents what the worker thread actually does to create and enqueue the file upload job. All the files are in ./galaxy/lib.

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
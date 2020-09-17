# Starting Galaxy

## What happens when you start Galaxy?

Galaxy is started by running ./run.sh script. The following call graph documents what happens during Galaxy startup process.  Please note, Galaxy is a WSGI app, so in principle all Python WSGI servers can run the Galaxy app (Paste, Gunicorn and uWSGI are known to work and have some level of support). This document separates web server specific section (e.g. Paste) from Galaxy specific section (FYI, Galaxy uses uWSGI by default).

## Paste

* ./galaxy/scripts/paster.py
  * Add ./galaxy/lib to system path
  * Check Python version
    * version >= 3.5 -> OK
    * version = 2.7 -> Deprecated
    * No other version is supported
  * serve.run()

* ./galaxy/lib/galaxy/util/pastescript/serve.py (The Python Paste package contains Python modules that help in implementing WSGI middleware)
  * serve.run()
    * Parse Python command line arguments
    * Extract the command name from command line arguments (e.g., 'serve')
    * Get the Command object for command name, then invoke it (call Command's run() method)
  * Command.run()
    * Setup default options, validate command line arguments, then call ServeCommand's command() method
  * ServeCommand.command()
    * Conditionally, stop the daemon
    * If a config file is required, make sure a config file is provided on the command line arguments.
    * Possible subcommands: start, stop, restart, status (or None)
    * Call loadserver() method in ./galaxy/lib/galaxy/util/pastescript/loadwsgi.py
      * Calls loadobj()  -> calls LoaderContext's create() -> calls _Server's invoke()
    * Call loadapp() method in ./galaxy/lib/galaxy/util/pastescript/loadwsgi.py
      * Calls loadobj()  -> calls LoaderContext's create() -> calls _App's invoke() -> calls fix_call() on app_factory (in ./galaxy/lib/galaxy/webapps/galaxy/buildapp.py)

## Galaxy

* app_factory:
  * Create UniverseApplication  (in ./galaxy/lib/galaxy/webapps/galaxy/buildapp.py)
    * Create GalaxyAppConfiguration instance from config file specified on the command line, then check for errors
    * Configure logging (in ./galaxy/lib/galaxy/config/__init__.py)
    * Create ExecutionTimerFactory
      * Which has a GalaxyStatsdClient field
    * Configure FluentTraceLogger
    * Create the application stack (uWSGi, Paste, or Webless)
      * App registers post fork functions to start application stack threads
    * Create GalaxyQueueWorker instance (a worker for Galaxy's queues, used for dispatching control tasks. Sqlite instance)
    * Configure tool shed registry
    * Configure object store. build_object_store_from_config() (in ./galaxy/lib/galaxy/objectstore/__init__.py) calls objectstore_class.from_xml(), calls clazz.parse_xml()
    * Configure models in _configure_models()
      * Calls create_or_verify_database() in ./galaxy/libl/galaxy/model/migrate/check.py
        * If a new database, calls migrate_from_scratch() in  ./galaxy/libl/galaxy/model/migrate/check.py
          * Calls mapping.init() in ./galaxy/libl/galaxy/model/mapping.py (Details of how data objects are mapped to relational DB tables).
      * Calls init_models_from_config in  in ./galaxy/libl/galaxy/model/mapping.py
    * Configure security
    * Set GalaxyTagHandler (in ./galaxy/lib/galaxy/model/tags.py)
      * Handles CRUD operations for tagging datasets, workflows, visualizations, etc
    * Set DatasetCollectionManager (in ./galaxy/lib/galaxy/managers/collections.py)
    * Configure HistoryManager
    * Configure HistoryDatasetAssociation (HDA) Manager
    * Create WorkflowsManager
      * Handles CRUD operations related to workflows
    * Configure DependencyResolverView (a RESTful interface to galaxy.tool_util.deps.DependencyResolver)
    * Configure TestDataResolver
    * Configure LibraryManager (Data libraries under Shared Data)
    * Configure FolderManager (Folders are folders in a data library)
    * Configure DynamicToolManager (Tools that are loaded from DB instead of disk files)
    * Configure DataProviderRegistry
    * Configure JobMetrics manager
    * Configure ErrorReport plugins
    * Configure job management configuration
    * Setup a tool cache
    * Watch various config files for immediate reload
    * Configure Data Manager
    * Configure UpdateRespositoyManager
    * Load proprietary datatype convertors and display applications
    * Configure VisualizationRegistry, ToursRegistry, and WebHookRegistry
    * Load security policy and quota management
    * Configure heartbeat for thread profiling
    * If configured, create Sentry client
      * App registers post fork functions to start Sentry client thread
    * Create JobManager
      * App registers post fork functions to start application job manager thread
        * Job manager thread starts monitor threads for JobHandlerQueue and JobHandlerStopQueue (2 threads)
      * JobManager has a JobHandler field, which manages the preparation, running, tracking, and finishing of jobs
        * JobHandler has a job dispatcher, which launches underlying job runners
          * DefaultJobDispatcher calls app's JobConfiguration's get_job_runner_plugins() to create LocalJobRunner instances
            * The default number of LocalJobRuner instances is 4 (4 threads)
        * JobHandler also has queues for starting and stopping jobs (unless track_jobs_in_database is True)
    * Create WorkflowSchedulingManager
      * Starts workflow request monitor thread in __start_request_monitor() method (1 thread)
    * Configure InteractiveToolManager
    * Create database heartbeat instance
      * App registers post fork functions to start application DB heartbeat thread (1 thread)
  * Create CommunityWebApplication (in ./galaxy/lib/galaxy/webapps/galaxy/buildapp.py)
    * CommunityWebApplication: A WSGI application that maps requests to objects using routes and to methods on those objects
    * Map all requests to controllers/actions
    * Wrap web app in some middleware and return webapp

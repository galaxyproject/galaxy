~~~~~~~~~~~~~~
``config_dir``
~~~~~~~~~~~~~~

:Description:
    The directory that will be prepended to relative paths in options
    specifying other Galaxy config files (e.g. datatypes_config_file).
    Defaults to the directory in which galaxy.yml is located.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``managed_config_dir``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The directory that will be prepended to relative paths in options
    specifying config files controlled by Galaxy (such as
    shed_tool_config_file, etc.). Must be writable by the user running
    Galaxy.  Defaults to `<config_dir>/` if running Galaxy from source
    or `<data_dir>/config` otherwise.
:Default: ``None``
:Type: str


~~~~~~~~~~~~
``data_dir``
~~~~~~~~~~~~

:Description:
    The directory that will be prepended to relative paths in options
    specifying Galaxy data/cache directories and files (such as the
    default SQLite database, file_path, etc.). Defaults to `database/`
    if running Galaxy from source or `<config_dir>/data` otherwise.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~
``templates_dir``
~~~~~~~~~~~~~~~~~

:Description:
    The directory containing custom templates for Galaxy, such as
    HTML/text email templates. Defaults to 'templates'. Default
    templates can be found in the Galaxy root under config/templates.
    These can be copied to <templates_dir> if you wish to customize
    them.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``templates``
:Type: str


~~~~~~~~~~~~~
``cache_dir``
~~~~~~~~~~~~~

:Description:
    Top level cache directory. Any other cache directories
    (template_cache_path, etc.) should be subdirectories.
    The value of this option will be resolved with respect to
    <data_dir>.
:Default: ``cache``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``database_connection``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    By default, Galaxy uses a SQLite database at
    '<data_dir>/universe.sqlite'. You may use a SQLAlchemy connection
    string to specify an external database instead.
    Sample default
    'sqlite:///<data_dir>/universe.sqlite?isolation_level=IMMEDIATE'
    You may specify additional options that will be passed to the
    SQLAlchemy database engine by using the prefix
    "database_engine_option_". For some of these options, default
    values are provided (e.g. see database_engine_option_pool_size,
    etc.).
    The same applies to `install_database_connection`, for which you
    should use the "install_database_engine_option_" prefix.
    For more options, please check SQLAlchemy's documentation at
    https://docs.sqlalchemy.org/en/14/core/engines.html?highlight=create_engine#sqlalchemy.create_engine
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``database_engine_option_pool_size``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If the server logs errors about not having enough database pool
    connections, you will want to increase these values, or consider
    running more Galaxy processes.
:Default: ``5``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``database_engine_option_max_overflow``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If the server logs errors about not having enough database pool
    connections, you will want to increase these values, or consider
    running more Galaxy processes.
:Default: ``10``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``database_engine_option_pool_recycle``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If using MySQL and the server logs the error "MySQL server has
    gone away", you will want to set this to some positive value (7200
    should work).
:Default: ``-1``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``database_engine_option_server_side_cursors``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If large database query results are causing memory or response
    time issues in the Galaxy process, leave the result on the server
    instead.  This option is only available for PostgreSQL and is
    highly recommended.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``database_query_profiling_proxy``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Log all database transactions, can be useful for debugging and
    performance profiling.  Logging is done via Python's 'logging'
    module under the qualname
    'galaxy.model.orm.logging_connection_proxy'
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~
``database_template``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    If auto-creating a postgres database on startup - it can be based
    on an existing template database. This will set that. This is
    probably only useful for testing but documentation is included
    here for completeness.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``database_log_query_counts``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Log number of SQL queries executed and total time spent
    dispatching SQL statements for each web request. If statsd is also
    enabled this information will be logged there as well. This should
    be considered somewhat experimental, we are unsure of the
    performance costs of running this in production. This is useful
    information for optimizing database interaction performance.
    Similar information can be obtained on a per-request basis by
    enabling the sql_debug middleware and adding sql_debug=1 to a
    request string.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``slow_query_log_threshold``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Slow query logging.  Queries slower than the threshold indicated
    below will be logged to debug.  A value of '0' is disabled.  For
    example, you would set this to .005 to log all queries taking
    longer than 5 milliseconds.
:Default: ``0.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_per_request_sql_debugging``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enables a per request sql debugging option. If this is set to
    true, append ?sql_debug=1 to web request URLs to enable detailed
    logging on the backend of SQL queries generated during that
    request. This is useful for debugging slow endpoints during
    development.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``install_database_connection``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    By default, Galaxy will use the same database to track user data
    and tool shed install data.  There are many situations in which it
    is valuable to separate these - for instance bootstrapping fresh
    Galaxy instances with pretested installs.  The following option
    can be used to separate the tool shed install database (all other
    options listed above but prefixed with ``install_`` are also
    available).
    Defaults to the value of the 'database_connection' option.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``database_auto_migrate``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Setting the following option to true will cause Galaxy to
    automatically migrate the database forward after updates. This is
    not recommended for production use.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~
``database_wait``
~~~~~~~~~~~~~~~~~

:Description:
    Wait for database to become available instead of failing
    immediately.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~
``database_wait_attempts``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Number of attempts before failing if database_wait is enabled.
:Default: ``60``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~
``database_wait_sleep``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Time to sleep between attempts if database_wait is enabled (in
    seconds).
:Default: ``1.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``history_audit_table_prune_interval``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Time (in seconds) between attempts to remove old rows from the
    history_audit database table. Set to 0 to disable pruning.
:Default: ``3600``
:Type: int


~~~~~~~~~~~~~
``file_path``
~~~~~~~~~~~~~

:Description:
    Where dataset files are stored. It must be accessible at the same
    path on any cluster nodes that will run Galaxy jobs, unless using
    Pulsar. The default value has been changed from 'files' to
    'objects' as of 20.05; however, Galaxy will first check if the
    'files' directory exists before using 'objects' as the default.
    The value of this option will be resolved with respect to
    <data_dir>.
:Default: ``objects``
:Type: str


~~~~~~~~~~~~~~~~~
``new_file_path``
~~~~~~~~~~~~~~~~~

:Description:
    Where temporary files are stored. It must be accessible at the
    same path on any cluster nodes that will run Galaxy jobs, unless
    using Pulsar.
    The value of this option will be resolved with respect to
    <data_dir>.
:Default: ``tmp``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``maximum_upload_file_size``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Maximum size of uploadable files, specified in bytes (default:
    100GB). This value is ignored if an external upload server is
    configured.
:Default: ``107374182400``
:Type: int


~~~~~~~~~~~~~~~~~~~~
``tool_config_file``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Tool config files, defines what tools are available in Galaxy.
    Tools can be locally developed or installed from Galaxy tool
    sheds. (config/tool_conf.xml.sample will be used if left unset and
    config/tool_conf.xml does not exist). Can be a single file, a list
    of files, or (for backwards compatibility) a comma-separated list
    of files.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``tool_conf.xml``
:Type: any


~~~~~~~~~~~~~~~~~~~~~~~~~
``shed_tool_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Tool config file for tools installed from the Galaxy Tool Shed.
    Must be writable by Galaxy and generally should not be edited by
    hand. In older Galaxy releases, this file was part of the
    tool_config_file option. It is still possible to specify this file
    (and other shed-enabled tool config files) in tool_config_file,
    but in the standard case of a single shed-enabled tool config,
    this option is preferable. This file will be created automatically
    upon tool installation, whereas Galaxy will fail to start if any
    files in tool_config_file cannot be read.
    The value of this option will be resolved with respect to
    <managed_config_dir>.
:Default: ``shed_tool_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``migrated_tools_config``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This option is deprecated. In previous releases this file was
    maintained by tool migration scripts that are no longer part of
    the code base. The option remains as a placeholder for deployments
    where these scripts were previously run and such a file exists.
    The value of this option will be resolved with respect to
    <managed_config_dir>.
:Default: ``migrated_tools_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``integrated_tool_panel_config``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    File that contains the XML section and tool tags from all tool
    panel config files integrated into a single file that defines the
    tool panel layout.  This file can be changed by the Galaxy
    administrator to alter the layout of the tool panel.  If not
    present, Galaxy will create it.
    The value of this option will be resolved with respect to
    <managed_config_dir>.
:Default: ``integrated_tool_panel.xml``
:Type: str


~~~~~~~~~~~~~
``tool_path``
~~~~~~~~~~~~~

:Description:
    Default path to the directory containing the tools defined in
    tool_conf.xml. Other tool config files must include the tool_path
    as an attribute in the <toolbox> tag.
:Default: ``tools``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``tool_dependency_dir``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Various dependency resolver configuration parameters will have
    defaults set relative to this path, such as the default conda
    prefix, default Galaxy packages path, legacy tool shed
    dependencies path, and the dependency cache directory.
    Set the string to null to explicitly disable tool dependency
    handling. If this option is set to none or an invalid path,
    installing tools with dependencies from the Tool Shed or in Conda
    will fail.
    The value of this option will be resolved with respect to
    <data_dir>.
:Default: ``dependencies``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dependency_resolvers_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Specifies the path to the standalone dependency resolvers
    configuration file. This configuration can now be specified
    directly in the Galaxy configuration, see the description of the
    'dependency_resolvers' option for details.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``dependency_resolvers_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~
``conda_prefix``
~~~~~~~~~~~~~~~~

:Description:
    conda_prefix is the location on the filesystem where Conda
    packages and environments are installed.
    Sample default '<tool_dependency_dir>/_conda'
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~
``conda_exec``
~~~~~~~~~~~~~~

:Description:
    Override the Conda executable to use, it will default to the one
    on the PATH (if available) and then to <conda_prefix>/bin/conda
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~
``conda_debug``
~~~~~~~~~~~~~~~

:Description:
    Pass debug flag to conda commands.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~
``conda_ensure_channels``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    conda channels to enable by default
    (https://conda.io/docs/user-guide/tasks/manage-channels.html)
:Default: ``conda-forge,bioconda``
:Type: str


~~~~~~~~~~~~~~~~~~~
``conda_use_local``
~~~~~~~~~~~~~~~~~~~

:Description:
    Use locally-built conda packages.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~
``conda_auto_install``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set to true to instruct Galaxy to look for and install missing
    tool dependencies before each job runs.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~
``conda_auto_init``
~~~~~~~~~~~~~~~~~~~

:Description:
    Set to true to instruct Galaxy to install Conda from the web
    automatically if it cannot find a local copy and conda_exec is not
    configured. The default is true if running Galaxy from source, and
    false if running from installed packages.
:Default: ``None``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``conda_copy_dependencies``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    You must set this to true if conda_prefix and
    job_working_directory are not on the same volume, or some conda
    dependencies will fail to execute at job runtime. Conda will copy
    packages content instead of creating hardlinks or symlinks. This
    will prevent problems with some specific packages (perl, R), at
    the cost of extra disk space usage and extra time spent copying
    packages.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``local_conda_mapping_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Path to a file that provides a mapping from abstract packages to
    concrete conda packages. See
    `config/local_conda_mapping.yml.sample` for examples.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``local_conda_mapping.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``modules_mapping_files``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Path to a file that provides a mapping from abstract packages to
    locally installed modules. See
    `config/environment_modules_mapping.yml.sample` for examples.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``environment_modules_mapping.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``use_cached_dependency_manager``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Certain dependency resolvers (namely Conda) take a considerable
    amount of time to build an isolated job environment in the
    job_working_directory if the job working directory is on a network
    share.  Set this option to true to cache the dependencies in a
    folder. This option is beta and should only be used if you
    experience long waiting times before a job is actually submitted
    to your cluster.
    This only affects tools where some requirements can be resolved
    but not others, most modern best practice tools can use prebuilt
    environments in the Conda directory.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_dependency_cache_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    By default the tool_dependency_cache_dir is the _cache directory
    of the tool dependency directory.
    Sample default '<tool_dependency_dir>/_cache'
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``precache_dependencies``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    By default, when using a cached dependency manager, the
    dependencies are cached when installing new tools and when using
    tools for the first time. Set this to false if you prefer
    dependencies to be cached only when installing new tools.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_sheds_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    File containing the Galaxy Tool Sheds that should be made
    available to install from in the admin interface (.sample used if
    default does not exist).
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``tool_sheds_conf.xml``
:Type: str


~~~~~~~~~~~~~~~
``watch_tools``
~~~~~~~~~~~~~~~

:Description:
    Monitor the tools and tool directories listed in any tool config
    file specified in tool_config_file option.  If changes are found,
    tools are automatically reloaded. Watchdog (
    https://pypi.org/project/watchdog/ ) must be installed and
    available to Galaxy to use this option. Other options include
    'auto' which will attempt to watch tools if the watchdog library
    is available but won't fail to load Galaxy if it is not and
    'polling' which will use a less efficient monitoring scheme that
    may work in wider range of scenarios than the watchdog default.
:Default: ``false``
:Type: str


~~~~~~~~~~~~~~~~~~~
``watch_job_rules``
~~~~~~~~~~~~~~~~~~~

:Description:
    Monitor dynamic job rules. If changes are found, rules are
    automatically reloaded. Takes the same values as the 'watch_tools'
    option.
:Default: ``false``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``watch_core_config``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Monitor a subset of options in the core configuration file (See
    RELOADABLE_CONFIG_OPTIONS in lib/galaxy/config/__init__.py).  If
    changes are found, modified options are automatically reloaded.
    Takes the same values as the 'watch_tools' option.
:Default: ``false``
:Type: str


~~~~~~~~~~~~~~~
``watch_tours``
~~~~~~~~~~~~~~~

:Description:
    Monitor the interactive tours directory specified in the
    'tour_config_dir' option. If changes are found, modified tours are
    automatically reloaded. Takes the same values as the 'watch_tools'
    option.
:Default: ``false``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~
``short_term_storage_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Location of files available for a short time as downloads (short
    term storage). This directory is exclusively used for serving
    dynamically generated downloadable content. Galaxy may uses the
    new_file_path parameter as a general temporary directory and that
    directory should be monitored by a tool such as tmpwatch in
    production environments. short_term_storage_dir on the other hand
    is monitored by Galaxy's task framework and should not require
    such external tooling.
    The value of this option will be resolved with respect to
    <cache_dir>.
:Default: ``short_term_web_storage``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``short_term_storage_default_duration``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Default duration before short term web storage files will be
    cleaned up by Galaxy tasks (in seconds). The default duration is 1
    day.
:Default: ``86400``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``short_term_storage_maximum_duration``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The maximum duration short term storage files can hosted before
    they will be marked for clean up.  The default setting of 0
    indicates no limit here.
:Default: ``0``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``short_term_storage_cleanup_interval``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    How many seconds between instances of short term storage being
    cleaned up in default Celery task configuration.
:Default: ``3600``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``file_sources_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Configured FileSource plugins.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``file_sources_conf.yml``
:Type: str


~~~~~~~~~~~~~~~~
``file_sources``
~~~~~~~~~~~~~~~~

:Description:
    FileSource plugins described embedded into Galaxy's config.
:Default: ``None``
:Type: seq


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_templates_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Configured Object Store templates configuration file.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``object_store_templates.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_templates``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Configured Object Store templates embedded into Galaxy's config.
:Default: ``None``
:Type: seq


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``file_source_templates_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Configured user file source templates configuration file.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``file_source_templates.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``file_source_templates``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Configured user file source templates embedded into Galaxy's
    config.
:Default: ``None``
:Type: seq


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_config_templates_use_saved_configuration``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    User defined object stores and file sources are saved in the
    database with their last valid configuration. It may be the case
    that the admin changes file source and object store templates over
    time such that the variables and secrets an instance is saved with
    no longer match the configuration's expected values. For this
    reason, admins should always add new versions of templates instead
    of just changing them - however people take shortcuts and
    divergences might happen. If a template is changed in such a way
    it breaks or if a template disappears from the library of
    templates this parameter controls how and if the database version
    will be used.
    By default, it will simply be used as a 'fallback' if a
    configuration cannot be resolved against the template version in
    the configuration file. Using 'preferred' instead will mean the
    stored database version is always used. This ensures a greater
    degree of reproducibility without effort on the part of the admin
    but also means that small issues are not easy to fix. Using
    'never' instead will ensure the config templates are always only
    loaded from the template library files - this might make sense for
    admins who want to disable templates without worrying about the
    contents of the database.
:Default: ``fallback``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_mulled_containers``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable Galaxy to fetch containers registered with quay.io
    generated from tool requirements resolved through Conda. These
    containers (when available) have been generated using mulled -
    https://github.com/mulled. Container availability will vary by
    tool, this option will only be used for job destinations with
    Docker or Singularity enabled.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``container_resolvers_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Container resolvers configuration. Set up a file describing
    container resolvers to use when discovering containers for Galaxy.
    If this is set to None, the default container resolvers loaded is
    determined by enable_mulled_containers. For available options see
    https://docs.galaxyproject.org/en/master/admin/container_resolvers.html
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``container_resolvers``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Rather than specifying a container_resolvers_config_file, the
    definition of the resolvers to enable can be embedded into
    Galaxy's config with this option. This has no effect if a
    container_resolvers_config_file is used. Takes the same options
    that can be set in container_resolvers_config_file.
:Default: ``None``
:Type: seq


~~~~~~~~~~~~~~~~~~
``involucro_path``
~~~~~~~~~~~~~~~~~~

:Description:
    involucro is a tool used to build Docker or Singularity containers
    for tools from Conda dependencies referenced in tools as
    `requirement` s. The following path is the location of involucro
    on the Galaxy host. This is ignored if the relevant container
    resolver isn't enabled, and will install on demand unless
    involucro_auto_init is set to false.
    The value of this option will be resolved with respect to
    <tool_dependency_dir>.
:Default: ``involucro``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``involucro_auto_init``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Install involucro as needed to build Docker or Singularity
    containers for tools. Ignored if relevant container resolver is
    not used.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~
``mulled_channels``
~~~~~~~~~~~~~~~~~~~

:Description:
    Conda channels to use when building Docker or Singularity
    containers using involucro.
:Default: ``conda-forge,bioconda``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_tool_shed_check``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable automatic polling of relative tool sheds to see if any
    updates are available for installed repositories.  Ideally only
    one Galaxy server process should be able to check for repository
    updates.  The setting for hours_between_check should be an integer
    between 1 and 24.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~
``hours_between_check``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable automatic polling of relative tool sheds to see if any
    updates are available for installed repositories.  Ideally only
    one Galaxy server process should be able to check for repository
    updates.  The setting for hours_between_check should be an integer
    between 1 and 24.
:Default: ``12``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_data_table_config_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    XML config file that contains data table entries for the
    ToolDataTableManager.  This file is manually # maintained by the
    Galaxy administrator (.sample used if default does not exist).
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``tool_data_table_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``shed_tool_data_table_config``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    XML config file that contains additional data table entries for
    the ToolDataTableManager.  This file is automatically generated
    based on the current installed tool shed repositories that contain
    valid tool_data_table_conf.xml.sample files.  At the time of
    installation, these entries are automatically added to the
    following file, which is parsed and applied to the
    ToolDataTableManager at server start up.
    The value of this option will be resolved with respect to
    <managed_config_dir>.
:Default: ``shed_tool_data_table_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~
``tool_data_path``
~~~~~~~~~~~~~~~~~~

:Description:
    Directory where data used by tools is located.  See the samples in
    that directory and the Galaxy Community Hub for help:
    https://galaxyproject.org/admin/data-integration
:Default: ``tool-data``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``shed_tool_data_path``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Directory where Tool Data Table related files will be placed when
    installed from a ToolShed. Defaults to the value of the
    'tool_data_path' option.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``watch_tool_data_dir``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Monitor the tool_data and shed_tool_data_path directories. If
    changes in tool data table files are found, the tool data tables
    for that data manager are automatically reloaded. Watchdog (
    https://pypi.org/project/watchdog/ ) must be installed and
    available to Galaxy to use this option. Other options include
    'auto' which will attempt to use the watchdog library if it is
    available but won't fail to load Galaxy if it is not and 'polling'
    which will use a less efficient monitoring scheme that may work in
    wider range of scenarios than the watchdog default.
:Default: ``false``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``refgenie_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    File containing refgenie configuration, e.g.
    /path/to/genome_config.yaml. Can be used by refgenie backed tool
    data tables.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``build_sites_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    File that defines the builds (dbkeys) available at sites used by
    display applications and the URL to those sites.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``build_sites.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``builds_file_path``
~~~~~~~~~~~~~~~~~~~~

:Description:
    File containing old-style genome builds.
    The value of this option will be resolved with respect to
    <tool_data_path>.
:Default: ``shared/ucsc/builds.txt``
:Type: str


~~~~~~~~~~~~~~~~~
``len_file_path``
~~~~~~~~~~~~~~~~~

:Description:
    Directory where chrom len files are kept, currently mainly used by
    trackster.
    The value of this option will be resolved with respect to
    <tool_data_path>.
:Default: ``shared/ucsc/chrom``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``datatypes_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Datatypes config file(s), defines what data (file) types are
    available in Galaxy (.sample is used if default does not exist).
    If a datatype appears in multiple files, the last definition is
    used (though the first sniffer is used so limit sniffer
    definitions to one file).
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``datatypes_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``sniff_compressed_dynamic_datatypes_default``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable sniffing of compressed datatypes. This can be
    configured/overridden on a per-datatype basis in the
    datatypes_conf.xml file. With this option set to false the
    compressed datatypes will be unpacked before sniffing.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~
``datatypes_disable_auto``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Disable the 'Auto-detect' option for file uploads
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``visualization_plugins_directory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Visualizations config directory: where to look for individual
    visualization plugins.  The path is relative to the Galaxy root
    dir.  To use an absolute path begin the path with '/'.  This is a
    comma-separated list.
:Default: ``config/plugins/visualizations``
:Type: str


~~~~~~~~~~~~~~~~~~~
``tour_config_dir``
~~~~~~~~~~~~~~~~~~~

:Description:
    Interactive tour directory: where to store interactive tour
    definition files. Galaxy ships with several basic interface tours
    enabled, though a different directory with custom tours can be
    specified here. The path is relative to the Galaxy root dir.  To
    use an absolute path begin the path with '/'.  This is a
    comma-separated list.
:Default: ``config/plugins/tours``
:Type: str


~~~~~~~~~~~~~~~~
``webhooks_dir``
~~~~~~~~~~~~~~~~

:Description:
    Webhooks directory: where to store webhooks - plugins to extend
    the Galaxy UI. By default none will be loaded.  Set to
    config/plugins/webhooks/demo to load Galaxy's demo webhooks.  To
    use an absolute path begin the path with '/'.  This is a
    comma-separated list. Add test/functional/webhooks to this list to
    include the demo webhooks used to test the webhook framework.
:Default: ``config/plugins/webhooks``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``job_working_directory``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Each job is given a unique empty directory as its current working
    directory. This option defines in what parent directory those
    directories will be created.
    The value of this option will be resolved with respect to
    <data_dir>.
:Default: ``jobs_directory``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``template_cache_path``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Mako templates are compiled as needed and cached for reuse, this
    directory is used for the cache
    The value of this option will be resolved with respect to
    <cache_dir>.
:Default: ``compiled_templates``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``check_job_script_integrity``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set to false to disable various checks Galaxy will do to ensure it
    can run job scripts before attempting to execute or submit them.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``check_job_script_integrity_count``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Number of checks to execute if check_job_script_integrity is
    enabled.
:Default: ``35``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``check_job_script_integrity_sleep``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Time to sleep between checks if check_job_script_integrity is
    enabled (in seconds).
:Default: ``0.25``
:Type: float


~~~~~~~~~~~~~~~~~~~~~
``default_job_shell``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set the default shell used by non-containerized jobs Galaxy-wide.
    This defaults to bash for all jobs and can be overridden at the
    destination level for heterogeneous clusters. conda job resolution
    requires bash or zsh so if this is switched to /bin/sh for
    instance - conda resolution should be disabled. Containerized jobs
    always use /bin/sh - so more maximum portability tool authors
    should assume generated commands run in sh.
:Default: ``/bin/bash``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_tool_document_cache``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Whether to enable the tool document cache. This cache stores
    expanded XML strings. Enabling the tool cache results in slightly
    faster startup times. The tool cache is backed by a SQLite
    database, which cannot be stored on certain network disks. The
    cache location is configurable with the ``tool_cache_data_dir``
    tag in tool config files.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_search_index_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Directory in which the toolbox search index is stored. The value
    of this option will be resolved with respect to <data_dir>.
:Default: ``tool_search_index``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``biotools_content_directory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Point Galaxy at a repository consisting of a copy of the bio.tools
    database (e.g. https://github.com/bio-tools/content/) to resolve
    bio.tools data for tool metadata.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``biotools_use_api``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Set this to true to attempt to resolve bio.tools metadata for
    tools for tool not resovled via biotools_content_directory.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``biotools_service_cache_type``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    bio.tools web service request related caching. The type of beaker
    cache used.
:Default: ``file``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``biotools_service_cache_data_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    bio.tools web service request related caching. The data directory
    to point beaker cache at.
    The value of this option will be resolved with respect to
    <cache_dir>.
:Default: ``biotools/data``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``biotools_service_cache_lock_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    bio.tools web service request related caching. The lock directory
    to point beaker cache at.
    The value of this option will be resolved with respect to
    <cache_dir>.
:Default: ``biotools/locks``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``biotools_service_cache_url``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When biotools_service_cache_type = ext:database, this is the url
    of the database used by beaker for bio.tools web service request
    related caching. The application config code will set it to the
    value of database_connection if this is not set.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``biotools_service_cache_table_name``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When biotools_service_cache_type = ext:database, this is the
    database table name used by beaker for bio.tools web service
    request related caching.
:Default: ``beaker_cache``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``biotools_service_cache_schema_name``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When biotools_service_cache_type = ext:database, this is the
    database table name used by beaker for bio.tools web service
    request related caching.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``citation_cache_type``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Citation related caching.  Tool citations information maybe
    fetched from external sources such as https://doi.org/ by Galaxy -
    the following parameters can be used to control the caching used
    to store this information.
:Default: ``file``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``citation_cache_data_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Citation related caching.  Tool citations information maybe
    fetched from external sources such as https://doi.org/ by Galaxy -
    the following parameters can be used to control the caching used
    to store this information.
    The value of this option will be resolved with respect to
    <cache_dir>.
:Default: ``citations/data``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``citation_cache_lock_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Citation related caching.  Tool citations information maybe
    fetched from external sources such as https://doi.org/ by Galaxy -
    the following parameters can be used to control the caching used
    to store this information.
    The value of this option will be resolved with respect to
    <cache_dir>.
:Default: ``citations/locks``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``citation_cache_url``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When citation_cache_type = ext:database, this is the url of the
    database used by beaker for citation caching. The application
    config code will set it to the value of database_connection if
    this is not set.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``citation_cache_table_name``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When citation_cache_type = ext:database, this is the database
    table name used by beaker for citation related caching.
:Default: ``beaker_cache``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``citation_cache_schema_name``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When citation_cache_type = ext:database, this is the database
    schema name of the table used by beaker for citation related
    caching.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``mulled_resolution_cache_type``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Mulled resolution caching. Mulled resolution uses external APIs of
    quay.io, these requests are caching using this and the following
    parameters
:Default: ``file``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``mulled_resolution_cache_data_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Data directory used by beaker for caching mulled resolution
    requests.
    The value of this option will be resolved with respect to
    <cache_dir>.
:Default: ``mulled/data``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``mulled_resolution_cache_lock_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Lock directory used by beaker for caching mulled resolution
    requests.
    The value of this option will be resolved with respect to
    <cache_dir>.
:Default: ``mulled/locks``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``mulled_resolution_cache_expire``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Seconds until the beaker cache is considered old and a new value
    is created.
:Default: ``3600``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``mulled_resolution_cache_url``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When mulled_resolution_cache_type = ext:database, this is the url
    of the database used by beaker for caching mulled resolution
    requests. The application config code will set it to the value of
    database_connection if this is not set.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``mulled_resolution_cache_table_name``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When mulled_resolution_cache_type = ext:database, this is the
    database table name used by beaker for caching mulled resolution
    requests.
:Default: ``beaker_cache``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``mulled_resolution_cache_schema_name``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When mulled_resolution_cache_type = ext:database, this is the
    database schema name of the table used by beaker for caching
    mulled resolution requests.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Configuration file for the object store If this is set and exists,
    it overrides any other objectstore settings.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``object_store_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``object_store_config``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Rather than specifying an object_store_config_file, the object
    store configuration can be embedded into Galaxy's config with this
    option.
    This option has no effect if the file specified by
    object_store_config_file exists. Otherwise, if this option is set,
    it overrides any other objectstore settings.
    The syntax, available storage plugins, and documentation of their
    options is explained in detail in the object store sample
    configuration file, `object_store_conf.sample.yml`
:Default: ``None``
:Type: seq


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_cache_monitor_driver``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Specify where cache monitoring is driven for caching object stores
    such as S3, Azure, and iRODS. This option has no affect on disk
    object stores. For production instances, the cache should be
    monitored by external tools such as tmpwatch and this value should
    be set to 'external'. This will disable all cache monitoring in
    Galaxy. Alternatively, 'celery' can monitor caches using a
    periodic task or an 'inprocess' thread can be used - but this last
    option seriously limits Galaxy's ability to scale. The default of
    'auto' will use 'celery' if 'enable_celery_tasks' is set to true
    or 'inprocess' otherwise. This option serves as the default for
    all object stores and can be overridden on a per object store
    basis (but don't - just setup tmpwatch for all relevant cache
    paths).
:Default: ``auto``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_cache_monitor_interval``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    For object store cache monitoring done by Galaxy, this is the
    interval between cache checking steps. This is used by both
    inprocess cache monitors (which we recommend you do not use) and
    by the celery task if it is configured (by setting
    enable_celery_tasks to true and not setting
    object_store_cache_monitor_driver to external).
:Default: ``600``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_cache_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Default cache path for caching object stores if cache not
    configured for that object store entry.
    The value of this option will be resolved with respect to
    <cache_dir>.
:Default: ``object_store_cache``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_cache_size``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Default cache size, in GB, for caching object stores if the cache
    is not configured for that object store entry.
:Default: ``-1``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_always_respect_user_selection``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set this to true to indicate in the UI that a user's object store
    selection isn't simply a "preference" that job destinations often
    respect but in fact will always be respected. This should be set
    to true to simplify the UI as long as job destinations never
    override 'object_store_id's for a jobs.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_store_by``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    What Dataset attribute is used to reference files in an
    ObjectStore implementation, this can be 'uuid' or 'id'. The
    default will depend on how the object store is configured,
    starting with 20.05 Galaxy will try to default to 'uuid' if it can
    be sure this is a new Galaxy instance - but the default will be
    'id' in many cases. In particular, if the name of the directory
    set in <file_path> is `objects`, the default will be set to
    'uuid', otherwise it will be 'id'.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~
``smtp_server``
~~~~~~~~~~~~~~~

:Description:
    Galaxy sends mail for various things: subscribing users to the
    mailing list if they request it, password resets, reporting
    dataset errors, and sending activation emails. To do this, it
    needs to send mail through an SMTP server, which you may define
    here (host:port). Galaxy will automatically try STARTTLS but will
    continue upon failure.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~
``smtp_username``
~~~~~~~~~~~~~~~~~

:Description:
    If your SMTP server requires a username and password, you can
    provide them here (password in cleartext here, but if your server
    supports STARTTLS it will be sent over the network encrypted).
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~
``smtp_password``
~~~~~~~~~~~~~~~~~

:Description:
    If your SMTP server requires a username and password, you can
    provide them here (password in cleartext here, but if your server
    supports STARTTLS it will be sent over the network encrypted).
:Default: ``None``
:Type: str


~~~~~~~~~~~~
``smtp_ssl``
~~~~~~~~~~~~

:Description:
    If your SMTP server requires SSL from the beginning of the
    connection
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~
``mailing_join_addr``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    On the user registration form, users may choose to join a mailing
    list. This is the address used to subscribe to the list. Uncomment
    and leave empty if you want to remove this option from the user
    registration form.
    Example value 'galaxy-announce-join@lists.galaxyproject.org'
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``mailing_join_subject``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The subject of the email sent to the mailing list join address.
    See the `mailing_join_addr` option for more information.
:Default: ``Join Mailing List``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``mailing_join_body``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    The body of the email sent to the mailing list join address. See
    the `mailing_join_addr` option for more information.
:Default: ``Join Mailing List``
:Type: str


~~~~~~~~~~~~~~~~~~
``error_email_to``
~~~~~~~~~~~~~~~~~~

:Description:
    Datasets in an error state include a link to report the error.
    Those reports will be sent to this address.  Error reports are
    disabled if no address is set.  Also this email is shown as a
    contact to user in case of Galaxy misconfiguration and other
    events user may encounter.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~
``email_from``
~~~~~~~~~~~~~~

:Description:
    Email address to use in the 'From' field when sending emails for
    account activations, workflow step notifications, password resets,
    and tool error reports.  We recommend using a string in the
    following format: Galaxy Project <galaxy-no-reply@example.com>. If
    not configured, '<galaxy-no-reply@HOSTNAME>' will be used.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``custom_activation_email_message``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This text will be inserted at the end of the activation email's
    message, before the 'Your Galaxy Team' signature.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``instance_resource_url``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    URL of the support resource for the galaxy instance.  Used outside
    of web contexts such as in activation emails and in Galaxy
    markdown report generation.
    Example value 'https://galaxyproject.org/'
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``instance_access_url``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    URL used to access this Galaxy server. Used outside of web
    contexts such as in Galaxy markdown report generation.
    Example value 'https://usegalaxy.org'
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``email_domain_blocklist_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    E-mail domains blocklist is used for filtering out users that are
    using disposable email addresses at registration.  If their
    address's base domain matches any domain on the list, they are
    refused registration. Address subdomains are ignored (both
    'name@spam.com' and 'name@foo.spam.com' will match 'spam.com').
    Example value 'email_blocklist.conf'
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``email_domain_allowlist_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    E-mail domains allowlist is used to specify allowed email address
    domains. If the list is non-empty and a user attempts registration
    using an email address belonging to a domain that is not on the
    list, registration will be denied. Unlike
    <email_domain_allowlist_file> which matches the address's base
    domain, here email addresses are matched against the full domain
    (base + subdomain). This is a more restrictive option than
    <email_domain_blocklist_file>, and therefore, in case
    <email_domain_allowlist_file> is set and is not empty,
    <email_domain_blocklist_file> will be ignored.
    Example value 'email_allowlist.conf'
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``registration_warning_message``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Registration warning message is used to discourage people from
    registering multiple accounts.  Applies mostly for the main Galaxy
    instance. If no message specified the warning box will not be
    shown.
:Default: ``Please register only one account - we provide this service free of charge and have limited computational resources. Multi-accounts are tracked and will be subjected to account termination and data deletion.``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``user_activation_on``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    User account activation feature global flag.  If set to false, the
    rest of the Account activation configuration is ignored and user
    activation is disabled (i.e. accounts are active since
    registration). The activation is also not working in case the SMTP
    server is not defined.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``activation_grace_period``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Activation grace period (in hours).  Activation is not forced
    (login is not disabled) until grace period has passed.  Users
    under grace period can't run jobs. Enter 0 to disable grace
    period.
:Default: ``3``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~
``inactivity_box_content``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Shown in warning box to users that were not activated yet. In use
    only if activation_grace_period is set.
:Default: ``Your account has not been activated yet.  Feel free to browse around and see what's available, but you won't be able to upload data or run jobs until you have verified your email address.``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``password_expiration_period``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Password expiration period (in days). Users are required to change
    their password every x days. Users will be redirected to the
    change password screen when they log in after their password
    expires. Enter 0 to disable password expiration.
:Default: ``0``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_account_interface``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Allow users to manage their account data, change passwords or
    delete their accounts.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~
``session_duration``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy Session Timeout This provides a timeout (in minutes) after
    which a user will have to log back in. A duration of 0 disables
    this feature.
:Default: ``0``
:Type: int


~~~~~~~~~~~
``ga_code``
~~~~~~~~~~~

:Description:
    You can enter tracking code here to track visitor's behavior
    through your Google Analytics account.  Example: UA-XXXXXXXX-Y
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``plausible_server``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Please enter the URL for the Plausible server (including https) so
    this can be used for tracking with Plausible
    (https://plausible.io/).
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``plausible_domain``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Please enter the URL for the Galaxy server so this can be used for
    tracking with Plausible (https://plausible.io/).
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~
``matomo_server``
~~~~~~~~~~~~~~~~~

:Description:
    Please enter the URL for the Matomo server (including https) so
    this can be used for tracking with Matomo (https://matomo.org/).
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~
``matomo_site_id``
~~~~~~~~~~~~~~~~~~

:Description:
    Please enter the site ID for the Matomo server so this can be used
    for tracking with Matomo (https://matomo.org/).
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~
``display_servers``
~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy can display data at various external browsers.  These
    options specify which browsers should be available.  URLs and
    builds available at these browsers are defined in the specified
    files.
    If use_remote_user is set to true, display application servers
    will be denied access to Galaxy and so displaying datasets in
    these sites will fail. display_servers contains a list of
    hostnames which should be allowed to bypass security to display
    datasets.  Please be aware that there are security implications if
    this is allowed.  More details (including required changes to the
    proxy server config) are available in the Apache proxy
    documentation on the Galaxy Community Hub.
    The list of servers in this sample config are for the UCSC Main,
    Test and Archaea browsers, but the default if left commented is to
    not allow any display sites to bypass security (you must uncomment
    the line below to allow them).
:Default: ``hgw1.cse.ucsc.edu,hgw2.cse.ucsc.edu,hgw3.cse.ucsc.edu,hgw4.cse.ucsc.edu,hgw5.cse.ucsc.edu,hgw6.cse.ucsc.edu,hgw7.cse.ucsc.edu,hgw8.cse.ucsc.edu,lowepub.cse.ucsc.edu``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_old_display_applications``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set this to false to disable the old-style display applications
    that are hardcoded into datatype classes. This may be desirable
    due to using the new-style, XML-defined, display applications that
    have been defined for many of the datatypes that have the
    old-style. There is also a potential security concern with the
    old-style applications, where a malicious party could provide a
    link that appears to reference the Galaxy server, but contains a
    redirect to a third-party server, tricking a Galaxy user to access
    said site.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~
``aws_estimate``
~~~~~~~~~~~~~~~~

:Description:
    This flag enables an AWS cost estimate for every job based on
    their runtime matrices. CPU, RAM and runtime usage is mapped
    against AWS pricing table. Please note, that those numbers are
    only estimates.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``carbon_emission_estimates``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This flag enables carbon emissions estimates for every job based
    on its runtime metrics. CPU and RAM usage and the total job
    runtime are used to determine an estimate value. These estimates
    and are based off of the work of the Green Algorithms Project and
    the United States Environmental Protection Agency (EPA). Visit
    https://www.green-algorithms.org/ and
    https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator.
    for more detals.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``geographical_server_location_code``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The estimated geographical location of the server hosting your
    galaxy instance given as an ISO 3166 code. This is used to make
    carbon emissions estimates more accurate as the location effects
    the carbon intensity values used in the estimate calculation. This
    defaults to "GLOBAL" if not set or the
    `geographical_server_location_code` value is invalid or
    unsupported. To see a full list of supported locations, visit
    https://docs.galaxyproject.org/en/master/admin/carbon_emissions.html
:Default: ``GLOBAL``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``power_usage_effectiveness``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The estimated power usage effectiveness of the data centre housing
    the server your galaxy instance is running on. This can make
    carbon emissions estimates more accurate. For more information on
    how to calculate a PUE value, visit
    https://en.wikipedia.org/wiki/Power_usage_effectiveness
:Default: ``1.67``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``interactivetools_enable``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable InteractiveTools.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``interactivetools_upstream_proxy``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set this to false to redirect users of Interactive tools directly
    to the Interactive tools proxy. `interactivetools_upstream_proxy`
    should only be set to false in development.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``interactivetools_proxy_host``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Hostname and port of Interactive tools proxy. It is assumed to be
    hosted on the same hostname and port as Galaxy by default.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``interactivetools_base_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Base path for interactive tools running at a subpath without a
    subdomain. Defaults to "/".
:Default: ``/``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``interactivetools_map``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Map for the interactivetool proxy. Mappings are stored in a SQLite
    database file located on this path. As an alternative, you may
    also store them in any other RDBMS supported by SQLAlchemy using
    the option ``interactivetoolsproxy_map``, which overrides this
    one.
    The value of this option will be resolved with respect to
    <data_dir>.
:Default: ``interactivetools_map.sqlite``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``interactivetoolsproxy_map``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Use a database supported by SQLAlchemy as map for the
    interactivetool proxy. When this option is set, the value of
    ``interactivetools_map`` is ignored. The value of this option must
    be a `SQLAlchemy database URL
    <https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls>`_.
    Mappings are written to the table "gxitproxy" within the database.
    This value cannot match ``database_connection`` nor
    ``install_database_connection``.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``interactivetools_prefix``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Prefix to use in the formation of the subdomain or path for
    interactive tools
:Default: ``interactivetool``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``retry_interactivetool_metadata_internally``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy Interactive Tools (GxITs) can be stopped from within the
    Galaxy interface, killing the GxIT job without completing its
    metadata setting post-job steps. In such a case it may be
    desirable to set metadata on job outputs internally (in the Galaxy
    job handler process). The default is is the value of
    `retry_metadata_internally`, which defaults to `true`.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~
``visualizations_visible``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Show visualization tab and list in masthead.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~
``message_box_visible``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Show a message box under the masthead.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~
``message_box_content``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Show a message box under the masthead.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``message_box_class``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Class of the message box under the masthead. Possible values are:
    'info' (the default), 'warning', 'error', 'done'.
:Default: ``info``
:Type: str


~~~~~~~~~
``brand``
~~~~~~~~~

:Description:
    Append "{brand}" text to the masthead.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``display_galaxy_brand``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This option has been deprecated, use the `logo_src` instead to
    change the default logo including the galaxy brand title.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~
``pretty_datetime_format``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Format string used when showing date and time information. The
    string may contain: - the directives used by Python
    time.strftime() function (see
    https://docs.python.org/library/time.html#time.strftime), -
    $locale (complete format string for the server locale), - $iso8601
    (complete format string as specified by ISO 8601 international
    standard).
:Default: ``$locale (UTC)``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``trs_servers_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Allow import of workflows from the TRS servers configured in the
    specified YAML or JSON file. The file should be a list with 'id',
    'label', and 'api_url' for each entry. Optionally, 'link_url' and
    'doc' may be specified as well for each entry.
    If this is null (the default), a simple configuration containing
    just Dockstore will be used.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``trs_servers_conf.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_preferences_extra_conf_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Location of the configuration file containing extra user
    preferences.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``user_preferences_extra_conf.yml``
:Type: str


~~~~~~~~~~~~~~~~~~
``default_locale``
~~~~~~~~~~~~~~~~~~

:Description:
    Default localization for Galaxy UI. Allowed values are listed at
    the end of client/src/nls/locale.js. With the default value
    (auto), the locale will be automatically adjusted to the user's
    navigator language. Users can override this settings in their user
    preferences if the localization settings are enabled in
    user_preferences_extra_conf.yml
:Default: ``auto``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``galaxy_url_prefix``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    URL prefix for Galaxy application. If Galaxy should be served
    under a prefix set this to the desired prefix value.
:Default: ``/``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``galaxy_infrastructure_url``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    URL (with schema http/https) of the Galaxy instance as accessible
    within your local network. This URL is used as a default by pulsar
    file staging and Interactive Tool containers for communicating
    back with Galaxy via the API.
    If you plan to run Interactive Tools make sure the docker
    container can reach this URL.
:Default: ``http://localhost:8080``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``galaxy_infrastructure_web_port``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If the above URL cannot be determined ahead of time in dynamic
    environments but the port which should be used to access Galaxy
    can be - this should be set to prevent Galaxy from having to
    guess.  For example if Galaxy is sitting behind a proxy with
    REMOTE_USER enabled - infrastructure shouldn't talk to Python
    processes directly and this should be set to 80 or 443, etc... If
    unset this file will be read for a server block defining a port
    corresponding to the webapp.
:Default: ``8080``
:Type: int


~~~~~~~~~~~~~~~
``welcome_url``
~~~~~~~~~~~~~~~

:Description:
    The URL of the page to display in Galaxy's middle pane when
    loaded.  This can be an absolute or relative URL.
:Default: ``/static/welcome.html``
:Type: str


~~~~~~~~~~~~
``logo_url``
~~~~~~~~~~~~

:Description:
    The URL linked by the "Galaxy/brand" text.
:Default: ``/``
:Type: str


~~~~~~~~~~~~
``logo_src``
~~~~~~~~~~~~

:Description:
    The brand image source.
:Default: ``/static/favicon.svg``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``logo_src_secondary``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The custom brand image source.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~
``helpsite_url``
~~~~~~~~~~~~~~~~

:Description:
    The URL linked by the "Galaxy Help" link in the "Help" menu.
:Default: ``https://help.galaxyproject.org/``
:Type: str


~~~~~~~~~~~~
``wiki_url``
~~~~~~~~~~~~

:Description:
    The URL linked by the "Community Hub" link in the "Help" menu.
:Default: ``https://galaxyproject.org/``
:Type: str


~~~~~~~~~~~~~
``quota_url``
~~~~~~~~~~~~~

:Description:
    The URL linked for quota information in the UI.
:Default: ``https://galaxyproject.org/support/account-quotas/``
:Type: str


~~~~~~~~~~~~~~~
``support_url``
~~~~~~~~~~~~~~~

:Description:
    The URL linked by the "Support" link in the "Help" menu.
:Default: ``https://galaxyproject.org/support/``
:Type: str


~~~~~~~~~~~~~~~~
``citation_url``
~~~~~~~~~~~~~~~~

:Description:
    The URL linked by the "How to Cite Galaxy" link in the "Help"
    menu.
:Default: ``https://galaxyproject.org/citing-galaxy``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``release_doc_base_url``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The URL linked by the "Galaxy Version" link in the "Help" menu.
:Default: ``https://docs.galaxyproject.org/en/release_``
:Type: str


~~~~~~~~~~~~~~~~~~~
``screencasts_url``
~~~~~~~~~~~~~~~~~~~

:Description:
    The URL linked by the "Videos" link in the "Help" menu.
:Default: ``https://www.youtube.com/c/galaxyproject``
:Type: str


~~~~~~~~~~~~~
``terms_url``
~~~~~~~~~~~~~

:Description:
    The URL linked by the "Terms and Conditions" link in the "Help"
    menu, as well as on the user registration and login forms and in
    the activation emails.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~
``static_enabled``
~~~~~~~~~~~~~~~~~~

:Description:
    Serve static content, which must be enabled if you're not serving
    it via a proxy server.  These options should be self explanatory
    and so are not documented individually.  You can use these paths
    (or ones in the proxy server) to point to your own styles.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~
``static_cache_time``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Serve static content, which must be enabled if you're not serving
    it via a proxy server.  These options should be self explanatory
    and so are not documented individually.  You can use these paths
    (or ones in the proxy server) to point to your own styles.
:Default: ``360``
:Type: int


~~~~~~~~~~~~~~
``static_dir``
~~~~~~~~~~~~~~

:Description:
    Serve static content, which must be enabled if you're not serving
    it via a proxy server.  These options should be self explanatory
    and so are not documented individually.  You can use these paths
    (or ones in the proxy server) to point to your own styles.
:Default: ``static/``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``static_images_dir``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Serve static content, which must be enabled if you're not serving
    it via a proxy server.  These options should be self explanatory
    and so are not documented individually.  You can use these paths
    (or ones in the proxy server) to point to your own styles.
:Default: ``static/images``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``static_favicon_dir``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Serve static content, which must be enabled if you're not serving
    it via a proxy server.  These options should be self explanatory
    and so are not documented individually.  You can use these paths
    (or ones in the proxy server) to point to your own styles.
:Default: ``static/favicon.ico``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``static_scripts_dir``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Serve static content, which must be enabled if you're not serving
    it via a proxy server.  These options should be self explanatory
    and so are not documented individually.  You can use these paths
    (or ones in the proxy server) to point to your own styles.
:Default: ``static/scripts/``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``static_style_dir``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Serve static content, which must be enabled if you're not serving
    it via a proxy server.  These options should be self explanatory
    and so are not documented individually.  You can use these paths
    (or ones in the proxy server) to point to your own styles.
:Default: ``static/style``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``static_robots_txt``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Serve static content, which must be enabled if you're not serving
    it via a proxy server.  These options should be self explanatory
    and so are not documented individually.  You can use these paths
    (or ones in the proxy server) to point to your own styles.
:Default: ``static/robots.txt``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``display_chunk_size``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Incremental Display Options
:Default: ``65536``
:Type: int


~~~~~~~~~~~~~~~~~~~~
``apache_xsendfile``
~~~~~~~~~~~~~~~~~~~~

:Description:
    For help on configuring the Advanced proxy features, see:
    https://docs.galaxyproject.org/en/master/admin/production.html
    Apache can handle file downloads (Galaxy-to-user) via
    mod_xsendfile.  Set this to true to inform Galaxy that
    mod_xsendfile is enabled upstream.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``nginx_x_accel_redirect_base``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The same download handling can be done by nginx using
    X-Accel-Redirect.  This should be set to the path defined in the
    nginx config as an internal redirect with access to Galaxy's data
    files (see documentation linked above).
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~
``upstream_gzip``
~~~~~~~~~~~~~~~~~

:Description:
    If using compression in the upstream proxy server, use this option
    to disable gzipping of dataset collection and library archives,
    since the upstream server will do it faster on the fly. To enable
    compression add ``application/zip`` to the proxy's compressable
    mimetypes.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~
``upstream_mod_zip``
~~~~~~~~~~~~~~~~~~~~

:Description:
    If using the mod-zip module in nginx, use this option to assemble
    zip archives in nginx. This is preferable over the upstream_gzip
    option as Galaxy does not need to serve the archive. Requires
    setting up internal nginx locations to all paths that can be
    archived. See
    https://docs.galaxyproject.org/en/master/admin/nginx.html#creating-archives-with-mod-zip
    for details.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~
``x_frame_options``
~~~~~~~~~~~~~~~~~~~

:Description:
    The following default adds a header to web request responses that
    will cause modern web browsers to not allow Galaxy to be embedded
    in the frames of web applications hosted at other hosts - this can
    help prevent a class of attack called clickjacking
    (https://www.owasp.org/index.php/Clickjacking).  If you configure
    a proxy in front of Galaxy - please ensure this header remains
    intact to protect your users.  Uncomment and leave empty to not
    set the `X-Frame-Options` header.
:Default: ``SAMEORIGIN``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``nginx_upload_store``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    nginx can also handle file uploads (user-to-Galaxy) via
    nginx_upload_module. Configuration for this is complex and
    explained in detail in the documentation linked above.  The upload
    store is a temporary directory in which files uploaded by the
    upload module will be placed.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``nginx_upload_path``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    This value overrides the action set on the file upload form, e.g.
    the web path where the nginx_upload_module has been configured to
    intercept upload requests.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``nginx_upload_job_files_store``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy can also use nginx_upload_module to receive files staged
    out upon job completion by remote job runners (i.e. Pulsar) that
    initiate staging operations on the remote end.  See the Galaxy
    nginx documentation for the corresponding nginx configuration.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``nginx_upload_job_files_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy can also use nginx_upload_module to receive files staged
    out upon job completion by remote job runners (i.e. Pulsar) that
    initiate staging operations on the remote end.  See the Galaxy
    nginx documentation for the corresponding nginx configuration.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``tus_upload_store``
~~~~~~~~~~~~~~~~~~~~

:Description:
    The upload store is a temporary directory in which files uploaded
    by the tus middleware or server for user uploads will be placed.
    Defaults to new_file_path if not set.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tus_upload_store_job_files``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The upload store is a temporary directory in which files uploaded
    by the tus middleware or server for remote job files (Pulsar) will
    be placed. Defaults to tus_upload_store if not set.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``chunk_upload_size``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy can upload user files in chunks without using nginx. Enable
    the chunk uploader by specifying a chunk size larger than 0. The
    chunk size is specified in bytes (default: 10MB).
:Default: ``10485760``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_manage``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Have Galaxy manage dynamic proxy component for routing requests to
    other services based on Galaxy's session cookie.  It will attempt
    to do this by default though you do need to install node+npm and
    do an npm install from `lib/galaxy/web/proxy/js`.  It is generally
    more robust to configure this externally, managing it in the same
    way Galaxy itself is managed.  If true, Galaxy will only launch
    the proxy if it is actually going to be used (e.g. for Jupyter).
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~
``dynamic_proxy``
~~~~~~~~~~~~~~~~~

:Description:
    As of 16.04 Galaxy supports multiple proxy types. The original
    NodeJS implementation, alongside a new Golang
    single-binary-no-dependencies version. Valid values are (node,
    golang)
:Default: ``node``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_session_map``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The NodeJS dynamic proxy can use an SQLite database or a JSON file
    for IPC, set that here.
    The value of this option will be resolved with respect to
    <data_dir>.
:Default: ``session_map.sqlite``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_bind_port``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set the port and IP for the dynamic proxy to bind to, this must
    match the external configuration if dynamic_proxy_manage is set to
    false.
:Default: ``8800``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_bind_ip``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set the port and IP for the dynamic proxy to bind to, this must
    match the external configuration if dynamic_proxy_manage is set to
    false.
:Default: ``0.0.0.0``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_debug``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable verbose debugging of Galaxy-managed dynamic proxy.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_external_proxy``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The dynamic proxy is proxied by an external proxy (e.g. apache
    frontend to nodejs to wrap connections in SSL).
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_prefix``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Additionally, when the dynamic proxy is proxied by an upstream
    server, you'll want to specify a prefixed URL so both Galaxy and
    the proxy reside under the same path that your cookies are under.
    This will result in a url like
    https://FQDN/galaxy-prefix/gie_proxy for proxying
:Default: ``gie_proxy``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_golang_noaccess``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This attribute governs the minimum length of time between
    consecutive HTTP/WS requests through the proxy, before the proxy
    considers a container as being inactive and kills it.
:Default: ``60``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_golang_clean_interval``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    In order to kill containers, the golang proxy has to check at some
    interval for possibly dead containers. This is exposed as a
    configurable parameter, but the default value is probably fine.
:Default: ``10``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_golang_docker_address``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The golang proxy needs to know how to talk to your docker daemon.
    Currently TLS is not supported, that will come in an update.
:Default: ``unix:///var/run/docker.sock``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_golang_api_key``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The golang proxy uses a RESTful HTTP API for communication with
    Galaxy instead of a JSON or SQLite file for IPC. If you do not
    specify this, it will be set randomly for you. You should set this
    if you are managing the proxy manually.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~
``auto_configure_logging``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If true, Galaxy will attempt to configure a simple root logger if
    a "loggers" section does not appear in this configuration file.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~
``log_destination``
~~~~~~~~~~~~~~~~~~~

:Description:
    Log destination, defaults to special value "stdout" that logs to
    standard output. If set to anything else, then it will be
    interpreted as a path that will be used as the log file, and
    logging to stdout will be disabled.
:Default: ``stdout``
:Type: str


~~~~~~~~~~~~~~~~~~~
``log_rotate_size``
~~~~~~~~~~~~~~~~~~~

:Description:
    Size of log file at which size it will be rotated as per the
    documentation in
    https://docs.python.org/library/logging.handlers.html#logging.handlers.RotatingFileHandler
    If log_rotate_count is not also set, no log rotation will be
    performed. A value of 0 (the default) means no rotation. Size can
    be a number of bytes or a human-friendly representation like "100
    MB" or "1G".
:Default: ``0``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``log_rotate_count``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Number of log file backups to keep, per the documentation in
    https://docs.python.org/library/logging.handlers.html#logging.handlers.RotatingFileHandler
    Any additional rotated log files will automatically be pruned. If
    log_rotate_size is not also set, no log rotation will be
    performed. A value of 0 (the default) means no rotation.
:Default: ``0``
:Type: int


~~~~~~~~~~~~~
``log_level``
~~~~~~~~~~~~~

:Description:
    Verbosity of console log messages. Acceptable values can be found
    here: https://docs.python.org/library/logging.html#logging-levels
    A custom debug level of "TRACE" is available for even more
    verbosity.
:Default: ``DEBUG``
:Type: str


~~~~~~~~~~~
``logging``
~~~~~~~~~~~

:Description:
    Controls where and how the server logs messages. If set, overrides
    all settings in the log_* configuration options. Configuration is
    described in the documentation at:
    https://docs.galaxyproject.org/en/master/admin/config_logging.html
:Default: ``None``
:Type: map


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``database_engine_option_echo``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Print database operations to the server log (warning, quite
    verbose!).
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``database_engine_option_echo_pool``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Print database pool operations to the server log (warning, quite
    verbose!).
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~
``log_events``
~~~~~~~~~~~~~~

:Description:
    Turn on logging of application events and some user events to the
    database.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~
``log_actions``
~~~~~~~~~~~~~~~

:Description:
    Turn on logging of user actions to the database.  Actions
    currently logged are grid views, tool searches, and use of
    "recently" used tools menu.  The log_events and log_actions
    functionality will eventually be merged.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~
``fluent_log``
~~~~~~~~~~~~~~

:Description:
    Fluentd configuration.  Various events can be logged to the
    fluentd instance configured below by enabling fluent_log.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~
``fluent_host``
~~~~~~~~~~~~~~~

:Description:
    Fluentd configuration.  Various events can be logged to the
    fluentd instance configured below by enabling fluent_log.
:Default: ``localhost``
:Type: str


~~~~~~~~~~~~~~~
``fluent_port``
~~~~~~~~~~~~~~~

:Description:
    Fluentd configuration.  Various events can be logged to the
    fluentd instance configured below by enabling fluent_log.
:Default: ``24224``
:Type: int


~~~~~~~~~~~~~~~~~~~~~
``sanitize_all_html``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Sanitize all HTML tool output.  By default, all tool output served
    as 'text/html' will be sanitized thoroughly.  This can be disabled
    if you have special tools that require unaltered output.  WARNING:
    disabling this does make the Galaxy instance susceptible to XSS
    attacks initiated by your users.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``sanitize_allowlist_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Datasets created by tools listed in this file are trusted and will
    not have their HTML sanitized on display.  This can be manually
    edited or manipulated through the Admin control panel -- see
    "Manage Allowlist"
    The value of this option will be resolved with respect to
    <managed_config_dir>.
:Default: ``sanitize_allowlist.txt``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``serve_xss_vulnerable_mimetypes``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    By default Galaxy will serve non-HTML tool output that may
    potentially contain browser executable JavaScript content as plain
    text.  This will for instance cause SVG datasets to not render
    properly and so may be disabled by setting this option to true.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``allowed_origin_hostnames``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Return a Access-Control-Allow-Origin response header that matches
    the Origin header of the request if that Origin hostname matches
    one of the strings or regular expressions listed here. This is a
    comma-separated list of hostname strings or regular expressions
    beginning and ending with /. E.g.
    mysite.com,google.com,usegalaxy.org,/^[\w\.]*example\.com/ See:
    https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``trust_jupyter_notebook_conversion``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set to true to use Jupyter nbconvert to build HTML from Jupyter
    notebooks in Galaxy histories.  This process may allow users to
    execute arbitrary code or serve arbitrary HTML.  If enabled,
    Jupyter must be available and on Galaxy's PATH, to do this run
    `pip install jinja2 pygments jupyter` in Galaxy's virtualenv.
:Default: ``false``
:Type: bool


~~~~~~~~~
``debug``
~~~~~~~~~

:Description:
    Debug enables access to various config options useful for
    development and debugging: use_lint, use_profile, and
    use_printdebug.  It also causes the files used by PBS/SGE
    (submission script, output, and error) to remain on disk after the
    job is complete.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``use_access_logging_middleware``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Log request start as well as request end. Disables uvicorn access
    log handler.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~
``use_lint``
~~~~~~~~~~~~

:Description:
    Check for WSGI compliance.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~
``use_profile``
~~~~~~~~~~~~~~~

:Description:
    Run the Python profiler on each request.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~
``use_printdebug``
~~~~~~~~~~~~~~~~~~

:Description:
    Intercept print statements and show them on the returned page.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``monitor_thread_join_timeout``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When stopping Galaxy cleanly, how much time to give various
    monitoring/polling threads to finish before giving up on joining
    them. Set to 0 to disable this and terminate without waiting.
    Among others, these threads include the job handler workers, which
    are responsible for preparing/submitting and collecting/finishing
    jobs, and which can cause job errors if not shut down cleanly. If
    using supervisord, consider also increasing the value of
    `stopwaitsecs`. See the Galaxy Admin Documentation for more.
:Default: ``30``
:Type: int


~~~~~~~~~~~~~~~~~
``use_heartbeat``
~~~~~~~~~~~~~~~~~

:Description:
    Write thread status periodically to 'heartbeat.log',  (careful,
    uses disk space rapidly!).  Useful to determine why your processes
    may be consuming a lot of CPU.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~
``heartbeat_interval``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Control the period (in seconds) between dumps. Use -1 to disable.
    Regardless of this setting, if use_heartbeat is enabled, you can
    send a Galaxy process SIGUSR1 (`kill -USR1`) to force a dump.
:Default: ``20``
:Type: int


~~~~~~~~~~~~~~~~~
``heartbeat_log``
~~~~~~~~~~~~~~~~~

:Description:
    Heartbeat log filename. Can accept the template variables
    {server_name} and {pid}
:Default: ``heartbeat_{server_name}.log``
:Type: str


~~~~~~~~~~~~~~
``sentry_dsn``
~~~~~~~~~~~~~~

:Description:
    Log to Sentry Sentry is an open source logging and error
    aggregation platform.  Setting sentry_dsn will enable the Sentry
    middleware and errors will be sent to the indicated sentry
    instance.  This connection string is available in your sentry
    instance under <project_name> -> Settings -> API Keys.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``sentry_event_level``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Determines the minimum log level that will be sent as an event to
    Sentry. Possible values are DEBUG, INFO, WARNING, ERROR or
    CRITICAL.
:Default: ``ERROR``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``sentry_traces_sample_rate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set to a number between 0 and 1. With this option set, every
    transaction created will have that percentage chance of being sent
    to Sentry. A value higher than 0 is required to analyze
    performance.
:Default: ``0.0``
:Type: float


~~~~~~~~~~~~~~~~~~~
``sentry_ca_certs``
~~~~~~~~~~~~~~~~~~~

:Description:
    Use this option to provide the path to location of the CA
    (Certificate Authority) certificate file if the sentry server uses
    a self-signed certificate.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~
``statsd_host``
~~~~~~~~~~~~~~~

:Description:
    Log to statsd Statsd is an external statistics aggregator
    (https://github.com/etsy/statsd) Enabling the following options
    will cause galaxy to log request timing and other statistics to
    the configured statsd instance.  The statsd_prefix is useful if
    you are running multiple Galaxy instances and want to segment
    statistics between them within the same aggregator.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~
``statsd_port``
~~~~~~~~~~~~~~~

:Description:
    Log to statsd Statsd is an external statistics aggregator
    (https://github.com/etsy/statsd) Enabling the following options
    will cause galaxy to log request timing and other statistics to
    the configured statsd instance.  The statsd_prefix is useful if
    you are running multiple Galaxy instances and want to segment
    statistics between them within the same aggregator.
:Default: ``8125``
:Type: int


~~~~~~~~~~~~~~~~~
``statsd_prefix``
~~~~~~~~~~~~~~~~~

:Description:
    Log to statsd Statsd is an external statistics aggregator
    (https://github.com/etsy/statsd) Enabling the following options
    will cause galaxy to log request timing and other statistics to
    the configured statsd instance.  The statsd_prefix is useful if
    you are running multiple Galaxy instances and want to segment
    statistics between them within the same aggregator.
:Default: ``galaxy``
:Type: str


~~~~~~~~~~~~~~~~~~~
``statsd_influxdb``
~~~~~~~~~~~~~~~~~~~

:Description:
    If you are using telegraf to collect these metrics and then
    sending them to InfluxDB, Galaxy can provide more nicely tagged
    metrics. Instead of sending prefix + dot-separated-path, Galaxy
    will send prefix with a tag path set to the page url
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~
``statsd_mock_calls``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Mock out statsd client calls - only used by testing infrastructure
    really. Do not set this in production environments.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~
``library_import_dir``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Add an option to the library upload form which allows
    administrators to upload a directory of files.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_library_import_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Add an option to the library upload form which allows authorized
    non-administrators to upload a directory of files.  The configured
    directory must contain sub-directories named the same as the
    non-admin user's Galaxy login ( email ).  The non-admin user is
    restricted to uploading files or sub-directories of files
    contained in their directory.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_library_import_dir_auto_creation``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If user_library_import_dir is set, this option will auto create a
    library import directory for every user (based on their email)
    upon login.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_library_import_symlink_allowlist``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    For security reasons, users may not import any files that actually
    lie outside of their `user_library_import_dir` (e.g. using
    symbolic links). A list of directories can be allowed by setting
    the following option (the list is comma-separated). Be aware that
    *any* user with library import permissions can import from
    anywhere in these directories (assuming they are able to create
    symlinks to them).
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_library_import_check_permissions``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    In conjunction or alternatively, Galaxy can restrict user library
    imports to those files that the user can read (by checking basic
    unix permissions). For this to work, the username has to match the
    username on the filesystem.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~
``allow_path_paste``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Allow admins to paste filesystem paths during upload. For
    libraries this adds an option to the admin library upload tool
    allowing admins to paste filesystem paths to files and directories
    in a box, and these paths will be added to a library.  For history
    uploads, this allows pasting in paths as URIs. (i.e. prefixed with
    file://). Set to true to enable.  Please note the security
    implication that this will give Galaxy Admins access to anything
    your Galaxy user has access to.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``disable_library_comptypes``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Users may choose to download multiple files from a library in an
    archive.  By default, Galaxy allows users to select from a few
    different archive formats if testing shows that Galaxy is able to
    create files using these formats. Specific formats can be disabled
    with this option, separate more than one format with commas.
    Available formats are currently 'zip', 'gz', and 'bz2'.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~
``tool_name_boost``
~~~~~~~~~~~~~~~~~~~

:Description:
    In tool search, a query match against a tool's name text will
    receive this score multiplier.
:Default: ``20.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_name_exact_multiplier``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If a search query matches a tool name exactly, the score will be
    multiplied by this factor.
:Default: ``10.0``
:Type: float


~~~~~~~~~~~~~~~~~
``tool_id_boost``
~~~~~~~~~~~~~~~~~

:Description:
    In tool search, a query match against a tool's ID text will
    receive this score multiplier. The query must be an exact match
    against ID in order to be counted as a match.
:Default: ``20.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~
``tool_section_boost``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    In tool search, a query match against a tool's section text will
    receive this score multiplier.
:Default: ``3.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_description_boost``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    In tool search, a query match against a tool's description text
    will receive this score multiplier.
:Default: ``8.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~
``tool_label_boost``
~~~~~~~~~~~~~~~~~~~~

:Description:
    In tool search, a query match against a tool's label text will
    receive this score multiplier.
:Default: ``1.0``
:Type: float


~~~~~~~~~~~~~~~~~~~
``tool_stub_boost``
~~~~~~~~~~~~~~~~~~~

:Description:
    A stub is parsed from the GUID as "owner/repo/tool_id". In tool
    search, a query match against a tool's stub text will receive this
    score multiplier.
:Default: ``2.0``
:Type: float


~~~~~~~~~~~~~~~~~~~
``tool_help_boost``
~~~~~~~~~~~~~~~~~~~

:Description:
    In tool search, a query match against a tool's help text will
    receive this score multiplier.
:Default: ``1.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~
``tool_help_bm25f_k1``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The lower this parameter, the greater the diminishing reward for
    term frequency in the help text. A higher K1 increases the level
    of reward for additional occurences of a term. The default value
    will provide a slight increase in score for the first, second and
    third occurrence and little reward thereafter.
:Default: ``0.5``
:Type: float


~~~~~~~~~~~~~~~~~~~~~
``tool_search_limit``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Limits the number of results in toolbox search. Use to set the
    maximum number of tool search results to display.
:Default: ``20``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_enable_ngram_search``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Disabling this will prevent partial matches on tool names.
    Enable/disable Ngram-search for tools. It makes tool search
    results tolerant for spelling mistakes in the query, and will also
    match query substrings e.g. "genome" will match "genomics" or
    "metagenome".
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~
``tool_ngram_minsize``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set minimum character length of ngrams
:Default: ``3``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~
``tool_ngram_maxsize``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set maximum character length of ngrams
:Default: ``4``
:Type: int


~~~~~~~~~~~~~~~~~~~~~
``tool_ngram_factor``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Ngram matched scores will be multiplied by this factor. Should
    always be below 1, because an ngram match is a partial match of a
    search term.
:Default: ``0.2``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_test_data_directories``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set tool test data directory. The test framework sets this value
    to
    'test-data,https://github.com/galaxyproject/galaxy-test-data.git'
    which will cause Galaxy to clone down extra test data on the fly
    for certain tools distributed with Galaxy but this is likely not
    appropriate for production systems. Instead one can simply clone
    that repository directly and specify a path here instead of a Git
    HTTP repository.
:Default: ``test-data``
:Type: str


~~~~~~~~~~~~~
``id_secret``
~~~~~~~~~~~~~

:Description:
    Galaxy encodes various internal values when these values will be
    output in some format (for example, in a URL or cookie).  You
    should set a key to be used by the algorithm that encodes and
    decodes these values. It can be any string with a length between 5
    and 56 bytes. One simple way to generate a value for this is with
    the shell command:   python -c 'from __future__ import
    print_function; import time; print(time.time())' | md5sum | cut -f
    1 -d ' '
:Default: ``USING THE DEFAULT IS NOT SECURE!``
:Type: str


~~~~~~~~~~~~~~~~~~~
``use_remote_user``
~~~~~~~~~~~~~~~~~~~

:Description:
    User authentication can be delegated to an upstream proxy server
    (usually Apache).  The upstream proxy should set a REMOTE_USER
    header in the request. Enabling remote user disables regular
    logins.  For more information, see:
    https://docs.galaxyproject.org/en/master/admin/special_topics/apache.html
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~
``remote_user_maildomain``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If use_remote_user is enabled and your external authentication
    method just returns bare usernames, set a default mail domain to
    be appended to usernames, to become your Galaxy usernames (email
    addresses).
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``remote_user_header``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If use_remote_user is enabled, the header that the upstream proxy
    provides the remote username in defaults to HTTP_REMOTE_USER (the
    ``HTTP_`` is prepended by WSGI).  This option allows you to change
    the header.  Note, you still need to prepend ``HTTP_`` to the
    header in this option, but your proxy server should *not* include
    ``HTTP_`` at the beginning of the header name.
:Default: ``HTTP_REMOTE_USER``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``remote_user_secret``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If use_remote_user is enabled, anyone who can log in to the Galaxy
    host may impersonate any other user by simply sending the
    appropriate header.  Thus a secret shared between the upstream
    proxy server, and Galaxy is required. If anyone other than the
    Galaxy user is using the server, then apache/nginx should pass a
    value in the header 'GX_SECRET' that is identical to the one
    below.
:Default: ``USING THE DEFAULT IS NOT SECURE!``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``remote_user_logout_href``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If use_remote_user is enabled, you can set this to a URL that will
    log your users out.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``post_user_logout_href``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This is the default url to which users are redirected after they
    log out.
:Default: ``/root/login?is_logout_redirect=true``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``normalize_remote_user_email``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If your proxy and/or authentication source does not normalize
    e-mail addresses or user names being passed to Galaxy - set this
    option to true to force these to lower case.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~
``single_user``
~~~~~~~~~~~~~~~

:Description:
    If an e-mail address is specified here, it will hijack remote user
    mechanics (``use_remote_user``) and have the webapp inject a
    single fixed user. This has the effect of turning Galaxy into a
    single user application with no login or external proxy required.
    Such applications should not be exposed to the world.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~
``admin_users``
~~~~~~~~~~~~~~~

:Description:
    Administrative users - set this to a comma-separated list of valid
    Galaxy users (email addresses).  These users will have access to
    the Admin section of the server, and will have access to create
    users, groups, roles, libraries, and more.  For more information,
    see:   https://galaxyproject.org/admin/
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~
``require_login``
~~~~~~~~~~~~~~~~~

:Description:
    Force everyone to log in (disable anonymous access).
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``show_welcome_with_login``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Show the site's welcome page (see welcome_url) alongside the login
    page (even if require_login is true).
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~
``prefer_custos_login``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Controls the order of the login page to prefer Custos-based login
    and registration.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~
``allow_user_creation``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Allow unregistered users to create new accounts (otherwise, they
    will have to be created by an admin).
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~
``allow_user_deletion``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Allow administrators to delete accounts.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``allow_user_impersonation``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Allow administrators to log in as other users (useful for
    debugging).
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``show_user_prepopulate_form``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When using LDAP for authentication, allow administrators to
    pre-populate users using an additional form on 'Create new user'
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``upload_from_form_button``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If 'always-on', add another button to tool form data inputs that
    allow uploading data from the tool form in fewer clicks (at the
    expense of making the form more complicated). This applies to
    workflows as well.
    Avoiding making this a boolean because we may add options such as
    'in-single-form-view' or 'in-simplified-workflow-views'.
    https://github.com/galaxyproject/galaxy/pull/9809/files#r461889109
:Default: ``always-off``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``allow_user_dataset_purge``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Allow users to remove their datasets from disk immediately
    (otherwise, datasets will be removed after a time period specified
    by an administrator in the cleanup scripts run via cron)
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``new_user_dataset_access_role_default_private``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    By default, users' data will be public, but setting this to true
    will cause it to be private.  Does not affect existing users and
    data, only ones created after this option is set.  Users may still
    change their default back to public.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~
``expose_user_name``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Expose user list.  Setting this to true will expose the user list
    to authenticated users.  This makes sharing datasets in smaller
    galaxy instances much easier as they can type a name/email and
    have the correct user show up. This makes less sense on large
    public Galaxy instances where that data shouldn't be exposed.  For
    semi-public Galaxies, it may make sense to expose just the
    username and not email, or vice versa.
    If enable_beta_gdpr is set to true, then this option will be
    overridden and set to false.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~
``expose_user_email``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Expose user list.  Setting this to true will expose the user list
    to authenticated users.  This makes sharing datasets in smaller
    galaxy instances much easier as they can type a name/email and
    have the correct user show up. This makes less sense on large
    public Galaxy instances where that data shouldn't be exposed.  For
    semi-public Galaxies, it may make sense to expose just the
    username and not email, or vice versa.
    If enable_beta_gdpr is set to true, then this option will be
    overridden and set to false.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~
``fetch_url_allowlist``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    List of allowed local network addresses for "Upload from URL"
    dialog. By default, Galaxy will deny access to the local network
    address space, to prevent users making requests to services which
    the administrator did not intend to expose. Previously, you could
    request any network service that Galaxy might have had access to,
    even if the user could not normally access it. It should be a
    comma-separated list of IP addresses or IP address/mask, e.g.
    10.10.10.10,10.0.1.0/24,fd00::/8
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``enable_beta_gdpr``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Enables GDPR Compliance mode. This makes several changes to the
    way Galaxy logs and exposes data externally such as removing
    emails and usernames from logs and bug reports. It also causes the
    delete user admin action to permanently redact their username and
    password, but not to delete data associated with the account as
    this is not currently easily implementable.
    You are responsible for removing personal data from backups.
    This forces expose_user_email and expose_user_name to be false,
    and forces user_deletion to be true to support the right to
    erasure.
    Please read the GDPR section under the special topics area of the
    admin documentation.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_beta_workflow_modules``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable beta workflow modules that should not yet be considered
    part of Galaxy's stable API. (The module state definitions may
    change and workflows built using these modules may not function in
    the future.)
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~
``edam_panel_views``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Comma-separated list of the EDAM panel views to load - choose from
    merged, operations, topics. Set to empty string to disable EDAM
    all together. Set default_panel_view to 'ontology:edam_topics' to
    override default tool panel to use an EDAM view.
:Default: ``operations,topics``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``edam_toolbox_ontology_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Sets the path to EDAM ontology file - if the path doesn't exist
    PyPI package data will be loaded.
    The value of this option will be resolved with respect to
    <data_dir>.
:Default: ``EDAM.tsv``
:Type: str


~~~~~~~~~~~~~~~~~~~
``panel_views_dir``
~~~~~~~~~~~~~~~~~~~

:Description:
    Directory to check out for toolbox tool panel views. The path is
    relative to the Galaxy root dir.  To use an absolute path begin
    the path with '/'.  This is a comma-separated list.
:Default: ``config/plugins/activities``
:Type: str


~~~~~~~~~~~~~~~
``panel_views``
~~~~~~~~~~~~~~~

:Description:
    Definitions of static toolbox panel views embedded directly in the
    config instead of reading YAML from directory with
    panel_views_dir.
:Default: ``None``
:Type: seq


~~~~~~~~~~~~~~~~~~~~~~
``default_panel_view``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Default tool panel view for the current Galaxy configuration. This
    should refer to an id of a panel view defined using the
    panel_views or panel_views_dir configuration options or an EDAM
    panel view. The default panel view is simply called `default` and
    refers to the tool panel state defined by the integrated tool
    panel.
:Default: ``default``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``default_workflow_export_format``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Default format for the export of workflows. Possible values are
    'ga' or 'format2'.
:Default: ``ga``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``parallelize_workflow_scheduling_within_histories``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If multiple job handlers are enabled, allow Galaxy to schedule
    workflow invocations in multiple handlers simultaneously. This is
    discouraged because it results in a less predictable order of
    workflow datasets within in histories.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``maximum_workflow_invocation_duration``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This is the maximum amount of time a workflow invocation may stay
    in an active scheduling state in seconds. Set to -1 to disable
    this maximum and allow any workflow invocation to schedule
    indefinitely. The default corresponds to 1 month.
:Default: ``2678400``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``maximum_workflow_jobs_per_scheduling_iteration``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Specify a maximum number of jobs that any given workflow
    scheduling iteration can create. Set this to a positive integer to
    prevent large collection jobs in a workflow from preventing other
    jobs from executing. This may also mitigate memory issues
    associated with scheduling workflows at the expense of increased
    total DB traffic because model objects are expunged from the SQL
    alchemy session between workflow invocation scheduling iterations.
    Set to -1 to disable any such maximum.
:Default: ``1000``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~
``flush_per_n_datasets``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Maximum number of datasets to create before flushing created
    datasets to database. This affects tools that create many output
    datasets. Higher values will lead to fewer database flushes and
    faster execution, but require more memory. Set to -1 to disable
    creating datasets in batches.
:Default: ``1000``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~
``max_discovered_files``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set this to a positive integer value to limit the number of
    datasets that can be discovered by a single job. This prevents
    accidentally creating large numbers of datasets when running tools
    that create a potentially unlimited number of output datasets,
    such as tools that split a file into a collection of datasets for
    each line in an input dataset.
:Default: ``10000``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``history_local_serial_workflow_scheduling``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Force serial scheduling of workflows within the context of a
    particular history
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~
``enable_oidc``
~~~~~~~~~~~~~~~

:Description:
    Enables and disables OpenID Connect (OIDC) support.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~
``oidc_config_file``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Sets the path to OIDC configuration file.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``oidc_config.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``oidc_backends_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Sets the path to OIDC backends configuration file.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``oidc_backends_config.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``oidc_scope_prefix``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Sets the prefix for OIDC scopes specific to this Galaxy instance.
    If an API call is made against this Galaxy instance using an OIDC
    bearer token, any scopes must be prefixed with this value e.g.
    https://galaxyproject.org/api. More concretely, to request all
    permissions that the user has, the scope would have to be
    specified as "<prefix>:*". e.g "https://galaxyproject.org/api:*".
    Currently, only * is recognised as a valid scope, and future
    iterations may provide more fine-grained scopes.
:Default: ``https://galaxyproject.org/api``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``auth_config_file``
~~~~~~~~~~~~~~~~~~~~

:Description:
    XML config file that allows the use of different authentication
    providers (e.g. LDAP) instead or in addition to local
    authentication (.sample is used if default does not exist).
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``auth_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``api_allow_run_as``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Optional list of email addresses of API users who can make calls
    on behalf of other users.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``bootstrap_admin_api_key``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    API key that allows performing some admin actions without actually
    having a real admin user in the database and config. Only set this
    if you need to bootstrap Galaxy, in particular to create a real
    admin user account via API. You should probably not set this on a
    production server.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``organization_name``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    The name of the organization that operates this Galaxy instance.
    Serves as the default for the GA4GH service organization name and
    can be exposed through Galaxy markdown for reports and such. For
    instance, "Not Evil Corporation".
    For GA4GH APIs, this is exposed via the service-info endpoint for
    the Galaxy DRS API. If unset, one will be generated using
    ga4gh_service_id (but only in the context of GA4GH APIs).
    For more information on GA4GH service definitions - check out
    https://github.com/ga4gh-discovery/ga4gh-service-registry and
    https://editor.swagger.io/?url=https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-registry/develop/service-registry.yaml
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``organization_url``
~~~~~~~~~~~~~~~~~~~~

:Description:
    The URL of the organization that operates this Galaxy instance.
    Serves as the default for the GA4GH service organization name and
    can be exposed through Galaxy markdown for reports and such. For
    instance, "notevilcorp.com".
    For GA4GH APIs, this is exposed via the service-info endpoint.
    For more information on GA4GH service definitions - check out
    https://github.com/ga4gh-discovery/ga4gh-service-registry and
    https://editor.swagger.io/?url=https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-registry/develop/service-registry.yaml
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``ga4gh_service_id``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Service ID for GA4GH services (exposed via the service-info
    endpoint for the Galaxy DRS API). If unset, one will be generated
    using the URL the target API requests are made against.
    For more information on GA4GH service definitions - check out
    https://github.com/ga4gh-discovery/ga4gh-service-registry and
    https://editor.swagger.io/?url=https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-registry/develop/service-registry.yaml
    This value should likely reflect your service's URL. For instance
    for usegalaxy.org this value should be org.usegalaxy. Particular
    Galaxy implementations will treat this value as a prefix and
    append the service type to this ID. For instance for the DRS
    service "id" (available via the DRS API) for the above
    configuration value would be org.usegalaxy.drs.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``ga4gh_service_environment``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Service environment (exposed via the service-info endpoint for the
    Galaxy DRS API) for implemented GA4GH services.
    Suggested values are prod, test, dev, staging.
    For more information on GA4GH service definitions - check out
    https://github.com/ga4gh-discovery/ga4gh-service-registry and
    https://editor.swagger.io/?url=https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-registry/develop/service-registry.yaml
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``enable_tool_tags``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable tool tags (associating tools with tags).  This has its own
    option since its implementation has a few performance implications
    on startup for large servers.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_unique_workflow_defaults``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable a feature when running workflows.  When enabled, default
    datasets are selected for "Set at Runtime" inputs from the history
    such that the same input will not be selected twice, unless there
    are more inputs than compatible datasets in the history. When
    false, the most recently added compatible item in the history will
    be used for each "Set at Runtime" input, independent of others in
    the workflow.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``simplified_workflow_run_ui``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If set to 'off' by default, always use the traditional workflow
    form that renders all steps in the GUI and serializes the tool
    state of all steps during invocation. Set to 'prefer' to default
    to a simplified workflow UI that only renders the inputs if
    possible (the workflow must have no disconnected runtime inputs
    and not replacement parameters within tool steps). In the future
    'force' may be added an option for Galaskio-style servers that
    should only render simplified workflows.
:Default: ``prefer``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``simplified_workflow_run_ui_target_history``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When the simplified workflow run form is rendered, should the
    invocation outputs be sent to the 'current' history or a 'new'
    history. If the user should be presented and option between these
    - set this to 'prefer_current' or 'prefer_new' to display a
    runtime setting with the corresponding default. The default is to
    provide the user this option and default it to the current history
    (the traditional behavior of Galaxy for years) - this corresponds
    to the setting 'prefer_current'.
:Default: ``prefer_current``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``simplified_workflow_run_ui_job_cache``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When the simplified workflow run form is rendered, should the
    invocation use job caching. This isn't a boolean so an option for
    'show-selection' can be added later.
:Default: ``off``
:Type: str


~~~~~~~~~~~~~~~~~~~
``ftp_upload_site``
~~~~~~~~~~~~~~~~~~~

:Description:
    Enable Galaxy's "Upload via FTP" interface.  You'll need to
    install and configure an FTP server (we've used ProFTPd since it
    can use Galaxy's database for authentication) and set the
    following two options. This will be provided to users in the help
    text as 'log in to the FTP server at '. Thus, it should be the
    hostname of your FTP server.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~
``ftp_upload_dir``
~~~~~~~~~~~~~~~~~~

:Description:
    This should point to a directory containing subdirectories
    matching users' identifier (defaults to e-mail), where Galaxy will
    look for files.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``ftp_upload_dir_identifier``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    User attribute to use as subdirectory in calculating default
    ftp_upload_dir pattern. By default this will be email so a user's
    FTP upload directory will be ${ftp_upload_dir}/${user.email}. Can
    set this to other attributes such as id or username though.
:Default: ``email``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``ftp_upload_dir_template``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Python string template used to determine an FTP upload directory
    for a particular user.
    Defaults to '${ftp_upload_dir}/${ftp_upload_dir_identifier}'.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``ftp_upload_purge``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Set to false to prevent Galaxy from deleting uploaded FTP files as
    it imports them.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~
``enable_quotas``
~~~~~~~~~~~~~~~~~

:Description:
    Enable enforcement of quotas.  Quotas can be set from the Admin
    interface.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~
``expose_dataset_path``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This option allows users to see the full path of datasets via the
    "View Details" option in the history. This option also exposes the
    command line to non-administrative users. Administrators can
    always see dataset paths.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_tool_source_display``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This option allows users to view the tool wrapper source code.
    This is safe to enable if you have not hardcoded any secrets in
    any of the tool wrappers installed on this Galaxy server. If you
    have only installed tool wrappers from  public tool sheds and
    tools shipped with Galaxy there you can enable this option.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``job_metrics_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    YAML or XML config file that contains the job metric collection
    configuration.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``job_metrics_conf.xml``
:Type: str


~~~~~~~~~~~~~~~
``job_metrics``
~~~~~~~~~~~~~~~

:Description:
    Rather than specifying a job_metrics_config_file, the definition
    of the metrics to enable can be embedded into Galaxy's config with
    this option. This has no effect if a job_metrics_config_file is
    used.
    The syntax, available instrumenters, and documentation of their
    options is explained in detail in the documentation:
    https://docs.galaxyproject.org/en/master/admin/job_metrics.html
    By default, the core plugin is enabled. Setting this option to
    false or an empty list disables metrics entirely.
:Default: ``None``
:Type: seq


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``expose_potentially_sensitive_job_metrics``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This option allows users to see the job metrics (except for
    environment variables).
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_legacy_sample_tracking_api``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable the API for sample tracking
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_data_manager_user_view``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Allow non-admin users to view available Data Manager options.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``data_manager_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    File where Data Managers are configured (.sample used if default
    does not exist).
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``data_manager_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``shed_data_manager_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    File where Tool Shed based Data Managers are configured. This file
    will be created automatically upon data manager installation.
    The value of this option will be resolved with respect to
    <managed_config_dir>.
:Default: ``shed_data_manager_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``galaxy_data_manager_data_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Directory to store Data Manager based tool-data. Defaults to the
    value of the <tool_data_path> option.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~
``job_config_file``
~~~~~~~~~~~~~~~~~~~

:Description:
    To increase performance of job execution and the web interface,
    you can separate Galaxy into multiple processes.  There are more
    than one way to do this, and they are explained in detail in the
    documentation:
    https://docs.galaxyproject.org/en/master/admin/scaling.html
    By default, Galaxy manages and executes jobs from within a single
    process and notifies itself of new jobs via in-memory queues.
    Jobs are run locally on the system on which Galaxy is started.
    Advanced job running capabilities can be configured through the
    job configuration file or the <job_config> option.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``job_conf.yml``
:Type: str


~~~~~~~~~~~~~~
``job_config``
~~~~~~~~~~~~~~

:Description:
    Description of job running configuration, can be embedded into
    Galaxy configuration or loaded from an additional file with the
    job_config_file option.
:Default: ``None``
:Type: map


~~~~~~~~~~~~~~~~~~~~~~~~
``dependency_resolvers``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Rather than specifying a dependency_resolvers_config_file, the
    definition of the resolvers to enable can be embedded into
    Galaxy's config with this option. This has no effect if a
    dependency_resolvers_config_file is used.
    The syntax, available resolvers, and documentation of their
    options is explained in detail in the documentation:
    https://docs.galaxyproject.org/en/master/admin/dependency_resolvers.html
:Default: ``None``
:Type: seq


~~~~~~~~~~~~~~~~~~~~~~~~~
``dependency_resolution``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Alternative representation of various dependency resolution
    parameters. Takes the dictified version of a DependencyManager
    object - so this is ideal for automating the configuration of
    dependency resolution from one application that uses a
    DependencyManager to another.
:Default: ``None``
:Type: map


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``default_job_resubmission_condition``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When jobs fail due to job runner problems, Galaxy can be
    configured to retry these or reroute the jobs to new destinations.
    Very fine control of this is available with resubmit declarations
    in the job config. For simple deployments of Galaxy though, the
    following attribute can define resubmission conditions for all job
    destinations. If any job destination defines even one resubmission
    condition explicitly in the job config - the condition described
    by this option will not apply to that destination. For instance,
    the condition: 'attempt < 3 and unknown_error and (time_running <
    300 or time_since_queued < 300)' would retry up to two times jobs
    that didn't fail due to detected memory or walltime limits but did
    fail quickly (either while queueing or running). The commented out
    default below results in no default job resubmission condition,
    failing jobs are just failed outright.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~
``track_jobs_in_database``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This option is deprecated, use the `mem-self` handler assignment
    option in the job configuration instead.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~
``use_tasked_jobs``
~~~~~~~~~~~~~~~~~~~

:Description:
    This enables splitting of jobs into tasks, if specified by the
    particular tool config. This is a new feature and not recommended
    for production servers yet.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``local_task_queue_workers``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This enables splitting of jobs into tasks, if specified by the
    particular tool config. This is a new feature and not recommended
    for production servers yet.
:Default: ``2``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``job_handler_monitor_sleep``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Each Galaxy job handler process runs one thread responsible for
    discovering jobs and dispatching them to runners. This thread
    operates in a loop and sleeps for the given number of seconds at
    the end of each iteration. This can be decreased if extremely high
    job throughput is necessary, but doing so can increase CPU usage
    of handler processes. Float values are allowed.
:Default: ``1.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``job_runner_monitor_sleep``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Each Galaxy job handler process runs one thread per job runner
    plugin responsible for checking the state of queued and running
    jobs.  This thread operates in a loop and sleeps for the given
    number of seconds at the end of each iteration. This can be
    decreased if extremely high job throughput is necessary, but doing
    so can increase CPU usage of handler processes. Float values are
    allowed.
:Default: ``1.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~~~~~
``workflow_monitor_sleep``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Each Galaxy workflow handler process runs one thread responsible
    for checking the state of active workflow invocations.  This
    thread operates in a loop and sleeps for the given number of
    seconds at the end of each iteration. This can be decreased if
    extremely high job throughput is necessary, but doing so can
    increase CPU usage of handler processes. Float values are allowed.
:Default: ``1.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~
``metadata_strategy``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Determines how metadata will be set. Valid values are `directory`,
    `extended`, `directory_celery` and `extended_celery`. In extended
    mode jobs will decide if a tool run failed, the object stores
    configuration is serialized and made available to the job and is
    used for writing output datasets to the object store as part of
    the job and dynamic output discovery (e.g. discovered datasets
    <discover_datasets>, unpopulated collections, etc) happens as part
    of the job. In `directory_celery` and `extended_celery` metadata
    will be set within a celery task.
:Default: ``directory``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``retry_metadata_internally``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Although it is fairly reliable, setting metadata can occasionally
    fail.  In these instances, you can choose to retry setting it
    internally or leave it in a failed state (since retrying
    internally may cause the Galaxy process to be unresponsive).  If
    this option is set to false, the user will be given the option to
    retry externally, or set metadata manually (when possible).
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``max_metadata_value_size``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Very large metadata values can cause Galaxy crashes.  This will
    allow limiting the maximum metadata key size (in bytes used in
    memory, not the end result database value size) Galaxy will
    attempt to save with a dataset.  Use 0 to disable this feature.
    The default is 5MB, but as low as 1MB seems to be a reasonable
    size.
:Default: ``5242880``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``outputs_to_working_directory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This option will override tool output paths to write outputs to
    the job working directory (instead of to the file_path) and the
    job manager will move the outputs to their proper place in the
    dataset directory on the Galaxy server after the job completes.
    This is necessary (for example) if jobs run on a cluster and
    datasets can not be created by the user running the jobs (e.g. if
    the filesystem is mounted read-only or the jobs are run by a
    different user than the galaxy user).
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``retry_job_output_collection``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If your network filesystem's caching prevents the Galaxy server
    from seeing the job's stdout and stderr files when it completes,
    you can retry reading these files.  The job runner will retry the
    number of times specified below, waiting 1 second between tries.
    For NFS, you may want to try the -noac mount option (Linux) or
    -actimeo=0 (Solaris).
:Default: ``0``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_evaluation_strategy``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Determines which process will evaluate the tool command line. If
    set to "local" the tool command line, configuration files and
    other dynamic values will be templated in the job handler process.
    If set to ``remote`` the tool command line will be built as part
    of the submitted job. Note that ``remote`` is a beta setting that
    will be useful for materializing deferred datasets as part of the
    submitted job. Note also that you have to set
    ``metadata_strategy`` to ``extended`` if you set this option to
    ``remote``.
:Default: ``local``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``preserve_python_environment``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    In the past Galaxy would preserve its Python environment when
    running jobs ( and still does for internal tools packaged with
    Galaxy). This behavior exposes Galaxy internals to tools and could
    result in problems when activating Python environments for tools
    (such as with Conda packaging). The default legacy_only will
    restrict this behavior to tools identified by the Galaxy team as
    requiring this environment. Set this to "always" to restore the
    previous behavior (and potentially break Conda dependency
    resolution for many tools). Set this to legacy_and_local to
    preserve the environment for legacy tools and locally managed
    tools (this might be useful for instance if you are installing
    software into Galaxy's virtualenv for tool development).
:Default: ``legacy_only``
:Type: str


~~~~~~~~~~~~~~~
``cleanup_job``
~~~~~~~~~~~~~~~

:Description:
    Clean up various bits of jobs left on the filesystem after
    completion.  These bits include the job working directory,
    external metadata temporary files, and DRM stdout and stderr files
    (if using a DRM).  Possible values are: always, onsuccess, never
:Default: ``always``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``drmaa_external_runjob_script``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When running DRMAA jobs as the Galaxy user
    (https://docs.galaxyproject.org/en/master/admin/cluster.html#submitting-jobs-as-the-real-user)
    this script is used to run the job script Galaxy generates for a
    tool execution.
    Example value 'sudo -E scripts/drmaa_external_runner.py
    --assign_all_groups'
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``drmaa_external_killjob_script``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When running DRMAA jobs as the Galaxy user
    (https://docs.galaxyproject.org/en/master/admin/cluster.html#submitting-jobs-as-the-real-user)
    this script is used to kill such jobs by Galaxy (e.g. if the user
    cancels the job).
    Example value 'sudo -E scripts/drmaa_external_killer.py'
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``external_chown_script``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When running DRMAA jobs as the Galaxy user
    (https://docs.galaxyproject.org/en/master/admin/cluster.html#submitting-jobs-as-the-real-user)
    this script is used transfer permissions back and forth between
    the Galaxy user and the user that is running the job.
    Example value 'sudo -E scripts/external_chown_script.py'
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``real_system_username``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When running DRMAA jobs as the Galaxy user
    (https://docs.galaxyproject.org/en/master/admin/cluster.html#submitting-jobs-as-the-real-user)
    Galaxy can extract the user name from the email address (actually
    the local-part before the @) or the username which are both stored
    in the Galaxy data base. The latter option is particularly useful
    for installations that get the authentication from LDAP. Also,
    Galaxy can accept the name of a common system user (eg.
    galaxy_worker) who can run every job being submitted. This user
    should not be the same user running the galaxy system. Possible
    values are user_email (default), username or <common_system_user>
:Default: ``user_email``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~
``environment_setup_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    File to source to set up the environment when running jobs.  By
    default, the environment in which the Galaxy server starts is used
    when running jobs locally, and the environment set up per the
    DRM's submission method and policy is used when running jobs on a
    cluster (try testing with `qsub` on the command line).
    environment_setup_file can be set to the path of a file on the
    cluster that should be sourced by the user to set up the
    environment prior to running tools.  This can be especially useful
    for running jobs as the actual user, to remove the need to
    configure each user's environment individually.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_beta_markdown_export``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable export of Galaxy Markdown documents (pages and workflow
    reports) to PDF. Requires manual installation and setup of
    weasyprint (latest version available for Python 2.7 is 0.42).
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~
``markdown_export_css``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    CSS file to apply to all Markdown exports to PDF - currently used
    by WeasyPrint during rendering an HTML export of the document to
    PDF.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``markdown_export.css``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``markdown_export_css_pages``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    CSS file to apply to "Galaxy Page" exports to PDF. Generally
    prefer markdown_export_css, but this is here for deployments that
    would like to tailor different kinds of exports.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``markdown_export_pages.css``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``markdown_export_css_invocation_reports``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    CSS file to apply to invocation report exports to PDF. Generally
    prefer markdown_export_css, but this is here for deployments that
    would like to tailor different kinds of exports.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``markdown_export_invocation_reports.css``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``markdown_export_prologue``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Prologue Markdown/HTML to apply to markdown exports to PDF.
    Allowing branded headers.
:Default: ``""``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``markdown_export_epilogue``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Prologue Markdown/HTML to apply to markdown exports to PDF.
    Allowing branded footers.
:Default: ``""``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``markdown_export_prologue_pages``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Alternative to markdown_export_prologue that applies just to page
    exports.
:Default: ``""``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``markdown_export_prologue_invocation_reports``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Alternative to markdown_export_prologue that applies just to
    invocation report exports.
:Default: ``""``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``markdown_export_epilogue_pages``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Alternative to markdown_export_epilogue that applies just to page
    exports.
:Default: ``""``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``markdown_export_epilogue_invocation_reports``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Alternative to markdown_export_epilogue that applies just to
    invocation report exports.
:Default: ``""``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``job_resource_params_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Optional file containing job resource data entry fields
    definition. These fields will be presented to users in the tool
    forms and allow them to overwrite default job resources such as
    number of processors, memory and walltime.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``job_resource_params_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``workflow_resource_params_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Similar to the above parameter, workflows can describe parameters
    used to influence scheduling of jobs within the workflow. This
    requires both a description of the fields available (which
    defaults to the definitions in job_resource_params_file if not
    set).
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``workflow_resource_params_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``workflow_resource_params_mapper``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    This parameter describes how to map users and workflows to a set
    of workflow resource parameter to present (typically input IDs
    from workflow_resource_params_file). If this this is a function
    reference it will be passed various inputs (workflow model object
    and user) and it should produce a list of input IDs. If it is a
    path it is expected to be an XML or YAML file describing how to
    map group names to parameter descriptions (additional types of
    mappings via these files could be implemented but haven't yet -
    for instance using workflow tags to do the mapping).
    Sample default path
    'config/workflow_resource_mapper_conf.yml.sample'
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``workflow_schedulers_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Optional configuration file similar to `job_config_file` to
    specify which Galaxy processes should schedule workflows.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``workflow_schedulers_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``workflow_scheduling_separate_materialization_iteration``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Workflows launched with URI/URL inputs that are not marked as
    'deferred' are "materialized" (or undeferred) by the workflow
    scheduler. This might be a lengthy process. Setting this to 'True'
    will place the invocation back in the queue after materialization
    before scheduling the workflow so it is less likely to starve
    other workflow scheduling. Ideally, Galaxy would allow more fine
    grain control of handlers but until then, this provides a way to
    tip the balance between "doing more work" and "being more fair".
    The default here is pretty arbitrary - it has been to False to
    optimize Galaxy for automated, single user applications where
    "fairness" is mostly irrelevant.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~
``cache_user_job_count``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If using job concurrency limits (configured in job_config_file),
    several extra database queries must be performed to determine the
    number of jobs a user has dispatched to a given destination.  By
    default, these queries will happen for every job that is waiting
    to run, but if cache_user_job_count is set to true, it will only
    happen once per iteration of the handler queue. Although better
    for performance due to reduced queries, the trade-off is a greater
    possibility that jobs will be dispatched past the configured
    limits if running many handlers.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~
``toolbox_auto_sort``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    If true, the toolbox will be sorted by tool id when the toolbox is
    loaded. This is useful for ensuring that tools are always
    displayed in the same order in the UI.  If false, the order of
    tools in the toolbox will be preserved as they are loaded from the
    tool config files.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~
``tool_filters``
~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters
    (https://galaxyproject.org/user-defined-toolbox-filters/) that
    admins may use to restrict the tools to display.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``tool_label_filters``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters
    (https://galaxyproject.org/user-defined-toolbox-filters/) that
    admins may use to restrict the tool labels to display.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``tool_section_filters``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters
    (https://galaxyproject.org/user-defined-toolbox-filters/) that
    admins may use to restrict the tool sections to display.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``user_tool_filters``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters
    (https://galaxyproject.org/user-defined-toolbox-filters/) that
    users may use to restrict the tools to display.
:Default: ``examples:restrict_upload_to_admins, examples:restrict_encode``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_tool_section_filters``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters
    (https://galaxyproject.org/user-defined-toolbox-filters/) that
    users may use to restrict the tool sections to display.
:Default: ``examples:restrict_text``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_tool_label_filters``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters
    (https://galaxyproject.org/user-defined-toolbox-filters/) that
    users may use to restrict the tool labels to display.
:Default: ``examples:restrict_upload_to_admins, examples:restrict_encode``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``toolbox_filter_base_modules``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The base module(s) that are searched for modules for toolbox
    filtering
    (https://galaxyproject.org/user-defined-toolbox-filters/)
    functions.
:Default: ``galaxy.tools.filters,galaxy.tools.toolbox.filters,galaxy.tool_util.toolbox.filters``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``amqp_internal_connection``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy uses AMQP internally for communicating between processes.
    For example, when reloading the toolbox or locking job execution,
    the process that handled that particular request will tell all
    others to also reload, lock jobs, etc. For connection examples,
    see
    https://docs.celeryq.dev/projects/kombu/en/stable/userguide/connections.html
    Without specifying anything here, galaxy will first attempt to use
    your specified database_connection above.  If that's not specified
    either, Galaxy will automatically create and use a separate sqlite
    database located in your <galaxy>/database folder (indicated in
    the commented out line below).
:Default: ``sqlalchemy+sqlite:///./database/control.sqlite?isolation_level=IMMEDIATE``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``enable_celery_tasks``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Offload long-running tasks to a Celery task queue. Activate this
    only if you have setup a Celery worker for Galaxy and you have
    configured the `celery_conf` option below. Specifically, you need
    to set the `result_backend` option in the `celery_conf` option to
    a valid Celery result backend URL. By default, Galaxy uses an
    SQLite database at '<data_dir>/results.sqlite' for storing task
    results. For details, see
    https://docs.galaxyproject.org/en/master/admin/production.html#use-celery-for-asynchronous-tasks
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~
``celery_conf``
~~~~~~~~~~~~~~~

:Description:
    Configuration options passed to Celery.
    To refer to a task by name, use the template `galaxy.foo` where
    `foo` is the function name of the task defined in the
    galaxy.celery.tasks module.
    The `broker_url` option, if unset or null, defaults to the value
    of `amqp_internal_connection`. The `result_backend` option, if
    unset or null, defaults to an SQLite database at
    '<data_dir>/results.sqlite' for storing task results. Please use a
    more robust backend (e.g. Redis) for production setups.
    The galaxy.fetch_data task can be disabled by setting its route to
    "disabled": `galaxy.fetch_data: disabled`. (Other tasks cannot be
    disabled on a per-task basis at this time.)
    For details, see Celery documentation at
    https://docs.celeryq.dev/en/stable/userguide/configuration.html.
:Default: ``{'broker_url': None, 'result_backend': None, 'task_routes': {'galaxy.fetch_data': 'galaxy.external', 'galaxy.set_job_metadata': 'galaxy.external'}}``
:Type: any


~~~~~~~~~~~~~~~~~~~~~~~~~~
``celery_user_rate_limit``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If set to a non-0 value, upper limit on number of tasks that can
    be executed per user per second.
:Default: ``0.0``
:Type: float


~~~~~~~~~~~~~~
``use_pbkdf2``
~~~~~~~~~~~~~~

:Description:
    Allow disabling pbkdf2 hashing of passwords for legacy situations.
    This should normally be left enabled unless there is a specific
    reason to disable it.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~
``cookie_domain``
~~~~~~~~~~~~~~~~~

:Description:
    Tell Galaxy that multiple domains sharing the same root are
    associated to this instance and wants to share the same session
    cookie. This allow a user to stay logged in when passing from one
    subdomain to the other. This root domain will be written in the
    unique session cookie shared by all subdomains.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``select_type_workflow_threshold``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Due to performance considerations (select2 fields are pretty
    'expensive' in terms of memory usage) Galaxy uses the regular
    select fields for non-dataset selectors in the workflow run form.
    use 0 in order to always use select2 fields, use -1 (default) in
    order to always use the regular select fields, use any other
    positive number as threshold (above threshold: regular select
    fields will be used)
:Default: ``-1``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_tool_recommendations``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Allow the display of tool recommendations in workflow editor and
    after tool execution. If it is enabled and set to true, please
    enable 'tool_recommendation_model_path' as well
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_recommendation_model_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set remote path of the trained model (HDF5 file) for tool
    recommendation.
:Default: ``https://github.com/galaxyproject/galaxy-test-data/raw/master/tool_recommendation_model_v_0.2.hdf5``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``topk_recommendations``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set the number of predictions/recommendations to be made by the
    model
:Default: ``20``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``admin_tool_recommendations_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set path to the additional tool preferences from Galaxy admins. It
    has two blocks. One for listing deprecated tools which will be
    removed from the recommendations and another is for adding
    additional tools to be recommended along side those from the deep
    learning model.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``tool_recommendations_overwrite.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``overwrite_model_recommendations``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Overwrite or append to the tool recommendations by the deep
    learning model. When set to true, all the recommendations by the
    deep learning model are overwritten by the recommendations set by
    an admin in a config file 'tool_recommendations_overwrite.yml'.
    When set to false, the recommended tools by admins and predicted
    by the deep learning model are shown.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~
``error_report_file``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Path to error reports configuration file.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``error_report.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_destinations_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Path to dynamic tool destinations configuration file.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``tool_destinations.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``welcome_directory``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Location of New User Welcome data, a single directory containing
    the images and JSON of Topics/Subtopics/Slides as export. This
    location is relative to galaxy/static
:Default: ``plugins/welcome_page/new_user/static/topics/``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``vault_config_file``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Vault config file.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``vault_conf.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``display_builtin_converters``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Display built-in converters in the tool panel.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~
``themes_config_file``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Optional file containing one or more themes for galaxy. If several
    themes are defined, users can choose their preferred theme in the
    client.
    The value of this option will be resolved with respect to
    <config_dir>.
:Default: ``themes_conf.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_beacon_integration``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enables user preferences and api endpoint for the beacon
    integration.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_training_recommendations``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Displays a link to training material, if any includes the current
    tool. When activated the following options also need to be set:
    tool_training_recommendations_link,
    tool_training_recommendations_api_url
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_training_recommendations_link``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Template URL to display all tutorials containing current tool.
    Valid template inputs are:   {repository_owner}   {name}
    {tool_id}   {training_tool_identifier}   {version}
:Default: ``https://training.galaxyproject.org/training-material/by-tool/{training_tool_identifier}.html``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_training_recommendations_api_url``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    URL to API describing tutorials containing specific tools. When
    CORS is used, make sure to add this host.
:Default: ``https://training.galaxyproject.org/training-material/api/top-tools.json``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``citations_export_message_html``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Message to display on the export citations tool page
:Default: ``When writing up your analysis, remember to include all references that should be cited in order to completely describe your work. Also, please remember to <a href="https://galaxyproject.org/citing-galaxy">cite Galaxy</a>.``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_notification_system``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enables the Notification System integrated in Galaxy.
    Users can receive automatic notifications when a certain resource
    is shared with them or when some long running operations have
    finished, etc.
    The system allows notification scheduling and expiration, and
    users can opt-out of specific notification categories or channels.
    Admins can schedule and broadcast notifications that will be
    visible to all users, including special server-wide announcements
    such as scheduled maintenance, high load warnings, and event
    announcements, to name a few examples.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``expired_notifications_cleanup_interval``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The interval in seconds between attempts to delete all expired
    notifications from the database (every 24 hours by default). Runs
    in a Celery task.
:Default: ``86400``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dispatch_notifications_interval``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The interval in seconds between attempts to dispatch notifications
    to users (every 10 minutes by default). Runs in a Celery task.
:Default: ``600``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~
``help_forum_api_url``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The URL pointing to the Galaxy Help Forum API base URL. The API
    must be compatible with Discourse API
    (https://docs.discourse.org/).
:Default: ``https://help.galaxyproject.org/``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_help_forum_tool_panel_integration``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable the integration of the Galaxy Help Forum in the tool panel.
    This requires the help_forum_api_url to be set.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~
``file_source_temp_dir``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Directory to store temporary files for file sources. This defaults
    to new_file_path if not set.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``file_source_webdav_use_temp_files``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Default value for use_temp_files for webdav plugins that don't
    explicitly declare this.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``file_source_listings_expiry_time``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Number of seconds before file source content listings are
    refreshed. Shorter times will result in more queries while
    browsing a file sources. Longer times will result in fewer
    requests to file sources but outdated contents might be displayed
    to the user. Currently only affects s3fs file sources.
:Default: ``60``
:Type: int




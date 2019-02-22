~~~~~~~~~~~~~~~
``cookie_path``
~~~~~~~~~~~~~~~

:Description:
    When running multiple Galaxy instances under separate URL prefixes
    on a single hostname, you will want to set this to the same path
    as the prefix set in the uWSGI "mount" configuration option above.
    This value becomes the "path" attribute set in the cookie so the
    cookies from one instance will not clobber those from another.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``database_connection``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    By default, Galaxy uses a SQLite database at
    'database/universe.sqlite'.  You may use a SQLAlchemy connection
    string to specify an external database instead.  This string takes
    many options which are explained in detail in the config file
    documentation.
:Default: ``sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE``
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
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``slow_query_log_threshold``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Slow query logging.  Queries slower than the threshold indicated
    below will be logged to debug.  A value of '0' is disabled.  For
    example, you would set this to .005 to log all queries taking
    longer than 5 milliseconds.
:Default: ``0``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_per_request_sql_debugging``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable's a per request sql debugging option. If this is set to
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
    options listed above but prefixed with install_ are also
    available).
:Default: ``sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE``
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


~~~~~~~~~~~~~
``file_path``
~~~~~~~~~~~~~

:Description:
    Where dataset files are stored. It must accessible at the same
    path on any cluster nodes that will run Galaxy jobs, unless using
    Pulsar.
:Default: ``database/files``
:Type: str


~~~~~~~~~~~~~~~~~
``new_file_path``
~~~~~~~~~~~~~~~~~

:Description:
    Where temporary files are stored. It must accessible at the same
    path on any cluster nodes that will run Galaxy jobs, unless using
    Pulsar.
:Default: ``database/tmp``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``tool_config_file``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Tool config files, defines what tools are available in Galaxy.
    Tools can be locally developed or installed from Galaxy tool
    sheds. (config/tool_conf.xml.sample will be used if left unset and
    config/tool_conf.xml does not exist).
:Default: ``config/tool_conf.xml,config/shed_tool_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``check_migrate_tools``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable / disable checking if any tools defined in the above non-
    shed tool_config_files (i.e., tool_conf.xml) have been migrated
    from the Galaxy code distribution to the Tool Shed. This
    functionality is largely untested in modern Galaxy releases and
    has serious issues such as #7273 and the possibility of slowing
    down Galaxy startup, so the default and recommended value is
    False.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~
``migrated_tools_config``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Tool config maintained by tool migration scripts.  If you use the
    migration scripts to install tools that have been migrated to the
    tool shed upon a new release, they will be added to this tool
    config file.
:Default: ``config/migrated_tools_conf.xml``
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
    Path to the directory in which tool dependencies are placed.  This
    is used by the Tool Shed to install dependencies and can also be
    used by administrators to manually install or link to
    dependencies.  For details, see:
    https://galaxyproject.org/admin/config/tool-dependencies Set the
    string to None to explicitly disable tool dependency handling. If
    this option is set to none or an invalid path, installing tools
    with dependencies from the Tool Shed will fail.
:Default: ``database/dependencies``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dependency_resolvers_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The dependency resolvers config file specifies an ordering and
    options for how Galaxy resolves tool dependencies (requirement
    tags in Tool XML). The default ordering is to the use the Tool
    Shed for tools installed that way, use local Galaxy packages, and
    then use Conda if available. See https://github.com/galaxyproject/
    galaxy/blob/dev/doc/source/admin/dependency_resolvers.rst for more
    information on these options.
:Default: ``config/dependency_resolvers_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~
``conda_prefix``
~~~~~~~~~~~~~~~~

:Description:
    conda_prefix is the location on the filesystem where Conda
    packages and environments are installed IMPORTANT: Due to a
    current limitation in conda, the total length of the conda_prefix
    and the job_working_directory path should be less than 50
    characters!
:Default: ``<tool_dependency_dir>/_conda``
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
    conda channels to enable by default (https://conda.io/docs/user-
    guide/tasks/manage-channels.html)
:Default: ``iuc,conda-forge,bioconda,defaults``
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
    Set to True to instruct Galaxy to look for and install missing
    tool dependencies before each job runs.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~
``conda_auto_init``
~~~~~~~~~~~~~~~~~~~

:Description:
    Set to True to instruct Galaxy to install Conda from the web
    automatically if it cannot find a local copy and conda_exec is not
    configured.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``conda_copy_dependencies``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    You must set this to True if conda_prefix and
    job_working_directory are not on the same volume, or some conda
    dependencies will fail to execute at job runtime. Conda will copy
    packages content instead of creating hardlinks or symlinks. This
    will prevent problems with some specific packages (perl, R), at
    the cost of extra disk space usage and extra time spent copying
    packages.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``use_cached_dependency_manager``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Certain dependency resolvers (namely Conda) take a considerable
    amount of time to build an isolated job environment in the
    job_working_directory if the job working directory is on a network
    share.  Set the following option to True to cache the dependencies
    in a folder. This option is beta and should only be used if you
    experience long waiting times before a job is actually submitted
    to your cluster.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_dependency_cache_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    By default the tool_dependency_cache_dir is the _cache directory
    of the tool dependency directory
:Default: ``<tool_dependency_dir>/_cache``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``precache_dependencies``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    By default, when using a cached dependency manager, the
    dependencies are cached when installing new tools and when using
    tools for the first time. Set this to False if you prefer
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
:Default: ``config/tool_sheds_conf.xml``
:Type: str


~~~~~~~~~~~~~~~
``watch_tools``
~~~~~~~~~~~~~~~

:Description:
    Set to True to enable monitoring of tools and tool directories
    listed in any tool config file specified in tool_config_file
    option. If changes are found, tools are automatically reloaded.
    Watchdog ( https://pypi.org/project/watchdog/ ) must be installed
    and available to Galaxy to use this option. Other options include
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
    Set to True to enable monitoring of dynamic job rules. If changes
    are found, rules are automatically reloaded. Takes the same values
    as the 'watch_tools' option.
:Default: ``false``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``legacy_eager_objectstore_initialization``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    As of 18.09, Galaxy defaults to setting up the object store
    configuration for output datasets during the job queue step in job
    handlers. This should generally provide for more robust job
    submission, more configurability, and a better user experience but
    may in some cases slightly slow down the job handler job setup
    process. On the off chance that an admin would like to or need to
    optimize job handlers at the expense of user experience and web
    handling this option will remain for some time by setting this
    option to true. This behavior however should be considered
    deprecated and this option will likely be removed in future
    versions of Galaxy. For more information see
    https://github.com/galaxyproject/galaxy/issues/6513.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_beta_mulled_containers``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable Galaxy to fetch Docker containers registered with quay.io
    generated from tool requirements resolved through conda. These
    containers (when available) have been generated using mulled -
    https://github.com/mulled . These containers are highly beta and
    availability will vary by tool. This option will additionally only
    be used for job destinations with Docker enabled.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``containers_resolvers_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Container resolvers configuration (beta). Setup a file describing
    container resolvers to use when discovering containers for Galaxy.
    If this is set to None, the default containers loaded is
    determined by enable_beta_mulled_containers.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~
``involucro_path``
~~~~~~~~~~~~~~~~~~

:Description:
    involucro is a tool used to build Docker or Singularity containers
    for tools from Conda dependencies referenced in tools as
    `requirement`s. The following path is the location of involucro on
    the Galaxy host. This is ignored if the relevant container
    resolver isn't enabled, and will install on demand unless
    involucro_auto_init is set to False.
:Default: ``database/dependencies/involucro``
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


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``manage_dependency_relationships``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable use of an in-memory registry with bi-directional
    relationships between repositories (i.e., in addition to lists of
    dependencies for a repository, keep an in-memory registry of
    dependent items for each repository.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_data_table_config_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    XML config file that contains data table entries for the
    ToolDataTableManager.  This file is manually # maintained by the
    Galaxy administrator (.sample used if default does not exist).
:Default: ``config/tool_data_table_conf.xml``
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
:Default: ``config/shed_tool_data_table_conf.xml``
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
    installed from a ToolShed. Defaults to tool_data_path.
:Default: ``tool-data``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``watch_tool_data_dir``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set to True to enable monitoring of the tool_data and
    shed_tool_data_path directories. If changes in tool data table
    files are found, the tool data tables for that data manager are
    automatically reloaded. Watchdog (
    https://pypi.org/project/watchdog/ ) must be installed and
    available to Galaxy to use this option. Other options include
    'auto' which will attempt to use the watchdog library if it is
    available but won't fail to load Galaxy if it is not and 'polling'
    which will use a less efficient monitoring scheme that may work in
    wider range of scenarios than the watchdog default.
:Default: ``false``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``builds_file_path``
~~~~~~~~~~~~~~~~~~~~

:Description:
    File containing old-style genome builds
:Default: ``tool-data/shared/ucsc/builds.txt``
:Type: str


~~~~~~~~~~~~~~~~~
``len_file_path``
~~~~~~~~~~~~~~~~~

:Description:
    Directory where chrom len files are kept, currently mainly used by
    trackster
:Default: ``tool-data/shared/ucsc/chrom``
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
:Default: ``config/datatypes_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``sniff_compressed_dynamic_datatypes_default``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable sniffing of compressed datatypes. This can be
    configured/overridden on a per-datatype basis in the
    datatypes_conf.xml file. With this option set to False the
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
    comma separated list. Defaults to "config/plugins/visualizations".
:Default: ``config/plugins/visualizations``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``interactive_environment_plugins_directory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Interactive environment plugins root directory: where to look for
    interactive environment plugins.  By default none will be loaded.
    Set to config/plugins/interactive_environments to load Galaxy's
    stock plugins. These will require Docker to be configured and have
    security considerations, so proceed with caution. The path is
    relative to the Galaxy root dir.  To use an absolute path begin
    the path with '/'.  This is a comma separated list.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``interactive_environment_swarm_mode``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    To run interactive environment containers in Docker Swarm mode (on
    an existing swarm), set this option to True and set
    `docker_connect_port` in the IE plugin config (ini) file(s) of any
    IE plugins you have enabled and ensure that you are not using any
    `docker run`-specific options in your plugins' `command_inject`
    options (swarm mode services run using `docker service create`,
    which has a different and more limited set of options). This
    option can be overridden on a per-plugin basis by using the
    `swarm_mode` option in the plugin's ini config file.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``swarm_manager_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy can run a "swarm manager" service that will monitor
    utilization of the swarm and provision/deprovision worker nodes as
    necessary. The service has its own configuration file.
:Default: ``config/swarm_manager_conf.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~
``tour_config_dir``
~~~~~~~~~~~~~~~~~~~

:Description:
    Interactive tour directory: where to store interactive tour
    definition files. Galaxy ships with several basic interface tours
    enabled, though a different directory with custom tours can be
    specified here. The path is relative to the Galaxy root dir.  To
    use an absolute path begin the path with '/'.  This is a comma
    separated list.
:Default: ``config/plugins/tours``
:Type: str


~~~~~~~~~~~~~~~~
``webhooks_dir``
~~~~~~~~~~~~~~~~

:Description:
    Webhooks directory: where to store webhooks - plugins to extend
    the Galaxy UI. By default none will be loaded.  Set to
    config/plugins/webhooks/demo to load Galaxy's demo webhooks.  To
    use an absolute path begin the path with '/'.  This is a comma
    separated list. Add test/functional/webhooks to this list to
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
:Default: ``database/jobs_directory``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``cluster_files_directory``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If using a cluster, Galaxy will write job scripts and
    stdout/stderr to this directory.
:Default: ``database/pbs``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``template_cache_path``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Mako templates are compiled as needed and cached for reuse, this
    directory is used for the cache
:Default: ``database/compiled_templates``
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
:Default: ``database/citations/data``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``citation_cache_lock_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Citation related caching.  Tool citations information maybe
    fetched from external sources such as https://doi.org/ by Galaxy -
    the following parameters can be used to control the caching used
    to store this information.
:Default: ``database/citations/lock``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Configuration file for the object store If this is set and exists,
    it overrides any other objectstore settings.
:Default: ``config/object_store_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``object_store_store_by``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    What Dataset attribute is used to reference files in an
    ObjectStore implementation, default is 'id' but can also be set to
    'uuid' for more de-centralized usage.
:Default: ``id``
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
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~
``smtp_username``
~~~~~~~~~~~~~~~~~

:Description:
    If your SMTP server requires a username and password, you can
    provide them here (password in cleartext here, but if your server
    supports STARTTLS it will be sent over the network encrypted).
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~
``smtp_password``
~~~~~~~~~~~~~~~~~

:Description:
    If your SMTP server requires a username and password, you can
    provide them here (password in cleartext here, but if your server
    supports STARTTLS it will be sent over the network encrypted).
:Default: ````
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
:Default: ``galaxy-announce-join@bx.psu.edu``
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
:Default: ````
:Type: str


~~~~~~~~~~~~~~
``email_from``
~~~~~~~~~~~~~~

:Description:
    Email address to use in the 'From' field when sending emails for
    account activations, workflow step notifications and password
    resets. We recommend using string in the following format: Galaxy
    Project <galaxy-no-reply@example.com> If not configured, '<galaxy-
    no-reply@HOSTNAME>' will be used.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``instance_resource_url``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    URL of the support resource for the galaxy instance.  Used in
    activation emails.
:Default: ``https://galaxyproject.org/``
:Type: str


~~~~~~~~~~~~~~~~~~
``blacklist_file``
~~~~~~~~~~~~~~~~~~

:Description:
    E-mail domains blacklist is used for filtering out users that are
    using disposable email address during the registration.  If their
    address domain matches any domain in the blacklist, they are
    refused the registration.
:Default: ``config/disposable_email_blacklist.conf``
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
    User account activation feature global flag.  If set to "False",
    the rest of the Account activation configuration is ignored and
    user activation is disabled (i.e. accounts are active since
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
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~
``display_servers``
~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy can display data at various external browsers.  These
    options specify which browsers should be available.  URLs and
    builds available at these browsers are defined in the specifield
    files.  If use_remote_user = True, display application servers
    will be denied access to Galaxy and so displaying datasets in
    these sites will fail. display_servers contains a list of
    hostnames which should be allowed to bypass security to display
    datasets.  Please be aware that there are security implications if
    this is allowed.  More details (including required changes to the
    proxy server config) are available in the Apache proxy
    documentation on the Galaxy Community Hub.  The list of servers in
    this sample config are for the UCSC Main, Test and Archaea
    browsers, but the default if left commented is to not allow any
    display sites to bypass security (you must uncomment the line
    below to allow them).
:Default: ``hgw1.cse.ucsc.edu,hgw2.cse.ucsc.edu,hgw3.cse.ucsc.edu,hgw4.cse.ucsc.edu,hgw5.cse.ucsc.edu,hgw6.cse.ucsc.edu,hgw7.cse.ucsc.edu,hgw8.cse.ucsc.edu,lowepub.cse.ucsc.edu``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_old_display_applications``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    To disable the old-style display applications that are hardcoded
    into datatype classes, set enable_old_display_applications =
    False. This may be desirable due to using the new-style, XML-
    defined, display applications that have been defined for many of
    the datatypes that have the old-style. There is also a potential
    security concern with the old-style applications, where a
    malicious party could provide a link that appears to reference the
    Galaxy server, but contains a redirect to a third-party server,
    tricking a Galaxy user to access said site.
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
:Default: ````
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
    Append "/{brand}" to the "Galaxy" text in the masthead.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~
``pretty_datetime_format``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Format string used when showing date and time information. The
    string may contain: - the directives used by Python
    time.strftime() function (see
    https://docs.python.org/library/time.html#time.strftime ), -
    $locale (complete format string for the server locale), - $iso8601
    (complete format string as specified by ISO 8601 international
    standard).
:Default: ``$locale (UTC)``
:Type: str


~~~~~~~~~~~~~~~~~~
``default_locale``
~~~~~~~~~~~~~~~~~~

:Description:
    Default localization for Galaxy UI. Allowed values are listed at
    the end of client/galaxy/scripts/nls/locale.js. With the default
    value (auto), the locale will be automatically adjusted to the
    user's navigator language. Users can override this settings in
    their user preferences if the localization settings are enabled in
    user_preferences_extra_conf.yml
:Default: ``auto``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``galaxy_infrastructure_url``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    URL (with schema http/https) of the Galaxy instance as accessible
    within your local network - if specified used as a default by
    pulsar file staging and Jupyter Docker container for communicating
    back with Galaxy via the API.  If you are attempting to setup GIEs
    on Mac OS X with Docker for Mac - this should likely be the IP
    address of your machine on the virtualbox network (vboxnet0) setup
    for the Docker host VM. This can found by running ifconfig and
    using the IP address of the network vboxnet0.
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


~~~~~~~~~~~~~~~~
``helpsite_url``
~~~~~~~~~~~~~~~~

:Description:
    The URL linked by the "Galaxy Help" link in the "Help" menu.
:Default: ````
:Type: str


~~~~~~~~~~~~
``wiki_url``
~~~~~~~~~~~~

:Description:
    The URL linked by the "Wiki" link in the "Help" menu.
:Default: ``https://galaxyproject.org/``
:Type: str


~~~~~~~~~~~~~~~
``support_url``
~~~~~~~~~~~~~~~

:Description:
    The URL linked by the "Support" link in the "Help" menu.
:Default: ``https://galaxyproject.org/support/``
:Type: str


~~~~~~~~~~~~~~~
``biostar_url``
~~~~~~~~~~~~~~~

:Description:
    Enable integration with a custom Biostar instance.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~
``biostar_key_name``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable integration with a custom Biostar instance.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~
``biostar_key``
~~~~~~~~~~~~~~~

:Description:
    Enable integration with a custom Biostar instance.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``biostar_enable_bug_reports``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable integration with a custom Biostar instance.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``biostar_never_authenticate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable integration with a custom Biostar instance.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~
``citation_url``
~~~~~~~~~~~~~~~~

:Description:
    The URL linked by the "How to Cite Galaxy" link in the "Help"
    menu.
:Default: ``https://galaxyproject.org/citing-galaxy``
:Type: str


~~~~~~~~~~~~~~
``search_url``
~~~~~~~~~~~~~~

:Description:
    The URL linked by the "Search" link in the "Help" menu.
:Default: ``https://galaxyproject.org/search/``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``mailing_lists_url``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    The URL linked by the "Mailing Lists" link in the "Help" menu.
:Default: ``https://galaxyproject.org/mailing-lists``
:Type: str


~~~~~~~~~~~~~~~~~~~
``screencasts_url``
~~~~~~~~~~~~~~~~~~~

:Description:
    The URL linked by the "Videos" link in the "Help" menu.
:Default: ``https://vimeo.com/galaxyproject``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``genomespace_ui_url``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Points to the GenomeSpace UI service which will be used by the
    GenomeSpace importer and exporter tools
:Default: ``https://gsui.genomespace.org/jsui/``
:Type: str


~~~~~~~~~~~~~
``terms_url``
~~~~~~~~~~~~~

:Description:
    The URL linked by the "Terms and Conditions" link in the "Help"
    menu, as well as on the user registration and login forms and in
    the activation emails.
:Default: ````
:Type: str


~~~~~~~~~~
``qa_url``
~~~~~~~~~~

:Description:
    The URL linked by the "Galaxy Q&A" link in the "Help" menu The
    Galaxy Q&A site is under development; when the site is done, this
    URL will be set and uncommented.
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
:Default: ``static/june_2007_style/blue``
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
    mod_xsendfile.  Set this to True to inform Galaxy that
    mod_xsendfile is enabled upstream.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``nginx_x_accel_redirect_base``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The same download handling can be done by nginx using X-Accel-
    Redirect.  This should be set to the path defined in the nginx
    config as an internal redirect with access to Galaxy's data files
    (see documentation linked above).
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~
``upstream_gzip``
~~~~~~~~~~~~~~~~~

:Description:
    If using compression in the upstream proxy server, use this option
    to disable gzipping of library .tar.gz and .zip archives, since
    the proxy server will do it faster on the fly.
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
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``nginx_upload_path``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    This value overrides the action set on the file upload form, e.g.
    the web path where the nginx_upload_module has been configured to
    intercept upload requests.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``nginx_upload_job_files_store``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy can also use nginx_upload_module to receive files staged
    out upon job completion by remote job runners (i.e. Pulsar) that
    initiate staging operations on the remote end.  See the Galaxy
    nginx documentation for the corresponding nginx configuration.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``nginx_upload_job_files_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy can also use nginx_upload_module to receive files staged
    out upon job completion by remote job runners (i.e. Pulsar) that
    initiate staging operations on the remote end.  See the Galaxy
    nginx documentation for the corresponding nginx configuration.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``chunk_upload_size``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy can upload user files in chunks without using nginx. Enable
    the chunk uploader by specifying a chunk size larger than 0. The
    chunk size is specified in bytes (default: 100MB).
:Default: ``104857600``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_manage``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Have Galaxy manage dynamic proxy component for routing requests to
    other services based on Galaxy's session cookie.  It will attempt
    to do this by default though you do need to install node+npm and
    do an npm install from `lib/galaxy/web/proxy/js`.  It is generally
    more robust to configure this externally, managing it however
    Galaxy is managed.  If True, Galaxy will only launch the proxy if
    it is actually going to be used (e.g. for Jupyter).
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~
``dynamic_proxy``
~~~~~~~~~~~~~~~~~

:Description:
    As of 16.04 Galaxy supports multiple proxy types. The original
    NodeJS implementation, alongside a new Golang single-binary-no-
    dependencies version. Valid values are (node, golang)
:Default: ``node``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_session_map``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The NodeJS dynamic proxy can use an SQLite database or a JSON file
    for IPC, set that here.
:Default: ``database/session_map.sqlite``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_bind_port``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set the port and IP for the the dynamic proxy to bind to, this
    must match the external configuration if dynamic_proxy_manage is
    False.
:Default: ``8800``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~
``dynamic_proxy_bind_ip``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set the port and IP for the the dynamic proxy to bind to, this
    must match the external configuration if dynamic_proxy_manage is
    False.
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
    This will result in a url like https://FQDN/galaxy-
    prefix/gie_proxy for proxying
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
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~
``auto_configure_logging``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If True, Galaxy will attempt to configure a simple root logger if
    a "loggers" section does not appear in this configuration file.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~
``log_level``
~~~~~~~~~~~~~

:Description:
    Verbosity of console log messages.  Acceptable values can be found
    here: https://docs.python.org/library/logging.html#logging-levels
    A custom debug level of "TRACE" is available for even more
    verbosity.
:Default: ``DEBUG``
:Type: str


~~~~~~~~~~~
``logging``
~~~~~~~~~~~

:Description:
    Controls where and how the server logs messages. If unset, the
    default is to log all messages to standard output at the level
    defined by the `log_level` configuration option. Configuration is
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
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~
``log_actions``
~~~~~~~~~~~~~~~

:Description:
    Turn on logging of user actions to the database.  Actions
    currently logged are grid views, tool searches, and use of
    "recently" used tools menu.  The log_events and log_actions
    functionality will eventually be merged.
:Default: ``true``
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
``sanitize_whitelist_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Whitelist sanitization file. Datasets created by tools listed in
    this file are trusted and will not have their HTML sanitized on
    display.  This can be manually edited or manipulated through the
    Admin control panel -- see "Manage Display Whitelist"
:Default: ``config/sanitize_whitelist.txt``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``serve_xss_vulnerable_mimetypes``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    By default Galaxy will serve non-HTML tool output that may
    potentially contain browser executable JavaScript content as plain
    text.  This will for instance cause SVG datasets to not render
    properly and so may be disabled by setting the following option to
    True.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``allowed_origin_hostnames``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Return a Access-Control-Allow-Origin response header that matches
    the Origin header of the request if that Origin hostname matches
    one of the strings or regular expressions listed here. This is a
    comma separated list of hostname strings or regular expressions
    beginning and ending with /. E.g.
    mysite.com,google.com,usegalaxy.org,/^[\w\.]*example\.com/ See:
    https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``trust_jupyter_notebook_conversion``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set the following to True to use Jupyter nbconvert to build HTML
    from Jupyter notebooks in Galaxy histories.  This process may
    allow users to execute arbitrary code or serve arbitrary HTML.  If
    enabled, Jupyter must be available and on Galaxy's PATH, to do
    this run `pip install jinja2 pygments jupyter` in Galaxy's
    virtualenv.
:Default: ``false``
:Type: bool


~~~~~~~~~
``debug``
~~~~~~~~~

:Description:
    Debug enables access to various config options useful for
    development and debugging: use_lint, use_profile, use_printdebug
    and use_interactive.  It also causes the files used by PBS/SGE
    (submission script, output, and error) to remain on disk after the
    job is complete.
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


~~~~~~~~~~~~~~~~~~~
``use_interactive``
~~~~~~~~~~~~~~~~~~~

:Description:
    Enable live debugging in your browser.  This should NEVER be
    enabled on a public site.
:Default: ``false``
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
    `stopwaitsecs`. If using job handler mules, consider also setting
    the `mule-reload-mercy` uWSGI option. See the Galaxy Admin
    Documentation for more.
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
    send a Galaxy process (unless running with uWSGI) SIGUSR1 (`kill
    -USR1`) to force a dump.
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
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``sentry_sloreq_threshold``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Sentry slow request logging.  Requests slower than the threshold
    indicated below will be sent as events to the configured Sentry
    server (above, sentry_dsn).  A value of '0' is disabled.  For
    example, you would set this to .005 to log all queries taking
    longer than 5 milliseconds.
:Default: ``0.0``
:Type: float


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


~~~~~~~~~~~~~~~~~~~~~~
``library_import_dir``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Add an option to the library upload form which allows
    administrators to upload a directory of files.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_library_import_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Add an option to the library upload form which allows authorized
    non-administrators to upload a directory of files.  The configured
    directory must contain sub-directories named the same as the non-
    admin user's Galaxy login ( email ).  The non-admin user is
    restricted to uploading files or sub-directories of files
    contained in their directory.
:Default: ````
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
``user_library_import_symlink_whitelist``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    For security reasons, users may not import any files that actually
    lie outside of their `user_library_import_dir` (e.g. using
    symbolic links). A list of directories can be allowed by setting
    the following option (the list is comma-separated). Be aware that
    *any* user with library import permissions can import from
    anywhere in these directories (assuming they are able to create
    symlinks to them).
:Default: ````
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
    file://). Set to True to enable.  Please note the security
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


~~~~~~~~~~~~~~~~~~~~~~~~~
``transfer_manager_port``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Some sequencer integration features in beta allow you to
    automatically transfer datasets.  This is done using a lightweight
    transfer manager which runs outside of Galaxy (but is spawned by
    it automatically).  Galaxy will communicate with this manager over
    the port specified here.
:Default: ``8163``
:Type: int


~~~~~~~~~~~~~~~~~~~
``tool_name_boost``
~~~~~~~~~~~~~~~~~~~

:Description:
    Boosts are used to customize this instance's toolbox search. The
    higher the boost, the more importance the scoring algorithm gives
    to the given field.  Section refers to the tool group in the tool
    panel.  Rest of the fields are tool's attributes.
:Default: ``9.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~
``tool_section_boost``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Boosts are used to customize this instance's toolbox search. The
    higher the boost, the more importance the scoring algorithm gives
    to the given field.  Section refers to the tool group in the tool
    panel.  Rest of the fields are tool's attributes.
:Default: ``3.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_description_boost``
~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Boosts are used to customize this instance's toolbox search. The
    higher the boost, the more importance the scoring algorithm gives
    to the given field.  Section refers to the tool group in the tool
    panel.  Rest of the fields are tool's attributes.
:Default: ``2.0``
:Type: float


~~~~~~~~~~~~~~~~~~~~
``tool_label_boost``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Boosts are used to customize this instance's toolbox search. The
    higher the boost, the more importance the scoring algorithm gives
    to the given field.  Section refers to the tool group in the tool
    panel.  Rest of the fields are tool's attributes.
:Default: ``1.0``
:Type: float


~~~~~~~~~~~~~~~~~~~
``tool_stub_boost``
~~~~~~~~~~~~~~~~~~~

:Description:
    Boosts are used to customize this instance's toolbox search. The
    higher the boost, the more importance the scoring algorithm gives
    to the given field.  Section refers to the tool group in the tool
    panel.  Rest of the fields are tool's attributes.
:Default: ``5.0``
:Type: float


~~~~~~~~~~~~~~~~~~~
``tool_help_boost``
~~~~~~~~~~~~~~~~~~~

:Description:
    Boosts are used to customize this instance's toolbox search. The
    higher the boost, the more importance the scoring algorithm gives
    to the given field.  Section refers to the tool group in the tool
    panel.  Rest of the fields are tool's attributes.
:Default: ``0.5``
:Type: float


~~~~~~~~~~~~~~~~~~~~~
``tool_search_limit``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Limits the number of results in toolbox search.  Can be used to
    tweak how many results will appear.
:Default: ``20``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_enable_ngram_search``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable/ disable Ngram-search for tools. It makes tool search
    results tolerant for spelling mistakes in the query by dividing
    the query into multiple ngrams and search for each ngram
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~
``tool_ngram_minsize``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set minimum size of ngrams
:Default: ``3``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~
``tool_ngram_maxsize``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set maximum size of ngrams
:Default: ``4``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_test_data_directories``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set tool test data directory. The test framework sets this value
    to 'test-data,https://github.com/galaxyproject/galaxy-test-
    data.git' which will cause Galaxy to clone down extra test data on
    the fly for certain tools distributed with Galaxy but this is
    likely not appropriate for production systems. Instead one can
    simply clone that repository directly and specify a path here
    instead of a Git HTTP repository.
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
    logins.  For more information, see: https://docs.galaxyproject.org
    /en/master/admin/special_topics/apache.html
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
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``remote_user_header``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If use_remote_user is enabled, the header that the upstream proxy
    provides the remote username in defaults to HTTP_REMOTE_USER (the
    'HTTP_' is prepended by WSGI).  This option allows you to change
    the header.  Note, you still need to prepend 'HTTP_' to the header
    in this option, but your proxy server should *not* include 'HTTP_'
    at the beginning of the header name.
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
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``normalize_remote_user_email``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If your proxy and/or authentication source does not normalize
    e-mail addresses or user names being passed to Galaxy - set the
    following option to True to force these to lower case.
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
:Default: ````
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
    page (even if require_login is True)
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
    debugging)
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``show_user_prepopulate_form``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When using LDAP for authentication, allow administrators to pre-
    populate users using an additional form on 'Create new user'
:Default: ``false``
:Type: bool


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
    By default, users' data will be public, but setting this to True
    will cause it to be private.  Does not affect existing users and
    data, only ones created after this option is set.  Users may still
    change their default back to public.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~
``expose_user_name``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Expose user list.  Setting this to True will expose the user list
    to authenticated users.  This makes sharing datasets in smaller
    galaxy instances much easier as they can type a name/email and
    have the correct user show up. This makes less sense on large
    public Galaxy instances where that data shouldn't be exposed.  For
    semi-public Galaxies, it may make sense to expose just the
    username and not email, or vice versa.  If enable_beta_gdpr is set
    to True, then this option will be overridden and set to False.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~
``expose_user_email``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Expose user list.  Setting this to True will expose the user list
    to authenticated users.  This makes sharing datasets in smaller
    galaxy instances much easier as they can type a name/email and
    have the correct user show up. This makes less sense on large
    public Galaxy instances where that data shouldn't be exposed.  For
    semi-public Galaxies, it may make sense to expose just the
    username and not email, or vice versa.  If enable_beta_gdpr is set
    to True, then this option will be overridden and set to False.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~
``fetch_url_whitelist``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Whitelist for local network addresses for "Upload from URL"
    dialog. By default, Galaxy will deny access to the local network
    address space, to prevent users making requests to services which
    the administrator did not intend to expose. Previously, you could
    request any network service that Galaxy might have had access to,
    even if the user could not normally access it. It should be a
    comma separated list of IP addresses or IP address/mask, e.g.
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
    this is not currently easily implementable.  You are responsible
    for removing personal data from backups.  This forces
    expose_user_email and expose_user_name to be false, and forces
    user_deletion to be true to support the right to erasure.  Please
    read the GDPR section under the special topics area of the admin
    documentation.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_beta_ts_api_install``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable the new interface for installing tools from Tool Shed via
    the API. Admin menu will list both if enabled.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_beta_containers_interface``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable the new container interface for Interactive Environments
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_submission_burst_threads``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Set the following to a number of threads greater than 1 to spawn a
    Python task queue for dealing with large tool submissions (either
    through the tool form or as part of an individual workflow step
    across large collection). This affects workflow scheduling and web
    processes, not job handlers. This is a beta option and should not
    be used in production.
:Default: ``1``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tool_submission_burst_at``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If tool_submission_burst_threads is set to a number greater than
    1, this is the number of jobs to schedule at which the task queue
    will be created.
:Default: ``10``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_beta_workflow_modules``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable beta workflow modules that should not yet be considered
    part of Galaxy's stable API.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_beta_workflow_format``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable import and export of workflows as Galaxy Format 2
    workflows.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``force_beta_workflow_scheduled_min_steps``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Following options only apply to workflows scheduled using the
    legacy workflow run API (running workflows via a POST to
    /api/workflows). Force usage of Galaxy's beta workflow scheduler
    under certain circumstances - this workflow scheduling forces
    Galaxy to schedule workflows in the background so initial
    submission of the workflows is significantly sped up. This does
    however force the user to refresh their history manually to see
    newly scheduled steps (for "normal" workflows - steps are still
    scheduled far in advance of them being queued and scheduling here
    doesn't refer to actual cluster job scheduling). Workflows
    containing more than the specified number of steps will always use
    the Galaxy's beta workflow scheduling.
:Default: ``250``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``force_beta_workflow_scheduled_for_collections``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Following options only apply to workflows scheduled using the
    legacy workflow run API (running workflows via a POST to
    /api/workflows). Force usage of Galaxy's beta workflow scheduler
    under certain circumstances - this workflow scheduling forces
    Galaxy to schedule workflows in the background so initial
    submission of the workflows is significantly sped up. This does
    however force the user to refresh their history manually to see
    newly scheduled steps (for "normal" workflows - steps are still
    scheduled far in advance of them being queued and scheduling here
    doesn't refer to actual cluster job scheduling). Workflows
    containing more than the specified number of steps will always use
    the Galaxy's beta workflow scheduling. Switch to using Galaxy's
    beta workflow scheduling for all workflows involving collections.
:Default: ``false``
:Type: bool


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
    Set to -1 to disable any such maximum (the default).
:Default: ``-1``
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
:Default: ``config/oidc_config.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``oidc_backends_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Sets the path to OIDC backends configuration file.
:Default: ``config/oidc_backends_config.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``auth_config_file``
~~~~~~~~~~~~~~~~~~~~

:Description:
    XML config file that allows the use of different authentication
    providers (e.g. LDAP) instead or in addition to local
    authentication (.sample is used if default does not exist).
:Default: ``config/auth_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``api_allow_run_as``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Optional list of email addresses of API users who can make calls
    on behalf of other users.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~
``master_api_key``
~~~~~~~~~~~~~~~~~~

:Description:
    Master key that allows many API admin actions to be used without
    actually having a defined admin user in the database/config.  Only
    set this if you need to bootstrap Galaxy, you probably do not want
    to set this on public servers.
:Default: ``changethis``
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
    False, the most recently added compatible item in the history will
    be used for each "Set at Runtime" input, independent of others in
    the Workflow
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~
``myexperiment_url``
~~~~~~~~~~~~~~~~~~~~

:Description:
    The URL to the myExperiment instance being used (omit scheme but
    include port)
:Default: ``www.myexperiment.org:80``
:Type: str


~~~~~~~~~~~~~~~~~~
``ftp_upload_dir``
~~~~~~~~~~~~~~~~~~

:Description:
    Enable Galaxy's "Upload via FTP" interface.  You'll need to
    install and configure an FTP server (we've used ProFTPd since it
    can use Galaxy's database for authentication) and set the
    following two options. This should point to a directory containing
    subdirectories matching users' identifier (defaults to e-mail),
    where Galaxy will look for files.
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~
``ftp_upload_site``
~~~~~~~~~~~~~~~~~~~

:Description:
    This should be the hostname of your FTP server, which will be
    provided to users in the help text.
:Default: ````
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
:Default: ``${ftp_upload_dir}/${ftp_upload_dir_identifier}``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``ftp_upload_purge``
~~~~~~~~~~~~~~~~~~~~

:Description:
    This should be set to False to prevent Galaxy from deleting
    uploaded FTP files as it imports them.
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
:Default: ``config/data_manager_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``shed_data_manager_config_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    File where Tool Shed based Data Managers are configured.
:Default: ``config/shed_data_manager_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``galaxy_data_manager_data_path``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Directory to store Data Manager based tool-data; defaults to
    tool_data_path.
:Default: ``tool-data``
:Type: str


~~~~~~~~~~~~~~~~~~~
``job_config_file``
~~~~~~~~~~~~~~~~~~~

:Description:
    To increase performance of job execution and the web interface,
    you can separate Galaxy into multiple processes.  There are more
    than one way to do this, and they are explained in detail in the
    documentation:
    https://docs.galaxyproject.org/en/master/admin/scaling.html  By
    default, Galaxy manages and executes jobs from within a single
    process and notifies itself of new jobs via in-memory queues.
    Jobs are run locally on the system on which Galaxy is started.
    Advanced job running capabilities can be configured through the
    job configuration file.
:Default: ``config/job_conf.xml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``default_job_resubmission_condition``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When jobs fail due to job runner problems, Galaxy can be
    configured to retry these or reroute the jobs to new destinations.
    Very fine control of this is available with resubmit declarations
    in job_conf.xml. For simple deployments of Galaxy though, the
    following attribute can define resubmission conditions for all job
    destinations. If any job destination defines even one resubmission
    condition explicitly in job_conf.xml - the condition described by
    this option will not apply to that destination. For instance, the
    condition: 'attempt < 3 and unknown_error and (time_running < 300
    or time_since_queued < 300)' would retry up to two times jobs that
    didn't fail due to detected memory or walltime limits but did fail
    quickly (either while queueing or running). The commented out
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


~~~~~~~~~~~~~~~~~~~~~~~
``enable_job_recovery``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Enable job recovery (if Galaxy is restarted while cluster jobs are
    running, it can "recover" them when it starts).  This is not safe
    to use if you are running more than one Galaxy server using the
    same database.
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``retry_metadata_internally``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Although it is fairly reliable, setting metadata can occasionally
    fail.  In these instances, you can choose to retry setting it
    internally or leave it in a failed state (since retrying
    internally may cause the Galaxy process to be unresponsive).  If
    this option is set to False, the user will be given the option to
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
    (https://docs.galaxyproject.org/en/master/admin/cluster.html
    #submitting-jobs-as-the-real-user) this script is used to run the
    job script Galaxy generates for a tool execution.
:Default: ``sudo -E scripts/drmaa_external_runner.py --assign_all_groups``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``drmaa_external_killjob_script``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When running DRMAA jobs as the Galaxy user
    (https://docs.galaxyproject.org/en/master/admin/cluster.html
    #submitting-jobs-as-the-real-user) this script is used to kill
    such jobs by Galaxy (e.g. if the user cancels the job).
:Default: ``sudo -E scripts/drmaa_external_killer.py``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~
``external_chown_script``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When running DRMAA jobs as the Galaxy user
    (https://docs.galaxyproject.org/en/master/admin/cluster.html
    #submitting-jobs-as-the-real-user) this script is used transfer
    permissions back and forth between the Galaxy user and the user
    that is running the job.
:Default: ``sudo -E scripts/external_chown_script.py``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``real_system_username``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    When running DRMAA jobs as the Galaxy user
    (https://docs.galaxyproject.org/en/master/admin/cluster.html
    #submitting-jobs-as-the-real-user) Galaxy can extract the user
    name from the email address (actually the local-part before the @)
    or the username which are both stored in the Galaxy data base. The
    latter option is particularly useful for installations that get
    the authentication from LDAP. Also, Galaxy can accept the name of
    a common system user (eg. galaxy_worker) who can run every job
    being submitted. This user should not be the same user running the
    galaxy system. Possible values are user_email (default), username
    or <common_system_user>
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
:Default: ````
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``job_resource_params_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Optional file containing job resource data entry fields
    definition. These fields will be presented to users in the tool
    forms and allow them to overwrite default job resources such as
    number of processors, memory and walltime.
:Default: ``config/job_resource_params_conf.xml``
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
:Default: ``config/workflow_resource_params_conf.xml``
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
    path it is expected to an XML or YAML file describing how to map
    group names to parameter descriptions (additional types of
    mappings via these files could be implemented but haven't yet -
    for instance using workflow tags to do the mapping).
:Default: ``config/workflow_resource_mapper_conf.yml``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``cache_user_job_count``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    If using job concurrency limits (configured in job_config_file),
    several extra database queries must be performed to determine the
    number of jobs a user has dispatched to a given destination.  By
    default, these queries will happen for every job that is waiting
    to run, but if cache_user_job_count is set to True, it will only
    happen once per iteration of the handler queue. Although better
    for performance due to reduced queries, the trade-off is a greater
    possibility that jobs will be dispatched past the configured
    limits if running many handlers.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~
``tool_filters``
~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters (https://galaxyproject.org/user-defined-
    toolbox-filters/) that admins may use to restrict the tools to
    display.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~
``tool_label_filters``
~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters (https://galaxyproject.org/user-defined-
    toolbox-filters/) that admins may use to restrict the tool labels
    to display.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~
``tool_section_filters``
~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters (https://galaxyproject.org/user-defined-
    toolbox-filters/) that admins may use to restrict the tool
    sections to display.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~~~~~~~~
``user_tool_filters``
~~~~~~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters (https://galaxyproject.org/user-defined-
    toolbox-filters/) that users may use to restrict the tools to
    display.
:Default: ``examples:restrict_upload_to_admins, examples:restrict_encode``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_tool_section_filters``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters (https://galaxyproject.org/user-defined-
    toolbox-filters/) that users may use to restrict the tool sections
    to display.
:Default: ``examples:restrict_text``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~
``user_tool_label_filters``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Define toolbox filters (https://galaxyproject.org/user-defined-
    toolbox-filters/) that users may use to restrict the tool labels
    to display.
:Default: ``examples:restrict_upload_to_admins, examples:restrict_encode``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``toolbox_filter_base_modules``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    The base module(s) that are searched for modules for toolbox
    filtering (https://galaxyproject.org/user-defined-toolbox-
    filters/) functions.
:Default: ``galaxy.tools.toolbox.filters,galaxy.tools.filters``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``amqp_internal_connection``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy uses AMQP internally for communicating between processes.
    For example, when reloading the toolbox or locking job execution,
    the process that handled that particular request will tell all
    others to also reload, lock jobs, etc. For connection examples,
    see http://docs.celeryproject.org/projects/kombu/en/latest/usergui
    de/connections.html  Without specifying anything here, galaxy will
    first attempt to use your specified database_connection above.  If
    that's not specified either, Galaxy will automatically create and
    use a separate sqlite database located in your <galaxy>/database
    folder (indicated in the commented out line below).
:Default: ``sqlalchemy+sqlite:///./database/control.sqlite?isolation_level=IMMEDIATE``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``enable_communication_server``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy real time communication server settings
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``communication_server_host``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy real time communication server settings
:Default: ``http://localhost``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``communication_server_port``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Galaxy real time communication server settings
:Default: ``7070``
:Type: int


~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``persistent_communication_rooms``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    persistent_communication_rooms is a comma-separated list of rooms
    that should be always available.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~~
``use_pbkdf2``
~~~~~~~~~~~~~~

:Description:
    Allow disabling pbkdf2 hashing of passwords for legacy situations.
    This should normally be left enabled unless there is a specific
    reason to disable it.
:Default: ``true``
:Type: bool




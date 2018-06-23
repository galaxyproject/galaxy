~~~~~~~~~~~~~~~
``filter-with``
~~~~~~~~~~~~~~~

:Description:
    If running behind a proxy server and Galaxy is served from a
    subdirectory, enable the proxy-prefix filter and set the prefix in
    the [filter:proxy-prefix] section above.
:Default: ``proxy-prefix``
:Type: str


~~~~~~~~~~~~~~~
``cookie_path``
~~~~~~~~~~~~~~~

:Description:
    If proxy-prefix is enabled and you're running more than one Galaxy
    instance behind one hostname, you will want to set this to the
    same path as the prefix in the filter above.  This value becomes
    the "path" attribute set in the cookie so the cookies from each
    instance will not clobber each other.
:Default: ``None``
:Type: str


~~~~~~~~~~~~~
``log_level``
~~~~~~~~~~~~~

:Description:
    Verbosity of console log messages.  Acceptable values can be found
    here: https://docs.python.org/2/library/logging.html#logging-
    levels
:Default: ``DEBUG``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``database_connection``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Database connection Galaxy reports are intended for production
    Galaxy instances, so sqlite (and the default value below) is not
    supported. An SQLAlchemy connection string should be used specify
    an external database.
:Default: ``sqlite:///./database/universe.sqlite?isolation_level=IMMEDIATE``
:Type: str


~~~~~~~~~~~~~
``file_path``
~~~~~~~~~~~~~

:Description:
    Where dataset files are saved Temporary storage for additional
    datasets, this should be shared through the cluster
:Default: ``database/files``
:Type: str


~~~~~~~~~~~~~~~~~
``new_file_path``
~~~~~~~~~~~~~~~~~

:Description:
    Where dataset files are saved Temporary storage for additional
    datasets, this should be shared through the cluster
:Default: ``database/tmp``
:Type: str


~~~~~~~~~~~~~~~~~~~~~~~
``template_cache_path``
~~~~~~~~~~~~~~~~~~~~~~~

:Description:
    Mako templates are compiled as needed and cached for reuse, this
    directory is used for the cache
:Default: ``database/compiled_templates/reports``
:Type: str


~~~~~~~~~
``debug``
~~~~~~~~~

:Description:
    Configuration for debugging middleware
:Default: ``false``
:Type: bool


~~~~~~~~~~~~
``use_lint``
~~~~~~~~~~~~

:Description:
    Check for WSGI compliance.
:Default: ``false``
:Type: bool


~~~~~~~~~~~~~~~~~~~
``use_interactive``
~~~~~~~~~~~~~~~~~~~

:Description:
    NEVER enable this on a public site (even test or QA)
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~~~
``use_heartbeat``
~~~~~~~~~~~~~~~~~

:Description:
    Write thread status periodically to 'heartbeat.log' (careful, uses
    disk space rapidly!)
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~
``use_profile``
~~~~~~~~~~~~~~~

:Description:
    Profiling middleware (cProfile based)
:Default: ``true``
:Type: bool


~~~~~~~~~~~~~~~
``smtp_server``
~~~~~~~~~~~~~~~

:Description:
    Mail
:Default: ``yourserver@yourfacility.edu``
:Type: str


~~~~~~~~~~~~~~~~~~
``error_email_to``
~~~~~~~~~~~~~~~~~~

:Description:
    Mail
:Default: ``your_bugs@bx.psu.edu``
:Type: str


~~~~~~~~~~~~~~~~~~~~
``enable_beta_gdpr``
~~~~~~~~~~~~~~~~~~~~

:Description:
    Enables GDPR Compliance mode. This makes several changes to the
    way Galaxy logs and exposes data externally such as removing
    emails/usernames from logs and bug reports.  You are responsible
    for removing personal data from backups.  Please read the GDPR
    section under the special topics area of the admin documentation.
:Default: ``false``
:Type: bool




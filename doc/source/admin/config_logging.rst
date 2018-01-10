Logging Configuration
========================================

Overview
----------------------------

There are two ways in which you can configure logging for Galaxy servers:

1. Basic/automatic configuration with control over log level and log destination (standard output or a named log file).
2. More complex configuration using the Python :mod:`logging` module's :func:`logging.config.dictConfig` or :func:`logging.config.fileConfig`.

By default, Galaxy logs all messages to standard output at the ``DEBUG`` logging level, unless the ``--daemon`` argument
is passed to ``run.sh``, in which case, output is logged to the file ``galaxy.log`` in the current directory.

The way in which you configure logging depends on whether you are using a YAML or INI configuration file, and also on
whether you are using the uWSGI application server, or Python Paste. Galaxy servers that were created starting with
Galaxy Release 18.01 or later use a YAML configuration file with uWSGI. Galaxy servers that were created with 17.09 or
older use an INI configuration file, and Python Paste by default, but they could be configured to run under uWSGI (and
this was the recommendation for production servers).  If you upgrade a pre-18.01 server running under Paste to 18.01 or
later but do not convert your INI config (``galaxy.ini``) to a YAML config (``galaxy.yml``), the INI config and Paste
will still be used.

uWSGI, Paste, and related terminology are explained in detail in the :doc:`Scaling and Load Balancing <scaling>`
documentation.

Basic Configuration
----------------------------

Basic logging configuration can be used to modify the level of log messages and the file to which Galaxy logs. The level
is controlled by the ``log_level`` configuration option.

If not set, Galaxy logs all messages at the ``DEBUG`` level (versions prior to 18.01 defaulted to ``INFO`` if unset, but
the default config file shipped with ``log_level`` explicitly set to ``DEBUG`` for development purposes).

Galaxy logs all messages to standard output by default if running in the foreground. If running in the background (``sh
run.sh --daemon``) under uWSGI, the log is written to ``galaxy.log`` in the current directory. If running in the
background under Paste, the log is written to ``paster.log``.

**Setting the log level:**

In ``galaxy.yml``, set ``log_level``:

.. code-block:: yaml

    galaxy:
        log_level: LEVEL


Or if using ``galaxy.ini``:

.. code-block:: ini

    [app:main]
    log_level = LEVEL


Where ``LEVEL`` is one of the `logging levels`_ documented in the :mod:`logging` module.

**Logging to a file:**

To change the log file name or location, use the ``$GALAXY_LOG`` environment variable like so:

.. code-block:: shell-session

    $ GALAXY_LOG=/path/to/galaxy/logfile sh run.sh --daemon


Advanced Configuration
----------------------------

With the improved uWSGI support added in Galaxy release 18.01, additional fields identifying the uWSGI worker ID and
mule ID can be added to log messages. These are implemented as the custom Python logging filter
:class:`galaxy.web.stack.UWSGILogFilter` which provides two new Python :class:`logging.LogRecord` attributes:
``%(worker_id)s`` and ``%(mule_id)s``. These aid in identifying which log messages are being emitted by which process
and are used in the default message format when running under uWSGI, but are available to you if you wish to change the
message format. The default message format under uWSGI can be found in
:data:`galaxy.web.stack.UWSGIApplicationStack.log_format`.

Additionally, because uWSGI can start multiple distinct Galaxy processes (e.g. job handler mules) from a single config
file, by default it would not be possible to log each process to a separate file, meaning that the combined log file
could be quite verbose. In order to alleviate this, a ``filename_template`` attribute has been added to
:class:`logging.FileHandler` (or derivative classes) definitions so that multiple file logging is possible.

If you are still using Paste or an INI configuration file, it is still possible to use :func:`logging.config.fileConfig`
logging, but ``filename_template`` is not available in this scenario.

YAML
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The full syntax of Python's :func:`logging.config.dictConfig` is available under the ``logging`` key in the ``galaxy``
section of ``galaxy.yml``. The default as of this release can be found in the
:data:`galaxy.config.LOGGING_CONFIG_DEFAULT` constant and has been converted to YAML format here:

.. include:: config_logging_default_yaml.rst

Using ``run.sh --daemon`` causes Galaxy to log to ``galaxy.log``, but this is done using uWSGI's logging functionality
and does not allow for splitting logging in to multiple files. The following logging definition will cause the creation
of log files ``galaxy_web_0.log`` (the combined messages of all web workers) and ``galaxy_job-handlers_N.log`` where
``N`` is the instance ID of the server process in its pool (aka the mule's position in its farm argument):

.. code-block:: yaml

    galaxy:
        logging:
            filters:
                stack:
                    (): galaxy.web.stack.application_stack_log_filter
            formatters:
                stack:
                    (): galaxy.web.stack.application_stack_log_formatter
            handlers:
                console:
                    class: logging.StreamHandler
                    level: DEBUG
                    formatter: generic
                    stream: ext://sys.stderr
                files:
                    class: logging.FileHandler
                    level: DEBUG
                    formatter: generic
                    filename: galaxy_default.log
                    filename_template: galaxy_{pool_name}_{server_id}.log
            loggers:
                galaxy:
                    handlers:
                    - console
                    - files
                    level: DEBUG
                    propagate: 0
                    qualname: galaxy
                paste.httpserver.ThreadPool:
                    level: WARN
                    qualname: paste.httpserver.ThreadPool
                routes.middleware:
                    level: WARN
                    qualname: routes.middleware
            root:
                handlers:
                - console
                - files
                level: INFO
            version: 1


The list of available template facts for all Galaxy application server types, and their values under the various
possible :doc:`server deployment scenarios <scaling>` are given below:

+-------------------+-----------------------------------------------------------------------------------------------+
| Fact              | Application server                                                                            |
+-------------------+-------------------------------+-------------------------------+-------------------------------+
|                   | Paste/webless                 | uWSGI web worker              | uWSGI mule                    |
+===================+===============================+===============================+===============================+
| ``server_name``   | ``NAME`` for                  | ``main``, but can be modified with ``server_name`` in         |
|                   | ``[server:<NAME>]`` in        | ``galaxy.yml``                                                |
|                   | ``galaxy.ini``                |                                                               |
+-------------------+-------------------------------+-------------------------------+-------------------------------+
| ``server_id``     | ``None``                      | 1-based worker ID             | 1-based mule ID               |
+-------------------+-------------------------------+-------------------------------+-------------------------------+
| ``pool_name``     | ``None``                      | ``web``                       | Mule's farm name              |
+-------------------+-------------------------------+-------------------------------+-------------------------------+
| ``instance_id``   | ``None``                      | Same as ``server_id``         | Mule's 1-based position in    |
|                   |                               |                               | its defined farm              |
+-------------------+-------------------------------+-------------------------------+-------------------------------+
| ``fqdn``          | Fully-qualified domain name of the host on which Galaxy is running                            |
+-------------------+-----------------------------------------------------------------------------------------------+
| ``hostname``      | "Short" hostname (with domain portion stripped) of the host on which Galaxy is running        |
+-------------------+-----------------------------------------------------------------------------------------------+

INI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With an INI galaxy configuration, it is possible to use Python's :func:`logging.config.fileConfig` configuration method for
advanced logging configuration. For example:

.. code-block:: ini

    [loggers]
    keys = root, galaxy

    [handlers]
    keys = console

    [formatters]
    keys = generic

    [logger_root]
    level = INFO
    handlers = console

    [logger_galaxy]
    level = DEBUG
    handlers = console
    qualname = galaxy
    propagate = 0

    [handler_console]
    class = StreamHandler
    args = (sys.stderr,)
    level = DEBUG
    formatter = generic

    [formatter_generic]
    format = %(name)s %(levelname)-5.5s %(asctime)s [p:%(process)s,w:%(worker_id)s,m:%(mule_id)s] [%(threadName)s] %(message)s


However, the ``filename_template`` Galaxy extension is not available with this method.

.. _logging levels: https://docs.python.org/2/library/logging.html#logging-levels
.. _fileConfig file format: https://docs.python.org/2/library/logging.config.html#configuration-file-format

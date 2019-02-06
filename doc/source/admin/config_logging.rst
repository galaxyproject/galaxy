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

For more useful and manageable logging when running Galaxy with forking application stacks (e.g. uWSGI) where multiple
Galaxy server processes are forked after the Galaxy application is loaded, some extensions to standard Python
:mod:`logging` are available in Galaxy:

- Two custom fields (aka Python :class:`logging.LogRecord` attributes) identifying the uWSGI worker ID and mule ID can
  be added to log messages: ``%(worker_id)s`` and ``%(mule_id)s``. These fields aid in associating log messages with the
  Galaxy server processes that emitted them. They are included in the default log format (found in
  :data:`galaxy.web.stack.UWSGIApplicationStack.log_format`) when using uWSGI and are available for use in custom log
  formats.

- A custom ``filename_template`` config option is available to :class:`logging.FileHandler` (or derivative class) log
  handler definitions so that multiple file logging is possible. Without this custom option, all forked Galaxy server
  processes would only be able to log to a single combined log file, which can be very difficult to work with.

YAML
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Advanced logging configuration is performed under the ``logging`` key in the ``galaxy`` section of ``galaxy.yml``. The
syntax is a YAML dictionary in the syntax of Python's :func:`logging.config.dictConfig`. This section covers a few of
the most common configurations as well as Galaxy's customizations. Consult the :func:`logging.config.dictConfig`
documentation for a complete explanation of the syntax and possibilities.

Default
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The default as of this Galaxy release can be found (in Python syntax) in the
:data:`galaxy.config.LOGGING_CONFIG_DEFAULT` constant and (in YAML) below:

.. include:: config_logging_default_yaml.rst

Split Logfiles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using ``run.sh --daemon`` causes Galaxy to log to ``galaxy.log``, but this is done using uWSGI's logging functionality
and does not allow for splitting logging in to multiple files. The following logging definition uses the
``filename_template`` custom handler configuration option to split logging in to the files ``galaxy_web_0.log`` (the
combined messages of all web workers) and ``galaxy_job-handlers_N.log`` where ``N`` is the instance ID of the server
process in its pool (aka the mule's position in its farm argument). In addition to the split file logging, the combined
output is also still logged to standard error.

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
            filters:
            - stack
            formatter: stack
            level: DEBUG
            stream: ext://sys.stderr
          files:
            class: logging.FileHandler
            filters:
            - stack
            level: DEBUG
            formatter: stack
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

The list of available template facts for use in ``filename_template`` with all Galaxy application server types, and
their values under the various possible :doc:`server deployment scenarios <scaling>` are given below:

+-------------------+-----------------------------------------------------------------------------------------------+
| Fact              | Application server                                                                            |
+-------------------+-------------------------------+-------------------------------+-------------------------------+
|                   | Paste/webless                 | uWSGI web worker              | uWSGI mule                    |
+===================+===============================+===============================+===============================+
| ``server_name``   | ``NAME`` for                  | ``main``, but can be modified with ``server_name`` in         |
|                   | ``[server:<NAME>]`` in        | ``galaxy.yml``                                                |
|                   | ``galaxy.ini``                |                                                               |
+-------------------+-------------------------------+-------------------------------+-------------------------------+
| ``server_id``     | ``None``                      | 1-indexed worker ID           | 1-indexed mule ID             |
+-------------------+-------------------------------+-------------------------------+-------------------------------+
| ``pool_name``     | ``None``                      | ``web``                       | Mule's farm name              |
+-------------------+-------------------------------+-------------------------------+-------------------------------+
| ``instance_id``   | ``None``                      | Same as ``server_id``         | Mule's 1-indexed position in  |
|                   |                               |                               | its defined farm              |
+-------------------+-------------------------------+-------------------------------+-------------------------------+
| ``fqdn``          | Fully-qualified domain name of the host on which Galaxy is running                            |
+-------------------+-----------------------------------------------------------------------------------------------+
| ``hostname``      | "Short" hostname (with domain portion stripped) of the host on which Galaxy is running        |
+-------------------+-----------------------------------------------------------------------------------------------+

The log message format can be customized by adding a (or modifying the default) formatter as in the following (partial)
example. Note that in addition to the new format, the value of ``formatter`` in the ``console`` handler has been
changed:

.. code-block:: yaml

    galaxy:
      logging:
        formatters:
          myformat:
            (): '%(name)s %(levelname)s %(asctime)s [p:%(process)s,w:%(worker_id)s,m:%(mule_id)s] [%(threadName)s] %(message)s'
        handlers:
          console:
            class: logging.StreamHandler
            filters:
            - stack
            formatter: myformat
            level: DEBUG
            stream: ext://sys.stderr

INI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With an INI Galaxy configuration, it is possible to use Python's :func:`logging.config.fileConfig` configuration method for
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

While Galaxy's custom log format fields can be used (as seen in the example), the ``filename_template`` handler
configuration extension is only available in the YAML format configuration file.

.. _logging levels: https://docs.python.org/2/library/logging.html#logging-levels
.. _fileConfig file format: https://docs.python.org/2/library/logging.config.html#configuration-file-format

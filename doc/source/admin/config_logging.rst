Logging Configuration
========================================

Overview
----------------------------

There are two ways in which you can configure logging for Galaxy servers:

1. Basic/automatic configuration with control over log level and log destination (standard output or a named log file).
2. More complex configuration using the Python :mod:`logging` module's :func:`logging.config.dictConfig` or :func:`logging.config.fileConfig`.

Basic Configuration
----------------------------

Basic logging configuration can be used to modify the level of log messages and the file to which Galaxy logs.

The logging level is controlled by the ``log_level`` configuration option. By default, Galaxy logs all messages at the
``DEBUG`` level.

Galaxy logs all messages to standard output by default if running in the foreground. If running in the background (e.g.
by passing the ``--daemon`` argument to ``run.sh``), the log is written to a location configured in
`gravity <https://github.com/galaxyproject/gravity/>`_.

Gravity and related terminology are explained in detail in the :doc:`Scaling and Load Balancing <scaling>` documentation.

**Setting the log level:**

In ``galaxy.yml``, set ``log_level``:

.. code-block:: yaml

    galaxy:
        log_level: LEVEL

Where ``LEVEL`` is one of the `logging levels`_ documented in the :mod:`logging` module.

**Logging to a file:**

To change the log file name or location, use the ``$GALAXY_LOG`` environment variable like so:

.. code-block:: shell-session

    $ GALAXY_LOG=/path/to/galaxy/logfile sh run.sh --daemon

It is also possible to specify the path to the log file using the ``log_destination`` configuration option in
``galaxy.yml``. Additionally, it is possible to automatically rotate logs once the log file reaches a given size, using
the ``log_rotate_size`` and ``log_rotate_count`` options, which control the size at which the log is rotated, and the
number of rotated logs to keep, respectively:

.. code-block:: yaml

    galaxy:
        # Set log file path
        log_destination: /srv/galaxy/log/galaxy.log
        # Rotate once log reaches 100 MB
        log_rotate_size: 100 MB
        # Keep the 10 most recent log files
        log_rotate_count: 10

Advanced Configuration
----------------------------

For more useful and manageable logging when running Galaxy with forking application stacks where multiple
Galaxy server processes are forked after the Galaxy application is loaded, a custom ``filename_template`` config option
is available to :class:`logging.FileHandler` (or derivative class) log handler definitions so that multiple file logging is possible.
Without this custom option, all forked Galaxy server processes would only be able to log to a single combined log file,
which can be very difficult to work with.

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

.. _logging levels: https://docs.python.org/library/logging.html#logging-levels
.. _fileConfig file format: https://docs.python.org/library/logging.config.html#configuration-file-format

Logging Configuration
========================================

Overview
----------------------------

Logging in Galaxy is performed through the Python `logging`_ module. Traditionally, and on Galaxy releases prior to
18.01, customization of the logging could be performed in two ways:

1. Basic/automatic configuration with control over log level and log destination (standard output or a named log file).
2. More complex configuration using `logging.config.fileConfig`_.

Starting with release 18.01, it's possible to use the more featureful `logging.config.dictConfig`_ format, with a few
Galaxy-specific extensions described below.

By default, Galaxy logs all messages to standard output at the ``DEBUG`` logging level.

.. .. The way in which logging is configured depends on whether you are using Python Paste or uWSGI.  See :ref:`Application
.. .. Server <application_server>` for help figuring out what you're using. If using uWSGI, it also depends on whether you are
.. .. using an INI or YAML configuration file.

The way in which logging is configured depends on whether you are using an YAML or INI configuration file. Galaxy
servers that were created starting with Galaxy Release 18.01 or later use a YAML configuration file. Galaxy servers that
were created with 17.09 or older use an INI configuration file. If you upgrade a pre-18.01 server to 18.01 or later but
do not convert your INI config (``galaxy.ini``) to a YAML config (``galaxy.yml``), the INI config will still be used.

Basic Configuration
----------------------------

YAML
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Setting the log level:**

```yaml
galaxy:
    log_level: LEVEL
```

Where ``LEVEL`` is one of the `logging levels`_ documented in the `logging`_ module.

**Logging to a file:**

When using ``run.sh --daemon``, the log is written to ``galaxy.log`` in the current directory. To change this:

INI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Setting the log level:


```ini
[app:main]
log_level = LEVEL
```

**Logging to a file:**

Where ``LEVEL`` is one of the `logging levels`_ documented in the `logging`_ module.

When using ``run.sh --daemon``, the log is written to ``paster.log`` in the current directory. To change this:

Advanced Configuration
----------------------------

YAML
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~







On Galaxy servers older than 18.01, or newer servers still running under Paste (see :ref:`Application Server
<application_server`), the logging level is controlled by the ``log_level`` option in ``galaxy.ini``. The possible
values are the `logging levels`_ documented in the `logging`_ module. If not set, the default is ``INFO``, however,
``galaxy.ini.sample`` ships with the value set to ``DEBUG`` for development purposes.

By default, if started in the foreground (e.g. ``run.sh`` with no arguments), log messages are sent to standard output.
If running detached with ``run.sh --daemon``, messages are instead logged to ``paster.log`` in the current directory.



If not specified,
the default l


In the main Galaxy configuration file, ``galaxy.yml``, 


.. _logging: https://docs.python.org/2/library/logging.html
.. _logging levels: https://docs.python.org/2/library/logging.html#logging-levels
.. _logging.config.fileConfig: https://docs.python.org/2/library/logging.config.html#logging.config.fileConfig
.. _logging.config.dictConfig: https://docs.python.org/2/library/logging.config.html#logging.config.dictConfig
.. _fileConfig file format: https://docs.python.org/2/library/logging.config.html#configuration-file-format

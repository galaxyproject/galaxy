Galaxy Configuration
========================================

Overview
----------------------------

Galaxy has a large number of configuration files in an array of formats. Although it is not required to modify *any*
Galaxy configuration files to run the server, most Galaxy servers will modify at least the core configuration file.
These have grown organically over time as new features with the needs for advanced syntaxes and config isolation have
been added. An effort is under way to `standardize and unify configuration formats`_.

Configuration files can be found underneath the ``config/`` subdirectory, wherein you can find ``<name>.sample`` files
corresponding to configuration files that you can modify by copying the ``<name>.sample`` to ``<name>``. In many cases,
you will find that the sample configuration provides the most up-to-date and detailed documentation about the features
configured therein.

Most config files are administered by hand, although a few (ones which begin with ``shed_*``) are modified by Galaxy
when installing from the Galaxy Tool Shed. When starting Galaxy for the first time, these files are copied from their
sample files automatically. You should not need to modify these unless you want to change the directory in to which Tool
Shed tools are installed.


Configuration Files
----------------------------

The primary Galaxy configuration file is ``galaxy.yml``. You will need to use this file to modify core functionality
such as the port on which Galaxy listens, the directory in which Galaxy datasets are stored, the database connection
options, and so forth.

The most commonly modified configuration files include:

- ``galaxy.yml``: Core Galaxy configuration file.
- ``tool_conf.xml``: Describes the paths to local tool configurations that Galaxy should attempt to load.  Tools that
  are installed via the Tool Shed are configured to load in the ``shed_tool_conf.xml`` file.  See the :doc:`Tool Panel
  Administration <tool_panel>` and `Installing Tools into Galaxy`_ documentation for more.
- ``datatypes_conf.xml``: Describes the file formats that are supported in Galaxy. See the `Datatypes documentation`_
  for more.
- ``job_conf.xml``: Controls how Galaxy runs tools, e.g. to run them on a compute cluster. See the :doc:`Cluster
  documentation <cluster>` for more.

Some configuration files are only used when adding local components, rather than ones installed from the Tool Shed:

- ``tool_conf.xml``: As described above.
- ``tool_data_table_conf.xml``: Describes the mapping between Data Tables - the structured format that allow tools to
  work with locally cached reference data - and the location files that describe the actual data that is available (e.g.
  paths, genome builds, etc.).  Data table configurations are also provided by tools in the Tool Shed, those are
  configured in ``shed_tool_data_table_conf.xml``.  See the `Data Preparation documentation`_ for more.
- ``data_manager_conf.xml``: Describes the paths to local Data Managers, special Galaxy tools that automatically fetch
  or create data for Data Tables and manage the corresponding data table and location configuration files. See the `Data
  Managers documentation`_ for more.
- ``local_conda_mapping.yml``: Define mappings between the names specified in the tool configuration (``<requirement>``
  tags) and the conda resolver's names (conda package name).
- ``lmod_modules_mapping.yml``: Define mappings between the names specified in the tool configuration (``<requirement>``
  tags) and the Lmod system.

Some configuration files are used to control the way that Galaxy resolves tool dependencies. Most Galaxy tools are only
descriptions of how to run a particular command line tool, and they do not contain the dependent command line tool. The
task of locating and making available these command line tools is performed by the Galaxy tool dependencies system,
which has configuration files of its own:

Additional configuration files and their purposes are:

- ``auth_conf.xml``: Configures the pluggable authentication service. By default, Galaxy users are created and managed
  internally.
- ``build_sites.yml``: Controls which display applications are available and their configuration paths
- ``containers_conf.yml``: Configures the beta Galaxy containers interface, currently only used by Galaxy Interactive
  Environments, and only neccesary for Docker Swarm support.
- ``dependency_resolvers_conf.xml``: Describes how Galaxy tools (which are typically just descriptions of how to run a
  particular command line tool) should locate their dependencies (the command line tool) that are not part of the tool.
  See the `Dependency Resolvers documentation <dependency_resolvers>` for more.
- ``error_report.yml``: Controls how user-initiated error reporting (e.g. due to tool failure) is performed. See the
  :doc:`Bug Reports documentation <special_topics/bug_reports>` for more.
- ``job_metrics_conf.xml``: Enables reporting of certain conditions and collection of metrics when jobs run.
- ``job_resource_params_conf.xml``: Describes tool form elements that should be inserted into tool forms that can be
  used by users to control runtime parameters such as memory allocations, cluster selection, and so forth.
- ``object_store_conf.xml``: Configures more advanced storage paradigms for Galaxy datasets, including layout across
  multiple filesystems, or in object storage systems such as Swift or Amazon S3.
- ``swarm_manager_conf.yml``: Configures the experimental Docker Swarm manager.
- ``tool_destinations.yml``: Configures dynamic tool destinations, which allow for mapping tools to job destinations
  based on certain runtime job properties, such as the user submitting it, input sizes, and so forth.
- ``tool_sheds_conf.xml``: Defines the list of Tool Shed servers that should appear in the Galaxy Administration
  interface when searching for new tools.
- ``workflow_schedulers_conf.xml``: Similar to the job configuration, controls the scheduling of workflows as jobs.

.. _standardize and unify configuration formats: https://github.com/galaxyproject/galaxy/issues/5148
.. _Installing Tools into Galaxy: https://galaxyproject.org/admin/tools/add-tool-from-toolshed-tutorial/
.. _Datatypes documentation: https://galaxyproject.org/learn/datatypes/
.. _Data Preparation documentation: https://galaxyproject.org/admin/data-preparation/
.. _Data Managers documentation: https://galaxyproject.org/admin/tools/data-managers/


Configuration Basics
----------------------------

- Edit ``config/galaxy.yml`` (copy it from ``config/galaxy.yml.sample`` if it does not exist) to make configuration
  changes. This is a `uWSGI YAML configuration file`_ and should contain two sections, one named ``uwsgi`` for uWSGI and
  one named ``galaxy`` for Galaxy.

    - The default port for the Galaxy web server is ``8080``, and it only binds to localhost by default. To configure
      uWSGI to listen on all available network addresses, set ``http`` to ``0.0.0.0:<port>`` (e.g. ``http:
      0.0.0.0:8080``).
    - Some uWSGI options are required for uWSGI to run Galaxy properly and will be added to the ``uwsgi`` command line
      by ``run.sh`` if not specified in ``galaxy.yml``.
    - uWSGI has a `large number of options`_. The Galaxy documentation refers to some of them, but many additional
      advanced deployment scenarios are available.

- Run Galaxy with ``sh run.sh``
- Use a web browser and go to the address you configured in ``galaxy.yml`` (defaults to http://localhost:8080/)

.. _uWSGI YAML configuration file: https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html
.. _large number of options: https://uwsgi-docs.readthedocs.io/en/latest/Options.html

----------------------------
Configuration Options
----------------------------

.. include:: galaxy_options.rst

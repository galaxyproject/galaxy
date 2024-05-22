.. _job_metrics:


Collecting Job Metrics
======================

Galaxy can collect various metrics about jobs that it runs. The metrics that can be collected depend on which plugins
(described in this section) are enabled. Two ``galaxy.yml`` configuration options control the job metrics plugin
configuration:

1. ``job_metrics``: Inline global configuration of job metrics plugins
2. ``job_metrics_config_file``: Path to a standalone metrics configuration file. Prior to Galaxy 23.2, this was the only
   way to configure job metrics plugins. It defaults to ``<config_dir>/job_metrics_conf.xml`` for legacy reasons, but
   using the XML syntax is discouraged, YAML (the syntax is the same as ``job_metrics``) is preferred.

If the ``job_metrics_config_file`` exists, it overrides anything configured in ``job_metrics``.

Default Job Metrics Configuration
---------------------------------

If no configuration is specified, the default is to load only the ``core`` plugin:

.. code-block:: yaml

  - type: core

Available Job Metrics Plugins
-----------------------------

The list of metrics plugins implemented in the code can be found at ``lib/galaxy/job_metrics/instrumenters``.


core
~~~~

The core plugin captures the number of cores allocated to the job (``$GALAXY_SLOTS``), the start and end time of job (in
seconds since epoch) and computes the runtime in seconds.

It has no options.

.. code-block:: yaml

    - type: core

cpuinfo
~~~~~~~

The cpuinfo plugin captures the processor count on the system that that job ran on (note that this may differ from the
number of CPUs actually allocated to the job).

The optional ``verbose`` option (default: ``false``) captures details (likely far too much) about each CPU, as found in
``/proc/cpuinfo``.

The cpuinfo plugin works on Linux only.

.. code-block:: yaml

    - type: cpuinfo
      verbose: false

meminfo
~~~~~~~

The meminfo plugin captures the memory information on the system that the job ran on (note that this may differ from the
amount of memory actually allocated to the job).

It has no options.

.. code-block:: yaml

    - type: meminfo

hostname
~~~~~~~~

The hostname plugin captures the output of ``hostname`` on the system that the job ran on.

It has no options.

.. code-block:: yaml

    - type: hostname

uname
~~~~~

The uname plugin captures the output of ``uname -a`` on the system that the job ran on.

It has no options.

.. code-block:: yaml

    - type: uname

env
~~~

The env plugin captures environment variables set in the job's executing environment.

By default, it captures **all** environment variables, which is likely excessive but may be useful for debugging. The
optional ``variables`` option can be set to a list of variables to capture (if set). For legacy purposes, this can also
be a comma-separated string of variable names.

.. code-block:: yaml

    - type: env
      variables:
        - HOSTNAME
        - SLURM_CPUS_ON_NODE
        - SLURM_JOBID

cgroup
~~~~~~

The cgroup plugin captures values set by `Linux Control Groups (cgroups)
<https://docs.kernel.org/admin-guide/cgroup-v2.html>`_. This is most useful if your jobs run in unique per-job Cgroups
(as Slurm does `if so configured <https://slurm.schedmd.com/cgroups.html>`_).

Both cgroups version 1 (cgroupsv1) and cgroups version 2 (cgroupsv2) are supported, by default metrics will be collected
for whichever version is mounted on the system where the job ran. The optional ``version`` option (default: ``auto``)
can be used to only generate metrics capture commands in the job script for the specified cgroups version (``1`` or
``2``).

By default, only a small set of cgroup parameters will be recorded, the list of which can be found in
``lib/galaxy/job_metrics/instrumenters/cgroup.py`` in the Galaxy code. The optional ``verbose`` option (default:
``false``) can be set to capture all parameters in the ``cpu``, ``cpuacct``, and ``memory`` controllers (cgroups version
1) or ``cpu`` and ``memory`` controllers (cgroups version 2).

It is also possible to specify exactly which cgroup parameters to capture by setting the optional ``params`` option to a
list of parameter names (files in the controller directory) to capture. For legacy purposes, this can also be a
comma-separated string of cgroup parameter names.

The cgroup plugin works on Linux only.

.. code-block:: yaml

    - type: cgroup
      verbose: false
      version: 2
      params:
        - cpu.stat
        - memory.peak

Overriding the Global Job Metrics Configuration
-----------------------------------------------

Individual Galaxy job config environments (destinations) can disable metric collection by setting the ``metrics`` parameter on that environment:


.. code-block:: yaml

   execution:
     environments:
       example:
         metrics:
           - type: core
           - type: cpuinfo
           - type: meminfo

Alternatively, a file can be specified:

.. code-block:: yaml

   execution:
     environments:
       example:
         metrics:
          src: path
          path: /srv/galaxy/config/metrics_override.yml

Additional accepted values for ``src`` include ``default`` and ``disabled``.

# Connecting to a Cluster

Galaxy is designed to run jobs on your local system by default, but it can be configured to run jobs on a cluster.  The front-end Galaxy application runs on a single server as usual, but tools are run on cluster nodes instead.

A [general reference for the job configuration file](jobs.md) is also available.

## Distributed Resources Managers

Galaxy is known to work with:

* [TORQUE Resource Manager](http://www.adaptivecomputing.com/products/torque/)
* [PBS Professional](https://www.pbsworks.com/PBSProduct.aspx?n=PBS-Professional&c=Overview-and-Capabilities)
* [Open Grid Engine](http://gridscheduler.sourceforge.net/)
* [Univa Grid Engine](http://www.univa.com/products/grid-engine.php) (previously known as Sun Grid Engine and Oracle Grid Engine)
* [Platform LSF](https://www.ibm.com/us-en/marketplace/hpc-workload-management)
* [HTCondor](http://research.cs.wisc.edu/htcondor/)
* [Slurm](https://slurm.schedmd.com/)
* [Galaxy Pulsar](#pulsar) (formerly LWR)

It should also work with [any other DRM](http://www.drmaa.org/implementations.php) which implements a [DRMAA](http://www.drmaa.org) interface. If you successfully run Galaxy with a DRM not listed here, please let us know via an email to the [galaxy-dev mailing list](https://galaxyproject.org/mailing-lists/).

If you do not already have a DRM, [Pulsar](#pulsar) is available which does not require an existing cluster or a shared filesystem and can also run jobs on Windows hosts.

Installing and configuring your cluster hardware and management software is outside the scope of this document (and specific to each site).  That said, a few pitfalls commonly encountered when trying to get the user Galaxy runs as (referred to in this documentation as `galaxy_user`) able to run jobs on the DRM are addressed here:

* The host on which the Galaxy server processes run (referred to in this documentation as `galaxy_server`) should be configured in the DRM as a "submit host".
* `galaxy_user` must have a real shell configured in your name service (`/etc/passwd`, LDAP, etc.).  System accounts may be configured with a disabled shell like `/bin/false` (Debian/Ubuntu) or `/bin/nologin` Fedora/RedHat.
  * If Galaxy is configured to submit jobs as real user (see below) then the above must be true for all users of Galaxy.
* The Galaxy server and the worker nodes are running the same version of Python (worker nodes will run Python scripts calling the Galaxy code and its dependencies to set job output file metadata).

To continue, you should have a working DRM that `galaxy_user` can successfully submit jobs to.

## Preliminary Setup

Galaxy (with the exception of the [Pulsar](#pulsar) runner) currently requires a shared filesystem between the application server and the cluster nodes. There is some legacy code in the PBS runner that does file staging, but its operational status is unknown. The path to Galaxy must be exactly the same on both the nodes and the application server (although it is possible to use symlinks to partially subvert the absolute path requirement). This is because absolute paths are used to refer to datasets and tools when running the command on the cluster node. The shared filesystem and absolute pathnames are limitations that will eventually be removed as development time permits.

For example, if Galaxy is installed like so:

```console
galaxy_user@galaxy_server% git clone https://github.com/galaxyproject/galaxy.git /clusterfs/galaxy/galaxy-app
```


Then that directory should be accessible from all cluster nodes:

```console
galaxy_user@galaxy_server% qsub -I
qsub: waiting for job 1234.torque.server to start
qsub: job 1234.torque.server ready

galaxy_user@node1% cd /clusterfs/galaxy/galaxy-app
galaxy_user@node1%
```


If your cluster nodes have Internet access (NAT is okay) and you want to run the data source tools (upload, ucsc, etc.) on the cluster (doing so is highly recommended), set `new_file_path` in `galaxy.yml` to a directory somewhere in your shared filesystem:

```yaml
new_file_path: /clusterfs/galaxy/tmp
```


Additionally some of the runners including DRMAA may use the ``cluster_files_directory`` for sharing files with the cluster, which defaults to ``database/pbs``. You may need to create this folder.

```yaml
cluster_files_directory: database/pbs
```

You may also find that attribute caching in your filesystem causes problems with job completion since it interferes with Galaxy detecting the presence and correct sizes of output files. In NFS caching can be disabled with the `-noac` mount option on Linux (on the Galaxy server), but this may have a significant impact on performance since all attributes will have to be read from the file server upon every file access. You should try the `retry_job_output_collection` option in `galaxy.yml` first to see if this solves the problem.

## Runner Configuration

**This documentation covers configuration of the various runner plugins, not how to distribute jobs to the various plugins.** Consult the [job configuration file documentation](jobs.md) for full details on the correct syntax, and for instructions on how to configure tools to actually use the runners explained below.

### Local

Runs jobs locally on the Galaxy application server (no DRM).

#### Workers

It is possible to configure the number of concurrent local jobs that can be run by using the `workers` attribute on the plugin.

```xml
<plugins>
    <plugin id="local" type="runner" load="galaxy.jobs.runners.local:LocalJobRunner" workers="8"/>
</plugins>
```


#### Slots

For each destination using the local runner, it is possible to specify the number of CPU slots to assign (default is 1).

```xml
<destinations>
    <destination id="local_1slot" runner="local"/>
    <destination id="local_2slots" runner="local">
        <param id="local_slots">2</param>
    </destination>
</destinations>
```


The value of *local_slots* is used to define [GALAXY_SLOTS](https://galaxyproject.org/admin/config/galaxy_slots/).

### DRMAA

Runs jobs via any DRM which supports the [Distributed Resource Management Application API](http://www.drmaa.org). Most commonly used to interface with [PBS Professional](https://www.pbsworks.com/PBSProduct.aspx?n=PBS-Professional&c=Overview-and-Capabilities), [Sun Grid Engine](http://gridscheduler.sourceforge.net/), [Univa Grid Engine](http://www.univa.com/products/grid-engine.php), [Platform LSF](https://www.ibm.com/us-en/marketplace/hpc-workload-management), and [SLURM](https://slurm.schedmd.com/).

#### Dependencies

Galaxy interfaces with DRMAA via [drmaa-python](https://github.com/pygridtools/drmaa-python). The `drmaa-python` module is provided with Galaxy, but you must tell it where your DRM's DRMAA library is located, via the `$DRMAA_LIBRARY_PATH` environment variable, for example:

```console
galaxy_server% export DRMAA_LIBRARY_PATH=/galaxy/lsf/7.0/linux2.6-glibc2.3-x86_64/lib/libdrmaa.so
galaxy_server% export DRMAA_LIBRARY_PATH=/galaxy/sge/lib/lx24-amd64/libdrmaa.so
```


#### DRM Notes

**Limitations**: The DRMAA runner does not work if Galaxy is configured to run jobs as real user, because in this setting jobs are submitted with an external script, i.e. in an extra DRMAA session, and the session based (python) DRMAA library can only query jobs within the session in which started them. Furthermore, the DRMAA job runner only distinguishes successful and failed jobs and ignores information about possible failure sources, e.g. runtime / memory violation, which could be used for job resubmission. Specialized job runners are abvailable that are not affected by these limitations, e.g. univa and slurm runners.

**TORQUE**: The DRMAA runner can also be used (instead of the [PBS](#pbs) runner) to submit jobs to TORQUE, however, problems have been reported when using the `libdrmaa.so` provided with TORQUE.  Using this library will result in a segmentation fault when the drmaa runner attempts to write the job template, and any native job runner options will not be passed to the DRM.  Instead, you should compile the [pbs-drmaa](http://apps.man.poznan.pl/trac/pbs-drmaa/wiki) library and use this as the value for `$DRMAA_LIBRARY_PATH`.

**Slurm**: You will need to install [slurm-drmaa](https://github.com/natefoo/slurm-drmaa/). In production on [usegalaxy.org](https://usegalaxy.org) we observed pthread deadlocks in slurm-drmaa that would cause Galaxy job handlers to eventually stop processing jobs until the handler was restarted. Compiling slurm-drmaa using the compiler flags `-g -O0` (keep debugging symbols, disable optimization) caused the deadlock to disappear.

#### Parameters and Configuration

Most [options defined in the DRMAA interface](http://www.ogf.org/documents/GFD.143.pdf) are supported.  Exceptions include `remoteCommand`, `jobName`, `outputPath`, and `errorPath` since these attributes are set by Galaxy.  To pass parameters to your underlying DRM, use the `nativeSpecification` parameter.  The format of this parameter is dependent upon the underlying DRM.  However, for Grid Engine, it is the list of command line parameters that would be passed to `qsub(1)`.

```xml
<plugins>
    <plugin id="drmaa" type="runner" load="galaxy.jobs.runners.drmaa:DRMAAJobRunner"/>
</plugins>
<destinations default="sge_default">
    <destination id="sge_default" runner="drmaa"/>
    <destination id="big_jobs" runner="drmaa">
        <param id="nativeSpecification">-P bignodes -R y -pe threads 8</param>
    </destination>
</destinations>
```

### Univa

The so called Univa job runner extends the DRMAA job runner to circumvent the limitations of the DRMAA runner. Despite its name it __may__ be used for various DRMAA based setups in the following cases (currently this has been tested for UNIVA only):

- If jobs run as the Galaxy user it can be used for any DRMAA based system.
- If jobs are not run as Galaxy user (e.g. as real user) then the runner can be used if `qstat` and `qacct` are available to query jobs.

Unlike the DRMAA runner which uses only `drmaa.job_status` to query jobs the Univa runner uses `drmaa.job_status` and `drmaa.wait` if possible and if this fails (e.g. in a real user setting) `qstat` and `qacct` to query jobs.

#### Dependencies, Parameters, and Configuration

All as in the DRMAA runner, in `job_conf.xml` use `galaxy.jobs.runners.univa:UnivaJobRunner` instead of `galaxy.jobs.runners.drmaa:DRMAAJobRunner`.


### PBS

Runs jobs via the [TORQUE Resource Manager](http://www.adaptivecomputing.com/products/torque/). For PBS Pro, use [DRMAA](#drmaa).

#### Dependencies

Galaxy uses the [pbs_python](https://github.com/ehiggs/pbs-python) module to interface with TORQUE.  pbs_python must be compiled against your TORQUE installation, so it cannot be provided with Galaxy. You can install the package as follows:

```console
galaxy_user@galaxy_server% git clone https://github.com/ehiggs/pbs-python
galaxy_user@galaxy_server% cd pbs-python
galaxy_user@galaxy_server% source /clusterfs/galaxy/galaxy-app/.venv/bin/activate
galaxy_user@galaxy_server% python setup.py install
```

As of May 2014 there are still some outstanding bugs in pbs_python. Notably, error code translation is out of alignment.  For example if you get error #15025 "Bad UID for Job Execution" pbs_python will report this error incorrectly as "Queue already exists".  You may consult the [TORQUE source code](https://github.com/adaptivecomputing/torque/blob/4.2.7/src/include/pbs_error_db.h) for the proper error message that corresponds with a given error number.


#### Parameters and Configuration

Most options available to `qsub(1b)` and `pbs_submit(3b)` are supported.  Exceptions include `-o/Output_Path`, `-e/Error_Path`, and `-N/Job_Name` since these PBS job attributes are set by Galaxy.  Parameters can be specified by either their flag (as used with `qsub`) or long name (as used with `pbs_submit`).

```xml
<plugins>
    <plugin id="pbs" type="runner" load="galaxy.jobs.runners.pbs:PBSJobRunner"/>
</plugins>
<destinations default="pbs_default">
    <destination id="pbs_default" runner="pbs"/>
    <destination id="other_cluster" runner="pbs">
        <param id="destination">@other.cluster</param>
    </destination>
    <destination id="long_jobs" runner="pbs">
        <param id="Resource_List">walltime=72:00:00,nodes=1:ppn=8</param>
        <param id="-p">128</param>
    </destination>
</destinations>
```

The value of *ppn=* is used by PBS to define the environment variable `$PBS_NCPUS` which in turn is used by galaxy for [GALAXY_SLOTS](https://galaxyproject.org/admin/config/galaxy_slots/).


### Condor

Runs jobs via the [HTCondor](http://research.cs.wisc.edu/htcondor/) DRM.  There are no configurable parameters.  Galaxy's interface is via calls to HTCondor's command line tools, rather than via an API.

```xml
<plugins>
    <plugin id="condor" type="runner" load="galaxy.jobs.runners.condor:CondorJobRunner"/>
</plugins>
<destinations>
    <destination id="condor" runner="condor"/>
</destinations>
```

Galaxy will submit jobs to HTCondor as the "galaxy" user (or whatever user the Galaxy server runs as).  In order for vanilla job execution to work as expected, your cluster should be configured with a common UID_DOMAIN to allow Galaxy's jobs to run as "galaxy" everywhere (instead of "nobody").

If you need to add additional parameters to your condor submission, you can do so by supplying `<param/>`s:

```xml
<destinations>
    <destination id="condor" runner="condor">
        <param id="Requirements">(machine == some.specific.host)</param>
        <param id="request_cpus">4</param>
    </destination>
</destinations>
```

### Pulsar

Runs jobs via Galaxy [Pulsar](https://pulsar.readthedocs.io/). Pulsar does not require an existing cluster or a shared filesystem and can also run jobs on Windows hosts. It also has the ability to interface with all of the DRMs supported by Galaxy. Pulsar provides a much looser coupling between Galaxy job execution and the Galaxy server host than is possible with Galaxy's native job execution code.


### CLI

Runs jobs via a command-line/shell interface. The CLI runner itself takes plugins of two types:

* Shell: For interacting with different shell types. Plugins for rsh, ssh, and gsi-ssh are provided.
* Job: For interacting with a DRM via the DRM's command-line interface. A plugin for Torque is provided

If you are interested in developing additional plugins, see `lib/galaxy/jobs/runners/util/cli/` for examples.


#### Parameters and Configuration

The cli runner requires, at a minimum, two parameters:

```eval_rst
``shell_plugin``
    This required parameter should be `a cli_shell class <https://github.com/galaxyproject/galaxy/tree/dev/lib/galaxy/jobs/runners/util/cli/shell>`_ currently one of: ``LocalShell``, ``RemoteShell``, ``SecureShell``, ``ParamikoShell``, or ``GlobusSecureShell`` describing which shell plugin to use.

``job_plugin``
    This required parameter should be `a cli_job class <https://github.com/galaxyproject/galaxy/tree/dev/lib/galaxy/jobs/runners/util/cli/job>`_ currently one of ``Torque``, ``SlurmTorque``, or ``Slurm``.
```

All other parameters are specific to the chosen plugins. Parameters to pass to the shell plugin begin with the id `shell_` and parameters to pass to the job plugin begin with the id `job_`.

#### Shell Plugins

The `RemoteShell` plugin uses `rsh(1)` to connect to a remote system and execute shell commands.

```eval_rst
``shell_username``
    Optional user to log in to the remote system as. If unset uses ``rsh``'s default behavior (attempt to log in with the current user's username).

``shell_hostname``
    Remote system hostname to log in to.

``shell_rsh``
    ``rsh``-like command to excute (e.g. ``<param id="shell_rsh">/opt/example/bin/remsh</param>``) - just defaults to ``rst``.
```

The `RemoteShell` parameters translate to a command line of `% <shell_rsh> [-l <shell_username>] <shell_hostname> "<remote_command_with_args>"`, where the inclusion of `-l` is dependent on whether `shell_username` is set. Alternate values for `shell_rsh` must be compatible with this syntax.

The `SecureShell` plugin works like the `RemoteShell` plugin and takes the same parameters, with the following differences:

* The `shell_rsh` default value is `ssh`
* The command line that will be executed is `% <shell_rsh> -oStrictHostKeyChecking=yes -oConnectTimeout=60 [-l <shell_username>] <shell_hostname> "<remote_command_with_args>"`

The `GlobusSecureShell` plugin works like the `SecureShell` plugin and takes the same parameters, with the following difference:

* The `shell_rsh` default value is `gsi-ssh`

The ``ParamikoShell`` option was added in 17.09 with this pull request https://github.com/galaxyproject/galaxy/pull/4358 from Marius van den Beek.

#### Job Plugins

The `Torque` plugin uses `qsub(1)` and `qstat(1)` to interface with a Torque server on the command line.

```eval_rst
``job_<PBS_JOB_ATTR>``
    ``<PBS_JOB_ATTR>`` refers to a ``qsub(1B)`` or ``pbs_submit(3B)`` argument/attribute
    (e.g. ``<param id="job_Resource_List">walltime=24:00:00,ncpus=4</param>``).
```

Torque attributes can be defined in either their short (e.g. [qsub(1B)](http://cf.ccmr.cornell.edu/cgi-bin/w3mman2html.cgi?qsub(1B)) argument as used on the command line or in a script as `#PBS -<ARG>`) or long (e.g. [pbs_submit(3B)](http://cf.ccmr.cornell.edu/cgi-bin/w3mman2html.cgi?pbs_submit(3B)) attribute as used in the C library) oforms. Some additional examples follow:

* `<param id="job_-q">queue</param>`: set the PBS destination (in this example, a queue), equivalent to `<param id="job_destination">queue</param>`
* `<param id="job_Priority">128</param>`: set the job priority, equivalent to `<param id="job_-p">128</param>`

```xml
<plugins>
    <plugin id="cli" type="runner" load="galaxy.jobs.runners.cli:CLIJobRunner"/>
</plugins>
<destinations default="cli_default">
    <destination id="cli_default" runner="cli">
        <param id="shell_plugin">SecureShell</param>
        <param id="job_plugin">Torque</param>
        <param id="shell_hostname">cluster.example.org</param>
    </destination>
    <destination id="long_jobs" runner="cli">
        <param id="job_Resource_List">walltime=72:00:00,nodes=1:ppn=8</param>
        <param id="job_-p">128</param>
    </destination>
</destinations>
```


Most options available to `qsub(1b)` and `pbs_submit(3b)` are supported.  Exceptions include `-o/Output_Path`, `-e/Error_Path`, and `-N/Job_Name` since these PBS job attributes are set by Galaxy.

## Submitting Jobs as the Real User

Galaxy runs as a process on your server as whatever user starts the server - usually an account created for the purpose of running Galaxy. Jobs will be submitted to your cluster(s) as this user. In environments where users in Galaxy are guaranteed to be users on the underlying system (i.e. Galaxy is configured to use external authentication), it may be desirable to submit jobs to the cluster as the user logged in to Galaxy rather than Galaxy's system user.

### Caveats

Since this is a complex problem, the current solution does have some caveats:

* All of the datasets stored in Galaxy will have to be readable on the underlying filesystem by all Galaxy users. Said users need not have direct access to any systems which mount these filesystems, only the ability to run jobs on clusters that mount them. But I expect that in most environments, users will have the ability to submit jobs to these clusters or log in to these clusters outside of Galaxy, so this will be a security concern to evaluate for most environments.
  * *Technical details* - Since Galaxy maintains dataset sharing internally and all files are owned by the Galaxy user, when running jobs only under a single user, permissions can be set such that only the Galaxy user can read all datasets. Since the dataset may be shared by multiple users, it is not suitable to simply change ownership of inputs before a job runs (what if another user tried to use the same dataset as an input during this time?). This could possibly be solved if Galaxy had tight control over extended ACLs on the file, but since many different ACL schemes exist, Galaxy would need a module for each scheme to be supported.
* The real user system works by changing ownership of the job's working directory to the system prior to running the job, and back to the Galaxy user once the job has completed. It does this by executing a site-customizable script via [sudo](https://www.sudo.ws/).
  * Two possibilities to determine the system user that corresponds to a galaxy user are implemented: i) the user whos name matches the Galaxy user's email address (with the @domain stripped off) and ii) the user whos name is equal to the galaxy user name. Until release 17.05 only the former option is available. The latter option is suitable for Galaxy installations that user external authentification (e.g. LDAP) against a source that is also the source of the system users.
  * The script accepts a path and does nothing to ensure that this path is a Galaxy working directory per default (and not at all up to release 17.05). So anyone who has access to the Galaxy user could use this script and sudo to change the ownership of any file or directory. Furthermore, anyone with write access to the script could introduce arbitrary (harmful) code -- so it might be a good idea to give write access only to trustworthy users, e.g., root.

### Configuration

You'll need to ensure that all datasets are stored on the filesystem such that they are readable by all users that will use Galaxy: either made readable by a group, or world-readable. If using a group, set your `umask(1)` to `027` or for world-readable, use `022` Setting the umask assumes your underlying filesystem uses POSIX permissions, so if this is not the case, your environment changes may be different.

The directory specified in `new_file_path` in the Galaxy config should be world-writable, cluster-accessible (via the same absolute path) and have its sticky bit (+t) set. This directory should also be cleaned regularly using a script or program as is appropriate for your site, since temporary files created here may not always be cleaned up under certain conditions.

The `outputs_to_working_directory` option in the Galaxy config **must** be set to `True`. This ensures that a tool/job's outputs are written to the temporary working directory, which (when using the real user system) is owned by the real user who submitted the job. If left set to the default (`False`), the tool will attempt to write directly to the directory specified in `file_path` (by default, `database/files/`), which must be owned by the Galaxy user (and thus will not be writable by the real user).

For releases later than 17.05 you can configure the method how the system user is determined in `config/galaxy.yml` via the variable `real_system_username`. For determining the system user from the email adress stored in Galaxy set it to `user_email`, otherwise for determining the system user from the Galaxy user name set it to `username`.

Once these are set, you must set the `drmaa_external_*` and `external_chown_script` settings in the Galaxy config and configure `sudo(8)` to allow them to be run. A sudo config using the three scripts set in the sample `galaxy.yml` would be:

```
galaxy  ALL = (root) NOPASSWD: SETENV: /opt/galaxy/scripts/drmaa_external_runner.py
galaxy  ALL = (root) NOPASSWD: SETENV: /opt/galaxy/scripts/drmaa_external_killer.py
galaxy  ALL = (root) NOPASSWD: SETENV: /opt/galaxy/scripts/external_chown_script.py
```

If your sudo config contains `Defaults    requiretty`, this option must be disabled.

For Galaxy releases > 17.05, the sudo call has been moved to `galaxy.yml` and is thereby configurable by the Galaxy admin. This can be of interest because sudo removes `PATH`, `LD_LIBRARY_PATH`, etc. variables per default in some installations. In such cases the sudo calls in the three variables in galaxy.yml can be adapted, e.g., `sudo -E PATH=... LD_LIBRARY_PATH=... /PATH/TO/GALAXY/scripts/drmaa_external_runner.py`. In order to allow setting the variables this way adaptions to the sudo configuration might be necessary. For example, the path to the python inside the galaxy's python virtualenv may have to be inserted before the script call to make sure the virtualenv is used for drmaa submissions of real user jobs.

```
drmaa_external_runjob_script: sudo -E .venv/bin/python scripts/drmaa_external_runner.py --assign_all_groups
```

Also for Galaxy releases > 17.05: In order to allow `external_chown_script.py` to chown only path below certain entry points the variable `ALLOWED_PATHS` in the python script can be adapted. It is sufficient to include the directorries `job_working_directory` and `new_file_path` as configured in `galaxy.yml`.

It is also a good idea to make sure that only trusted users, e.g. root, have write access to all three scripts.

Some maintenance and support of this code will be provided via the usual [Support](https://galaxyproject.org/support/) channels, but improvements and fixes would be greatly welcomed, as this is a complex feature which is not used by the Galaxy Development Team.

## Special environment variables for job resources

Galaxy *tries* to define special environment variables for each job that contain
the information on the number of available slots and the amount of available
memory:

* `GALAXY_SLOTS`: number of available slots
* `GALAXY_MEMORY_MB`: total amount of available memory in MB
* `GALAXY_MEMORY_MB_PER_SLOT`: amount of memory that is available for each slot in MB

More precisely Galaxy inserts bash code in the job submit script that
tries to determine these values. This bash code is defined here:

* lib/galaxy/jobs/runners/util/job_script/CLUSTER_SLOTS_STATEMENT.sh
* lib/galaxy/jobs/runners/util/job_script/MEMORY_STATEMENT.sh

If this code is unable to determine the variables, then they will not be set.
Therefore in the tool XML files the variables should be used with a default,
e.g. `\${GALAXY_SLOTS:-1}` (see also https://planemo.readthedocs.io/en/latest/writing_advanced.html#cluster-usage).

In particular `GALAXY_MEMORY_MB` and `GALAXY_MEMORY_MB_PER_SLOT` are currently
defined only for a few cluster types. Contributions are very welcome, e.g. let
the Galaxy developers know how to modify that file to support your cluster.

## Contributors

* **Oleksandr Moskalenko**, debugged a number of problems related to running jobs as the real user and using DRMAA with TORQUE.
* **Jaime Frey**, developer of the HTCondor job runner plugin.
* **Ilya Chorny**, developer of the original "real user" job running code.

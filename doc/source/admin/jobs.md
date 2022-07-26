# Galaxy Job Configuration

By default, jobs in Galaxy are run locally on the server on which the Galaxy application was started.  Many options are available for running Galaxy jobs on other systems, including clusters and other remote resources.

This document is a reference for the job configuration file. [Detailed documentation](cluster.md) is provided for configuring Galaxy to work with a variety of Distributed Resource Managers (DRMs) such as TORQUE, Grid Engine, LSF, and HTCondor.  Additionally, a wide range of infrastructure decisions and configuration changes should be made when running Galaxy as a production service, as one is likely doing if using a cluster.  It is highly recommended that the [production server documentation](production.md) and [cluster configuration documentation](cluster.md) be read before making changes to the job configuration.

**The most up-to-date details of advanced job configuration features can be found in the [sample job_conf.xml](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/config/sample/job_conf.xml.sample_advanced) found in the Galaxy distribution.**

Configuration of where to run jobs is performed in the `job_conf.xml` file in `$GALAXY_ROOT/config/`.  The path to the config file can be overridden by setting the value of `job_config_file` in `config/galaxy.yml`.  Sample configurations are provided at `config/job_conf.xml.sample_basic` and `config/job_conf.xml.sample_advanced`.  The job configuration file is not required - if it does not exist, a default configuration that runs jobs on the local system (with a maximum of 4 concurrent jobs) will be used.  `job_conf.xml.sample_basic` provides a configuration identical to the default configuration if no `job_conf.xml` exists.

## job_conf.xml Syntax

The root element is `<job_conf>`.

### Job Runner Plugins

The `<plugins>` collection defines job runner plugins that should be loaded when Galaxy starts.

This configuration element may define a ``workers`` parameters which is the default number of worker threads to spawn for doing runner plugin "work", e.g. doing job preparation, post-processing, and cleanup. The default number of such workers is ``4``.

The collection contains `<plugin>` elements. Each ``plugin`` element may define the following parameters.

```eval_rst
id
    ``id`` of the runner plugin referenced in ``destination`` configuration elements.

type
    This must be ``runner`` currently.

load
    Python module containing the plugin, and the class to instantiate.  If no class name is provided, the module must list class names to load in a module-level ``__all__`` list.
    For example ``galaxy.jobs.runners.local:LocalJobRunner``.

workers
    Number of worker threads to start for this plugin only (defaults to the value specified
    on ``plugins`` configuration).
```

### Job Handlers

The `<handlers>` configuration elements defines which Galaxy server processes (when [running multiple server processes](scaling.md)) should be used for running jobs, and how to group those processes.

The handlers configuration may define a ``default`` attribute. This is the the handler(s) that should be used if no explicit handler is defined for a job. If unset, any untagged handlers will be used by default.

The collection contains `<handler>` elements.

```eval_rst
id
    A server name that should be used to run jobs. Server names are dependent on your application server deployment scenario and are explained in the :ref:`configuration section of the scaling documentation <scaling-configuration>`.

tags
    A comma-separated set of strings that optional define tags to which this handler belongs.
```

### Job Destinations

The `<destinations>` collection defines the parameters that should be used to run a job that is sent to the specified destination. This configuration element should define a ``default``
attribute that should be the ``id`` of the ``destination`` to used if no explicit destination is defined for a job.

The collection contains `<destination>`s, which are can be collections or single elements.

```eval_rst
id
    Identifier to be referenced in ``<tool>`` configuration elements in the ``tools`` section.

runner
    Job runner ``plugin`` to be used to run jobs sent to this destination.

tags
    Tags to which this destination belongs (for example `tags="longwalltime,bigcluster"`).
```

``destination`` elements may contain zero or more ``<param>``s, which are passed to the destination's defined runner plugin and interpreted in a way native to that plugin. For details on the parameter specification, see the documentation on [Cluster configuration](cluster.md).

### Environment Modifications

As of the June 2014 release, destinations may contain additional `env` elements to configure the environment for jobs on that resource. These each map to shell commands that will be injected to Galaxy's job script and executed on the destination resource.

```eval_rst
id
    Environment variable to set (in this case text of element is value this is set to
    (e.g. ``id="_JAVA_OPTIONS"``).

file
    Optional path to script File will be sourced to configure environment
    (e.g. ``file="/mnt/java_cluster/environment_setup.sh"``).

exec
    Optional shell command to execute to configure environment
    (e.g. ``module load javastuff/2.10``)

raw
    Disable auto-quoting of values when setting up environment variables.
```

Destinations may also specify other destinations (which may be dynamic destinations) that jobs should be resubmitted to if they fail to complete at the first destination for certain reasons. This is done with the `<resubmit>` tag contained within a `<destination>`.

```eval_rst
condition
    Failure expression on which to resubmit jobs - this Python expression may contain
    the boolean variables ``memory_limit_reached``, ``walltime_reached``,
    ``unknown_error``, or ``any_failure`` and the numeric variables ``seconds_running``
    and ``attempt``. See the test case configuration https://github.com/galaxyproject/galaxy/blob/dev/test/integration/resubmission_job_conf.xml for examples of various expressions.

handler
    Job handler(s) that should be used to run jobs for this tool after resubmission.

destination
    Job destination(s) that should be used to run jobs for this tool after resubmission.
```

**Note:** Currently, failure conditions for memory limits and walltime are only implemented for the [Slurm](cluster.md) job runner plugin. Contributions for other implementations would be greatly appreciated! An example job configuration and an always-fail job runner plugin for development [can be found in this gist](https://gist.github.com/natefoo/361414fbca3c0ea63aa5).


### Running jobs in containers

Galaxy can be configured to run jobs in container runtimes. Currently the two supported runtimes are [Docker](https://www.docker.com) and [Singularity](https://www.sylabs.io/). Each ``<destination>`` can enable container support
with ``<param id="docker_enabled">true</param>`` and/or ``<param id="singularity_enabled">true</param>``, as documented
in the [advanced sample job_conf.xml](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/config/sample/job_conf.xml.sample_advanced).
In the case of Docker, containers are run using **sudo** unless ``<param id="docker_sudo">false</param>`` is specified, thus
the user that Galaxy runs as should be able to run ``sudo docker`` without a password prompt for Docker containers to
work.

The images used for containers can either be specified explicitely in the ``<destination>`` using the *docker_default_container_id*, *docker_container_id_override*, *singularity_default_container_id* and
*singularity_container_id_override* parameters, but (perhaps more commonly) the image to use can be derived from the
tool requirements of the Galaxy tool being executed. In this latter case the image is specified by the
tool using a ``<container>`` tag in the ``<requirements>`` section.

### Running jobs on a Kubernetes cluster via Pulsar

In order to dispatch jobs to a Kubernetes (K8s) cluster via Pulsar,
Pulsar implements a "two-container" architecture per pod, where
one container stages job execution environment (`pulsar-container`)
and another container encompasses tool's executables (`tool-container`).

Note that this architecture is experimental and under active development,
it is increasingly improved and it will soon be production-grade ready.

In order to setup Galaxy to use the "two-container" architecture, you may
take the following steps:

1. In the `galaxy.yml` set the following attributes: 

- `job_config_file: job_conf.yml`
- Appropriately configure `galaxy_infrastructure_url`; for example,
set it as the following on macOS:
`galaxy_infrastructure_url: 'http://host.docker.internal:$GALAXY_WEB_PORT'`

2. In the `job_conf.yml` set the following runners and execution attributes appropriately:

```yaml
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    workers: 1
  pulsar_k8s:
    load: galaxy.jobs.runners.pulsar:PulsarKubernetesJobRunner
    amqp_url: amqp://guest:guest@localhost:5672//

execution:
  default: pulsar_k8s_environment
  environments:
    pulsar_k8s_environment:
      k8s_config_path: ~/.kube/config
      k8s_galaxy_instance_id: any-dns-friendly-random-str
      k8s_namespace: default
      runner: pulsar_k8s
      docker_enabled: true
      docker_default_container_id: busybox:ubuntu-14.04
      pulsar_app_config:
        message_queue_url: 'amqp://guest:guest@host.docker.internal:5672//'
    local_environment:
      runner: local
```

### Macros

The job configuration XML file may contain any number of macro definitions using the same
XML macro syntax used by [Galaxy tools](https://planemo.readthedocs.io/en/latest/writing_advanced.html#macros-reusable-elements).

See [Pull Request #362](https://github.com/galaxyproject/galaxy/pull/362) for implementation details and the [advanced sample job_conf.xml](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/config/sample/job_conf.xml.sample_advanced) for examples.

## Mapping Tools To Destinations

### Static Destination Mapping

The `<tools>` collection provides a mapping from tools to a destination (or collection of destinations identified by tag) and handler (or collection of handlers).  Any tools not matching an entry in the collection will use the default handler and default destination as explained above.

The `<tools>` collection has no attributes.

The collection contains `<tool>`s, which are can be collections or single elements.

```eval_rst
id
    ``id`` attribute of a Galaxy tool. Valid forms include the short ``id``` as found in the Tool's XML configuration, a full Tool Shed GUID, or a Tool Shed GUID without the version component (for example ``id="toolshed.example.org/repos/nate/filter_tool_repo/filter_tool/1.0.0"`` or ``id="toolshed.example.org/repos/nate/filter_tool_repo/filter_tool"`` or ``id="filter_tool"``).

handler
    Job handler(s) that should be used to run jobs for this tool.
    (e.g. ``handler="handler0"`` or ``handler="ngs"``). This is optional and if unspecified
    will default to the handler specified as the default handler in the job configuration or
    the only job handler if only one is specified.

destination
    Job destination(s) that should be used to run jobs for this tool (e.g. ``destination="galaxy_cluster"`` or ``destination="long_walltime"``). The is optional
    and defaults the default destination.
```

Tool collections contain zero or more `<param>`s, which map to parameters set at job-creation, to allow for assignment of handlers and destinations based on the manner in which the job was created.  Currently, only one parameter is defined - namely ``source``.

The *content* of the `<param id="source">` tag is the component that created the job.  Currently, only Galaxy's visualization component sets this job parameter, and its value is `trackster`.

```xml
<param id="source">trackster</param>
```

### Dynamic Destination Mapping

Galaxy has very sophisticated job configuration options that allow different tools to be submitted to queuing systems with various parameters and in most cases this is sufficient. However, sometimes it is necessary to have job execution parameters be determined at runtime based on factors such as the job inputs, user submitting the job, cluster status, etc...  In these cases the dynamic job destination mechanism allows the deployer to describe how the job should be executed using python functions. There are various flavors of dynamic destinations to handle these scenarios.

The two most generic and useful dynamic destination types are `python` and `dtd`. The `python` type allows arbitrary Python functions to define destinations for jobs, while the DTD method (introduced in Galaxy 16.07) defines rules for routing in a YAML file.

#### Dynamic Destination Mapping (DTD method)

DTD is a special dynamic job destination type that builds up rules given a YAML-based DSL - see `config/tool_destinations.yml.sample` (on [Github](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/config/sample/tool_destinations.yml.sample)) for a syntax description, examples, and a description of how to validate and debug this file.

To define and use rules, copy this sample file to `config/tool_destinations.yml` and add your rules. Anything routed with a `dynamic` runner of type `dtd` will then use this file (such as the destination defined with the following XML block in `job_conf.xml`).

```xml
    <destination id="dtd_destination" runner="dynamic">
      <param id="type">dtd</param>
    </destination>
```

#### Dynamic Destination Mapping (Python method)

The simplest way to get started with dynamic job destinations is to first create a dynamic job destination in `job_conf.xml`'s `<destinations>` section:

```xml
    <destination id="blast" runner="dynamic">
      <param id="type">python</param>
      <param id="function">ncbi_blastn_wrapper</param>
    </destination>
```


Note that any parameters defined on dynamic destinations are only available to the function. If your function dispatches to a static destination, parameters are not propagated automatically.

Next for any tool one wants to dynamically assign job destinations for, this `blast` dynamic destination must be specified in the `job_conf.xml`'s `<tools>` section:

```xml
    <tool id="ncbi_blastn_wrapper" destination="blast" />
```

Finally, you will need to define a function that describes how `ncbi_blastn_wrapper` should be executed. To do this, one must create a python source file in `lib/galaxy/jobs/rules`, for instance `destinations.py` (though the name of this file is largely unimportant, one can distribute any number of functions across any number of files and they will be automatically detected by Galaxy).

So open `lib/galaxy/jobs/rules/destinations.py` and define a `ncbi_blastn_wrapper` function. A couple possible examples may be:

```python
from galaxy.jobs import JobDestination
import os

def ncbi_blastn_wrapper(job):
    # Allocate extra time
    inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
    inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
    query_file = inp_data[ "query" ].file_name
    query_size = os.path.getsize( query_file )
    if query_size > 1024 * 1024:
        walltime_str = "walltime=24:00:00/"
    else:
        walltime_str = "walltime=12:00:00/"
    return JobDestination(id="ncbi_blastn_wrapper", runner="pbs", params={"Resource_List": walltime_str})

```

or

```python
from galaxy.jobs import JobDestination
import os

def ncbi_blastn_wrapper(app, user_email):
     # Assign admin users' jobs to special admin_project.
     admin_users = app.config.get( "admin_users", "" ).split( "," )
     params = {}
     if user_email in admin_users:
         params["nativeSpecification"] = "-P bigNodes"
    return JobDestination(id="ncbi_blastn_wrapper", runner="drmaa", params=params)
```


The first example above delegates to the PBS job runner and allocates extra walltime for larger input files (based on tool input parameter named `query`). The second example delegates to the DRMAA job runner and assigns users in the in the admin list to a special project (perhaps configured to have a higher priority or extended walltime).

The above examples demonstrate that the dynamic job destination framework will pass in the arguments to your function that are needed based on the argument names. The valid argument names at this time are:

```eval_rst
``app``
    Global Galaxy application object, has attributes such as config (the configuration parameters loaded from ``config/galaxy.yml``) and ``job_config`` (Galaxy representation of the data loaded in from ``job_conf.xml``).

``user_email``
    E-mail of user submitting this job.

``user``
    Galaxy model object for user submitting this job.

``job``
    Galaxy model object for submitted job, see the above example for how input information can be derived from this.

``job_wrapper``
    An object meant a higher level utility for reasoning about jobs than ``job``.

``tool``
    Tool object corresponding to this job.

``tool_id``
    ID of the tool corresponding to this job

``rule_helper``
    Utility object with methods designed to allow job rules to interface cleanly with the rest of Galaxy and shield them from low-level details of models, metrics, etc....

``resource_params``
    A dictionary of parameters specified by the user using ``job_resource_params_conf.xml`` (if configured).

``workflow_invocation_uuid``
    A randomly generated UUID for the workflow invocation generating this job - this can be
    useful for instance in routing all the jobs in the same workflow to one resource.
```

Also available though less likely useful are ``job_id``.

The above examples demonstrated mapping one tool to one function. Multiple tools may be mapped to the same function, by specifying a function the the dynamic destination:

```xml
    <destination id="blast_dynamic" runner="dynamic">
      <param id="type">python</param>
      <param id="function">blast_dest</param>
    </destination>
```


```xml
    <tool id="ncbi_blastn_wrapper" destination="blast_dynamic" />
    <tool id="ncbi_blastp_wrapper" destination="blast_dynamic" />
    <tool id="ncbi_tblastn_wrapper" destination="blast_dynamic" />
```

In this case, you would need to define a function named `blast_dest` in your python rules file and it would be called for all three tools. In cases like this, it may make sense to take in `tool_id` or `tool` as argument to factor the actual tool being used into your decision.

As a natural extension to this, a dynamic job runner can be used as the default destination. The below examples demonstrate this and other features such as returning mapping failure messages to your users and defaulting back to existing static destinations defined in `job_conf.xml`.

##### Additional Dynamic Job Destination Examples

The following example assumes the existence of a job destination with ids `short_pbs` and `long_pbs` and that a default dynamic job runner has been defined as follows in `job_conf.xml`:

```xml
  <destinations default="dynamic">
    <destination id="dynamic">
      <param id="type">python</param>
      <param id="function">default_runner</param>
    <destination>
    ...
```

With these if place, the following `default_runner` rule function will route all tools with id containing `mothur` to the `long_pbs` destination defined `jobs_conf.xml` and all other tools to the `short_pbs` destination:

```python
def default_runner(tool_id):
    if 'mothur' in tool_id:
        return 'long_pbs'
    else:
        return 'short_pbs'
```


As another example, assume that a few tools should be only accessible to developers and all other users should receive a message indicating they are not authorized to use this tool. This can be accomplished with the following `job_conf.xml` fragment

```xml
  <destinations default="dynamic">
    <destination id="dev_dynamic">
      <param id="type">python</param>
      <param id="function">dev_only</param>
    <destination>
    ...
  <tools>
    <tool id="test1" destination="dev_dynamic" />
    <tool id="test2" destination="dev_dynamic" />
    ...
```


Coupled with placing the following function in a rules file.

```python
from galaxy.jobs.mapper import JobMappingException
from galaxy.jobs import JobDestination
DEV_EMAILS = ["mary@example.com"]

def dev_only(user_email):
    if user_email in DEV_EMAILS
       return JobDestination(id="dev_only", runner="drmaa")
    else:
       raise JobMappingException("This tool is under development and you are not authorized to it.")
```


There is an additional page on [Access Control](https://galaxyproject.org/admin/config/access-control/) for those interested.

##### Additional Tricks

If one would like to tweak existing static job destinations in just one or two parameters, the following idiom can be used to fetch static JobDestination objects from Galaxy in these rule methods - `dest = app.job_config.get_destination( id_or_tag )`.

## Limiting Job Resource Usage

The `<limits>` collection defines the number of concurrent jobs users can run, output size limits, and a Galaxy-specific limit on the maximum amount of time a job can run (rather than relying on a DRM's time-limiting feature).  This replaces the former `job_walltime`, `output_size_limit`, `registered_user_job_limit`, `anonymous_user_job_limit` configuration parameters, as well as the (mostly broken) `[galaxy:job_limits]` section.

*NB: The `job_walltime` and `output_size` limits are only implemented in the `local` and `pbs` job runner plugins.  Implementation in other runners is likely to be fairly easy and would simply require a bit of testing - we would gladly accept a pull request implementing these features in the other provided runner plugins.*

The `<limits>` collection has no attributes.

The collection contains `<limit>`s, which have different meanings based on their required `type` attribute:

```eval_rst
``type``
    Type of limit to define - one of ``registered_user_concurrent_jobs``, ``anonymous_user_concurrent_jobs``, ``destination_user_concurrent_jobs``, ``destination_total_concurrent_jobs``, ``walltime``, and ``output_size``.

``id``
    Optional destination on which to apply limit (for ``destination_user_concurrent_jobs`` and ``destination_total_concurrent_jobs`` types only) (e.g. ``id="galaxy_cluster"``).

``tag``
    Optional destinations on which to apply limit (for ``destination_user_concurrent_jobs`` and ``destination_total_concurrent_jobs`` types only).
```

If a limit tag is defined, its value must be set.  If the limit tag is not defined, the default for each type is unlimited.  The syntax for the available `type`s are:

```eval_rst
``registered_user_concurrent_jobs``
    Limit on the number of jobs a user with a registered Galaxy account can have active across all destinations.

``anonymous_user_concurrent_jobs``
    Limit on the number of jobs an unregistered/anonymous user can have active across all destinations.

``destination_user_concurrent_jobs``
    The number of jobs a user can have active in the specified destination, or across all destinations identified by the specified tag.

``destination_total_concurrent_jobs``
    The number of jobs that can be active in the specified destination (or across all destinations identified by the specified tag) by any/all users.

``walltime``
    Amount of time a job can run (in any destination) before it will be terminated by Galaxy.

``total_walltime``
    Total walltime that jobs may not exceed during a set period. If total walltime of finished
    jobs exceeds this value, any new jobs are paused. This limit should include a ``window``
    attribute that is the number in days representing the period.

``output_size``
    Size that any defined tool output can grow to before the job will be terminated. This does not include temporary files created by the job (e.g. ``53687091200`` for 50 GB).
```

The concept of "across all destinations" is used because Galaxy allows users to run jobs across any number of local or remote (cluster) resources.  A user may always queue an unlimited number of jobs in Galaxy's internal job queue.  The concurrency limits apply to jobs that have been dispatched and are in the `queued` or `running` states.  These limits prevent users from monopolizing the resources Galaxy runs on by, for example, preventing a single user from submitting more long-running jobs than Galaxy has cluster slots to run and subsequently blocking all Galaxy jobs from running for any other user.

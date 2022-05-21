# Scaling and Load Balancing

The Galaxy framework is written in Python and makes extensive use of threads.  However, one of the drawbacks of Python
is the [Global Interpreter Lock](http://docs.python.org/c-api/init.html#thread-state-and-the-global-interpreter-lock),
which prevents more than one thread from being on CPU at a time.  Because of this, having a multi-core system will not
improve the Galaxy framework's performance out of the box since Galaxy can use (at most) one core at a time in its
default configuration.  However, Galaxy can easily run in multiple separate processes, which solves this problem.  For a
more thorough explanation of this problem and why you will almost surely want to switch to the multiprocess
configuration if running for more than a small handful of users, see the [production configuration](production.md)
page.

Just to be clear: Increasing the number of plugin workers in `job_conf.xml` will not make your Galaxy server much more responsive.
The key to scaling Galaxy is the ability to run *multiple* Galaxy servers which co-operatively work on the same database.

## Terminology

* **web worker** - Galaxy server process responsible for servicing web requests for the UI/API
* **job handler** - Galaxy server process responsible for setting up, starting, and monitoring jobs, submitting jobs to
  a cluster (if configured), for setting metadata (if not set on the cluster), and cleaning up after jobs
  * **tags** - Handlers can be grouped in to a "pool" of handlers using *tags*, after which, individual tools may be
    mapped to a handler tag such that all executions of that tool are handled by the tagged handler(s).
  * **default** - Any handlers without defined tags - aka "untagged handlers" - will handle executions of all tools
    not mapped to a specific handler ID or tag.
* **Webless Galaxy application** - The Galaxy application run as a standalone Python application with no web/ASGI server

## Application Servers

It is possible to run the Galaxy server in many different ways, including under different web application frameworks, or
as a standalone server with no web stack.

Starting with the 22.01 release the default application server is [Gunicorn][Gunicorn].
Gunicorn serves Galaxy as an ASGI web application.

### Historical note

Prior to the 18.01 release, Galaxy (by default) used the [Python Paste][paste] web stack, and ran in a single process.
Between the 18.01 release and the 22.01 release, [uWSGI](https://uwsgi-docs.readthedocs.io/) was used as the default
application server.
In release 22.05 we dropped support for running Galaxy as a WSGI application via uWSGI or paste.
For more information about this, please consult the version of this document that is
appropriate to your Galaxy release.

[Gunicorn]: https://gunicorn.org/
[paste]: https://paste.readthedocs.io/

## Deployment Options

There are multiple deployment strategies for the Galaxy application that you can choose from. The right one depends on
the configuration of the infrastructure on which you are deploying. In all cases, all Galaxy job features such as
[running on a cluster](cluster.md) are supported.

Although Gunicorn implements many features that were previously the responsibility of an upstream proxy server,
it is recommended to place a proxy server in front of Gunicorn and utilize it for all of its traditional
roles (serving static content, serving dataset downloads, etc.) as described in the [production
configuration](production.md) documentation.

### Gunicorn with jobs handled by web workers (default configuration)

Referred to in this documentation as the **all-in-one** strategy.

* Job handlers and web workers are the same processes and cannot be separated
* A random web worker will be the job handler for that job

Under this strategy, jobs will be handled by Gunicorn workers. Having web processes handle jobs will negatively impact
UI/API performance.

This is the default out-of-the-box configuration.

### Gunicorn for web serving and Webless Galaxy applications as job handlers

Referred to in this documentation as the **Gunicorn + Webless** strategy.

* Job handlers are started as standalone Python applications with no web stack
* Jobs are dispatched from web workers to job handlers via the Galaxy database
* Jobs can be dispatched to job handlers running on any host
* Additional job handlers can be added dynamically without reconfiguring/restarting Galaxy (19.01 or later)
* The recommended deployment strategy for production Galaxy instances

By default, handler assignment will occur using the **Database Transaction Isolation** or **Database SKIP LOCKED**
methods (see below).

## Job Handler Assignment Methods

Job handler assignment methods are configurable with the `assign_with`
attribute on the `<handlers>` tag in `job_conf.xml`.  The available methods are:

* **Database Transaction Isolation** (`db-transaction-isolation`, new in 19.01) - Jobs are assigned a handler by handlers selecting the unassigned
  job from the database using SQL transaction isolation, which uses database locks to guarantee that only one handler
  can select a given job. This occurs by the web worker that receives the tool execution request (via the UI or API)
  setting a new job's 'handler' column in the database to the configured tag/default (or `_default_` if no tag/default
  is configured). Handlers "listen" for jobs by selecting jobs from the database that match the handler tag(s) for which
  they are configured. `db-transaction-isolation` is the default assignment method if no handlers are defined,
  or handlers are defined but no `assign_with` attribute is set on the `handlers` tag and *Database SKIP LOCKED* is not available.

* **Database SKIP LOCKED** (`db-skip-locked`, new in 19.01) - Jobs are assigned a handler by handlers selecting the unassigned job from
  the database using `SELECT ... FOR UPDATE SKIP LOCKED` on databases that support this query (see the next section for
  details). This occurs via the same process as *Database Transaction Isolation*, the only difference is the way in
  which handlers query the database. This is the default if no handlers are defined, or handlers are defined but no `assign_with` attribute is set
  on the `handlers` tag and *Database SKIP LOCKED* is available.

* **Database Self Assignment** (`db-self`) - Like *In-memory Self Assignment* but assignment occurs by setting a new job's 'handler'
  column in the database to the process that created the job at the time it is created. Additionally, if a tool is
  configured to use a specific handler (ID or tag), that handler is assigned (tags by *Database Preassignment*). This is
  the default fallback if no handlers are defined and the database does not support *Database SKIP LOCKED* or *Database Transaction Isolation*.

* **In-memory Self Assignment** (`mem-self`) - Jobs are assigned to the web worker that received the tool execution request from the
  user via an internal in-memory queue. If a tool is configured to use a specific handler, that configuration is
  ignored; the process that creates the job *always* handles it. This can be slightly faster than **Database Self
  Assignment** but only makes sense in single process environments without dedicated job handlers. This option
  supersedes the former `track_jobs_in_database` option in `galaxy.yml` and corresponds to setting that option to
  `false`.

* **Database Preassignment** (`db-preassign`) - Jobs are assigned a handler by selecting one at random from the configured tag or default
  handlers at the time the job is created. This occurs by the web worker that receives the tool execution request (via
  the UI or API) setting a new job's 'handler' column in the database to the randomly chose handler ID (hence
  "preassignment"). This is the default only if handlers are defined and the database does not support *Database SKIP LOCKED* or *Database Transaction Isolation*.

In all cases, if a tool is configured to use a specific handler (by ID, not tag), configured assignment methods are
ignored and that handler is directly assigned in the job's 'handler' column at job creation time.

See the `config/job_conf.xml.sample_advanced` file in the Galaxy distribution for instructions on setting the
assignment method.

### Choosing an Assignment Method

Prior to Galaxy 19.01, the most common deployment strategies assigned handlers using what is
now (since 19.01) referred to as *Database Preassignment*.  Although still a fallback option when the database
does not support *Database SKIP LOCKED* or *Database Transaction Isolation*, preassignment has a few drawbacks:

* Web workers do not have a way to know whether a particular handler is alive when assigning that handler
* Jobs are not load balanced across handlers
* Changing the number of handlers requires changing `job_conf.xml` and restarting *all* Galaxy processes

The "database locking" methods (*Database SKIP LOCKED* and *Database Transaction Isolation*) were created to solve
these issues. The preferred method between the two options is *Database SKIP LOCKED*, but it requires PostgreSQL 9.5
or newer, SQLite 3.25 or newer or MySQL 8.0 or newer (untested), or MariaDB 10.3 or newer (untested).
If using an older database version, use *Database Transaction Isolation* instead. A detailed explanation of these database locking methods in PostgreSQL can be
found in the excellent [What is SKIP LOCKED for in PostgreSQL 9.5?][2ndquadrant-skip-locked] entry on the [2ndQuadrant
PostgreSQL Blog][2ndquadrant-blog].

The preferred assignment method is *Database SKIP LOCKED* or *Database Transaction Isolation*.

[2ndquadrant-skip-locked]: https://www.2ndquadrant.com/en/blog/what-is-select-skip-locked-for-in-postgresql-9-5/
[2ndquadrant-blog]: https://www.2ndquadrant.com/en/blog/

```eval_rst
.. _scaling-configuration:
```

## Configuration

### Gunicorn

We will only outline a few of Gunicorn's options, consult the [Gunicorn documentation](https://docs.gunicorn.org/en/latest/settings.html) for more.

Note that by default Galaxy will use [gravity](https://github.com/galaxyproject/gravity/) to create a [supervisor](http://supervisord.org/) configuration in Gravity's state directory.
Gravity's state directory is located in `database/gravity`, and you can find the generated supervisor configuration in
`database/gravity/supervisor`. The location of the state directory can be controlled using the `--state-dir` argument
of `galaxyctl`, or using the `GRAVITY_STATE_DIR` environment variable.
Configuration values for the supervisor configuration are read from the `gravity` section of your `galaxy.yml` file.
This is the preferred and out-of-the box way of configuring Gunicorn for serving Galaxy.
If you are not using `./run.sh` for starting Galaxy or you would like to use another process manager,
all the Gunicorn configuration values can also directly be set on the command line.

Configuration is performed in the `gravity` section of `galaxy.yml`. You will find that the default, if copied from
`galaxy.yml.sample`, is commented out. The default configuration options are provided to Gunicorn on the command line by
using `gravity` within the `run.sh` script.

After making changes to the `gravity` section, you always need to activate Galaxy's virtualenv and run `galaxyctl update`,
or one of the `start`, `stop`, `restart`, and `graceful` subcommands of the `galaxyctl` command, which will run the `update` command internally.

#### Common Gunicorn configuration

In `galaxy.yml`, define a `gravity` section. Shown below are the options common to all deployment strategies:

```yaml
gravity:
  app_server: gunicorn
  gunicorn:
    # listening options
    bind: '127.0.0.1:8080'
    # performance options
    workers: 1
    # Other options that will be passed to gunicorn
    extra_args:

```

Some of these options deserve explanation:

* `workers`: Controls the number of Galaxy application processes Gunicorn will spawn. Increased web performance can be
  attained by increasing this value. If Gunicorn is the only application on the server, a good starting value is the number of CPUs * 2 + 1.
4-12 workers should be able to handle hundreds if not thousands of requests per second.
* `extra_args`: You can specify additional arguments to pass to gunicorn here.

Note that the performance option values given above are just examples and should be tuned per your specific needs.
However, as given, they are a good place to start.

#### Listening and proxy options

**With a proxy server:**

To use a socket for the communication between the proxy and Gunicorn, set the `bind` option to a path:

```yaml
gravity:
  app_server: gunicorn
  gunicorn:
    # listening options
    bind: 'unix:/srv/galaxy/var/gunicorn.sock'
    extra_args: '--forwarded-allow-ips="*"'
```

Here we've used a UNIX domain socket because there's less overhead than a TCP socket and it can be secured by filesystem
permissions. Note that we've added `--forwarded-allow-ips="*"` to ensure that the domain socket is trusted as a source from which to proxy headers.

You can also listen on a port:

```yaml
  app_server: gunicorn
  gunicorn:
    # listening options
    bind: '127.0.0.1:4001'
```

If you are listening on a port do not set `--forwarded-allow-ips="*"`.

The choice of port 4001 is arbitrary, but in both cases, the socket location must match whatever socket the proxy server
is configured to communicate with. If using a UNIX domain socket, be sure that the proxy server's user has read/write
permission on the socket. Because Galaxy and the proxy server most likely run as different users, this is not likely to
be the case by default. One common solution is to add the proxy server's user to the Galaxy user's primary group.
Gunicorn's `umask` option can also help here.

You can consult the Galaxy documentation for [Apache](apache.md) or [nginx](nginx.md)
for help with the proxy-side configuration.

By setting the `bind` option to a socket, `run.sh` will no longer automatically serve Galaxy via HTTP (since it is assumed that
you are setting a socket to serve Galaxy via a proxy server). If you wish to continue serving HTTP directly with Gunicorn
while using a socket, you can add an additional `--bind` argument via the `extra_args` option:

```yaml
gravity:
  app_server: gunicorn
  gunicorn:
    # listening options
    bind: 'unix:/srv/galaxy/var/gunicorn.sock'
    extra_args: '--forwarded-allow-ips="*" --bind 127.0.0.1:8080'
```

Note that this should only be used for debugging purposes due to `--forwarded-allow-ips="*"`.

**Without a proxy server**:

It is strongly recommended to use a proxy server.

Gunicorn can be configured to serve HTTPS directly:

```yaml
  # listening options
  gunicorn:
    # listening options
    bind: '0.0.0.0:443'
    keyfile: server.key
    certfile: server.crt
```

See [Gunicorn's SSL documentation](https://docs.gunicorn.org/en/latest/settings.html#ssl) for more details.

To bind to ports < 1024 (e.g. if you want to bind to the standard HTTP/HTTPS ports 80/443), you must bind as the `root`
user and drop privileges to the Galaxy user. However you are strongly encouraged to setup a proxy server
as described in the [production configuration](production.md) documentation.

### Job Handling

```eval_rst
.. warning::

   In all strategies, once a handler has been assigned jobs, you cannot unconfigure that handler (e.g. to decrease the
   number of handlers) until it has finished processing all its assigned jobs, or else its jobs will never reach a
   terminal state. In order to allow a handler to run but not receive any new jobs, configure it with an unused tag (e.g
   ``<handler id="handler5" tags="drain" />``) and restart *all* Galaxy processes.

   Alternatively, you can stop the handler and reassign its jobs to another handler, but this is currently only possible
   using an ``UPDATE`` query in the database and is only recommended for advanced Galaxy administrators.
```

#### all-in-one job handling

Ensure that no `<handlers>` section exists in your `job_conf.xml` (or no `job_conf.xml` exists at all) and start Galaxy
normally. No additional configuration is required. To increase the number of web workers/job handlers, increase the
value of `workers` in the gunicorn section of your galaxy.yml file:

```yaml
gravity:
  ...
  gunicorn:
    ...
    # performance options
    workers: 4
    ...
```

Jobs will be handled according to rules outlined above in [Job Handler Assignment Methods](#job-handler-assignment-methods).

```eval_rst
.. note::

   If a ``<handlers>`` section is defined in ``job_conf.xml``, Galaxy's web workers will no longer load and start the
   job handling code, so tools cannot be mapped to specific handlers in this strategy. If you wish to control job
   handling, choose another deployment strategy.
```

##### Statically defined handlers

In the  `<handlers>` section in `job_conf.xml`, define the webless handlers you plan to start. Tools can be mapped
to specific handlers, or to handler tags, as in the following example:

```xml
<job_conf>
    <handlers>
        <handler id="handler1" />
        <handler id="handler2" />
        <handler id="handler3" tags="nodefault" />
        <handler id="handler4" tags="special" />
        <handler id="handler5" tags="special" />
    </handlers>
    <tools>
        <tool id="test1" handler="handler3" />
        <tool id="test2" handler="special" />
        <tool id="test3" handler="handler2" />
    </tools>
</job_conf>
```

```eval_rst
.. tip::

   Any untagged handler will be automatically considered a default handler. As seen in the example above, it is possible
   to map any tool to any handler or tag, however, a handler must be tagged to prevent it from handling jobs created for
   tools that are not explicitly mapped to handlers. Thus, ``handler2`` will handle *all* executions of tool ``test3``,
   but it will also (along with ``handler1``) handle tools that are not explicitly mapped to handlers. In contrast,
   ``handler3`` will *only* handle executions of tool ``test1``.
```

`run.sh` will start the gunicorn and job handler process(es), but if you are not using `run.sh` or the generated supervisor setup you will need to start the webless handler processes yourself. This is done on the command line like so:

```console
$ cd /srv/galaxy/server
$ ./scripts/galaxy-main -c config/galaxy.yml --server-name handler0 --daemonize
$ ./scripts/galaxy-main -c config/galaxy.yml --server-name handler1 --daemonize
$ ./scripts/galaxy-main -c config/galaxy.yml --server-name handler2 --daemonize
```

#### Dynamically defined handlers

In order to define handlers dynamically, you must be using one of the new "database locking" handler assignment methods
as explained in [Job Handler Assignment Methods](#job-handler-assignment-methods), such as in the following
`job_conf.xml`:

```xml
<job_conf>
    <handlers assign_with="db-skip-locked" />
    <tools>
        <tool id="test1" handler="special" />
    </tools>
</job_conf>
```

Note that we have defined a `<handlers>` section without any `<handler>` entries,
and we have explicitly configured the assignment method with `assign_with="db-skip-locked"`.

To let gravity know how many webless handler processes should be started set the number of processes to start in the `gravity:` section of galaxy.yml:

```yaml
gravity:
  handlers:
    handler:
      processes: 3
      pools:
        - job-handler
        - workflow-scheduler
    special:
      pools:
        - job-handler.special
```

In this example 4 processes will be started in total:
3 processes will act as job handler and workflow scheduler, and one process will be dedicated to handling jobs for the `special` tag only. With the `job_conf.xml` configuration above these would be jobs created by the `test1` tool.
You can omit the `pools` argument, this will then default to:

```yaml
        ...
        pools:
          - job-handler
          - workflow-scheduler
        ...
```

If you omit the `processes` argument this will default to a single process.
You can further customize the handler names using the `name_template` section,
for a complete example see [this gravity test case](https://github.com/galaxyproject/gravity/blob/a00df1c671fdc01e3fbc42f64a851a45a37a1870/tests/test_process_manager.py#L28).

If you are not using dynamic handlers please omit the `handlers` entry completely, as these will
otherwise be idle and not handle jobs or workflows.

As with statically defined handlers, `run.sh` will start the process(es), but if you are not using `run.sh` or the generated supervisor config you will need to start the webless handler processes yourself. This is done on the command line like so (note the addition of the `--attach-to-pool` option):

```console
$ cd /srv/galaxy/server
./scripts/galaxy-main -c config/galaxy.yml --server-name handler_0 --attach-to-pool job-handlers --attach-to-pool workflow-scheduler --daemonize
./scripts/galaxy-main -c config/galaxy.yml --server-name handler_1 --attach-to-pool job-handlers --attach-to-pool workflow-scheduler --daemonize
./scripts/galaxy-main -c config/galaxy.yml --server-name handler_3 --attach-to-pool job-handlers --attach-to-pool workflow-scheduler --daemonize
./scripts/galaxy-main -c config/galaxy.yml --server-name special_0 --attach-to-pool job-handlers.special --daemonize
```

In this example:

* `handler_0`, `handler_1` and `handler2` will handle tool executions that are not explicitly mapped to handlers
* `special_0` will handle tool executions that are mapped to the `special` handler tag

## gravity & galaxyctl

[Gravity](https://github.com/galaxyproject/gravity) is a management tool for Galaxy servers,
and is installed when you set up Galaxy.

It provides two executables, `galaxyctl`, which is used to manage the starting, stopping, and logging of Galaxy's various processes, and `galaxy`, which can be used to run a Galaxy server in the foreground.

These commands are available from within Galaxy's virtualenv, or you can install them globally.
If you have used the standard installation method for Galaxy by running `./run.sh` or executing
`./scripts/common_startup.sh`, a default directory has been configured in which gravity stores
its state. If you have installed Galaxy or gravity by another means, you can use the `--state-dir` argument
or the `GRAVITY_STATE_DIR` environment variable to control the state directory. If a state dir is not specified, it defaults to `~/.config/galaxy-gravity`.
In the following sections we assume you have correctly set up gravity and can use the `galaxyctl` command.

## Logging and daemonization

When running `./run.sh` the log output is shown on screen, and ^ctrl-c will stop all processes.
Galaxy can be started in the background by running `./run.sh --daemon`.

Alternatively, you can control Galaxy using the `galaxyctl` command provided by gravity.
After activating Galaxy's virtual environment you can start Galaxy in the background
using `galaxyctl start`:

```console
$ galaxyctl start
celery                           STARTING
celery-beat                      STARTING
gunicorn                         STARTING
Log files are in /Users/mvandenb/src/doc_test/database/gravity/log
```

All process logs can be seen with `galaxyctl follow`:

```console
$ galaxyctl follow
==> /Users/mvandenb/src/doc_test/database/gravity/log/gunicorn.log <==
galaxy.webapps.galaxy.buildapp DEBUG 2022-02-17 16:31:33,344 [pN:main,p:91480,tN:MainThread] Prior to webapp return, Galaxy thread <Thread(JobHandlerQueue.monitor_thread, started daemon 123145470246912)> is alive.
galaxy.webapps.galaxy.buildapp DEBUG 2022-02-17 16:31:33,345 [pN:main,p:91480,tN:MainThread] Prior to webapp return, Galaxy thread <Thread(JobHandlerStopQueue.monitor_thread, started daemon 123145487036416)> is alive.
galaxy.webapps.galaxy.buildapp DEBUG 2022-02-17 16:31:33,345 [pN:main,p:91480,tN:MainThread] Prior to webapp return, Galaxy thread <Thread(WorkflowRequestMonitor.monitor_thread, started daemon 123145503825920)> is alive.
galaxy.webapps.galaxy.buildapp DEBUG 2022-02-17 16:31:33,345 [pN:main,p:91480,tN:MainThread] Prior to webapp return, Galaxy thread <Thread(database_heartbeart_main.thread, started daemon 123145520615424)> is alive.
galaxy.webapps.galaxy.buildapp DEBUG 2022-02-17 16:31:33,345 [pN:main,p:91480,tN:MainThread] Prior to webapp return, Galaxy thread <GalaxyQueueWorker(Thread-1, started daemon 123145537404928)> is alive.
galaxy.webapps.galaxy.buildapp DEBUG 2022-02-17 16:31:33,346 [pN:main,p:91480,tN:MainThread] Prior to webapp return, Galaxy thread <Thread(Thread-2, started daemon 123145554194432)> is alive.
galaxy.webapps.galaxy.buildapp DEBUG 2022-02-17 16:31:33,346 [pN:main,p:91480,tN:MainThread] Prior to webapp return, Galaxy thread <Thread(Thread-3, started daemon 123145570983936)> is alive.
[2022-02-17 16:31:34 +0100] [91480] [INFO] Started server process [91480]
[2022-02-17 16:31:34 +0100] [91480] [INFO] Waiting for application startup.
[2022-02-17 16:31:34 +0100] [91480] [INFO] Application startup complete.

==> /Users/mvandenb/src/doc_test/database/gravity/log/celery.log <==
[2022-02-17 16:31:27,008: DEBUG/MainProcess] ^-- substep ok
[2022-02-17 16:31:27,009: DEBUG/MainProcess] | Consumer: Starting Events
[2022-02-17 16:31:27,009: DEBUG/MainProcess] ^-- substep ok
[2022-02-17 16:31:27,009: DEBUG/MainProcess] | Consumer: Starting Tasks
[2022-02-17 16:31:27,035: DEBUG/MainProcess] ^-- substep ok
[2022-02-17 16:31:27,035: DEBUG/MainProcess] | Consumer: Starting Heart
[2022-02-17 16:31:27,035: DEBUG/MainProcess] ^-- substep ok
[2022-02-17 16:31:27,035: DEBUG/MainProcess] | Consumer: Starting event loop
[2022-02-17 16:31:27,035: INFO/MainProcess] celery@MacBook-Pro-2.local ready.
[2022-02-17 16:31:27,035: DEBUG/MainProcess] basic.qos: prefetch_count->8

==> /Users/mvandenb/src/doc_test/database/gravity/log/celery-beat.log <==
[2022-02-17 16:29:04,023: DEBUG/MainProcess] beat: Ticking with max interval->5.00 minutes
[2022-02-17 16:29:04,024: DEBUG/MainProcess] beat: Waking up in 5.00 minutes.
No Galaxy config file found, running from current working directory: /Users/mvandenb/src/doc_test
[2022-02-17 16:31:26,818: DEBUG/MainProcess] Setting default socket timeout to 30
[2022-02-17 16:31:26,819: INFO/MainProcess] beat: Starting...
[2022-02-17 16:31:26,824: DEBUG/MainProcess] Current schedule:
<ScheduleEntry: prune-history-audit-table galaxy.celery.tasks.prune_history_audit_table() <freq: 1.00 hour>
<ScheduleEntry: celery.backend_cleanup celery.backend_cleanup() <crontab: 0 4 * * * (m/h/d/dM/MY)>
[2022-02-17 16:31:26,824: DEBUG/MainProcess] beat: Ticking with max interval->5.00 minutes
[2022-02-17 16:31:26,825: DEBUG/MainProcess] beat: Waking up in 5.00 minutes.
```

More advanced logging options are described in the Galaxy [Logging Configuration documentation](config_logging).

## Starting and Stopping

If you want to run your Galaxy server as a persistent service, you can include the `galaxy` script from Galaxy's
virtualenv in the configuration of your process manager (e.g. systemd). You can then continue using the `galaxyctl` command as usual
to start/stop/restart Galaxy or follow the logs.

### Transparent restarts

For zero-downtime restarts use the command `galaxyctl graceful`.

### Systemd

This is a sample config for systemd. More information on systemd.service environment
settings can be found in the [documentation](https://www.freedesktop.org/software/systemd/man/systemd.exec.html#Environment=)
The filename follows the pattern `<service_name>.service`. In this case we will use `galaxy.service`

```ini
[Unit]
Description=Galaxy processes
After=network.target
After=time-sync.target

[Service]
PermissionsStartOnly=true
Type=simple
User=galaxy
Group=galaxy
Restart=on-abort
WorkingDirectory=/srv/galaxy/server
TimeoutStartSec=10
ExecStart=/srv/galaxy/venv/bin/galaxy --state-dir /srv/galaxy/database/gravity
Environment=VIRTUAL_ENV=/srv/galaxy/venv PATH=/srv/galaxy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
[Install]
WantedBy=multi-user.target
```

We can now enable and start the the Galaxy services with systemd:

```console
# systemctl enable galaxy
Created symlink from /etc/systemd/system/multi-user.target.wants/galaxy.service to /etc/systemd/system/galaxy.service.
```

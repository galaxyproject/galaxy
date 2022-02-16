# Scaling and Load Balancing

The Galaxy framework is written in Python and makes extensive use of threads.  However, one of the drawbacks of Python
is the [Global Interpreter Lock](http://docs.python.org/c-api/init.html#thread-state-and-the-global-interpreter-lock),
which prevents more than one thread from being on CPU at a time.  Because of this, having a multi-core system will not
improve the Galaxy framework's performance out of the box since Galaxy can use (at most) one core at a time in its
default configuration.  However, Galaxy can easily run in multiple separate processes, which solves this problem.  For a
more thorough explanation of this problem and why you will almost surely want to switch to the multiprocess
configuration if running for more than a small handful of users, see the [production configuration](production.md)
page.

Just to be clear: Increasing the number of plugin workers in `job_conf.xml` will not make you Galaxy server much more responsive.
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
as a standalone server with no web stack. Prior to the 18.01 release, Galaxy (by default)
used the [Python Paste][paste] web stack, and ran in a single process. Between the 18.01 release and the 22.01 release
uWSGI was used as the default application server. Starting with the 22.01 release the default application server is
Gunicorn. For information about uWSGI in the Galaxy context please consult the version of this document that is
appropriate to your Galaxy version.

Gunicorn is able to serve ASGI applications. Galaxy can act as an ASGI web application since release 21.01,
and we will drop support for being run as a WSGI application via uWSGI in Galaxy release 22.05.

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
* A web worker that receives the job request from the UI/API will be the job handler for that job

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
methods (see below). If the database used does not support this mechanism (in practice this should only apply
to sqlite before version 3.25, which is not at all recommended for production Galaxy server) a handler is randomly
assigned by the web worker when the job is submitted via the UI/API, meaning that jobs may be assigned to unresponsive handlers.

### uWSGI for web serving with Mules as job handlers

This strategy is deprecated and will be removed in Galaxy release 22.05.
You can consult the documentation for older versions of Galaxy for details.

If you're migrating Galaxy to 22.01 or newer we recommend you set up the
**Gunicorn + Webless** strategy above.

## Job Handler Assignment Methods

Job handler assignment methods are configurable with the `assign_with`
attribute on the `<handlers>` tag in `job_conf.xml`.  The available methods are:

* **Database Transaction Isolation** (`db-transaction-isolation`, new in 19.01) - Jobs are assigned a handler by handlers selecting the unassigned
  job from the database using SQL transaction isolation, which uses database locks to guarantee that only one handler
  can select a given job. This occurs by the web worker that receives the tool execution request (via the UI or API)
  setting a new job's 'handler' column in the database to the configured tag/default (or `_default_` if no tag/default
  is configured). Handlers "listen" for jobs by selecting jobs from the database that match the handler tag(s) for which
  they are configured. `db-transaction-isolation` is the default assignment method if no handlers are defined,
  or handlers are defined but no assign_with attribute is set on the `handlers` tag and *Database SKIP LOCKED* is not available.

* **Database SKIP LOCKED** (`db-skip-locked`, new in 19.01) - Jobs are assigned a handler by handlers selecting the unassigned job from
  the database using `SELECT ... FOR UPDATE SKIP LOCKED` on databases that support this query (see the next section for
  details). This occurs via the same process as *Database Transaction Isolation*, the only difference is the way in
  which handlers query the database. This is the default if no handlers are defined, or handlers are defined but no assign_with attribute is set
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

Prior to Galaxy 19.01, the most common deployment strategies (e.g. **uWSGI + Webless**) assigned handlers using what is
now (since 19.01) referred to as *Database Preassignment*.  Although still a fallback option when the database
does not support *Database SKIP LOCKED* or *Database Transaction Isolation*, preassignment has a few drawbacks:

* Web workers do not have a way to know whether a particular handler is alive when assigning that handler
* Jobs are not load balanced across handlers
* Changing the number of handlers requires changing `job_conf.xml` and restarting *all* Galaxy processes

The "database locking" methods (*Database SKIP LOCKED* and *Database Transaction Isolation*) were created to solve
these issues. The preferred method between the two options is *Database SKIP LOCKED*, but it requires PostgreSQL 9.5
or newer, sqlite 3.25 or newer or MySQL 8.0 or newer (untested), or MariaDB 10.3 or newer (untested).
If using an older database version, use *Database Transaction Isolation* instead. A detailed explanation of these database locking methods in PostgreSQL can be
found in the excellent [What is SKIP LOCKED for in PostgreSQL 9.5?][2ndquadrant-skip-locked] entry on the [2ndQuadrant
PostgreSQL Blog][2ndquadrant-blog].

The preferred assignment method is *Database SKIP LOCKED* or *Database Transaction Isolation*.

[2ndquadrant-skip-locked]: https://blog.2ndquadrant.com/what-is-select-skip-locked-for-in-postgresql-9-5/
[2ndquadrant-blog]: https://blog.2ndquadrant.com/

```eval_rst
.. _scaling-configuration:
```

## Configuration

### Gunicorn

We will only outline a few of Gunicorn's options, consult the [Gunicorn documentation](https://docs.gunicorn.org/en/latest/settings.html) for more.


Note that by default Galaxy will use [gravity](https://github.com/galaxyproject/gravity/) to create a [supervisor](http://supervisord.org/) configuration that
uses Gunicorn configuration values read from the `gravity` section of your `galaxy.yml` file.
This is the preferred and out-of-the box way of configuring Gunicorn for serving Galaxy.
If you are not using `./run.sh` for starting Galaxy or you would like to use another process manager
all of the Gunicorn configuration values can also directly be set on the command line.

Configuration is performed in the `gravity` section of `galaxy.yml`. You will find that the default, if copied from
`galaxy.yml.sample`, is commented out. The default configuration options are provided to Gunicorn on the command line by
using `gravity` within the `run.sh` script.

After making changes to the gravity section you always need to activate Galaxy's virtualenv and run `galaxyctl update`


#### Common Gunicorn configuration

In `galaxy.yml`, define a `gravity` section. Shown below are the options common to all deployment strategies:

```yaml
gravity:
  app_server: gunicorn
  gunicorn:
    # TODO: CHANGE THIS IN GRAVITY, so we can use file descriptors
    # listening options
    bind: '127.0.0.1:8080'
    # performance options
    workers: 1
    # Other options that will be passed to gunicorn
    gunicorn_extra_args:

```

Some of these options deserve explanation:

* `workers`: Controls the number of Galaxy application processes Gunicorn will spawn. Increased web performance can be
  attained by increasing this value. If Gunicorn is the only application on the server the number of CPUs * 2 + 1 is
  a good starting value, 4 - 12 workers should be able to handle hundreds if not thousands of requests per second.
* `gunicorn_extra_args`: You can specify additional arguments to pass to gunicorn here.

Note that the performance option values given above are just examples and should be tuned per your specific needs.
However, as given, they are a good place to start.

#### Listening and proxy options

**With a proxy server:**

To use a socket for the communication between the proxy and Gunicorn, set the `bind` option to a path:

```yaml
gravity:
  app_server: gunicorn
  gunicorn:
    # TODO: CHANGE THIS IN GRAVITY, so we can use file descriptors
    # listening options
    bind: '/srv/galaxy/var/gunicorn.sock'
```

Here we've used a UNIX domain socket because there's less overhead than a TCP socket and it can be secured by filesystem
permissions, but you can also listen on a port:

```yaml
  app_server: gunicorn
  gunicorn:
    # TODO: CHANGE THIS IN GRAVITY, so we can use file descriptors
    # listening options
    bind: '127.0.0.1:4001'
```

The choice of port 4001 is arbitrary, but in both cases, the socket location must match whatever socket the proxy server
is configured to communicate with. If using a UNIX domain socket, be sure that the proxy server's user has read/write
permission on the socket. Because Galaxy and the proxy server most likely run as different users, this is not likely to
be the case by default. One common solution is to add the proxy server's user to the Galaxy user's primary group.
Gunicorn's `umask` option can also help here.

You can consult the Galaxy documentation for [Apache](apache.md) or [nginx](nginx.md)
for help with the proxy-side configuration.

By setting the `bind` option to a socket, `run.sh` will no longer automatically serve Galaxy via HTTP (since it is assumed that
you are setting a socket to serve Galaxy via a proxy server). If you wish to continue serving HTTP directly with Gunicorn
while using a socket, you can add an additional `--bind` argument via the `gunicorn_extra_args` option:

```yaml
gravity:
  app_server: gunicorn
  gunicorn:
    # TODO: CHANGE THIS IN GRAVITY, so we can use file descriptors
    # listening options
    bind: '/srv/galaxy/var/gunicorn.sock'
    gunicorn_extra_args: '--bind 127.0.0.1:8080'
```

**Without a proxy server**:

It is strongly recommended to use a proxy server.

Gunicorn can be configured to serve HTTPS directly:

```yaml
  # listening options
  gunicorn:
    # TODO: CHANGE THIS IN GRAVITY, so we can use file descriptors
    # listening options
    bind: '0.0.0.0:443'
    keyfile: server.key
    certfile: server.crt
```

See [Gunicorn's SSL documentation](https://docs.gunicorn.org/en/latest/settings.html#ssl) for more details.

To bind to ports < 1024 (e.g. if you want to bind to the standard HTTP/HTTPS ports 80/443), you must bind as the `root`
user and drop privileges to the Galaxy user. However you are strongly encouraged to setup [Apache](apache.md) or [nginx](nginx.md) instead.

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

`run.sh` will start the gunicorn and job handler process(es), but if you are not using run.sh or the generated supervisor setup you will need to start the webless handler processes yourself. This is done on the command line like so:

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

As with statically defined handlers, `run.sh` will start the process(es), but if you are not using `run.sh` or the generated supervisor config you will need to start the webless handler processes yourself. This is done on the command line like so (note the addition of the `--attach-to-pool`
option):

```console
$ cd /srv/galaxy/server
$ ./scripts/galaxy-main -c config/galaxy.yml --server-name handler0 --attach-to-pool job-handlers --daemonize
$ ./scripts/galaxy-main -c config/galaxy.yml --server-name handler1 --attach-to-pool job-handlers.special --daemonize
$ ./scripts/galaxy-main -c config/galaxy.yml --server-name handler2 --attach-to-pool job-handlers --attach-to-pool job-handlers.special --daemonize
```

In this example:

* `handler0` and `handler2` will handle tool executions that are not explicitly mapped to handlers
* `handler1` and `handler2` will handle tool executions that are mapped to the `special` handler tag


**Signals**

The signal handling options (`die-on-term` and `hook-master-start` with `unix_signal` values) are not required but, if
set, will override [uWSGI's unconventional signal handling](https://uwsgi-docs.readthedocs.io/en/latest/Management.html)
and cause `SIGTERM` to kill the server rather than restart it, and the uWSGI master process to gracefully shut down its
web workers and job handler mules (i.e. the various Galaxy application processes) when it receives a `SIGINT` (signal 2)
or `SIGTERM` (signal 15) signal (e.g. from `kill(1)` or `<CTRL>+<C>`). When shutting down gracefully, uWSGI will wait 60
seconds (by default, but this can be changed with the `reload-mercy`, `worker-reload-mercy` and `mule-reload-mercy`
options) for child processes to die before forcefully killing them with `SIGKILL` (signal 9). Alternatively, you may
prefer to have it shut down gracefully on `SIGTERM` but forcefully on `SIGINT` (forceful shutdown by uWSGI is still
slightly cleaner than `kill -9` of the master process since it can attempt to release sockets cleanly) or vice-versa,
which you can do by setting one of the signals to call `kill_them_all` rather than `gracefully_kill_them_all`:

```yaml
  # fix up signal handling
  die-on-term: true
  hook-master-start: unix_signal:2 kill_them_all
  hook-master-start: unix_signal:15 gracefully_kill_them_all
```

More details on the `unix_signal` hook can be found in [uWSGI Issue #849](https://github.com/unbit/uwsgi/issues/849).

**Logging and daemonization**

It's possible to configure uWSGI to log to a file with the `logto` or `logto2` options (when running in the foreground,
the default), but more advanced logging options that split log files for each process are possible and described in the
Galaxy [Logging Configuration documentation](config_logging)

When running as a daemon with `run.sh --daemon`, output is logged to `galaxy.log` and the pid is written to
`galaxy.pid`. These can be controlled with the `daemonize` and `pidfile` arguments (their `daemonize2` and `pidfile2`
counterparts wait until after the application successfully loads to open and write the files). If you set a `daemonize*`
option, you should not use the `--daemon` argument to `run.sh` (or not use `run.sh` at all, and start Galaxy directly
with `uwsgi` on the command line).


## Starting and Stopping

If you are using the **uWSGI + Webless job handlers** deployment strategy or want to run your Galaxy server as a
persistent service, you can control it through a process manager. The current recommended process manager is
[Supervisord](http://supervisord.org/). If you are comfortable with systemd and are running a relatively modern Linux
distribution, you can also configure Galaxy as a service directly in systemd.

### Supervisord

You can use a supervisord config file like the following or be inspired by [this
example](https://github.com/galaxyproject/galaxy/blob/dev/contrib/galaxy_supervisor.conf). Be sure to `supervisord
update` or `supervisord reread && supervisord restart` whenever you make configuration changes.

```ini
[program:web]
command         = /srv/galaxy/venv/bin/uwsgi --yaml /srv/galaxy/config/galaxy.yml
directory       = /srv/galaxy/server
umask           = 022
autostart       = true
autorestart     = true
startsecs       = 10
stopwaitsecs    = 65
user            = galaxy
numprocs        = 1
stopsignal      = INT
```

This configuration defines a "program" named `web` which represents our Galaxy uWSGI frontend. You'll notice that we've
set a command, a directory, a umask, all of which you should be familiar with. Additionally we've specified that the
process should `autostart` on boot, and `autorestart` if it ever crashes. We specify `startsecs` to say "the process
must stay up for this long before we consider it OK. If the process crashes sooner than that (e.g. bad changes you've
made to your local installation) supervisord will try again a couple of times to restart the process before giving up
and marking it as failed. This is one of the many ways supervisord is much friendly for managing these sorts of tasks. 

The value of `stopwaitsecs` should be at least as large as the smallest value of uWSGI's `reload-mercy`,
`worker-reload-mercy`, and `mule-reload-mercy` options, all of which default to `60`.

If using the **uWSGI + Webless** strategy, you'll need to addtionally define job handlers to start. There's no simple
way to activate a virtualenv when using supervisor, but you can simulate the effects by setting `$PATH` and
`$VIRTUAL_ENV`:

```ini
[program:handler]
command         = /srv/galaxy/venv/bin/python ./scripts/galaxy-main -c /srv/galaxy/config/galaxy.yml --server-name=handler%(process_num)s --pid-file=/srv/galaxy/var/handler%(process_num)s.pid --log-file=/srv/galaxy/log/handler%(process_num)s.log
directory       = /srv/galaxy/server
process_name    = handler%(process_num)s
numprocs        = 3
umask           = 022
autostart       = true
autorestart     = true
startsecs       = 15
stopwaitsecs    = 35
user            = galaxy
environment     = VIRTUAL_ENV="/srv/galaxy/venv",PATH="/srv/galaxy/venv/bin:%(ENV_PATH)s"
```

This is similar to the "web" definition above, however, you'll notice that we use `%(process_num)s`. That's a variable
substitution in the `command` and `process_name` fields. We've set `numprocs = 3`, which says to launch three handler
processes. Supervisord will loop over `0..numprocs` and launch `handler0`, `handler1`, and `handler2` processes
automatically for us, templating out the command string so each handler receives a different log file and name.

The value of `stopwaitsecs` should be at least as large as `monitor_thread_join_timeout * runner_plugin_count`, which
is `30` in the default configuration (`monitor_thread_join_timeout` is a Galaxy configuration option and
`runner_plugin_count` is the number of `<plugin>`s in your `job_conf.xml`).

Lastly, collect the tasks defined above into a single group. If you are not using webless handlers this is as simple as:

```ini
[group:galaxy]
programs = web
```

With webless handlers, it is:

```ini
[group:galaxy]
programs = web, handler
```

This will let us manage these tasks more globally with the `supervisorctl` command line tool:

```console
# supervisorctl status
galaxy:handler0                  RUNNING   pid 7275, uptime 16:32:17
galaxy:handler1                  RUNNING   pid 7276, uptime 16:32:17
galaxy:handler2                  RUNNING   pid 7277, uptime 16:32:17
galaxy:web                       RUNNING   pid 7299, uptime 16:32:16
```

This command shows us the status of our jobs, and we can easily restart all of the processes at once by naming the
group. Familiar commands like start and stop are also available.

```console
# supervisorctl restart galaxy:
galaxy:handler0: stopped
galaxy:handler1: stopped
galaxy:handler2: stopped
galaxy:web: stopped
galaxy:web: started
galaxy:handler0: started
galaxy:handler1: started
galaxy:handler2: started
```

### Systemd

Sample **uWSGI + Webless** strategy for systemd. More information on systemd.service environment
settings can be found in the [documentation](http://0pointer.de/public/systemd-man/systemd.exec.html#Environment=)


```ini
[Unit]
Description=Galaxy web handler
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
ExecStart=/srv/galaxy/venv/bin/uwsgi --yaml /srv/galaxy/config/galaxy.yml
Environment=VIRTUAL_ENV=/srv/galaxy/venv PATH=/srv/galaxy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
[Install]
WantedBy=multi-user.target
```

For multiple handlers, the service file needs to be a [template unit](https://www.freedesktop.org/software/systemd/man/systemd.unit.html#Description>) - the filename follows the syntax 
`<service_name>@<argument>.service` and all instances of `%I` in the service file are replaced with the `<argument>`

```ini
[Unit]
Description=Galaxy job handlers
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
ExecStart=/srv/galaxy/venv/bin/python ./scripts/galaxy-main -c /srv/galaxy/config/galaxy.yml --server-name=handler%I --log-file=/srv/galaxy/log/handler%I.log
#Environment=VIRTUAL_ENV=/srv/galaxy/venv PATH=/srv/galaxy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
[Install]
WantedBy=multi-user.target
```

We can now enable and start the web services with systemd 
```console
# systemctl enable galaxy-web
Created symlink from /etc/systemd/system/multi-user.target.wants/galaxy-web.service to /etc/systemd/system/galaxy-web.service.
# systemctl enable galaxy-handler@{0..3}
Created symlink from /etc/systemd/system/multi-user.target.wants/galaxy-handler@0.service to /etc/systemd/system/galaxy-handler@.service.
Created symlink from /etc/systemd/system/multi-user.target.wants/galaxy-handler@1.service to /etc/systemd/system/galaxy-handler@.service.
Created symlink from /etc/systemd/system/multi-user.target.wants/galaxy-handler@2.service to /etc/systemd/system/galaxy-handler@.service.
Created symlink from /etc/systemd/system/multi-user.target.wants/galaxy-handler@3.service to /etc/systemd/system/galaxy-handler@.service.
# systemctl start galaxy-handler@{0..3}
# systemctl start galaxy-web
```

### Transparent Restart - Zerg Mode

The standard uWSGI operation mode allows you to restart the Galaxy application while blocking client connections. Zerg Mode does away with the waiting by running a special Zerg Pool process, and connecting Zergling workers (aka Galaxy application processes) to the pool. As long as at least one is connected, requests can be served.

See the [GCC2017 Admin Training session](https://github.com/galaxyproject/dagobah-training/blob/2017-montpellier/sessions/10-uwsgi/ex2-zerg-mode.md) on how to set this up.

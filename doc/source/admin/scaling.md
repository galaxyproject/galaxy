# Scaling and Load Balancing

The Galaxy framework is written in Python and makes extensive use of threads.  However, one of the drawbacks of Python
is the [Global Interpreter Lock](http://docs.python.org/c-api/init.html#thread-state-and-the-global-interpreter-lock),
which prevents more than one thread from being on CPU at a time.  Because of this, having a multi-core system will not
improve the Galaxy framework's performance out of the box since Galaxy can use (at most) one core at a time in its
default configuration.  However, Galaxy can easily run in multiple separate processes, which solves this problem.  For a
more thorough explanation of this problem and why you will almost surely want to switch to the multiprocess
configuration if running for more than a small handful of users, see the [production configuration](production.html)
page.

Just to be clear: increasing the values of `threadpool_workers` in `galaxy.yml` or the number of plugin workers in
`job_conf.xml` will not make you Galaxy server much more responsive.  The key to scaling Galaxy is the ability to run
*multiple* Galaxy servers which co-operatively work on the same database.

## Terminology

* **web worker** - Galaxy server process responsible for servicing web requests for the UI/API 
* **job handler** - Galaxy server process responsible for setting up, starting, and monitoring jobs, submitting jobs to
  a cluster (if configured), for setting metadata (if not set on the cluster), and cleaning up after jobs
* **[uWSGI][uwsgi]** - Powerful application server written in C that implements the HTTP and Python WSGI protocols
  * **[Mules][uwsgi-mules]** - uWSGI processes started after the main application (Galaxy) that can run separate code
    and receive messages from uWSGI web workers
  * **[Zerg Mode][uwsgi-zerg-mode]** - uWSGI configuration where multiple copies of the same application can be started
    simultaneously in order to maintain availability during application restarts
* **Webless Galaxy application** - The Galaxy application run as a standalone Python application with no web/WSGI server
* **[Paste][paste]** - Application server written in pure Python that implements the HTTP and Python WSGI protocols

[uwsgi]: https://uwsgi-docs.readthedocs.io/
[uwsgi-mules]: https://uwsgi-docs.readthedocs.io/en/latest/Mules.html
[uwsgi-zerg-mode]: https://uwsgi-docs.readthedocs.io/en/latest/Zerg.html
[paste]: https://paste.readthedocs.io/

## Application Servers

It is possible to run the Galaxy server in many different ways, including under different web application frameworks, or
as a standalone server with no web stack. For most of its modern life, prior to the 18.01 release, Galaxy (by default)
used the [Python Paste][paste] web stack, and ran in a single process.

Beginning with Galaxy release 18.01, the default application server for new installations of Galaxy is [uWSGI][uwsgi].
Prior to 18.01, it was possible (and indeed, recommended for production Galaxy servers) to run Galaxy under uWSGI, but
it was necessary to install and configure uWSGI separately from Galaxy. uWSGI is now provided with Galaxy as a Python
Wheel and installed in to its virtualenv, as described in detail in the [Framework
Dependencies](framework_dependencies.html) documentation.

uWSGI has numerous benefits over Python Paste for our purposes:

* Written in C and designed to be high performance
* Easily runs multiple processes by increasing `processes` config option
* Load balances multiple processes internally rather than requiring load balancing in the proxy server
* Offload engine for serving static content
* Speaks high performance native protocol between uWSGI and proxy server
* Can speak HTTP and HTTPS protocols without proxy server
* Incredibly featureful, supports a wide array of deployment scenarios
* Supports WebSockets, which enable Galaxy Interactive Environments out-of-the-box without a proxy server or Node.js

## Deployment Options

There are multiple deployment strategies for the Galaxy application that you can choose from. The right one depends on
the configuration of the infrastructure on which you are deploying. In all cases, all Galaxy job features such as
[running on a cluster](cluster.html) are supported.

Although uWSGI implements nearly all the features that were previously the responsibility of an upstream proxy server,
at this time, it is still recomended to place a proxy server in front of uWSGI and utilize it for all of its traditional
roles (serving static content, serving dataset downloads, etc.) as described in the [production
configuration](production.html) documentation.

When using uWSGI with a proxy server, it is recommended that you use the native high performance uWSGI protocol
(supported by both [Apache](apache.html) and [nginx](nginx.html)) between uWSGI and the
proxy server, rather than HTTP.

### uWSGI with jobs handled by web workers (default configuration)

Referred to in this documentation as the **uWSGI all-in-one** strategy.

* Job handlers and web workers are the same processes and cannot be separated
* The web worker that receives the job request from the UI/API will be the job handler for that job

Under this strategy, jobs will be handled by uWSGI web workers. Having web processes handle jobs will negatively impact
UI/API performance.

This is the default out-of-the-box configuration as of Galaxy Release 18.01.

### uWSGI for web serving with Mules as job handlers

Referred to in this documentation as the **uWSGI + Mules** strategy.

* Job handlers run as children of the uWSGI process
* Jobs are dispatched from web workers to job handlers via native *mule messaging*
* Jobs can only be dispatched to mules on the same host
* Trivially easy to enable (disabled by default for simplicity reasons)

Under this strategy, job handling is offloaded to dedicated non-web-serving processes that are started and stopped
directly by the master uWSGI process. As a benefit of using mule messaging, only job handlers that are alive will be
selected to run jobs.

This is the recommended deployment strategy.

```eval_rst
.. important::

   If using **Zerg Mode** or running more than one uWSGI *master* process, do not use **uWSGI + Mules**. Doing so can
   can cause jobs to be executed by mutiple handlers when recovering unassigned jobs at Galaxy server startup.

   Multiple master processes is a rare configuration and is typically only used in the case of load balancing the web
   application across multiple hosts. Note that multiple master proceses is not the same thing as the ``processess``
   uWSGI configuration option, which is perfectly safe to set when using job handler mules.

   For these scenarios, **uWSGI + Webless** is the recommended deployment strategy.
```

### uWSGI for web serving and Webless Galaxy applications as job handlers

Referred to in this documentation as the **uWSGI + Webless** strategy.

* Job handlers are started as standalone Python applications with no web stack
* Jobs are dispatched from web workers to job handlers via the Galaxy database
* Jobs can be dispatched to job handlers running on any host
* The recommended deployment strategy for production Galaxy instances prior to 18.01

Like mules, under this strategy, job handling is offloaded to dedicated non-web-serving processes, but those processes
are [managed by the administrator](#starting-and-stopping). Because the handler is randomly assigned by the web worker
when the job is submitted via the UI/API, jobs may be assigned to dead handlers.

This is the recommended deployment strategy when **Zerg Mode** is used, and for Galaxy servers that run web servers and
job handlers **on different hosts**.

## Legacy Deployment Options

Certain deployment strategies were commonly used prior to the introduction of new features described above. These are
still possible but should no longer be used.

### uWSGI for web serving with Paste Galaxy applications as job handlers

This is essentially the same as **uWSGI + Webless** but needlessly starts handlers with a web stack. This was
recommended before the Webless method existed.

### Paste for web serving with Paste or Webless job handlers

Unlike uWSGI, Paste cannot start multiple server processes on its own. Prior to uWSGI support, this was the only way to
run multiple Galaxy processes, but each web worker and job handler process had to be configured and managed separately.

### Paste web serving and job handling in a single process (default configuration, releases prior to 18.01)

This was the default configuration prior to the 18.01 Galaxy release and offered the simplest out-of-the-box setup at
the expense of performance and scalability.

```eval_rst
.. _scaling-configuration:
```

## Configuration

### uWSGI

Although this document goes in to significant detail about uWSGI configuration, many more options are available, as well
as additional documentation about options described here. Consult the uWSGI documentation for more:

* [Configuring uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html)
* [uWSGI Options](https://uwsgi-docs.readthedocs.io/en/latest/Options.html)
* [Quickstart for Python/WSGI applications](https://uwsgi-docs.readthedocs.io/en/latest/WSGIquickstart.html)

Configuration is performed in the `uwsgi` section of `galaxy.yml`. You will find that the default, if copied from
`galaxy.yml.sample`, is commented out. The default configuration options are provided to uWSGI on the command line by
Galaxy's `run.sh` script.

Galaxy releases prior to 18.01 (or upgraded-to-18.01+ servers which have not migrated their configuration to the YAML
format) used an INI-format configuration file, `galaxy.ini`.

Note that uWSGI's YAML parser is hand-coded and not actually conformant to the YAML standard. Specifically:

* Multiple identical keys with unique values can exist in the same dictionary/hash, as with `hook-master-start` in the
  example below.
* Quoting values (with single or double quotes) is unncessary since the parser treats all values as strings. The parser
  does not correctly handle these quote characters, resulting in invalid values.

If using `galaxy.ini`, the option names and values are the same but in INI format, for example:

```ini
[uwsgi]
processes = 4
socket = 127.0.0.1:4001
...
```

#### Configuration common to all uWSGI deployment styles

In `galaxy.yml`, define a `uwsgi` section. Shown below are the options common to all deployment scenarios:

```yaml
uwsgi:

    # required in order to start the galaxy application
    module: galaxy.webapps.galaxy.buildapp:uwsgi_app()
    virtualenv: .venv
    pythonpath: lib

    # performance options
    master: true
    enable-threads: true
    processes: 2
    threads: 4
    offload-threads: 1

    # fix up signal handling
    die-on-term: true
    hook-master-start: unix_signal:2 gracefully_kill_them_all
    hook-master-start: unix_signal:15 gracefully_kill_them_all

    # listening options
    
    # job handling options
```

Some of these options warrant explanation:

* `master`: Instructs uWSGI to first start a master process manager and then fork web workers, mules, http servers (if
  enabled), and any others from the master. This is required for certain operational modes such as daemonization, but
  can interfere with the use of `<CTRL>+<C>` to shut down Galaxy when running in the foreground on the command line, and
  so is not enabled by default (except when `run.sh --daemon` is used). Its use is strongly recommended for all
  production deployments.
* `processes`: Controls the number of Galaxy application processes uWSGI will spawn. Increased web performance can be
  attained by increasing this value.
* `threads`: Controls the number of web worker threads each application process will spawn.
* `offload-threads`: uWSGI can use a dedicated threadpool for serving static content and handling internal routing,
  setting this value automatically enables such offloading.

Additional options are explained in the [uWSGI Minutiae](#uwsgi-minutiae) below.

Note that the performance option values given above are just examples and should be tuned per your specific needs.
However, as given, they are a good place to start.

Due to the Python GIL, increasing the value of `threads` has diminishing returns on web performance while increasing the
memory footprint of each application process. Increasing it is most useful on servers experiencing a high amount of IO
waiting, but the greatest performance gain comes from increasing `processes` as appropriate for the hardware on which
Galaxy is running.

#### Listening and proxy options

**With a proxy server:**

To use the native uWSGI protocol, set the `socket` option:

```yaml
    # listening options
    socket: /srv/galaxy/var/uwsgi.sock
```

Here we've used a UNIX domain socket because there's less overhead than a TCP socket and it can be secured by filesystem
permissions, but you can also listen on a port:

```yaml
    # listening options
    socket: 127.0.0.1:4001
```

The choice of port 4001 is arbitrary, but in both cases, the socket location must match whatever socket the proxy server
is configured to communicate with. If using a UNIX domain socket, be sure that the proxy server's user has read/write
permission on the socket. Because Galaxy and the proxy server most likely run as different users, this is not likely to
be the case by default. One common solution is to add the proxy server's user to the Galaxy user's primary group.
uWSGI's `chmod-socket` option can also help here.

You can consult the Galaxy documentation for [Apache](apache.html) or [nginx](nginx.html)
for help with the proxy-side configuration.

By setting the `socket` option, `run.sh` will no longer automatically serve Galaxy via HTTP (since it is assumed that
you are setting a socket to serve Galaxy via a proxy server). If you wish to continue serving HTTP directly with uWSGI
while `socket` is set, you can use the `http` option as shown in the directions below.

**Without a proxy server** or with a proxy server that does not speak the uWSGI native protocol:

uWSGI can be configured to serve HTTP and/or HTTPS directly:

```yaml
    # listening options
    http: :8080
    https: :8443,server.crt,server.key
    static-map: /static/style=static/style/blue
    static-map: /static=static
```

To bind to ports < 1024 (e.g. if you want to bind to the standard HTTP/HTTPS ports 80/443), you must bind as the `root`
user and drop privileges to the Galaxy user with a configuration such as:

```yaml
    # listening options
    shared-socket: :80
    shared-socket: :443,server.crt,server.key
    http: =0
    https: =1
    uid: galaxy
    gid: galaxy
    static-map: /static/style=static/style/blue
    static-map: /static=static
```

To redirect HTTP traffic to the HTTPS port rather than serving Galaxy over HTTP, change `http: =0` in the above example
to `http-to-https: =0`.

Because `run.sh` performs setup steps, **it should not be run as `root`**. Instead, you can run uWSGI directly as root
with:

```sh-session
# cd /srv/galaxy/server
# ./.venv/bin/uwsgi --yaml config/galaxy.yml
```

You can run the startup-time setup steps as the galaxy user after upgrading Galaxy with `sh
./scripts/common_startup.sh`.

#### uWSGI all-in-one job handling

Ensure that no `<handlers>` section exists in your `job_conf.xml` (or no `job_conf.xml` exists at all) and start Galaxy
normally. No additional configuration is required. To increase the number of web workers/job handlers, increase the
value of `processes`.

By default, a job will be handled by the web worker that receives the job setup request (via the UI/API). Jobs can be
explicitly mapped to specific workers as described in the [Job configuration documentation](jobs.html) by using the
handler IDs `main.web.N`, where `N` is the web worker ID, starting at 1 and incrementing for each process defined by the
value of `processes`. Each worker that you wish to explicitly map jobs to should be defined in the `<handlers>` section
of `job_conf.xml`. *Do not* define a default handler.

For example, to have the 3rd web worker handle the `test1` tool, you would set the following in `job_conf.xml`
(irrelevant options are not shown):

```xml
<job_conf>
    <handlers>
        <handler id="main.web.3" />
    </handlers>
    <tools>
        <tool id="test1" handler="main.web.3" />
    </tools>
</job_conf>
```

#### uWSGI + Mule job handling

Ensure that no `<handlers>` section exists in your `job_conf.xml` (or no `job_conf.xml` exists at all) and add the
following to the `uwsgi` section of `galaxy.yml` to start a single job handler mule:

```yaml
    # job handling options
    mule: lib/galaxy/main.py
    farm: job-handlers:1
```

Then start Galaxy normally. To add additional mule handlers, add additional `mule` options and add their ID(s), comma
separated,  to the `job-handlers` farm. For example, 3 handlers are defined like so:

```yaml
    # job handling options
    mule: lib/galaxy/main.py
    mule: lib/galaxy/main.py
    mule: lib/galaxy/main.py
    farm: job-handlers:1,2,3
```

By default, a job will be handled by whatever mule currently has the lock on the mule message queue. After receiving a
message, it will release the lock, giving other mules a chance to handle future jobs.  Jobs can be explicitly mapped to
specific mules as described in the [Job configuration documentation](jobs.html) by using the handler IDs
`main.job-handlers.N`, where `N` is the mule's position in the farm, starting at 1 and incrementing for each mule in the
farm (this is not necessarily the mule ID, but it will be if you only define one farm and you add mules to that farm in
sequential order).  Each worker that you wish to explicitly map jobs to should be defined in the `<handlers>` section
of `job_conf.xml`. *Do not* define a default handler.

For example, to have the 2nd mule in the three-mule job-handlers farm shown above handle the `test1` tool, you would set
the following in `job_conf.xml` (irrelevant options are not shown):

```xml
<job_conf>
    <handlers>
        <handler id="main.job-handlers.2" />
    </handlers>
    <tools>
        <tool id="test1" handler="main.job-handlers.2" />
    </tools>
</job_conf>
```

#### uWSGI + Webless job handling

Define a `<handlers>` section in `job_conf.xml` defining the webless handlers you plan to start. In this case, unlike
the uWSGI job handling strategies, you will need to define a default:

```xml
<job_conf>
    <handlers default="handlers">
        <handler id="handler1" tags="handlers" />
        <handler id="handler2" tags="handlers" />
        <handler id="handler3" />
    </handlers>
    <tools>
        <tool id="test1" handler="handler3" />
    </tools>
</job_conf>
```

The definition of a default handler prevents uWSGI web workers from starting the Galaxy job handling code. `run.sh` will
start the uWSGI process(es), but you will need to start the webless handler processes yourself. This is done on the
command line like so:

```sh-session
$ cd /srv/galaxy/server
$ ./scripts/galaxy-main -c config/galaxy.yml --server-name handler0 --daemonize
$ ./scripts/galaxy-main -c config/galaxy.yml --server-name handler1 --daemonize
$ ./scripts/galaxy-main -c config/galaxy.yml --server-name handler2 --daemonize
```

However, a better option to managing processes by hand is to use a process manager as documented in the [Starting and
Stopping](#starting-and-stopping) section.

#### uWSGI Minutiae

**Threads**

Although `enable-threads` was explicitly set in our example, in reality, as long as any value is set for the `threads`
option, `enable-threads` is set implicitly. This option enables the Python GIL and application threads (threads started
by Galaxy itself for various non-web tasks), which Galaxy uses extensively. Setting it explicitly, however, is harmless
and can prevent strange difficult-to-debug situations if `threads` is accidentally unset.

**Worker/Mule shutdown/reload mercy**

By default, uWSGI will wait up to 60 seconds for web workers and mules to terminate. This is generally safe for
servicing web requests, but some parts of Galaxy's job preparation/submission and collection/finishing operations can
take quite a bit of time to complete and are not entirely reentrant: job errors or state inconsistencies can occur if
interrupted (although every effort has been made to minimize such possibilities).  By default, Galaxy will wait up to 30
seconds for the threads allocated for these operations to terminate after instructing them to shut down.  You can change
this behavior by increasing the value of `monitor_thread_join_timeout` in the `galaxy` section of `galaxy.yml`. The
maximum amount of time that Galaxy will take to shut down job runner workers is `monitor_thread_join_timeout *
runner_plugin_count` since each plugin is shut down sequentially (`runner_plugin_count` is the number of `<plugin>`s in
your `job_conf.xml`).

Thus you should set the appropriate uWSGI `*-restart-mercy` option to a value higher than the maximum job runner worker
shutdown time. If using **uWSGI all-in-one**, set `worker-reload-mercy`, and if using **uWSGI + Mule job handling**, set
`mule-reload-mercy` (both in the `uwsgi` section of `galaxy.yml`).

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
Galaxy [Logging Configuration documentation](config_logging.html)

When running as a daemon with `run.sh --daemon`, output is logged to `galaxy.log` and the pid is written to
`galaxy.pid`. These can be controlled with the `daemonize` and `pidfile` arguments (their `daemonize2` and `pidfile2`
counterparts wait until after the application successfully loads to open and write the files). If you set a `daemonize*`
option, you should not use the `--daemon` argument to `run.sh` (or not use `run.sh` at all, and start Galaxy directly
with `uwsgi` on the command line).

**External uwsgi binary:**

It is still possible to run Galaxy using an external copy of uWSGI (for example, installed from APT under
Debian/Ubuntu). This was the recommended installation method in the past. To use an external uWSGI, you'll need simply
need to start with uWSGI directly, rather than using the `run.sh` script. Once you have configured Galaxy/uWSGI, you can
start it with:

```sh-session
$ cd /srv/galaxy/server
$ uwsgi --yaml config/galaxy.yml
```

When installing uWSGI, be sure to install the Python plugin, as this is not always contained in the same package (such
as when installing from APT under Debian/Ubuntu). With the APT packages, you will also need to add `--plugin python` to
the command line (or `plugin: python` to the `uwsgi` section of `galaxy.yml`).

**Other options**

The `py-call-osafterfork` option may only be needed when mule messaging is in use, but it [seems to have no negative
effect](https://github.com/unbit/uwsgi/issues/643) and may solve other situations with starting a complex threaded
Python application.

The `chdir` option is useful if you are not using `run.sh`, to be able to call `uwsgi` from anywhere without having to
`cd` to the Galaxy directory first.

**Monitoring**

The [uwsgitop](https://github.com/xrmx/uwsgitop) tool uses uWSGI's stats server (the `stats` option, which is configured
to listen on a socket or port in the same manner as the `socket` option) to report on the health and performance of the
web workers. It can be installed with `pip install uwsgitop`. This tool can be useful for determing whether a worker is
stuck, or seeing the throughput of traffic on your site.

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

If using the **uWSGI + Webless** scenario, you'll need to addtionally define job handlers to start. There's no simple
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

TODO: write this section.

### Transparent Restart - Zerg Mode

The standard uWSGI operation mode allows you to restart the Galaxy application while blocking client connections. Zerg Mode does away with the waiting by running a special Zerg Pool process, and connecting Zergling workers (aka Galaxy application processes) to the pool. As long as at least one is connected, requests can be served.

See the [GCC2017 Admin Training session](https://github.com/galaxyproject/dagobah-training/blob/2017-montpellier/sessions/10-uwsgi/ex2-zerg-mode.md) on how to set this up.

## Notes on Legacy Configurations

The `track_jobs_in_database` option in the Galaxy config file can still be set, but doing so is unnecessary as it now
defaults to "enabled" under all scenarios. Galaxy's in-memory job tracking can still be used when using the **uWSGI
all-in-one** deployment strategy by setting the option to `false`. In-memory tracking can be slightly more responsive
and thus can be useful in development, but should not be used in production.

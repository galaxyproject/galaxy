# Scaling and Load Balancing

The Galaxy framework is written in Python and makes extensive use of threads.  However, one of the drawbacks of Python is the [Global Interpreter Lock](http://docs.python.org/c-api/init.html#thread-state-and-the-global-interpreter-lock), which prevents more than one thread from being on CPU at a time.  Because of this, having a multi-core system will not improve the Galaxy framework's performance out of the box since Galaxy can use (at most) one core at a time in its default configuration.  However, Galaxy can easily run in multiple separate processes, which solves this problem.  For a more thorough explanation of this problem and why you will almost surely want to switch to the multiprocess configuration if running for more than a small handful of users, see the [production configuration](production.html) page.

Just to be clear: increasing the values of `threadpool_workers` in `galaxy.yml` or the number of plugin workers in `job_conf.xml` will not make you Galaxy server much more responsive.  The key to scaling Galaxy is the ability to run *multiple* Galaxy servers which co-operatively work on the same database.

## Terminology

* **web worker** - Galaxy server process responsible for servicing web requests for the UI/API 
* **job handler** - Galaxy server process responsible for starting and monitoring jobs, submitting jobs to a cluster (if configured), and for setting metadata (if not set on the cluster)
* **[uWSGI][uwsgi]** - Powerful application server written in C that implements the HTTP and Python WSGI protocols
  * **[Mules][uwsgi-mules]** - uWSGI processes started after the main application (Galaxy) that can run separate code and receive messages from uWSGI web workers
  * **[Zerg Mode][uwsgi-zerg-mode]** - uWSGI configuration where multiple copies of the same application can be started simultaneously in order to maintain availability during application restarts
  * **[Emperor Mode][uwsgi-emperor-mode]** - uWSGI configuration where multiple distinct applications can be started by a single master uWSGI process
* **Webless Galaxy application** - The Galaxy application run as a standalone Python application with no web/WSGI server
* **[Paste][paste]** - Application server written in pure Python that implements the HTTP and Python WSGI protocols

[uwsgi]: http://uwsgi-docs.readthedocs.io/
[uwsgi-mules]: http://uwsgi-docs.readthedocs.io/en/latest/Mules.html
[uwsgi-zerg-mode]: http://uwsgi-docs.readthedocs.io/en/latest/Zerg.html
[uwsgi-emperor-mode]: http://uwsgi-docs.readthedocs.io/en/latest/Emperor.html
[paste]: http://paste.readthedocs.io/

### Deployment Options

There are multiple deployment strategies for the Galaxy application that you can choose from. The right one depends on the configuration of the infrastructure on which you are deploying.

#### uWSGI with jobs handled by web workers (default configuration)

* Easily runs multiple processes by increasing `processes` config option
* Load balanced internally
* Speaks native uWSGI protocol supported by nginx and Apache or direct HTTP (and SSL)
* Written in C and designed to be high performance
* Supports WebSockets, which enable Galaxy Interactive Environments out-of-the-box without a proxy server or Node.js
* Incredibly featureful, supports a wide array of deployment scenarios
* The default as of Galaxy Release 18.01
* Jobs are handled by uWSGI web workers (but all Galaxy job features such as [running on a cluster](cluster.html) are still supported) 

Under this strategy, jobs will be handled by the web worker that receives the job request from the UI/API. Having web processes handle jobs will negatively impact UI/API performance.

#### uWSGI for web serving with Mules as job handlers

* Job handlers run as children of the uWSGI process
* Jobs are dispatched from web workers to job handlers via native *mule messaging*
* Jobs can only be dispatched to mules on the same host
* Trivially easy to enable (disabled by default for simplicity reasons)

Under this strategy, job handling is offloaded to dedicated non-web-serving processes that are started and stopped directly by the master uWSGI process. As a benefit of using mule messaging, only job handlers that are alive will be selected to run jobs.

**uWSGI + Mule job handlers is the recommended deployment strategy** for Galaxy servers that run web servers and job handlers **on the same host**.

#### uWSGI for web serving and Webless Galaxy applications as job handlers

* Galaxy is started as a standalone Python application with no web stack
* Jobs are dispatched from web workers to job handlers via the Galaxy database
* Jobs can be dispatched to job handlers running on any host
* The recommended deployment strategy for production Galaxy instances prior to 18.01

Like mules, under this strategy, job handling is offloaded to dedicated non-web-serving processes, but those processes are [managed by the administrator](#starting-and-stopping). Because the handler is randomly assigned by the web worker when the job is submitted via the UI/API, jobs may be assigned to dead handlers.

**uWSGI + Webless job handlers is the recommended deployment strategy** for Galaxy servers that run web servers and job handlers **on different hosts**.

#### Legacy Deployment Options

Certain deployment strategies were commonly used prior to the introduction of new features described above. These are still possible but should no longer be used.

##### uWSGI for web serving with Paste Galaxy applications as job handlers

This is essentially the same as **uWSGI + Webless job handlers** but needlessly starts handlers with a web stack. This was recommended before the Webless method existed

##### Paste for web serving with Paste or Webless job handlers

Unlike uWSGI, Paste cannot start multiple server processes on its own. Prior to uWSGI support, this was the only way to run multiple Galaxy processes, but each web worker and job handler process had to be configured and managed separately.

##### Paste web serving and job handling in a single process

This was the default configuration prior to the 18.01 Galaxy release and offered the simplest out-of-the-box setup at the expense of performance and scalability.

#### uWSGI

In `galaxy.ini`, define a `[uwsgi]` section:

```ini
[uwsgi]
processes = 8
stats = 127.0.0.1:9191
socket = 127.0.0.1:4001
pythonpath = lib
threads = 4
logto = /path/to/uwsgi.log
master = True
```


Port numbers for `stats` and `socket` can be adjusted as desired. Moreover, in the `[app:main]` section, you must set:

```ini
static_enabled = False
track_jobs_in_database = True
```


You will also need to have uWSGI installed. There are a variety of ways to do this. It can be installed system-wide by installing from your system's package manager (on Debian and Ubuntu systems, the `uwsgi` and `uwsgi-plugin-python` provide the necessary components), or with the `easy_install` or `pip` commands (which will install it to the system's Python `site-packages` directory). Alternatively, if you are already running Galaxy from a Python virtualenv, you can use `pip install uwsgi` with that virtualenv's copy of `pip` to install to that virtualenv as your unprivileged Galaxy user.

Also, make sure you have installed PasteDeploy, you can follow the same ways from above.

The web processes can then be started under uWSGI using:

```console
% cd /path/to/galaxy-dist
% PYTHONPATH=eggs/PasteDeploy-1.5.0-py2.7.egg uwsgi --ini-paste config/galaxy.ini
```


The `--daemonize` option can be used to start in the background. uWSGI has an astounding number of options, see [its documentation](http://uwsgi.readthedocs.org/) for help.

Once started, a proxy server (typically Apache or nginx) must be configured to proxy requests to uWSGI (using uWSGI's native protocol). Configuration details for these can be found below.

### Job Handler(s)

In `galaxy.ini`, define one or more additional `[server:...]` sections:

```ini
[server:handler0]
use = egg:Paste#http
port = 8090
host = 127.0.0.1
use_threadpool = true
threadpool_workers = 5

[server:handler1]
use = egg:Paste#http
port = 8091
host = 127.0.0.1
use_threadpool = true
threadpool_workers = 5
```


Using web processes as handlers is possible, but it is not recommended since handler operations can impact web UI performance.

### Remaining configuration options

If you do not have a `job_conf.xml` file, you will need to create one.  There are samples for a basic configuration and an advanced configuration provided in the distribution.  Please note that creating `job_conf.xml` overrides any legacy job running settings in `galaxy.yml`.  See the [jobs configuration documentation](jobs.html) for more detail on job configuration.

In `job_conf.xml`, create `<handler>` tags with `id` attributes that match the handler server names you defined in `galaxy.yml`.  For example, using the configuration above, the `<handlers>` section of `job_conf.xml` would look like:

```xml
<handlers default="handlers">
    <handler id="handler0" tags="handlers"/>
    <handler id="handler1" tags="handlers"/>
</handlers>
```


Any tool not set to an explicit job destination will then be serviced by one of the handlers with the `handlers` tag.  It is possible to dedicate handlers to specific destinations or tools.  For details on how to do this, please see the [job configuration documentation](jobs.html).

## Starting and Stopping

Since you need to run multiple processes, the typical `run.sh` method for starting and stopping Galaxy won't work. The current recommended way to manage these multiple processes is with [Supervisord](http://supervisord.org/). You can use a supervisord config file like the following or be inspired by [this example](https://github.com/galaxyproject/galaxy/blob/dev/contrib/galaxy_supervisor.conf). Be sure to `supervisord restart` or `supervisord reread && supervisord update` whenever you make configuration changes.

```ini
[program:galaxy_uwsgi]
command         = /usr/bin/uwsgi --plugin python --ini-paste /path/to/galaxy/config/galaxy.ini
directory       = /path/to/galaxy
umask           = 022
autostart       = true
autorestart     = true
startsecs       = 10
user            = gxprod
environment     = PATH=/path/to/galaxy/venv:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin,PYTHON_EGG_CACHE=/path/to/galaxy/.python-eggs,PYTHONPATH=/path/to/galaxy/eggs/PasteDeploy-1.5.0-py2.7.egg
numprocs        = 1
stopsignal      = INT
```


This configuration defines a "program" named "galaxy_uwsgi" which represents our galaxy uWSGI frontend. You'll notice that we've set a command, a directory, a umask, all of which you should be familiar with. Additionally we've specified that the process should **autostart** on boot, and **autorestart** if it ever crashes. We specify **startsecs** to say "the process must stay up for this long before we consider it OK. If the process crashes sooner than that (e.g. bad changes you've made to your local installation) supervisord will try again a couple of times to restart the process before giving up and marking it as failed. This is one of the many ways supervisord is much friendly for managing these sorts of tasks. 

Next, we set up our job handlers:

```ini
[program:handler]
command         = /path/to/galaxy/venv/bin/python ./scripts/paster.py serve config/galaxy.ini --server-name=handler%(process_num)s --pid-file=/path/to/galaxy/handler%(process_num)s.pid --log-file=/path/to/galaxy/handler%(process_num)s.log
directory       = /path/to/galaxy
process_name    = handler%(process_num)s
numprocs        = 2
umask           = 022
autostart       = true
autorestart     = true
startsecs       = 15
user            = gxprod
environment     = PYTHON_EGG_CACHE=/path/to/galaxy/.python-eggs,SGE_ROOT=/var/lib/gridengine
```


Nearly all of this is the same as above, however, you'll notice that we use `$(process_num)s`. That's a variable substitution in the command and process_name fields. We've set **numproces=2** which says to launch two handler processes. Supervisord will launch loop over `0..numprocs` and launch a `handler0` and `handler1` process automatically for us, templating out the command string so each handler receives a different log file and name.

Lastly, we collect the two tasks above into a single group:

```ini
[group:galaxy]
programs = handler, galaxy_uwsgi
```


This will let us manage these tasks more globally with the `supervisorctl` command line tool:

```console
# supervisorctl status
galaxy:handler0                  RUNNING   pid 7275, uptime 16:32:17
galaxy:handler1                  RUNNING   pid 7276, uptime 16:32:17
galaxy:uwsgi                     RUNNING   pid 7299, uptime 16:32:16
```


This command shows us the status of our jobs, and we can easily restart all of the processes at once by naming the group. Familiar commands like start and stop are also available.

```console
# supervisorctl restart galaxy:
galaxy:handler0: stopped
galaxy:handler1: stopped
galaxy:uwsgi: stopped
galaxy:uwsgi: started
galaxy:handler0: started
galaxy:handler1: started
```

### Transparent restart - Zerg Mode

The standard uWSGI operation mode allows you to restart the Galaxy application while blocking client connections. Zerg Mode does away with the waiting by running a special Zerg Pool process, and connecting Zergling workers (aka Galaxy application processes) to the pool. As long as at least one is connected, requests can be served.

See the [GCC2017 Admin Training session](https://github.com/galaxyproject/dagobah-training/blob/2017-montpellier/sessions/10-uwsgi/ex2-zerg-mode.md) on how to set this up.

## Proxy Server

If using only one web process, you can proxy as per the normal instructions for a [production configuration page](production.html).  Otherwise, you'll need to set up load balancing.

If you have specified a separate job runner and you want to use the "Manage jobs" interface as administrator you also have to define a proxy for the job runner as shown [below](#manage-jobs).

### Apache

Be sure to consult the [Apache proxy documentation](special_topics/apache.html) for additional features such as proxying static content and accelerated downloads.

#### Standalone Paste-based processes

To balance on Apache, you'll need to enable `mod_proxy_balancer` in addition to `mod_proxy`, which is available in Apache 2.2 (but not older versions such as 1.3 or 2.0).  Add the following to your Apache configuration to set up balancing for the two example web servers defined above:

```apache
<Proxy balancer://galaxy>
    BalancerMember http://localhost:8080
    BalancerMember http://localhost:8081
</Proxy>
```


And replace the following line from the [regular proxy configuration](special_topics/apache.html):

```apache
RewriteRule ^(.*) http://localhost:8080$1 [P]
```


With:

```apache
RewriteRule ^(.*) balancer://galaxy$1 [P]
```


#### uWSGI

mod_uwsgi is available in apache2.4 and later. This means you *must* be on Ubuntu 14.04 or later. There are ways to do this on older systems, which is outside the scope of this documentation. You'll need to enable `mod_uwsgi`, and then add the following to your Apache configuration:

```apache
<Location "/galaxy">
Sethandler uwsgi-handler
uWSGISocket 127.0.0.1:4001
uWSGImaxVars 512
</Location>
```


### nginx

Be sure to consult the [nginx proxy documentation](special_topics/nginx.html) for additional features such as proxying static content and accelerated downloads.

#### Standalone Paste-based processes

To proxy with nginx, you'll simply need to add all of the web applications to the `upstream` section, [which already exists](special_topics/nginx.html).  The relevant parts of the configuration would look like this:

```nginx
http {
    upstream galaxy_app {
        server localhost:8080;
        server localhost:8081;
    }
    server {
        location / {
            proxy_pass http://galaxy_app;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-For  $proxy_add_x_forwarded_for;
        }
    }
}
```


#### uWSGI

uWSGI support is built in to nginx, so no extra modules or recompiling should be required. To proxy to Galaxy, use the following configuration:

```nginx
uwsgi_read_timeout 180;

location / {
    uwsgi_pass 127.0.0.1:4001;
    uwsgi_param UWSGI_SCHEME $scheme;
    include uwsgi_params;
}
```


`uwsgi_read_timeout` can be adjusted as appropriate for your site. This is the amount of time connections will block between while nginx waits for a response from uWSGI and is useful for holding client (browser) connections while uWSGI is restarting Galaxy subprocesses.

## Notes on legacy configurations

Previously it was necessary to create two separate Galaxy config files to use multiple processes.  This is no longer necessary, and if you have multiple config files in your existing installation, it is suggested that you merge them in to a single file.

Galaxy previously used a single "job manager" process to assign jobs to handlers.  This is no longer necessary as handlers are selected by the web processes at the time of job creation.

The `track_jobs_in_database` option in `galaxy.ini` can still be set but should be unnecessary.  If there are more than one `[server:...]` sections in the file, database job tracking will be enabled automatically.

# Production Environments

The [basic installation instructions](https://getgalaxy.org) are suitable for development by a single user, but when setting up Galaxy for a multi-user production environment, there are some additional steps that should be taken for the best performance.

### Why bother?

By default, Galaxy:

* Uses [SQLite](https://www.sqlite.org/) (a serverless database), so you don't have to run/configure a database server for quick or basic development.  However, while SQLite [supports concurrent access](https://sqlite.org/lockingv3.html) it does not support multiple concurrent writes, which can reduce system throughput.
* Uses a built-in HTTP server, written in Python.  Much of the work performed by this server can be moved to [nginx](nginx.md) or [Apache](apache.md), which will increase performance.
* Runs all tools locally.  Moving to a [cluster](cluster.md) will greatly increase capacity.
* Runs in a single process, which is a performance problem in [CPython](http://en.wikipedia.org/wiki/CPython).

Galaxy ships with this default configuration to ensure the simplest, most error-proof configuration possible when doing basic development.  As you'll soon see, the goal is to remove as much work as possible from the Galaxy process, since doing so will greatly speed up the performance of its remaining duties.  This is due to the Python Global Interpreter Lock (GIL), which is explained in detail in the [Advanced Configuration](#advanced-configuration) section.

### Groundwork for scalability

#### Use a clean environment

Many of the following instructions are best practices for any production application.

* Create a **NON-ROOT** user called galaxy.  Running as an existing user will cause problems down the line when you want to grant or restrict access to data.
* Start with a fresh checkout of Galaxy, don't try to convert one previously used for development.  Download and install it in the galaxy user home directory.
* Galaxy should be a managed system service (like Apache, mail servers, database servers, *etc.*) run by the galaxy user.  Init scripts, OS X launchd definitions and Solaris SMF manifests are provided in the `contrib/` directory of the distribution.  You can also use the `--daemon` and `--stop-daemon` arguments to `run.sh` to start and stop by hand, but still run detached.  When running as a daemon the server's output log will be written to `galaxy.log` instead of the terminal, unless instructed otherwise with the `--log-file` argument.
* Give Galaxy its own database user and database to prevent Galaxy's schema from conflicting with other tables in your database.  Also, restrict Galaxy's database user so it only has access to its own database.
* Make sure Galaxy is using a clean Python interpreter. Conflicts in `$PYTHONPATH` or the interpreter's `site-packages/` directory could cause problems. Galaxy manages its own dependencies for the framework, so you do not need to worry about these. The easiest way to do this is with a [virtualenv](https://virtualenv.pypa.io/):

```
nate@weyerbacher% pip install virtualenv
nate@weyerbacher% virtualenv --no-site-packages galaxy_env
nate@weyerbacher% . ./galaxy_env/bin/activate
nate@weyerbacher% cd galaxy-dist
nate@weyerbacher% sh run.sh
```

* Galaxy can be housed in a cluster/network filesystem (it's been tested with NFS and GPFS), and you'll want to do this if you'll be running it on a [cluster](cluster.md).

## Basic configuration

The steps to install Galaxy mostly follow those of the [regular instructions](http://getgalaxy.org).  The difference is that after performing the groundwork above, you should initialize the configuration file (`cp config/galaxy.yml.sample config/galaxy.yml`) and modify it as outlined below before starting the server. If you make any changes to this configuration file while the server is running, you will have to restart the server for the changes to take effect.

### Disable the developer settings

Two options are set in the sample `config/galaxy.yml` which should not be enabled on a production server. You should set both to `false`:

* `debug: false` - Disable middleware that loads the entire response in memory for displaying debugging information in the page.  If left enabled, the proxy server may timeout waiting for a response or your Galaxy process may run out of memory if it's serving large files.
* `use_interactive: false` - Disables displaying and live debugging of tracebacks via the web.  Leaving it enabled will expose your configuration (database password, id_secret, etc.).
* Disable `filter-with: gzip`.  Leaving the gzip filter enabled will cause UI failures because of the way templates are streamed once `debug` is set to `False`.  You will still be able (and are encouraged) to enable gzip in the proxy server.

During deployment, you may run into problems with failed jobs.  By default, Galaxy removes files related to job execution. You can instruct Galaxy to keep files of failed jobs with: `cleanup_job: onsuccess`

### Switching to a database server

The most important recommendation is to switch to an actual database server.  By default, Galaxy will use [SQLite](http://www.sqlite.org/), which is a serverless simple file database engine.  Since it's serverless, all of the database processing occurs in the Galaxy process itself.  This has two downsides: it occupies the aforementioned GIL (meaning that the process is not free to do other tasks), and it is not nearly as efficient as a dedicated database server.  There are other drawbacks, too.  When load increases with multiple users, the risk of transactional locks also increases.  Locks will cause (among other things) timeouts and job errors.  If you start with SQLite and then later realize a need for a database server, you'll need to migrate your database or start over.  Galaxy does not provide an internal method to migrate data from SQLite, and although free conversion tools are available on the web, this process is non-trivial.

For this reason, Galaxy also supports [PostgreSQL](https://www.postgresql.org/) and [MySQL](https://dev.mysql.com/). *PostgreSQL is much preferred since we've found it works better with our DB abstraction layer, [SQLAlchemy](https://www.sqlalchemy.org/).*

To use an external database, you'll need to set one up. That process is outside the scope of this document, but is usually simple. For example, on Debian and Redhat-based Linux distributions, one may already be installed. If not, it should be an `apt-get install` or `yum install` away. On macOS, there are installers available from the [PostgreSQL](https://www.postgresql.org/) website.

Once installed, create a new database user and new database which the new user is the owner of.  No further setup is required, since Galaxy manages its own schema.  If you are using a UNIX socket to connect the application to the database (this is the standard case if Galaxy and the database are on the same system), you'll want to name the database user the same as the system user under which you run the Galaxy process.

To configure Galaxy, set `database_connection` in Galaxy's config file, `config/galaxy.yml`. The syntax for a database URL is explained in the [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/latest/core/engines.html).

Here follow two example database URLs with username and password:

```
postgresql://username:password@localhost/mydatabase
mysql://username:password@localhost/mydatabase
```


It's worth noting that some platforms (for example, Debian/Ubuntu) store database sockets in a directory other than the database engine's default. If you're connecting to a database server on the same host as the Galaxy server and the socket is in a non-standard location, you'll need to use these custom arguments (these are the defaults for Debian/Ubuntu, change as necessary for your installation):

```
postgresql:///mydatabase?host=/var/run/postgresql
mysql:///mydatabase?unix_socket=/var/run/mysqld/mysqld.sock
```


For more hints on available options for the database URL, see the [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls).

If you are using [MySQL](https://dev.mysql.com/) and encounter the "MySQL server has gone away" error, please note the `database_engine_option_pool_recycle` option in `config/galaxy.yml`. If this does not solve your problem, see [this post](http://gmod.827538.n3.nabble.com/template/NamlServlet.jtp?macro=print_post&node=2354941) on the Galaxy Development [mailing list](https://galaxyproject.org/mailing-lists/).

If you are using [MySQL](https://dev.mysql.com/), please make sure the database output is in UTF-8, otherwise you may encounter Python TypeErrors.

If you are using [MySQL](https://dev.mysql.com/) with [MyISAM](https://dev.mysql.com/doc/refman/8.0/en/myisam-storage-engine.html) table engine, when Galaxy is in multiprocess configuration, workflow steps will [get executed out of order](http://dev.list.galaxyproject.org/Job-execution-order-mixed-up-tt4662488.html) and fail. Use [InnoDB](https://dev.mysql.com/doc/refman/8.0/en/innodb-storage-engine.html) engine instead or switch to [PostgreSQL](https://www.postgresql.org/).

### Using a proxy server

Galaxy contains a standalone web server and can serve all of its content directly to clients.  However, some tasks (such as serving static content) can be offloaded to a dedicated server that handles these tasks more efficiently.  A proxy server also allows you to authenticate users externally using any method supported by the proxy (for example, Kerberos or LDAP), instruct browsers to cache content, and compress outbound data. Also, Galaxy's built-in web server does not support byte-range requests (required for many external display applications), but this functionality can be offloaded to a proxy server.  In addition to freeing the GIL, compression and caching will reduce page load times.

Downloading and uploading data can also be moved to the proxy server.  This is explained in the [Make the proxy handle uploads and downloads](#make-the-proxy-handle-uploads-and-downloads) section below.

Virtually any server that proxies HTTP should work, although we provide configuration examples for:

* [Apache](apache.md), and
* [nginx](nginx.md), a high performance reverse proxy, used by our public Galaxy sites

### Using a compute cluster

Galaxy is a framework that runs command-line tools, and if properly configured, can run these tools on a compute [cluster](cluster.md).  Without a cluster, you'll be limited to the number of cores in your server, minus those needed to run Galaxy itself.  Galaxy currently supports TORQUE PBS, PBS Pro, Platform LSF, and Sun Grid Engine clusters, and does not require a dedicated or special cluster configuration.  Tools can even run on heterogeneous cluster nodes (differing operating systems), as long as any dependencies necessary to run the tool are available on that platform.

Using a cluster will also net you a fringe benefit: When running tools locally, they are child processes of the Galaxy server.  This means that if you restart the server, you lose contact with those jobs, and they must be restarted.  However on the cluster, if the Galaxy server restarts, the jobs will continue to run and finish.  Once the Galaxy job manager starts up, it'll resume tracking and finishing jobs as if nothing had happened.

Configuration is not difficult once your cluster is set up.  Details can be found on the [cluster](cluster.md) page.

### Cleaning up datasets

When datasets are deleted from a history or library, it is simply marked as deleted and not actually removed, since it can later be undeleted.  To free disk space, a set of scripts can be run (e.g. from `cron`) to remove the data files as specified by local policy.  See the [Purge histories and datasets](https://galaxyproject.org/admin/config/performance/purge-histories-and-datasets/) page for instructions.

### Rotate log files

To use logrotate to rotate Galaxy log files, add a new file named `galaxy` to `/etc/logrotate.d/` directory with something like:

```
PATH_TO_GALAXY_LOG_FILES {
  weekly
  rotate 8
  copytruncate
  compress
  missingok
  notifempty
}
```


### Local Data

To get started with setting up local data, please see [Data Integration](https://galaxyproject.org/admin/data-integration/).
* All local *reference genomes* must be included in the `builds.txt` file.
* Some tools (for example, Extract Genomic DNA) require that you cache (potentially huge) local .2bit data.
* Other tools (for example, Bowtie2) require that you cache both .fasta data and tool-specific indexes.
* The `galaxy_dist/tool-data/` directory contains a set of sample location (`<data_label>.loc`) files that describe the metadata and path to local data and indexes.
* Installed tool packages from the [Tool Shed](https://galaxyproject.org/toolshed/) may also include location files.
* Comments in location files explain the expected format.
* [Data Integration](https://galaxyproject.org/admin/data-integration/) explain how to obtain, create, or rysnc many common data and indexes. See an individual Tool Shed repository's documentation for more details.

### Enable upload via FTP

File sizes have grown very large thanks to rapidly advancing sequencer technology, and it is not always practical to upload these files through the browser. Thankfully, a simple solution is to allow Galaxy users to upload them via FTP and import those files in to their histories. Configuration for FTP is explained on the [File Upload via FTP](special_topics/ftp.md) page.

## Advanced configuration

### Load balancing and web application scaling

As already mentioned, unloading work from the Galaxy process is important due to the Python [Global Interpreter Lock](https://docs.python.org/c-api/init.html#thread-state-and-the-global-interpreter-lock) (GIL). The GIL is how Python ensures thread safety, and it accomplishes this by only allowing one thread to control execution at a time. This means that regardless of the number of cores in your server, Galaxy can only use one. However, there's a solution: run multiple Galaxy processes and use the proxy server to balance across all of these processes. In practice, Galaxy is split into job handler and web server processes. Job handlers do not service any user requests directly via the web. Instead, they watch the database for new jobs, and upon finding them, handle the preparation, monitoring, running, and completion of them. Likewise, the web server processes are free to deal only with serving content and files to web clients.

Full details on how to configure scaling and load balancing can be found in the [scaling](scaling.md) documentation.

### Unloading even more work

For those readers who've already been running Galaxy on a cluster, a bit of information was recently added to the [cluster](cluster.md) documentation regarding running the data source tools on the cluster (contrary to the default configuration).  Running all tools on the cluster is strongly encouraged, so if you have not done this, please check out the new information.

### Tune the database

[PostgreSQL](https://www.postgresql.org/) can store results more efficiently than Galaxy, and as a result, reduce Galaxy's memory footprint. When a query is made, the result will remain on the Postgres server and Galaxy can retrieve only the rows it needs. To enable this, set `database_engine_option_server_side_cursors: true` in the Galaxy config.

If your server logs errors about the database connection pool size, you may need to increase the default minimum and maximum number of pool connections, 5 and 10.  These config file options are `database_engine_option_pool_size` and `database_engine_option_max_overflow`.

Finally, if you are using Galaxy <= release_2014.06.02, we recommend that you instruct Galaxy to use one database connection per thread, to avoid connection overhead and overuse.  This can be enabled with `database_engine_option_strategy: threadlocal`.

### Make the proxy handle uploads and downloads

By default, Galaxy receives file uploads as a stream from the proxy server and then writes this file to disk.  Likewise, it sends files as a stream to the proxy server.  This occupies the GIL in that Galaxy process and will decrease responsiveness for other operations in that process.  To solve this problem, you can configure your proxy server to serve downloads directly, involving Galaxy only for the task of authorizing that the user has permission to read the dataset.  If using nginx as the proxy, you can configure it to receive uploaded files and write them to disk itself, only notifying Galaxy of the upload once it's completed.  All the details on how to configure these can be found on the [Apache](apache.md) and [nginx](nginx.md) proxy instruction pages.

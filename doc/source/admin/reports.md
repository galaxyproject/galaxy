# Galaxy Reports

Galaxy includes a report tool that is separate from the main process but which gives lots of potentially useful information about the usage of a Galaxy instance, for example the numbers of jobs that have been run each month, how much disk space each user is currently consuming and so on.

## Setup on localhost

The report tool takes its configuration settings from a file called `reports.yml`, which is located in the ``config/` subdirectory of the Galaxy distribution.

Configuring the reports for your local setup is a case of:

* Making a copy of ``reports.yml.sample`` called `reports.yml`.
* Editing the `database_connection` parameter to match the one in your `galaxy.yml` file
* Optionally, editing the `port` parameter (by default the tool uses port 9001)

You should also set the 'salt' parameter `session_secret` if you intend to expose the reports via the web proxy (see below).

Then you can start the report server using `sh run_reports.sh` and view the reports by pointing a web browser running on the same server to http://127.0.0.1:9001. If you'd like the report tool to persist between sessions then use `sh run_reports.sh --daemon` to run it as a background process. As with Galaxy itself, use `--stop-daemon` to halt the background process. (The log file is written to `reports_webapp.log` if you need to try and debug a problem.)

## Expose Outside

To make your reports available from outside of the localhost using NGINX proxy server you can check out the [blogpost](http://galacticengineer.blogspot.co.uk/2015/06/exposing-galaxy-reports-via-nginx-in.html) by Peter Briggs and the [Protect Galaxy Reports](https://galaxyproject.org/admin/config/nginx-proxy/#protect-galaxy-reports) section at the [Community Hub](https://galaxyproject.org).

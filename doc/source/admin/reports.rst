Galaxy Reports
========================================

Overview
----------------------------

For admins wishing to have more information on the usage of a Galaxy instance,
one can configure and use the Galaxy Reports application. This is a separate
application that can run beside Galaxy and must target the same database.

The Galaxy Reports application's easy to use web interface will give you information on the 
following (and more):

- Jobs

    - Today's jobs
    - Jobs per day this month
    - Jobs in error per day this month
    - All unfinished jobs
    - Jobs per month
    - Jobs in error per month
    - Jobs per user
    - Jobs per tool

- Workflows

    - Workflows per month
    - Workflows per user

- Users

    - Registered users
    - Date of last login
    - User disk usage

- System

    - Disk space maintenance


Configuration
----------------------------

- Configure ``config/reports.yml`` in the same manner as your main galaxy instance (i.e., same database connection, but different web server port). This is a uWSGI YAML configuration file and should contain a ``reports`` section with app-specific configuration (options described below).

    - The default port for the reports application is ``9001``, and like Galaxy it only binds to localhost by default.
    - ``database_connection`` should match the value used in your Galaxy configuration
    - ``database_connection`` should point at a Postgres database, experimental support for MySQL is available but sqlite is not supported at all.

- Run reports in a uWSGI server with ``sh run_reports.sh``
- Use a web browser and go to the address you configured in ``reports.yml`` (defaults to http://localhost:9001/)

----------------------------
Configuration Options
----------------------------

.. include:: reports_options.rst

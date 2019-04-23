Bug Reports
===========

In 17.09, bug reports were refactored to a plugin-type infrastructure. This
gives the administrator more control over how and when bug reports are
generated. In the past, email reports would be generated when the user clicks
the button and only then. Sentry reports would be generated for every failing
tool, as soon as the tool failed. This disparate behaviour was unified under a
single configuration file, ``config/error_report.yml.sample``.

Let's look at that briefly:

.. code-block:: yaml

    - type: email
      verbose: true
      user_submission: true
    - type: sentry
      user_submission: false

The actual configuration file contains more documentation which has been
stripped out here for the sake of brevity. As you can see, there are a couple of
different plugins that already exist. Additionally, there are some options that
are common to all plugins:

``user_submission``
  When true, this action is triggered only when the user is on the job error
  page and clicks "submit bug report".

  When false, this action is triggered *any* time a job errors, without user
  involvement

``verbose``
  When ``user_submission: true``, and ``verbose: true``, this indicates that a
  message is to be displayed to the end user. For example, the email plugin will
  inform the user that an email has been sent. Similarly, the JSON plugin will
  inform the user that a file has been written to a specific directory.

Email
-----

This is the classic bug-report mechanism that we are all familiar with. It
generates an email to the admin and the submitting user containing detailed
information about the job and links to the precise locations within Galaxy.

As a plugin, nothing has changed to this functionality, though future updates
may add features. It currently takes all of its configuration from your
``$GALAXY/config/galaxy.yml``, e.g. the variables ``error_email_to`` and
``email_from``.

JSON
----

This is a demo-plugin that writes the contents of the error report to a file in
your temp directory. This just serves as a full-featured reference
implementation that others can use to build their own bug reporting plugins.

When ``user_submission: true`` and ``verbose: true``, the plugin will inform the
user that a report has been written to ``/tmp/reports/<number>``.

Sentry
------

This refactors the existing on-failure submit-to-sentry behaviour into a bug
reporting plugin. Now, for example, you are able to disable the automatic
submission to sentry and only run that whenever the user reports it.

When ``user_submission: true`` and ``verbose: true``, the plugin will inform the
user with ``Submitted bug report to Sentry. Your guru meditation number is
dc907d44ce294f78b267a56f68e5cd1a``, using the same phrasing that is common to
users from Galaxy internal server errors.

InfluxDB
--------

This sends data directly to an InfluxDB server that you have available. If you
wish to use this plugin you will first need to ``pip install influxdb`` in
Galaxy's Python virtual environment.

This plugin will send a value of ``1`` every time an error occurs, tagged with
important information such as:

- handler
- tool_id
- tool_version
- exit_code

This allows you to visualize the rate of bug reports (``group by time(30m)``,
adjust as needed for how many error reports you see) in conjunction with any
other data you're already tracking in InfluxDB/Grafana. This setup allows
answering questions such as "did the change I make decrease the number of tool
failures on average"

GitHub
------

This plugin submits user bug reports to a GitHub repository of your choice. It
uses the HTML formatter from the email bug reporter.

Before submitting a bug report, the plugin will search for any open issues with
a matching title. If there are no matching issues, it opens a new issue,
otherwise, it makes a comment on the existing issue. This provides some measure
of de-duplication.

Issues will be tagged with the tool and version.

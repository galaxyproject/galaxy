GDPR Compliance
===============

To comply with the European Union law known as General Data Protection Regulation or [GDPR](http://eur-lex.europa.eu/legal-content/en/TXT/?uri=CELEX:32016R0679) starting on May 25, 2018 there are
some extra steps you as an admin need to take to protect information of users in your Galaxy.

Audience
--------

Anyone with users from the EU.

The Galaxy Project cares about privacy preserving regulations and meeting the
requirements of law. We have attempted to make compliance as easy as possible
so you can continue to serve EU users.

Configuration
-------------

The Galaxy GDPR compliance is enabled by switching the ``gdpr_compliance`` flag available in
the configuration of Galaxy, Reports, and the Tool Shed. If you intend to serve
users from anywhere in the EU, you should set this to true. This has some
important implications of which you must be aware:

Log Redaction
-------------

We attempt to redact all occurrences of ``username`` or ``email`` in the logs. Instead
we opt to log the user ID number which cannot be reversed into personally
identifying information (PII) without access to the database. This is to
pseudonymise the data and reduce risk of PII being leaked.

We may change this redaction method to use encoded user IDs in the future.

You can configure the location of the compliance log like so:

.. code-block:: yaml

    logging:
          filters:
              stack:
                  (): galaxy.web.stack.application_stack_log_filter
          formatters:
              stack:
                  (): galaxy.web.stack.application_stack_log_formatter
              brief:
                  format: '%(asctime)s %(levelname)-8s %(name)-15s %(message)s'
          handlers:
              console:
                  class: logging.StreamHandler
                  filters:
                  - stack
                  formatter: stack
                  level: DEBUG
                  stream: ext://sys.stderr
              compliance_log:
                  class : logging.handlers.RotatingFileHandler
                  formatter: brief
                  filename: compliance.log
                  backupCount: 0
          loggers:
              COMPLIANCE:
                  handlers:
                  - compliance_log
                  level: DEBUG
                  qualname: COMPLIANCE
              galaxy:
                  handlers:
                  - console
                  level: DEBUG
                  propagate: 0
                  qualname: galaxy
              paste.httpserver.ThreadPool:
                  level: WARN
                  qualname: paste.httpserver.ThreadPool
              routes.middleware:
                  level: WARN
                  qualname: routes.middleware
          root:
              handlers:
              - console
              level: INFO
          version: 1


Which will produce logging events like this:

.. code-block:: text

    2018-05-10 18:32:20,787 INFO     COMPLIANCE      delete-user-event: f597429621d6eb2b


User Deletion
-------------

User deletion is always enabled when ``gdpr_compliance`` is enabled to comply with
the right to erasure. When users are deleted, their PII is obscured.
In practice this means:

- username
- email
- user_address (when supplied)

All have their values that constitute PII permanently redacted with a one-way
hash function.

This does not automatically remove their histories or datasets or any data they
created on the service. It is expected that following deletion the normal
Galaxy cleanup scripts will take care of this.

Backups
-------

You are responsible for ensuring that backups are deleted, or re-executing the
deletion process for all affected users following a restore.

We have added a "compliance log" which should aid in this by logging the user's
ID number, allowing you to re-delete them following a restoration. There is
currently no automation to help enforce this; you are responsible for ensuring
that when you restore services from backup, that you re-delete any PII of users
which had previously requested deletion.

Tool Shed Specific
------------------

If a user has published a tool in your toolshed, when deleting their account
their username will be redacted as well.

This will break any future updates for Galaxies consuming the tool and they
will be stuck on the old version. Additionally due to how Galaxy builds
toolshed repository paths on disk, it will break any access even if you try and
install again from this repository owned by a redacted user.

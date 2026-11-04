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

The Galaxy GDPR compliance is enabled by switching the ``enable_beta_gdpr`` flag available in
the configuration of Galaxy and the Tool Shed. If you intend to serve
users from anywhere in the EU, you should set this to true. This has some
important implications of which you must be aware:

Log Redaction
-------------

We attempt to redact all occurrences of ``username`` or ``email`` in the logs. Instead
we opt to log the user ID number which cannot be reversed into personally
identifying information (PII) without access to the database. This is to
pseudonymise the data and reduce risk of PII being leaked.

We may change this redaction method to use encoded user IDs in the future.

When a user is purged, Galaxy logs a ``delete-user-event`` record with the
user's ID to the ``COMPLIANCE`` logger, at ``INFO`` level. With the default
logging configuration, this record goes to the same destination as the rest of
Galaxy's log (see the ``log_destination`` option), even when ``log_level`` is
set higher than ``INFO``.

To write these records to a separate file instead, start from the default
logging configuration shown in :doc:`../config_logging` and add a handler and a
logger for ``COMPLIANCE`` to it. Note that the file path should be absolute and
writable by the Galaxy user, e.g.:

.. code-block:: yaml

    logging:
        # ... the rest of the default logging configuration ...
        formatters:
            # ...
            brief:
                format: '%(asctime)s %(levelname)-8s %(name)-15s %(message)s'
        handlers:
            # ...
            compliance_log:
                class: logging.handlers.RotatingFileHandler
                formatter: brief
                filename: /srv/galaxy/var/log/compliance.log
        loggers:
            # ...
            COMPLIANCE:
                handlers:
                - compliance_log
                level: INFO
                qualname: COMPLIANCE

Which will produce logging events like this:

.. code-block:: text

    2018-05-10 18:32:20,787 INFO     COMPLIANCE      delete-user-event: 42


User Deletion
-------------

User deletion is always enabled when ``enable_beta_gdpr`` is enabled to comply with
the right to erasure. When users are purged, their PII is obscured.
In practice this means:

- their username and email are replaced with a one-way hash
- their display name is removed
- their user addresses (when supplied) are deleted

Note that this is pseudonymisation, not anonymisation: the hash is computed
from the original value and the time of the purge, which is also recorded in
the compliance log. So the redacted user record, together with the compliance
log, should still be treated as personal data.

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
Make sure the compliance log is kept for at least as long as your backups are.

Tool Shed Specific
------------------

If a user has published a tool in your toolshed, when deleting their account
their username will be redacted as well.

This will break any future updates for Galaxies consuming the tool and they
will be stuck on the old version. Additionally due to how Galaxy builds
toolshed repository paths on disk, it will break any access even if you try and
install again from this repository owned by a redacted user.

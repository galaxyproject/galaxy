GDPR Compliance
===============

With the new GDPR regulations that are in effect as of May 25, 2018, there are
some extra steps you as an admin need to take to protect your Galaxy.

Audience
--------

Anyone with users from the EU.

The Galaxy Project cares about privacy preserving regulations and meeting the
requirements within. Many smaller companies in the US are choosing to block the
EU completely, this is obviously not ideal. We have attempted to make
compliance as easy as possible so you can continue to serve EU users.

Configuration
-------------

The Galaxy GDPR compliance is behind the ``gdpr_compliance`` flag available in
the configuration of Galaxy, Reports, and the Tool Shed. If you intend to serve
users from anywhere in the EU, you should set this to true. This has some
important implications of which you must be aware.

Log Redaction
-------------

We attempt to redact all occurances of username or email in the logs. Instead
we opt to log the user ID number which cannot be reversed into personally
identifying information (PII) without access to the database. This is to
pseudonymise the data and reduce risk of PII being leaked.

We may change this redaction method to use encoded user IDs in the future once
we can obtain more legal advice.

User Deletion
-------------

User deletion is forced on when ``gdpr_compliance`` is enabled, as you must be
able to comply with the right to erasure. When users are deleted, their PII is
obscured. In practice this means:

- username
- email
- user_address (when supplied)

All have their values that consitute PII permanently redacted with a one-way
hash function.

Backups
-------

You are responsible for ensuring that backups are deleted, or re-executing the
deletion process for all affected users following a restore.

We have added a "compliance log" which should aid in this by logging the user's
ID number, allowing you to re-delete them following a restoration.

Tool Shed Specific
------------------

If a user has published a tool in your toolshed, when deleting their account it
will be broken for everyone who is using it.

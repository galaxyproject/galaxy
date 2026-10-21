"""
Classes that manage resources (models, tools, etc.) by using the current
Transaction.

Encapsulates the intersection of trans (or trans.sa_session), models,
and Controllers.

Responsibilities:

- model operations that involve the trans/sa_session (CRUD)
- security: ownership, accessibility
- common aspect-oriented operations via new mixins: sharable, annotatable,
  tagable, ratable

Not responsible for:

- encoding/decoding ids
- any http gobblygook
- formatting of returned data (always python structures)
- formatting of raised errors

The goal is to have Controllers only handle:

- query-string/payload parsing and encoding/decoding ids
- http
- return formatting
- control, improve namespacing in Controllers
- DRY for Controller ops (define here - use in both UI/API Controllers)

In other words, 'Business logic' independent of web transactions/user context
(trans) should be pushed into models - but logic that requires the context
trans should be placed under this module.
"""

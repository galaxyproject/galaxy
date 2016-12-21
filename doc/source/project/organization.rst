==================================
Galaxy Core Governance
==================================

This document informally outlines the organizational structure governing the
Galaxy core code base hosted at https://github.com/galaxyproject/galaxy. This
governance extends to code-related activities of this repository such as
releases and packaging. This governance does not include infrastructure such
as Galaxy's Trello board, the Galaxy mailing lists, etc... or other Galaxy-
related projects belonging to the ``galaxyproject`` organization on GitHub.


Procedure Documents
===================

The documents whose modification requires the special process specified below
are:

- this document
- CODE_OF_CONDUCT_.


Committers
==========

The *committers* group is the group of trusted developers and advocates who
manage the core Galaxy code base. They assume many roles required to achieve
the project's goals, especially those that require a high level of trust.

Galaxy Project *committers* are the only individuals who may commit to the
core Galaxy code base. All commits must be made in accordance with procedures
outlined below. In particular, in most cases
direct commit access is not allowed and this access is restricted to merging
pull requests issued by others.

*Committers* may participate in all formal votes, including votes to modify team
membership, merge pull requests, and modify the *Procedure Documents* listed
above.

Members
-------

- Enis Afgan (@afgane)
- Dannon Baker (@dannon)
- Daniel Blankenberg (@blankenberg)
- Dave Bouvier (@davebx)
- Martin Čech (@martenson)
- John Chilton (@jmchilton)
- Dave Clements (@tnabtaf)
- Nate Coraor (@natefoo)
- Jeremy Goecks (@jgoecks)
- Björn Grüning (@bgruening)
- Aysam Guerler (@guerler)
- Jennifer Hillman Jackson (@jennaj)
- Anton Nekrutenko (@nekrut)
- Eric Rasche (@erasche)
- Nicola Soranzo (@nsoranzo)
- James Taylor (@jxtx)
- Nitesh Turaga (@nturaga)
- Marius van den Beek (@mvdbeek)

Membership
----------

The *committers* group was seeded with the group of active developers and
advocates with commit access to the repository as of May 2015. This group
subsequently voted in new members.

Any member of the *committers* group may nominate an individual for membership
to the *committers* group. Such individuals must have demonstrated:

- Good grasp of the design of Galaxy core project.
- Solid track record of being constructive and helpful.
- Significant contributions to the project.
- Willingness to dedicate some time to improving Galaxy.

The above list of people is the canonical source used to determine
membership to the *committers* group - as such new members may be added to
this group by opening a pull request adding a qualified person to this list.
Pull requests modifying the membership of this list are subject to the normal
rules for pull requests that modify governance procedures outlined below - with
one exception - a *committer* may not vote
against their own removal from the group (for obvious reasons).

Given the responsibilities and power invested in this group - it is important
that individuals not actively working on Galaxy in some fashion are removed from
the group. If individuals in this group intend to change jobs or reallocate
volunteer activities and will no longer be active in the Galaxy community,
they should withdraw from membership of this group. Periodically, active
members may review this group and request inactive members are removed - this
should not be interpreted as a condemnation of these inactive members but
merely as a reflection of a desire to keep this group focused enough to remain
effective.

Direct Commit Access
--------------------

A *committer* may only commit directly to the Galaxy repository (i.e. outside of
a pull request and not following the procedures described below) the following
two categories of changes:

* Patches for serious security vulnerabilities.
* Cherry-picking and/or merging of existing approved commits to other branches.


Release branches
================

A *release branch* is created every few months from the ``dev`` branch of the
Galaxy repository. A newly created release branch is in a *freezed* state until
the committers decide that it is ready for public consumption. At this point, a
release tag will be assigned to a commit in the branch, changing the release
state to *tagged*.


Handling Pull Requests
======================

Everyone is encouraged to express opinions and issue non-binding votes on pull
requests, but only members of the *committers* group may issue binding votes
on pull requests.

Votes on pull requests should take the form of
`+1, 0, -1, and fractions <http://www.apache.org/foundation/voting.html>`_
as outlined by the Apache Foundation.

Pull requests modifying freezed and tagged release branches should be restricted
to bug fixes. Pull requests modifying tagged release branches require at least 2
*+1* binding votes from someone other than the author of the pull request with
no *-1* binding votes.

Pull requests changing or clarifying the *Procedure Documents* (listed above):

- Must be made to the ``dev`` branch of this repository.
- Must remain open for at least 192 hours (unless every qualified *committer* has
  voted).
- Require binding *+1* votes from at least 25% of qualified *committers* with no
  *-1* binding votes.
- Should be titled with the prefix *[PROCEDURES]* and tagged with
  the *procedures* tag in Github.
- Should not be modified once open. If changes are needed, the pull request
  should be closed, re-opened with modifications, and votes reset.
- Should be restricted to just modifying the procedures and generally should not
  contain code modifications.
- If the pull request adds or removes *committers*, there must be a separate
  pull request for each person added or removed.

Any other pull request requires at least 1 *+1* binding vote from someone other
than the author of the pull request. A member of the *committers* group merging
a pull request is considered an implicit +1.

Pull requests marked *[WIP]* (i.e. work in progress) in the title by the
author(s), or tagged WIP via GitHub tags, may *not* be merged without
coordinating the removal of that tag with the pull request author(s), and
completing the removal of that tag from wherever it is present in the open pull
request.

Timelines
---------

Except in the case of pull requests modifying governance procedures, there are
generally no objective guidelines defining how long pull requests must remain
open for comment. Subjectively speaking though - larger and more potentially
controversial pull requests containing enhancements should remain open for a at
least a few days to give everyone the opportunity to weigh in.

Vetoes
------

A note on vetoes (*-1* votes) taken verbatim from the
`Apache Foundation <http://www.apache.org/foundation/voting.html>`_:

  "A code-modification proposal may be stopped dead in its tracks by a *-1* vote
  by a qualified voter. This constitutes a veto, and it cannot be overruled nor
  overridden by anyone. Vetoes stand until and unless withdrawn by their casters.

  To prevent vetoes from being used capriciously, they must be accompanied by a
  technical justification showing why the change is bad (opens a security
  exposure, negatively affects performance, etc. ). A veto without a
  justification is invalid and has no weight."

For votes regarding non-coding issues such as procedure changes, the requirement
that a veto is accompanied by a *technical* justification is relaxed somewhat,
though a well reasoned justification must still be included.

Reversions
----------

A *-1* vote on any recently merged pull request requires an immediate
reversion of the merged pull request. The backout of such a pull request
invokes a mandatory, minimum 72 hour, review period.

- Recently merged pull requests are defined as a being within the past 168 hours (7
  days), so as to not prevent forward progress, while allowing for reversions of
  things merged without proper review and consensus.
- The person issuing the *-1* vote will, upon commenting *-1* with technical
  justification per the vetoes section, immediately open a pull request to
  revert the original merge in question. If any *committer* other than the *-1*
  issuer deems the justification technical - regardless of whether they agree
  with justification - that *committer* must then merge the pull request to
  revert.

Labeling and Milestones
-----------------------

Pull request handling, labeling, and milestone usage follows the procedures
described in ISSUES_.


Issue Reporting
===============

Issues (bugs, feature requests, etc.) should be reported at ISSUE_REPORT_, and
handling of issues follows the procedures described in ISSUES_.


.. _LICENSE: https://github.com/galaxyproject/galaxy/blob/dev/LICENSE.txt
.. _CODE_OF_CONDUCT: https://github.com/galaxyproject/galaxy/blob/dev/CODE_OF_CONDUCT.md
.. _ISSUES: https://github.com/galaxyproject/galaxy/blob/dev/doc/source/project/issues.rst
.. _ISSUE_REPORT: https://github.com/galaxyproject/galaxy/issues/

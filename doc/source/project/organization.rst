==================================
Galaxy Core Governance
==================================

This document informally outlines the organizational structure governing the
Galaxy core code base hosted at https://github.com/galaxyproject/galaxy . This
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
- SECURITY_POLICY_.


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
- Ahmed Awan (@ahmedhamidawan)
- Dannon Baker (@dannon)
- Matthias Bernt (@bernt-matthias)
- Daniel Blankenberg (@blankenberg)
- Martin Čech (@martenson)
- John Chilton (@jmchilton)
- Nate Coraor (@natefoo)
- John Davis (@jdavcs)
- Jeremy Goecks (@jgoecks)
- Nuwan Goonasekera (@nuwang)
- Björn Grüning (@bgruening)
- Aysam Guerler (@guerler)
- Alireza Heidari (@itisAliRH)
- Jennifer Hillman Jackson (@jennaj)
- David López (@davelopez)
- Laila Los (@ElectronicBlueberry)
- Anton Nekrutenko (@nekrut)
- Helena Rasche (@hexylena)
- Nicola Soranzo (@nsoranzo)
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

The above list of people is the canonical source used to determine membership to
the *committers* group - as such new members may be added to this group by
opening a pull request adding a qualified person to this list. Pull requests
modifying the membership of this list are subject to the normal rules for pull
requests that modify governance procedures outlined below, with one exception: a
*committer* may not vote against their own removal from the group (for obvious
reasons).

Given the responsibilities and power invested in this group, it is important
that individuals not actively working on Galaxy anymore are removed from the
group. If individuals in this group intend to change jobs or reallocate
volunteer activities and will no longer be active in the Galaxy community, they
should withdraw from membership of this group. Periodically, active members may
review this group and request that inactive members are removed - this should
not be interpreted as a condemnation of these inactive members but merely as a
reflection of the desire to keep this group focused enough to remain effective.



Direct Commit Access
--------------------

A *committer* may only commit directly to the Galaxy repository (i.e. outside of
a pull request and not following the procedures described below) the following
four categories of changes:

* Patches for serious security vulnerabilities.
* Cherry-picking and/or merging of existing approved commits to other branches.
* Everything under ``packages/`` .
* Release notes and changelogs.


Release branches
================

A *release branch* is created every few months from the ``dev`` branch of the
Galaxy repository. A newly created release branch is in a *frozen* state until
the committers decide that it is ready for public consumption. At this point, a
release tag will be assigned to a commit in the branch, changing the release
state to *tagged*.


Handling Pull Requests
======================

Everyone is encouraged to express opinions and issue non-binding votes on pull
requests, but only members of the *committers* group may issue binding votes
on pull requests.

Votes on pull requests should take the form of +1, 0, -1, and fractions as
outlined by the `Apache Software Foundation voting rules`_. The following are
equivalent to a +1 vote:

- a `thumbs up reaction <https://blog.github.com/2016-03-10-add-reactions-to-pull-requests-issues-and-comments/>`__
  on the pull request description;
- approving the pull request when submitting a
  `review <https://help.github.com/articles/reviewing-proposed-changes-in-a-pull-request/>`__.

The latter is the preferred method because it is integrated in GitHub, it allows
tracking the moment when the review was submitted, and it sends a notification
to subscribers.

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
- Members of the *committers* group may submit PRs updating their own name or
  username in the ``members`` section of this file.  This type of change is not
  subject to the 192 hour nor 25% rule, and can be merged by any other member.

Any other pull request requires at least 1 *+1* binding vote from someone other
than the author of the pull request. A member of the *committers* group merging
a pull request is considered an implicit +1.

Pull requests modifying frozen and tagged release branches should be restricted
to bug fixes. As an exception, pull requests which only add new datatypes can
target a frozen branch or the latest tagged release branch.

A pull request marked *[WIP]* (i.e. work in progress) in the title by its
author(s) may *not* be merged without coordinating the removal of that mark with
the pull request author(s). Nevertheless, pull request authors should normally
use the `draft <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests#draft-pull-requests>`__
state to indicate a work-in-progress pull request.

Timelines
---------

Except in the case of pull requests modifying governance procedures, there are
generally no objective guidelines defining how long pull requests must remain
open for comment. Subjectively speaking though - larger and more potentially
controversial pull requests containing enhancements should remain open for a at
least a few days to give everyone the opportunity to weigh in.

Vetoes
------

A note on vetoes (*-1* votes), taken verbatim from the
`Apache Software Foundation voting rules`_:

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

Pull request labeling and milestone usage follows the procedures described in
:doc:`Galaxy Issue Management <issues>`.


Issue Reporting
===============

Issues (bugs, feature requests, etc.) should be reported and handled as
described in :doc:`Galaxy Issue Management <issues>`.


.. _CODE_OF_CONDUCT: https://github.com/galaxyproject/galaxy/blob/dev/CODE_OF_CONDUCT.md
.. _SECURITY_POLICY: https://github.com/galaxyproject/galaxy/blob/dev/SECURITY.md
.. _Apache Software Foundation voting rules: https://www.apache.org/foundation/voting.html

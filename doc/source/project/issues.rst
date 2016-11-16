=======================
Galaxy Issue Management
=======================

The purpose of this document is to formalize how we manage the full
cycle (reporting, tracking progress, resolution) of both
feature/enhancement ideas and bugs, as well as providing a few general
guidelines for longer term planning for various Galaxy related projects.
Some inspiration taken from the way the
`Docker <https://github.com/docker/docker>`__ project labels issues.

Milestones
==========

Every pull request should, prior to merge, be assigned to the milestone
corresponding to the Galaxy release it will first appear in (15.10,
16.01, and so on). This, along with the tags applied, will be used to
generate the release notes.

Any non-PR issue assigned to a milestone *must* be resolved or
reassigned prior to publishing that release. This is the primary
mechanism by which we force reconciliation (issue/bug fixed, closed, or
intentionally postponed) prior to release, and prevent things falling
through the cracks. In practice, bugs should almost always be tagged
with a milestone which forces the reconciliation date. Issues *may* be,
but they don't necessarily have to be -- this is subjective and it
depends on whether or not the issue should be revisited prior to the
corresponding release.

Effective use of milestones should prevent bugs from falling through the
cracks, and will provide a mechanism for forcing the revisitation(and
thus progress or even potential discard) of ideas for enhancements or
features.

Deferring Issues
----------------

To prevent the review of issues attached to milestones from becoming too
cumbersome, and to encourage active review and handling of issues, any
contributor can choose to 'defer' an issue attached to an upcoming
release milestone to a later one. To do this, simply reassign the issue
to the new milestone and leave a comment so that others notice,
something like 'Issue deferred to target\_milestone\_reference, does not
block release current\_milestone\_reference'.

Once deferred, an issue can't simply be reattached back to the earlier
milestone -- this requires a PR. The intent here is to make it such that
if a contributor wants to force an issue to be handle with a release,
they need to put the work forward to do so or convince someone else to.

Labeling Structure
==================

To allow for easy search, filtering, and general issue management every
issue or PR (not tagged ``procedures`` or ``planning``) is *required* to
have three labels which indicate the type, status, and focus area of the
issue. Any issue without these three tags will be automatically have a
``triage`` label applied indicating that it needs human intervention to
be correctly tagged. These ``triage`` tagged issues will be regularly
reviewed and tagged as appropriate.

Kind Labels
-----------

The 'kind' label set is used for classifying the type of contribution or
request/report to separate enhancements and new features from bugs, etc.

-  ``kind/bug`` - something is broken, and it needs fixing
-  ``kind/enhancement`` - polish to an existing feature or interface
-  ``kind/feature`` - something brand new
-  ``kind/refactoring`` - refactoring of existing code, no functional
   changes
-  ``kind/testing`` - issues related to tests and the testing framework

Status Labels
-------------

The ``status`` of an issue or PR should be tracked using the following
labels:

-  ``status/planning`` - the issue planning phase, this issue may
   potentially need more information (or just more thinking) to proceed
   to a work in progress
-  ``status/WIP`` - this issue or PR is currently being worked on and in
   the case of a PR, it should not be merged until this tag is removed
-  ``status/review`` - PR is complete and ready for review, or when
   applied to an issue it is thought to be resolved but needs
   verification

We use the same set of status tags for PRs and issues to keep things
simple, but not every PR or issue needs to go through every state. For
example, it'll be common for a PR to be submitted with the label
'status/review', and get merged without needing to go through the rest
of the states.

Note that there are no ``status/complete``, ``status/wontfix``,
``status/duplicate``, or other terminal status indicators. This is
intentional to keep the tail end of bookkeeping from getting onerous.
These sorts of terminal states *and their justifications* (e.g. the
reason why it's a wontfix, or a reference to the duplicate issue) should
be indicated in the closing comment by the issue closer.

Area Labels
-----------

The 'area' label is used for tagging issues and pull requests to a
particular focus area. This allows for easy searching within that
particular domain, as well as more organized release notes.

-  ``area/admin`` - Changes to admin functionality of the Galaxy webapp.
-  ``area/API``
-  ``area/cleanup`` - General code cleanup.
-  ``area/database`` - Change requires a modification to Galaxy's database.
-  ``area/dataset-collections``
-  ``area/datatypes`` - Changes to Galaxy's datatypes
-  ``area/datatype-framework`` - Changes to Galaxy's datatype and metadata framework
-  ``area/documentation``
-  ``area/framework``
-  ``area/GIEs``
-  ``area/histories``
-  ``area/jobs``
-  ``area/performance``
-  ``area/reports``
-  ``area/system`` - Changes to scripts used to run or manage Galaxy.
-  ``area/tools`` - Changes to specific tools in Galaxy.
-  ``area/tool-framework``
-  ``area/toolshed``- Changes to the tool shed client or server.
-  ``area/UI-UX``
-  ``area/util``
-  ``area/visualizations``
-  ``area/workflows``

New labels should be proposed by opening a pull request against this document
in the dev branch of Galaxy.

Other Useful Labels
-------------------

While the three labels sets indicating kind, status, and area are
required there are several other labels that are be useful and/or have
special purpose.

-  ``procedures`` is a special tag that indicates that the issue is
   related to project governance, and it overrides the need for the trio
   of kind/status/area tags, and these are never auto-flagged for
   triage.  More details are available in the ORGANIZATION_ document.

-  ``planning`` is also a special tag that indicates the issue is
   related to larger-scale issue planning. These issues are typically
   meta-issues containing checklists and references to other issues
   which are subcomponents and stepping stones necessary for issue
   resolution. These *can* utilize the ``area/*`` tags but are not
   required to. Status and type make little sense here.

-  ``roadmap`` is a reserved tag for the primary project roadmap. This
   is a meta-issue that is not expected to be completed, but rather
   serves as an entry point to the high level development of the
   project.

-  ``friendliness/beginner`` can be used to indicate a nice entry-level
   issue that only requires limited understanding of the larger Galaxy
   framework and ecosystem. This is useful for encouraging new
   contributors.
   
-  ``friendliness/intermediate`` can be used to indicate an advanced
   level issue that requires decent understanding of the larger Galaxy
   framework and system.
         
-  ``friendliness/unfriendly`` can be used to mark issues that require
   deep understanding of the framework and/or exquisite programming
   abilities.

-  ``minor`` is a special tag used to generate release notes. It should
   only be applied to pull requests made by committers that fix
   functionality modified during the same release cycle. Such fixes are
   unimportant for release notes. No pull request issued by someone
   outside the committers group should have this tag applied because
   these pull requests must be highlighted in the release notes.

-  ``major`` is a special tag used to generate release notes. In practice
   this should be applied to at most a couple dozen pull requests each
   release and is used to prioritize important items of note for the
   top of release notes sections.
   
-  ``merge`` tag used to indicate PR that only merges a change that has
   been previously added. Used to filter things out of release notes.
   
-  ``feature-request`` is used to indicate a request for change or feature.

-  ``triage`` is a tag automatically added by a GalaxyBot to indicate that
   the issue needs to be evaluated and properly tagged.
   
-  ``hacktoberfest`` is a tag that encourages contributions to Galaxy codebase
   by including these issues in the `Hacktoberfest <https://hacktoberfest.digitalocean.com/>`__ event.
   Similar to ``friendliness/beginner`` tag in other characteristics.


The Roadmap
===========

We will maintain a single ``roadmap`` tagged meta-issue which will
describe (at a very high level) the *current* major areas of focus for
the project. This is similar to our PRIORITIES 2014/15 cards on Trello.
Using `Task
Lists <https://github.com/blog/1375-task-lists-in-gfm-issues-pulls-comments>`__,
this issue will link to sub-issues which will go into much more detail,
might have its own checklists to even more subcomponent cards, and so
on.

This ``roadmap`` issue will be assigned to every release milestone,
forcing periodic review of the roadmap.

Voting
======

Users can vote for issues by commenting with a +1. It's possible to sort
the issue list by 'most commented' which would be a good indicator of
what issues are 'hot', though this doesn't necessarily indicate a high
vote. It's possible that that this is good enough and in some ways
potentially more useful to find 'hot' issues than a flat vote count.

Automation
==========

For now, we will rely on a few simple automation rules:

-  All issues, unless tagged ``procedures`` or ``planning`` will
   automatically be tagged ``triage``, indicating that they require
   attention.

-  All PRs that are not assigned to a milestone will be tagged
   ``triage`` to indicate that they require attention prior to merge.

.. _ORGANIZATION: https://github.com/galaxyproject/galaxy/blob/dev/doc/source/project/organization.rst

=======================
Galaxy Issue Management
=======================

The purpose of this document is to formalize how we manage the full
cycle (reporting, tracking progress, resolution) of both
feature/enhancement ideas and bugs, as well as providing a few general
guidelines for longer term planning for various Galaxy related projects.
Some inspiration taken from the way the
`Docker <https://github.com/docker/docker>`__ project labels issues.

Issue Reporting
===============

Issues (bugs, feature requests, etc.) should be reported at `GitHub issues`_, and
handling of issues follows the procedures described in this document.

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
issue or PR (not tagged ``procedures`` or ``planning``) is expected to
have two labels which indicate the type (``kind/``) and focus
area (``area/``) of the issue. Any issue without these tags will
automatically have a ``triage`` label applied indicating that it needs
human intervention to be correctly tagged. These ``triage`` tagged
issues will be regularly reviewed and tagged as appropriate.

Kind Labels
-----------

The ``kind`` label set is used for classifying the type of contribution or
request/report to separate enhancements and new features from bugs, etc.

-  ``kind/bug`` - something is broken, and it needs fixing
-  ``kind/enhancement`` - polish to an existing feature or interface
-  ``kind/feature`` - something brand new
-  ``kind/refactoring`` - cleanup or refactoring of existing code, no
   functional changes

Status Labels
-------------

The default status of an issue or PR is "ready for review". If that is not the
case, the state should be communicated as follows:

- for issues, by using the ``status/planning`` label;
- for PRs, by using the `draft <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests#draft-pull-requests>`__
  state.

Note that there are no ``status/complete``, ``status/wontfix``,
``status/duplicate``, or other terminal status indicators. This is
intentional to keep the tail end of bookkeeping from getting onerous.
These sorts of terminal states *and their justifications* (e.g. the
reason why it's a wontfix, or a reference to the duplicate issue) should
be indicated in the closing comment by the issue closer.

The following statuses may be applied to issues that need to be revisited
after some event.

- ``status/needs feedback`` - this issue or pull request is waiting for
  a response from the author. The issue or pull request may be assumed stale
  and closed after a month. The committers reserve the right to close issues
  and pull requests without this process, but this tag makes tracking explicit
  and easy.

Area Labels
-----------

The ``area`` label is used for tagging issues and pull requests to a
particular focus area. This allows for easy searching within that
particular domain, as well as more organized release notes.

- ``area/admin`` - Changes to admin functionality of the Galaxy webapp
- ``area/API``
- ``area/auth`` - Authentication and authorization
- ``area/client-build``
- ``area/compliance``
- ``area/configuration`` - Galaxy's configuration system
- ``area/cwl`` - changes related to supporting the common workflow language in Galaxy
- ``area/database`` - Change to Galaxy's database or data access layer
- ``area/dataset-collections``
- ``area/datatypes`` - Changes to Galaxy's datatypes
- ``area/datatype-framework`` - Changes to Galaxy's datatype and metadata framework
- ``area/dependencies`` - Changes related to Python or JavaScript dependencies of Galaxy itself
- ``area/documentation``
- ``area/framework``
- ``area/histories``
- ``area/i18n`` - Internationalization and localization
- ``area/interactive-tools``
- ``area/jobs``
- ``area/jobs/kubernetes``
- ``area/libraries`` - Change related to data libraries
- ``area/objectstore``
- ``area/performance``
- ``area/reports`` - The reports webapp
- ``area/rules`` - Rule builder
- ``area/security``
- ``area/scripts`` - Changes to scripts used to run or manage Galaxy.
- ``area/testing``
- ``area/testing/api``
- ``area/testing/integration``
- ``area/testing/selenium``
- ``area/tool-framework``
- ``area/tool-dependencies`` - Changes to dependency resolution (including Conda)
- ``area/tools`` - Changes to specific tools in Galaxy
- ``area/toolshed``- Changes to the Tool Shed client or server
- ``area/UI-UX``
- ``area/upload``
- ``area/util``
- ``area/visualizations``
- ``area/webhooks``
- ``area/workflows``
- ``area/workflows/editor``
- ``area/workflows/reports``
- ``area/workflows/subworkflows``

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
   triage. More details are available in the
   :doc:`Galaxy Core Governance <organization>` document.

-  ``planning`` is also a special tag that indicates the issue is
   related to larger-scale issue planning. These issues are typically
   meta-issues containing checklists and references to other issues
   which are subcomponents and stepping stones necessary for issue
   resolution. These *can* utilize the ``area/*`` tags but are not
   required to. Status and type make little sense here.

-  ``friendliness/beginner`` can be used to indicate a nice entry-level
   issue that only requires limited understanding of the larger Galaxy
   framework and ecosystem. This is useful for encouraging new
   contributors. This tag may alternatively be called ``help wanted``.
   ``hacktoberfest`` or ``paper-cut`` are event specific tags that denote
   similar things about an issue.

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

- ``confirmed`` is a tag that should only be applied to issues that also have
  ``kind/bug``. The ``confirmed`` tag indicates a committer has verified the
  bug affects the actual current Galaxy development branch and isn't a usage
  issue, a previously fixed issue, etc..

- ``highlight`` is a tag that indicates at least one contributor thinks this
   pull request should be highlighted in some way in the relevant release's
   release notes. The person assembling release notes has final say about
   which pull requests are actually highlighted.

- ``highlight/user`` is a tag that indicates assigner of the tag thinks this
   pull request should be highlighted prominently in the relevant release's
   user facing release notes. The assigner of this tag is giving a strong
   endorsement of this highlight and is willing to do the work of writing
   the blurb for the release notes. If selected, the blurb should be written
   with target audience in mind - researchers using the Galaxy user interface.
   The person assembling the user release notes has final say about which
   pull requests are actually highlighted.

The Roadmap
===========

We will maintain a single ``roadmap`` GitHub project which will
describe (at a very high level) the *current* major areas of focus for
the project. This project will link to issues and PRs, which will go into
much more detail and might link to other sub-issues, projects, or PRs.

This ``roadmap`` project is subject to periodic review every release.

The current roadmap project is `here <https://github.com/galaxyproject/galaxy/projects/8>`__.

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

-  All PRs, unless tagged ``procedures`` or ``planning`` will
   automatically be tagged ``triage``, indicating that they require
   attention.

-  All PRs that are not assigned to a milestone will be tagged
   ``triage`` to indicate that they require attention prior to merge.

.. _Github issues: https://github.com/galaxyproject/galaxy/issues/

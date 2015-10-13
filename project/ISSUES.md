Galaxy Issue Management
=======================

The purpose of this document is to formalize how we manage the full cycle
(reporting, tracking progress, resolution) of both feature/enhancement ideas
and bugs, as well as providing a few general guidelines for longer term
planning for various Galaxy related projects.  Significant inspiration taken
from the way the [Docker](https://github.com/docker/docker) project manages
issues.

We've tried several different approaches over the course of the project and two
common problems we've tried to address in this approach are:

* The issue graveyard -- where, once off the first 'page' of issues or below
  the 'fold' in Trello, things sometimes do not resurface and are lost to
  history.

* Difficulty clearly presenting and maintaining a high level project roadmap
  and associated meta-issues.


Milestones
==========

Every pull request should, prior to merge, be assigned to the milestone
corresponding to the Galaxy release it will first appear in (15.10, 16.01, and
so on).  This, along with the tags applied, will be used to generate the
release notes.

Any non-PR issue assigned to a milestone *must* be resolved or reassigned prior
to publishing that release -- that is, this is the new way to create and track
"Issues Blocking Release".  This will be a primary way to report bugs and force
them to be reconciled (fixed, closed, or intentionally postponed) prior to
release.  In practice, bugs should almost always be tagged with a milestone
which forces the reconciliation date.  Issues *may* be, but they don't
necessarily have to be -- this is subjective and it depends on if the submitter
(or any other contributor) wants to force the issue to be revisited at the next
release.

Effective use of milestones should prevent bugs from falling through the
cracks, and will provide a mechanism for forcing the revisitation(and thus
progress or even potential discard) of ideas for enhancements or features.


Labeling Structure
==================

To allow for easy search, filtering, and general issue management every issue
or PR (not tagged `Procedures` or `Planning`) is *required* to have three
labels which indicate the type, status, and focus area of the issue.  Any issue
without these three tags will be automatically have a `triage` label applied
indicating that it needs human intervention to be correctly tagged.  These
`triage` tagged issues will be regularly reviewed and tagged as appropriate.

Kind Labels
-----------

The 'kind' label set is used for classifying the type of contribution or
request/report to separate enhancements and new features from bugs, etc.

* `kind/bug` - something is broken, and it needs fixing
* `kind/documentation` - documentation is unclear or can be improved
* `kind/enhancement` - polish to an existing feature or interface
* `kind/feature` - something brand new
* `kind/refactoring` - refactoring of existing code, no functional changes

Status Labels
-------------

The `status` of an issue or PR should be tracked using the following labels:

* `status/planning` - the issue planning phase, this issue may potentially need
  more information (or just more thinking) to proceed to a work in progress
* `status/WIP` - this issue or PR is currently being worked on and in the case
  of a PR, it should not be merged until this tag is removed
* `status/review` - PR is complete and ready for review, or when applied to an
  issue it is thought to be resolved but needs verification

We use the same set of status tags for PRs and issues to keep things simple,
but not every PR or issue needs to go through every state.  For example, it'll
be common for a PR to be submitted with the label 'status/review', and get
merged without needing to go through the rest of the states.

Note that there are no `status/complete`, `status/wontfix`, `status/duplicate`,
or other terminal status indicators.  This is intentional to keep the tail end
of bookkeeping from getting onerous.  These sorts of terminal states *and their
justifications* (e.g. the reason why it's a wontfix, or a reference to the
duplicate issue) should be indicated in the closing comment by the issue
closer.


Area Labels
------------

The 'area' label is used for tagging issues and pull requests to a particular
focus area.  This allows for easy searching within that particular domain, as
well as more organized release notes.  Some examples, not-exhaustive, are here:

* `area/API`
* `area/cleanup`
* `area/jobs`
* `area/tests`
* `area/GIEs`
* `area/toolshed`
* `area/UI-UX`
* `area/workflows`

This list will definitely grow over time.

Other Useful Labels
-------------------

While the three labels sets indicating kind, status, and area are required
there are several other labels that are be useful and/or have special purpose.

* `procedures` is a special tag that indicates that the issue is related to
  project governance, and it overrides the need for the trio of
  kind/status/area tags, and these are never auto-flagged for triage.

* `planning` is also a special tag that indicates the issue is related to
  larger-scale issue planning.  These issues are typically meta-issues
  containing checklists and references to other issues which are subcomponents
  and stepping stones necessary for issue resolution.  These *can* utilize the
  `area/*` tags but are not required to.  Status and type make little sense
  here.

* `roadmap` is a reserved tag for the primary project roadmap.  This is a
  meta-issue that is not expected to be completed, but rather serves as an
  entry point to the high level development of the project.

* `beginner-friendly` can be used to indicate a nice entry-level issue that
  only requires limited understanding of the larger Galaxy framework and
  ecosystem.  This is useful for encouraging new contributors.


The Roadmap
===========

We will maintain a single `Roadmap` tagged meta-issue which will describe (at a
very high level) the *current* major areas of focus for the project.  This is
similar to our PRIORITIES 2014/15 cards on Trello.  Using [Task
Lists](https://github.com/blog/1375-task-lists-in-gfm-issues-pulls-comments),
this issue will link to sub-issues which will go into much more detail, might
have its own checklists to even more subcomponent cards, and so on.  

This `Roadmap` issue will be assigned to every release milestone, forcing
periodic review of the roadmap.

To prevent the roadmap from being tied completely to GitHub, and to facilitate
portable change tracking over time, we will also maintain the file
project/ROADMAP.md within the repository.  Whenever the ROADMAP issue text is
changed, ROADMAP.md should be updated correspondingly.

This document won't have the organizational integration that a live GitHub
issue does, but this way we're be able to have a ROADMAP.md permanently
attached to the code regardless of what issue tracking or organizational
software we use in the future.


Voting
======

Users can vote for issues by commenting with a +1.  It's possible to sort the
issue list by 'most commented' which would be a good indicator of what issues
are 'hot', though this doesn't necessarily indicate a high vote.  It's possible
that that this is good enough and in some ways potentially more useful to find
'hot' issues than a flat vote count.


Automation
==========

For now, we will rely on a few simple automation rules:

* All issues, unless tagged `Procedures` or `Planning` will automatically be
  tagged `triage`, indicating that they require attention.

* All PRs that are not assigned to a milestone will be tagged `triage` to
  indicate that they require attention prior to merge.

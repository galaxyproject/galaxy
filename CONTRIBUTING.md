# Contributing

This document briefly describes how to contribute to the [core
galaxy project](https://github.com/galaxyproject/galaxy) -
also checkout our 2013 Galaxy Community
Conference presentation on the topic
([video](https://vimeo.com/channels/581875/73486255),
[presentation](https://wiki.galaxyproject.org/Documents/Presentations/GCC2013?action=AttachFile&do=view&target=BakerContribute.pdf)). For
information on contributing more broadly to the Galaxy ecosystem and a
deeper discussion of some of these points - please see the
[Develop](https://wiki.galaxyproject.org/Develop/) section of the
[Galaxy Wiki](https://wiki.galaxyproject.org/).

## Before you Begin

If you have an idea for a feature to add or an approach for a bugfix,
it is best to communicate with Galaxy developers early. The most
common venues for this are
[GitHub issues](https://github.com/galaxyproject/galaxy/issues) and the
[Galaxy and Tool Shed Trello boards](https://wiki.galaxyproject.org/Issues).
Browse through existing GitHub issues and Trello cards and if one seems related,
comment on it. If no existing issue/card seems appropriate, a new issue can be
opened using [this form](https://github.com/galaxyproject/galaxy/issues/new). Galaxy
developers are also generally available via
[IRC](https://wiki.galaxyproject.org/GetInvolved#IRC_Channel) and on
the [development mailing list](http://dev.list.galaxyproject.org/).

## How to Contribute

* All changes to the [core galaxy project](https://github.com/galaxyproject/galaxy)
  should be made through pull requests to this repository (with just two
  exceptions outlined below).

* If you are new to Git, the [Try Git](http://try.github.com/) tutorial is a good places to start.
  More learning resources are listed at https://help.github.com/articles/good-resources-for-learning-git-and-github/ .

* Make sure you have a free [GitHub](https://github.com/) account.

* Fork the [galaxy repository](https://github.com/galaxyproject/galaxy) on
  GitHub to make your changes.
  (While many Galaxy instances track
  [galaxy-dist](https://bitbucket.org/galaxy/galaxy-dist), active development
  happens in the galaxy GitHub repository and this is where pull requests
  should be made).

* Choose the correct branch to develop your changes against.

  * Additions of new features to the code base should be pushed to the `dev` branch (`git
    checkout dev`).

  * Most bug fixes to previously release components (things in galaxy-dist)
    should be made against the recent `release_XX.XX` branch (`git checkout release_XX.XX`).

  * Serious security problems should not be fixed via pull request - please
    responsibly disclose these by e-mailing them (with or without patches) to
    galaxy-committers@lists.galaxyproject.org . The Galaxy core development team will
    issue patches to public servers before announcing the issue to ensure there
    is time to patch and highlight these fixes widely. We will provide you
    credit for the discovery when publicly disclosing the issue.

* If your changes modify code - please ensure the resulting files
  conform to Galaxy [style
  guidelines](https://wiki.galaxyproject.org/Develop/BestPractices).

* Galaxy contains hundreds of tests of different types and complexity
  and running each is difficult and probably not reasonable at this
  time (someday we will provide a holistic test procedure to make this
  possible). For now, please just review the [running tests
  documentation](https://wiki.galaxyproject.org/Admin/RunningTests)
  and run any that seem relevant. Developers reviewing your pull
  request will be happy to help guide you to running the most relevant
  tests as part of the pull request review process and may request the
  output of these tests.

* Commit and push your changes to your
  [fork](https://help.github.com/articles/pushing-to-a-remote/).

* Open a [pull
  request](https://help.github.com/articles/creating-a-pull-request/)
  with these changes. You pull request message ideally should include:

   * A description of why the changes should be made.

   * A description of the implementation of the changes.

   * A description of how to test the changes.

* The pull request should pass all the continuous integration tests which are
  automatically run by GitHub using e.g. Travis CI.

## Ideas

Galaxy's [Trello board](http://bit.ly/gxytrello) is filled with bugs and ideas
for enhancements, but we maintain a [card](https://trello.com/c/eFdPIdIB) with
links to smaller issues we believe would make the best entry points for new
developers.

## A Quick Note about Tools

  For the most part, Galaxy tools should be published to the
  [Tool Shed](https://wiki.galaxyproject.org/ToolShed) and not in this
  repository directly. If you are looking to supply fixes for migrated
  core tools that used to exist in this repository - please checkout
  the [tools-devteam](https://github.com/galaxyproject/tools-devteam)
  repository on GitHub.

  More information about tool development can be found [on the
  wiki](https://wiki.galaxyproject.org/Develop).

## Handling Pull Requests

Everyone is encouraged to express opinions and issue non-binding votes on pull
requests, but only members of the *committers* group may issue binding votes
on pull requests. Information on the *committers* group can be found in the
[organization document](https://github.com/galaxyproject/galaxy/blob/dev/doc/source/project/organization.rst)
describing governance of the core Galaxy code base.

Votes on pull requests should take the form of
[+1, 0, -1, and fractions](http://www.apache.org/foundation/voting.html)
as outlined by the Apache Foundation.

Pull requests modifying pre-existing releases should be restricted to bug fixes
and require at least 2 *+1* binding votes from someone other than the author of
the pull request with no *-1* binding votes.

Pull requests changing or clarifying the procedures governing this repository:

- Must be made to the ``dev`` branch of this repository.
- Must remain open for at least 192 hours (unless every qualified committer has
  voted).
- Require binding *+1* votes from at least 25% of qualified *committers* with no
  *-1* binding votes.
- Should be titled with the prefix *[PROCEDURES]* and tagged with
  the *procedures* tag in Github.
- Should not be modified once open. If changes are needed, the pull request
  should be closed, re-opened with modifications, and votes reset.
- Should be restricted to just modifying the procedures and generally should not
  contain code modifications.
- If the pull request adds or removes committers, there must be a separate
  pull request for each person added or removed.

Any other pull request requires at least 1 *+1* binding vote from someone other
than the author of the pull request. A member of the committers group merging a
pull request is considered an implicit +1.

Pull requests marked *[WIP]* (i.e. work in progress) in the title by the
author(s), or tagged WIP via GitHub tags, may *not* be merged without
coordinating the removal of that tag with the pull request author(s), and
completing the removal of that tag from wherever it is present in the open pull
request.

### Timelines

Except in the case of pull requests modifying governance procedures, there are
generally no objective guidelines defining how long pull requests must remain
open for comment. Subjectively speaking though - larger and more potentially
controversial pull requests containing enhancements should remain open for a at
least a few days to give everyone the opportunity to weigh in.

### Vetoes

A note on vetoes (*-1* votes) taken verbatim from the
[Apache Foundation](http://www.apache.org/foundation/voting.html):

>"A code-modification proposal may be stopped dead in its tracks by a -1 vote
by a qualified voter. This constitutes a veto, and it cannot be overruled nor
overridden by anyone. Vetoes stand until and unless withdrawn by their casters.
>
>To prevent vetoes from being used capriciously, they must be accompanied by a
technical justification showing why the change is bad (opens a security
exposure, negatively affects performance, etc. ). A veto without a
justification is invalid and has no weight."

For votes regarding non-coding issues such as procedure changes, the requirement
that a veto is accompanied by a *technical* justification is relaxed somewhat,
though a well reasoned justification must still be included.

### Reversions

A *-1* vote on any recently merged pull request requires an immediate
reversion of the merged pull request. The backout of such a pull request
invokes a mandatory, minimum 72 hour, review period.

- Recently merged pull requests are defined as a being within the past 168 hours (7
  days), so as to not prevent forward progress, while allowing for reversions of
  things merged without proper review and consensus.
- The person issuing the -1 vote will, upon commenting `-1` with technical
  justification per the vetoes section, immediately open a pull request to
  revert the original merge in question. If any committer other than the -1
  issuer deems the justification technical - regardless of whether they agree
  with justification - that committer must then merge the pull request to
  revert.

### Direct Commit Access

The Galaxy *committers* group may only commit directly to Galaxy (i.e.  outside
of a pull request and not following the procedures described here) the
following two categories of patches:

* Patches for serious security vulnerabilities.
* Cherry-picking and/or merging of existing approved commits to other 
branches.

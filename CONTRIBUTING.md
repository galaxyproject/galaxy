# Contributing

Galaxy welcomes new development!  This document briefly describes how to
contribute to the [core galaxy
project](https://github.com/galaxyproject/galaxy) - also checkout our 2013
Galaxy Community Conference presentation on the topic
([video](https://vimeo.com/channels/581875/73486255),
[presentation](https://depot.galaxyproject.org/hub/attachments/documents/presentations/gcc2013/BakerContribute.pdf)).
For information on contributing more broadly to the Galaxy ecosystem and a
deeper discussion of some of these points - please see the
[Develop](https://galaxyproject.org/develop) section of the [Galaxy Community
Hub](https://galaxyproject.org).

## Before you Begin

If you have an idea for a feature to add or an approach for a bugfix, it is
best to communicate with Galaxy developers early. The primary venue for this is
the [GitHub issue tracker](https://github.com/galaxyproject/galaxy/issues).
Browse through existing GitHub issues and if one seems related, comment on it.
For more direct communication, Galaxy developers are generally available via
[IRC](https://galaxyproject.org/get-involved),
[Gitter](https://gitter.im/galaxyproject/Lobby) and on the [development mailing
list](http://dev.list.galaxyproject.org).

If you're looking to help but aren't sure where to start, we also maintain a
[tag](https://github.com/galaxyproject/galaxy/issues?q=is%3Aissue+is%3Aopen+label%3Afriendliness%2Ffriendly)
on GitHub for smaller issues we believe would make the best entry points for
new developers.

## Reporting a new issue

If no existing Galaxy issue seems appropriate, a new issue can be opened using
[this form](https://github.com/galaxyproject/galaxy/issues/new).

## How to Contribute

* All changes to the [core galaxy
  project](https://github.com/galaxyproject/galaxy) should be made through pull
  requests to this repository (with just two exceptions outlined below).

* If you are new to Git, the [Try Git](http://try.github.com/) tutorial is a
  good places to start.  More learning resources are listed at
  https://help.github.com/articles/good-resources-for-learning-git-and-github/

* Make sure you have a free [GitHub](https://github.com/) account.

* Fork the [galaxy repository](https://github.com/galaxyproject/galaxy) on
  GitHub to make your changes.  To keep your copy up to date with respect to
  the main repository, you need to frequently [sync your
  fork](https://help.github.com/articles/syncing-a-fork/):
  ```
    $ git remote add upstream https://github.com/galaxyproject/galaxy
    $ git fetch upstream
    $ git checkout dev
    $ git merge upstream/dev
  ```

* Choose the correct branch to develop your changes against.

  * Additions of new features to the code base should be pushed to the `dev`
    branch (`git checkout dev`).

  * Most bug fixes to previously release components (things in galaxy-dist)
    should be made against the recent `release_XX.XX` branch (`git checkout
    release_XX.XX`).

  * Serious security problems should not be fixed via pull request - please see
    [the Galaxy security policies](SECURITY_POLICY.md) for information about
    responsibly disclosing security issues.

* If your changes modify code please ensure the resulting files conform to
  Galaxy [style guidelines](https://galaxyproject.org/develop/best-practices).

* If you are working on the Galaxy Client (the user interface -- JavaScript,
  styles, etc.), see more information in the [client readme](client/README.md).

* Galaxy contains hundreds of tests of different types and complexity and
  running each is difficult and probably not reasonable at this time (someday
  we will provide a holistic test procedure to make this possible). For now,
  please just review the [running tests
  documentation](https://galaxyproject.org/admin/running-tests) and run any
  that seem relevant. Developers reviewing your pull request will be happy to
  help guide you to running the most relevant tests as part of the pull request
  review process and may request the output of these tests. You can run the
  continuous integration tests locally using `tox`, example: `tox -e
  py27-lint,py27-unit`.

* Commit and push your changes to your
  [fork](https://help.github.com/articles/pushing-to-a-remote/).

* Open a [pull
  request](https://help.github.com/articles/creating-a-pull-request/) with
  these changes. You pull request message ideally should include:

   * A description of why the changes should be made.

   * A description of the implementation of the changes.

   * A description of how to test the changes.

* The pull request should pass all the continuous integration tests which are
  automatically run by GitHub using e.g. Travis CI.

* Your pull request will be handled according to [some
  rules](doc/source/project/organization.rst#handling-pull-requests).

## A Quick Note about Tools

  For the most part, Galaxy tools should be published to the [Tool
  Shed](https://galaxyproject.org/toolshed) and not in this repository
  directly. If you are looking for migrated core tools that used to exist in
  this repository - please checkout the
  [tools-iuc](https://github.com/galaxyproject/tools-iuc) repository on GitHub.

  More information about tool development can be found [on the comunity
  hub](https://galaxyproject.org/develop).

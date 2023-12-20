# Contributing

Galaxy welcomes new development!  This document briefly describes how to
contribute to the [core galaxy repository](https://github.com/galaxyproject/galaxy).
For general information on the Galaxy ecosystem, please see the
[Galaxy Community Hub](https://galaxyproject.org).
For a description of how the Galaxy code is structured, see the
[Galaxy Code Architecture slides](https://training.galaxyproject.org/training-material/topics/dev/tutorials/architecture/slides.html)
that are part of the [Galaxy Training Materials](https://training.galaxyproject.org/).

## Before you Begin

If you have an idea for a feature to add or an approach for a bugfix, it is
best to communicate with Galaxy developers early. The primary venue for this is
the [GitHub issue tracker](https://github.com/galaxyproject/galaxy/issues).
Browse through existing GitHub issues and if one seems related, comment on it.
For more direct communication, Galaxy developers are generally available on
the [Galaxy Matrix space](https://matrix.to/#/#galaxyproject:matrix.org), in
particular on the [galaxyprojec/dev channel](https://matrix.to/#/#galaxyproject_dev:gitter.im)
and in the various [Working Group](https://galaxyproject.org/community/wg/)
channels.

If you're looking to help but aren't sure where to start, we also maintain a
[tag](https://github.com/galaxyproject/galaxy/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22)
on GitHub for smaller issues we believe would make the best entry points for
new developers.

## Reporting a new issue

If no existing Galaxy issue seems appropriate, a new issue can be opened using
[this form](https://github.com/galaxyproject/galaxy/issues/new).

## How to Contribute

All changes to the [core galaxy
repository](https://github.com/galaxyproject/galaxy) should be made through pull
requests (with just two exceptions outlined below).

If you are new to Git, the Software Carpentry's [Version Control with
Git](https://swcarpentry.github.io/git-novice/) tutorial is a good place to
start.  More learning resources are listed at
https://help.github.com/en/github/getting-started-with-github/git-and-github-learning-resources

1. Make sure you have a free [GitHub](https://github.com/) account. To increase
   the security of your account, we strongly recommend that you configure
   [two-factor authentication](https://docs.github.com/en/github/authenticating-to-github/securing-your-account-with-two-factor-authentication-2fa).
   Additionally, you may want to [sign your commits](https://docs.github.com/en/github/authenticating-to-github/managing-commit-signature-verification).

2. Fork the [galaxy repository](https://github.com/galaxyproject/galaxy) on
   GitHub to make your changes.  To keep your copy up to date with respect to
   the main repository, you need to frequently [sync your
   fork](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/syncing-a-fork):

   ```
   $ git remote add upstream https://github.com/galaxyproject/galaxy
   $ git fetch upstream
   $ git checkout dev
   $ git merge upstream/dev
   ```

3. Choose the correct branch to develop your changes against.

   * The `master` branch is kept in sync with the latest tagged release, but
     should **not** be used as the base (i.e. target) branch of a pull request.

   * Additions of new features to the codebase should be based off the `dev`
     branch (`git checkout -b feature_branch dev`), with few
     [exceptions](doc/source/project/organization.rst#handling-pull-requests).

   * Most bug fixes should target the oldest supported release exhibiting the
     issue (`git checkout -b bugfix_branch release_XX.XX`).

   * Serious security problems should not be fixed via pull request - please see
     [the Galaxy security policies](SECURITY.md) for information about
     responsibly disclosing security issues.

4. If your changes modify code please ensure the resulting files conform to
   the [style guidelines](#style-guidelines) below.

   If you are working on the Galaxy user interface (i.e. JavaScript,
   styles, etc.), see more information in the [client README](client/README.md).

5. Galaxy contains hundreds of tests of different types and complexity and
   running each is difficult and probably not reasonable on your workstation. So
   please review the [running tests documentation](test/TESTING.md) and run any
   that seem relevant.

   If possible, also try to add new tests for the features added or bugs fixed
   by your pull request.

   Developers reviewing your pull request will be happy to help you add or run
   the relevant tests as part of the pull request review process.

6. Write a useful and properly formatted commit message.
   Follow [these guidelines and template](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project#_commit_guidelines),
   in particular start your message with a short imperative sentence on a single
   line, possibly followed by a blank line and a more detailed explanation.

   In the detailed explanation it's good to include relevant references (e.g.
   any GitHub issue being fixed) using full URLs, and errors or tracebacks the
   commit is meant to fix.
   You can use the Markdown syntax for lists and code highlighting, wrapping the
   explanation text at 72 characters when possible.

   Example of a good commit message: https://github.com/galaxyproject/galaxy/commit/0429c4d515536f9cca6b70b2abeb019de807c955

7. Commit and push your changes to your
   [fork](https://help.github.com/en/github/using-git/pushing-commits-to-a-remote-repository).

8. Open a [pull
   request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request)
   with these changes. Your pull request message ideally should include:

   * Why you made the changes (e.g. references to GitHub issues being fixed).

   * A description of the implementation of the changes.

   * How to test the changes, if you haven't included specific tests already.

9. The pull request should pass all the continuous integration tests which are
   automatically started by GitHub.

10. Your pull request will be handled according to [some
    rules](doc/source/project/organization.rst#handling-pull-requests).

11. If, before your pull request is merged, conflicts arise between your branch
    and the target branch (because other commits were pushed to the target
    branch), you need to either:

    1) [rebase your branch](https://git-scm.com/docs/git-rebase) on top of the
       target branch, or
    2) merge the target branch into your branch.

    We recommend the first approach (i.e. rebasing) because it produces cleaner
    git histories, which are easier to bisect. If your branch is called
    `feature_branch` and your target branch is `dev`, you can rebase your branch
    with the following commands:

    ```
    $ git checkout feature_branch
    $ git pull
    $ git fetch upstream
    $ git rebase upstream/dev
    ```

    Once you have resolved the conflicts in all commits of your branch, you can
    force-push the rebased branch to update the pull request:

    ```
    $ git push --force
    ```

## Style guidelines

### Python

- Galaxy follows [PEP-8](https://www.python.org/dev/peps/pep-0008/), with
  particular emphasis on readability being the ultimate goal:
  - 4 spaces (not tabs!) per indentation level
  - divergences from PEP-8 are listed in the `[flake8]` section of the `.flake8`
    file and in the `[tool.ruff]` section of the `pyproject.toml` file.
  - The Python code base is automatically formatted using
    [isort](https://pycqa.github.io/isort/) (for imports) and
    [black](https://black.readthedocs.io). To easily format your Python code
    before submitting your contribution, please either use `make diff-format`
    or run `isort FILE; black FILE` for each FILE you modify.
- Python [docstrings](http://www.python.org/dev/peps/pep-0257/) need to be in
  [reStructured Text (RST)](https://docutils.sourceforge.io/rst.html) format and
  compatible with [Sphinx](https://www.sphinx-doc.org).
- String formatting should normally be done using
  [formatted string literals (f-strings)](https://docs.python.org/3/tutorial/inputoutput.html#formatted-string-literals),
  except:
  - when the format string is kept in a separate variable, in which case the
    [string ``format()`` method](https://docs.python.org/3/tutorial/inputoutput.html#the-string-format-method)
    should be used;
  - when [formatting a log message](https://docs.python.org/3/library/logging.html#logging.Logger.debug),
    in which case it's better to use a
    [`printf`-style](https://docs.python.org/3/library/stdtypes.html#old-string-formatting)
    message format string and pass its arguments to the logging method
    separately. This is a bit more efficient than using f-strings and allows for
    better log aggregation. For more information, see this
    [blog post](https://dev.to/izabelakowal/what-is-the-best-string-formatting-technique-for-logging-in-python-d1d).

## Documentation

General documentation (e.g. admin, development, release notes) is found in the
``doc/source/`` directory.
The documentation source files need to be written in one of these markup
languages:
- [reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html)
  (with Sphinx extensions)
- [Markdown](https://myst-parser.readthedocs.io/en/latest/syntax/typography.html)
  (with MyST-Parser extensions).
These source files are then built into HTML documentation with
[Sphinx](https://www.sphinx-doc.org/) by running ``make docs`` and published on
the [Galaxy Documentation website](https://docs.galaxyproject.org/).

## A Quick Note about Tools

For the most part, Galaxy tools should be published to a [Tool
Shed](https://galaxyproject.org/toolshed) and not in this repository directly.
More information about tool development can be found [on the community
hub](https://galaxyproject.org/develop).

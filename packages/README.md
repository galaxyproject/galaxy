# Package-centric Galaxy

You clone Galaxy as a [Monorepo](https://en.wikipedia.org/wiki/Monorepo) for
its Python backend. This packages directory allows us to distribute smaller
connected repositories out of individual Galaxy components. CI ensures these
repositories have valid dependencies and such defined by running each 
components tests in isolation.

## Development

Typically Galaxy developers develop against the monorepo but there are times
when developing against a small unit of Galaxy might make sense - such as to 
keep an AI (or human cognitive) context as small as possible.

This can be done by treating Galaxy as a
[uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/).
The pyproject.toml file in this directory defines a workspace for Galaxy
and allows development and testing of individual packages with
[uv](https://docs.astral.sh/uv/).

Here is an example workflow that will run tests for a specific package
after setting up a virtual environment for that package.

    $ git clone https://github.com/galaxyproject/galaxy.git
    $ cd galaxy/packages
    $ cd auth
    $ uv sync --all-extras
    $ uv run pytest tests

When switching between projects it is just important to remember
to rerun the sync command for that project.

The package ``Makefile`` has been updated to use ux also, so the above can
be simplified to just:

    $ git clone https://github.com/galaxyproject/galaxy.git
    $ cd galaxy/packages
    $ cd auth
    $ make test

If the environment has already been setup and you wish to just re-run
the tests. The ``make _test`` command be used to just do the testing in
the existing environment without messing with ``sync`` and adjusting
dependencies.

The ``Makefile`` can also be used for typechecking.

    $ git clone https://github.com/galaxyproject/galaxy.git
    $ cd galaxy/packages
    $ cd auth
    $ make mypy
    $ make _mypy  # a shortcut to just run mypy on an existing updated environment

This is equivalent to syncing the uv environment and then adding
Galaxy's type checking dependencies to it.

    $ uv sync --all-extras
    $ uv pip install -r ../../lib/galaxy/dependencies/pinned-typecheck-requirements.txt
    $ uv run mypy .

The ``Makefile`` can also be used for linting.

    $ git clone https://github.com/galaxyproject/galaxy.git
    $ cd galaxy/packages
    $ cd auth
    $ make lint
    $ make _lint  # a shortcut to just run ruff on an existing updated environment

This is equivalent to syncing the uv environment and then adding
Galaxy's linting dependencies to it.

    $ uv sync --all-extras
    $ uv pip install -r ../../lib/galaxy/dependencies/pinned-lint-requirements.txt
    $ uv run ruff check .

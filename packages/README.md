# Package-centric Galaxy

You clone Galaxy as a [Monorepo](https://en.wikipedia.org/wiki/Monorepo) for
its Python backend. This packages directory allows us to distribute smaller
connected repositories out of individual Galaxy components. CI ensures these
repositories have valid dependencies and such defined by running each
components tests in isolation (see `packages/test.sh`, run from the
repository root as `bash packages/test.sh`).

## Development

Typically Galaxy developers develop against the monorepo but there are times
when developing against a small unit of Galaxy might make sense - such as to
keep an AI (or human cognitive) context as small as possible.

Development uses a single
[uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
rooted at the repository root. The root `pyproject.toml`
(`name = "galaxy-workspace"`, `[tool.uv.workspace]` members `packages/*`) is
the workspace manifest. Project commands issued from package directories use
this workspace and its environment. Workspace members use editable installs,
which make their Python packages importable in that environment.

The exact uv version to use is pinned in `.tool-versions` at the repository
root. Both mise and asdf can read this file. Use the pinned version when
syncing or regenerating the lock.

All workspace members share the tracked root `uv.lock`. Resolve manifest
conflicts first, then regenerate the lock from the project manifests with the
pinned uv version. Review dependency changes before committing.

Sources live in `packages/<name>/src` and unit tests in
`packages/<name>/tests`. Keep Python code in its owning distribution; shared
fixtures and frontend assets use symbolic links. Shared pytest and sharding
support lives in `packages/test_driver`; composed application tests and their
fixtures live under `test/`.

Here is an example workflow that syncs the shared development environment
once from the repository root and then runs tests for a specific package:

    $ git clone https://github.com/galaxyproject/galaxy.git
    $ cd galaxy
    $ uv sync --locked --all-packages --all-extras --group dev
    $ uv run --locked --inexact --package galaxy-util --group dev pytest packages/util/tests

See the [development FAQ](../doc/source/dev/faq.rst) for environment setup
commands and dependency maintenance.

The per-package ``Makefile`` (symlinked as e.g. ``packages/auth/Makefile``)
targets the same root workspace, so package commands can also be run from
the package directory:

    $ git clone https://github.com/galaxyproject/galaxy.git
    $ cd galaxy/packages/auth
    $ make test

This syncs the workspace environment scoped to that package
(`uv sync --locked --package ...`) and runs its tests with
`uv run --locked --package ...`.

If the environment has already been setup and you wish to just re-run
the tests. The ``make _test`` command be used to just do the testing in
the existing environment without messing with ``sync`` and adjusting
dependencies.

The ``Makefile`` can also be used for typechecking.

    $ cd galaxy/packages/auth
    $ make mypy

This checks sources from the package's `src` directory, then checks its tests,
using the declared typecheck group and the root `mypy.ini`. Mypy resolves other
workspace packages through their installed editable distributions; no source
search-path list is needed. Run `make mypy` at the repository root to check all
packages and repository-level tests.

The ``Makefile`` can also be used for linting:

    $ make lint

Lint runs in an isolated tool environment, preserving the workspace's
application dependencies:

    $ uvx --with-requirements ../../requirements/pinned-lint-requirements.txt ruff check .

## Isolated package checks

The shared-workspace commands above are convenient for development but prove
nothing about package dependency isolation. The authoritative isolation check
remains `packages/test.sh` (used by the `test_galaxy_packages` tox
environments): it builds a throw-away virtualenv per package in dependency
order, installs that package's own dependencies, and runs its tests, mypy,
wheel build, and twine check there.

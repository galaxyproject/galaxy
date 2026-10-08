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
the only workspace: the former nested `packages/pyproject.toml` workspace
has been removed, so every `uv` command run from a package directory
resolves to the root workspace and its environment.

The exact uv version to use is pinned in `.uv-version` at the repository
root. Use that version when syncing or regenerating the lock.

The root `uv.lock` is the only workspace lockfile. Note that `*.lock` is
currently matched by `.gitignore` (a rule aimed at Galaxy runtime lock
files), so the lockfile lives as a local development artifact: regenerate
it with the pinned uv version rather than hand-editing it, and never run an
unrelated broad upgrade in a source-move change.

Here is an example workflow that syncs the shared development environment
once from the repository root and then runs tests for a specific package:

    $ git clone https://github.com/galaxyproject/galaxy.git
    $ cd galaxy
    $ uv sync --locked --group dev
    $ uv run --locked --package galaxy-util pytest packages/util/tests

`uv lock --check` verifies the lock is up to date without modifying it.

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
    $ make _mypy  # a shortcut to just run mypy on an existing updated environment

This is equivalent to syncing the package environment and then adding
Galaxy's type checking dependencies to it. During the workspace migration
those still live in ``lib/galaxy/dependencies/`` (future home:
a repository-level ``requirements/`` directory):

    $ uv sync --locked --package galaxy-auth --all-extras
    $ uv pip install -r ../../lib/galaxy/dependencies/pinned-typecheck-requirements.txt
    $ uv run --locked --package galaxy-auth mypy .

The ``Makefile`` can also be used for linting.

    $ cd galaxy/packages/auth
    $ make lint
    $ make _lint  # a shortcut to just run ruff on an existing updated environment

This is equivalent to syncing the package environment and then adding
Galaxy's linting dependencies to it.

    $ uv sync --locked --package galaxy-auth --all-extras
    $ uv pip install -r ../../lib/galaxy/dependencies/pinned-lint-requirements.txt
    $ uv run --locked --package galaxy-auth ruff check .

## Isolated package checks

The shared-workspace commands above are convenient for development but prove
nothing about package dependency isolation. The authoritative isolation check
remains `packages/test.sh` (used by the `test_galaxy_packages` tox
environments): it builds a throw-away virtualenv per package in dependency
order, installs that package's own dependencies, and runs its tests, mypy,
wheel build, and twine check there.

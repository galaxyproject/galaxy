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

The exact uv version to use is pinned in `.tool-versions` at the repository
root (`uv 0.12.23`). Both mise and asdf can read this file. Use the pinned
version when syncing or regenerating the lock.

The root `uv.lock` is tracked and is the only workspace lockfile. The
`.gitignore` exception for it keeps Galaxy runtime lock files ignored.
Resolve manifest conflicts first, then regenerate the lock with the pinned uv
version and review the dependency diff. Do not hand-edit the lock or run an
unrelated broad upgrade in a source-move change.

### Development profiles

Every profile resolves from the single root workspace lock. Tooling-only
requirement exports live in the repository-level `requirements/` directory;
the runtime exports (`pinned-requirements.txt`, `conditional-requirements.txt`,
`conditional-constraints.txt`) ship with the `galaxy-app` wheel and stay in
`packages/app/src/galaxy/dependencies/`.

| Profile | Setup | Notes |
| --- | --- | --- |
| App startup | `uv sync --locked --package galaxy-web-apps --all-extras` | Installs the editable server closure; startup uses an inexact sync to preserve additional dependencies. |
| Backend tests | `uv sync --locked --package galaxy-web-apps --all-extras --group dev` | The `dev` group includes the `test` group. |
| Tool Shed | `uv sync --locked --package galaxy-tool-shed --all-extras --group dev` | Installs the Tool Shed server closure; start with `run_tool_shed.sh`. |
| Browser tests | covered by the `test` group | `playwright` + `pytest-playwright`, `selenium` + `axe-selenium-python`. |
| Docs | covered by the `dev` group | Sphinx stack; docs CI installs `sphinxcontrib-simpleversioning` on top. |
| Typecheck | `uv sync --locked --group typecheck` | Or install `requirements/pinned-typecheck-requirements.txt` into an existing environment. |
| Lint | isolated environment, not a group | The pinned flake8/ruff tool set conflicts with the application resolve; build from `requirements/lint-requirements.txt`, frozen as `requirements/pinned-lint-requirements.txt` by `update_lint_requirements.sh`. |

Member extras used by `packages/test.sh` and installable via
`uv sync --locked --package <dist> --all-extras`:

| Package | Extras |
| --- | --- |
| `galaxy-util` | `image-util`, `template`, `jstree`, `config-template` |
| `galaxy-tool-util` | `cwl`, `mulled`, `edam` (plus `extended-assertions`, `test`) |
| `galaxy-objectstore` | `irods`, `azure-blob`, `s3` (plus `all`, `test`) |

Here is an example workflow that syncs the shared development environment
once from the repository root and then runs tests for a specific package:

    $ git clone https://github.com/galaxyproject/galaxy.git
    $ cd galaxy
    $ uv sync --locked --group dev
    $ uv run --locked --package galaxy-util --group dev pytest packages/util/tests

`uv lock --check` verifies the lock is up to date without modifying it.
Runtime exports live under `packages/app/src/galaxy/dependencies/`; tooling
exports live under `requirements/`. Regenerate them from the existing lock without
upgrading dependencies with `sh packages/app/src/galaxy/dependencies/update.sh --export-only`.
Run the same script with `--check` to verify the lock and exports without
changing them. CI runs this check on dependency changes. `make
update-dependencies` deliberately upgrades dependencies and regenerates the
exports; lint and conditional requirements retain their separate inputs.


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
Galaxy's type checking dependencies to it, which live in the
repository-level ``requirements/`` directory:

    $ uv sync --locked --package galaxy-auth --all-extras
    $ uv pip install -r ../../requirements/pinned-typecheck-requirements.txt
    $ uv run --locked --package galaxy-auth mypy .

The ``Makefile`` can also be used for linting.

    $ cd galaxy/packages/auth
    $ make lint
    $ make _lint  # a shortcut to just run ruff on an existing updated environment

This is equivalent to syncing the package environment and then adding
Galaxy's linting dependencies to it.

    $ uv sync --locked --package galaxy-auth --all-extras
    $ uv pip install -r ../../requirements/pinned-lint-requirements.txt
    $ uv run --locked --package galaxy-auth ruff check .

## Isolated package checks

The shared-workspace commands above are convenient for development but prove
nothing about package dependency isolation. The authoritative isolation check
remains `packages/test.sh` (used by the `test_galaxy_packages` tox
environments): it builds a throw-away virtualenv per package in dependency
order, installs that package's own dependencies, and runs its tests, mypy,
wheel build, and twine check there.

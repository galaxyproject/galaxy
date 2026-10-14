Galaxy Testing
==============

The Galaxy codebase is large and contains many kinds of tests. The simpler
tests can be run via `tox`, while the others via `./run_tests.sh` .

## Setup and direct pytest

Install the uv version pinned in `.tool-versions`, then from the repository root:

```sh
uv sync --locked --all-packages --all-extras --no-default-groups --group test
uv run --no-sync python -m pytest packages/util/tests
```

## tox

Install with `uv tool install tox --with tox-uv`. Use `tox -l` to list
available environments and, for example, `tox -e mulled` to run the external
dependency tests.

## ./run_tests.sh

The runner provides suite selection, application configuration, fixture/client
preparation, and reports. It syncs the locked test workspace once; it does not
run server bootstrap or install requirements exports. Run `./run_tests.sh --help`
for suite selectors. Use `--no-sync` to reuse a prepared environment.
`UV_PROJECT_ENVIRONMENT` selects the environment; otherwise the runner uses
`GALAXY_VIRTUAL_ENV`, the active virtualenv, or `.venv`, in that order.
`GALAXY_PYTHON` (or `TEST_PYTHON`) can select Python when syncing.

The old `--skip-venv`, `--no-create-venv`, `--skip-common-startup`, and pip
replacement flags have been removed. Use `--no-sync` with an existing uv
workspace environment instead. Client builds use `make client-production-maps`
when requested by the suite or `GALAXY_SKIP_CLIENT_BUILD=0`.

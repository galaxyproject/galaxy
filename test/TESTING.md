Galaxy Testing
==============

The Galaxy codebase is large and contains many kinds of tests. The simpler
tests can be run via `tox`, while the others via `./run_tests.sh` .

## tox

tox does not need to be installed in your virtualenv. Run it with `uvx`, and
include the `tox-uv` plugin so environments are built with `uv` rather than
`virtualenv` + `pip` (this is what CI uses, see `.github/workflows/`):

```bash
uvx --with tox-uv tox -l                    # list "test environments"
uvx --with tox-uv tox -e lint               # run the lint environment
```

For a persistent binary you can instead run `uv tool install tox --with tox-uv`
once and then invoke `tox` directly.

## ./run_tests.sh

To view the list of available tests and how to run them:
`./run_tests.sh --help` from Galaxy root directory

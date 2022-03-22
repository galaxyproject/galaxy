Galaxy Testing
==============

The Galaxy codebase is large and contains many kinds of tests. The simpler
tests can be run via `tox`, while the others via `./run_tests.sh` .

## tox

tox needs to be installed in your Python virtualenv with `pip install tox` .

To view the list of available "test environments" for tox: `tox -l`

To run the test for e.g. the `py36-lint` test environment: `tox -e py36-lint`

## ./run_tests.sh

To view the list of available tests and how to run them:
`./run_tests.sh --help` from Galaxy root directory

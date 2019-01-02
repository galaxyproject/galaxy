# Default tests run with make test and make quick-tests
NOSE_TESTS?=--exclude galaxy/util/dictobj.py,galaxy/util/jstree.py tests galaxy
# Default environment for make tox
ENV?=py27
# Extra arguments supplied to tox command
ARGS?=
# Location of virtualenv used for development.
VENV?=.venv
# Source virtualenv to execute command (flake8, sphinx, twine, etc...)
IN_VENV=if [ -f $(VENV)/bin/activate ]; then . $(VENV)/bin/activate; fi;
# TODO: add this upstream as a remote if it doesn't already exist.
UPSTREAM?=galaxyproject
SOURCE_DIR?=galaxy
BUILD_SCRIPTS_DIR=scripts
VERSION?=$(shell python $(BUILD_SCRIPTS_DIR)/print_version_for_release.py $(SOURCE_DIR))
DOC_URL?=https://galaxy-lib.readthedocs.org
PROJECT_URL?=https://github.com/galaxyproject/galaxy-lib
PROJECT_NAME?=galaxy-lib
TEST_DIR?=tests



.PHONY: clean-pyc clean-build docs clean

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "setup-venv - setup a development virutalenv in current directory."
	@echo "lint - check style using tox and flake8 for Python 2 and Python 3"
	@echo "lint-readme - check README formatting for PyPI"
	@echo "flake8 - check style using flake8 for current Python (faster than lint)"
	@echo "test - run tests with the default Python (faster than tox)"
	@echo "quick-test - run quickest tests with the default Python"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "open-docs - generate Sphinx HTML documentation and open in browser"
	@echo "open-rtd - open docs on readthedocs.org"
	@echo "open-project - open project on github"
	@echo "release - package, review, and upload a release"
	@echo "dist - package"
	@echo "setup-git-hook-lint - setup precommit hook for linting project"
	@echo "setup-git-hook-lint-and-test - setup precommit hook for linting and testing project"
	@echo "update-extern - update external artifacts copied locally"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

setup-venv:
	if [ ! -d $(VENV) ]; then virtualenv $(VENV); exit; fi;
	$(IN_VENV) pip install -r requirements.txt && pip install -r dev-requirements.txt

setup-git-hook-lint:
	cp $(BUILD_SCRIPTS_DIR)/pre-commit-lint .git/hooks/pre-commit

setup-git-hook-lint-and-test:
	cp $(BUILD_SCRIPTS_DIR)/pre-commit-lint-and-test .git/hooks/pre-commit

flake8:
	$(IN_VENV) flake8 --max-complexity 15 $(SOURCE_DIR)  $(TEST_DIR)

lint:
	$(IN_VENV) tox -e py27-lint && tox -e py34-lint

lint-readme:
	$(IN_VENV) python setup.py check -r -s

test:
	$(IN_VENV) nosetests $(NOSE_TESTS)

tox:
	$(IN_VENV) tox -e $(ENV) -- $(ARGS)

coverage:
	coverage run --source $(SOURCE_DIR) setup.py $(TEST_DIR)
	coverage report -m
	coverage html
	open htmlcov/index.html || xdg-open htmlcov/index.html

docs:
	$(IN_VENV) sphinx-apidoc -f -o docs/ galaxy
	$(IN_VENV) $(MAKE) -C docs clean
	$(IN_VENV) $(MAKE) -C docs html

_open-docs:
	open docs/_build/html/index.html || xdg-open docs/_build/html/index.html

open-docs: docs _open-docs

open-rtd: docs
	open $(DOC_URL) || xdg-open $(PROJECT_URL)

open-project:
	open $(PROJECT_URL) || xdg-open $(PROJECT_URL)

dist: clean
	$(IN_VENV) python setup.py sdist bdist_egg bdist_wheel
	ls -l dist

release-test-artifacts: dist
	$(IN_VENV) twine upload -r test dist/*
	open https://testpypi.python.org/pypi/$(PROJECT_NAME) || xdg-open https://testpypi.python.org/pypi/$(PROJECT_NAME)

release-artifacts: release-test-artifacts
	@while [ -z "$$CONTINUE" ]; do \
		read -r -p "Have you executed release-test and reviewed results? [y/N]: " CONTINUE; \
	done ; \
	[ $$CONTINUE = "y" ] || [ $$CONTINUE = "Y" ] || (echo "Exiting."; exit 1;)
	@echo "Releasing"
	$(IN_VENV) twine upload dist/*

commit-version:
	$(IN_VENV) python $(BUILD_SCRIPTS_DIR)/commit_version.py $(SOURCE_DIR) $(VERSION)

new-version:
	$(IN_VENV) python $(BUILD_SCRIPTS_DIR)/new_version.py $(SOURCE_DIR) $(VERSION) 2

release-local: commit-version release-artifacts new-version

push-release:
	git push $(UPSTREAM) master
	git push --tags $(UPSTREAM)

release: release-local push-release

add-history:
	$(IN_VENV) python scripts/bootstrap_history.py $(ITEM)

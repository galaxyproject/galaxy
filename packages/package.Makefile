# Location of virtualenv used for development.
VENV?=.venv
# Open resource on Mac OS X or Linux
OPEN_RESOURCE=bash -c 'open $$0 || xdg-open $$0'
# Source virtualenv to execute command (flake8, sphinx, twine, etc...)
IN_VENV=if [ -f $(VENV)/bin/activate ]; then . $(VENV)/bin/activate; fi;
UPSTREAM?=galaxyproject
SOURCE_DIR?=galaxy
BUILD_SCRIPTS_DIR=scripts
DEV_RELEASE?=0
VERSION?=$(shell DEV_RELEASE=$(DEV_RELEASE) python $(BUILD_SCRIPTS_DIR)/print_version_for_release.py)
PROJECT_NAME?=galaxy-$(shell basename $(CURDIR))
PROJECT_NAME:=$(subst _,-,$(PROJECT_NAME))
BRANCH?=$(shell git rev-parse --abbrev-ref HEAD)
TEST_DIR?=tests
TESTS?=$(SOURCE_DIR) $(TEST_DIR)

.PHONY: clean-pyc clean-build docs clean

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "setup-venv - setup a development virtualenv in current directory."
	@echo "lint-dist - twine check dist results, including validating README content"
	@echo "dist - package project for PyPI distribution"

clean: clean-build clean-pyc clean-tests

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr galaxy_*.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-tests:
	rm -fr .tox/

setup-venv:
	if [ ! -d $(VENV) ]; then virtualenv $(VENV); exit; fi;
	$(IN_VENV) pip install -r requirements.txt && pip install -r dev-requirements.txt

test:
	$(IN_VENV) pytest $(TESTS)

develop:
	python setup.py develop

dist: clean
	$(IN_VENV) python -m build
	ls -l dist

_twine-exists: ; @which twine > /dev/null

lint-dist: _twine-exists dist
	$(IN_VENV) twine check dist/*

_release-test-artifacts:
	$(IN_VENV) twine upload -r test dist/*
	$(OPEN_RESOURCE) https://testpypi.python.org/pypi/$(PROJECT_NAME)

release-test-artifacts: lint-dist _release-test-artifacts

_release-artifacts:
	@while [ -z "$$CONTINUE" ]; do \
	  read -r -p "Have you executed release-test and reviewed results? [y/N]: " CONTINUE; \
	done ; \
	[ $$CONTINUE = "y" ] || [ $$CONTINUE = "Y" ] || (echo "Exiting."; exit 1;)
	@echo "Releasing"
	$(IN_VENV) twine upload dist/*

release-artifacts: release-test-artifacts _release-artifacts

commit-version:
	$(IN_VENV) DEV_RELEASE=$(DEV_RELEASE) python $(BUILD_SCRIPTS_DIR)/commit_version.py $(VERSION)

new-version:
	$(IN_VENV) DEV_RELEASE=$(DEV_RELEASE) python $(BUILD_SCRIPTS_DIR)/new_version.py $(VERSION)

release-local: commit-version release-artifacts new-version

push-release:
	# git push $(UPSTREAM) $(BRANCH)
	# git push upstream $(PROJECT_NAME)-$(VERSION)
	echo "Makefile doesn't manually push release."

release: release-local push-release

mypy:
	mypy .

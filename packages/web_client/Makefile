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
DIST=dist
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

clean: clean-build clean-pyc clean-tests clean-web-client

clean-build:
	rm -fr build/
	rm -fr $(DIST)/
	rm -fr galaxy_*.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-tests:
	rm -fr .tox/

# Removing .venv instead of $(VENV) is intentional, because we can't guarantee we created $(VENV)
clean-web-client:
	rm -rf .venv
	rm -rf src/galaxy/web_client/dist src/galaxy/web_client/client_build_hash.txt

setup-venv:
	uv sync --inexact --all-extras

_test:
	uv run pytest $(TESTS)

test: setup-venv _test

_dist: src/galaxy/web_client/client_build_hash.txt
	uv build -o $(DIST)
	ls -l $(DIST)

dist: clean _dist

src/galaxy/web_client/client_build_hash.txt:
	# Use the main Galaxy virtualenv, since that's what `make client-production` uses
	cd ../..; \
		uv venv --allow-existing $(VENV); \
		$(IN_VENV) \
		uv pip install "nodejs-wheel==$$(cat client/.node_version)"; \
		make client-production
	mv ../../client/dist src/galaxy/web_client/
	git rev-parse HEAD > src/galaxy/web_client/client_build_hash.txt

_setup-mypy-venv: setup-venv
	uv pip install -r ../../lib/galaxy/dependencies/pinned-typecheck-requirements.txt

_mypy:
	uv run mypy .

mypy: _setup-mypy-venv _mypy

_setup-dev-venv:
	uv pip install -r dev-requirements.txt

lint-dist: _setup-dev-venv
	uv run twine check $(DIST)/*

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

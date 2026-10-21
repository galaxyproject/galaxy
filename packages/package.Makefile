# Location of virtualenv used for development.
VENV?=.venv
# Source virtualenv to execute commands that need the root environment.
IN_VENV=if [ -f $(VENV)/bin/activate ]; then . $(VENV)/bin/activate; fi;
SOURCE_DIR?=src/galaxy
PROJECT_NAME?=galaxy-$(shell basename $(CURDIR))
PROJECT_NAME:=$(subst _,-,$(PROJECT_NAME))
# Distribution name used to scope uv to this package in the single root
# workspace. packages/meta builds the published `galaxy` distribution,
# not `galaxy-meta`, hence the special case.
ifeq ($(shell basename $(CURDIR)),meta)
UV_PACKAGE?=galaxy
else
UV_PACKAGE?=$(PROJECT_NAME)
endif
BRANCH?=$(shell git rev-parse --abbrev-ref HEAD)
TEST_DIR?=tests
DIST=dist
TESTS?=$(SOURCE_DIR) $(TEST_DIR)
# Hooks for members that must generate bundled assets before packaging
# (packages/web_client builds the client and checks its artifacts).
DIST_PREREQS?=
DIST_CHECK_EXTRA?=

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
	rm -fr $(DIST)/
	find . -name "*.egg-info" -type d -exec rm -rf {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-tests:
	rm -fr .tox/

setup-venv:
	# Resolves the single root workspace (the nested packages/pyproject.toml
	# workspace was removed), scoped to this package. --inexact preserves the
	# mypy/lint tool installs below across re-syncs.
	uv sync --locked --inexact --package $(UV_PACKAGE) --all-extras

_test:
	uv run --locked --inexact --package $(UV_PACKAGE) --all-extras --group test pytest $(TESTS)

test: setup-venv _test

_dist: $(DIST_PREREQS)
	uv build -o $(DIST)
	ls -l $(DIST)

dist: clean _dist

_mypy:
	@if [ -n "$(wildcard src tests)" ]; then \
	    uv run --locked --inexact --package $(UV_PACKAGE) --all-extras --group typecheck bash -ec '\
	        if [ -d src ]; then (cd src && mypy .); fi; \
	        if [ -d tests ]; then (cd ../.. && mypy packages/$(notdir $(CURDIR))/tests); fi'; \
	fi

mypy: _mypy

_lint:
	uvx --with-requirements ../../requirements/pinned-lint-requirements.txt ruff check .

lint: _lint

lint-dist:
	uvx --from twine==6.2.0 twine check $(DIST)/*
	$(DIST_CHECK_EXTRA)

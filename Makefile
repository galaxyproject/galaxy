# Location of virtualenv used for development.
VENV?=.venv
# Source virtualenv to execute command (flake8, sphinx, twine, etc...)
IN_VENV=if [ -f "$(VENV)/bin/activate" ]; then . "$(VENV)/bin/activate"; fi;
RELEASE_CURR:=22.05
RELEASE_UPSTREAM:=upstream
TARGET_BRANCH=$(RELEASE_UPSTREAM)/dev
CONFIG_MANAGE=$(IN_VENV) python lib/galaxy/config/config_manage.py
PROJECT_URL?=https://github.com/galaxyproject/galaxy
DOCS_DIR=doc
DOC_SOURCE_DIR=$(DOCS_DIR)/source
SLIDESHOW_DIR=$(DOC_SOURCE_DIR)/slideshow
OPEN_RESOURCE=bash -c 'open $$0 || xdg-open $$0'
SLIDESHOW_TO_PDF?=bash -c 'docker run --rm -v `pwd`:/cwd astefanutti/decktape /cwd/$$0 /cwd/`dirname $$0`/`basename -s .html $$0`.pdf'
YARN := $(shell command -v yarn 2> /dev/null)
YARN_INSTALL_OPTS=--network-timeout 300000 --check-files
CWL_TARGETS := test/functional/tools/cwl_tools/v1.0/conformance_tests.yaml \
	test/functional/tools/cwl_tools/v1.1/conformance_tests.yaml \
	test/functional/tools/cwl_tools/v1.2/conformance_tests.yaml \
	lib/galaxy_test/api/cwl/test_cwl_conformance_v1_0.py \
	lib/galaxy_test/api/cwl/test_cwl_conformance_v1_1.py \
	lib/galaxy_test/api/cwl/test_cwl_conformance_v1_2.py

all: help
	@echo "This makefile is used for building Galaxy's JS client, documentation, and drive the release process. A sensible all target is not implemented."

docs: ## Generate HTML documentation.
# Run following commands to setup the Python portion of the requirements:
#   $ ./scripts/common_startup.sh
#   $ . .venv/bin/activate
#   $ pip install -r lib/galaxy/dependencies/dev-requirements.txt
	$(IN_VENV) $(MAKE) -C doc clean
	$(IN_VENV) $(MAKE) -C doc html

docs-develop: ## Fast doc generation and more warnings (for development)
	$(IN_VENV) GALAXY_DOCS_SKIP_VIEW_CODE=1 SPHINXOPTS='-j 4' $(MAKE) -C doc html

setup-venv:
	if [ ! -f $(VENV)/bin/activate ]; then bash scripts/common_startup.sh --dev-wheels; fi

diff-format:  ## Format Python code changes since last commit
	$(IN_VENV) darker .

format:  ## Format Python code base
	$(IN_VENV) isort .
	$(IN_VENV) black .

list-dependency-updates: setup-venv
	$(IN_VENV) pip list --outdated --format=columns

docs-slides-ready:
	test -f plantuml.jar ||  wget http://jaist.dl.sourceforge.net/project/plantuml/plantuml.jar
	java -jar plantuml.jar -c $(DOC_SOURCE_DIR)/slideshow/architecture/images/plantuml_options.txt -tsvg $(SLIDESHOW_DIR)/architecture/images/ *.plantuml.txt
	$(IN_VENV) python scripts/slideshow/build_slideshow.py 'Galaxy Architecture' $(SLIDESHOW_DIR)/architecture/galaxy_architecture.md

docs-slides-export: docs-slides-ready
	$(SLIDESHOW_TO_PDF) $(SLIDESHOW_DIR)/galaxy_architecture/galaxy_architecture.html

_open-docs:
	$(OPEN_RESOURCE) $(DOCS_DIR)/_build/html/index.html

open-docs: docs _open-docs ## generate Sphinx HTML documentation and open in browser

open-project: ## open project on github
	$(OPEN_RESOURCE) $(PROJECT_URL)

tool-shed-config-validate: ## validate tool shed YAML configuration file
	$(CONFIG_MANAGE) validate tool_shed

tool-shed-config-lint: ## lint tool shed YAML configuration file
	$(CONFIG_MANAGE) lint tool_shed

tool-shed-config-convert-dry-run: ## convert old style tool shed ini to yaml (dry run)
	$(CONFIG_MANAGE) convert tool_shed --dry-run

tool-shed-config-convert: ## convert old style tool shed ini to yaml
	$(CONFIG_MANAGE) convert tool_shed

reports-config-validate: ## validate reports YAML configuration file
	$(CONFIG_MANAGE) validate reports

reports-config-convert-dry-run: ## convert old style reports ini to yaml (dry run)
	$(CONFIG_MANAGE) convert reports --dry-run

reports-config-convert: ## convert old style reports ini to yaml
	$(CONFIG_MANAGE) convert reports

reports-config-lint: ## lint reports YAML configuration file
	$(CONFIG_MANAGE) lint reports

config-validate: ## validate galaxy YAML configuration file
	$(CONFIG_MANAGE) validate galaxy

config-convert-dry-run: ## convert old style galaxy ini to yaml (dry run)
	$(CONFIG_MANAGE) convert galaxy --dry-run

config-convert: ## convert old style galaxy ini to yaml
	$(CONFIG_MANAGE) convert galaxy

config-rebuild: ## Rebuild all sample YAML and RST files from config schema
	$(CONFIG_MANAGE) build_sample_yaml galaxy --add-comments
	$(CONFIG_MANAGE) build_rst galaxy > doc/source/admin/galaxy_options.rst
	$(CONFIG_MANAGE) build_sample_yaml reports --add-comments
	$(CONFIG_MANAGE) build_rst reports > doc/source/admin/reports_options.rst
	$(CONFIG_MANAGE) build_sample_yaml tool_shed --add-comments

config-lint: ## lint galaxy YAML configuration file
	$(CONFIG_MANAGE) lint galaxy

release-ensure-upstream: ## Ensure upstream branch for release commands setup
ifeq (shell git remote -v | grep $(RELEASE_UPSTREAM), )
	git remote add $(RELEASE_UPSTREAM) git@github.com:galaxyproject/galaxy.git
else
	@echo "Remote $(RELEASE_UPSTREAM) already exists."
endif

release-merge-stable-to-next: release-ensure-upstream ## Merge last release into dev
	git fetch $(RELEASE_UPSTREAM) && git checkout dev && git merge --ff-only $(RELEASE_UPSTREAM)/dev && git merge $(RELEASE_UPSTREAM)/$(RELEASE_PREVIOUS)

release-push-dev: release-ensure-upstream # Push local dev branch upstream
	git push $(RELEASE_UPSTREAM) dev

release-issue: ## Create release issue on github
	$(IN_VENV) python scripts/bootstrap_history.py --create-release-issue $(RELEASE_CURR)

release-check-metadata: ## check github PR metadata for target release
	$(IN_VENV) python scripts/bootstrap_history.py --check-release $(RELEASE_CURR)

release-check-blocking-issues: ## Check github for release blocking issues
	$(IN_VENV) python scripts/bootstrap_history.py --check-blocking-issues $(RELEASE_CURR)

release-check-blocking-prs: ## Check github for release blocking PRs
	$(IN_VENV) python scripts/bootstrap_history.py --check-blocking-prs $(RELEASE_CURR)

release-bootstrap-history: ## bootstrap history for a new release
	$(IN_VENV) python scripts/bootstrap_history.py --release $(RELEASE_CURR)

update-lint-requirements:
	./lib/galaxy/dependencies/update_lint_requirements.sh

update-dependencies: update-lint-requirements ## update pinned and dev dependencies
	$(IN_VENV) ./lib/galaxy/dependencies/update.sh

$(CWL_TARGETS):
	./scripts/update_cwl_conformance_tests.sh

generate-cwl-conformance-tests: $(CWL_TARGETS)  ## Initialise CWL conformance tests

clean-cwl-conformance-tests:  ## Clean CWL conformance tests
	for f in $(CWL_TARGETS); do \
		if [ $$(basename "$$f") = conformance_tests.yaml ]; then \
			rm -rf $$(dirname "$$f"); \
		else \
			rm -f "$$f"; \
		fi \
	done

update-cwl-conformance-tests: ## update CWL conformance tests
	$(MAKE) clean-cwl-conformance-tests
	$(MAKE) generate-cwl-conformance-tests

node-deps: ## Install NodeJS dependencies.
ifndef YARN
	@echo "Could not find yarn, which is required to build the Galaxy client.\nTo install yarn, please visit \033[0;34mhttps://yarnpkg.com/en/docs/install\033[0m for instructions, and package information for all platforms.\n"
	false;
else
	cd client && yarn install $(YARN_INSTALL_OPTS)
endif
	

client: node-deps ## Rebuild client-side artifacts for local development.
	cd client && yarn run build

client-production: node-deps ## Rebuild client-side artifacts for a production deployment without sourcemaps.
	cd client && yarn run build-production

client-production-maps: node-deps ## Rebuild client-side artifacts for a production deployment with sourcemaps.
	cd client && yarn run build-production-maps

client-format: node-deps ## Reformat client code
	cd client && yarn run format

client-watch: node-deps ## A useful target for parallel development building.  See also client-dev-server.
	cd client && yarn run watch

client-dev-server: node-deps ## Starts a webpack dev server for client development (HMR enabled)
	cd client && yarn run serve

client-test: node-deps  ## Run JS unit tests
	cd client && yarn run test

client-eslint-precommit: node-deps # Client linting for pre-commit hook; skips glob input and takes specific paths
	cd client && yarn run eslint-precommit

client-eslint: node-deps # Run client linting
	cd client && yarn run eslint

client-format-check: node-deps # Run client formatting check
	cd client && yarn run format-check

client-lint: client-eslint client-format-check ## ES lint and check format of client

client-test-watch: client ## Watch and run all client unit tests on changes
	cd client && yarn run jest-watch

serve-selenium-notebooks: ## Serve testing notebooks for Jupyter
	cd lib && export PYTHONPATH=`pwd`; jupyter notebook --notebook-dir=galaxy_test/selenium/jupyter

# Release Targets
release-create-rc: ## Create a release-candidate branch or new release-candidate version
	$(IN_VENV) ./scripts/release.sh -c

release-create: ## Create a release branch
	$(IN_VENV) ./scripts/release.sh

release-create-point: release-create ## Create a point release

.PHONY: help

help:
	@egrep '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

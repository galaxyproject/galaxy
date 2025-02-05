# Location of virtualenv used for development.
VENV?=.venv
# Source virtualenv to execute command (darker, sphinx, twine, etc...)
IN_VENV=if [ -f "$(VENV)/bin/activate" ]; then . "$(VENV)/bin/activate"; fi;
RELEASE_CURR:=25.0
RELEASE_UPSTREAM:=upstream
CONFIG_MANAGE=$(IN_VENV) python lib/galaxy/config/config_manage.py
PROJECT_URL?=https://github.com/galaxyproject/galaxy
DOCS_DIR=doc
DOC_SOURCE_DIR=$(DOCS_DIR)/source
SLIDESHOW_DIR=$(DOC_SOURCE_DIR)/slideshow
OPEN_RESOURCE=bash -c 'open $$0 || xdg-open $$0'
SLIDESHOW_TO_PDF?=bash -c 'docker run --rm -v `pwd`:/cwd astefanutti/decktape /cwd/$$0 /cwd/`dirname $$0`/`basename -s .html $$0`.pdf'
YARN := $(shell $(IN_VENV) command -v yarn 2> /dev/null)
YARN_INSTALL_OPTS=--network-timeout 300000 --check-files
# Default to not fail on error, set to 1 to fail client builds on a plugin error.
GALAXY_PLUGIN_BUILD_FAIL_ON_ERROR?=0
# Respect predefined NODE_OPTIONS, otherwise set maximum heap size low for
# compatibility with smaller machines.
NODE_OPTIONS ?= --max-old-space-size=3072
NODE_ENV = env NODE_OPTIONS=$(NODE_OPTIONS) GALAXY_PLUGIN_BUILD_FAIL_ON_ERROR=$(GALAXY_PLUGIN_BUILD_FAIL_ON_ERROR)	
CWL_TARGETS := test/functional/tools/cwl_tools/v1.0/conformance_tests.yaml \
	test/functional/tools/cwl_tools/v1.1/conformance_tests.yaml \
	test/functional/tools/cwl_tools/v1.2/conformance_tests.yaml \
	lib/galaxy_test/api/cwl/test_cwl_conformance_v1_0.py \
	lib/galaxy_test/api/cwl/test_cwl_conformance_v1_1.py \
	lib/galaxy_test/api/cwl/test_cwl_conformance_v1_2.py
NO_YARN_MSG="Could not find yarn, which is required to build the Galaxy client.\nIt should be shipped with Galaxy's virtualenv, but to install yarn manually please visit \033[0;34mhttps://yarnpkg.com/en/docs/install\033[0m for instructions, and package information for all platforms.\n"
SPACE := $() $()
NEVER_PYUPGRADE_PATHS := .venv/ .tox/ lib/galaxy/schema/bco/ \
	lib/galaxy/schema/drs/ lib/tool_shed_client/schema/trs \
	scripts/check_python.py tools/ test/functional/tools/cwl_tools/
PY37_PYUPGRADE_PATHS := lib/galaxy/exceptions/ lib/galaxy/job_metrics/ \
	lib/galaxy/objectstore/ lib/galaxy/tool_util/ lib/galaxy/util/ \
	test/unit/job_metrics/ test/unit/objectstore/ test/unit/tool_util/ \
	test/unit/util/

all: help
	@echo "This makefile is used for building Galaxy's JS client, documentation, and drive the release process. A sensible all target is not implemented."

docs: ## Generate HTML documentation.
# Run following commands to setup the Python portion of the requirements:
#   $ ./scripts/common_startup.sh
#   $ . .venv/bin/activate
#   $ pip install -r requirements.txt -r lib/galaxy/dependencies/dev-requirements.txt
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

remove-unused-imports:  ## Remove unused imports in Python code base
	$(IN_VENV) autoflake --in-place --remove-all-unused-imports --recursive --verbose lib/ test/

pyupgrade:  ## Convert older code patterns to Python 3.7/3.9 idiomatic ones
	ack --type=python -f | grep -v '^$(subst $(SPACE),\|^,$(NEVER_PYUPGRADE_PATHS) $(PY37_PYUPGRADE_PATHS))' | xargs pyupgrade --py39-plus
	ack --type=python -f | grep -v '^$(subst $(SPACE),\|^,$(NEVER_PYUPGRADE_PATHS) $(PY37_PYUPGRADE_PATHS))' | xargs auto-walrus
	ack --type=python -f $(PY37_PYUPGRADE_PATHS) | xargs pyupgrade --py37-plus

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
	$(IN_VENV) galaxy-release-util create-release-issue $(RELEASE_CURR)

release-check-blocking-issues: ## Check github for release blocking issues
	$(IN_VENV) galaxy-release-util check-blocking-issues $(RELEASE_CURR)

release-check-blocking-prs: ## Check github for release blocking PRs
	$(IN_VENV) galaxy-release-util check-blocking-prs $(RELEASE_CURR)

release-bootstrap-history: ## bootstrap history for a new release
	$(IN_VENV) galaxy-release-util create-changelog $(RELEASE_CURR)

update-lint-requirements:
	./lib/galaxy/dependencies/update_lint_requirements.sh

update-dependencies: update-lint-requirements ## update pinned, dev and typecheck dependencies
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

skip-client: ## Run only the server, skipping the client build.
	GALAXY_SKIP_CLIENT_BUILD=1 sh run.sh

node-deps: ## Install NodeJS dependencies.
ifndef YARN
	@echo $(NO_YARN_MSG)
	false;
else
	$(IN_VENV) yarn install $(YARN_INSTALL_OPTS)
endif

client-node-deps: ## Install NodeJS dependencies for the client.
ifndef YARN
	@echo $(NO_YARN_MSG)
	false;
else
	$(IN_VENV) cd client && yarn install $(YARN_INSTALL_OPTS)
endif

format-xsd:
	xmllint --format --output galaxy-tmp.xsd lib/galaxy/tool_util/xsd/galaxy.xsd
	mv galaxy-tmp.xsd lib/galaxy/tool_util/xsd/galaxy.xsd

build-api-schema:
	$(IN_VENV) python scripts/dump_openapi_schema.py _schema.yaml
	$(IN_VENV) python scripts/dump_openapi_schema.py --app shed _shed_schema.yaml

remove-api-schema:
	rm _schema.yaml
	rm _shed_schema.yaml

update-client-api-schema: client-node-deps build-api-schema
	$(IN_VENV) cd client && npx openapi-typescript ../_schema.yaml > src/api/schema/schema.ts && npx prettier --write src/api/schema/schema.ts
	$(IN_VENV) cd client && npx openapi-typescript ../_shed_schema.yaml > ../lib/tool_shed/webapp/frontend/src/schema/schema.ts && npx prettier --write ../lib/tool_shed/webapp/frontend/src/schema/schema.ts
	$(MAKE) remove-api-schema

lint-api-schema: build-api-schema
	$(IN_VENV) npx --yes @redocly/cli lint _schema.yaml
	$(IN_VENV) npx --yes @redocly/cli lint _shed_schema.yaml
	$(IN_VENV) codespell -I .ci/ignore-spelling.txt _schema.yaml
	$(IN_VENV) codespell -I .ci/ignore-spelling.txt _shed_schema.yaml
	$(MAKE) remove-api-schema

update-navigation-schema: client-node-deps
	$(IN_VENV) cd client && node navigation_to_schema.mjs

install-client: node-deps ## Install prebuilt client as defined in root package.json
	$(IN_VENV) yarn install && yarn run stage

client: client-node-deps ## Rebuild client-side artifacts for local development.
	$(IN_VENV) cd client && $(NODE_ENV) yarn run build

client-production: client-node-deps ## Rebuild client-side artifacts for a production deployment without sourcemaps.
	$(IN_VENV) cd client && $(NODE_ENV) yarn run build-production

client-production-maps: client-node-deps ## Rebuild client-side artifacts for a production deployment with sourcemaps.
	$(IN_VENV) cd client && $(NODE_ENV) yarn run build-production-maps

client-lint-autofix: client-node-deps ## Automatically fix linting errors in client code
	$(IN_VENV) cd client && yarn run eslint --quiet --fix

client-format: client-node-deps client-lint-autofix ## Reformat client code, ensures autofixes are applied first
	$(IN_VENV) cd client && yarn run format

client-dev-server: client-node-deps ## Starts a webpack dev server for client development (HMR enabled)
	$(IN_VENV) cd client && $(NODE_ENV) yarn run develop

client-test: client-node-deps  ## Run JS unit tests
	$(IN_VENV) cd client && yarn run test

client-eslint-precommit: client-node-deps # Client linting for pre-commit hook; skips glob input and takes specific paths
	$(IN_VENV) cd client && yarn run eslint-precommit

client-eslint: client-node-deps # Run client linting
	$(IN_VENV) cd client && yarn run eslint

client-format-check: client-node-deps # Run client formatting check
	$(IN_VENV) cd client && yarn run format-check

client-lint: client-eslint client-format-check ## ES lint and check format of client

client-test-watch: client ## Watch and run all client unit tests on changes
	$(IN_VENV) cd client && yarn run jest-watch

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

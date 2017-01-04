RELEASE_CURR:=16.01
RELEASE_CURR_MINOR_NEXT:=$(shell expr `awk '$$1 == "VERSION_MINOR" {print $$NF}' lib/galaxy/version.py | tr -d \" | sed 's/None/0/;s/dev/0/;' ` + 1)
RELEASE_NEXT:=16.04
# TODO: This needs to be updated with create_release_rc
#RELEASE_NEXT_BRANCH:=release_$(RELEASE_NEXT)
RELEASE_NEXT_BRANCH:=dev
RELEASE_UPSTREAM:=upstream
MY_UPSTREAM:=origin
# Location of virtualenv used for development.
VENV?=.venv
# Source virtualenv to execute command (flake8, sphinx, twine, etc...)
IN_VENV=if [ -f $(VENV)/bin/activate ]; then . $(VENV)/bin/activate; fi;
PROJECT_URL?=https://github.com/galaxyproject/galaxy
GRUNT_DOCKER_NAME:=galaxy/client-builder:16.01
GRUNT_EXEC?=node_modules/grunt-cli/bin/grunt
WEBPACK_EXEC?=node_modules/webpack/bin/webpack.js
GXY_NODE_MODULES=client/node_modules
DOCS_DIR=doc
DOC_SOURCE_DIR=$(DOCS_DIR)/source
SLIDESHOW_DIR=$(DOC_SOURCE_DIR)/slideshow
OPEN_RESOURCE=bash -c 'open $$0 || xdg-open $$0'
SLIDESHOW_TO_PDF?=bash -c 'docker run --rm -v `pwd`:/cwd astefanutti/decktape /cwd/$$0 /cwd/`dirname $$0`/`basename -s .html $$0`.pdf'

all: help
	@echo "This makefile is primarily used for building Galaxy's JS client. A sensible all target is not yet implemented."

# Building docs requires sphinx and utilities be installed (see issue 3166) as well as pandoc.
# Run following commands to setup the Python portion of these requirements:
#   $ ./scripts/common_startup.sh
#   $ . .venv/bin/activate
#   $ pip install sphinx sphinx_rtd_theme lxml recommonmark
docs: ## generate Sphinx HTML documentation, including API docs
	$(IN_VENV) $(MAKE) -C doc clean
	$(IN_VENV) $(MAKE) -C doc html

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

lint: ## check style using tox and flake8 for Python 2 and Python 3
	$(IN_VENV) tox -e py27-lint && tox -e py34-lint

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

npm-deps: ## Install NodeJS dependencies.
	cd client && npm install

grunt: npm-deps ## Calls out to Grunt to build client
	cd client && $(GRUNT_EXEC)

style: npm-deps ## Calls the style task of Grunt
	cd client && $(GRUNT_EXEC) style

client-install-libs: npm-deps ## Fetch updated client dependencies using bower.
	cd client && $(GRUNT_EXEC) install-libs

client: grunt style ## Rebuild all client-side artifacts

charts: npm-deps ## Rebuild charts
	NODE_PATH=$(GXY_NODE_MODULES) client/$(WEBPACK_EXEC) -p --config config/plugins/visualizations/charts/webpack.config.js

grunt-docker-image: ## Build docker image for running grunt
	docker build -t ${GRUNT_DOCKER_NAME} client

grunt-docker: grunt-docker-image ## Run grunt inside docker
	docker run -it -v `pwd`:/data ${GRUNT_DOCKER_NAME}

clean-grunt-docker-image: ## Remove grunt docker image
	docker rmi ${GRUNT_DOCKER_NAME}

grunt-watch-style: npm-deps ## Execute watching style builder for dev purposes
	cd client && $(GRUNT_EXEC) watch-style

grunt-watch-develop: npm-deps ## Execute watching grunt builder for dev purposes (unpacked, allows debugger statements)
	cd client && $(GRUNT_EXEC) watch --develop

webpack-watch: npm-deps ## Execute watching webpack for dev purposes
	cd client && ./node_modules/webpack/bin/webpack.js --watch

client-develop: grunt-watch-style grunt-watch-develop webpack-watch  ## A useful target for parallel development building.
	@echo "Remember to rerun `make client` before committing!"


# Release Targets
release-create-rc: release-ensure-upstream ## Create a release-candidate branch
	git checkout dev
	git pull --ff-only $(RELEASE_UPSTREAM) dev
	git push $(MY_UPSTREAM) dev
	git checkout -b release_$(RELEASE_CURR)
	git push $(MY_UPSTREAM) release_$(RELEASE_CURR)
	git push $(RELEASE_UPSTREAM) release_$(RELEASE_CURR)
	git checkout -b version-$(RELEASE_CURR)
	sed -i.bak -e "s/^VERSION_MAJOR = .*/VERSION_MAJOR = \"$(RELEASE_CURR)\"/" lib/galaxy/version.py
	sed -i.bak -e "s/^VERSION_MINOR = .*/VERSION_MINOR = \"rc1\"/" lib/galaxy/version.py
	rm -f lib/galaxy/version.py.bak
	git add lib/galaxy/version.py
	git commit -m "Update version to $(RELEASE_CURR).rc1"
	git checkout dev

	git checkout -b version-$(RELEASE_NEXT).dev
	sed -i.bak -e "s/^VERSION_MAJOR = .*/VERSION_MAJOR = \"$(RELEASE_NEXT)\"/" lib/galaxy/version.py
	rm -f lib/galaxy/version.py.bak
	git add lib/galaxy/version.py
	git commit -m "Update version to $(RELEASE_NEXT).dev"

	-git merge version-$(RELEASE_CURR)
	git checkout --ours lib/galaxy/version.py
	git add lib/galaxy/version.py
	git commit -m "Merge branch 'version-$(RELEASE_CURR)' into version-$(RELEASE_NEXT).dev"
	git push $(MY_UPSTREAM) version-$(RELEASE_CURR):version-$(RELEASE_CURR)
	git push $(MY_UPSTREAM) version-$(RELEASE_NEXT).dev:version-$(RELEASE_NEXT).dev
	git checkout dev
	git branch -d version-$(RELEASE_CURR)
	git branch -d version-$(RELEASE_NEXT).dev
	# TODO: Use hub to automate these PR creations or push directly.
	@echo "Open a PR from version-$(RELEASE_CURR) of your fork to release_$(RELEASE_CURR)"
	@echo "Open a PR from version-$(RELEASE_NEXT).dev of your fork to dev"

release-create: release-ensure-upstream ## Create a release branch
	git checkout master
	git pull --ff-only $(RELEASE_UPSTREAM) master
	git push $(MY_UPSTREAM) master
	git checkout release_$(RELEASE_CURR)
	git pull --ff-only $(RELEASE_UPSTREAM) release_$(RELEASE_CURR)
	#git push $(MY_UPSTREAM) release_$(RELEASE_CURR)
	git checkout dev
	git pull --ff-only $(RELEASE_UPSTREAM) dev
	#git push $(MY_UPSTREAM) dev
	# Test run of merging. If there are conflicts, it will fail here.
	git merge release_$(RELEASE_CURR)
	git checkout release_$(RELEASE_CURR)
	sed -i.bak -e "s/^VERSION_MINOR = .*/VERSION_MINOR = None/" lib/galaxy/version.py
	rm -f lib/galaxy/version.py.bak
	git add lib/galaxy/version.py
	git commit -m "Update version to $(RELEASE_CURR)"
	git tag -m "Tag version $(RELEASE_CURR)" v$(RELEASE_CURR)

	git checkout dev
	-git merge release_$(RELEASE_CURR)
	git checkout --ours lib/galaxy/version.py
	git add lib/galaxy/version.py
	git commit -m "Merge branch 'release_$(RELEASE_CURR)' into dev"
	git checkout master
	git merge release_$(RELEASE_CURR)
	git push $(RELEASE_UPSTREAM) release_$(RELEASE_CURR):release_$(RELEASE_CURR)
	git push $(RELEASE_UPSTREAM) dev:dev
	git push $(RELEASE_UPSTREAM) master:master
	git push $(RELEASE_UPSTREAM) --tags

release-create-point: ## Create a point release
	git pull --ff-only $(RELEASE_UPSTREAM) master
	git push $(MY_UPSTREAM) master
	git checkout release_$(RELEASE_CURR)
	git pull --ff-only $(RELEASE_UPSTREAM) release_$(RELEASE_CURR)
	#git push $(MY_UPSTREAM) release_$(RELEASE_CURR)
	git checkout $(RELEASE_NEXT_BRANCH)
	git pull --ff-only $(RELEASE_UPSTREAM) $(RELEASE_NEXT_BRANCH)
	#git push $(MY_UPSTREAM) $(RELEASE_NEXT_BRANCH)
	git merge release_$(RELEASE_CURR)
	git checkout release_$(RELEASE_CURR)
	sed -i.bak -e "s/^VERSION_MINOR = .*/VERSION_MINOR = \"$(RELEASE_CURR_MINOR_NEXT)\"/" lib/galaxy/version.py
	rm -f lib/galaxy/version.py.bak
	git add lib/galaxy/version.py
	git commit -m "Update version to $(RELEASE_CURR).$(RELEASE_CURR_MINOR_NEXT)"
	git tag -m "Tag version $(RELEASE_CURR).$(RELEASE_CURR_MINOR_NEXT)" v$(RELEASE_CURR).$(RELEASE_CURR_MINOR_NEXT)
	git checkout $(RELEASE_NEXT_BRANCH)
	-git merge release_$(RELEASE_CURR)
	git checkout --ours lib/galaxy/version.py
	git add lib/galaxy/version.py
	git commit -m "Merge branch 'release_$(RELEASE_CURR)' into $(RELEASE_NEXT_BRANCH)"
	git checkout master
	git merge release_$(RELEASE_CURR)
	#git push origin release_$(RELEASE_CURR):release_$(RELEASE_CURR)
	#git push origin $(RELEASE_NEXT_BRANCH):release_$(RELEASE_NEXT_BRANCH)
	#git push origin master:master
	#git push origin --tags
	git checkout release_$(RELEASE_CURR)

.PHONY: help

help:
	@egrep '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

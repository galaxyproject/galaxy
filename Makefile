RELEASE_CURR:=16.01
RELEASE_NEXT:=16.04
RELEASE_UPSTREAM:=upstream
GRUNT_DOCKER_NAME:=galaxy/client-builder:16.01

all:
	@echo "This makefile is primarily used for building Galaxy's JS client. A sensible all target is not yet implemented."

npm-deps:
	cd client && npm install

grunt: npm-deps
	cd client && node_modules/grunt-cli/bin/grunt

style: npm-deps
	cd client && node_modules/grunt-cli/bin/grunt style

webpack: npm-deps
	cd client && node_modules/webpack/bin/webpack.js -p

client: grunt style webpack

grunt-docker-image:
	docker build -t ${GRUNT_DOCKER_NAME} client

grunt-docker: grunt-docker-image
	docker run -it -v `pwd`:/data ${GRUNT_DOCKER_NAME}

clean-grunt-docker-image:
	docker rmi ${GRUNT_DOCKER_NAME}


# Release Targets
create_release_rc:
	git checkout dev
	git pull ${RELEASE_UPSTREAM} dev
	git push origin dev
	git checkout -b release_$(RELEASE_CURR)
	git push origin release_$(RELEASE_CURR)
	git push ${RELEASE_UPSTREAM} release_$(RELEASE_CURR)
	git checkout -b version-$(RELEASE_CURR)
	sed -i "s/^VERSION_MAJOR = .*/VERSION_MAJOR = \"$(RELEASE_CURR)\"/" lib/galaxy/version.py
	sed -i "s/^VERSION_MINOR = .*/VERSION_MINOR = \"rc1\"/" lib/galaxy/version.py
	git add lib/galaxy/version.py
	git commit -m "Update version to $(RELEASE_CURR).rc1"
	git checkout dev

	git checkout -b version-$(RELEASE_NEXT).dev
	sed -i "s/^VERSION_MAJOR = .*/VERSION_MAJOR = \"$(RELEASE_NEXT)\"/" lib/galaxy/version.py
	git add lib/galaxy/version.py
	git commit -m "Update version to $(RELEASE_NEXT).dev"

	git merge version-$(RELEASE_CURR)
	git checkout --ours lib/galaxy/version.py
	git add lib/galaxy/version.py
	git commit -m "Merge branch 'version-$(RELEASE_CURR)' into version-$(RELEASE_NEXT).dev"
	git push origin version-$(RELEASE_CURR):version-$(RELEASE_CURR)
	git push origin version-$(RELEASE_NEXT).dev:version-$(RELEASE_NEXT).dev

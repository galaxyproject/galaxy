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

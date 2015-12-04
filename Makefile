GRUNT_DOCKER_NAME:=galaxy-client-builder

all:
	@echo "This makefile is used for building Galaxy's JS client. A sensible all action is not yet implemented"

npm-deps:
	cd client && npm install

grunt: npm-deps
	cd client && grunt

grunt-docker-image:
	docker build -t ${GRUNT_DOCKER_NAME} client

grunt-docker: grunt-docker-image
	docker run -it -v `pwd`:/data ${GRUNT_DOCKER_NAME}

clean-grunt-docker-image:
	docker rmi ${GRUNT_DOCKER_NAME}

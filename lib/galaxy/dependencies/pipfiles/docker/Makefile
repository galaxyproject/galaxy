all:
	if ! docker inspect galaxy/update-python-dependencies >/dev/null 2>&1; then \
		docker build --no-cache -t galaxy/update-python-dependencies .; \
	fi

clean:
	docker rmi --force galaxy/update-python-dependencies

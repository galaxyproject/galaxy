GALAXY_ROOT=../../../..

client:
	yarn build

dev:
	yarn dev

format:
	yarn format

lint:
	yarn typecheck && yarn lint

# These next two tasks don't really belong here, but they do demonstrate
# how to get a test server running and populated with some initial data
# for the new tool shed frontend.
run_test_backend:
	cd $(GALAXY_ROOT); TOOL_SHED_CONFIG_OVERRIDE_BOOTSTRAP_ADMIN_API_KEY=tsadminkey TOOL_SHED_VITE_PORT=4040 TOOL_SHED_API_VERSION=v2 ./run_tool_shed.sh

bootstrap_test_backend:
	cd $(GALAXY_ROOT); . .venv/bin/activate; python scripts/bootstrap_test_shed.py

# web_client uses the shared workspace member Makefile and adds the client
# build steps that produce the wheel's bundled static assets.
#
# DIST_PREREQS must be set before the include: the shared _dist target expands
# its prerequisites when its rule is parsed, which happens during the include.

# Built by `make client-production` in the repository root.
DIST_PREREQS = src/galaxy/web_client/client_build_hash.txt
# Extra artifact checks that must pass alongside `twine check`.
DIST_CHECK_EXTRA = uv run --no-project python check_artifacts.py $(DIST)/*

include ../package.Makefile

.PHONY: clean-web-client

# Removing .venv instead of $(VENV) is intentional, because we can't guarantee we created $(VENV)
clean: clean-build clean-pyc clean-tests clean-web-client

clean-web-client:
	rm -rf .venv
	rm -rf src/galaxy/web_client/dist src/galaxy/web_client/client_build_hash.txt

src/galaxy/web_client/client_build_hash.txt:
	# Use the main Galaxy virtualenv, since that's what `make client-production` uses
	cd ../..; \
		uv venv --allow-existing $(VENV); \
		$(IN_VENV) \
		uv pip install "nodejs-wheel==$$(cat client/.node_version)"; \
		make client-production
	mv ../../client/dist src/galaxy/web_client/
	git rev-parse HEAD > src/galaxy/web_client/client_build_hash.txt

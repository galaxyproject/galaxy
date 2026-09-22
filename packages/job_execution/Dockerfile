# Default: the latest stable Galaxy release. CI and development builds select
# RUNTIME_SOURCE=source to install the matching checkout instead of PyPI wheels.
ARG PYTHON_IMAGE=python:3.14.7-slim-trixie
ARG GALAXY_VERSION=26.1.1
ARG RUNTIME_SOURCE=release

FROM ${PYTHON_IMAGE} AS build-base
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /venv
# Stable 26.1 packages predate the objectstore extras. Install the supported
# baseline backends explicitly for both release and checkout builds.
RUN /venv/bin/python -m pip install --no-cache-dir boto3 azure-storage-blob python-irodsclient

FROM build-base AS release-build
ARG GALAXY_VERSION
# Pin the Galaxy dependency closure together; pinning only job-execution would
# allow pip to silently combine different Galaxy releases.
RUN /venv/bin/python -m pip install --no-cache-dir \
    "galaxy-util==${GALAXY_VERSION}" \
    "galaxy-tool-util-models==${GALAXY_VERSION}" \
    "galaxy-config==${GALAXY_VERSION}" \
    "galaxy-schema==${GALAXY_VERSION}" \
    "galaxy-tool-util==${GALAXY_VERSION}" \
    "galaxy-files==${GALAXY_VERSION}" \
    "galaxy-objectstore==${GALAXY_VERSION}" \
    "galaxy-data==${GALAXY_VERSION}" \
    "galaxy-job-execution==${GALAXY_VERSION}"

FROM build-base AS source-build
COPY lib /galaxy/lib
COPY packages /galaxy/packages
# setuptools-scm cannot discover package data without the Git checkout.
RUN for package in util tool_util_models config schema tool_util files objectstore data job_execution; do \
        printf 'graft src\nglobal-exclude *.py[cod]\n' > /galaxy/packages/$package/MANIFEST.in; \
    done \
    && /venv/bin/python -m pip install --no-cache-dir \
        /galaxy/packages/util \
        /galaxy/packages/tool_util_models \
        /galaxy/packages/config \
        /galaxy/packages/schema \
        /galaxy/packages/tool_util \
        /galaxy/packages/files \
        /galaxy/packages/objectstore \
        /galaxy/packages/data \
        /galaxy/packages/job_execution

FROM ${RUNTIME_SOURCE}-build AS runtime-build

FROM ${PYTHON_IMAGE} AS runtime
ARG GALAXY_VERSION
ARG GIT_COMMIT=unspecified
ARG BUILD_DATE=unspecified
LABEL org.opencontainers.image.title="galaxy-job-execution" \
      org.opencontainers.image.authors="galaxyproject.org" \
      org.opencontainers.image.vendor="Galaxy Project" \
      org.opencontainers.image.documentation="https://docs.galaxyproject.org/en/latest/admin/containerized_metadata.html" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${GALAXY_VERSION}" \
      org.opencontainers.image.source="https://github.com/galaxyproject/galaxy" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.created="${BUILD_DATE}"
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH="/venv/bin:${PATH}" XDG_CACHE_HOME=/tmp/galaxy-cache
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1t64 libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=runtime-build /venv /venv
# Check in the final environment, where build tools and source files are absent.
RUN python -m pip check \
    && XDG_CACHE_HOME=/tmp/galaxy-build-cache python -c "from galaxy.metadata.set_metadata import set_metadata; import pysam; import h5py" \
    && rm -rf /tmp/galaxy-build-cache \
    && mkdir -p /etc/galaxy \
    && python -c "from importlib.metadata import distributions; print('\n'.join(sorted(d.metadata['Name'] + '==' + d.version for d in distributions())))" > /etc/galaxy/requirements.txt
CMD ["galaxy-set-metadata"]

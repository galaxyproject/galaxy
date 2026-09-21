# Stage 1:
# - base: ubuntu (default) OR prebuilt image0
# - install build tools
# - install package into venv
# Stage 2:
# - copy venv to final image
# - finalize container (set path, user...)

# Init ARGs
ARG STAGE1_BASE=python:3.11-slim
ARG FINAL_STAGE_BASE=$STAGE1_BASE

ARG GIT_COMMIT=unspecified
ARG BUILD_DATE=unspecified
ARG IMAGE_TAG=unspecified

#======================================================
# Stage 1 - Setup common requirements for build
#======================================================
FROM $STAGE1_BASE AS stage1
ARG DEBIAN_FRONTEND=noninteractive

# Init Env
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8

# Install build dependencies + ansible
RUN set -xe; \
    echo "Acquire::http {No-Cache=True;};" > /etc/apt/apt.conf.d/no-cache \
    && apt-get -qq update && apt-get install -y --no-install-recommends \
        locales locales-all \
        git \
        make \
        libc-dev \
        bzip2 \
        gcc \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

ADD lib /galaxy/lib
ADD packages /galaxy/packages

# setuptools-scm cannot discover package data without the Git checkout. Include
# the source resources explicitly (error_codes.json, datatype configs, etc.).
# Install the Galaxy dependency closure from this checkout, not released wheels.
RUN for package in util tool_util_models config schema tool_util files objectstore data job_execution; do \
        printf 'graft src\nglobal-exclude *.py[cod]\n' > /galaxy/packages/$package/MANIFEST.in; \
    done \
    && python -m venv /venv \
    && /venv/bin/python -m pip install \
        /galaxy/packages/util \
        /galaxy/packages/tool_util_models \
        /galaxy/packages/config \
        /galaxy/packages/schema \
        /galaxy/packages/tool_util \
        /galaxy/packages/files \
        "/galaxy/packages/objectstore[all]" \
        /galaxy/packages/data \
        /galaxy/packages/job_execution
ENV LC_ALL en_US.UTF-8

#======================================================
# Stage 2.1 - Copy to final image
#======================================================
# Remove build artifacts + files not needed in container
FROM $STAGE1_BASE

COPY --from=stage1 /venv /venv


ARG GIT_COMMIT
ARG BUILD_DATE
ARG IMAGE_TAG

LABEL org.opencontainers.image.title="galaxy-job-execution" \
      org.opencontainers.image.authors="galaxyproject.org" \
      org.opencontainers.image.vendor="Galaxy Project" \
      org.opencontainers.image.documentation="https://github.com/galaxyproject/galaxy" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="$IMAGE_TAG" \
      org.opencontainers.image.url="https://github.com/galaxyproject/galaxy" \
      org.opencontainers.image.source="https://github.com/galaxyproject/galaxy.git" \
      org.opencontainers.image.revision=$GIT_COMMIT \
      org.opencontainers.image.created=$BUILD_DATE

# Init Env
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV PATH="/venv/bin:${PATH}"

# Fail the image build if the installed metadata runtime is incomplete.
RUN python -c "from galaxy.metadata.set_metadata import set_metadata"

CMD ["galaxy-set-metadata"]

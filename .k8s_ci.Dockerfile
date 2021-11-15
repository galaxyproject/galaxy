# Stage 1:
# - base: ubuntu (default) OR prebuilt image0
# - install build tools
# - clone playbook
# Stage 2: build galaxy client and server in parallel
# Stage 2.1:
# - run playbook with server build steps only
# - remove build artifacts + files not needed in container
# Stage 2.2:
# - run playbook with client build steps only
# - remove build artifacts + files not needed in container
# Stage 3:
# - install python-virtualenv
# - create galaxy user + group + directory
# - copy galaxy files from stage 2.1 and 2.2
# - finalize container (set path, user...)

# Init ARGs
ARG ROOT_DIR=/galaxy
ARG SERVER_DIR=$ROOT_DIR/server

# For much faster build time override this with image0 (Dockerfile.0 build):
#   docker build --build-arg BASE=<image0 name>...
ARG STAGE1_BASE=ubuntu:20.04
ARG FINAL_STAGE_BASE=$STAGE1_BASE
# NOTE: the value of GALAXY_USER must be also hardcoded in COPY in final stage
ARG GALAXY_USER=galaxy
ARG GALAXY_PLAYBOOK_REPO=https://github.com/galaxyproject/galaxy-docker-k8s

ARG GIT_COMMIT=unspecified
ARG BUILD_DATE=unspecified
ARG IMAGE_TAG=unspecified

#======================================================
# Stage 1 - Setup common requirements for build
#======================================================
FROM $STAGE1_BASE AS stage1
ARG DEBIAN_FRONTEND=noninteractive
ARG SERVER_DIR
ARG GALAXY_PLAYBOOK_REPO

# Init Env
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8

# Install build dependencies + ansible
RUN set -xe; \
    echo "force-unsafe-io" > /etc/dpkg/dpkg.cfg.d/02apt-speedup \
    && echo "Acquire::http {No-Cache=True;};" > /etc/apt/apt.conf.d/no-cache \
    && apt-get -qq update && apt-get install -y --no-install-recommends \
        locales locales-all \
        apt-transport-https \
        git \
        make \
        libpython3.6 \
        python3-dev \
        python3-virtualenv \
        software-properties-common \
        ssh \
        gcc \
    && apt-get -qq update && apt-get install -y --no-install-recommends \
        ansible \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# Remove context from previous build; copy current context; run playbook
WORKDIR /tmp/ansible
RUN rm -rf *
ENV LC_ALL en_US.UTF-8
RUN git clone --depth 1 $GALAXY_PLAYBOOK_REPO galaxy-docker
WORKDIR /tmp/ansible/galaxy-docker
RUN ansible-galaxy install -r requirements.yml -p roles --force-with-deps

# Add Galaxy source code
COPY . $SERVER_DIR/

#======================================================
# Stage 2.1 - Build galaxy server
#======================================================
FROM stage1 AS server_build
ARG SERVER_DIR

RUN ansible-playbook -i localhost, playbook.yml -v -e galaxy_build_client=False

RUN cat /galaxy/server/lib/galaxy/dependencies/conditional-requirements.txt | grep psycopg2-binary | xargs /galaxy/server/.venv/bin/pip install

# Remove build artifacts + files not needed in container
WORKDIR $SERVER_DIR
# Save commit hash of HEAD before zapping git folder
RUN git rev-parse HEAD > GITREVISION
RUN rm -rf \
        .ci \
        .git \
        .venv/include/node \
        .venv/src/node* \
        doc \
        test \
        test-data
# Clean up *all* node_modules, including plugins.  Everything is already built+staged.
RUN find . -name "node_modules" -type d -prune -exec rm -rf '{}' +

#======================================================
# Stage 2.2 - Build galaxy client
#======================================================
FROM stage1 AS client_build
ARG SERVER_DIR

RUN ansible-playbook -i localhost, playbook.yml -v --tags "galaxy_build_client"

WORKDIR $SERVER_DIR
RUN rm -rf \
        .ci \
        .git \
        .venv/include/node \
        .venv/src/node* \
        doc \
        test \
        test-data
# Clean up *all* node_modules, including plugins.  Everything is already built+staged.
RUN find . -name "node_modules" -type d -prune -exec rm -rf '{}' +

#======================================================
# Stage 3 - Build final image based on previous stages
#======================================================
FROM $FINAL_STAGE_BASE
ARG DEBIAN_FRONTEND=noninteractive
ARG ROOT_DIR
ARG SERVER_DIR
ARG GALAXY_USER

ARG GIT_COMMIT
ARG BUILD_DATE
ARG IMAGE_TAG

LABEL org.opencontainers.image.title="Galaxy Minimal Image" \
      org.opencontainers.image.description="A size optimized image for Galaxy targeting k8s and ci applications" \
      org.opencontainers.image.authors="galaxyproject.org" \
      org.opencontainers.image.vendor="Galaxy Project" \
      org.opencontainers.image.documentation="https://github.com/galaxyproject/galaxy-docker-k8s" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="$IMAGE_TAG" \
      org.opencontainers.image.url="https://github.com/galaxyproject/galaxy-docker-k8s" \
      org.opencontainers.image.source="https://github.com/galaxyproject/galaxy.git" \
      org.opencontainers.image.revision=$GIT_COMMIT \
      org.opencontainers.image.created=$BUILD_DATE

# Init Env
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8

# Install python-virtualenv
RUN set -xe; \
    echo "force-unsafe-io" > /etc/dpkg/dpkg.cfg.d/02apt-speedup \
    && echo "Acquire::http {No-Cache=True;};" > /etc/apt/apt.conf.d/no-cache \
    && apt-get -qq update && apt-get install -y --no-install-recommends \
        locales \
        libpython3.6 \
        python3-virtualenv \
        vim-tiny \
        nano-tiny \
        curl \
    && locale-gen $LANG && update-locale LANG=$LANG \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# Create Galaxy user, group, directory; chown
RUN set -xe; \
      adduser --system --group $GALAXY_USER \
      && mkdir -p $SERVER_DIR \
      && chown $GALAXY_USER:$GALAXY_USER $ROOT_DIR -R

WORKDIR $ROOT_DIR
# Copy galaxy files to final image
# The chown value MUST be hardcoded (see #35018 at github.com/moby/moby)
COPY --chown=galaxy:galaxy --from=server_build $ROOT_DIR .
COPY --chown=galaxy:galaxy --from=client_build $SERVER_DIR/static ./server/static

WORKDIR $SERVER_DIR
EXPOSE 8080
USER $GALAXY_USER

ENV PATH="$SERVER_DIR/.venv/bin:${PATH}"

# [optional] to run:
CMD uwsgi --yaml config/galaxy.yml

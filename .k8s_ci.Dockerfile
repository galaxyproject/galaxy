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
# - create galaxy user + group + directory
# - copy galaxy files from stage 2.1 and 2.2
# - finalize container (set path, user...)

# Init ARGs
ARG ROOT_DIR=/galaxy
ARG SERVER_DIR=$ROOT_DIR/server

ARG STAGE1_BASE=python:3.12-slim
ARG FINAL_STAGE_BASE=$STAGE1_BASE
ARG GALAXY_USER=galaxy
ARG GALAXY_PLAYBOOK_REPO=https://github.com/galaxyproject/galaxy-docker-k8s
ARG GALAXY_PLAYBOOK_BRANCH=v4.2.0

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
ARG GALAXY_PLAYBOOK_BRANCH

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
    && pip install --no-cache virtualenv ansible \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# Remove context from previous build; copy current context; run playbook
WORKDIR /tmp/ansible
RUN rm -rf *
ENV LC_ALL en_US.UTF-8
RUN git clone --depth 1 --branch $GALAXY_PLAYBOOK_BRANCH $GALAXY_PLAYBOOK_REPO galaxy-docker
WORKDIR /tmp/ansible/galaxy-docker
RUN ansible-galaxy install -r requirements.yml -p roles --force-with-deps

# Add Galaxy source code
COPY . $SERVER_DIR/

#======================================================
# Stage 2.1 - Build galaxy server
#======================================================
FROM stage1 AS server_build
ARG SERVER_DIR

RUN ansible-playbook -i localhost, playbook.yml -v -e "{galaxy_build_client: false}" -e galaxy_virtualenv_command=virtualenv

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

RUN ansible-playbook -i localhost, playbook.yml -v --tags "galaxy_build_client" -e galaxy_virtualenv_command=virtualenv

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

# Install procps (contains kill, ps etc.), less, curl, vim-tiny and nano-tiny
# for convenience and debugging purposes. Nano and vim commands are aliased
# to their tiny variants using the debian alternatives system.
# Bzip2 and virtualenv are installed for backwards compatibility with older
# versions of this image which was based on Ubuntu and contained these
# utilities.
RUN set -xe; \
    echo "Acquire::http {No-Cache=True;};" > /etc/apt/apt.conf.d/no-cache \
    && apt-get -qq update && apt-get install -y --no-install-recommends \
        locales \
        vim-tiny \
        nano-tiny \
        curl \
        procps \
        less \
        bzip2 \
        tini \
        nodejs \
    && update-alternatives --install /usr/bin/nano nano /bin/nano-tiny 0 \
    && update-alternatives --install /usr/bin/vim vim /usr/bin/vim.tiny 0 \
    && echo "set nocompatible\nset backspace=indent,eol,start" >> /usr/share/vim/vimrc.tiny \
    && echo "$LANG UTF-8" > /etc/locale.gen \
    && locale-gen $LANG && update-locale LANG=$LANG \
    && curl -L https://github.com/galaxyproject/gxadmin/releases/latest/download/gxadmin > /usr/bin/gxadmin \
    && chmod +x /usr/bin/gxadmin \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# Create Galaxy user, group, directory; chown
RUN set -xe; \
      adduser --system --group --uid 10001 $GALAXY_USER \
      && mkdir -p $SERVER_DIR \
      && chown $GALAXY_USER:$GALAXY_USER $ROOT_DIR -R

WORKDIR $ROOT_DIR
# Copy galaxy files to final image
# The chown value MUST be hardcoded (see https://github.com/moby/moby/issues/35018)
COPY --chown=$GALAXY_USER:$GALAXY_USER --from=server_build $ROOT_DIR .
COPY --chown=$GALAXY_USER:$GALAXY_USER --from=client_build $SERVER_DIR/static ./server/static

WORKDIR $SERVER_DIR

# The data in version.json will be displayed in Galaxy's /api/version endpoint
RUN printf "{\n  \"git_commit\": \"$(cat GITREVISION)\",\n  \"build_date\": \"$BUILD_DATE\",\n  \"image_tag\": \"$IMAGE_TAG\"\n}\n" > version.json \
    && chown $GALAXY_USER:$GALAXY_USER version.json

EXPOSE 8080
USER $GALAXY_USER

ENV PATH="$SERVER_DIR/.venv/bin:${PATH}"
ENV GALAXY_CONFIG_CONDA_AUTO_INIT=False

ENTRYPOINT ["tini", "--"]

# [optional] to run:
CMD galaxy

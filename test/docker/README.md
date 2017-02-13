## Overview

Setup Docker environment for use with testing using the following
commands.

    % cd test/base
    % docker build -t galaxy/testing-base .

Alternatively, this can be fetched from [Dockerhub](https://hub.docker.com/).

    % docker pull galaxy/testing-base

The resulting docker container is ready to run most of Galaxy tests
(functional tests for specific bioinformatics tools may still fail for
now until they are migrated out of Galaxy and to the tool shed).

## Tagging a New Image

The Galaxy team maintains a password store that contains the password
for the Galaxy user on Docker Hub. Docker Hub can be used to trigger a
manual build against the dev branch. Once built, it can be pulled,
tagged, and tested as follows:

    % docker pull galaxy/testing-base:latest  # notice latest digest
    % docker tag <digest> galaxy/testing-base:<version>
    % export DOCKER_IMAGE=galaxy/testing-base:<version>
    % ./run_tests.sh --dockerize --api  # or whatever test suite you wish

Once verified, the tag must be pushed back to Docker Hub with:

    % docker login # Put in galaxy as the username and the secret password 
    % docker push galaxy/testing-base:<version>

The version should be the next dot release with the current dev Galaxy
version as the major and minor release (e.g. 17.01 from Galaxy and .0
for the first published image - so 17.01.0, .1 for the second published
image - so 17.01.1, etc...).

A pull request to Galaxy updating the default Docker image to target should
be made.

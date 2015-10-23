Setup Docker environment for use with testing using the following
commands.

    % cd test/base
    % docker build -t galaxy/testing-base .

Alternatively, this can be fetched from [Dockerhub](https://hub.docker.com/).

    % docker pull galaxy/testing-base

The resulting docker container is ready to run most of Galaxy tests
(functional tests for specific bioinformatics tools may still fail for
now until they are migrated out of Galaxy and to the tool shed).

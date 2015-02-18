Setup Docker environment for use with testing using the following
commands (until this is on Docker hub).

    % cd test/base
    % docker build -t galaxyprojectdotorg/testing-base .

This will create a docker container ready to run most of Galaxy tests
(functional tests for specific bioinformatics tools may still fail for
now until they are migrated out of Galaxy and to the tool shed).

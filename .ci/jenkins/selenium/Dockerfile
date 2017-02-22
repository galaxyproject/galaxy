FROM toolshed/requirements
MAINTAINER John Chilton, jmchilton@gmail.com

RUN apt-get -qq update && \
    apt-get install --no-install-recommends -y postgresql-client python-pip && \
    apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV GALAXY_ROOT=/galaxy \
    GALAXY_CONFIG_OVERRIDE_ADMIN_USERS=admin@galaxy.org \
    GALAXY_CONFIG_OVERRIDE_ALLOW_USER_DATASET_PURGE=true \
    GALAXY_CONFIG_OVERRIDE_ALLOW_LIBRARY_PATH_PASTE=true \
    GALAXY_CONFIG_OVERRIDE_ENABLE_BETA_WORKFLOW_MODULES=true \
    GALAXY_CONFIG_OVERRIDE_ALLOW_USER_DELETION=true \
    GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION=postgresql://postgres@postgres/galaxy \
    GALAXY_CONFIG_OVERRIDE_MASTER_API_KEY=94a548bea347a35e457a804bf75bec53 \
    GALAXY_CONFIG_OVERRIDE_JOB_CONFIG_FILE=/galaxy/config/job_conf.xml.sample_basic \
    GALAXY_CONFIG_OVERRIDE_DATATYPES_CONFIG_FILE=/galaxy/test/functional/tools/sample_datatypes_conf.xml \
    GALAXY_CONFIG_OVERRIDE_TOOL_CONFIG_FILE=/galaxy/test/functional/tools/samples_tool_conf.xml \
    GALAXY_CONFIG_FILE=/galaxy/.ci/jenkins/selenium/galaxy.ini \
    GALAXY_VIRTUAL_ENV=/galaxy_env

ADD run_galaxy.bash /run_galaxy.bash
EXPOSE 8080
CMD /run_galaxy.bash

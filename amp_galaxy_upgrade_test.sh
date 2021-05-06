#!/bin/sh

###########################################################
# Phase 1: set up new Galaxy 21.01 instance on test server
###########################################################

# create a new galaxy_21.01 repository (we only need master_21.01 branch to start with)
cd /srv/amp;
git clone -b master_21.01 --single-branch https://Github.com/AudiovisualMetadataPlatform/galaxy galaxy_21.01;
cd galaxy_21.01;

# amp_mgm.ini is not in repository, copy from config/ on server directly
cp /srv/amp/galaxy/config/mgm.ini config/amp_mgm.ini;

# optionally, if we want to keep old Galaxy 19.01 instance running while testing new Galaxy 21.01 instance:
# modify /srv/amp/galaxy_21.01/config/galaxy.yml to set port to 8301 (http: :8300)

# all python and shell scripts need to be executable
chmod ugo+x tools/**/*.py tools/**/*.sh;

# set Galaxy python path
export GALAXY_PYTHON=/bin/python3;

# copy old Galaxy DB to new instance DB; NOTE: changes in old DB after this point will be ignored 
cp -r ../galaxy/database/* database/;

# remove all pre-compiled python2 templates
rm -rf database/compiled_templates/;

# remove all old python2 cached stuff
find . -name "*.pyc" -exec rm -v "{}" ";"

# need to execute run.sh first (to create/activate venv)
./run.sh --daemon;

# then mirgrate DB, otherwise manage_db.sh throws syntax error
sh manage_db.sh upgrade;

# install all MGM dependencies into venv
source .venv/bin/activate;
pip3 install -r amp_requirements.txt;
#python -m spacy download en_core_web_lg;
deactivate;

# now we can start Galaxy 21.01
./run.sh --daemon;

###########################################################
# Phase 2: smoke test Galaxy 21.01 instance on test server
###########################################################

###########################################################
# Phase 3: swap Galaxy 19.01/21.01 instances on test server
###########################################################

# stop both Galaxy 19.01 and 21.01 instances
cd /srv/amp/galaxy;
./run.sh --stop-daemon;
cd /srv/amp/galaxy_21.01;
./run.sh --stop-daemon;

# disable Galaxy Test Bamboo plan
# on AMP Galaxy Github: rename master branch to master_19.01, rename master_21.01 branch to master

# swap Galaxy directories
cd /srv/amp;
mv galaxy galaxy_19.01;
mv galaxy_21.01 galaxy;

# rename mgm.ini
cp /srv/amp/config/mgm.ini /srv/amp/config/amp_mgm.ini;

# remove .venv to regenerate it, since it contains python scripts referencing absolute path to the old .venv directory
rm -rf .venv;

# update Galaxy Test Bamboo  plan
# enable and run Galaxy Test Bamboo plan 



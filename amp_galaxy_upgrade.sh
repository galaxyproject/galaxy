#!/bin/sh

cd /srv/amp;

# create a new galaxy_21.01 repository (we only need master_21.01 branch to start with)
git clone -b master_21.01 --single-branch https://github.com/AudiovisualMetadataPlatform/galaxy galaxy_21.01;
cd galaxy_21.01;

# amp_mgm.ini is not in repository, copy from old instance on server directly
cp /srv/amp/galaxy/config/mgm.ini config/amp_mgm.ini;

# all python and shell scripts need to be executable
chmod ugo+x tools/**/*.py tools/**/*.sh;

# set Galaxy python path
export GALAXY_PYTHON=/bin/python3;

# copy galaxy DB to new instance DB: stop old galaxy instance if needed, as changes in old DB after this point will be ignored 
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
pip3 install -r config/amp_requirements.txt;
#python -m spacy download en_core_web_lg;
deactivate;

# now we can start galaxy 21.01
./run.sh --daemon;

# disable galaxy bamboo plan
# on AMP galaxy github: rename master branch to master_19.01, rename master_21.01 branch to master

# swap galaxy dirs
cd /srv/amp;
mv galaxy galaxy_19.01;
mv galaxy_21.01 galaxy;

# enable and run galaxy bamboo plan 
#############################################################################
# Phase 4: backup Galaxy 19.01 and set up 21.01 instances on staging server
#############################################################################

# stop Galaxy 19.01 instance
cd /srv/amp/galaxy;
./run.sh --stop-daemon;

# disable Galaxy Staging Bamboo plan
# on AMP Galaxy Github: rename staging branch to staging_19.01, clone master branch to staging

# backup Galaxy directory
cd /srv/amp;
mv galaxy galaxy_19.01;

# create a new galaxy repository (we only need staging branch to start with)
git clone -b staging --single-branch https://Github.com/AudiovisualMetadataPlatform/galaxy
cd galaxy;

# resolve selinux to ensure symlinks work acoss galaxy/
restorecon -vr;

# rename mgm.ini and copy it from config/ on server directly
cp /srv/amp/config/mgm.ini /srv/amp/config/amp_mgm.ini;
cp /srv/amp/config/amp_mgm.ini config/;

# all python and shell scripts need to be executable
chmod ugo+x tools/**/*.py tools/**/*.sh ./*.sh;

# set Galaxy python path
export GALAXY_PYTHON=/bin/python3;

# copy old Galaxy DB to new instance DB; NOTE: changes in old DB after this point will be ignored 
cp -r ../galaxy_19.01/database/ database/;

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
# en_core_web_lg can't be installed with pip3, need to install with python (include in Bamboo plan)
python -m spacy download en_core_web_lg;
deactivate;

# now we can start Galaxy 21.01
./run.sh --daemon;

# update Galaxy Staging Bamboo plan
# enable and run Galaxy Staging Bamboo plan 





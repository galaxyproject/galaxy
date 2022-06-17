#!/bin/bash

set -e

# Same hacks to setup a Galaxy user as used in test/docker/base/run_test_wrapper.sh
# We want to make sure Galaxy runs as the same user as the external user so the files have the correct permission.
echo "Deleting galaxy user - it may not exist and this is fine."
deluser galaxy | true

: ${GALAXY_TEST_UID:-"1"}

echo "Creating galaxy group with gid $GALAXY_TEST_UID - it may already exist and this is fine."
groupadd -r galaxy -g "$GALAXY_TEST_UID" | true
echo "Creating galaxy user with uid $GALAXY_TEST_UID - it may already exist and this is fine."
useradd -u $GALAXY_TEST_UID -r -g galaxy -d /home/galaxy -c "Galaxy User" galaxy -s /bin/bash | true
echo "Setting galaxy user password - the operation may fail."
echo "galaxy:galaxy" | chpasswd | true

virtualenv "$GALAXY_VIRTUAL_ENV"
chown -R "$GALAXY_TEST_UID:$GALAXY_TEST_UID" "$GALAXY_VIRTUAL_ENV"

cd /galaxy
sudo -E -H -u "#${GALAXY_TEST_UID}" ./scripts/common_startup.sh || { echo "common_startup.sh failed"; exit 1; }

echo "Waiting for postgres to become available"
while ! nc -z postgres 5432;
do
    sleep 1
    printf "."
done

echo "Creating postgres database for Galaxy"
createdb -w -U postgres -h postgres galaxy

echo "Starting and waiting for Galaxy daemon(s)"
sudo -E -H -u "#${GALAXY_TEST_UID}" GALAXY_RUN_ALL=1 bash "$GALAXY_ROOT/run.sh" --daemon --wait

echo "Galaxy daemon ready, monitoring Galaxy logs"
tail -f "$GALAXY_ROOT/main.log"

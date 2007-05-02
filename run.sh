#!/bin/sh

## Set MACHTYPE to something, 
MACHTYPE=`uname -m`
[ "$MACHTYPE" = "Power Macintosh" ] && MACHTYPE="powerpc"
LC_ALL=POSIX
export MACHTYPE LC_ALL

KERNEL=`uname -s | tr "A-Z" "a-z"`
ARCH="$KERNEL-$MACHTYPE"

echo "Architecture appears to be $ARCH"

UNIVERSE_HOME=`pwd`
PYTHONPATH=$UNIVERSE_HOME/lib:$UNIVERSE_HOME/eggs
export UNIVERSE_HOME PYTHONPATH

## For PBS - if you need to force node paths (i.e. the arch the frontend
## runs on is not the same arch as the compute nodes or Galaxy is
## installed in a different path on the node).
#NODEMACH="i686"
#NODEARCH="linux-i686"
#NODEPATH=$PATH

## Certain tools (EMBOSS, PAML...) are not distributed with Galaxy.
## If you have them installed, add their bin directories to the PATH.
PATH=$PATH:/depot/apps/$MACHTYPE/bin:/home/universe/$ARCH/EMBOSS/bin:/home/universe/$ARCH/ImageMagick/bin:/home/universe/$ARCH/PAML/paml3.15/bin

## NODEPATH defaults to $PATH
: ${NODEPATH:=$PATH}

export PATH NODEPATH

# Create directories
CREATE_DIRS="files tmp"
for CREATE_DIR in $CREATE_DIRS; do
    if [ ! -e $UNIVERSE_HOME/database/$CREATE_DIR ]; then
        mkdir -p $UNIVERSE_HOME/database/$CREATE_DIR
    fi
done

echo "python path: $PYTHONPATH"

python2.4 ./scripts/paster.py serve universe_wsgi.ini $@

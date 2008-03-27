## Set MACHTYPE to something, 
MACHTYPE=`uname -m`
[ "$MACHTYPE" = "Power Macintosh" ] && MACHTYPE="powerpc"
LC_ALL=POSIX
export MACHTYPE LC_ALL

KERNEL=`uname -s | tr "A-Z" "a-z"`
ARCH="$KERNEL-$MACHTYPE"

PLATFORMS=`$GALAXY_PYTHON ./scripts/get_platforms.py`

UNIVERSE_HOME=`pwd`
PYTHONPATH=$UNIVERSE_HOME/lib
for PLATFORM in $PLATFORMS; do
    echo "Using eggs in $PLATFORM"
    PYTHONPATH=$PYTHONPATH:$UNIVERSE_HOME/eggs/$PLATFORM
done

$GALAXY_PYTHON ./scripts/check_eggs.py
if [ $? -ne 0 ]; then
    exit 1
fi

export UNIVERSE_HOME PYTHONPATH

## For PBS - if you need to force node paths (i.e. the arch the frontend
## runs on is not the same arch as the compute nodes or Galaxy is
## installed in a different path on the node).
#NODEMACH="i686"
#NODEARCH="linux-i686"
#NODEPATH=$PATH

## Certain tools (EMBOSS, PAML...) are not distributed with Galaxy.
## If you have them installed, add their bin directories to the PATH.
PATH=$PATH:/depot/apps/$MACHTYPE/bin:/home/universe/$ARCH/EMBOSS-5.0.0/bin:/home/universe/$ARCH/ImageMagick/bin:/home/universe/$ARCH/PAML/paml3.15/bin

## NODEPATH defaults to $PATH
: ${NODEPATH:=$PATH}

export PATH NODEPATH

echo "python path: $PYTHONPATH"
echo "path: $PATH"

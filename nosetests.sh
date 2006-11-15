#!/bin/sh

## Set MACHTYPE to something, 
MACHTYPE=`uname -m`
if [[ $MACHTYPE = "Power Macintosh" ]]; then MACHTYPE="powerpc"; fi
export MACHTYPE 
export LC_ALL=POSIX

KERNEL=`uname -s | tr "A-Z" "a-z"`
ARCH="$KERNEL-$MACHTYPE"

echo "Architecture appears to be $ARCH"

export UNIVERSE_HOME=`pwd`
export PATH=$PATH:$UNIVERSE_HOME/arch/$ARCH/bin:/depot/apps/$MACHTYPE/bin:/home/universe/$ARCH/EMBOSS/EMBOSS-3.0.0/bin:/home/universe/$ARCH/EMBOSS/bin:/home/universe/$ARCH/ImageMagick/bin
export PYTHONPATH=$UNIVERSE_HOME/lib:$UNIVERSE_HOME/modules:$UNIVERSE_HOME/eggs:$UNIVERSE_HOME/arch/$ARCH/lib/python:eggs/NoseHTML-0.1-py2.4.egg

echo "python path: $PYTHONPATH"

python2.4 ./scripts/nosetests.py $@

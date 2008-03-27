#!/bin/sh
#
# Try to find a usable python
#

if [ "$GALAXY_PYTHON" != "" ]; then
    PYTHONS="$GALAXY_PYTHON"
else
    PYTHONS="python python2.4 python2.5"
fi

found=""
for python in $PYTHONS; do
    version=`$python -c 'import sys; print sys.version[:3]' 2>/dev/null`
    if [ $? -eq 0 ]; then
        case $version in
        2.4|2.5)
            found="$python"
            break
            ;;
        esac
    fi
done

if [ "$found" != "" ]; then
    GALAXY_PYTHON="$found"
else

    # user manually defined $GALAXY_PYTHON
    if [ "$GALAXY_PYTHON" != "" ]; then

        /bin/cat <<EOF
ERROR: \$GALAXY_PYTHON is set, but what it points to is not a suitable
Python interpreter.  This version of Galaxy requires either Python 2.4
or 2.5.  Possible solutions:
  * Unset \$GALAXY_PYTHON to let Galaxy attempt to find a suitable
    Python itself
  * Set \$GALAXY_PYTHON to a suitable Python interpreter.
\$GALAXY_PYTHON is currently set to: $GALAXY_PYTHON
EOF

    # couldn't find one in $PATH
    else

        /bin/cat <<EOF
ERROR: Unable to find a suitable Python interpreter.  This version of
Galaxy requires either Python 2.4 or 2.5.  Possible solutions:
  * If you have a suitable Python installed outside your \$PATH, modify
    your \$PATH to include it.
  * If you have a suitable Python installed outside your \$PATH and
    don't want to change your \$PATH, set the \$GALAXY_PYTHON environment
    variable to the path of your python executable.
  * If you don't have a suitable Python installed anywhere, install one.
EOF

    fi

    exit 1

fi

#!/bin/sh
set -e

SET_VENV=1
for arg in "$@"; do
    [ "$arg" = "--skip-venv" ] && SET_VENV=0
done

# Conda Python is in use, do not use virtualenv
if python -V 2>&1 | grep -q -e 'Anaconda' -e 'Continuum Analytics' ; then
    CONDA_ALREADY_INSTALLED=1
else
    CONDA_ALREADY_INSTALLED=0
fi

DEV_WHEELS=0
FETCH_WHEELS=1
CREATE_VENV=1
REPLACE_PIP=$SET_VENV
COPY_SAMPLE_FILES=1

for arg in "$@"; do
    [ "$arg" = "--skip-eggs" ] && FETCH_WHEELS=0
    [ "$arg" = "--skip-wheels" ] && FETCH_WHEELS=0
    [ "$arg" = "--dev-wheels" ] && DEV_WHEELS=1
    [ "$arg" = "--no-create-venv" ] && CREATE_VENV=0
    [ "$arg" = "--no-replace-pip" ] && REPLACE_PIP=0
    [ "$arg" = "--replace-pip" ] && REPLACE_PIP=1
    [ "$arg" = "--stop-daemon" ] && FETCH_WHEELS=0
    [ "$arg" = "--skip-samples" ] && COPY_SAMPLE_FILES=0
done

SAMPLES="
    config/migrated_tools_conf.xml.sample
    config/shed_tool_conf.xml.sample
    config/shed_tool_data_table_conf.xml.sample
    config/shed_data_manager_conf.xml.sample
    lib/tool_shed/scripts/bootstrap_tool_shed/user_info.xml.sample
    tool-data/shared/ucsc/builds.txt.sample
    tool-data/shared/ucsc/manual_builds.txt.sample
    tool-data/shared/ucsc/ucsc_build_sites.txt.sample
    tool-data/shared/igv/igv_build_sites.txt.sample
    tool-data/shared/rviewer/rviewer_build_sites.txt.sample
    static/welcome.html.sample
"

RMFILES="
    lib/pkg_resources.pyc
"

if [ $COPY_SAMPLE_FILES -eq 1 ]; then
	# Create any missing config/location files
	for sample in $SAMPLES; do
		file=${sample%.sample}
	    if [ ! -f "$file" -a -f "$sample" ]; then
	        echo "Initializing $file from $(basename "$sample")"
	        cp "$sample" "$file"
	    fi
	done
fi

# remove problematic cached files
for rmfile in $RMFILES; do
    [ -f "$rmfile" ] && rm -f "$rmfile"
done

: ${GALAXY_CONFIG_FILE:=config/galaxy.ini}
if [ ! -f "$GALAXY_CONFIG_FILE" ]; then
    GALAXY_CONFIG_FILE=universe_wsgi.ini
fi
if [ ! -f "$GALAXY_CONFIG_FILE" ]; then
    GALAXY_CONFIG_FILE=config/galaxy.ini.sample
fi

: ${GALAXY_VIRTUAL_ENV:=.venv}

if [ $SET_VENV -eq 1 -a $CREATE_VENV -eq 1 ]; then
    if [ ! -d "$GALAXY_VIRTUAL_ENV" ]
    then
        if [ $CONDA_ALREADY_INSTALLED -eq 1 ]; then
            echo "There is no existing Galaxy virtualenv and Conda is available, so we are skipping virtualenv creation.  Please be aware that this may cause missing dependencies."
            SET_VENV=0
        else
            # If .venv does not exist, and there is no conda available, attempt to create it.
            # Ensure Python is a supported version before creating .venv
            python ./scripts/check_python.py || exit 1
            if command -v virtualenv >/dev/null; then
                virtualenv -p python2.7 "$GALAXY_VIRTUAL_ENV"
            else
                vvers=13.1.2
                vurl="https://pypi.python.org/packages/source/v/virtualenv/virtualenv-${vvers}.tar.gz"
                vsha="aabc8ef18cddbd8a2a9c7f92bc43e2fea54b1147330d65db920ef3ce9812e3dc"
                vtmp=$(mktemp -d -t galaxy-virtualenv-XXXXXX)
                vsrc="$vtmp/$(basename $vurl)"
                # SSL certificates are not checked to prevent problems with messed
                # up client cert environments. We verify the download using a known
                # good sha256 sum instead.
                echo "Fetching $vurl"
                if command -v curl >/dev/null; then
                    curl --insecure -L -o "$vsrc" "$vurl"
                elif command -v wget >/dev/null; then
                    wget --no-check-certificate -O "$vsrc" "$vurl"
                else
                    python -c "import urllib; urllib.urlretrieve('$vurl', '$vsrc')"
                fi
                echo "Verifying $vsrc checksum is $vsha"
                python -c "import hashlib; assert hashlib.sha256(open('$vsrc', 'rb').read()).hexdigest() == '$vsha', '$vsrc: invalid checksum'"
                tar zxf "$vsrc" -C "$vtmp"
                python "$vtmp/virtualenv-$vvers/virtualenv.py" "$GALAXY_VIRTUAL_ENV"
                rm -rf "$vtmp"
            fi
        fi
    fi
fi

if [ $SET_VENV -eq 1 ]; then
    # If there is a .venv/ directory, assume it contains a virtualenv that we
    # should run this instance in.
    if [ -d "$GALAXY_VIRTUAL_ENV" ];
    then
        echo "Activating virtualenv at $GALAXY_VIRTUAL_ENV"
        . "$GALAXY_VIRTUAL_ENV/bin/activate"
        # Because it's a virtualenv, we assume $PYTHONPATH is unnecessary for
        # anything in the venv to work correctly, and having it set can cause
        # problems when there are conflicts with Galaxy's dependencies outside
        # the venv (e.g. virtualenv-burrito's pip and six).
        #
        # If you are skipping the venv setup we shall assume you know what
        # you're doing and will deal with any conflicts.
        unset PYTHONPATH
    fi

    if [ -z "$VIRTUAL_ENV" ]; then
        echo "ERROR: A virtualenv cannot be found. Please create a virtualenv in $GALAXY_VIRTUAL_ENV, or activate one."
        exit 1
    fi
fi

: ${GALAXY_WHEELS_INDEX_URL:="https://wheels.galaxyproject.org/simple"}
if [ $REPLACE_PIP -eq 1 ]; then
    pip install 'pip>=8.1'
fi

if [ $FETCH_WHEELS -eq 1 ]; then
    pip install -r requirements.txt --index-url "${GALAXY_WHEELS_INDEX_URL}"
    GALAXY_CONDITIONAL_DEPENDENCIES=$(PYTHONPATH=lib python -c "import galaxy.dependencies; print '\n'.join(galaxy.dependencies.optional('$GALAXY_CONFIG_FILE'))")
    [ -z "$GALAXY_CONDITIONAL_DEPENDENCIES" ] || echo "$GALAXY_CONDITIONAL_DEPENDENCIES" | pip install -r /dev/stdin --index-url "${GALAXY_WHEELS_INDEX_URL}"
fi

if [ $FETCH_WHEELS -eq 1 -a $DEV_WHEELS -eq 1 ]; then
    dev_requirements='./lib/galaxy/dependencies/dev-requirements.txt'
    [ -f $dev_requirements ] && pip install -r $dev_requirements --index-url "${GALAXY_WHEELS_INDEX_URL}"
fi

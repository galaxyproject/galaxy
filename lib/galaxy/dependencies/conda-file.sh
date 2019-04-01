#!/bin/bash
#
# Conda does not have all of Galaxy's dependencies, and the list of which ones it does is always changing. As a result,
# it's not possible to keep a conda requirements file up to date. However, with Conda >= 4.4, we can use Conda itself to
# determine which dependencies it can install. Pip will be used (upon Galaxy startup) to install the rest.
#
# You should use this script like so:
#
# conda create --override-channels -c conda-forge -c bioconda -c defaults \
#     -n <env> --file <(lib/galaxy/dependencies/conda-file.sh) python=2.7

here=$(dirname $0)

if ! command -v conda >/dev/null; then
    printf "$0: command not found: conda\n" >&2
    printf "hint: did you run 'conda activate base'?\n" >&2
    exit 1
fi

printf "Filtering out Galaxy requirements not available from Conda:" >&2
egrep -iv $( \
    conda create --override-channels -c conda-forge -c bioconda -c defaults \
        -n _gx_test_env --dry-run --file <(sed 's/;.*//' $here/pinned-requirements.txt) python=2.7 2>&1 \
        | grep '^\s*-' | grep -v https: | awk '{print $NF}' | paste -s -d'|' \
) $here/pinned-requirements.txt | sed 's/;.*//'
printf " done\n" >&2

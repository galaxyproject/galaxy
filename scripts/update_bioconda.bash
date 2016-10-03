#!/bin/bash

set -e

PACKAGE="galaxy-lib"
CONDA_RECIPES="bioconda-recipes"
UPSTREAM="bioconda"

HUB_EXEC=${HUB_EXEC:-`which hub | echo ''`}
if [ -z "$HUB_EXEC" ];
then
    HUB_EXEC="./hub/hub"
fi
HUB_EXEC=`python2 -c "import os; print os.path.abspath('$HUB_EXEC')"`
echo "Using hub executable $HUB_EXEC"

CONDA_EXEC=${CONDA_EXEC:-`which conda | echo ''`}
if [ -z "$CONDA_EXEC" ];
then
    CONDA_EXEC=~/miniconda2/bin/conda
fi
CONDA_EXEC=`python2 -c "import os; print os.path.abspath('$CONDA_EXEC')"`

RECIPE="recipes/$PACKAGE"
VERSION=`python2 -c "import xmlrpclib; print xmlrpclib.ServerProxy('https://pypi.python.org/pypi').package_releases('$PACKAGE')[0]"`
URL=`python2 -c "import xmlrpclib; import re; print re.escape([s for s in xmlrpclib.ServerProxy('https://pypi.python.org/pypi').release_urls('$PACKAGE', '$VERSION') if s['filename'].endswith('.tar.gz')][0]['url'])"`
MD5SUM=`md5sum dist/$PACKAGE-$VERSION.tar.gz | cut -d' ' -f1`
GITHUB_USER=`python2 -c "import json; import os.path; print json.loads(open(os.path.expanduser('~/.github.json'), 'r').read())['login']"`
BRANCH="$PACKAGE-$VERSION"

if [ ! -d $CONDA_RECIPES ];
then
    $HUB_EXEC clone $UPSTREAM/$CONDA_RECIPES
fi
cd $CONDA_RECIPES
$HUB_EXEC fork | true

git checkout master
git merge --ff-only origin/master

METADATA="$RECIPE/meta.yaml"
OLD_VERSION=`python2 -c "import yaml; print yaml.load(open('$METADATA', 'r').read())['package']['version']"`

OLD_RECIPE="$RECIPE/$OLD_VERSION"
mkdir "$OLD_RECIPE"
find "$RECIPE" -maxdepth 1 -type f | xargs -I {} cp {} "$OLD_RECIPE"

git checkout -b "$BRANCH"

sed -E -i "s/^  version: .*$/  version: \"$VERSION\"/" $METADATA
sed -E -i "s/^  url: .*$/  url: $URL/" $METADATA
sed -E -i "s/^  md5: .*$/  md5: $MD5SUM/" $METADATA

"$CONDA_EXEC" build "$RECIPE" --channel bioconda --channel r
git add "$RECIPE/meta.yaml"
git add "$OLD_RECIPE"
git commit -m "Update $PACKAGE to version $VERSION"
git push "$GITHUB_USER" "$BRANCH"

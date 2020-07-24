#!/bin/bash

set -e

helm repo add gxy https://raw.githubusercontent.com/cloudve/helm-charts/master/

cat ${HOME}/files_added.json
cat ${HOME}/files_modified.json

#!/bin/bash
#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

PULL_REPO=$1
PULL_DEST=$2

# is this is a merge request and there a branch with a name matching the MR branch in the
# other repo, pull that
export BRANCH_FOUND=""
if [ "${BUILD_CAUSE_SCMTRIGGER}" == "true" ]; then
logger "This is an SCM-caused build"
if [ "${gitlabActionType}" == 'MERGE' ]; then
logger "This is a merge-request-caused build"
    if [ "${gitlabSourceBranch}" != "" ]; then
    logger "The specified branch is: ${gitlabSourceBranch}"
    export BRANCH_FOUND=`git ls-remote -h ${PULL_REPO} | grep "refs/heads/${gitlabSourceBranch}$"`
    logger "Branch found test ${BRANCH_FOUND}"
    fi
fi
fi

if [ "${BRANCH_FOUND}" == "" ]; then
logger "No specified branch - is there a target branch?: ${gitlabTargetBranch}"
if [ "${gitlabTargetBranch}" != "" ]; then
    logger "A target branch is specified: ${gitlabTargetBranch}"
    export BRANCH_FOUND=`git ls-remote -h ${PULL_REPO} | grep "refs/heads/${gitlabTargetBranch}$"`
    logger "Branch found test ${BRANCH_FOUND}"
    if [ "${BRANCH_FOUND}" != "" ]; then
    export MR_BRANCH=${gitlabTargetBranch}
    else
    export MR_BRANCH=master
    fi
else
    export MR_BRANCH=master
fi
else
    export MR_BRANCH=${gitlabSourceBranch}
fi

git clone --branch ${MR_BRANCH} --single-branch --depth 1 ${PULL_REPO} ${PULL_DEST}

# Switch to project root; also root of repo checkout
pushd ${PULL_DEST}

git pull
git submodule update --init --recursive

popd


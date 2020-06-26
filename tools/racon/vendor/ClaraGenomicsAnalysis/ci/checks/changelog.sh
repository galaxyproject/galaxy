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

# Checkout master for comparison
git checkout --quiet master

# Switch back to tip of PR branch
git checkout --quiet current-pr-branch

# Ignore errors during searching
set +e

# Get list of modified files between matster and PR branch
CHANGELOG=`git diff --name-only master...current-pr-branch | grep CHANGELOG.md`
RETVAL=0

exit $RETVAL

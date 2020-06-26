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

# Ignore errors and set path
set -e

# Logger function for build status output
function logger() {
  echo -e "\n>>>> $@\n"
}

################################################################################
# Init
################################################################################

PATH=/conda/bin:$PATH

# Set home to the job's workspace
export HOME=$WORKSPACE

cd ${WORKSPACE}

source ci/common/prep-init-env.sh ${WORKSPACE}

################################################################################
# SDK style check
################################################################################

# Run copyright header check
logger "Run Copyright header check..."
./ci/checks/check_copyright.py

# Run style check
logger "Run Python formatting check..."
python -m pip install -r ./pyclaragenomics/requirements.txt
flake8 pyclaragenomics/

logger "Run C++ formatting check..."
mkdir --parents ${WORKSPACE}/build
cd ${WORKSPACE}/build

# Initialize CMake
cmake .. -DCMAKE_BUILD_TYPE=Release -Dcga_enable_tests=ON -Dcga_enable_benchmarks=ON

# Run format check
make check-format

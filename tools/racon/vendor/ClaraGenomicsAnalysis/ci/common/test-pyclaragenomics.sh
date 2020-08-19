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

######################################
# ClaraGenomicsAnalysis CPU/GPU conda build script for CI #
######################################
set -e

run_tests() {
  cd test/
  if [ "${TEST_ON_GPU}" == '1' ]; then
      python -m pytest -m gpu -s
  else
      python -m pytest -m cpu -s
  fi
}

PYCLARAGENOMICS_DIR=$1
cd $PYCLARAGENOMICS_DIR

# Install external dependencies.
python -m pip install -r requirements.txt
python setup_pyclaragenomics.py --build_output_folder cga_build
run_tests

cd $PYCLARAGENOMICS_DIR
# Uninstall pyclaragenomics
pip uninstall -y pyclaragenomics
# Test wheel package creation
python setup_pyclaragenomics.py --build_output_folder cga_build_wheel --create_wheel_only
yes | pip install $PYCLARAGENOMICS_DIR/pyclaragenomics_wheel/pyclaragenomics-*.whl
run_tests

#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

LOCAL_BUILD_ROOT=$1
CGA_ROOT=$2
CMAKE_OPTS=$3
BUILD_THREADS=$4
GPU_BUILD=$5
GPU_TEST=$6

if [ "$GPU_BUILD" == '1' ]; then
  CMAKE_BUILD_GPU="-Dracon_enable_cuda=ON -DCLARAGENOMICSANALYSIS_SRC_PATH=${CGA_ROOT}"
elif [ "$GPU_BUILD" == '0' ]; then
  CMAKE_BUILD_GPU="-Dracon_enable_cuda=OFF -DCLARAGENOMICSANALYSIS_SRC_PATH=${CGA_ROOT}"
fi

echo "CGA Root ${CGA_ROOT}"

cd ${LOCAL_BUILD_ROOT}
export LOCAL_BUILD_DIR=${LOCAL_BUILD_ROOT}/build

echo "Local build dir = ${LOCAL_BUILD_DIR}"
# Use CMake-based build procedure
mkdir --parents ${LOCAL_BUILD_DIR}
cd ${LOCAL_BUILD_DIR}

# configure
cmake $CMAKE_OPTS ${CMAKE_BUILD_GPU} ..
# build
make -j${BUILD_THREADS} VERBOSE=1 all

if [ "$GPU_TEST" == '1' ]; then
  logger "Pulling GPU test data..."
  cd ${WORKSPACE}
  if [ ! -d "ont-racon-data" ]; then
    if [ ! -f "${ont-racon-data.tar.gz}" ]; then
      wget -q -L https://s3.us-east-2.amazonaws.com/racon-data/ont-racon-data.tar.gz
    fi
    tar xvzf ont-racon-data.tar.gz
  fi

  logger "Running Racon end to end test..."

  logger "Test results..."
  cd ${LOCAL_BUILD_DIR}/bin
  ./cuda_test.sh
fi

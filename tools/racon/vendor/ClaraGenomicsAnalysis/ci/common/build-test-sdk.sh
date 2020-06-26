#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

CMAKE_BUILD_GPU=""
LOCAL_BUILD_ROOT=$1
CMAKE_OPTS=$2
BUILD_THREADS=$3
GPU_TEST=$4

cd ${LOCAL_BUILD_ROOT}
export LOCAL_BUILD_DIR=${LOCAL_BUILD_ROOT}/build

# Use CMake-based build procedure
mkdir --parents ${LOCAL_BUILD_DIR}
cd ${LOCAL_BUILD_DIR}

logger "Configure CMake..."
cmake .. $CMAKE_COMMON_VARIABLES ${CMAKE_BUILD_GPU} \
    -Dcga_enable_tests=ON \
    -Dcga_enable_benchmarks=ON \
    -Dcga_build_shared=ON \
    -DCMAKE_INSTALL_PREFIX=${LOCAL_BUILD_DIR}/install \
    -GNinja

logger "Run build..."
ninja all install package

logger "Install package..."
DISTRO=$(awk -F= '/^NAME/{print $2}' /etc/os-release)
DISTRO=${DISTRO//\"/}

PACKAGE_DIR=${LOCAL_BUILD_DIR}/cga-package
mkdir -p $PACKAGE_DIR
if [ "$DISTRO" == "Ubuntu" ]; then
    dpkg-deb -X ${LOCAL_BUILD_DIR}/*.deb $PACKAGE_DIR
elif [ "$DISTRO" == "CentOS Linux" ]; then
    rpm2cpio ${LOCAL_BUILD_DIR}/*.rpm | cpio -idmv
    mv usr/ $PACKAGE_DIR/
else
    echo "Unknown OS found - ${DISTRO}."
    exit 1
fi

logger "Creating symlink to installed package..."
UNPACK_ROOT=$(readlink -f "$PACKAGE_DIR/usr/local")
CGA_SYMLINK_PATH="$UNPACK_ROOT/ClaraGenomicsAnalysis"
ln -s $UNPACK_ROOT/ClaraGenomicsAnalysis-* $CGA_SYMLINK_PATH
CGA_LIB_DIR=${CGA_SYMLINK_PATH}/lib

# Run tests
if [ "$GPU_TEST" == '1' ]; then
  logger "GPU config..."
  nvidia-smi

  logger "Running ClaraGenomicsAnalysis unit tests..."
  # Avoid using 'find' which reutrns 0 even if -exec command fails
  for binary_test in "${LOCAL_BUILD_DIR}"/install/tests/*; do
    LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CGA_LIB_DIR "${binary_test}";
  done

  logger "Running ClaraGenomicsAnalysis benchmarks..."
  LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CGA_LIB_DIR ${LOCAL_BUILD_DIR}/install/benchmarks/cudapoa/benchmark_cudapoa --benchmark_filter="BM_SingleBatchTest"
  LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CGA_LIB_DIR ${LOCAL_BUILD_DIR}/install/benchmarks/cudaaligner/benchmark_cudaaligner --benchmark_filter="BM_SingleAlignment"
fi


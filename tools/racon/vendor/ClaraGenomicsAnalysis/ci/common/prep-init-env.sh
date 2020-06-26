#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

################################################################################
# SETUP - Check environment
################################################################################

logger "Get env..."
env

logger "Check versions..."
gcc --version
g++ --version

# FIX Added to deal with Anancoda SSL verification issues during conda builds
conda config --set ssl_verify False

# Conda add custom packages for ClaraGenomicsAnalysis CI
logger "Conda install ClaraGenomicsAnalysis custom packages"
conda install \
    -c conda-forge \
    -c sarcasm \
    -c bioconda \
    doxygen \
    clang-format \
    ninja \
    minimap2 \
    miniasm \
    racon \
    cmake

# Update LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib

# Show currentl installed paths
set -x
ls /usr/local/include
ls /usr/local/lib
set +x

################################################################################
# BUILD - Conda package builds 
################################################################################

CUDA_REL=${CUDA:0:3}
if [ "${CUDA:0:2}" == '10' ]; then
  # CUDA 10 release
  CUDA_REL=${CUDA:0:4}
fi

# Cleanup local git
cd "$1"
git clean -xdf


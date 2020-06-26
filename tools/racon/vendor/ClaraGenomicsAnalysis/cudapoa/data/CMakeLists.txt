#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

set(CUDAPOA_BENCHMARK_DATA_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../data")
configure_file(file_location.hpp.in ${PROJECT_BINARY_DIR}/data/file_location.hpp @ONLY)

set_property(GLOBAL PROPERTY cudapoa_data_include_dir "${PROJECT_BINARY_DIR}/data")

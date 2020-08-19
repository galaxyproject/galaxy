#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

# Add 3rd party build dependencies.
if (NOT TARGET bioparser)
    add_subdirectory(3rdparty/bioparser EXCLUDE_FROM_ALL)
endif()

get_property(enable_tests GLOBAL PROPERTY enable_tests)
if (enable_tests AND NOT TARGET gtest)
    add_subdirectory(3rdparty/googletest EXCLUDE_FROM_ALL)
endif()

get_property(enable_benchmarks GLOBAL PROPERTY enable_benchmarks)
if (enable_benchmarks AND NOT TARGET benchmark)
    set(BENCHMARK_ENABLE_TESTING OFF)
    set(BENCHMARK_ENABLE_GTEST_TESTS OFF)
    add_subdirectory(3rdparty/benchmark EXCLUDE_FROM_ALL)
endif()

if (NOT TARGET spdlog)
# FORCE spdlog to put out an install target, which we need
    set(SPDLOG_INSTALL ON CACHE BOOL "Generate the install target." FORCE)
    add_subdirectory(3rdparty/spdlog EXCLUDE_FROM_ALL)
endif()

if (NOT TARGET spoa)
    add_subdirectory(3rdparty/spoa EXCLUDE_FROM_ALL)
# Don't show warnings when compiling the 3rd party library
    target_compile_options(spoa PRIVATE -w)
endif()

set(CUB_DIR ${PROJECT_SOURCE_DIR}/3rdparty/cub CACHE STRING
	  "Path to cub repo")


#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

cmake_minimum_required(VERSION 3.10.2)
set(CGA_PROJECT_NAME ClaraGenomicsAnalysis)
set(CGA_VERSION 0.4.0)
project(${CGA_PROJECT_NAME})

# Process options.
option(cga_enable_tests "Build ClaraGenomicsAnalysis unit tests" OFF)
option(cga_enable_benchmarks "Build ClaraGenomicsAnalysis benchmarks" OFF)
option(cga_build_shared "Build ClaraGenomicsAnalysis libraries as shared objects" OFF)
option(cga_device_synchronize_kernels "Run cudaDeviceSynchronize() in CGA_CU_CHECK_ERR calls" OFF)
# The spoa_accurate option runs a different (and slower) version of
# the topological sort in cudapoa which exactly matches the output
# of the topological sort implementation in the SPOA library. This is
# useful for validation. When the option is turned off, a faster
# custom top sort function is run which outputs a correct but different
# ordering of the graph. This leads to subtle differences in the
# overall consensus generated, and hence makes it harder to validate and debug.
option(spoa_accurate "Run cudapoa code in mode that matches spoa" OFF)
option(cga_enable_cudapoa_nw_print "Enable verbose prints within cudapoa NW kernel" OFF)
option(cga_profiling "Compile a binary for profiling with NVTX markers." OFF)
option(cga_generate_docs "Generate Doxygen documentation" ON)

# Must be included before others for options value validation
include(cmake/Utils.cmake)

validate_boolean(cga_enable_tests)
if (cga_enable_tests)
    message(STATUS "Enabling ClaraGenomicsAnalysis unit tests")
    set_property(GLOBAL PROPERTY enable_tests ON)
endif()

validate_boolean(cga_enable_benchmarks)
if (cga_enable_benchmarks)
    message(STATUS "Enabling ClaraGenomicsAnalysis benchmarks")
    set_property(GLOBAL PROPERTY enable_benchmarks ON)
endif()

validate_boolean(cga_build_shared)
if (cga_build_shared)
    message(STATUS "Building ClaraGenomicsAnalysis libraries as shared objects")
    set_property(GLOBAL PROPERTY cga_library_type SHARED)
else()
    message(STATUS "Building ClaraGenomicsAnalysis libraries as static objects")
    set_property(GLOBAL PROPERTY cga_library_type STATIC)
endif()

include(cmake/CXX.cmake)
include(cmake/CUDA.cmake)
include(cmake/Doxygen.cmake)
include(cmake/3rdparty.cmake)
include(cmake/Tests.cmake)
include(cmake/Benchmarks.cmake)
include(cmake/Format.cmake)
include(cmake/Packaging.cmake)

# Add ClaraGenomicsAnalysis projects.
add_subdirectory(common/logging)
add_subdirectory(common/utils)
add_subdirectory(common/io)
add_subdirectory(cudapoa)
add_subdirectory(cudamapper)
add_subdirectory(cudaaligner)

# Add documentation generation.
validate_boolean(cga_generate_docs)
if (cga_generate_docs)
    message(STATUS "Enabling Doxygen documentation generation")
    set_doxygen_mainpage(${CMAKE_CURRENT_SOURCE_DIR}/README.md)
    add_docs_target("ClaraGenomicsAnalysis" "${CGA_VERSION}")
else()
    message(STATUS "Disabling Doxygen documentation generation")
endif()

# Add auto formatting.
cga_enable_formatting_targets()

if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set (CMAKE_INSTALL_PREFIX ${CMAKE_BINARY_DIR}/install CACHE PATH "The default SDK install path is install" FORCE)
endif (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)

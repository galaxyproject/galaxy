#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

project(cudapoa)

# Process data subdirectory first
add_subdirectory(data)

# Project specific NVCC flags
set(CUDA_NVCC_FLAGS "${CUDA_NVCC_FLAGS} -std=c++11")

get_property(cga_library_type GLOBAL PROPERTY cga_library_type)
cuda_add_library(cudapoa ${cga_library_type}
    src/cudapoa.cpp
    src/cudapoa_kernels.cu
    src/batch.cpp
    src/cudapoa_batch.cpp
    src/allocate_block.cpp
    )

target_link_libraries(cudapoa utils logging)

target_compile_options(cudapoa PRIVATE -Werror -Wall -Wextra -march=native)

if(cga_enable_cudapoa_nw_print)
    target_compile_definitions(cudapoa PUBLIC NW_VERBOSE_PRINT)
endif()

if(spoa_accurate)
    target_compile_definitions(cudapoa PUBLIC SPOA_ACCURATE)
endif()

target_include_directories(cudapoa 
    PUBLIC 
        $<INSTALL_INTERFACE:include>    
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

add_doxygen_source_dir(${CMAKE_CURRENT_SOURCE_DIR}/include)

install(TARGETS cudapoa
    COMPONENT logging
    EXPORT cudapoa
    DESTINATION lib
    INCLUDES DESTINATION include
)
install(DIRECTORY include/ DESTINATION include)
install(EXPORT cudapoa DESTINATION cmake)

# Add other folders.
add_subdirectory(tests)
add_subdirectory(benchmarks)
add_subdirectory(samples)


# Add auto formatting.
cga_enable_auto_formatting("${CMAKE_CURRENT_SOURCE_DIR}")

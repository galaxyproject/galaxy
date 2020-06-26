#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

project(cudaaligner)

# Project specific NVCC flags
if((CUDA_VERSION_MAJOR GREATER 10) OR (CUDA_VERSION_MAJOR EQUAL 10 AND CUDA_VERSION_MINOR GREATER 0))
set(CUDA_NVCC_FLAGS "${CUDA_NVCC_FLAGS} -std=c++14 --expt-relaxed-constexpr")
else()
set(CUDA_NVCC_FLAGS "${CUDA_NVCC_FLAGS} -std=c++14")
endif()

get_property(cga_library_type GLOBAL PROPERTY cga_library_type)
cuda_add_library(cudaaligner ${cga_library_type}
    src/cudaaligner.cpp
    src/aligner.cpp
    src/alignment_impl.cpp
    src/aligner_global.cpp
    src/aligner_global_ukkonen.cpp
    src/aligner_global_myers.cpp
    src/aligner_global_hirschberg_myers.cpp
    src/needleman_wunsch_cpu.cpp
    src/ukkonen_gpu.cu
    src/myers_gpu.cu
    src/hirschberg_myers_gpu.cu
    )

add_library(cudaaligner_internal INTERFACE)
target_include_directories(cudaaligner_internal INTERFACE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(cudaaligner utils logging)

target_compile_options(cudaaligner PRIVATE -Werror -Wall -Wextra -march=native)

target_include_directories(cudaaligner 
    PUBLIC 
        $<INSTALL_INTERFACE:include>    
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_compile_options(cudaaligner PRIVATE -Werror)

add_doxygen_source_dir(${CMAKE_CURRENT_SOURCE_DIR}/include)

# Add tests folder
add_subdirectory(tests)
add_subdirectory(benchmarks)
add_subdirectory(samples)

install(TARGETS cudaaligner
    COMPONENT logging
    EXPORT cudaaligner
    DESTINATION lib
    INCLUDES DESTINATION include
)
install(DIRECTORY include/ DESTINATION include)
install(EXPORT cudaaligner DESTINATION cmake)

# Add auto formatting.
cga_enable_auto_formatting("${CMAKE_CURRENT_SOURCE_DIR}")

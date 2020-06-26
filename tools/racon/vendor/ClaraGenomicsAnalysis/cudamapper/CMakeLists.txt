#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

project(cudamapper)

# Process data subdirectory first
add_subdirectory(data)

find_package(CUDA 9.0 QUIET REQUIRED)

if(NOT ${CUDA_FOUND})
    message(FATAL_ERROR "CUDA not detected on system. Please install")
else()
    message(STATUS "Using CUDA ${CUDA_VERSION} from ${CUDA_TOOLKIT_ROOT_DIR}")
    set(CUDA_NVCC_FLAGS "${CUDA_NVCC_FLAGS} -lineinfo --expt-extended-lambda -use_fast_math -Xcompiler -Wall,-Wno-pedantic -std=c++14")
endif()

cuda_add_library(minimizer
        src/minimizer.cu)
target_include_directories(minimizer PUBLIC include)
target_link_libraries(minimizer logging pthread utils)
target_compile_options(minimizer PRIVATE -Werror)

cuda_add_library(index_gpu
        src/index.cu
        src/index_gpu.cu
        src/minimizer.cu)
target_include_directories(index_gpu PUBLIC include)
target_link_libraries(index_gpu logging minimizer pthread utils cgaio)
target_compile_options(index_gpu PRIVATE -Werror)

cuda_add_library(matcher_gpu
        src/matcher_gpu.cu)
target_include_directories(matcher_gpu PUBLIC include)
target_link_libraries(matcher_gpu logging utils cgaio)
target_compile_options(matcher_gpu PRIVATE -Werror)

add_library(cudamapper_utils
        src/cudamapper_utils.cpp)
target_include_directories(cudamapper_utils PUBLIC include)

cuda_add_library(overlapper_triggerred
        src/overlapper_triggered.cu)
target_include_directories(overlapper_triggerred PUBLIC include ${CUB_DIR})
target_link_libraries(overlapper_triggerred logging utils cgaio)
target_compile_options(overlapper_triggerred PRIVATE -Werror)

add_doxygen_source_dir(${CMAKE_CURRENT_SOURCE_DIR}/include)

cuda_add_executable(cudamapper
        src/cudamapper.cpp
        src/main.cu
        src/matcher.cu
        src/overlapper.cpp
)

target_compile_options(cudamapper PRIVATE -Werror)

target_include_directories(cudamapper
    PUBLIC 
        $<INSTALL_INTERFACE:include>    
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_link_libraries(cudamapper utils index_gpu matcher_gpu logging overlapper_triggerred cudamapper_utils)

# Add tests folder
add_subdirectory(tests)

install(TARGETS cudamapper 
    EXPORT cudamapper
    DESTINATION bin
)
install(EXPORT cudamapper DESTINATION cmake)

# Add auto formatting.
cga_enable_auto_formatting("${CMAKE_CURRENT_SOURCE_DIR}")

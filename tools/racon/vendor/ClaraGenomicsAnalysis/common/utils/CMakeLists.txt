#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

project(utils)

add_library(utils INTERFACE)
target_link_libraries(utils INTERFACE logging)
if (cga_profiling)
    find_library(NVTX_LIBRARY nvToolsExt HINTS ${CUDA_TOOLKIT_ROOT_DIR}/lib64)
    target_compile_definitions(utils INTERFACE -DCGA_PROFILING)
    target_link_libraries(utils INTERFACE ${NVTX_LIBRARY})
endif()

add_doxygen_source_dir(${CMAKE_CURRENT_SOURCE_DIR}/include)

target_include_directories(utils
    INTERFACE 
        $<INSTALL_INTERFACE:include>    
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

if (cga_device_synchronize_kernels)
target_compile_definitions(utils
    INTERFACE
    CGA_DEVICE_SYNCHRONIZE)
endif()


install(TARGETS utils
    EXPORT utils
    DESTINATION lib
    INCLUDES DESTINATION include
)
install(DIRECTORY include/ DESTINATION include)
install(EXPORT utils DESTINATION cmake)

# Add tests
add_subdirectory(tests)

# Adding formatting
cga_enable_auto_formatting("${CMAKE_CURRENT_SOURCE_DIR}")

#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

project(logging)

get_property(cga_library_type GLOBAL PROPERTY cga_library_type)
add_library(logging ${cga_library_type}
        src/logging.cpp)
target_link_libraries(logging PUBLIC spdlog pthread utils)

add_doxygen_source_dir(${CMAKE_CURRENT_SOURCE_DIR}/include)

target_include_directories(logging
    PUBLIC 
        $<INSTALL_INTERFACE:include>    
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_compile_options(logging PRIVATE -Werror)

install(TARGETS logging 
    EXPORT logging
    DESTINATION lib
    INCLUDES DESTINATION include
)
install(DIRECTORY include/ DESTINATION include)
install(EXPORT logging DESTINATION cmake)

# Add auto formatting.
cga_enable_auto_formatting("${CMAKE_CURRENT_SOURCE_DIR}")

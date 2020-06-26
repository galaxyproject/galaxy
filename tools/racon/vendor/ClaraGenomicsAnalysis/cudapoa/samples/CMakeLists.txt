#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

project(sample_cudapoa)

get_property(cudapoa_data_include_dir GLOBAL PROPERTY cudapoa_data_include_dir)
include_directories(${cudapoa_data_include_dir})

add_executable(${PROJECT_NAME}
               sample_cudapoa.cpp
               )

target_link_libraries(${PROJECT_NAME}
                      cudapoa
                      )

install(TARGETS ${PROJECT_NAME}
            DESTINATION samples)

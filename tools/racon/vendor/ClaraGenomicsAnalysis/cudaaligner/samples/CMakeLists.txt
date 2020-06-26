#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

project(sample_cudaaligner)

add_executable(${PROJECT_NAME}
               sample_cudaaligner.cpp
               )

target_link_libraries(${PROJECT_NAME}
                      cudaaligner
                      )

install(TARGETS ${PROJECT_NAME}
            DESTINATION samples)

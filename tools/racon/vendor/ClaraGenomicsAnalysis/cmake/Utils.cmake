#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

function(validate_boolean CMAKE_OPTION)
    if ((NOT ${CMAKE_OPTION} STREQUAL "ON") AND (NOT ${CMAKE_OPTION} STREQUAL "OFF"))
        message(FATAL_ERROR "${CMAKE_OPTION}  can only be set to ON/OFF")
    endif()
endfunction(validate_boolean)

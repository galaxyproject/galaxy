#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

set(TARGET_NAME cgautilstests)

set(SOURCES
    main.cpp
    TestGraph.cpp)

set(LIBS
    utils)

cga_add_tests(${TARGET_NAME} "${SOURCES}" "${LIBS}")

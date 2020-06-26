#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

set(CGA_ENABLE_PACKAGING TRUE)

# Find Linux Distribution
EXECUTE_PROCESS(
    COMMAND "awk" "-F=" "/^NAME/{print $2}" "/etc/os-release"
    OUTPUT_VARIABLE LINUX_OS_NAME
    )

if (${LINUX_OS_NAME} MATCHES "Ubuntu")
    MESSAGE(STATUS "Package generator - DEB")
    SET(CPACK_GENERATOR "DEB")
elseif(${LINUX_OS_NAME} MATCHES "CentOS")
    MESSAGE(STATUS "Package generator - RPM")
    SET(CPACK_GENERATOR "RPM")
else()
    MESSAGE(STATUS "Unrecognized Linux distribution - ${LINUX_OS_NAME}. Disabling packaging.")
    set(CGA_ENABLE_PACKAGING FALSE)
endif()

if (CGA_ENABLE_PACKAGING)
    SET(CPACK_DEBIAN_PACKAGE_MAINTAINER "NVIDIA Corporation")
    SET(CPACK_PACKAGE_VERSION "${CGA_VERSION}")
    SET(CPACK_PACKAGING_INSTALL_PREFIX "/usr/local/${CGA_PROJECT_NAME}-${CGA_VERSION}")

    include(CPack)
endif()

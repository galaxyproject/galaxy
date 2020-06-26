#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

get_property(enable_benchmarks GLOBAL PROPERTY enable_benchmarks)
function(cga_add_benchmarks NAME MODULE SOURCES LIBS)
    # Add test executable
    if (enable_benchmarks)
        cuda_add_executable(${NAME} ${SOURCES})

        # Link gtest to benchmarks binary
        target_link_libraries(${NAME}
            ${LIBS}
            benchmark)
        # Install to benchmarks location
        install(TARGETS ${NAME}
            DESTINATION benchmarks/${MODULE})
    endif()
endfunction(cga_add_benchmarks)

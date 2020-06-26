#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#


project(benchmark_cudaaligner)

set(SOURCES
    main.cpp
    )

set(LIBS
    cudaaligner_internal
    cudaaligner
    utils)

cga_add_benchmarks(${PROJECT_NAME} "cudaaligner" "${SOURCES}" "${LIBS}")

install(FILES README.md
    DESTINATION benchmarks/cudaaligner)

#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

set(TARGET_NAME cudapoatests)

set(SOURCES
    main.cpp
    Test_CudapoaBatch.cpp
    Test_CudapoaTopSort.cpp
    Test_CudapoaAddAlignment.cpp
    Test_CudapoaNW.cpp
    Test_CudapoaGenerateConsensus.cpp
    Test_CudapoaBatchEnd2End.cpp
    Test_CudapoaGenerateMSA2.cpp
    Test_CudapoaSerializeGraph.cpp)

get_property(cudapoa_data_include_dir GLOBAL PROPERTY cudapoa_data_include_dir)
include_directories(${cudapoa_data_include_dir})

set(LIBS
    cudapoa
    spoa)

cga_add_tests(${TARGET_NAME} "${SOURCES}" "${LIBS}")

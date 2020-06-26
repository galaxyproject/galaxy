#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import pytest


from claragenomics.bindings import cuda


@pytest.mark.gpu
def test_cuda_get_device():
    device_count = cuda.cuda_get_device_count()
    assert(device_count > 0)


@pytest.mark.gpu
def test_cuda_device_selection():
    device_count = cuda.cuda_get_device_count()
    if (device_count > 0):
        for device in range(device_count):
            cuda.cuda_set_device(device)
            assert(cuda.cuda_get_device() == device)


@pytest.mark.gpu
def test_cuda_memory_info():
    device_count = cuda.cuda_get_device_count()
    if (device_count > 0):
        for device in range(device_count):
            (free, total) = cuda.cuda_get_mem_info(device)
            assert(free > 0)
            assert(total > 0)
            assert(free < total)

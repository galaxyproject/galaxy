#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

# cython: profile=False
# distutils: language = c++
# cython: embedsignature = True
# cython: language_level = 3

# Declare core CUDA structs and API calls which 
# can be used to interface with the CUDA runtime API.

# Declare cudaStream_t and cudaError_t without specifying particular
# include files since they will be added by the CUDA runtime API includes.
cdef extern from *:
    ctypedef void* _Stream "cudaStream_t"
    ctypedef int _Error "cudaError_t"

# Declare commonly used CUDA runtime API calls.
cdef extern from "cuda_runtime_api.h":
    # CUDA Stream APIs
    cdef _Error cudaStreamCreate(_Stream* s)
    cdef _Error cudaStreamDestroy(_Stream s)
    cdef _Error cudaStreamSynchronize(_Stream s)
    # CUDA Error APIs
    cdef _Error cudaGetLastError()
    cdef const char* cudaGetErrorString(_Error e)
    cdef const char* cudaGetErrorName(_Error e)
    # CUDA Device Info APIs
    cdef _Error cudaGetDeviceCount(int* count)
    cdef _Error cudaSetDevice(int device)
    cdef _Error cudaGetDevice(int* device)
    cdef _Error cudaMemGetInfo(size_t* free, size_t* total)

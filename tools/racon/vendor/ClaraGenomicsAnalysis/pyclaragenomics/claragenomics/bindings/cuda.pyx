#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

cimport claragenomics.bindings.cuda_runtime_api as cuda_runtime

class CudaRuntimeError(Exception):
    """
    Wrapper class for CUDA error handling.
    """
    def __init__(self, error):
        cdef cuda_runtime._Error e = error
        cdef bytes err_name = cuda_runtime.cudaGetErrorName(e)
        cdef bytes err_str = cuda_runtime.cudaGetErrorString(e)
        err_msg = "{} : {}".format(err_name.decode(), err_str.decode())
        super().__init__(err_msg)

cdef class CudaStream:
    """
    Class to abstract the usage of CUDA streams which enable
    easy asynchronous execution of CUDA kernels.
    """

    # Using size_t to store stream since underlying
    # representation of cudaStream_t is a (void *)
    # and python doesn't know how to deal with converting
    # (void *) to python objects.
    cdef size_t stream

    def __cinit__(self):
        """
        Constructs a CudaStream object to encapsulate a CUDA stream.
        """
        cdef cuda_runtime._Stream s
        cdef cuda_runtime._Error e = cuda_runtime.cudaStreamCreate(&s)
        if (e != 0):
            raise CudaRuntimeError(e)
        self.stream = <size_t>s

    def __init__(self):
        """
        Dummy implementation of __init__ function to allow
        for Python subclassing.
        """
        pass

    def __dealloc__(self):
        self.sync()
        cdef cuda_runtime._Stream s = <cuda_runtime._Stream>self.stream
        cdef cuda_runtime._Error e = cuda_runtime.cudaStreamDestroy(s)
        if (e != 0):
            raise CudaRuntimeError(e)

    def sync(self):
        """
        Synchronize the CUDA stream.
        """
        cdef cuda_runtime._Stream s = <cuda_runtime._Stream>self.stream
        cdef cuda_runtime._Error e = cuda_runtime.cudaStreamSynchronize(s)
        if (e != 0):
            raise CudaRuntimeError(e)

    @property
    def stream(self):
        """
        Get the raw stream representation.

        Returns:
            Raw stream encoded as size_t type
        """
        return self.stream

def cuda_get_device_count():
    """
    Get total number of CUDA-capable devices available.

    Returns:
        Number of CUDA-capable devices.
    """
    cdef int device_count
    cdef cuda_runtime._Error e = cuda_runtime.cudaGetDeviceCount(&device_count)
    if (e != 0):
        raise CudaRuntimeError(e)
    return device_count

def cuda_set_device(device_id):
    """
    Set current CUDA context to a specific device.
    """
    cdef cuda_runtime._Error e = cuda_runtime.cudaSetDevice(device_id)
    if (e != 0):
        raise CudaRuntimeError(e)

def cuda_get_device():
    """
    Get the device for the current CUDA context.

    Returns:
        Device ID for current context.
    """
    cdef int device_id
    cdef cuda_runtime._Error e = cuda_runtime.cudaGetDevice(&device_id)
    if (e != 0):
        raise CudaRuntimeError(e)
    return device_id

def cuda_get_mem_info(device_id):
    """
    Get memory information for a specific CUDA-capable device.

    Args:
        device_id : ID of CUDA-capable device

    Returns:
        A tuple with first element showing available memory and second
        element showing total memory (both in bytes).
    """
    cdef size_t free
    cdef size_t total
    initial_dev = cuda_get_device()
    if (initial_dev != device_id):
        cuda_set_device(device_id)
    cdef cuda_runtime._Error e = cuda_runtime.cudaMemGetInfo(&free, &total)
    if (e != 0):
        raise CudaRuntimeError(e)
    if (initial_dev != device_id):
        cuda_set_device(initial_dev)
    return (free, total)

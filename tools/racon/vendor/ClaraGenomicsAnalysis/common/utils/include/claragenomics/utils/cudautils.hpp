/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#pragma once
/// \file
/// \defgroup cudautils Internal CUDA utilities package

#include <claragenomics/utils/cudaversions.hpp>
#include <claragenomics/logging/logging.hpp>

#include <cuda_runtime_api.h>
#include <cassert>

#ifdef CGA_PROFILING
#include <nvToolsExt.h>
#endif // CGA_PROFILING

/// \ingroup cudautils
/// \{

/// \ingroup cudautils
/// \def CGA_CU_CHECK_ERR
/// \brief Log on CUDA error in enclosed expression
#define CGA_CU_CHECK_ERR(ans)                                            \
    {                                                                    \
        claragenomics::cudautils::gpu_assert((ans), __FILE__, __LINE__); \
    }

/// \}

namespace claragenomics
{

namespace cudautils
{

/// gpu_assert
/// Logs and/or exits on cuda error
/// \ingroup cudautils
/// \param code The CUDA status code of the function being asserted
/// \param file Filename of the calling function
/// \param line File line number of the calling function
inline void gpu_assert(cudaError_t code, const char* file, int line)
{
#ifdef CGA_DEVICE_SYNCHRONIZE
    // This device synchronize forces the most recent CUDA call to fully
    // complete, increasing the chance of catching the CUDA error near the
    // offending function. Only run if existing code is success to avoid
    // potentially overwriting previous error code.
    if (code == cudaSuccess)
    {
        code = cudaDeviceSynchronize();
    }
#endif

    if (code != cudaSuccess)
    {
        std::string err = "GPU Error:: " +
                          std::string(cudaGetErrorString(code)) +
                          " " + std::string(file) +
                          " " + std::to_string(line);
        CGA_LOG_ERROR("{}\n", err);
        // In Debug mode, this assert will cause a debugger trap
        // which is beneficial when debugging errors.
        assert(false);
        std::abort();
    }
}

/// align
/// Alignment of memory chunks in cudapoa. Must be a power of two
/// \tparam IntType type of data to align
/// \tparam boundary Boundary to align to (NOTE: must be power of 2)
/// \param value Input value that is to be aligned
/// \return Value aligned to boundary
template <typename IntType, int32_t boundary>
__host__ __device__ __forceinline__
    IntType
    align(const IntType& value)
{
    static_assert((boundary & (boundary - 1)) == 0, "Boundary for align must be power of 2");
    return (value + boundary) & ~(boundary - 1);
}

#ifdef CGA_PROFILING
/// \ingroup cudautils
/// \def CGA_NVTX_RANGE
/// \brief starts an NVTX range for profiling which stops automatically at the end of the scope
/// \param varname an arbitrary variable name for the nvtx_range object, which doesn't conflict with other variables in the scope
/// \param label the label/name of the NVTX range
#define CGA_NVTX_RANGE(varname, label) ::claragenomics::cudautils::nvtx_range varname(label)
/// nvtx_range
/// implementation of CGA_NVTX_RANGE
class nvtx_range
{
public:
    explicit nvtx_range(char const* name)
    {
        nvtxRangePush(name);
    }

    ~nvtx_range()
    {
        nvtxRangePop();
    }
};
#else
/// \ingroup cudautils
/// \def CGA_NVTX_RANGE
/// \brief Dummy implementation for CGA_NVTX_RANGE macro
/// \param varname Unused variable
/// \param label Unused variable
#define CGA_NVTX_RANGE(varname, label)
#endif // CGA_PROFILING

} // namespace cudautils

/// \brief A class to switch the CUDA device for the current scope using RAII
///
/// This class takes a CUDA device during construction,
/// switches to the given device using cudaSetDevice,
/// and switches back to the CUDA device which was current before the switch on destruction.
class scoped_device_switch
{
public:
    /// \brief Constructor
    ///
    /// \param device_id ID of CUDA device to switch to while class is in scope
    explicit scoped_device_switch(int32_t device_id)
    {
        CGA_CU_CHECK_ERR(cudaGetDevice(&device_id_before_));
        CGA_CU_CHECK_ERR(cudaSetDevice(device_id));
    }

    /// \brief Destructor switches back to original device ID
    ~scoped_device_switch()
    {
        cudaSetDevice(device_id_before_);
    }

    scoped_device_switch()                            = delete;
    scoped_device_switch(scoped_device_switch const&) = delete;
    scoped_device_switch& operator=(scoped_device_switch const&) = delete;

private:
    int32_t device_id_before_;
};

} // namespace claragenomics

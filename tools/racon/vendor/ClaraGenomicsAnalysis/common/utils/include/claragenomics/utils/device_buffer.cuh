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

#include <claragenomics/utils/cudautils.hpp>
#include <exception>
#include <utility>
#include <cassert>
#ifndef NDEBUG
#include <limits>
#endif

namespace claragenomics
{

class device_memory_allocation_exception : public std::exception
{
public:
    device_memory_allocation_exception()                                          = default;
    device_memory_allocation_exception(device_memory_allocation_exception const&) = default;
    device_memory_allocation_exception& operator=(device_memory_allocation_exception const&) = default;
    virtual ~device_memory_allocation_exception()                                            = default;

    virtual const char* what() const noexcept
    {
        return "Could not allocate device memory!";
    }
};

template <typename T>
class device_buffer
{
public:
    using value_type = T;

    device_buffer() = default;

    explicit device_buffer(size_t n_elements)
        : size_(n_elements)
    {
        cudaError_t err = cudaMalloc(reinterpret_cast<void**>(&data_), size_ * sizeof(T));
        if (err == cudaErrorMemoryAllocation)
        {
            // Clear the error from the runtime...
            err = cudaGetLastError();
            // Did a different async error happen in the meantime?
            if (err != cudaErrorMemoryAllocation)
            {
                CGA_CU_CHECK_ERR(err);
            }
            throw device_memory_allocation_exception();
        }
        CGA_CU_CHECK_ERR(err);
    }

    device_buffer(device_buffer const&) = delete;
    device_buffer& operator=(device_buffer const&) = delete;

    device_buffer(device_buffer&& r)
        : data_(std::exchange(r.data_, nullptr))
        , size_(std::exchange(r.size_, 0))
    {
    }

    device_buffer& operator=(device_buffer&& r)
    {
        data_ = std::exchange(r.data_, nullptr);
        size_ = std::exchange(r.size_, 0);
        return *this;
    }

    void free()
    {
        CGA_CU_CHECK_ERR(cudaFree(data_));
        data_ = nullptr;
        size_ = 0;
    }

    ~device_buffer()
    {
        cudaFree(data_);
    }

    value_type* data() { return data_; }
    value_type const* data() const { return data_; }
    size_t size() const { return size_; }

private:
    value_type* data_ = nullptr;
    size_t size_      = 0;
};

template <typename T>
void device_memset_async(device_buffer<T>& buffer, int value, cudaStream_t stream)
{
    assert(value <= std::numeric_limits<unsigned char>::max());
    CGA_CU_CHECK_ERR(cudaMemsetAsync(buffer.data(), value, sizeof(typename device_buffer<T>::value_type) * buffer.size(), stream));
}

} // end namespace claragenomics

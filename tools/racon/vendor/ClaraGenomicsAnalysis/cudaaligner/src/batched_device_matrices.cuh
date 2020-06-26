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

#include "matrix_cpu.hpp"

#include <claragenomics/utils/cudautils.hpp>
#include <claragenomics/utils/device_buffer.cuh>

#include <tuple>
#include <cassert>

namespace claragenomics
{
namespace cudaaligner
{

__device__ inline bool error(int32_t x, int32_t y)
{
    printf("assert: x=%d, y=%d\n", x, y);
    return false;
}

template <typename T>
class device_matrix_view
{
public:
    __device__ device_matrix_view(T* storage, int32_t n_rows, int32_t n_cols)
        : data_(storage)
        , n_rows_(n_rows)
        , n_cols_(n_cols)
    {
    }

    __device__ inline T const& operator()(int32_t i, int32_t j) const
    {
        assert(0 <= i || error(0, i));
        assert(i < n_rows_ || error(i, n_rows_));
        assert(0 <= j || error(0, j));
        assert(j < n_cols_ || error(j, n_cols_));
        return data_[i + n_rows_ * j];
    }
    __device__ inline T& operator()(int32_t i, int32_t j)
    {
        assert(0 <= i || error(0, i));
        assert(i < n_rows_ || error(i, n_rows_));
        assert(0 <= j || error(0, j));
        assert(j < n_cols_ || error(j, n_cols_));
        return data_[i + n_rows_ * j];
    }
    __device__ inline int32_t num_rows() const
    {
        return n_rows_;
    }
    __device__ inline int32_t num_cols() const
    {
        return n_cols_;
    }

private:
    T* data_;
    int32_t n_rows_;
    int32_t n_cols_;
};

template <typename T>
class batched_device_matrices
{
public:
    class device_interface
    {
    public:
        device_interface(T* storage, int32_t n_matrices, int32_t max_elements_per_matrix)
            : storage_(storage)
            , max_elements_per_matrix_(max_elements_per_matrix)
            , n_matrices_(n_matrices)
        {
        }
        __device__ device_matrix_view<T> get_matrix_view(int32_t id, int32_t n_rows, int32_t n_cols)
        {
            assert(id < n_matrices_);
            assert(n_rows * n_cols <= max_elements_per_matrix_ || error(n_rows * n_cols, max_elements_per_matrix_));
            if (n_rows * n_cols > max_elements_per_matrix_)
            {
                n_rows = 0;
                n_cols = 0;
            }
            return device_matrix_view<T>(storage_ + id * static_cast<ptrdiff_t>(max_elements_per_matrix_), n_rows, n_cols);
        }
        __device__ inline T* data(int32_t id)
        {
            return storage_ + id * static_cast<ptrdiff_t>(max_elements_per_matrix_);
        }

        __device__ inline int32_t get_max_elements_per_matrix() const
        {
            return max_elements_per_matrix_;
        }

    private:
        T* storage_;
        int32_t max_elements_per_matrix_;
        int32_t n_matrices_;
    };

    batched_device_matrices(int32_t n_matrices, int32_t max_elements_per_matrix, cudaStream_t stream)
        : storage_(static_cast<size_t>(n_matrices) * static_cast<size_t>(max_elements_per_matrix))
        , max_elements_per_matrix_(max_elements_per_matrix)
        , n_matrices_(n_matrices)
    {
        CGA_CU_CHECK_ERR(cudaMalloc(reinterpret_cast<void**>(&dev_), sizeof(device_interface)));
        CGA_CU_CHECK_ERR(cudaMemsetAsync(storage_.data(), 0, storage_.size() * sizeof(T), stream));
        device_interface tmp(storage_.data(), n_matrices_, max_elements_per_matrix_);
        CGA_CU_CHECK_ERR(cudaMemcpyAsync(dev_, &tmp, sizeof(device_interface), cudaMemcpyHostToDevice, stream));
        CGA_CU_CHECK_ERR(cudaStreamSynchronize(stream)); // sync because tmp will be destroyed.
    }

    ~batched_device_matrices()
    {
        cudaFree(dev_);
    }

    device_interface* get_device_interface()
    {
        return dev_;
    }

    matrix<T> get_matrix(int32_t id, int32_t n_rows, int32_t n_cols, cudaStream_t stream)
    {
        assert(id >= 0);
        assert(n_rows >= 0);
        assert(n_cols >= 0);

        if (id >= n_matrices_)
            throw std::runtime_error("Requested id is out of bounds.");

        if (n_rows * n_cols > max_elements_per_matrix_)
            throw std::runtime_error("Requested matrix size is larger than batched_device_matrices::max_elements_per_matrix_.");
        matrix<T> m(n_rows, n_cols);
        CGA_CU_CHECK_ERR(cudaMemcpyAsync(m.data(), storage_.data() + id * static_cast<ptrdiff_t>(max_elements_per_matrix_), sizeof(T) * n_rows * n_cols, cudaMemcpyDeviceToHost, stream));
        CGA_CU_CHECK_ERR(cudaStreamSynchronize(stream));
        return m;
    }

private:
    device_buffer<T> storage_;
    device_interface* dev_ = nullptr;
    int32_t max_elements_per_matrix_;
    int32_t n_matrices_;
};

} // end namespace cudaaligner
} // end namespace claragenomics

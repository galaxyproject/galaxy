/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "ukkonen_gpu.cuh"
#include "batched_device_matrices.cuh"
#include <claragenomics/cudaaligner/cudaaligner.hpp>
#include <claragenomics/utils/limits.cuh>

#include <limits>
#include <cstdint>
#include <algorithm>
#include <cassert>
#include <thrust/tuple.h>

#define CGA_UKKONEN_MAX_THREADS_PER_BLOCK 1024

namespace claragenomics
{
namespace cudaaligner
{
namespace kernels
{

template <typename T>
__device__ T min3(T t1, T t2, T t3)
{
    return min(t1, min(t2, t3));
}

__device__ thrust::tuple<int, int> to_matrix_indices(int k, int l, int p)
{
    int const j = k - (p + l) / 2 + l;
    int const i = l - j;
    return thrust::make_tuple(i, j);
}

__device__ thrust::tuple<int, int> to_band_indices(int i, int j, int p)
{
    int const k = (j - i + p) / 2;
    int const l = (j + i);
    return thrust::make_tuple(k, l);
}

#ifndef NDEBUG
__launch_bounds__(CGA_UKKONEN_MAX_THREADS_PER_BLOCK) // Workaround for a register allocation problem when compiled with -g
#endif
    __global__ void ukkonen_backtrace_kernel(int8_t* paths_base, int32_t* lengths, int32_t max_path_length, batched_device_matrices<nw_score_t>::device_interface* s, int32_t const* sequence_lengths_d, int32_t n_alignments, int32_t p)
{
    // Using scoring schema from cudaaligner.hpp
    // Match = 0
    // Mismatch = 1
    // Insertion = 2
    // Deletion = 3

    using thrust::swap;
    using thrust::tie;
    int32_t const id = blockIdx.x * blockDim.x + threadIdx.x;

    if (id >= n_alignments)
        return;

    CGA_CONSTEXPR nw_score_t max = numeric_limits<nw_score_t>::max() - 1;

    int32_t m        = sequence_lengths_d[2 * id] + 1;
    int32_t n        = sequence_lengths_d[2 * id + 1] + 1;
    int8_t insertion = static_cast<int8_t>(AlignmentState::insertion);
    int8_t deletion  = static_cast<int8_t>(AlignmentState::deletion);
    if (m > n)
    {
        swap(n, m);
        swap(insertion, deletion);
    }
    int8_t* path = paths_base + id * static_cast<ptrdiff_t>(max_path_length);
    assert(p >= 0);
    assert(n >= m);
    int32_t const bw                      = (1 + n - m + 2 * p + 1) / 2;
    device_matrix_view<nw_score_t> scores = s->get_matrix_view(id, bw, n + m);

    int32_t i = m - 1;
    int32_t j = n - 1;

    nw_score_t myscore = [scores, i, j, p] {
        int k, l;
        tie(k, l) = to_band_indices(i, j, p);
        return scores(k, l);
    }();
    int32_t pos = 0;
    while (i > 0 && j > 0)
    {
        int8_t r = 0;
        int k, l;
        tie(k, l)              = to_band_indices(i - 1, j, p);
        nw_score_t const above = k < 0 || k >= scores.num_rows() || l < 0 || l >= scores.num_cols() ? max : scores(k, l);
        tie(k, l)              = to_band_indices(i - 1, j - 1, p);
        nw_score_t const diag  = k < 0 || k >= scores.num_rows() || l < 0 || l >= scores.num_cols() ? max : scores(k, l);
        tie(k, l)              = to_band_indices(i, j - 1, p);
        nw_score_t const left  = k < 0 || k >= scores.num_rows() || l < 0 || l >= scores.num_cols() ? max : scores(k, l);

        if (left + 1 == myscore)
        {
            r       = insertion;
            myscore = left;
            --j;
        }
        else if (above + 1 == myscore)
        {
            r       = deletion;
            myscore = above;
            --i;
        }
        else
        {
            r       = (diag == myscore ? static_cast<int8_t>(AlignmentState::match) : static_cast<int8_t>(AlignmentState::mismatch));
            myscore = diag;
            --i;
            --j;
        }
        path[pos] = r;
        ++pos;
    }
    while (i > 0)
    {
        path[pos] = deletion;
        ++pos;
        --i;
    }
    while (j > 0)
    {
        path[pos] = insertion;
        ++pos;
        --j;
    }
    lengths[id] = pos;
}

__device__ void ukkonen_compute_score_matrix_odd(device_matrix_view<nw_score_t>& scores, int32_t kmax, int32_t k, int32_t m, int32_t n, char const* query, char const* target, int32_t max_target_query_length, int32_t p, int32_t l)
{
    CGA_CONSTEXPR nw_score_t max = numeric_limits<nw_score_t>::max() - 1;
    while (k < kmax)
    {
        int32_t const lmin = abs(2 * k + 1 - p);
        int32_t const lmax = 2 * k + 1 <= p ? 2 * (m - p + 2 * k + 1) + lmin : (2 * min(m, n - (2 * k + 1) + p) + lmin);
        if (lmin + 1 <= l && l < lmax)
        {
            int32_t const j        = k - (p + l) / 2 + l;
            int32_t const i        = l - j;
            nw_score_t const diag  = l - 2 < 0 ? max : scores(k, l - 2) + (query[i - 1] == target[j - 1] ? 0 : 1);
            nw_score_t const left  = l - 1 < 0 ? max : scores(k, l - 1) + 1;
            nw_score_t const above = l - 1 < 0 || k + 1 >= scores.num_rows() ? max : scores(k + 1, l - 1) + 1;
            scores(k, l)           = min3(diag, left, above);
        }
        k += blockDim.x;
    }
}

__device__ void ukkonen_compute_score_matrix_even(device_matrix_view<nw_score_t>& scores, int32_t kmax, int32_t k, int32_t m, int32_t n, char const* query, char const* target, int32_t max_target_query_length, int32_t p, int32_t l)
{
    CGA_CONSTEXPR nw_score_t max = numeric_limits<nw_score_t>::max() - 1;
    while (k < kmax)
    {
        int32_t const lmin = abs(2 * k - p);
        int32_t const lmax = 2 * k <= p ? 2 * (m - p + 2 * k) + lmin : (2 * min(m, n - 2 * k + p) + lmin);
        if (lmin + 1 <= l && l < lmax)
        {
            int32_t const j        = k - (p + l) / 2 + l;
            int32_t const i        = l - j;
            nw_score_t const left  = k - 1 < 0 || l - 1 < 0 ? max : scores(k - 1, l - 1) + 1;
            nw_score_t const diag  = l - 2 < 0 ? max : scores(k, l - 2) + (query[i - 1] == target[j - 1] ? 0 : 1);
            nw_score_t const above = l - 1 < 0 ? max : scores(k, l - 1) + 1;
            scores(k, l)           = min3(left, diag, above);
        }
        k += blockDim.x;
    }
}

__device__ void ukkonen_init_score_matrix(device_matrix_view<nw_score_t>& scores, int32_t k, int32_t p)
{
    CGA_CONSTEXPR nw_score_t max = numeric_limits<nw_score_t>::max() - 1;
    while (k < scores.num_rows())
    {
        for (int32_t l = 0; l < scores.num_cols(); ++l)
        {
            nw_score_t init_value = max;
            int32_t i, j;
            thrust::tie(i, j) = to_matrix_indices(k, l, p);

            if (i == 0)
                init_value = j;
            else if (j == 0)
                init_value = i;

            scores(k, l) = init_value;
        }
        k += blockDim.x;
    }
}

#ifndef NDEBUG
__launch_bounds__(CGA_UKKONEN_MAX_THREADS_PER_BLOCK) // Workaround for a register allocation problem when compiled with -g
#endif
    __global__ void ukkonen_compute_score_matrix(batched_device_matrices<nw_score_t>::device_interface* s, char const* sequences_d, int32_t const* sequence_lengths_d, int32_t max_target_query_length, int32_t p, int32_t max_cols)
{
    using thrust::swap;
    int32_t const k  = blockIdx.x * blockDim.x + threadIdx.x;
    int32_t const id = blockIdx.y * blockDim.y + threadIdx.y;

    int32_t m          = sequence_lengths_d[2 * id] + 1;
    int32_t n          = sequence_lengths_d[2 * id + 1] + 1;
    char const* query  = sequences_d + (2 * id) * max_target_query_length;
    char const* target = sequences_d + (2 * id + 1) * max_target_query_length;
    if (m > n)
    {
        swap(n, m);
        swap(query, target);
    }
    assert(p >= 0);
    int32_t const bw        = (1 + n - m + 2 * p + 1) / 2;
    int32_t const kmax_odd  = (n - m + 2 * p - 1) / 2 + 1;
    int32_t const kmax_even = (n - m + 2 * p) / 2 + 1;

    device_matrix_view<nw_score_t> scores = s->get_matrix_view(id, bw, n + m);
    ukkonen_init_score_matrix(scores, k, p);
    __syncthreads();
    if (p % 2 == 0)
    {
        for (int lx = 0; lx < 2 * max_cols; ++lx)
        {
            ukkonen_compute_score_matrix_even(scores, kmax_even, k, m, n, query, target, max_target_query_length, p, 2 * lx);
            __syncthreads();
            ukkonen_compute_score_matrix_odd(scores, kmax_odd, k, m, n, query, target, max_target_query_length, p, 2 * lx + 1);
            __syncthreads();
        }
    }
    else
    {
        for (int lx = 0; lx < 2 * max_cols; ++lx)
        {
            ukkonen_compute_score_matrix_odd(scores, kmax_odd, k, m, n, query, target, max_target_query_length, p, 2 * lx);
            __syncthreads();
            ukkonen_compute_score_matrix_even(scores, kmax_even, k, m, n, query, target, max_target_query_length, p, 2 * lx + 1);
            __syncthreads();
        }
    }
}

} // end namespace kernels

dim3 calc_blocks(dim3 const& n_threads, dim3 const& blocksize)
{
    dim3 r;
    r.x = (n_threads.x + blocksize.x - 1) / blocksize.x;
    r.y = (n_threads.y + blocksize.y - 1) / blocksize.y;
    r.z = (n_threads.z + blocksize.z - 1) / blocksize.z;
    return r;
}

constexpr int32_t calc_good_blockdim(int32_t n)
{
    constexpr int32_t warpsize = 32;
    int32_t i                  = n + (warpsize - n % warpsize);
    return i > CGA_UKKONEN_MAX_THREADS_PER_BLOCK ? CGA_UKKONEN_MAX_THREADS_PER_BLOCK : i;
}

void ukkonen_compute_score_matrix_gpu(batched_device_matrices<nw_score_t>& score_matrices, char const* sequences_d, int32_t const* sequence_lengths_d, int32_t max_length_difference, int32_t max_target_query_length, int32_t n_alignments, int32_t p, cudaStream_t stream)
{
    using kernels::ukkonen_compute_score_matrix;
    assert(p >= 0);
    assert(max_length_difference >= 0);
    assert(max_target_query_length >= 0);

    int32_t const max_bw   = (1 + max_length_difference + 2 * p + 1) / 2;
    int32_t const max_cols = 2 * (max_target_query_length + 1);

    // Transform to diagonal coordinates
    // (i,j) -> (k=(j-i+p)/2, l=(j+i))
    dim3 const compute_blockdims(calc_good_blockdim(max_bw), 1, 1);
    dim3 const blocks = dim3(1, n_alignments, 1);

    ukkonen_compute_score_matrix<<<blocks, compute_blockdims, 0, stream>>>(score_matrices.get_device_interface(), sequences_d, sequence_lengths_d, max_target_query_length, p, max_cols);
    CGA_CU_CHECK_ERR(cudaPeekAtLastError());
}

void ukkonen_backtrace_gpu(int8_t* paths_d, int32_t* path_lengths_d, int32_t max_path_length, batched_device_matrices<nw_score_t>& scores, int32_t const* sequence_lengths_d, int32_t n_alignments, int32_t p, cudaStream_t stream)
{
    kernels::ukkonen_backtrace_kernel<<<n_alignments, 1, 0, stream>>>(paths_d, path_lengths_d, max_path_length, scores.get_device_interface(), sequence_lengths_d, n_alignments, p);
    CGA_CU_CHECK_ERR(cudaPeekAtLastError());
}

void ukkonen_gpu(int8_t* paths_d, int32_t* path_lengths_d, int32_t max_path_length,
                 char const* sequences_d,
                 int32_t const* sequence_lengths_d,
                 int32_t max_length_difference,
                 int32_t max_target_query_length,
                 int32_t n_alignments,
                 batched_device_matrices<nw_score_t>* score_matrices,
                 int32_t ukkonen_p,
                 cudaStream_t stream)
{
    if (score_matrices == nullptr)
        return;

    ukkonen_compute_score_matrix_gpu(*score_matrices, sequences_d, sequence_lengths_d, max_length_difference, max_target_query_length, n_alignments, ukkonen_p, stream);
    ukkonen_backtrace_gpu(paths_d, path_lengths_d, max_path_length, *score_matrices, sequence_lengths_d, n_alignments, ukkonen_p, stream);
}

size_t ukkonen_max_score_matrix_size(int32_t max_query_length, int32_t max_target_length, int32_t max_length_difference, int32_t max_p)
{
    assert(max_target_length >= 0);
    assert(max_query_length >= 0);
    assert(max_p >= 0);
    assert(max_length_difference >= 0);
    size_t const max_target_query_length = std::max(max_target_length, max_query_length);
    size_t const n                       = max_target_query_length + 1;
    size_t const m                       = max_target_query_length + 1;
    size_t const bw                      = (1 + max_length_difference + 2 * max_p + 1) / 2;
    return bw * (n + m);
}

} // end namespace cudaaligner
} // end namespace claragenomics

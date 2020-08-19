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

#include <cuda_runtime_api.h>
#include "batched_device_matrices.cuh"

namespace claragenomics
{
namespace cudaaligner
{

namespace hirschbergmyers
{
using WordType   = uint32_t;
using nw_score_t = int32_t;

struct query_target_range
{
    char const* query_begin  = nullptr;
    char const* query_end    = nullptr;
    char const* target_begin = nullptr;
    char const* target_end   = nullptr;
};
} // namespace hirschbergmyers

void hirschberg_myers_gpu(device_buffer<hirschbergmyers::query_target_range>& stack_buffer,
                          int32_t stacksize_per_alignment,
                          int8_t* paths_d, int32_t* path_lengths_d, int32_t max_path_length,
                          char const* sequences_d,
                          int32_t const* sequence_lengths_d,
                          int32_t max_target_query_length,
                          int32_t n_alignments,
                          batched_device_matrices<hirschbergmyers::WordType>& pv,
                          batched_device_matrices<hirschbergmyers::WordType>& mv,
                          batched_device_matrices<int32_t>& score,
                          batched_device_matrices<hirschbergmyers::WordType>& query_patterns,
                          int32_t switch_to_myers_threshold,
                          cudaStream_t stream);

} // end namespace cudaaligner
} // end namespace claragenomics

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
#include <cstdint>

namespace claragenomics
{
namespace cudaaligner
{

using nw_score_t = int16_t;

template <typename T>
class batched_device_matrices;

size_t ukkonen_max_score_matrix_size(int32_t max_query_length, int32_t max_target_length, int32_t max_length_difference, int32_t max_p);

void ukkonen_compute_score_matrix_gpu(batched_device_matrices<nw_score_t>& score_matrices, char const* sequences_d, int32_t const* sequence_lengths_d, int32_t max_length_difference, int32_t max_target_query_length, int32_t n_alignments, int32_t p, cudaStream_t stream);

void ukkonen_gpu(int8_t* paths_d, int32_t* path_lengths_d, int32_t max_path_length,
                 char const* sequences_d, int32_t const* sequence_lengths_d,
                 int32_t max_length_difference,
                 int32_t max_target_query_length,
                 int32_t n_alignments,
                 batched_device_matrices<nw_score_t>* score_matrices,
                 int32_t ukkonen_p,
                 cudaStream_t stream);

} // end namespace cudaaligner
} // end namespace claragenomics

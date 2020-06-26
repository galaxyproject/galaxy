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
#include "batched_device_matrices.cuh"

#include <cuda_runtime_api.h>

namespace claragenomics
{
namespace cudaaligner
{

namespace myers
{
using WordType = uint32_t;
}

int32_t myers_compute_edit_distance(std::string const& target, std::string const& query);
matrix<int32_t> myers_get_full_score_matrix(std::string const& target, std::string const& query);

void myers_gpu(int8_t* paths_d, int32_t* path_lengths_d, int32_t max_path_length,
               char const* sequences_d,
               int32_t const* sequence_lengths_d,
               int32_t max_target_query_length,
               int32_t n_alignments,
               batched_device_matrices<myers::WordType>& pv,
               batched_device_matrices<myers::WordType>& mv,
               batched_device_matrices<int32_t>& score,
               batched_device_matrices<myers::WordType>& query_patterns,
               cudaStream_t stream);

} // end namespace cudaaligner
} // end namespace claragenomics

/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "aligner_global_ukkonen.hpp"
#include "ukkonen_gpu.cuh"
#include "batched_device_matrices.cuh"

namespace claragenomics
{

namespace cudaaligner
{

static constexpr float max_target_query_length_difference = 0.1; // query has to be >=90% of target length

AlignerGlobalUkkonen::AlignerGlobalUkkonen(int32_t max_query_length, int32_t max_target_length, int32_t max_alignments, cudaStream_t stream, int32_t device_id)
    : AlignerGlobal(max_query_length, max_target_length, max_alignments, stream, device_id)
    , score_matrices_()
    , ukkonen_p_(100)
{
    scoped_device_switch dev(device_id);
    int32_t const allocated_max_length_difference = this->get_max_target_length() * max_target_query_length_difference;
    score_matrices_                               = std::make_unique<batched_device_matrices<nw_score_t>>(
        max_alignments,
        ukkonen_max_score_matrix_size(this->get_max_query_length(), this->get_max_target_length(), allocated_max_length_difference, ukkonen_p_),
        stream);
}

AlignerGlobalUkkonen::~AlignerGlobalUkkonen()
{
    // Keep empty destructor to keep batched_device_matrices type incomplete in the .hpp file.
}

StatusType AlignerGlobalUkkonen::add_alignment(const char* query, int32_t query_length, const char* target, int32_t target_length)
{
    int32_t const allocated_max_length_difference = this->get_max_target_length() * max_target_query_length_difference;
    if (std::abs(query_length - target_length) > allocated_max_length_difference)
    {
        CGA_LOG_DEBUG("{} {}", "Exceeded maximum length difference b/w target and query allowed : ", allocated_max_length_difference);
        return StatusType::exceeded_max_alignment_difference;
    }

    return BaseType::add_alignment(query, query_length, target, target_length);
}

void AlignerGlobalUkkonen::run_alignment(int8_t* results_d, int32_t* result_lengths_d, int32_t max_result_length,
                                         const char* sequences_d, int32_t* sequence_lengths_d, int32_t* sequence_lengths_h, int32_t max_sequence_length,
                                         int32_t num_alignments, cudaStream_t stream)
{
    int32_t max_length_difference = 0;
    for (int32_t i = 0; i < num_alignments; ++i)
    {
        max_length_difference = std::max(max_length_difference,
                                         std::abs(sequence_lengths_h[2 * i] - sequence_lengths_h[2 * i + 1]));
    }

    ukkonen_gpu(results_d, result_lengths_d, max_result_length,
                sequences_d, sequence_lengths_d,
                max_length_difference, max_sequence_length, num_alignments,
                score_matrices_.get(),
                ukkonen_p_,
                stream);
}

} // namespace cudaaligner
} // namespace claragenomics

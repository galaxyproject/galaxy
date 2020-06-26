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

#include "aligner_global.hpp"
#include "ukkonen_gpu.cuh"

namespace claragenomics
{

namespace cudaaligner
{

template <typename T>
class batched_device_matrices;

class AlignerGlobalUkkonen : public AlignerGlobal
{
public:
    AlignerGlobalUkkonen(int32_t max_query_length, int32_t max_target_length, int32_t max_alignments, cudaStream_t stream, int32_t device_id);
    virtual ~AlignerGlobalUkkonen();
    StatusType add_alignment(const char* query, int32_t query_length, const char* target, int32_t target_length) override;

private:
    using BaseType = AlignerGlobal;

    virtual void run_alignment(int8_t* results_d, int32_t* result_lengths_d, int32_t max_result_length,
                               const char* sequences_d, int32_t* sequence_lengths_d, int32_t* sequence_lengths_h, int32_t max_sequence_length,
                               int32_t num_alignments, cudaStream_t stream) override;

    std::unique_ptr<batched_device_matrices<nw_score_t>> score_matrices_;
    int32_t ukkonen_p_;
};

} // namespace cudaaligner
} // namespace claragenomics

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

#include "ukkonen_gpu.cuh"

#include <claragenomics/cudaaligner/aligner.hpp>
#include <claragenomics/utils/signed_integer_utils.hpp>
#include <claragenomics/utils/device_buffer.cuh>

#include <thrust/system/cuda/experimental/pinned_allocator.h>

namespace claragenomics
{

namespace cudaaligner
{

class AlignerGlobal : public Aligner
{
public:
    AlignerGlobal(int32_t max_query_length, int32_t max_target_length, int32_t max_alignments, cudaStream_t stream, int32_t device_id);
    virtual ~AlignerGlobal()            = default;
    AlignerGlobal(const AlignerGlobal&) = delete;

    virtual StatusType align_all() override;

    virtual StatusType sync_alignments() override;

    virtual StatusType add_alignment(const char* query, int32_t query_length, const char* target, int32_t target_length) override;

    virtual const std::vector<std::shared_ptr<Alignment>>& get_alignments() const override
    {
        return alignments_;
    }

    virtual int32_t num_alignments() const
    {
        return get_size(alignments_);
    }

    virtual void reset() override;

    int32_t get_max_target_length() const
    {
        return max_target_length_;
    }

    int32_t get_max_query_length() const
    {
        return max_query_length_;
    }

private:
    template <typename T>
    using pinned_host_vector = std::vector<T, thrust::system::cuda::experimental::pinned_allocator<T>>;

    virtual void run_alignment(int8_t* results_d, int32_t* result_lengths, int32_t max_result_length, const char* sequences_d, int32_t* sequence_lengths_d, int32_t* sequence_lengths_h, int32_t max_sequence_length, int32_t num_alignments, cudaStream_t stream) = 0;

    int32_t max_query_length_;
    int32_t max_target_length_;
    int32_t max_alignments_;
    std::vector<std::shared_ptr<Alignment>> alignments_;

    device_buffer<char> sequences_d_;
    pinned_host_vector<char> sequences_h_;

    device_buffer<int32_t> sequence_lengths_d_;
    pinned_host_vector<int32_t> sequence_lengths_h_;

    device_buffer<int8_t> results_d_;
    pinned_host_vector<int8_t> results_h_;

    device_buffer<int32_t> result_lengths_d_;
    pinned_host_vector<int32_t> result_lengths_h_;

    cudaStream_t stream_;
    int32_t device_id_;
};

} // namespace cudaaligner
} // namespace claragenomics

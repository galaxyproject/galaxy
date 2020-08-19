/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "aligner_global.hpp"
#include "alignment_impl.hpp"

#include <claragenomics/utils/signed_integer_utils.hpp>
#include <claragenomics/utils/cudautils.hpp>
#include <claragenomics/utils/mathutils.hpp>
#include <claragenomics/logging/logging.hpp>

#include <cstring>
#include <algorithm>
#include <cuda_runtime_api.h>

namespace claragenomics
{

namespace cudaaligner
{

constexpr int32_t calc_max_result_length(int32_t max_query_length, int32_t max_target_length)
{
    constexpr int32_t alignment_bytes = 4;
    const int32_t max_length          = max_query_length + max_target_length;
    return ceiling_divide(max_length, alignment_bytes) * alignment_bytes;
}

AlignerGlobal::AlignerGlobal(int32_t max_query_length, int32_t max_target_length, int32_t max_alignments, cudaStream_t stream, int32_t device_id)
    : max_query_length_(throw_on_negative(max_query_length, "max_query_length must be non-negative."))
    , max_target_length_(throw_on_negative(max_target_length, "max_target_length must be non-negative."))
    , max_alignments_(throw_on_negative(max_alignments, "max_alignments must be non-negative."))
    , alignments_()
    , sequences_h_(2 * std::max(max_query_length, max_target_length) * max_alignments)
    , sequence_lengths_h_(2 * max_alignments)
    , results_h_(calc_max_result_length(max_query_length, max_target_length) * max_alignments)
    , result_lengths_h_(max_alignments)
    , stream_(stream)
    , device_id_(device_id)
{
    if (max_alignments < 1)
    {
        throw std::runtime_error("Max alignments must be at least 1.");
    }
    scoped_device_switch dev(device_id);
    sequences_d_        = device_buffer<char>(sequences_h_.size());
    sequence_lengths_d_ = device_buffer<int32_t>(sequence_lengths_h_.size());
    results_d_          = device_buffer<int8_t>(results_h_.size());
    result_lengths_d_   = device_buffer<int32_t>(result_lengths_h_.size());
    device_memset_async(sequences_d_, 0, stream);
    device_memset_async(sequence_lengths_d_, 0, stream);
    device_memset_async(results_d_, 0, stream);
    device_memset_async(result_lengths_d_, 0, stream);
}

StatusType AlignerGlobal::add_alignment(const char* query, int32_t query_length, const char* target, int32_t target_length)
{
    if (query_length < 0 || target_length < 0)
    {
        CGA_LOG_DEBUG("{} {}", "Negative target or query length is not allowed.");
        return StatusType::generic_error;
    }

    int32_t const max_alignment_length = std::max(max_query_length_, max_target_length_);
    int32_t const num_alignments       = get_size(alignments_);
    if (num_alignments >= max_alignments_)
    {
        CGA_LOG_DEBUG("{} {}", "Exceeded maximum number of alignments allowed : ", max_alignments_);
        return StatusType::exceeded_max_alignments;
    }

    if (query_length > max_query_length_)
    {
        CGA_LOG_DEBUG("{} {}", "Exceeded maximum length of query allowed : ", max_query_length_);
        return StatusType::exceeded_max_length;
    }

    if (target_length > max_target_length_)
    {
        CGA_LOG_DEBUG("{} {}", "Exceeded maximum length of target allowed : ", max_target_length_);
        return StatusType::exceeded_max_length;
    }

    memcpy(&sequences_h_[(2 * num_alignments) * max_alignment_length],
           query,
           sizeof(char) * query_length);
    memcpy(&sequences_h_[(2 * num_alignments + 1) * max_alignment_length],
           target,
           sizeof(char) * target_length);

    sequence_lengths_h_[2 * num_alignments]     = query_length;
    sequence_lengths_h_[2 * num_alignments + 1] = target_length;

    std::shared_ptr<AlignmentImpl> alignment = std::make_shared<AlignmentImpl>(query,
                                                                               query_length,
                                                                               target,
                                                                               target_length);
    alignment->set_alignment_type(AlignmentType::global_alignment);
    alignments_.push_back(alignment);

    return StatusType::success;
}

StatusType AlignerGlobal::align_all()
{
    scoped_device_switch dev(device_id_);
    const int32_t max_alignment_length = std::max(max_query_length_, max_target_length_);
    const int32_t num_alignments       = get_size(alignments_);
    const int32_t max_result_length    = calc_max_result_length(max_query_length_, max_target_length_);
    CGA_CU_CHECK_ERR(cudaMemcpyAsync(sequence_lengths_d_.data(),
                                     sequence_lengths_h_.data(),
                                     2 * sizeof(int32_t) * num_alignments,
                                     cudaMemcpyHostToDevice,
                                     stream_));
    CGA_CU_CHECK_ERR(cudaMemcpyAsync(sequences_d_.data(),
                                     sequences_h_.data(),
                                     2 * sizeof(char) * max_alignment_length * num_alignments,
                                     cudaMemcpyHostToDevice,
                                     stream_));

    // Run kernel
    run_alignment(results_d_.data(), result_lengths_d_.data(),
                  max_result_length, sequences_d_.data(), sequence_lengths_d_.data(), sequence_lengths_h_.data(),
                  max_alignment_length,
                  num_alignments,
                  stream_);

    CGA_CU_CHECK_ERR(cudaMemcpyAsync(results_h_.data(),
                                     results_d_.data(),
                                     sizeof(int8_t) * max_result_length * num_alignments,
                                     cudaMemcpyDeviceToHost,
                                     stream_));
    CGA_CU_CHECK_ERR(cudaMemcpyAsync(result_lengths_h_.data(),
                                     result_lengths_d_.data(),
                                     sizeof(int32_t) * num_alignments,
                                     cudaMemcpyDeviceToHost,
                                     stream_));
    return StatusType::success;
}

StatusType AlignerGlobal::sync_alignments()
{
    scoped_device_switch dev(device_id_);
    CGA_CU_CHECK_ERR(cudaStreamSynchronize(stream_));

    const int32_t n_alignments      = get_size(alignments_);
    const int32_t max_result_length = calc_max_result_length(max_query_length_, max_target_length_);
    std::vector<AlignmentState> al_state;
    for (int32_t i = 0; i < n_alignments; ++i)
    {
        al_state.clear();
        assert(result_lengths_h_[i] < max_result_length);
        const int8_t* r_begin = results_h_.data() + i * max_result_length;
        const int8_t* r_end   = r_begin + result_lengths_h_[i];
        std::transform(r_begin, r_end, std::back_inserter(al_state), [](int8_t x) { return static_cast<AlignmentState>(x); });
        std::reverse(begin(al_state), end(al_state));
        AlignmentImpl* alignment = dynamic_cast<AlignmentImpl*>(alignments_[i].get());
        alignment->set_alignment(al_state);
        alignment->set_status(StatusType::success);
    }
    return StatusType::success;
}

void AlignerGlobal::reset()
{
    alignments_.clear();
}
} // namespace cudaaligner
} // namespace claragenomics

/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "aligner_global_hirschberg_myers.hpp"
#include "hirschberg_myers_gpu.cuh"
#include "batched_device_matrices.cuh"

#include <claragenomics/utils/mathutils.hpp>

namespace claragenomics
{

namespace cudaaligner
{

static constexpr int32_t hirschberg_myers_stackbuffer_size     = 64;
static constexpr int32_t hirschberg_myers_switch_to_myers_size = 63; // ideally a value 16*n-1, since memory allocation will require one more element.

struct AlignerGlobalHirschbergMyers::Workspace
{
    Workspace(int32_t max_alignments, int32_t max_n_words, int32_t max_target_length, int32_t switch_to_myers_size, cudaStream_t stream)
        : stackbuffer(max_alignments * hirschberg_myers_stackbuffer_size)
        , pvs(max_alignments, max_n_words * (switch_to_myers_size + 1), stream)
        , mvs(max_alignments, max_n_words * (switch_to_myers_size + 1), stream)
        , scores(max_alignments, std::max(max_n_words * (switch_to_myers_size + 1), (max_target_length + 1) * 2), stream)
        , query_patterns(max_alignments, max_n_words * 8, stream)
    {
        assert(switch_to_myers_size >= 1);
    }
    device_buffer<hirschbergmyers::query_target_range> stackbuffer;
    batched_device_matrices<hirschbergmyers::WordType> pvs;
    batched_device_matrices<hirschbergmyers::WordType> mvs;
    batched_device_matrices<int32_t> scores;
    batched_device_matrices<hirschbergmyers::WordType> query_patterns;
};

AlignerGlobalHirschbergMyers::AlignerGlobalHirschbergMyers(int32_t max_query_length, int32_t max_target_length, int32_t max_alignments, cudaStream_t stream, int32_t device_id)
    : AlignerGlobal(max_query_length, max_target_length, max_alignments, stream, device_id)
{
    scoped_device_switch dev(device_id);
    workspace_ = std::make_unique<Workspace>(max_alignments, ceiling_divide<int32_t>(max_query_length, sizeof(hirschbergmyers::WordType)), max_target_length, hirschberg_myers_switch_to_myers_size, stream);
}

AlignerGlobalHirschbergMyers::~AlignerGlobalHirschbergMyers()
{
    // Keep empty destructor to keep Workspace type incomplete in the .hpp file.
}

void AlignerGlobalHirschbergMyers::run_alignment(int8_t* results_d, int32_t* result_lengths_d, int32_t max_result_length,
                                                 const char* sequences_d, int32_t* sequence_lengths_d, int32_t* sequence_lengths_h, int32_t max_sequence_length,
                                                 int32_t num_alignments, cudaStream_t stream)
{
    static_cast<void>(sequence_lengths_h);
    hirschberg_myers_gpu(workspace_->stackbuffer, hirschberg_myers_stackbuffer_size, results_d, result_lengths_d, max_result_length,
                         sequences_d, sequence_lengths_d, max_sequence_length, num_alignments,
                         workspace_->pvs, workspace_->mvs, workspace_->scores, workspace_->query_patterns,
                         hirschberg_myers_switch_to_myers_size,
                         stream);
}

} // namespace cudaaligner
} // namespace claragenomics

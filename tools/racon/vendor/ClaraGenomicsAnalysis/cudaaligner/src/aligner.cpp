/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <claragenomics/cudaaligner/aligner.hpp>

#include "aligner_global_hirschberg_myers.hpp"

namespace claragenomics
{

namespace cudaaligner
{

std::unique_ptr<Aligner> create_aligner(int32_t max_query_length, int32_t max_target_length, int32_t max_alignments, AlignmentType type, cudaStream_t stream, int32_t device_id)
{
    if (type == AlignmentType::global_alignment)
    {
        return std::make_unique<AlignerGlobalHirschbergMyers>(max_query_length, max_target_length, max_alignments, stream, device_id);
    }
    else
    {
        throw std::runtime_error("Aligner for specified type not implemented yet.");
    }
}
} // namespace cudaaligner
} // namespace claragenomics

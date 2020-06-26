/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <vector>

#include "claragenomics/cudamapper/types.hpp"

namespace claragenomics
{
namespace cudamapper
{

void fuse_overlaps(std::vector<Overlap>& fused_overlaps, const std::vector<Overlap>& unfused_overlaps)
{
    // If the target start position is greater than the target end position
    // We can safely assume that the query and target are template and complement
    // reads. TODO: Incorporate sketchelement direction value when this is implemented
    auto set_relative_strand = [](Overlap& o) {
        if (o.target_start_position_in_read_ > o.target_end_position_in_read_)
        {
            o.relative_strand                = RelativeStrand::Reverse;
            auto tmp                         = o.target_end_position_in_read_;
            o.target_end_position_in_read_   = o.target_start_position_in_read_;
            o.target_start_position_in_read_ = tmp;
        }
        else
        {
            o.relative_strand = RelativeStrand::Forward;
        }
    };

    if (unfused_overlaps.size() == 0)
    {
        return;
    }

    Overlap fused_overlap = unfused_overlaps[0];

    for (size_t i = 0; i < unfused_overlaps.size() - 1; i++)
    {
        const Overlap& next_overlap = unfused_overlaps[i + 1];
        if ((fused_overlap.target_read_id_ == next_overlap.target_read_id_) &&
            (fused_overlap.query_read_id_ == next_overlap.query_read_id_))
        {
            //need to fuse
            fused_overlap.num_residues_ += next_overlap.num_residues_;
            fused_overlap.query_end_position_in_read_  = next_overlap.query_end_position_in_read_;
            fused_overlap.target_end_position_in_read_ = next_overlap.target_end_position_in_read_;
        }
        else
        {
            set_relative_strand(fused_overlap);
            fused_overlaps.push_back(fused_overlap);
            fused_overlap = unfused_overlaps[i + 1];
        }
    }

    set_relative_strand(fused_overlap);
    fused_overlaps.push_back(fused_overlap);
}
} // namespace cudamapper
} // namespace claragenomics

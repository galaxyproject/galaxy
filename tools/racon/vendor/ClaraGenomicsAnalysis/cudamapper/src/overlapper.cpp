/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <algorithm>
#include <claragenomics/cudamapper/overlapper.hpp>

namespace claragenomics
{
namespace cudamapper
{

void Overlapper::filter_overlaps(std::vector<Overlap>& filtered_overlaps, const std::vector<Overlap>& overlaps, size_t min_residues, size_t min_overlap_len)
{
    auto valid_overlap = [&min_residues, &min_overlap_len](Overlap overlap) { return ((overlap.num_residues_ >= min_residues) &&
                                                                                      ((overlap.query_end_position_in_read_ - overlap.query_start_position_in_read_) > min_overlap_len)); };

    std::copy_if(overlaps.begin(), overlaps.end(),
                 std::back_inserter(filtered_overlaps),
                 valid_overlap);
}

void Overlapper::print_paf(const std::vector<Overlap>& overlaps)
{
    std::vector<Overlap> filtered_overlaps;
    filter_overlaps(filtered_overlaps, overlaps);

    for (const auto& overlap : filtered_overlaps)
    {
        // Add basic overlap information.
        std::printf("%s\t%i\t%i\t%i\t%c\t%s\t%i\t%i\t%i\t%i\t%i\t%i",
                    overlap.query_read_name_,
                    overlap.query_length_,
                    overlap.query_start_position_in_read_,
                    overlap.query_end_position_in_read_,
                    static_cast<unsigned char>(overlap.relative_strand),
                    overlap.target_read_name_,
                    overlap.target_length_,
                    overlap.target_start_position_in_read_,
                    overlap.target_end_position_in_read_,
                    overlap.num_residues_,
                    0,
                    255);
        // If CIGAR string is generated, output in PAF.
        if (overlap.cigar_ != 0)
        {
            std::printf("\tcg:Z:%s", overlap.cigar_);
        }
        // Add new line to demarcate new entry.
        std::printf("\n");
    }
}
} // namespace cudamapper
} // namespace claragenomics

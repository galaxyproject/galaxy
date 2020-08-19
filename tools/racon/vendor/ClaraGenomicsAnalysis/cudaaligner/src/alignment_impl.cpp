/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "alignment_impl.hpp"

#include <claragenomics/utils/signed_integer_utils.hpp>

namespace claragenomics
{

namespace cudaaligner
{

AlignmentImpl::AlignmentImpl(const char* query, int32_t query_length, const char* target, int32_t target_length)
    : query_(query, query + throw_on_negative(query_length, "query_length has to be non-negative."))
    , target_(target, target + throw_on_negative(target_length, "target_length has to be non-negative."))
    , status_(StatusType::uninitialized)
    , type_(AlignmentType::unset)
{
    // Initialize Alignment object.
}

char AlignmentImpl::alignment_state_to_cigar_state(AlignmentState s) const
{
    // CIGAR string format from http://bioinformatics.cvr.ac.uk/blog/tag/cigar-string/
    // Implementing a reduced set of CIGAR states, covering only the M, D and I characters.
    switch (s)
    {
    case AlignmentState::match:
    case AlignmentState::mismatch: return 'M';
    case AlignmentState::insertion: return 'I';
    case AlignmentState::deletion: return 'D';
    default: throw std::runtime_error("Unrecognized alignment state.");
    }
}

std::string AlignmentImpl::convert_to_cigar() const
{
    if (get_size(alignment_) < 1)
    {
        return std::string("");
    }

    std::string cigar        = "";
    char last_cigar_state    = alignment_state_to_cigar_state(alignment_[0]);
    int32_t count_last_state = 0;
    for (auto const& x : alignment_)
    {
        const char cur_cigar_state = alignment_state_to_cigar_state(x);
        if (cur_cigar_state == last_cigar_state)
        {
            count_last_state++;
        }
        else
        {
            cigar += std::to_string(count_last_state) + last_cigar_state;
            count_last_state = 1;
            last_cigar_state = cur_cigar_state;
        }
    }
    cigar += std::to_string(count_last_state) + last_cigar_state;
    return cigar;
}

FormattedAlignment AlignmentImpl::format_alignment() const
{
    int64_t t_pos = 0;
    int64_t q_pos = 0;
    std::string t_str;
    std::string q_str;
    for (auto const& x : alignment_)
    {
        switch (x)
        {
        case AlignmentState::match:
        case AlignmentState::mismatch:
            t_str += target_[t_pos++];
            q_str += query_[q_pos++];
            break;
        case AlignmentState::deletion:
            t_str += "-";
            q_str += query_[q_pos++];
            break;
        case AlignmentState::insertion:
            t_str += target_[t_pos++];
            q_str += "-";
            break;
        default:
            throw std::runtime_error("Unknown alignment state");
        }
    }

    return {q_str, t_str};
}
} // namespace cudaaligner
} // namespace claragenomics

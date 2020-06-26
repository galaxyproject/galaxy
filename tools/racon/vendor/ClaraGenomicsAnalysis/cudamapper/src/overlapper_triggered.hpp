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

#include <vector>

#include <claragenomics/cudamapper/types.hpp>
#include <claragenomics/cudamapper/overlapper.hpp>

namespace claragenomics
{
namespace cudamapper
{

/// OverlapperTriggered - generates overlaps and displays them on screen.
/// Uses a dynamic programming approach where an overlap is "triggered" when a run of
/// Anchors (e.g 3) with a score above a threshold is encountered and untriggerred
/// when a single anchor with a threshold below the value is encountered.
class OverlapperTriggered : public Overlapper
{

public:
    /// \brief finds all overlaps
    /// Uses a dynamic programming approach where an overlap is "triggered" when a run of
    /// Anchors (e.g 3) with a score above a threshold is encountered and untriggerred
    /// when a single anchor with a threshold below the value is encountered.
    /// \param overlaps Output vector into which generated overlaps will be placed
    /// \param anchors vector of anchors
    /// \param index_query Index
    /// \param index_target
    /// \return vector of Overlap objects
    void get_overlaps(std::vector<Overlap>& overlaps, thrust::device_vector<Anchor>& anchors, const Index& index_query, const Index& index_target) override;
};
} // namespace cudamapper
} // namespace claragenomics

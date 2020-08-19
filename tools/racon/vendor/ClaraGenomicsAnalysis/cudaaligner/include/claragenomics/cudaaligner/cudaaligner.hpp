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

#include <cstdint>

namespace claragenomics
{

namespace cudaaligner
{
/// \defgroup cudaaligner CUDA Aligner package
/// Base docs for the cudaaligner package (tbd)
/// \{

/// CUDA Aligner error type
enum StatusType
{
    success = 0,
    uninitialized,
    exceeded_max_alignments,
    exceeded_max_length,
    exceeded_max_alignment_difference,
    generic_error
};

/// AlignmentType - Enum for storing type of alignment.
enum AlignmentType
{
    global_alignment = 0,
    unset
};

/// AlignmentState - Enum for encoding each position in alignment.
enum AlignmentState : int8_t
{
    match = 0,
    mismatch,
    insertion, // Absent in query, present in target
    deletion   // Present in query, absent in target
};

/// Initialize CUDA Aligner context.
StatusType Init();
/// \}
} // namespace cudaaligner
} // namespace claragenomics

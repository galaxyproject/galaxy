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

/// \defgroup cudamapper CUDA mapper package
/// Base docs for the cudamapper package (tbd)
/// \{

namespace claragenomics
{
namespace cudamapper
{
enum class StatusType
{
    success = 0,
    generic_error
};

StatusType Init();
}; // namespace cudamapper
}; // namespace claragenomics

/// \}

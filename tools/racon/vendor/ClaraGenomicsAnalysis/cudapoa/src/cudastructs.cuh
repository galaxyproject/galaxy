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

namespace claragenomics
{

namespace cudapoa
{

template <typename SeqT>
struct SeqT4
{
    SeqT r0, r1, r2, r3;
};

template <typename ScoreT>
struct ScoreT4
{
    ScoreT s0, s1, s2, s3;
};

template <>
struct __align__(4) ScoreT4<int16_t>
{
    int16_t s0, s1, s2, s3;
};
} // namespace cudapoa
} // namespace claragenomics

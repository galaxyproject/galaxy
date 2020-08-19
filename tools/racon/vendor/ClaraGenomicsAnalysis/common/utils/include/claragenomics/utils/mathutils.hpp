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

#include <cassert>
#include <type_traits>
#include <cuda_runtime_api.h>
#ifndef __CUDA_ARCH__
#include <algorithm>
#endif

namespace claragenomics
{

template <typename Integer>
__host__ __device__ constexpr inline Integer ceiling_divide(Integer i, Integer j)
{
    static_assert(std::is_integral<Integer>::value, "Arguments have to be integer types.");
    assert(i >= 0);
    assert(j > 0);
    return (i + j - 1) / j;
}

template <typename T>
__host__ __device__ inline T const& min3(T const& t1, T const& t2, T const& t3)
{
#ifdef __CUDA_ARCH__
    return min(t1, min(t2, t3));
#else
    return std::min(t1, std::min(t2, t3));
#endif
}

} // namespace claragenomics

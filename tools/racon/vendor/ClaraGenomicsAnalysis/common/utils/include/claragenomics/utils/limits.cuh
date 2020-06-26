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

#include <claragenomics/utils/cudaversions.hpp>
#include <limits>
#include <cstdint>

namespace claragenomics
{
#ifdef CGA_CUDA_BEFORE_10_1
template <typename T>
struct numeric_limits
{
};

template <>
struct numeric_limits<int16_t>
{
    CGA_CONSTEXPR static __device__ int16_t max() { return INT16_MAX; }
};

template <>
struct numeric_limits<int32_t>
{
    CGA_CONSTEXPR static __device__ int32_t max() { return INT32_MAX; }
};
#else
using std::numeric_limits;
#endif

} // end namespace claragenomics

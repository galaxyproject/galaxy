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
/// \def CGA_CUDA_BEFORE_XX_X
/// \brief Macros to enable/disable CUDA version specific code
#define CGA_CUDA_BEFORE_XX_X 1

#if __CUDACC_VER_MAJOR__ < 10 || (__CUDACC_VER_MAJOR__ == 10 && __CUDACC_VER_MINOR__ < 1)
#define CGA_CUDA_BEFORE_10_1
#endif

#if (__CUDACC_VER_MAJOR__ == 9 && __CUDACC_VER_MINOR__ < 2)
#define CGA_CUDA_BEFORE_9_2
#endif

/// \def CGA_CONSTEXPR
/// \brief C++ constexpr for device code - falls back to const for CUDA 10.0 and earlier
#ifdef CGA_CUDA_BEFORE_10_1
#define CGA_CONSTEXPR const
#else
#define CGA_CONSTEXPR constexpr
#endif

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

#include <string>
#include <stdint.h>

namespace claragenomics
{

namespace stringutils
{

// utility function to convert an array of node ids into a readable string representation
template <class T>
inline std::string array_to_string(T* arr, size_t len, std::string delim = "-")
{
    std::string res;
    for (size_t i = 0; i < len; i++)
    {
        res += std::to_string(arr[i]) + (i == len - 1 ? "" : delim);
    }
    return res;
}

} //namespace stringutils

} // namespace claragenomics

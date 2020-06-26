/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <cctype>
#include "bioparser_sequence.hpp"

namespace claragenomics
{

namespace cudamapper
{
BioParserSequence::BioParserSequence(const char* name, uint32_t name_length, const char* data,
                                     uint32_t data_length)
    : name_(name, name_length)
    , data_()
{

    data_.reserve(data_length);
    for (uint32_t i = 0; i < data_length; ++i)
    {
        data_ += std::toupper(data[i]);
    }
}
} // namespace cudamapper

} // namespace claragenomics

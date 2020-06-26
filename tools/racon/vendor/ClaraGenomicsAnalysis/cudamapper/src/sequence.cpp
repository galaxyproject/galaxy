/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <claragenomics/cudamapper/sequence.hpp>
#include "bioparser_sequence.hpp"

namespace claragenomics
{
namespace cudamapper
{
std::unique_ptr<Sequence> Sequence::create_sequence(const char* name, uint32_t name_length, const char* data,
                                                    uint32_t data_length)
{
    return std::make_unique<BioParserSequence>(name, name_length, data, data_length);
}

std::unique_ptr<Sequence> Sequence::create_sequence(const std::string& name, const std::string& data)
{
    return std::make_unique<BioParserSequence>(name.c_str(), name.size(), data.c_str(), data.size());
}

} // namespace cudamapper
} // namespace claragenomics

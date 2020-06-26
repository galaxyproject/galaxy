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

#include <memory>
#include <string>
#include "claragenomics/cudamapper/sequence.hpp"

namespace claragenomics
{
namespace cudamapper
{
///BioParserSequence - represents sequence. Compatible with BioParser's FastaParser
class BioParserSequence : public Sequence
{
public:
    ~BioParserSequence() = default;

    /// returns sequence read name.
    /// \return `name_` private variable
    const std::string& name() const
    {
        return name_;
    }

    /// returns sequence read data. Typically DNA bases
    /// \return `data_` private variable
    const std::string& data() const
    {
        return data_;
    }

    /// \brief BioParserSequence constructor - constructs a Sequence implementation compatible with bioparser's
    /// FastaParser
    ///
    /// \param name sequence name
    /// \param name_length length of name
    /// \param data DNA bases (typically sequence of characters from set A,C,T,G)
    /// \param data_length sequence length
    BioParserSequence(const char* name, uint32_t name_length, const char* data,
                      uint32_t data_length);

private:
    std::string name_;
    std::string data_;
};
} // namespace cudamapper
} // namespace claragenomics

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

namespace claragenomics
{

namespace cudamapper
{
/// \addtogroup cudamapper
/// \{

/// Sequence - represents an individual read (name, DNA nucleotides etc)
class Sequence
{
public:
    /// \brief Virtual destructor for Sequence
    virtual ~Sequence() = default;

    /// Sequence name
    virtual const std::string& name() const = 0;

    /// Sequence data. Typically this is a sequence of bases A,C,T,G
    virtual const std::string& data() const = 0;

    /// create_sequence - return a Sequence object
    /// \return Sequence implementation
    static std::unique_ptr<Sequence> create_sequence(const char* name, uint32_t name_length, const char* data,
                                                     uint32_t data_length);

    /// create_sequence - return a Sequence object
    /// \return Sequence implementation
    static std::unique_ptr<Sequence> create_sequence(const std::string& name, const std::string& data);
};

/// \}
} // namespace cudamapper

} // namespace claragenomics

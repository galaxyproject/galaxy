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

#include <cstdint>
#include <memory>
#include <claragenomics/cudamapper/types.hpp>

namespace claragenomics
{

namespace cudamapper
{
/// \addtogroup cudamapper
/// \{

/// SketchElement - Contains integer representation, position, direction and read id of a kmer
class SketchElement
{
public:
    /// \brief Is this a representation of forward or reverse compliment
    enum class DirectionOfRepresentation
    {
        FORWARD,
        REVERSE
    };

    /// \brief Virtual destructor for SketchElement
    virtual ~SketchElement() = default;

    /// \brief returns integer representation of a kmer
    /// \return integer representation
    virtual representation_t representation() const = 0;

    /// \brief returns position of the sketch in the read
    /// \return position of the sketch in the read
    virtual position_in_read_t position_in_read() const = 0;

    /// \brief returns representation's direction
    /// \return representation's direction
    virtual DirectionOfRepresentation direction() const = 0;

    /// \brief returns read ID
    /// \return read ID
    virtual read_id_t read_id() const = 0;
};

/// \}

} // namespace cudamapper

} // namespace claragenomics

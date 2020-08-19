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

#include <claragenomics/cudaaligner/cudaaligner.hpp>

#include <memory>
#include <vector>
#include <string>

namespace claragenomics
{

namespace cudaaligner
{
/// \addtogroup cudaaligner
/// \{

/// \typedef FormattedAlignment
/// Holds formatted strings representing an alignment.
/// FormattedAlignment.first = formatted string for query
/// FormattedAlignment.second = formatted string for target
typedef std::pair<std::string, std::string> FormattedAlignment;

/// Alignment - Object encapsulating an alignment between 2 string.
class Alignment
{
public:
    /// \brief Virtual destructor
    virtual ~Alignment() = default;

    /// \brief Returns query sequence
    virtual const std::string& get_query_sequence() const = 0;

    /// \brief Returns target sequence
    virtual const std::string& get_target_sequence() const = 0;

    /// \brief Converts an alignment to CIGAR format.
    ///        The is a reduced implementation of the CIGAR standard
    ///        supporting only M, I and D states.
    ///
    /// \return CIGAR string
    virtual std::string convert_to_cigar() const = 0;

    /// \brief Returns type of alignment
    ///
    /// \return Type of alignment
    virtual AlignmentType get_alignment_type() const = 0;

    /// \brief Return status of alignment
    ///
    /// \return Status of alignment
    virtual StatusType get_status() const = 0;

    /// \brief Get the alignment between sequences
    ///
    /// \return Vector of AlignmentState encoding sequence of match,
    ///         mistmatch and insertions in alignment.
    virtual const std::vector<AlignmentState>& get_alignment() const = 0;

    /// \brief Print formatted alignment to stderr.
    virtual FormattedAlignment format_alignment() const = 0;
};

/// \}
} // namespace cudaaligner
} // namespace claragenomics

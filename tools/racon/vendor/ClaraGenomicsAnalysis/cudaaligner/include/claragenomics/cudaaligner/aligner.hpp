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
#include <cuda_runtime_api.h>

namespace claragenomics
{

namespace cudaaligner
{

// Forward declaration of Alignment class.
class Alignment;

/// \addtogroup cudaaligner
/// \{

/// \class Aligner
/// CUDA Alignment object
class Aligner
{
public:
    /// \brief Virtual destructor for Aligner.
    virtual ~Aligner() = default;

    /// \brief Launch CUDA accelerated alignment
    ///
    /// Perform alignment on all Alignment objects previously
    /// inserted. This is an async call, and returns before alignment
    /// is fully finished. To sync the alignments, refer to the
    /// sync_alignments() call;
    /// To
    virtual StatusType align_all() = 0;

    /// \brief Waits for CUDA accelerated alignment to finish
    ///
    /// Blocking call that waits for all the alignments scheduled
    /// on the GPU to come to completion.
    virtual StatusType sync_alignments() = 0;

    /// \brief Add new alignment object. Only strings with characters
    ///        from the alphabet [ACGT] are guaranteed to provide correct results.
    ///
    /// \param query Query string
    /// \param query_length  Query string length
    /// \param target Target string
    /// \param target_length Target string length
    virtual StatusType add_alignment(const char* query, int32_t query_length, const char* target, int32_t target_length) = 0;

    /// \brief Return the computed alignments.
    ///
    /// \return Vector of Alignments.
    virtual const std::vector<std::shared_ptr<Alignment>>& get_alignments() const = 0;

    /// \brief Reset aligner object.
    virtual void reset() = 0;
};

/// \brief Created Aligner object
///
/// \param max_query_length Maximum length of query string
/// \param max_target_length Maximum length of target string
/// \param max_alignments Maximum number of alignments to be performed
/// \param type Type of aligner to construct
/// \param stream CUDA Stream used for GPU interaction of the object
/// \param device_id GPU device ID to run all CUDA operations on
///
/// \return Unique pointer to Aligner object
std::unique_ptr<Aligner> create_aligner(int32_t max_query_length, int32_t max_target_length, int32_t max_alignments, AlignmentType type, cudaStream_t stream, int32_t device_id);

/// \}
} // namespace cudaaligner
} // namespace claragenomics

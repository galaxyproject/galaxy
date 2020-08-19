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
#include <vector>
#include <claragenomics/cudamapper/sketch_element.hpp>
#include <claragenomics/cudamapper/types.hpp>
#include <claragenomics/io/fasta_parser.hpp>

#include <thrust/device_vector.h>

namespace claragenomics
{

namespace cudamapper
{
/// \addtogroup cudamapper
/// \{

/// Index - manages mapping of (k,w)-kmer-representation and all its occurences
class Index
{
public:
    /// \brief Virtual destructor
    virtual ~Index() = default;

    /// \brief returns an array of representations of sketch elements
    /// \return an array of representations of sketch elements
    virtual const thrust::device_vector<representation_t>& representations() const = 0;

    /// \brief returns an array of reads ids for sketch elements
    /// \return an array of reads ids for sketch elements
    virtual const thrust::device_vector<read_id_t>& read_ids() const = 0;

    /// \brief returns an array of starting positions of sketch elements in their reads
    /// \return an array of starting positions of sketch elements in their reads
    virtual const thrust::device_vector<position_in_read_t>& positions_in_reads() const = 0;

    /// \brief returns an array of directions in which sketch elements were read
    /// \return an array of directions in which sketch elements were read
    virtual const thrust::device_vector<SketchElement::DirectionOfRepresentation>& directions_of_reads() const = 0;

    /// \brief returns read name of read with the given read_id
    /// \param read_id
    /// \return read name of read with the given read_id
    virtual const std::string& read_id_to_read_name(const read_id_t read_id) const = 0;

    /// \brief returns an array where each representation is recorder only once, sorted by representation
    /// \return an array where each representation is recorder only once, sorted by representation
    virtual const thrust::device_vector<representation_t>& unique_representations() const = 0;

    /// \brief returns first occurrence of corresponding representation from unique_representations() in data arrays
    /// \return first occurrence of corresponding representation from unique_representations() in data arrays
    virtual const thrust::device_vector<std::uint32_t>& first_occurrence_of_representations() const = 0;

    /// \brief returns read length for the read with the gived read_id
    /// \param read_id
    /// \return read length for the read with the gived read_id
    virtual const std::uint32_t& read_id_to_read_length(const read_id_t read_id) const = 0;

    /// \brief returns number of reads in input data
    /// \return number of reads in input data
    virtual std::uint64_t number_of_reads() const = 0;

    /// \brief Return the maximum kmer length allowable
    /// \return Return the maximum kmer length allowable
    static uint64_t maximum_kmer_size()
    {
        return sizeof(representation_t) * 8 / 2;
    }

    /// \brief generates a mapping of (k,w)-kmer-representation to all of its occurrences for one or more sequences
    /// \param parser parser for the whole input file (part that goes into this index is determined by first_read_id and past_the_last_read_id)
    /// \param first_read_id read_id of the first read to the included in this index
    /// \param past_the_last_read_id read_id+1 of the last read to be included in this index
    /// \param kmer_size k - the kmer length
    /// \param window_size w - the length of the sliding window used to find sketch elements  (i.e. the number of adjacent kmers in a window, adjacent = shifted by one basepair)
    /// \param hash_representations - if true, hash kmer representations
    /// \return instance of Index
    static std::unique_ptr<Index>
    create_index(const io::FastaParser& parser,
                 const read_id_t first_read_id,
                 const read_id_t past_the_last_read_id,
                 const std::uint64_t kmer_size,
                 const std::uint64_t window_size,
                 const bool hash_representations = true);
};

/// \}

} // namespace cudamapper

} // namespace claragenomics

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
#include <vector>
#include <claragenomics/cudamapper/sketch_element.hpp>
#include <claragenomics/cudamapper/types.hpp>

#include <claragenomics/utils/device_buffer.cuh>

namespace claragenomics
{
namespace cudamapper
{

/// Minimizer - represents one occurrance of a minimizer
class Minimizer : public SketchElement
{
public:
    /// \brief constructor
    ///
    /// \param representation 2-bit packed representation of a kmer
    /// \param position position of the minimizer in the read
    /// \param direction in which the read was read (forward or reverse complimet)
    /// \param read_id read's id
    Minimizer(representation_t representation, position_in_read_t position_in_read, DirectionOfRepresentation direction, read_id_t read_id);

    /// \brief returns minimizers representation
    /// \return minimizer representation
    representation_t representation() const override;

    /// \brief returns position of the minimizer in the sequence
    /// \return position of the minimizer in the sequence
    position_in_read_t position_in_read() const override;

    /// \brief returns representation's direction
    /// \return representation's direction
    DirectionOfRepresentation direction() const override;

    /// \brief returns read ID
    /// \return read ID
    read_id_t read_id() const override;

    /// \brief read_id, position_in_read and direction of a minimizer
    struct ReadidPositionDirection
    {
        // read id
        read_id_t read_id_;
        // position in read
        position_in_read_t position_in_read_;
        // direction
        char direction_;
    };

    // TODO: this will be replaced with Minimizer
    /// \brief a collection of sketch element
    struct GeneratedSketchElements
    {
        // representations of sketch elements
        device_buffer<representation_t> representations_d;
        // read_ids, positions_in_reads and directions of sketch elements. Each element from this data structure corresponds to the element with the same index from representations_d
        device_buffer<ReadidPositionDirection> rest_d;
    };

    /// \brief generates sketch elements from the given input
    ///
    /// \param number_of_reads_to_add number of reads which should be added to the collection (= number of reads in the data that is passed to the function)
    /// \param minimizer_size
    /// \param window_size
    /// \param read_id_of_first_read read_id numbering in the output should should be offset by this value
    /// \param merged_basepairs_d basepairs of all reads, gouped by reads (device memory)
    /// \param read_id_to_basepairs_section_h for each read_id points to the section of merged_basepairs_d that belong to that read_id (host memory)
    /// \param read_id_to_basepairs_section_h for each read_id points to the section of merged_basepairs_d that belong to that read_id (device memory)
    /// \param hash_minimizers if true, apply a hash function to the representations
    static GeneratedSketchElements generate_sketch_elements(const std::uint64_t number_of_reads_to_add,
                                                            const std::uint64_t minimizer_size,
                                                            const std::uint64_t window_size,
                                                            const std::uint64_t read_id_of_first_read,
                                                            const device_buffer<char>& merged_basepairs_d,
                                                            const std::vector<ArrayBlock>& read_id_to_basepairs_section_h,
                                                            const device_buffer<ArrayBlock>& read_id_to_basepairs_section_d,
                                                            const bool hash_representations = true);

private:
    representation_t representation_;
    position_in_read_t position_in_read_;
    DirectionOfRepresentation direction_;
    read_id_t read_id_;
};

} // namespace cudamapper
} // namespace claragenomics

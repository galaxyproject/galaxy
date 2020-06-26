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

#include <vector>

#include <thrust/copy.h>
#include <thrust/device_vector.h>
#include <thrust/host_vector.h>

#include <claragenomics/cudamapper/index.hpp>
#include <claragenomics/cudamapper/types.hpp>
#include <claragenomics/io/fasta_parser.hpp>
#include <claragenomics/logging/logging.hpp>
#include <claragenomics/utils/device_buffer.cuh>
#include <claragenomics/utils/mathutils.hpp>

namespace claragenomics
{
namespace cudamapper
{
/// IndexGPU - Contains sketch elements grouped by representation and by read id within the representation
///
/// Sketch elements are separated in four data arrays: representations, read_ids, positions_in_reads and directions_of_reads.
/// Elements of these four arrays with the same index represent one sketch element
/// (representation, read_id of the read it belongs to, position in that read of the first basepair of sketch element and whether it is
/// forward or reverse complement representation).
///
/// Elements of data arrays are grouped by sketch element representation and within those groups by read_id. Both representations and read_ids within
/// representations are sorted in ascending order
///
/// In addition to this the class contains an array where each representation is recorder only once (unique_representations) sorted by representation
/// and an array in which the index of first occurrence of that representation is recorded
///
/// \tparam SketchElementImpl any implementation of SketchElement
template <typename SketchElementImpl>
class IndexGPU : public Index
{
public:
    /// \brief Constructor
    ///
    /// \param parser parser for the whole input file (part that goes into this index is determined by first_read_id and past_the_last_read_id)
    /// \param first_read_id read_id of the first read to the included in this index
    /// \param past_the_last_read_id read_id+1 of the last read to be included in this index
    /// \param kmer_size k - the kmer length
    /// \param window_size w - the length of the sliding window used to find sketch elements (i.e. the number of adjacent k-mers in a window, adjacent = shifted by one basepair)
    /// \param hash_representations - if true, hash kmer representations
    IndexGPU(const io::FastaParser& parser,
             const read_id_t first_read_id,
             const read_id_t past_the_last_read_id,
             const std::uint64_t kmer_size,
             const std::uint64_t window_size,
             const bool hash_representations = true);

    /// \brief returns an array of representations of sketch elements
    /// \return an array of representations of sketch elements
    const thrust::device_vector<representation_t>& representations() const override;

    /// \brief returns an array of reads ids for sketch elements
    /// \return an array of reads ids for sketch elements
    const thrust::device_vector<read_id_t>& read_ids() const override;

    /// \brief returns an array of starting positions of sketch elements in their reads
    /// \return an array of starting positions of sketch elements in their reads
    const thrust::device_vector<position_in_read_t>& positions_in_reads() const override;

    /// \brief returns an array of directions in which sketch elements were read
    /// \return an array of directions in which sketch elements were read
    const thrust::device_vector<typename SketchElementImpl::DirectionOfRepresentation>& directions_of_reads() const override;

    /// \brief returns an array where each representation is recorder only once, sorted by representation
    /// \return an array where each representation is recorder only once, sorted by representation
    const thrust::device_vector<representation_t>& unique_representations() const override;

    /// \brief returns first occurrence of corresponding representation from unique_representations() in data arrays
    /// \return first occurrence of corresponding representation from unique_representations() in data arrays
    const thrust::device_vector<std::uint32_t>& first_occurrence_of_representations() const override;

    /// \brief returns read name of read with the given read_id
    /// \param read_id
    /// \return read name of read with the given read_id
    const std::string& read_id_to_read_name(const read_id_t read_id) const override;

    /// \brief returns read length for the read with the gived read_id
    /// \param read_id
    /// \return read length for the read with the gived read_id
    const std::uint32_t& read_id_to_read_length(const read_id_t read_id) const override;

    /// \brief returns number of reads in input data
    /// \return number of reads in input data
    std::uint64_t number_of_reads() const override;

private:
    /// \brief generates the index
    void generate_index(const io::FastaParser& query_parser,
                        const read_id_t first_read_id,
                        const read_id_t past_the_last_read_id,
                        const bool hash_representations);

    thrust::device_vector<representation_t> representations_d_;
    thrust::device_vector<read_id_t> read_ids_d_;
    thrust::device_vector<position_in_read_t> positions_in_reads_d_;
    thrust::device_vector<typename SketchElementImpl::DirectionOfRepresentation> directions_of_reads_d_;

    thrust::device_vector<representation_t> unique_representations_d_;
    thrust::device_vector<std::uint32_t> first_occurrence_of_representations_d_;

    std::vector<std::string> read_id_to_read_name_;
    std::vector<std::uint32_t> read_id_to_read_length_;

    const read_id_t first_read_id_ = 0;
    // number of basepairs in a k-mer
    const std::uint64_t kmer_size_ = 0;
    // the number of adjacent k-mers in a window, adjacent = shifted by one basepair
    const std::uint64_t window_size_ = 0;
    std::uint64_t number_of_reads_   = 0;
};

namespace details
{
namespace index_gpu
{
/// \brief Creates compressed representation of index
///
/// Creates two arrays: first one contains a list of unique representations and the second one the index
/// at which that representation occurrs for the first time in the original data.
/// Second element contains one additional elemet at the end, containing the total number of elemets in the original array.
///
/// For example:
/// 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20
/// 0  0  0  0 12 12 12 12 12 12 23 23 23 32 32 32 32 32 46 46 46
/// ^           ^                 ^        ^              ^       ^
/// gives:
/// 0 12 23 32 46
/// 0  4 10 13 18 21
///
/// \param unique_representations_d empty on input, contains one value of each representation on the output
/// \param first_occurrence_index_d empty on input, index of first occurrence of each representation and additional elemnt on the output
/// \param input_representations_d an array of representaton where representations with the same value stand next to each other
void find_first_occurrences_of_representations(thrust::device_vector<representation_t>& unique_representations_d,
                                               thrust::device_vector<std::uint32_t>& first_occurrence_index_d,
                                               const thrust::device_vector<representation_t>& input_representations_d);

/// \brief Writes 0 to the output array if the value to the left is the same as the current value, 1 otherwise. First element is always 1
///
/// For example:
/// 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20
/// 0  0  0  0 12 12 12 12 12 12 23 23 23 32 32 32 32 32 46 46 46
/// gives:
/// 1  0  0  0  1  0  0  0  0  0  1  0  0  1  0  0  0  0  1  0  0
///
/// \param representations_d
/// \param number_of_elements
/// \param new_value_mask_d generated array
__global__ void create_new_value_mask(const representation_t* const representations_d,
                                      const std::size_t number_of_elements,
                                      std::uint32_t* const new_value_mask_d);

/// \brief Helper kernel for find_first_occurrences_of_representations
///
/// Creates two arrays: first one contains a list of unique representations and the second one the index
/// at which that representation occurrs for the first time in the original data.
///
/// For example:
/// 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20
/// 0  0  0  0 12 12 12 12 12 12 23 23 23 32 32 32 32 32 46 46 46
/// 1  0  0  0  1  0  0  0  0  0  1  0  0  1  0  0  0  0  1  0  0
/// 1  1  1  1  2  2  2  2  2  2  3  3  3  4  4  4  4  4  5  5  5
/// ^           ^                 ^        ^              ^
/// gives:
/// 0 12 23 32 46
/// 0  4 10 13 18
///
/// \param representation_index_mask_d an array in which each element from input_representatons_d is mapped to an ordinal number of that representation (array "1  1  1  1  2  2  2  2  2  2  3  3  3  4  4  4  4  4  5  5  5" in the example)
/// \param input_representatons_d all representations (array "0  0  0  0 12 12 12 12 12 12 23 23 23 32 32 32 32 32 46 46 46" in the example)
/// \param number_of_input_elements number of elements in input_representatons_d and representation_index_mask_d
/// \param starting_index_of_each_representation_d index with first occurrence of each representation (array "0 12 23 32 46" in the example)
/// \param unique_representations_d representation that corresponds to each element in starting_index_of_each_representation_d (array "0  4 10 13 18" in the example)
__global__ void find_first_occurrences_of_representations_kernel(const std::uint64_t* const representation_index_mask_d,
                                                                 const representation_t* const input_representations_d,
                                                                 const std::size_t number_of_input_elements,
                                                                 std::uint32_t* const starting_index_of_each_representation_d,
                                                                 representation_t* const unique_representations_d);

/// \brief Splits array of structs into one array per struct element
///
/// \param rest_d original struct
/// \param positions_in_reads_d output array
/// \param read_ids_d output array
/// \param directions_of_reads_d output array
/// \param total_elements number of elements in each array
///
/// \tparam ReadidPositionDirection any implementation of SketchElementImpl::ReadidPositionDirection
/// \tparam DirectionOfRepresentation any implementation of SketchElementImpl::SketchElementImpl::DirectionOfRepresentation
template <typename ReadidPositionDirection, typename DirectionOfRepresentation>
__global__ void copy_rest_to_separate_arrays(const ReadidPositionDirection* const rest_d,
                                             read_id_t* const read_ids_d,
                                             position_in_read_t* const positions_in_reads_d,
                                             DirectionOfRepresentation* const directions_of_reads_d,
                                             const std::size_t total_elements)
{
    auto i = blockIdx.x * blockDim.x + threadIdx.x;

    if (i >= total_elements)
        return;

    read_ids_d[i]            = rest_d[i].read_id_;
    positions_in_reads_d[i]  = rest_d[i].position_in_read_;
    directions_of_reads_d[i] = DirectionOfRepresentation(rest_d[i].direction_);
}

} // namespace index_gpu
} // namespace details

template <typename SketchElementImpl>
IndexGPU<SketchElementImpl>::IndexGPU(const io::FastaParser& parser,
                                      const read_id_t first_read_id,
                                      const read_id_t past_the_last_read_id,
                                      const std::uint64_t kmer_size,
                                      const std::uint64_t window_size,
                                      const bool hash_representations)
    : first_read_id_(first_read_id)
    , kmer_size_(kmer_size)
    , window_size_(window_size)
    , number_of_reads_(0)
{
    generate_index(parser,
                   first_read_id_,
                   past_the_last_read_id,
                   hash_representations);
}

template <typename SketchElementImpl>
const thrust::device_vector<representation_t>& IndexGPU<SketchElementImpl>::representations() const
{
    return representations_d_;
};

template <typename SketchElementImpl>
const thrust::device_vector<read_id_t>& IndexGPU<SketchElementImpl>::read_ids() const
{
    return read_ids_d_;
}

template <typename SketchElementImpl>
const thrust::device_vector<position_in_read_t>& IndexGPU<SketchElementImpl>::positions_in_reads() const
{
    return positions_in_reads_d_;
}

template <typename SketchElementImpl>
const thrust::device_vector<typename SketchElementImpl::DirectionOfRepresentation>& IndexGPU<SketchElementImpl>::directions_of_reads() const
{
    return directions_of_reads_d_;
}

template <typename SketchElementImpl>
const thrust::device_vector<representation_t>& IndexGPU<SketchElementImpl>::unique_representations() const
{
    return unique_representations_d_;
}

template <typename SketchElementImpl>
const thrust::device_vector<std::uint32_t>& IndexGPU<SketchElementImpl>::first_occurrence_of_representations() const
{
    return first_occurrence_of_representations_d_;
}

template <typename SketchElementImpl>
const std::string& IndexGPU<SketchElementImpl>::read_id_to_read_name(const read_id_t read_id) const
{
    return read_id_to_read_name_[read_id - first_read_id_];
}

template <typename SketchElementImpl>
const std::uint32_t& IndexGPU<SketchElementImpl>::read_id_to_read_length(const read_id_t read_id) const
{
    return read_id_to_read_length_[read_id - first_read_id_];
}

template <typename SketchElementImpl>
std::uint64_t IndexGPU<SketchElementImpl>::number_of_reads() const
{
    return number_of_reads_;
}

template <typename SketchElementImpl>
void IndexGPU<SketchElementImpl>::generate_index(const io::FastaParser& parser,
                                                 const read_id_t first_read_id,
                                                 const read_id_t past_the_last_read_id,
                                                 const bool hash_representations)
{

    // check if there are any reads to process
    if (first_read_id >= past_the_last_read_id)
    {
        CGA_LOG_INFO("No Sketch Elements to be added to index");
        number_of_reads_ = 0;
        return;
    }

    number_of_reads_ = past_the_last_read_id - first_read_id;

    std::uint64_t total_basepairs = 0;
    std::vector<ArrayBlock> read_id_to_basepairs_section_h;
    std::vector<io::FastaSequence> fasta_reads;

    // deterine the number of basepairs in each read and assign read_id to each read
    for (read_id_t read_id = first_read_id; read_id < past_the_last_read_id; ++read_id)
    {
        fasta_reads.emplace_back(parser.get_sequence_by_id(read_id));
        const std::string& read_basepairs = fasta_reads.back().seq;
        const std::string& read_name      = fasta_reads.back().name;
        if (read_basepairs.length() >= window_size_ + kmer_size_ - 1)
        {
            read_id_to_basepairs_section_h.emplace_back(ArrayBlock{total_basepairs, static_cast<std::uint32_t>(read_basepairs.length())});
            total_basepairs += read_basepairs.length();
            read_id_to_read_name_.push_back(read_name);
            read_id_to_read_length_.push_back(read_basepairs.length());
        }
        else
        {
            // TODO: Implement this skipping in a correct manner
            CGA_LOG_INFO("Skipping read {}. It has {} basepairs, one window covers {} basepairs",
                         read_name,
                         read_basepairs.length(),
                         window_size_ + kmer_size_ - 1);
        }
    }

    if (0 == total_basepairs)
    {
        CGA_LOG_INFO("Index for reads {} to past {} is empty",
                     first_read_id,
                     past_the_last_read_id);
        number_of_reads_ = 0;
        return;
    }

    std::vector<char> merged_basepairs_h(total_basepairs);

    // copy basepairs from each read into one big array
    // read_id starts from first_read_id which can have an arbitrary value, local_read_id always starts from 0
    for (read_id_t local_read_id = 0; local_read_id < number_of_reads_; ++local_read_id)
    {
        const std::string& read_basepairs = fasta_reads[local_read_id].seq;
        std::copy(std::begin(read_basepairs),
                  std::end(read_basepairs),
                  std::next(std::begin(merged_basepairs_h), read_id_to_basepairs_section_h[local_read_id].first_element_));
    }
    fasta_reads.clear();
    fasta_reads.shrink_to_fit();

    // move basepairs to the device
    CGA_LOG_INFO("Allocating {} bytes for read_id_to_basepairs_section_d", read_id_to_basepairs_section_h.size() * sizeof(decltype(read_id_to_basepairs_section_h)::value_type));
    device_buffer<decltype(read_id_to_basepairs_section_h)::value_type> read_id_to_basepairs_section_d(read_id_to_basepairs_section_h.size());
    CGA_CU_CHECK_ERR(cudaMemcpy(read_id_to_basepairs_section_d.data(),
                                read_id_to_basepairs_section_h.data(),
                                read_id_to_basepairs_section_h.size() * sizeof(decltype(read_id_to_basepairs_section_h)::value_type),
                                cudaMemcpyHostToDevice));

    CGA_LOG_INFO("Allocating {} bytes for merged_basepairs_d", merged_basepairs_h.size() * sizeof(decltype(merged_basepairs_h)::value_type));
    device_buffer<decltype(merged_basepairs_h)::value_type> merged_basepairs_d(merged_basepairs_h.size());
    CGA_CU_CHECK_ERR(cudaMemcpy(merged_basepairs_d.data(),
                                merged_basepairs_h.data(),
                                merged_basepairs_h.size() * sizeof(decltype(merged_basepairs_h)::value_type),
                                cudaMemcpyHostToDevice));
    merged_basepairs_h.clear();
    merged_basepairs_h.shrink_to_fit();

    // sketch elements get generated here
    auto sketch_elements                                                      = SketchElementImpl::generate_sketch_elements(number_of_reads_,
                                                                       kmer_size_,
                                                                       window_size_,
                                                                       first_read_id,
                                                                       merged_basepairs_d,
                                                                       read_id_to_basepairs_section_h,
                                                                       read_id_to_basepairs_section_d,
                                                                       hash_representations);
    device_buffer<representation_t> representations_d                         = std::move(sketch_elements.representations_d);
    device_buffer<typename SketchElementImpl::ReadidPositionDirection> rest_d = std::move(sketch_elements.rest_d);

    CGA_LOG_INFO("Deallocating {} bytes from read_id_to_basepairs_section_d", read_id_to_basepairs_section_d.size() * sizeof(decltype(read_id_to_basepairs_section_d)::value_type));
    read_id_to_basepairs_section_d.free();
    CGA_LOG_INFO("Deallocating {} bytes from merged_basepairs_d", merged_basepairs_d.size() * sizeof(decltype(merged_basepairs_d)::value_type));
    merged_basepairs_d.free();

    // *** sort sketch elements by representation ***
    // As this is a stable sort and the data was initailly grouper by read_id this means that the sketch elements within each representations are sorted by read_id
    thrust::stable_sort_by_key(thrust::device,
                               representations_d.data(),
                               representations_d.data() + representations_d.size(),
                               rest_d.data());

    // copy the data to member functions (depending on the interface desing these copies might not be needed)
    representations_d_.resize(representations_d.size());
    representations_d_.shrink_to_fit();
    thrust::copy(thrust::device,
                 representations_d.data(),
                 representations_d.data() + representations_d.size(),
                 representations_d_.begin());
    representations_d.free();

    read_ids_d_.resize(representations_d_.size());
    read_ids_d_.shrink_to_fit();
    positions_in_reads_d_.resize(representations_d_.size());
    positions_in_reads_d_.shrink_to_fit();
    directions_of_reads_d_.resize(representations_d_.size());
    directions_of_reads_d_.shrink_to_fit();

    const std::uint32_t threads = 256;
    const std::uint32_t blocks  = ceiling_divide<int64_t>(representations_d_.size(), threads);

    details::index_gpu::copy_rest_to_separate_arrays<<<blocks, threads>>>(rest_d.data(),
                                                                          read_ids_d_.data().get(),
                                                                          positions_in_reads_d_.data().get(),
                                                                          directions_of_reads_d_.data().get(),
                                                                          representations_d_.size());

    // now generate the index elements
    details::index_gpu::find_first_occurrences_of_representations(unique_representations_d_,
                                                                  first_occurrence_of_representations_d_,
                                                                  representations_d_);
}

} // namespace cudamapper
} // namespace claragenomics

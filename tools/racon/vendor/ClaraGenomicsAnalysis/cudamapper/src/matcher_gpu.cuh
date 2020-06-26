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
#include <thrust/device_vector.h>
#include <claragenomics/cudamapper/matcher.hpp>
#include <claragenomics/cudamapper/types.hpp>

namespace claragenomics
{

namespace cudamapper
{

class MatcherGPU : public Matcher
{
public:
    MatcherGPU(const Index& query_index,
               const Index& target_index);

    thrust::device_vector<Anchor>& anchors() override;

private:
    thrust::device_vector<Anchor> anchors_d_;
};

namespace details
{

namespace matcher_gpu
{
/// \brief Finds the array index of the target representation for each query representation
///
/// Takes an array of query representations and an array of target representations
/// and checks for each query representation if the representation is present in the target array.
/// To return the result, the function takes a reference to an array of indices \param found_target_indices_d
/// which has to be of the same length of the query representations array.
/// If a query representation is found in the target the same representation the corresponding index
/// of the target array will be stored in \param found_target_indices_d at the position corresponding
/// to the query in the query array.
/// If a query is not found in the target array, -1 will be stored to the corresponding position of \param found_target_indices_d
/// For example:
///   query:
///     array-index:    0  1  2  3  4
///     representation: 0 12 23 32 46
///   target:
///     array-index:    0  1  2  3  4  5  6
///     representation: 5 12 16 23 24 25 46
///
/// gives:
///   found_target_indicies_d:
///     array-index:    0  1  2  3  4
///     target-index:  -1  1  3 -1  6
///
/// \param found_target_indices_d The array which will filled with the resulting target indices. This array has to be of same size as query_representations_d.
/// \param query_representations_d An array of query representations
/// \param target_representations_d An sorted array of target representations
void find_query_target_matches(
    thrust::device_vector<std::int64_t>& found_target_indices_d,
    const thrust::device_vector<representation_t>& query_representations_d,
    const thrust::device_vector<representation_t>& target_representations_d);

/// \brief Computes the starting indices for an array of anchors based on the matches in query and target arrays.
///
/// Takes the arrays which store the positions of the first occurrences the different representations
/// in the query and target representation arrays (see find_first_occurrences_of_representations)
/// and the array with the found matches (see find_query_target_matches) and computes the starting indices to construct an array of anchors.
/// The i-1-th element tells the starting point of the i-th element in the query array (including invalid entries for unmatched queries).
/// The last element is the total number of anchors.
/// For example:
///   query:
///     representation: 0 12 23 32 46
///     starting index: 0  4 10 13 18 21
///   target:
///     representation: 5 12 16 23 24 25 46
///     starting index: 0  3  7  9 13 16 18 21
///
///   found_target_indicies_d: (matching representations: 12, 23, 46)
///     array-index:    0  1  2  3  4
///     target-index:  -1  1  3 -1  6 (-1 indicates no matching representation in target)
///
///     anchors per representation:
///     12: (10-4)*(7-3)
///     23: (13-10)*(13-9)
///     46: (21-18)*(21-18)
///   gives:
///     query representation:                 0 12 23 32 46
///     number of anchors per representation: 0 24 12  0  9
///     anchor starting index:                0 24 36 36 45
///
/// \param anchor_starting_indices_d The starting indices for the anchors based on each query
/// \param query_starting_index_of_each_representation_d
/// \param found_target_indices_d
/// \param target_starting_index_of_each_representation_d
void compute_anchor_starting_indices(
    thrust::device_vector<std::int64_t>& anchor_starting_indices_d,
    const thrust::device_vector<std::uint32_t>& query_starting_index_of_each_representation_d,
    const thrust::device_vector<std::int64_t>& found_target_indices_d,
    const thrust::device_vector<std::uint32_t>& target_starting_index_of_each_representation_d);

/// \brief Generates an array of anchors from matches of representations of the query and target index
///
/// Fills the array of anchors with anchors of matches between the query and target index by using the
/// anchor_starting_indices for each unique representation of the query index.
/// The anchor_starting_indices can be computed by compute_anchor_starting_indices and the size of the
/// anchors array must match the last element of anchor_starting_indices.
///
/// For example:
///   (see also compute_anchor_starting_indices() )
///   anchor_starting_indices:
///   query:
///     (representation: 0 12 23 32 46)
///      starting index: 0  4 10 13 18 21
///   target:
///     (representation: 5 12 16 23 24 25 46)
///      starting index: 0  3  7  9 13 16 18 21
///   matching representations are 12, 23, 46
///
///   (query representation:      0 12 23 32 46)
///   array-index:                0  1  2  3  4
///   found_target_indices_d:    -1  1  3 -1  6 (-1 indicates no matching representation in target)
///   anchor_starting_indices_d:  0 24 36 36 45
///
///   query:
///     read_ids (arbitrary data):           0  1  2  3  4  5  6  7  8  9  10 ... 21
///     positions_in_read (arbitrary data):  0 10 20 30 40 50 60 70 80 90 100 ... 210
///   target:
///     read_ids (arbitrary data):          60 61 62 63 64 65 66 67 68 69  70 ...  81
///     positions_in_read (arbitrary data):  0 11 22 33 44 55 66 77 88 99 110 ... 231
///
///   anchors:
///     all-to-all combinations of representations 12, 23, 46:
///     format:
///     representation: anchors (query_read_id, query_position, target_read_id, target_position)
///     12: (4,40,63,33), (4,40,64,44), ..., (4,40,66,66), (5,50,63,33), ..., (5,50,66,66), ..., ..., (9,90,66,66) -- 24 elements in total
///     23: (10,100,69,99), (10,100,70,110), ..., (10,100,72,132), (11,110,69,99), ..., ..., (12,120,72,132) --  12 elements in total
///     46: (18,180,78,198), ..., ..., (20,200,80,220) -- 9 elements in total
///
///
/// \param anchors the array to be filled with anchors, the size of this array has to be equal to the last element of anchor_starting_indices
/// \param anchor_starting_indices_d the array of starting indices of the set of anchors for each unique representation of the query index (representations with no match in target will have the same starting index as the last matching representation)
/// \param query_starting_index_of_each_representation_d the starting index of a representation in query_read_ids and query_positions_in_read
/// \param found_target_indices_d the found matches in the array of unique target representation for each unique representation of query index
/// \param target_starting_index_of_each_representation_d the starting index of a representation in target_read_ids and target_positions_in_read
/// \param query_read_ids the array of read ids of the (read id, position)-pairs in query index
/// \param query_positions_in_read the array of positions of the (read id, position)-pairs in query index
/// \param target_read_ids the array of read ids of the (read id, position)-pairs in target index
/// \param target_positions_in_read the array of positions of the (read id, position)-pairs in target index
void generate_anchors(
    thrust::device_vector<Anchor>& anchors,
    const thrust::device_vector<std::int64_t>& anchor_starting_indices_d,
    const thrust::device_vector<std::uint32_t>& query_starting_index_of_each_representation_d,
    const thrust::device_vector<std::int64_t>& found_target_indices_d,
    const thrust::device_vector<std::uint32_t>& target_starting_index_of_each_representation_d,
    const thrust::device_vector<read_id_t>& query_read_ids,
    const thrust::device_vector<position_in_read_t>& query_positions_in_read,
    const thrust::device_vector<read_id_t>& target_read_ids,
    const thrust::device_vector<position_in_read_t>& target_positions_in_read);

/// \brief Performs a binary search on target_representations_d for each element of query_representations_d and stores the found index (or -1 iff not found) in found_target_indices.
///
/// For example:
///   query:
///     array-index:    0  1  2  3  4
///     representation: 0 12 23 32 46
///   target:
///     array-index:    0  1  2  3  4  5  6
///     representation: 5 12 16 23 24 25 46
///
/// gives:
///   found_target_indicies_d:
///     array-index:    0  1  2  3  4
///     target-index:  -1  1  3 -1  6
///
/// \param found_target_indices_d the array which will hold the result
/// \param query_representations_d the array of queries
/// \param n_query_representations size of \param query_representations_d and \param found_target_indices_d
/// \param target_representations_d the array of targets to be searched
/// \param n_target_representations size of \param target_representations_d
__global__ void find_query_target_matches_kernel(
    int64_t* const found_target_indices_d,
    const representation_t* const query_representations_d,
    const int64_t n_query_representations,
    const representation_t* const target_representations_d,
    const int64_t n_target_representations);

/// \brief Generates an array of anchors from matches of representations of the query and target index
///
/// see generate_anchors()
///
/// \param anchors the array to be filled with anchors, the size of this array has to be equal to the last element of anchor_starting_indices
/// \param n_anchors the size of the anchors array
/// \param anchor_starting_indices_d the array of starting indices of the set of anchors for each unique representation of the query index (representations with no match in target will have the same starting index as the last matching representation)
/// \param query_starting_index_of_each_representation_d the starting index of a representation in query_read_ids and query_positions_in_read
/// \param found_target_indices_d the found matches in the array of unique target representation for each unique representation of query index
/// \param target_starting_index_of_each_representation_d the starting index of a representation in target_read_ids and target_positions_in_read
/// \param n_query_representations the size of the query_starting_index_of_each_representation_d and found_target_indices_d arrays, ie. the number of unique representations in the query index
/// \param query_read_ids the array of read ids of the (read id, position)-pairs in query index
/// \param query_positions_in_read the array of positions of the (read id, position)-pairs in query index
/// \param target_read_ids the array of read ids of the (read id, position)-pairs in target index
/// \param target_positions_in_read the array of positions of the (read id, position)-pairs in target index
__global__ void generate_anchors_kernel(
    Anchor* const anchors_d,
    const int64_t n_anchors,
    const int64_t* const anchor_starting_index_d,
    const std::uint32_t* const query_starting_index_of_each_representation_d,
    const std::int64_t* const found_target_indices_d,
    const int32_t n_query_representations,
    const std::uint32_t* const target_starting_index_of_each_representation_d,
    const read_id_t* const query_read_ids,
    const position_in_read_t* const query_positions_in_read,
    const read_id_t* const target_read_ids,
    const position_in_read_t* const target_positions_in_read);
} // namespace matcher_gpu

} // namespace details

} // namespace cudamapper

} // namespace claragenomics

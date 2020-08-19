/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "matcher_gpu.cuh"

#include <thrust/scan.h>
#include <thrust/transform_scan.h>
#include <thrust/execution_policy.h>
#include <cassert>

#include <claragenomics/utils/cudautils.hpp>
#include <claragenomics/utils/mathutils.hpp>
#include <claragenomics/utils/signed_integer_utils.hpp>

namespace
{
template <typename RandomAccessIterator, typename ValueType>
__device__ RandomAccessIterator lower_bound(RandomAccessIterator lower_bound, RandomAccessIterator upper_bound, ValueType query)
{
    assert(upper_bound >= lower_bound);
    while (upper_bound > lower_bound)
    {
        RandomAccessIterator mid = lower_bound + (upper_bound - lower_bound) / 2;
        const auto mid_value     = *mid;
        if (mid_value < query)
            lower_bound = mid + 1;
        else
            upper_bound = mid;
    }
    return lower_bound;
}

template <typename RandomAccessIterator, typename ValueType>
__device__ RandomAccessIterator upper_bound(RandomAccessIterator lower_bound, RandomAccessIterator upper_bound, ValueType query)
{
    assert(upper_bound >= lower_bound);
    while (upper_bound > lower_bound)
    {
        RandomAccessIterator mid = lower_bound + (upper_bound - lower_bound) / 2;
        const auto mid_value     = *mid;
        if (mid_value <= query)
            lower_bound = mid + 1;
        else
            upper_bound = mid;
    }
    return lower_bound;
}
} // namespace

namespace claragenomics
{

namespace cudamapper
{

MatcherGPU::MatcherGPU(const Index& query_index,
                       const Index& target_index)
{

    CGA_NVTX_RANGE(profile, "matcherGPU");
    if (query_index.number_of_reads() == 0 || target_index.number_of_reads() == 0)
        return;

    // We need to compute a set of anchors between the query and the target.
    // An anchor is a combination of a query (read_id, position) and
    // target {read_id, position} with the same representation.
    // The set of anchors of a matching query and target representation
    // is the all-to-all combination of the corresponding set of {(read_id, position)}
    // of the query with the set of {(read_id, position)} of the target.
    //
    // We compute the anchors for each unique representation of the query index.
    // The array index of the following data structures will correspond to the array index of the
    // unique representation in the query index.

    thrust::device_vector<std::int64_t> found_target_indices_d(query_index.unique_representations().size());
    thrust::device_vector<std::int64_t> anchor_starting_indices_d(query_index.unique_representations().size());

    // First we search for each unique representation of the query index, the array index
    // of the same representation in the array of unique representations of target index
    // (or -1 if representation is not found).
    details::matcher_gpu::find_query_target_matches(found_target_indices_d, query_index.unique_representations(), target_index.unique_representations());

    // For each unique representation of the query index compute the number of corrsponding anchors
    // and store the resulting starting index in an anchors array if all anchors are stored in a flat array.
    // The last element will be the total number of anchors.
    details::matcher_gpu::compute_anchor_starting_indices(anchor_starting_indices_d, query_index.first_occurrence_of_representations(), found_target_indices_d, target_index.first_occurrence_of_representations());

    const int64_t n_anchors = anchor_starting_indices_d.back(); // D->H transfer

    anchors_d_.resize(n_anchors);

    // Generate the anchors
    // by computing the all-to-all combinations of the matching representations in query and target
    details::matcher_gpu::generate_anchors(anchors_d_,
                                           anchor_starting_indices_d,
                                           query_index.first_occurrence_of_representations(),
                                           found_target_indices_d,
                                           target_index.first_occurrence_of_representations(),
                                           query_index.read_ids(),
                                           query_index.positions_in_reads(),
                                           target_index.read_ids(),
                                           target_index.positions_in_reads());
}

thrust::device_vector<Anchor>& MatcherGPU::anchors()
{
    return anchors_d_;
}

namespace details
{

namespace matcher_gpu
{

void find_query_target_matches(
    thrust::device_vector<std::int64_t>& found_target_indices_d,
    const thrust::device_vector<representation_t>& query_representations_d,
    const thrust::device_vector<representation_t>& target_representations_d)
{
    assert(found_target_indices_d.size() == query_representations_d.size());

    const int32_t n_threads = 256;
    const int32_t n_blocks  = ceiling_divide<int64_t>(query_representations_d.size(), n_threads);

    find_query_target_matches_kernel<<<n_blocks, n_threads>>>(found_target_indices_d.data().get(), query_representations_d.data().get(), get_size(query_representations_d), target_representations_d.data().get(), get_size(target_representations_d));
}

void compute_anchor_starting_indices(
    thrust::device_vector<std::int64_t>& anchor_starting_indices_d,
    const thrust::device_vector<std::uint32_t>& query_starting_index_of_each_representation_d,
    const thrust::device_vector<std::int64_t>& found_target_indices_d,
    const thrust::device_vector<std::uint32_t>& target_starting_index_of_each_representation_d)
{
    assert(query_starting_index_of_each_representation_d.size() == found_target_indices_d.size() + 1);
    assert(anchor_starting_indices_d.size() == found_target_indices_d.size());

    const std::uint32_t* const query_starting_indices  = query_starting_index_of_each_representation_d.data().get();
    const std::uint32_t* const target_starting_indices = target_starting_index_of_each_representation_d.data().get();
    const std::int64_t* const found_target_indices     = found_target_indices_d.data().get();

    thrust::transform_inclusive_scan(
        thrust::make_counting_iterator(std::int64_t(0)),
        thrust::make_counting_iterator(get_size(anchor_starting_indices_d)),
        anchor_starting_indices_d.begin(),
        [query_starting_indices, target_starting_indices, found_target_indices] __device__(std::uint32_t query_index) -> std::int64_t {
            std::int32_t n_queries_with_representation = query_starting_indices[query_index + 1] - query_starting_indices[query_index];
            std::int64_t target_index                  = found_target_indices[query_index];
            std::int32_t n_targets_with_representation = 0;
            if (target_index >= 0)
                n_targets_with_representation = target_starting_indices[target_index + 1] - target_starting_indices[target_index];
            return n_queries_with_representation * n_targets_with_representation;
        },
        thrust::plus<std::int64_t>());
}

__global__ void find_query_target_matches_kernel(
    int64_t* const found_target_indices,
    const representation_t* const query_representations_d,
    const int64_t n_query_representations,
    const representation_t* const target_representations_d,
    const int64_t n_target_representations)
{
    const int64_t i = blockIdx.x * blockDim.x + threadIdx.x;

    if (i >= n_query_representations)
        return;

    const representation_t query = query_representations_d[i];
    int64_t found_target_index   = -1;
    const representation_t* lb   = lower_bound(target_representations_d, target_representations_d + n_target_representations, query);
    if (*lb == query)
        found_target_index = lb - target_representations_d;

    found_target_indices[i] = found_target_index;
}

void generate_anchors(
    thrust::device_vector<Anchor>& anchors,
    const thrust::device_vector<std::int64_t>& anchor_starting_indices_d,
    const thrust::device_vector<std::uint32_t>& query_starting_index_of_each_representation_d,
    const thrust::device_vector<std::int64_t>& found_target_indices_d,
    const thrust::device_vector<std::uint32_t>& target_starting_index_of_each_representation_d,
    const thrust::device_vector<read_id_t>& query_read_ids,
    const thrust::device_vector<position_in_read_t>& query_positions_in_read,
    const thrust::device_vector<read_id_t>& target_read_ids,
    const thrust::device_vector<position_in_read_t>& target_positions_in_read)
{
    assert(anchor_starting_indices_d.size() + 1 == query_starting_index_of_each_representation_d.size());
    assert(found_target_indices_d.size() + 1 == query_starting_index_of_each_representation_d.size());
    assert(query_read_ids.size() == query_positions_in_read.size());
    assert(target_read_ids.size() == target_positions_in_read.size());

    const int32_t n_threads = 256;
    const int32_t n_blocks  = ceiling_divide<int64_t>(get_size(anchors), n_threads);
    generate_anchors_kernel<<<n_blocks, n_threads>>>(
        anchors.data().get(),
        get_size(anchors),
        anchor_starting_indices_d.data().get(),
        query_starting_index_of_each_representation_d.data().get(),
        found_target_indices_d.data().get(),
        get_size(found_target_indices_d),
        target_starting_index_of_each_representation_d.data().get(),
        query_read_ids.data().get(),
        query_positions_in_read.data().get(),
        target_read_ids.data().get(),
        target_positions_in_read.data().get());
}

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
    const position_in_read_t* const target_positions_in_read)
{
    // Fill the anchor_d array. Each thread generates one anchor.
    std::int64_t anchor_idx = blockIdx.x * blockDim.x + threadIdx.x;

    if (anchor_idx >= n_anchors)
        return;

    // Figure out for which representation this thread should compute the anchor.
    // We only need the index in the unique representation array of the query index
    // not the representation itself.
    const std::int64_t representation_idx = upper_bound(anchor_starting_index_d, anchor_starting_index_d + n_query_representations, anchor_idx) - anchor_starting_index_d;

    assert(representation_idx < n_query_representations);

    // Compute the index of the anchor within only this representation.
    std::uint32_t relative_anchor_index = anchor_idx;
    if (representation_idx > 0)
        relative_anchor_index -= anchor_starting_index_d[representation_idx - 1];

    // Get the ranges within the query and target index with this representation.
    const std::int64_t j = found_target_indices_d[representation_idx];
    assert(j >= 0);
    const std::uint32_t query_begin  = query_starting_index_of_each_representation_d[representation_idx];
    const std::uint32_t target_begin = target_starting_index_of_each_representation_d[j];
    const std::uint32_t target_end   = target_starting_index_of_each_representation_d[j + 1];

    const std::uint32_t n_targets = target_end - target_begin;

    // Overall we want to do an all-to-all (n*m) matching between the query and target entries
    // with the same representation.
    // Compute the exact combination query and target index entry for which
    // we generate the anchor in this thread.
    const std::uint32_t query_idx  = query_begin + relative_anchor_index / n_targets;
    const std::uint32_t target_idx = target_begin + relative_anchor_index % n_targets;

    assert(query_idx < query_starting_index_of_each_representation_d[representation_idx + 1]);

    // Generate and store the anchor
    Anchor a;
    a.query_read_id_           = query_read_ids[query_idx];
    a.target_read_id_          = target_read_ids[target_idx];
    a.query_position_in_read_  = query_positions_in_read[query_idx];
    a.target_position_in_read_ = target_positions_in_read[target_idx];
    anchors_d[anchor_idx]      = a;
}

} // namespace matcher_gpu

} // namespace details
} // namespace cudamapper

} // namespace claragenomics

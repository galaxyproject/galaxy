/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "gtest/gtest.h"

#include "cudamapper_file_location.hpp"

#include <thrust/host_vector.h>
#include <thrust/device_vector.h>

#include <claragenomics/utils/cudautils.hpp>
#include <claragenomics/utils/signed_integer_utils.hpp>

#include "../src/matcher_gpu.cuh"

namespace claragenomics
{

namespace cudamapper
{
void test_find_query_target_matches(const thrust::host_vector<representation_t>& query_representations_h,
                                    const thrust::host_vector<representation_t>& target_representations_h,
                                    const thrust::host_vector<std::int64_t>& expected_found_target_indices_h)
{
    const thrust::device_vector<representation_t> query_representations_d(query_representations_h);
    const thrust::device_vector<representation_t> target_representations_d(target_representations_h);
    thrust::device_vector<int64_t> found_target_indices_d(query_representations_d.size());

    details::matcher_gpu::find_query_target_matches(found_target_indices_d, query_representations_d, target_representations_d);

    thrust::device_vector<int64_t> found_target_indices_h(found_target_indices_d);

    ASSERT_EQ(found_target_indices_h.size(), expected_found_target_indices_h.size());

    for (int32_t i = 0; i < get_size(found_target_indices_h); ++i)
    {
        EXPECT_EQ(found_target_indices_h[i], expected_found_target_indices_h[i]) << "index: " << i;
    }
}

TEST(TestCudamapperMatcherGPU, test_find_query_target_matches_small_example)
{
    thrust::host_vector<representation_t> query_representations_h;
    query_representations_h.push_back(0);
    query_representations_h.push_back(12);
    query_representations_h.push_back(23);
    query_representations_h.push_back(32);
    query_representations_h.push_back(46);
    thrust::host_vector<representation_t> target_representations_h;
    target_representations_h.push_back(5);
    target_representations_h.push_back(12);
    target_representations_h.push_back(16);
    target_representations_h.push_back(23);
    target_representations_h.push_back(24);
    target_representations_h.push_back(25);
    target_representations_h.push_back(46);

    thrust::host_vector<int64_t> expected_found_target_indices_h;
    expected_found_target_indices_h.push_back(-1);
    expected_found_target_indices_h.push_back(1);
    expected_found_target_indices_h.push_back(3);
    expected_found_target_indices_h.push_back(-1);
    expected_found_target_indices_h.push_back(6);

    test_find_query_target_matches(query_representations_h, target_representations_h, expected_found_target_indices_h);
}

TEST(TestCudamapperMatcherGPU, test_query_target_matches_large_example)
{
    const std::int64_t total_query_representations = 1000000;

    thrust::host_vector<representation_t> query_representations_h;
    thrust::host_vector<representation_t> target_representations_h;

    for (std::int64_t i = 0; i < total_query_representations; ++i)
    {
        query_representations_h.push_back(i * 3);
    }

    thrust::device_vector<std::int64_t> expected_found_target_indices_h(query_representations_h.size(), -1);

    const representation_t max_representation = query_representations_h.back();
    for (representation_t r = 0; r < max_representation; r += 2)
    {
        target_representations_h.push_back(r);
        if (r % 3 == 0)
        {
            if (r / 3 < expected_found_target_indices_h.size())
            {
                expected_found_target_indices_h[r / 3] = get_size(target_representations_h) - 1;
            }
        }
    }

    test_find_query_target_matches(query_representations_h, target_representations_h, expected_found_target_indices_h);
}

void test_compute_number_of_anchors(const thrust::host_vector<std::uint32_t>& query_starting_index_of_each_representation_h,
                                    const thrust::host_vector<std::int64_t>& found_target_indices_h,
                                    const thrust::host_vector<std::uint32_t>& target_starting_index_of_each_representation_h,
                                    const thrust::host_vector<std::int64_t>& expected_anchor_starting_indices_h)
{
    const thrust::device_vector<std::uint32_t> query_starting_index_of_each_representation_d(query_starting_index_of_each_representation_h);
    const thrust::device_vector<std::uint32_t> target_starting_index_of_each_representation_d(target_starting_index_of_each_representation_h);
    const thrust::device_vector<std::int64_t> found_target_indices_d(found_target_indices_h);
    thrust::device_vector<std::int64_t> anchor_starting_indices_d(found_target_indices_h.size());

    details::matcher_gpu::compute_anchor_starting_indices(anchor_starting_indices_d, query_starting_index_of_each_representation_d, found_target_indices_d, target_starting_index_of_each_representation_d);

    thrust::host_vector<std::int64_t> anchor_starting_indices_h(anchor_starting_indices_d);

    for (int32_t i = 0; i < get_size(found_target_indices_h); ++i)
    {
        EXPECT_EQ(anchor_starting_indices_h[i], expected_anchor_starting_indices_h[i]);
    }
}

TEST(TestCudamapperMatcherGPU, test_compute_number_of_anchors_small_example)
{
    thrust::host_vector<representation_t> query_starting_index_of_each_representation_h;
    query_starting_index_of_each_representation_h.push_back(0);
    query_starting_index_of_each_representation_h.push_back(4);
    query_starting_index_of_each_representation_h.push_back(10);
    query_starting_index_of_each_representation_h.push_back(13);
    query_starting_index_of_each_representation_h.push_back(18);
    query_starting_index_of_each_representation_h.push_back(21);

    thrust::host_vector<representation_t> target_starting_index_of_each_representation_h;
    target_starting_index_of_each_representation_h.push_back(0);
    target_starting_index_of_each_representation_h.push_back(3);
    target_starting_index_of_each_representation_h.push_back(7);
    target_starting_index_of_each_representation_h.push_back(9);
    target_starting_index_of_each_representation_h.push_back(13);
    target_starting_index_of_each_representation_h.push_back(16);
    target_starting_index_of_each_representation_h.push_back(18);
    target_starting_index_of_each_representation_h.push_back(21);

    thrust::host_vector<int64_t> found_target_indices_h;
    found_target_indices_h.push_back(-1);
    found_target_indices_h.push_back(1);
    found_target_indices_h.push_back(3);
    found_target_indices_h.push_back(-1);
    found_target_indices_h.push_back(6);

    thrust::host_vector<int64_t> expected_anchor_starting_indices;
    expected_anchor_starting_indices.push_back(0);
    expected_anchor_starting_indices.push_back(24);
    expected_anchor_starting_indices.push_back(36);
    expected_anchor_starting_indices.push_back(36);
    expected_anchor_starting_indices.push_back(45);

    test_compute_number_of_anchors(query_starting_index_of_each_representation_h,
                                   found_target_indices_h,
                                   target_starting_index_of_each_representation_h,
                                   expected_anchor_starting_indices);
}

TEST(TestCudamapperMatcherGPU, test_compute_number_of_anchors_large_example)
{
    const std::int64_t length = 100000;

    thrust::host_vector<representation_t> query_starting_index_of_each_representation_h;
    thrust::host_vector<representation_t> target_starting_index_of_each_representation_h;
    thrust::host_vector<std::int64_t> found_target_indices_h(length - 1, -1);
    thrust::host_vector<std::int64_t> expected_anchor_starting_indices_h;
    std::int64_t expected_n_anchors = 0;
    for (std::int64_t i = 0; i < length; ++i)
    {
        query_starting_index_of_each_representation_h.push_back(2 * i);
        target_starting_index_of_each_representation_h.push_back(10 * i + i % 10);
        if (i % 3 == 0 && i < length - 1)
        {
            found_target_indices_h[i] = i;
            expected_n_anchors += 2 * (10 + (i + 1) % 10 - i % 10);
        }
        if (i < length - 1)
            expected_anchor_starting_indices_h.push_back(expected_n_anchors);
    }

    test_compute_number_of_anchors(query_starting_index_of_each_representation_h,
                                   found_target_indices_h,
                                   target_starting_index_of_each_representation_h,
                                   expected_anchor_starting_indices_h);
}

void test_generate_anchors(
    const thrust::host_vector<Anchor>& expected_anchors_h,
    const thrust::host_vector<std::int64_t>& anchor_starting_indices_h,
    const thrust::host_vector<std::uint32_t>& query_starting_index_of_each_representation_h,
    const thrust::host_vector<std::int64_t>& found_target_indices_h,
    const thrust::host_vector<std::uint32_t>& target_starting_index_of_each_representation_h,
    const thrust::host_vector<read_id_t>& query_read_ids_h,
    const thrust::host_vector<position_in_read_t>& query_positions_in_read_h,
    const thrust::host_vector<read_id_t>& target_read_ids_h,
    const thrust::host_vector<position_in_read_t>& target_positions_in_read_h)
{
    const thrust::device_vector<std::int64_t> anchor_starting_indices_d(anchor_starting_indices_h);
    const thrust::device_vector<std::uint32_t> query_starting_index_of_each_representation_d(query_starting_index_of_each_representation_h);
    const thrust::device_vector<std::int64_t> found_target_indices_d(found_target_indices_h);
    const thrust::device_vector<std::uint32_t> target_starting_index_of_each_representation_d(target_starting_index_of_each_representation_h);
    const thrust::device_vector<read_id_t> query_read_ids_d(query_read_ids_h);
    const thrust::device_vector<position_in_read_t> query_positions_in_read_d(query_positions_in_read_h);
    const thrust::device_vector<read_id_t> target_read_ids_d(target_read_ids_h);
    const thrust::device_vector<position_in_read_t> target_positions_in_read_d(target_positions_in_read_h);

    thrust::device_vector<Anchor> anchors_d(anchor_starting_indices_h.back());

    details::matcher_gpu::generate_anchors(anchors_d,
                                           anchor_starting_indices_d,
                                           query_starting_index_of_each_representation_d,
                                           found_target_indices_d,
                                           target_starting_index_of_each_representation_d,
                                           query_read_ids_d,
                                           query_positions_in_read_d,
                                           target_read_ids_d,
                                           target_positions_in_read_d);

    thrust::host_vector<Anchor> anchors_h(anchors_d);
    ASSERT_EQ(anchors_h.size(), expected_anchors_h.size());

    for (int64_t i = 0; i < get_size(anchors_h); ++i)
    {
        EXPECT_EQ(anchors_h[i].query_read_id_, expected_anchors_h[i].query_read_id_) << " index: " << i;
        EXPECT_EQ(anchors_h[i].query_position_in_read_, expected_anchors_h[i].query_position_in_read_) << " index: " << i;
        EXPECT_EQ(anchors_h[i].target_read_id_, expected_anchors_h[i].target_read_id_) << " index: " << i;
        EXPECT_EQ(anchors_h[i].target_position_in_read_, expected_anchors_h[i].target_position_in_read_) << " index: " << i;
    }
}

TEST(TestCudamapperMatcherGPU, test_generate_anchors_small_example)
{
    thrust::host_vector<representation_t> query_starting_index_of_each_representation_h;
    query_starting_index_of_each_representation_h.push_back(0);
    query_starting_index_of_each_representation_h.push_back(4);
    query_starting_index_of_each_representation_h.push_back(10);
    query_starting_index_of_each_representation_h.push_back(13);
    query_starting_index_of_each_representation_h.push_back(18);
    query_starting_index_of_each_representation_h.push_back(21);

    thrust::host_vector<representation_t> target_starting_index_of_each_representation_h;
    target_starting_index_of_each_representation_h.push_back(0);
    target_starting_index_of_each_representation_h.push_back(3);
    target_starting_index_of_each_representation_h.push_back(7);
    target_starting_index_of_each_representation_h.push_back(9);
    target_starting_index_of_each_representation_h.push_back(13);
    target_starting_index_of_each_representation_h.push_back(16);
    target_starting_index_of_each_representation_h.push_back(18);
    target_starting_index_of_each_representation_h.push_back(21);

    thrust::host_vector<int64_t> found_target_indices_h;
    found_target_indices_h.push_back(-1);
    found_target_indices_h.push_back(1);
    found_target_indices_h.push_back(3);
    found_target_indices_h.push_back(-1);
    found_target_indices_h.push_back(6);

    thrust::host_vector<int64_t> anchor_starting_indices_h;
    anchor_starting_indices_h.push_back(0);
    anchor_starting_indices_h.push_back(24);
    anchor_starting_indices_h.push_back(36);
    anchor_starting_indices_h.push_back(36);
    anchor_starting_indices_h.push_back(45);

    thrust::host_vector<read_id_t> query_read_ids_h;
    thrust::host_vector<position_in_read_t> query_positions_in_read_h;
    for (std::uint32_t i = 0; i < query_starting_index_of_each_representation_h.back(); ++i)
    {
        query_read_ids_h.push_back(i);
        query_positions_in_read_h.push_back(10 * i);
    }

    thrust::host_vector<read_id_t> target_read_ids_h;
    thrust::host_vector<position_in_read_t> target_positions_in_read_h;
    for (std::uint32_t i = 0; i < target_starting_index_of_each_representation_h.back(); ++i)
    {
        target_read_ids_h.push_back(100 * i);
        target_positions_in_read_h.push_back(1000 * i);
    }

    thrust::host_vector<Anchor> expected_anchors(anchor_starting_indices_h.back());
    for (int32_t i = 0; i < 6; ++i)
        for (int32_t j = 0; j < 4; ++j)
        {
            Anchor& a                  = expected_anchors[i * 4 + j];
            a.query_read_id_           = 4 + i;
            a.query_position_in_read_  = 10 * (4 + i);
            a.target_read_id_          = 100 * (j + 3);
            a.target_position_in_read_ = 1000 * (j + 3);
        }

    for (int32_t i = 0; i < 3; ++i)
        for (int32_t j = 0; j < 4; ++j)
        {
            Anchor& a                  = expected_anchors[i * 4 + j + 24];
            a.query_read_id_           = 10 + i;
            a.query_position_in_read_  = 10 * (10 + i);
            a.target_read_id_          = 100 * (j + 9);
            a.target_position_in_read_ = 1000 * (j + 9);
        }

    for (int32_t i = 0; i < 3; ++i)
        for (int32_t j = 0; j < 3; ++j)
        {
            Anchor& a                  = expected_anchors[i * 3 + j + 36];
            a.query_read_id_           = 18 + i;
            a.query_position_in_read_  = 10 * (18 + i);
            a.target_read_id_          = 100 * (j + 18);
            a.target_position_in_read_ = 1000 * (j + 18);
        }

    test_generate_anchors(
        expected_anchors,
        anchor_starting_indices_h,
        query_starting_index_of_each_representation_h,
        found_target_indices_h,
        target_starting_index_of_each_representation_h,
        query_read_ids_h,
        query_positions_in_read_h,
        target_read_ids_h,
        target_positions_in_read_h);
}

TEST(TestCudamapperMatcherGPU, OneReadOneMinimizer)
{
    std::unique_ptr<io::FastaParser> parser = io::create_fasta_parser(std::string(CUDAMAPPER_BENCHMARK_DATA_DIR) + "/gatt.fasta");
    std::unique_ptr<Index> query_index      = Index::create_index(*parser, 0, parser->get_num_seqences(), 4, 1);
    std::unique_ptr<Index> target_index     = Index::create_index(*parser, 0, parser->get_num_seqences(), 4, 1);
    MatcherGPU matcher(*query_index, *target_index);

    const thrust::host_vector<Anchor> anchors(matcher.anchors());
    ASSERT_EQ(get_size(anchors), 1);
}

} // namespace cudamapper
} // namespace claragenomics

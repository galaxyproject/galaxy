/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <algorithm>
#include <numeric>
#include <random>
#include "gtest/gtest.h"
#include "mock_index.cuh"
#include "cudamapper_file_location.hpp"
#include "../src/cudamapper_utils.hpp"
#include "../src/overlapper_triggered.hpp"

namespace claragenomics
{
namespace cudamapper
{

TEST(TestCudamapperOverlapperTriggerred, FuseTwoOverlaps)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;

    Overlap overlap1;
    overlap1.query_read_id_                 = 20;
    overlap1.target_read_id_                = 22;
    overlap1.query_start_position_in_read_  = 1000;
    overlap1.query_end_position_in_read_    = 2000;
    overlap1.target_start_position_in_read_ = 4000;
    overlap1.target_end_position_in_read_   = 5000;
    unfused_overlaps.push_back(overlap1);

    Overlap overlap2;
    overlap2.query_read_id_                 = 20;
    overlap2.target_read_id_                = 22;
    overlap2.query_start_position_in_read_  = 10000;
    overlap2.query_end_position_in_read_    = 12000;
    overlap2.target_start_position_in_read_ = 14000;
    overlap2.target_end_position_in_read_   = 15000;

    unfused_overlaps.push_back(overlap2);
    std::vector<Overlap> fused_overlaps;
    fuse_overlaps(fused_overlaps, unfused_overlaps);

    ASSERT_EQ(fused_overlaps.size(), 1u);
}

TEST(TestCudamapperOverlapperTriggerred, DoNotuseTwoOverlaps)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;

    Overlap overlap1;
    overlap1.query_read_id_                 = 20;
    overlap1.target_read_id_                = 23;
    overlap1.query_start_position_in_read_  = 1000;
    overlap1.query_end_position_in_read_    = 2000;
    overlap1.target_start_position_in_read_ = 4000;
    overlap1.target_end_position_in_read_   = 5000;
    unfused_overlaps.push_back(overlap1);

    Overlap overlap2;
    overlap2.query_read_id_                 = 20;
    overlap2.target_read_id_                = 22;
    overlap2.query_start_position_in_read_  = 10000;
    overlap2.query_end_position_in_read_    = 12000;
    overlap2.target_start_position_in_read_ = 14000;
    overlap2.target_end_position_in_read_   = 15000;

    unfused_overlaps.push_back(overlap2);
    std::vector<Overlap> fused_overlaps;
    fuse_overlaps(fused_overlaps, unfused_overlaps);

    ASSERT_EQ(fused_overlaps.size(), 2u);
}

TEST(TestCudamapperOverlapperTriggerred, OneOverlap)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;

    Overlap overlap1;
    overlap1.query_read_id_                 = 20;
    overlap1.target_read_id_                = 23;
    overlap1.query_start_position_in_read_  = 1000;
    overlap1.query_end_position_in_read_    = 2000;
    overlap1.target_start_position_in_read_ = 4000;
    overlap1.target_end_position_in_read_   = 5000;
    unfused_overlaps.push_back(overlap1);

    std::vector<Overlap> fused_overlaps;
    fuse_overlaps(fused_overlaps, unfused_overlaps);

    ASSERT_EQ(fused_overlaps.size(), 1u);
}

TEST(TestCudamapperOverlapperTriggerred, NoOverlaps)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;

    std::vector<Overlap> fused_overlaps;
    fuse_overlaps(fused_overlaps, unfused_overlaps);

    ASSERT_EQ(fused_overlaps.size(), 0u);
}

TEST(TestCudamapperOverlapperTriggerred, Fusee3Overlapsto2)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;

    Overlap overlap1;
    overlap1.query_read_id_                 = 20;
    overlap1.target_read_id_                = 23;
    overlap1.query_start_position_in_read_  = 1000;
    overlap1.query_end_position_in_read_    = 2000;
    overlap1.target_start_position_in_read_ = 4000;
    overlap1.target_end_position_in_read_   = 5000;
    unfused_overlaps.push_back(overlap1);

    Overlap overlap2;
    overlap2.query_read_id_                 = 20;
    overlap2.target_read_id_                = 23;
    overlap2.query_start_position_in_read_  = 10000;
    overlap2.query_end_position_in_read_    = 12000;
    overlap2.target_start_position_in_read_ = 14000;
    overlap2.target_end_position_in_read_   = 15000;
    unfused_overlaps.push_back(overlap2);

    Overlap overlap3;
    overlap3.query_read_id_                 = 27;
    overlap3.target_read_id_                = 29;
    overlap3.query_start_position_in_read_  = 10000;
    overlap3.query_end_position_in_read_    = 12000;
    overlap3.target_start_position_in_read_ = 14000;
    overlap3.target_end_position_in_read_   = 15000;

    unfused_overlaps.push_back(overlap3);

    std::vector<Overlap> fused_overlaps;
    fuse_overlaps(fused_overlaps, unfused_overlaps);

    ASSERT_EQ(fused_overlaps.size(), 2u);
}

TEST(TestCudamapperOverlapperTriggerred, OneAchorNoOverlaps)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;
    thrust::device_vector<Anchor> anchors;

    MockIndex test_index;
    std::vector<std::string> testv;
    testv.push_back("READ0");
    testv.push_back("READ1");
    testv.push_back("READ2");
    std::vector<std::uint32_t> test_read_length(testv.size(), 1000);

    for (std::size_t i = 0; i < testv.size(); ++i)
    {
        EXPECT_CALL(test_index, read_id_to_read_name(i)).WillRepeatedly(testing::ReturnRef(testv[i]));
        EXPECT_CALL(test_index, read_id_to_read_length(i)).WillRepeatedly(testing::ReturnRef(test_read_length[i]));
    }

    Anchor anchor1;

    anchors.push_back(anchor1);

    std::vector<Overlap> overlaps;
    overlapper.get_overlaps(overlaps, anchors, test_index, test_index);
    ASSERT_EQ(overlaps.size(), 0u);
}

TEST(TestCudamapperOverlapperTriggerred, FourAnchorsOneOverlap)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;
    thrust::device_vector<Anchor> anchors;

    MockIndex test_index;
    std::vector<std::string> testv;
    testv.push_back("READ0");
    testv.push_back("READ1");
    testv.push_back("READ2");
    std::vector<std::uint32_t> test_read_length(testv.size(), 1000);

    for (std::size_t i = 0; i < testv.size(); ++i)
    {
        EXPECT_CALL(test_index, read_id_to_read_name(i)).WillRepeatedly(testing::ReturnRef(testv[i]));
        EXPECT_CALL(test_index, read_id_to_read_length(i)).WillRepeatedly(testing::ReturnRef(test_read_length[i]));
    }

    Anchor anchor1;
    anchor1.query_read_id_           = 1;
    anchor1.target_read_id_          = 2;
    anchor1.query_position_in_read_  = 100;
    anchor1.target_position_in_read_ = 1000;

    Anchor anchor2;
    anchor2.query_read_id_           = 1;
    anchor2.target_read_id_          = 2;
    anchor2.query_position_in_read_  = 200;
    anchor2.target_position_in_read_ = 1100;

    Anchor anchor3;
    anchor3.query_read_id_           = 1;
    anchor3.target_read_id_          = 2;
    anchor3.query_position_in_read_  = 300;
    anchor3.target_position_in_read_ = 1200;

    Anchor anchor4;
    anchor4.query_read_id_           = 1;
    anchor4.target_read_id_          = 2;
    anchor4.query_position_in_read_  = 400;
    anchor4.target_position_in_read_ = 1300;

    anchors.push_back(anchor1);
    anchors.push_back(anchor2);
    anchors.push_back(anchor3);
    anchors.push_back(anchor4);

    std::vector<Overlap> overlaps;
    overlapper.get_overlaps(overlaps, anchors, test_index, test_index);
    ASSERT_EQ(overlaps.size(), 1u);
    ASSERT_EQ(overlaps[0].query_read_id_, 1u);
    ASSERT_EQ(overlaps[0].target_read_id_, 2u);
    ASSERT_EQ(overlaps[0].query_start_position_in_read_, 100u);
    ASSERT_EQ(overlaps[0].query_end_position_in_read_, 400u);
    ASSERT_EQ(overlaps[0].target_start_position_in_read_, 1000u);
    ASSERT_EQ(overlaps[0].target_end_position_in_read_, 1300u);
}

TEST(TestCudamapperOverlapperTriggerred, FourAnchorsNoOverlap)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;
    thrust::device_vector<Anchor> anchors;

    MockIndex test_index;
    std::vector<std::string> testv;
    testv.push_back("READ0");
    testv.push_back("READ1");
    testv.push_back("READ2");
    std::vector<std::uint32_t> test_read_length(testv.size(), 1000);

    for (std::size_t i = 0; i < testv.size(); ++i)
    {
        EXPECT_CALL(test_index, read_id_to_read_name(i)).WillRepeatedly(testing::ReturnRef(testv[i]));
        EXPECT_CALL(test_index, read_id_to_read_length(i)).WillRepeatedly(testing::ReturnRef(test_read_length[i]));
    }

    Anchor anchor1;
    anchor1.query_read_id_           = 1;
    anchor1.target_read_id_          = 2;
    anchor1.query_position_in_read_  = 100;
    anchor1.target_position_in_read_ = 1000;

    Anchor anchor2;
    anchor2.query_read_id_           = 3;
    anchor2.target_read_id_          = 4;
    anchor2.query_position_in_read_  = 200;
    anchor2.target_position_in_read_ = 1100;

    Anchor anchor3;
    anchor3.query_read_id_           = 5;
    anchor3.target_read_id_          = 6;
    anchor3.query_position_in_read_  = 300;
    anchor3.target_position_in_read_ = 1200;

    Anchor anchor4;
    anchor4.query_read_id_           = 8;
    anchor4.target_read_id_          = 9;
    anchor4.query_position_in_read_  = 400;
    anchor4.target_position_in_read_ = 1300;

    anchors.push_back(anchor1);
    anchors.push_back(anchor2);
    anchors.push_back(anchor3);
    anchors.push_back(anchor4);

    std::vector<Overlap> overlaps;
    overlapper.get_overlaps(overlaps, anchors, test_index, test_index);
    ASSERT_EQ(overlaps.size(), 0u);
}

TEST(TestCudamapperOverlapperTriggerred, FourColinearAnchorsOneOverlap)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;
    thrust::device_vector<Anchor> anchors;

    MockIndex test_index;
    std::vector<std::string> testv;
    testv.push_back("READ0");
    testv.push_back("READ1");
    testv.push_back("READ2");
    std::vector<std::uint32_t> test_read_length(testv.size(), 1000);

    for (std::size_t i = 0; i < testv.size(); ++i)
    {
        EXPECT_CALL(test_index, read_id_to_read_name(i)).WillRepeatedly(testing::ReturnRef(testv[i]));
        EXPECT_CALL(test_index, read_id_to_read_length(i)).WillRepeatedly(testing::ReturnRef(test_read_length[i]));
    }

    Anchor anchor1;
    anchor1.query_read_id_           = 1;
    anchor1.target_read_id_          = 2;
    anchor1.query_position_in_read_  = 100;
    anchor1.target_position_in_read_ = 1000;

    Anchor anchor2;
    anchor2.query_read_id_           = 1;
    anchor2.target_read_id_          = 2;
    anchor2.query_position_in_read_  = 200 * 10;
    anchor2.target_position_in_read_ = 1100 * 10;

    Anchor anchor3;
    anchor3.query_read_id_           = 1;
    anchor3.target_read_id_          = 2;
    anchor3.query_position_in_read_  = 300 * 10;
    anchor3.target_position_in_read_ = 1200 * 10;

    Anchor anchor4;
    anchor4.query_read_id_           = 1;
    anchor4.target_read_id_          = 2;
    anchor4.query_position_in_read_  = 400 * 10;
    anchor4.target_position_in_read_ = 1300 * 10;

    anchors.push_back(anchor1);
    anchors.push_back(anchor2);
    anchors.push_back(anchor3);
    anchors.push_back(anchor4);

    std::vector<Overlap> overlaps;
    overlapper.get_overlaps(overlaps, anchors, test_index, test_index);
    ASSERT_EQ(overlaps.size(), 0u);
}

TEST(TestCudamapperOverlapperTriggerred, FourAnchorsLastNotInOverlap)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;
    thrust::device_vector<Anchor> anchors;

    MockIndex test_index;
    std::vector<std::string> testv;
    testv.push_back("READ0");
    testv.push_back("READ1");
    testv.push_back("READ2");
    std::vector<std::uint32_t> test_read_length(testv.size(), 1000);

    for (std::size_t i = 0; i < testv.size(); ++i)
    {
        EXPECT_CALL(test_index, read_id_to_read_name(i)).WillRepeatedly(testing::ReturnRef(testv[i]));
        EXPECT_CALL(test_index, read_id_to_read_length(i)).WillRepeatedly(testing::ReturnRef(test_read_length[i]));
    }

    Anchor anchor1;
    anchor1.query_read_id_           = 1;
    anchor1.target_read_id_          = 2;
    anchor1.query_position_in_read_  = 100;
    anchor1.target_position_in_read_ = 1000;

    Anchor anchor2;
    anchor2.query_read_id_           = 1;
    anchor2.target_read_id_          = 2;
    anchor2.query_position_in_read_  = 200;
    anchor2.target_position_in_read_ = 1100;

    Anchor anchor3;
    anchor3.query_read_id_           = 1;
    anchor3.target_read_id_          = 2;
    anchor3.query_position_in_read_  = 300;
    anchor3.target_position_in_read_ = 1200;

    Anchor anchor4;
    anchor4.query_read_id_           = 1;
    anchor4.target_read_id_          = 2;
    anchor4.query_position_in_read_  = 400 + 2000;
    anchor4.target_position_in_read_ = 1300 + 2000;

    anchors.push_back(anchor1);
    anchors.push_back(anchor2);
    anchors.push_back(anchor3);
    anchors.push_back(anchor4);

    std::vector<Overlap> overlaps;
    overlapper.get_overlaps(overlaps, anchors, test_index, test_index);
    ASSERT_EQ(overlaps.size(), 1u);
    ASSERT_EQ(overlaps[0].query_read_id_, 1u);
    ASSERT_EQ(overlaps[0].target_read_id_, 2u);
    ASSERT_EQ(overlaps[0].query_start_position_in_read_, 100u);
    ASSERT_EQ(overlaps[0].query_end_position_in_read_, 300u);
    ASSERT_EQ(overlaps[0].target_start_position_in_read_, 1000u);
    ASSERT_EQ(overlaps[0].target_end_position_in_read_, 1200u);
}

TEST(TestCudamapperOverlapperTriggerred, ShuffledAnchors)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;
    thrust::device_vector<Anchor> anchors;

    MockIndex test_index;
    std::vector<std::string> testv;
    testv.push_back("READ0");
    testv.push_back("READ1");
    testv.push_back("READ2");
    std::vector<std::uint32_t> test_read_length(testv.size(), 1000);

    for (std::size_t i = 0; i < testv.size(); ++i)
    {
        EXPECT_CALL(test_index, read_id_to_read_name(i)).WillRepeatedly(testing::ReturnRef(testv[i]));
        EXPECT_CALL(test_index, read_id_to_read_length(i)).WillRepeatedly(testing::ReturnRef(test_read_length[i]));
    }

    Anchor anchor1;
    anchor1.query_read_id_           = 1;
    anchor1.target_read_id_          = 2;
    anchor1.query_position_in_read_  = 100;
    anchor1.target_position_in_read_ = 1000;

    Anchor anchor2;
    anchor2.query_read_id_           = 1;
    anchor2.target_read_id_          = 2;
    anchor2.query_position_in_read_  = 200;
    anchor2.target_position_in_read_ = 1100;

    Anchor anchor3;
    anchor3.query_read_id_           = 1;
    anchor3.target_read_id_          = 2;
    anchor3.query_position_in_read_  = 300;
    anchor3.target_position_in_read_ = 1200;

    Anchor anchor4;
    anchor4.query_read_id_           = 1;
    anchor4.target_read_id_          = 2;
    anchor4.query_position_in_read_  = 400 + 2000;
    anchor4.target_position_in_read_ = 1300 + 2000;

    // This anchor has the same query_id, target_id and query position as anchor 3 - should not affect result at all.
    // because it's target id is lower
    Anchor anchor5;
    anchor5.query_read_id_           = 1;
    anchor5.target_read_id_          = 2;
    anchor5.query_position_in_read_  = 300;
    anchor5.target_position_in_read_ = 1050;

    anchors.push_back(anchor1);
    anchors.push_back(anchor2);
    anchors.push_back(anchor3);
    anchors.push_back(anchor4);
    anchors.push_back(anchor5);

    auto rng = std::default_random_engine{};
    rng.seed(2);
    //Shuffle the anchors 100 times and check that the generated overlaps are always the same.
    for (size_t i = 0; i < 100; i++)
    {
        std::vector<Overlap> overlaps;
        overlapper.get_overlaps(overlaps, anchors, test_index, test_index);
        std::shuffle(std::begin(overlaps), std::end(overlaps), rng);
        ASSERT_EQ(overlaps.size(), 1u);
        ASSERT_EQ(overlaps[0].query_read_id_, 1u);
        ASSERT_EQ(overlaps[0].target_read_id_, 2u);
        ASSERT_EQ(overlaps[0].query_start_position_in_read_, 100u);
        ASSERT_EQ(overlaps[0].query_end_position_in_read_, 300u);
        ASSERT_EQ(overlaps[0].target_start_position_in_read_, 1000u);
        ASSERT_EQ(overlaps[0].target_end_position_in_read_, 1200u);
    }
}

TEST(TestCudamapperOverlapperTriggerred, ReverseStrand)
{
    OverlapperTriggered overlapper;

    std::vector<Overlap> unfused_overlaps;
    thrust::device_vector<Anchor> anchors;

    MockIndex test_index;
    std::vector<std::string> testv;
    testv.push_back("READ0");
    testv.push_back("READ1");
    testv.push_back("READ2");
    std::vector<std::uint32_t> test_read_length(testv.size(), 1000);

    for (std::size_t i = 0; i < testv.size(); ++i)
    {
        EXPECT_CALL(test_index, read_id_to_read_name(i)).WillRepeatedly(testing::ReturnRef(testv[i]));
        EXPECT_CALL(test_index, read_id_to_read_length(i)).WillRepeatedly(testing::ReturnRef(test_read_length[i]));
    }

    Anchor anchor1;
    anchor1.query_read_id_           = 1;
    anchor1.target_read_id_          = 2;
    anchor1.query_position_in_read_  = 100;
    anchor1.target_position_in_read_ = 1300;

    Anchor anchor2;
    anchor2.query_read_id_           = 1;
    anchor2.target_read_id_          = 2;
    anchor2.query_position_in_read_  = 200;
    anchor2.target_position_in_read_ = 1200;

    Anchor anchor3;
    anchor3.query_read_id_           = 1;
    anchor3.target_read_id_          = 2;
    anchor3.query_position_in_read_  = 300;
    anchor3.target_position_in_read_ = 1100;

    Anchor anchor4;
    anchor4.query_read_id_           = 1;
    anchor4.target_read_id_          = 2;
    anchor4.query_position_in_read_  = 400;
    anchor4.target_position_in_read_ = 1000;

    anchors.push_back(anchor1);
    anchors.push_back(anchor2);
    anchors.push_back(anchor3);
    anchors.push_back(anchor4);

    std::vector<Overlap> overlaps;
    overlapper.get_overlaps(overlaps, anchors, test_index, test_index);
    ASSERT_EQ(overlaps.size(), 1u);
    ASSERT_GT(overlaps[0].target_end_position_in_read_, overlaps[0].target_start_position_in_read_);
    ASSERT_EQ(overlaps[0].relative_strand, RelativeStrand::Reverse);
    ASSERT_EQ(char(overlaps[0].relative_strand), '-');
}

} // namespace cudamapper
} // namespace claragenomics

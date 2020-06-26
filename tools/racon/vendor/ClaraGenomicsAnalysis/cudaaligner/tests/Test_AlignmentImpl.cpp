/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "../src/alignment_impl.hpp"

#include <claragenomics/utils/signed_integer_utils.hpp>

#include "gtest/gtest.h"
#include <memory>

namespace claragenomics
{

namespace cudaaligner
{

using ::testing::ValuesIn;

// Individual tests
TEST(TestAlignmentImplIndividual, Status)
{
    std::unique_ptr<AlignmentImpl> alignment_ = std::make_unique<AlignmentImpl>("A", 1, "T", 1);
    ASSERT_EQ(StatusType::uninitialized, alignment_->get_status()) << "Initial status incorrect";

    alignment_->set_status(StatusType::success);
    ASSERT_EQ(StatusType::success, alignment_->get_status()) << "Status not set properly";
}

TEST(TestAlignmentImplIndividual, Type)
{
    std::unique_ptr<AlignmentImpl> alignment_ = std::make_unique<AlignmentImpl>("A", 1, "T", 1);
    ASSERT_EQ(AlignmentType::unset, alignment_->get_alignment_type()) << "Initial type incorrect";

    alignment_->set_alignment_type(AlignmentType::global_alignment);
    ASSERT_EQ(AlignmentType::global_alignment, alignment_->get_alignment_type()) << "Type not set properly";
}

// Parametrized tests
typedef struct AlignmentTestData
{
    std::string query;
    std::string target;
    std::vector<AlignmentState> alignment;
    FormattedAlignment formatted_alignment;
    std::string cigar;
} AlignmentTestData;

std::vector<AlignmentTestData> create_alignment_test_cases()
{
    std::vector<AlignmentTestData> test_cases;
    AlignmentTestData data;

    // Test case 1
    data.query     = "AAAA";
    data.target    = "TTATG";
    data.alignment = {
        AlignmentState::mismatch,
        AlignmentState::mismatch,
        AlignmentState::match,
        AlignmentState::mismatch,
        AlignmentState::insertion};
    data.formatted_alignment = std::make_pair("AAAA-", "TTATG");
    data.cigar               = "4M1I";
    test_cases.push_back(data);

    // Test case 2
    data.query     = "CGATAATG";
    data.target    = "CATAA";
    data.alignment = {
        AlignmentState::deletion,
        AlignmentState::mismatch,
        AlignmentState::match,
        AlignmentState::match,
        AlignmentState::match,
        AlignmentState::match,
        AlignmentState::deletion,
        AlignmentState::deletion};
    data.formatted_alignment = std::make_pair("CGATAATG", "-CATAA--");
    data.cigar               = "1D5M2D";
    test_cases.push_back(data);

    // Test case 3
    data.query     = "GTTAG";
    data.target    = "AAGTCTAGAA";
    data.alignment = {
        AlignmentState::insertion,
        AlignmentState::insertion,
        AlignmentState::match,
        AlignmentState::match,
        AlignmentState::insertion,
        AlignmentState::match,
        AlignmentState::match,
        AlignmentState::match,
        AlignmentState::insertion,
        AlignmentState::insertion,
    };
    data.formatted_alignment = std::make_pair("--GT-TAG--", "AAGTCTAGAA");
    data.cigar               = "2I2M1I3M2I";
    test_cases.push_back(data);

    // Test case 4
    data.query     = "GTTACA";
    data.target    = "GATTCA";
    data.alignment = {
        AlignmentState::match,
        AlignmentState::insertion,
        AlignmentState::match,
        AlignmentState::match,
        AlignmentState::deletion,
        AlignmentState::match,
        AlignmentState::match};
    data.formatted_alignment = std::make_pair("G-TTACA", "GATT-CA");
    data.cigar               = "1M1I2M1D2M";
    test_cases.push_back(data);

    return test_cases;
};

class TestAlignmentImpl : public ::testing::TestWithParam<AlignmentTestData>
{
public:
    void SetUp()
    {
        param_     = GetParam();
        alignment_ = std::make_unique<AlignmentImpl>(param_.query.c_str(),
                                                     param_.query.size(),
                                                     param_.target.c_str(),
                                                     param_.target.size());
        alignment_->set_alignment(param_.alignment);
    }

protected:
    std::unique_ptr<AlignmentImpl> alignment_;
    AlignmentTestData param_;
};

TEST_P(TestAlignmentImpl, StringGetters)
{
    ASSERT_EQ(param_.query, alignment_->get_query_sequence()) << "Query doesn't match original string";
    ASSERT_EQ(param_.target, alignment_->get_target_sequence()) << "Target doesn't match original string";
}

TEST_P(TestAlignmentImpl, AlignmentState)
{
    const std::vector<AlignmentState>& al_read = alignment_->get_alignment();
    ASSERT_EQ(param_.alignment.size(), al_read.size());
    for (int64_t i = 0; i < get_size(param_.alignment); i++)
    {
        ASSERT_EQ(param_.alignment[i], al_read[i]);
    }
}

TEST_P(TestAlignmentImpl, AlignmentFormatting)
{
    FormattedAlignment formatted_alignment = alignment_->format_alignment();
    std::string query                      = formatted_alignment.first;
    std::string target                     = formatted_alignment.second;
    ASSERT_EQ(param_.formatted_alignment.first, query);
    ASSERT_EQ(param_.formatted_alignment.second, target);
}

TEST_P(TestAlignmentImpl, CigarFormatting)
{
    std::string cigar = alignment_->convert_to_cigar();
    ASSERT_EQ(param_.cigar, cigar);
}

INSTANTIATE_TEST_SUITE_P(TestAlignment, TestAlignmentImpl, ValuesIn(create_alignment_test_cases()));
} // namespace cudaaligner
} // namespace claragenomics

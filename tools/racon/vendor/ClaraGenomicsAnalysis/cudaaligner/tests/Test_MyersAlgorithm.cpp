/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "../src/myers_gpu.cuh"
#include "../src/needleman_wunsch_cpu.hpp"

#include <claragenomics/utils/genomeutils.hpp>

#include <random>
#include <gtest/gtest.h>

namespace claragenomics
{

namespace cudaaligner
{

struct TestCaseData
{
    std::string target;
    std::string query;
    int32_t edit_distance;
};

std::vector<TestCaseData> create_myers_test_cases()
{
    std::vector<TestCaseData> tests;

    TestCaseData t;

    t.target        = "AAAAAAAAAA";
    t.query         = "CGTCGTCGTC";
    t.edit_distance = 10;
    tests.push_back(t);

    t.target        = "AATAATAATA";
    t.query         = "CGTCGTCGTC";
    t.edit_distance = 7;
    tests.push_back(t);

    t.target        = "AATAATAATA";
    t.query         = "";
    t.edit_distance = 10;
    tests.push_back(t);

    t.target        = "";
    t.query         = "CGTCGTCGTC";
    t.edit_distance = 10;
    tests.push_back(t);

    t.target        = "AATAATAATA";
    t.query         = "C";
    t.edit_distance = 10;
    tests.push_back(t);

    t.target        = "CGTCGTCGTC";
    t.query         = "CGTCGTCGTC";
    t.edit_distance = 0;
    tests.push_back(t);

    t.target        = "CGTCGTCGTCCGTCGTCGTCCGTCGTCGTCGT";
    t.query         = "AGTCGTCGTCCGTAATCGTCCGTCGTCGTCGA";
    t.edit_distance = 4;
    tests.push_back(t);

    t.target        = "CGTCGTCGTCCGTCGTCGTCCGTCGTCGTCGTC";
    t.query         = "AGTCGTCGTCCGTAATCGTCCGTCGTCGTCGTA";
    t.edit_distance = 4;
    tests.push_back(t);

    t.target        = "GTCGTCGTCCGTCGTCGTCCGTCGTCGTCGTCGTCGTCGTCCGTCGTCGTCCGTCGTCGTCGTCGTCGTCGTCCGTCGTCGTCCGTCGTCGTCGTC";
    t.query         = "GTCGTCGTCCGTCGTCGTCCGTCGTCGTCGAAAACGTCGTCCGTCGTCGTCCGTCGTCGAAAACGTCGTCGTCCGTAGTCGTCCGACGTCGTCGTC";
    t.edit_distance = 10;
    tests.push_back(t);

    t.target        = "GTCGTCGTCCGTCGTCGTCCGTCGTCGTCGTCGTCGTCGTCCGTCGTCGTCCGTCGTCGTCGTCGTCGTCGTCCGTCGTCGTCCGTCGTCGTCGTC";
    t.query         = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
    t.edit_distance = 96;
    tests.push_back(t);

    std::minstd_rand rng(1);
    t.target        = claragenomics::genomeutils::generate_random_genome(5000, rng);
    t.query         = claragenomics::genomeutils::generate_random_genome(4800, rng);
    matrix<int> s   = needleman_wunsch_build_score_matrix_naive(t.target, t.query);
    t.edit_distance = s(s.num_rows() - 1, s.num_cols() - 1);
    tests.push_back(t);
    return tests;
}

class TestMyersEditDistance : public ::testing::TestWithParam<TestCaseData>
{
};

TEST_P(TestMyersEditDistance, TestCases)
{
    TestCaseData t = GetParam();

    int32_t d = myers_compute_edit_distance(t.target, t.query);
    ASSERT_EQ(d, t.edit_distance);
}

class TestMyersScoreMatrix : public ::testing::TestWithParam<TestCaseData>
{
};

TEST_P(TestMyersScoreMatrix, TestCases)
{
    TestCaseData t = GetParam();

    matrix<int32_t> m = myers_get_full_score_matrix(t.target, t.query);
    matrix<int32_t> r = needleman_wunsch_build_score_matrix_naive(t.target, t.query);

    ASSERT_EQ(m.num_rows(), r.num_rows());
    ASSERT_EQ(m.num_cols(), r.num_cols());

    for (int32_t j = 0; j < m.num_cols(); ++j)
    {
        for (int32_t i = 0; i < m.num_rows(); ++i)
        {
            EXPECT_EQ(m(i, j), r(i, j)) << "index: (" << i << "," << j << ")";
        }
    }
}

INSTANTIATE_TEST_SUITE_P(TestMyersAlgorithm, TestMyersEditDistance, ::testing::ValuesIn(create_myers_test_cases()));
INSTANTIATE_TEST_SUITE_P(TestMyersAlgorithm, TestMyersScoreMatrix, ::testing::ValuesIn(create_myers_test_cases()));

} // namespace cudaaligner
} // namespace claragenomics

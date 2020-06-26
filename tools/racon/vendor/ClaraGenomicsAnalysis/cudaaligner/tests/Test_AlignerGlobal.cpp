/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "../src/aligner_global_ukkonen.hpp"
#include "../src/aligner_global_myers.hpp"
#include "../src/aligner_global_hirschberg_myers.hpp"

#include <claragenomics/cudaaligner/alignment.hpp>
#include <claragenomics/utils/signed_integer_utils.hpp>
#include <claragenomics/utils/genomeutils.hpp>

#include <random>
#include "gtest/gtest.h"

namespace claragenomics
{

namespace cudaaligner
{

enum class AlignmentAlgorithm
{
    Default = 0,
    Ukkonen,
    Myers,
    HirschbergMyers
};

std::string get_algorithm_name(AlignmentAlgorithm x)
{
    switch (x)
    {
    case AlignmentAlgorithm::Default: return "Default";
    case AlignmentAlgorithm::Ukkonen: return "Ukkonen";
    case AlignmentAlgorithm::Myers: return "Myers";
    case AlignmentAlgorithm::HirschbergMyers: return "Hirschberg + Myers";
    default: return "";
    }
}

// Common data structures and functions.
struct AlignerTestData
{
    std::vector<std::pair<std::string, std::string>> inputs;
    std::vector<std::string> cigars;
    AlignmentAlgorithm algorithm = AlignmentAlgorithm::Ukkonen;
};

// Test adding alignments to Aligner objects
TEST(TestCudaAligner, TestAlignmentAddition)
{
    std::unique_ptr<AlignerGlobal> aligner = std::make_unique<AlignerGlobalUkkonen>(10, 10, 5, nullptr, 0);
    ASSERT_EQ(StatusType::success, aligner->add_alignment("ATCG", 4, "TACG", 4));
    ASSERT_EQ(StatusType::success, aligner->add_alignment("ATCG", 4, "TACG", 4));
    ASSERT_EQ(StatusType::success, aligner->add_alignment("ATCG", 4, "TACG", 4));

    ASSERT_EQ(3, aligner->num_alignments());

    ASSERT_EQ(StatusType::exceeded_max_length, aligner->add_alignment("ATCGATTACGC", 11, "TACGTACGGA", 10));
    ASSERT_EQ(StatusType::exceeded_max_length, aligner->add_alignment("ATCGATTACG", 10, "ATACGTAGCGA", 11));

    ASSERT_EQ(3, aligner->num_alignments());

    ASSERT_EQ(StatusType::success, aligner->add_alignment("ATCG", 4, "TACG", 4));
    ASSERT_EQ(StatusType::success, aligner->add_alignment("ATCG", 4, "TACG", 4));

    ASSERT_EQ(5, aligner->num_alignments());

    ASSERT_EQ(StatusType::exceeded_max_alignments, aligner->add_alignment("ATCG", 4, "TACG", 4));

    ASSERT_EQ(5, aligner->num_alignments());
}

// Test correctness of genome alignment.
std::vector<AlignerTestData> create_aligner_test_cases()
{
    std::vector<AlignerTestData> test_cases;
    AlignerTestData data;

    // Test case 1
    data.inputs    = {{"AAAA", "TTAT"}};
    data.cigars    = {"4M"};
    data.algorithm = AlignmentAlgorithm::Default;
    test_cases.push_back(data);

    // Test case 2
    data.inputs    = {{"ATAAAAAAAA", "AAAAAAAAA"}};
    data.cigars    = {"1M1D8M"};
    data.algorithm = AlignmentAlgorithm::Default;
    test_cases.push_back(data);

    // Test case 3
    data.inputs    = {{"AAAAAAAAA", "ATAAAAAAAA"}};
    data.cigars    = {"1M1I8M"};
    data.algorithm = AlignmentAlgorithm::Default;
    test_cases.push_back(data);

    // Test case 4
    data.inputs    = {{"ACTGA", "GCTAG"}};
    data.cigars    = {"3M1D1M1I"};
    data.algorithm = AlignmentAlgorithm::Default;
    test_cases.push_back(data);

    // Test case 5
    data.inputs    = {{"ACTGA", "GCTAG"}, {"ACTG", "ACTG"}, {"A", "T"}};
    data.cigars    = {"3M1D1M1I", "4M", "1M"};
    data.algorithm = AlignmentAlgorithm::Default;
    test_cases.push_back(data);

    // Test case 6
    data.inputs = {
        {"AAAA", "TTAT"}, {"ATAAAAAAAA", "AAAAAAAAA"}, {"AAAAAAAAA", "ATAAAAAAAA"}, {"ACTGA", "GCTAG"}, {"ACTGA", "GCTAG"}, {"ACTG", "ACTG"}, {"A", "T"}, {"AAAA", "TTAT"}, {"ATAAAAAAAA", "AAAAAAAAA"}, {"AAAAAAAAA", "ATAAAAAAAA"}, {"ACTGA", "GCTAG"}, {"ACTGA", "GCTAG"}, {"ACTG", "ACTG"}, {"A", "T"}, {"AAAA", "TTAT"}, {"ATAAAAAAAA", "AAAAAAAAA"}, {"AAAAAAAAA", "ATAAAAAAAA"}, {"ACTGA", "GCTAG"}, {"ACTGA", "GCTAG"}, {"ACTG", "ACTG"}, {"A", "T"}, {"AAAA", "TTAT"}, {"ATAAAAAAAA", "AAAAAAAAA"}, {"AAAAAAAAA", "ATAAAAAAAA"}, {"ACTGA", "GCTAG"}, {"ACTGA", "GCTAG"}, {"ACTG", "ACTG"}, {"A", "T"}};
    data.cigars = {
        "4M", "1M1D8M", "1M1I8M", "3M1D1M1I", "3M1D1M1I", "4M", "1M",
        "4M", "1M1D8M", "1M1I8M", "3M1D1M1I", "3M1D1M1I", "4M", "1M",
        "4M", "1M1D8M", "1M1I8M", "3M1D1M1I", "3M1D1M1I", "4M", "1M",
        "4M", "1M1D8M", "1M1I8M", "3M1D1M1I", "3M1D1M1I", "4M", "1M"};
    data.algorithm = AlignmentAlgorithm::Default;
    test_cases.push_back(data);

    std::minstd_rand rng(1);
    data.inputs    = {{claragenomics::genomeutils::generate_random_genome(4800, rng), claragenomics::genomeutils::generate_random_genome(5000, rng)}};
    data.cigars    = {}; // do not test cigars
    data.algorithm = AlignmentAlgorithm::Default;
    test_cases.push_back(data);

    std::vector<AlignerTestData> test_cases_final;
    test_cases_final.reserve(4 * test_cases.size());
    test_cases_final.insert(test_cases_final.end(), test_cases.begin(), test_cases.end());
    std::transform(test_cases.begin(), test_cases.end(), std::back_inserter(test_cases_final), [](AlignerTestData td) { td.algorithm = AlignmentAlgorithm::Ukkonen; return td; });
    std::transform(test_cases.begin(), test_cases.end(), std::back_inserter(test_cases_final), [](AlignerTestData td) { td.algorithm = AlignmentAlgorithm::Myers; return td; });
    std::transform(test_cases.begin(), test_cases.end(), std::back_inserter(test_cases_final), [](AlignerTestData td) { td.algorithm = AlignmentAlgorithm::HirschbergMyers; return td; });

    return test_cases_final;
};

class TestAlignerGlobal : public ::testing::TestWithParam<AlignerTestData>
{
};

int32_t get_max_sequence_length(std::vector<std::pair<std::string, std::string>> const& inputs)
{
    int64_t max_string_size = 0;
    for (auto const& pair : inputs)
    {
        max_string_size = std::max(max_string_size, get_size(pair.first));
        max_string_size = std::max(max_string_size, get_size(pair.second));
    }
    return static_cast<int32_t>(max_string_size);
}

TEST_P(TestAlignerGlobal, TestAlignmentKernel)
{
    AlignerTestData param                                          = GetParam();
    const std::vector<std::pair<std::string, std::string>>& inputs = param.inputs;
    const std::vector<std::string>& cigars                         = param.cigars;

    if (!cigars.empty())
    {
        ASSERT_EQ(inputs.size(), cigars.size()) << "Input data length mismatch";
    }

    const int32_t max_string_size = get_max_sequence_length(inputs) + 1;
    std::unique_ptr<Aligner> aligner;
    switch (param.algorithm)
    {
    case AlignmentAlgorithm::Default:
        aligner = claragenomics::cudaaligner::create_aligner(max_string_size,
                                                             max_string_size,
                                                             param.inputs.size(),
                                                             claragenomics::cudaaligner::AlignmentType::global_alignment,
                                                             nullptr,
                                                             0);
    case AlignmentAlgorithm::Ukkonen:
        aligner = std::make_unique<AlignerGlobalUkkonen>(max_string_size,
                                                         max_string_size,
                                                         param.inputs.size(),
                                                         nullptr,
                                                         0);
        break;
    case AlignmentAlgorithm::HirschbergMyers:
        aligner = std::make_unique<AlignerGlobalHirschbergMyers>(max_string_size,
                                                                 max_string_size,
                                                                 param.inputs.size(),
                                                                 nullptr,
                                                                 0);
        break;
    default:
    case AlignmentAlgorithm::Myers:
        aligner = std::make_unique<AlignerGlobalMyers>(max_string_size,
                                                       max_string_size,
                                                       param.inputs.size(),
                                                       nullptr,
                                                       0);
    }
    for (auto& pair : inputs)
    {
        auto& query  = pair.first;
        auto& target = pair.second;
        ASSERT_EQ(StatusType::success, aligner->add_alignment(query.c_str(), query.length(),
                                                              target.c_str(), target.length()))
            << "Could not add alignment to aligner";
    }

    aligner->align_all();
    aligner->sync_alignments();

    const std::vector<std::shared_ptr<Alignment>>& alignments = aligner->get_alignments();
    ASSERT_EQ(get_size(alignments), get_size(inputs));
    for (int32_t a = 0; a < get_size(alignments); a++)
    {
        auto alignment = alignments[a];
        EXPECT_EQ(StatusType::success, alignment->get_status()) << "Alignment status is not success";
        EXPECT_EQ(AlignmentType::global_alignment, alignment->get_alignment_type()) << "Alignment type is not global";
        if (!cigars.empty())
        {
            EXPECT_EQ(cigars[a], alignment->convert_to_cigar()) << "CIGAR doesn't match for alignment of\n"
                                                                << alignment->get_query_sequence()
                                                                << "\nand\n"
                                                                << alignment->get_target_sequence()
                                                                << "\nindex: " << a
                                                                << "\nusing " << get_algorithm_name(param.algorithm);
        }
    }
}

INSTANTIATE_TEST_SUITE_P(TestCudaAligner, TestAlignerGlobal, ::testing::ValuesIn(create_aligner_test_cases()));

// Test performance of kernel for large genomes
std::vector<AlignerTestData> create_aligner_perf_test_cases()
{
    std::vector<AlignerTestData> test_cases;
    AlignerTestData data;

    // Test case 1
    std::minstd_rand rng(1);
    data.inputs = {{claragenomics::genomeutils::generate_random_genome(1000, rng), claragenomics::genomeutils::generate_random_genome(1000, rng)}};
    test_cases.push_back(data);

    // Test case 2
    data.inputs = {{claragenomics::genomeutils::generate_random_genome(9500, rng), claragenomics::genomeutils::generate_random_genome(9000, rng)},
                   {claragenomics::genomeutils::generate_random_genome(3456, rng), claragenomics::genomeutils::generate_random_genome(3213, rng)},
                   {claragenomics::genomeutils::generate_random_genome(20000, rng), claragenomics::genomeutils::generate_random_genome(20000, rng)},
                   {claragenomics::genomeutils::generate_random_genome(15000, rng), claragenomics::genomeutils::generate_random_genome(14000, rng)}};
    test_cases.push_back(data);

    return test_cases;
};

class TestAlignerGlobalImplPerf : public TestAlignerGlobal
{
};

TEST_P(TestAlignerGlobalImplPerf, TestAlignmentKernelPerf)
{
    AlignerTestData param                                          = GetParam();
    const std::vector<std::pair<std::string, std::string>>& inputs = param.inputs;
    const int32_t max_string_size                                  = get_max_sequence_length(inputs) + 1;
    std::unique_ptr<Aligner> aligner                               = std::make_unique<AlignerGlobalUkkonen>(max_string_size,
                                                                              max_string_size,
                                                                              param.inputs.size(),
                                                                              nullptr,
                                                                              0);

    for (auto& pair : inputs)
    {
        auto& query  = pair.first;
        auto& target = pair.second;
        ASSERT_EQ(StatusType::success, aligner->add_alignment(query.c_str(), query.length(),
                                                              target.c_str(), target.length()));
    }

    aligner->align_all();
    aligner->sync_alignments();

    const std::vector<std::shared_ptr<Alignment>>& alignments = aligner->get_alignments();
    ASSERT_EQ(alignments.size(), inputs.size());
}

INSTANTIATE_TEST_SUITE_P(TestCudaAligner, TestAlignerGlobalImplPerf, ::testing::ValuesIn(create_aligner_perf_test_cases()));
} // namespace cudaaligner
} // namespace claragenomics

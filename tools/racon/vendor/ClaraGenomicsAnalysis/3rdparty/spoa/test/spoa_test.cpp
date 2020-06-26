/*!
 * @file spoa_test.cpp
 *
 * @brief Spoa unit test source file
 */

#include "spoa_test_config.h"

#include "sequence.hpp"

#include "spoa/spoa.hpp"
#include "bioparser/bioparser.hpp"
#include "gtest/gtest.h"

class SpoaAlignmentTest: public ::testing::Test {
public:
    void SetUp(const std::string& file_name, spoa::AlignmentType alignment_type,
        std::int8_t m, std::int8_t n, std::int8_t g, std::int8_t e,
        std::int8_t q, std::int8_t c) {

        parser = bioparser::createParser<bioparser::FastqParser, spoa::Sequence>(
            file_name);
        alignment_engine = spoa::createAlignmentEngine(alignment_type, m, n, g,
            e, q, c);
        graph = spoa::createGraph();
    }

    void TearDown() {}

    void initialize() {
        parser->parse(sequences, -1);

        std::size_t max_sequence_size = 0;
        for (const auto& it: sequences) {
            max_sequence_size = std::max(max_sequence_size, it->data().size());
        }
        alignment_engine->prealloc(max_sequence_size, 4);
    }

    void construct_partial_order_graph(bool use_qualities) {
        for (const auto& it: sequences) {
            auto alignment = alignment_engine->align(it->data(), graph);

            if (use_qualities) {
                graph->add_alignment(alignment, it->data(), it->quality());
            } else {
                graph->add_alignment(alignment, it->data());
            }
        }
    }

    std::vector<std::unique_ptr<spoa::Sequence>> sequences;
    std::unique_ptr<bioparser::Parser<spoa::Sequence>> parser;
    std::unique_ptr<spoa::AlignmentEngine> alignment_engine;
    std::unique_ptr<spoa::Graph> graph;
};

TEST(SpoaTest, AlignmentTypeError) {
    try {
        auto alignment_engine = spoa::createAlignmentEngine(
            static_cast<spoa::AlignmentType>(4), 1, -1, -1);
    } catch(std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[spoa::createAlignmentEngine] error: "
            "invalid alignment type!");
    }
}

TEST(SpoaTest, EmptyInputError) {
    auto alignment_engine = spoa::createAlignmentEngine(
        static_cast<spoa::AlignmentType>(0), 1, -1, -1);
    auto graph = spoa::createGraph();
    auto alignment = alignment_engine->align("", graph);

    EXPECT_TRUE(alignment.empty());
}

TEST_F(SpoaAlignmentTest, GraphClear) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(false);

    auto consensus = graph->generate_consensus();

    graph->clear();
    construct_partial_order_graph(false);

    auto test = graph->generate_consensus();

    EXPECT_TRUE(consensus.compare(test) == 0);
}

TEST_F(SpoaAlignmentTest, LocalConsensus) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(false);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "AATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGA"
        "CCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGG"
        "GAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGC"
        "AGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGT"
        "ACTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCGC"
        "ACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGTT"
        "GAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGATA"
        "CGCTTTACACGCGCAACCAAGGATTTCGG";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, LocalAffineConsensus) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -6, -8 ,-6);

    initialize();
    construct_partial_order_graph(false);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "AATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGA"
        "CCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGG"
        "GAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGC"
        "AGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGT"
        "ACTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCGC"
        "ACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGTT"
        "GAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGATA"
        "CGCTTTACACGCGCAACCAAGGATTTCGG";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, LocalConvexConsensus) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(false);

    auto consensus = graph->generate_consensus();

    std::string valid_result =  "AATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGA"
        "CCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGG"
        "GAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGC"
        "AGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGT"
        "ACTCTGACACCGACGAATTTTACCCAGTTGCAGGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCG"
        "CACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGT"
        "TGAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAAGCAGA"
        "TACGCTG";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, LocalConsensusWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(true);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "AATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGA"
        "CCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGG"
        "GAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGC"
        "AGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGT"
        "ACTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCGC"
        "ACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGTT"
        "GAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGATA"
        "CGCTTTACACGCGCAACCAAGGATTTCGG";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, LocalAffineConsensusWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(true);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "AATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGA"
        "CCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGG"
        "GAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGC"
        "AGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGT"
        "ACTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCGC"
        "ACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGTT"
        "GAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGATA"
        "CGCTTTACACGCGCAACCAAGGATTTCGG";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, LocalConvexConsensusWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(true);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "AATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGA"
        "CCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGG"
        "GAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGC"
        "AGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGT"
        "ACTCTGACACCGACGAATTTTACCCAGTTGCAGGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCG"
        "CACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGT"
        "TGAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGAT"
        "ACGCTG";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, GlobalConsensus) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(false);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "ATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGAC"
        "CTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGGG"
        "AGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGCA"
        "GGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGTA"
        "CTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCGCA"
        "CAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGTTG"
        "AGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGATAC"
        "GC";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, GlobalAffineConsensus) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(false);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "ATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGAC"
        "CTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGGG"
        "AGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGCA"
        "GGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGTA"
        "CTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCGCA"
        "CAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGTTG"
        "AGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGATAC"
        "GC";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, GlobalConvexConsensus) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(false);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "ATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGAC"
        "CTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGGG"
        "AGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGCA"
        "GGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGTA"
        "CTCTGACACCGACGAATTTTACCCAGTTGCAGGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCGC"
        "ACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGTT"
        "GAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAAGCAGAT"
        "ACGC";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, GlobalConsensusWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(true);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "ATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGAC"
        "CTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGGG"
        "AGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGCA"
        "GGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGTA"
        "CTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCGCA"
        "CAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGTTG"
        "AGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGATAC"
        "GC";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, GlobalAffineConsensusWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(true);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "ATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGAC"
        "CTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGGG"
        "AGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGCA"
        "GGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGTA"
        "CTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCGCA"
        "CAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGTTG"
        "AGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGATAC"
        "GC";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, GlobalConvexConsensusWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(true);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "ATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCGAC"
        "CTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAGGG"
        "AGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGGCA"
        "GGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCGTA"
        "CTCTGACACCGACGAATTTTACCCAGTTGCAGGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCGC"
        "ACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGTT"
        "GAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAAGCAGAT"
        "ACGC";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, SemiGlobalConsensus) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(false);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "ACATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCG"
        "ACCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAG"
        "GGAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGG"
        "CAGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCG"
        "TACTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCG"
        "CACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGT"
        "TGAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGAT"
        "ACGCGTTTTACACGCGCAACCAAGGATTTCGG";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, SemiGlobalAffineConsensus) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(false);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "GTATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCG"
        "ACCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAG"
        "GGAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGG"
        "CAGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCG"
        "TACTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCG"
        "CACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGT"
        "TGAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGAT"
        "ACGCGTTTTACACGCGCAACCAAGGATTTCGG";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, SemiGlobalConvexConsensus) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(false);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "GTATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCG"
        "ACCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAG"
        "GGAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGG"
        "CAGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCG"
        "TACTCTGACACCGACGAATTTTACCCAGTTGCAGGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCC"
        "GCACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACG"
        "TTGAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAAGCAG"
        "ATACGC";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, SemiGlobalConsensusWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(true);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "ACATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCG"
        "ACCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAG"
        "GGAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGG"
        "CAGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCG"
        "TACTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCG"
        "CACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGT"
        "TGAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGAT"
        "ACGCGTTTTACACGCGCAACCAAGGATTTCGG";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, SemiGlobalAffineConsensusWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(true);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "ACATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCG"
        "ACCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAG"
        "GGAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGG"
        "CAGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCG"
        "TACTCTGACACCGACGAATTTTACCCAGTTGCAGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCCG"
        "CACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACGT"
        "TGAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAGCAGAT"
        "ACGCGTTTTACACGCGCAACCAAGGATTTCGG";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, SemiGlobalConvexConsensusWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(true);

    auto consensus = graph->generate_consensus();

    std::string valid_result = "GTATGATGCGCTTTGTTGGCGCGGTGGCTTGATGCAGGGGCTAATCG"
        "ACCTCTGGCAACCACTTTTCCATGACAGGAGTTGAATATGGCATTCAGTAATCCCTTCGATGATCCGCAG"
        "GGAGCGTTTTACATATTGCGCAATGCGCAGGGGCAATTCAGTCTGTGGCCGCAACAATGCGTCTTACCGG"
        "CAGGCTGGGACATTGTGTGTCAGCCGCAGTCACAGGCGTCCTGCCAGCAGTGGCTGGAAGCCCACTGGCG"
        "TACTCTGACACCGACGAATTTTACCCAGTTGCAGGGAGGCACAATGAGCCAGCATTTACCTTTGGTCGCC"
        "GCACAGCCCGGCATCTGGATGGCAGAAAAACTGTCAGAATTACCCTCCGCCTGGAGCGTGGCGCATTACG"
        "TTGAGTTAACCGGAGAGGTTGATTCGCCATTACTGGCCCGCGCGGTGGTTGCCGGACTAGCGCAAAGCAG"
        "ATACGC";

    EXPECT_TRUE(consensus.compare(valid_result) == 0);
}

TEST_F(SpoaAlignmentTest, LocalMSA) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(false);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, LocalAffineMSA) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(false);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, LocalConvexMSA) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(false);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, LocalMSAWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(true);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, LocalAffineMSAWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(true);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, LocalConvexMSAWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kSW,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(true);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, GlobalMSA) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(false);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, GlobalAffineMSA) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(false);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, GlobalConvexMSA) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(false);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, GlobalMSAWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(true);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, GlobalAffineMSAWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(true);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, GlobalConvexMSAWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kNW,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(true);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, SemiGlobalMSA) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(false);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, SemiGlobalAffineMSA) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(false);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, SemiGlobalConvexMSA) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(false);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, SemiGlobalMSAWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -8, -8, -8);

    initialize();
    construct_partial_order_graph(true);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, SemiGlobalAffineMSAWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -6, -8, -6);

    initialize();
    construct_partial_order_graph(true);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

TEST_F(SpoaAlignmentTest, SemiGlobalConvexMSAWithQualities) {
    SetUp(spoa_test_data_path + "sample.fastq", spoa::AlignmentType::kOV,
        5, -4, -8, -6, -10, -2);

    initialize();
    construct_partial_order_graph(true);

    std::vector<std::string> msa;
    graph->generate_multiple_sequence_alignment(msa);

    EXPECT_TRUE(msa.size() == sequences.size());

    for (std::uint32_t i = 0; i < msa.size(); ++i) {
        std::string tmp = "";
        for (const auto& c: msa[i]) {
            if (c != '-') tmp += c;
        }

        EXPECT_TRUE(tmp.size() == sequences[i]->data().size());
        EXPECT_TRUE(tmp.compare(sequences[i]->data()) == 0);
    }
}

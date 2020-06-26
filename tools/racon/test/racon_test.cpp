/*!
 * @file racon_test.cpp
 *
 * @brief Racon unit test source file
 */

#include "racon_test_config.h"

#include "sequence.hpp"
#include "polisher.hpp"

#include "edlib.h"
#include "bioparser/bioparser.hpp"
#include "gtest/gtest.h"

uint32_t calculateEditDistance(const std::string& query, const std::string& target) {

    EdlibAlignResult result = edlibAlign(query.c_str(), query.size(), target.c_str(),
        target.size(), edlibDefaultAlignConfig());

    uint32_t edit_distance = result.editDistance;
    edlibFreeAlignResult(result);

    return edit_distance;
}

class RaconPolishingTest: public ::testing::Test {
public:
    void SetUp(const std::string& sequences_path, const std::string& overlaps_path,
        const std::string& target_path, racon::PolisherType type,
        uint32_t window_length, double quality_threshold, double error_threshold,
        int8_t match, int8_t mismatch, int8_t gap, uint32_t cuda_batches = 0,
        bool cuda_banded_alignment = false, uint32_t cudaaligner_batches = 0) {

        polisher = racon::createPolisher(sequences_path, overlaps_path, target_path,
            type, window_length, quality_threshold, error_threshold, true, match,
            mismatch, gap, 4, cuda_batches, cuda_banded_alignment, cudaaligner_batches);
    }

    void TearDown() {}

    void initialize() {
        polisher->initialize();
    }

    void polish(std::vector<std::unique_ptr<racon::Sequence>>& dst,
        bool drop_unpolished_sequences) {

        return polisher->polish(dst, drop_unpolished_sequences);
    }

    std::unique_ptr<racon::Polisher> polisher;
};

TEST(RaconInitializeTest, PolisherTypeError) {
    EXPECT_DEATH((racon::createPolisher("", "", "", static_cast<racon::PolisherType>(3),
        0, 0, 0, 0, 0, 0, 0, 0)), ".racon::createPolisher. error: invalid polisher"
        " type!");
}

TEST(RaconInitializeTest, WindowLengthError) {
    EXPECT_DEATH((racon::createPolisher("", "", "", racon::PolisherType::kC, 0,
        0, 0, 0, 0, 0, 0, 0)), ".racon::createPolisher. error: invalid window length!");
}

TEST(RaconInitializeTest, SequencesPathExtensionError) {
    EXPECT_DEATH((racon::createPolisher("", "", "", racon::PolisherType::kC, 500,
        0, 0, 0, 0, 0, 0, 0)), ".racon::createPolisher. error: file  has unsupported "
        "format extension .valid extensions: .fasta, .fasta.gz, .fna, .fna.gz, "
        ".fa, .fa.gz, .fastq, .fastq.gz, .fq, .fq.gz.!");
}

TEST(RaconInitializeTest, OverlapsPathExtensionError) {
    EXPECT_DEATH((racon::createPolisher(racon_test_data_path + "sample_reads.fastq.gz",
        "", "", racon::PolisherType::kC, 500, 0, 0, 0, 0, 0, 0, 0)),
        ".racon::createPolisher. error: file  has unsupported format extension "
        ".valid extensions: .mhap, .mhap.gz, .paf, .paf.gz, .sam, .sam.gz.!");
}

TEST(RaconInitializeTest, TargetPathExtensionError) {
    EXPECT_DEATH((racon::createPolisher(racon_test_data_path + "sample_reads.fastq.gz",
        racon_test_data_path + "sample_overlaps.paf.gz", "", racon::PolisherType::kC,
        500, 0, 0, 0, 0, 0, 0, 0)), ".racon::createPolisher. error: file  has "
        "unsupported format extension .valid extensions: .fasta, .fasta.gz, .fna, "
        ".fna.gz, .fa, .fa.gz, .fastq, .fastq.gz, .fq, .fq.gz.!");
}

TEST_F(RaconPolishingTest, ConsensusWithQualities) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_overlaps.paf.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 5, -4, -8);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1312);
}

TEST_F(RaconPolishingTest, ConsensusWithoutQualities) {
    SetUp(racon_test_data_path + "sample_reads.fasta.gz", racon_test_data_path +
        "sample_overlaps.paf.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 5, -4, -8);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1566);
}

TEST_F(RaconPolishingTest, ConsensusWithQualitiesAndAlignments) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_overlaps.sam.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 5, -4, -8);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1317);
}

TEST_F(RaconPolishingTest, ConsensusWithoutQualitiesAndWithAlignments) {
    SetUp(racon_test_data_path + "sample_reads.fasta.gz", racon_test_data_path +
        "sample_overlaps.sam.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 5, -4, -8);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1770);
}

TEST_F(RaconPolishingTest, ConsensusWithQualitiesLargerWindow) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_overlaps.paf.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 1000, 10, 0.3, 5, -4, -8);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1289);
}

TEST_F(RaconPolishingTest, ConsensusWithQualitiesEditDistance) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_overlaps.paf.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 1, -1, -1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1321);
}

TEST_F(RaconPolishingTest, FragmentCorrectionWithQualities) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_ava_overlaps.paf.gz", racon_test_data_path + "sample_reads.fastq.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 1, -1, -1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 39);

    uint32_t total_length = 0;
    for (const auto& it: polished_sequences) {
        total_length += it->data().size();
    }
    EXPECT_EQ(total_length, 389394);
}

TEST_F(RaconPolishingTest, FragmentCorrectionWithQualitiesFull) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_ava_overlaps.paf.gz", racon_test_data_path + "sample_reads.fastq.gz",
        racon::PolisherType::kF, 500, 10, 0.3, 1, -1, -1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, false);
    EXPECT_EQ(polished_sequences.size(), 236);

    uint32_t total_length = 0;
    for (const auto& it: polished_sequences) {
        total_length += it->data().size();
    }
    EXPECT_EQ(total_length, 1658216);
}

TEST_F(RaconPolishingTest, FragmentCorrectionWithoutQualitiesFull) {
    SetUp(racon_test_data_path + "sample_reads.fasta.gz", racon_test_data_path +
        "sample_ava_overlaps.paf.gz", racon_test_data_path + "sample_reads.fasta.gz",
        racon::PolisherType::kF, 500, 10, 0.3, 1, -1, -1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, false);
    EXPECT_EQ(polished_sequences.size(), 236);

    uint32_t total_length = 0;
    for (const auto& it: polished_sequences) {
        total_length += it->data().size();
    }
    EXPECT_EQ(total_length, 1663982);
}

TEST_F(RaconPolishingTest, FragmentCorrectionWithQualitiesFullMhap) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_ava_overlaps.mhap.gz", racon_test_data_path + "sample_reads.fastq.gz",
        racon::PolisherType::kF, 500, 10, 0.3, 1, -1, -1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, false);
    EXPECT_EQ(polished_sequences.size(), 236);

    uint32_t total_length = 0;
    for (const auto& it: polished_sequences) {
        total_length += it->data().size();
    }
    EXPECT_EQ(total_length, 1658216);
}

#ifdef CUDA_ENABLED
TEST_F(RaconPolishingTest, ConsensusWithQualitiesCUDA) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_overlaps.paf.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 5, -4, -8, 1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1385); // CPU 1312
}

TEST_F(RaconPolishingTest, ConsensusWithoutQualitiesCUDA) {
    SetUp(racon_test_data_path + "sample_reads.fasta.gz", racon_test_data_path +
        "sample_overlaps.paf.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 5, -4, -8, 1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1607); // CPU 1566
}

TEST_F(RaconPolishingTest, ConsensusWithQualitiesAndAlignmentsCUDA) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_overlaps.sam.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 5, -4, -8, 1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1541); // CPU 1317
}

TEST_F(RaconPolishingTest, ConsensusWithoutQualitiesAndWithAlignmentsCUDA) {
    SetUp(racon_test_data_path + "sample_reads.fasta.gz", racon_test_data_path +
        "sample_overlaps.sam.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 5, -4, -8, 1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1661); // CPU 1770
}

TEST_F(RaconPolishingTest, ConsensusWithQualitiesLargerWindowCUDA) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_overlaps.paf.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 1000, 10, 0.3, 5, -4, -8, 1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 4168); // CPU 1289
}

TEST_F(RaconPolishingTest, ConsensusWithQualitiesEditDistanceCUDA) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_overlaps.paf.gz", racon_test_data_path + "sample_layout.fasta.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 1, -1, -1, 1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 1);

    polished_sequences[0]->create_reverse_complement();

    auto parser = bioparser::createParser<bioparser::FastaParser, racon::Sequence>(
        racon_test_data_path + "sample_reference.fasta.gz");
    parser->parse(polished_sequences, -1);
    EXPECT_EQ(polished_sequences.size(), 2);

    EXPECT_EQ(calculateEditDistance(polished_sequences[0]->reverse_complement(),
        polished_sequences[1]->data()), 1361); // CPU 1321
}

TEST_F(RaconPolishingTest, FragmentCorrectionWithQualitiesCUDA) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_ava_overlaps.paf.gz", racon_test_data_path + "sample_reads.fastq.gz",
        racon::PolisherType::kC, 500, 10, 0.3, 1, -1, -1, 1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, true);
    EXPECT_EQ(polished_sequences.size(), 39);

    uint32_t total_length = 0;
    for (const auto& it: polished_sequences) {
        total_length += it->data().size();
    }
    EXPECT_EQ(total_length, 385543); // CPU 389394
}

TEST_F(RaconPolishingTest, FragmentCorrectionWithQualitiesFullCUDA) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_ava_overlaps.paf.gz", racon_test_data_path + "sample_reads.fastq.gz",
        racon::PolisherType::kF, 500, 10, 0.3, 1, -1, -1, 1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, false);
    EXPECT_EQ(polished_sequences.size(), 236);

    uint32_t total_length = 0;
    for (const auto& it: polished_sequences) {
        total_length += it->data().size();
    }
    EXPECT_EQ(total_length, 1655505); // CPU 1658216
}

TEST_F(RaconPolishingTest, FragmentCorrectionWithoutQualitiesFullCUDA) {
    SetUp(racon_test_data_path + "sample_reads.fasta.gz", racon_test_data_path +
        "sample_ava_overlaps.paf.gz", racon_test_data_path + "sample_reads.fasta.gz",
        racon::PolisherType::kF, 500, 10, 0.3, 1, -1, -1, 1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, false);
    EXPECT_EQ(polished_sequences.size(), 236);

    uint32_t total_length = 0;
    for (const auto& it: polished_sequences) {
        total_length += it->data().size();
    }
    EXPECT_EQ(total_length, 1663732); // CPU 1663982
}

TEST_F(RaconPolishingTest, FragmentCorrectionWithQualitiesFullMhapCUDA) {
    SetUp(racon_test_data_path + "sample_reads.fastq.gz", racon_test_data_path +
        "sample_ava_overlaps.mhap.gz", racon_test_data_path + "sample_reads.fastq.gz",
        racon::PolisherType::kF, 500, 10, 0.3, 1, -1, -1, 1);

    initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polish(polished_sequences, false);
    EXPECT_EQ(polished_sequences.size(), 236);

    uint32_t total_length = 0;
    for (const auto& it: polished_sequences) {
        total_length += it->data().size();
    }
    EXPECT_EQ(total_length, 1655505); // CPU 1658216
}
#endif

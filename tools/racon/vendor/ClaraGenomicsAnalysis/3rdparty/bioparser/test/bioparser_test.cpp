/*!
 * @file bioparser_test.cpp
 *
 * @brief Bioparser unit test source file
 */

#include "bioparser_test_config.h"

#include "bioparser/bioparser.hpp"
#include "gtest/gtest.h"

class Read {
public:
    Read(const char* name, std::uint32_t name_length,
        const char* sequence, std::uint32_t sequence_length)
            : name_(name, name_length), sequence_(sequence, sequence_length),
            quality_() {
    }

    Read(const char* name, std::uint32_t name_length,
        const char* sequence, std::uint32_t sequence_length,
        const char* quality, std::uint32_t quality_length)
            : name_(name, name_length), sequence_(sequence, sequence_length),
            quality_(quality, quality_length) {
    }

    ~Read() {}

    std::string name_;
    std::string sequence_;
    std::string quality_;
};

void reads_summary(std::uint32_t& name_size, std::uint32_t& sequence_size,
    std::uint32_t& quality_size, const std::vector<std::unique_ptr<Read>>& reads) {

    name_size = 0;
    sequence_size = 0;
    quality_size = 0;
    for (const auto& it: reads) {
        name_size += it->name_.size();
        sequence_size += it->sequence_.size();
        quality_size += it->quality_.size();
    }
}

class Overlap {
public:
    Overlap(std::uint64_t a_id,
        std::uint64_t b_id,
        double error,
        std::uint32_t minmers,
        std::uint32_t a_rc,
        std::uint32_t a_begin,
        std::uint32_t a_end,
        std::uint32_t a_length,
        std::uint32_t b_rc,
        std::uint32_t b_begin,
        std::uint32_t b_end,
        std::uint32_t b_length)
            : q_name_(),
            q_id_(a_id - 1),
            q_begin_(a_begin),
            q_end_(a_end),
            q_length_(a_length),
            t_name_(),
            t_id_(b_id - 1),
            t_begin_(b_begin),
            t_end_(b_end),
            t_length_(b_length),
            orientation_(a_rc == b_rc ? '+' : '-'),
            error_(error * 10000),
            minmers_(minmers),
            matching_bases_(),
            overlap_length_(),
            mapping_quality_() {
    }

    Overlap(const char* q_name, std::uint32_t q_name_length,
        std::uint32_t q_length,
        std::uint32_t q_begin,
        std::uint32_t q_end,
        char orientation,
        const char* t_name, std::uint32_t t_name_length,
        std::uint32_t t_length,
        std::uint32_t t_begin,
        std::uint32_t t_end,
        std::uint32_t matching_bases,
        std::uint32_t overlap_length,
        std::uint32_t quality)
            : q_name_(q_name, q_name_length),
            q_id_(),
            q_begin_(q_begin),
            q_end_(q_end),
            q_length_(q_length),
            t_name_(t_name, t_name_length),
            t_id_(),
            t_begin_(t_begin),
            t_end_(t_end),
            t_length_(t_length),
            orientation_(orientation),
            error_(),
            minmers_(),
            matching_bases_(matching_bases),
            overlap_length_(overlap_length),
            mapping_quality_(quality) {
    }

    ~Overlap() {}

    std::string q_name_;
    std::uint64_t q_id_;
    std::uint32_t q_begin_;
    std::uint32_t q_end_;
    std::uint32_t q_length_;
    std::string t_name_;
    std::uint64_t t_id_;
    std::uint32_t t_begin_;
    std::uint32_t t_end_;
    std::uint32_t t_length_;
    char orientation_;
    std::uint32_t error_;
    std::uint32_t minmers_;
    std::uint32_t matching_bases_;
    std::uint32_t overlap_length_;
    std::uint32_t mapping_quality_;
};

void overlaps_summary(std::uint32_t& name_size, std::uint32_t& total_value,
    const std::vector<std::unique_ptr<Overlap>>& overlaps) {

    name_size = 0;
    total_value = 0;
    for (const auto& it: overlaps) {
        name_size += it->q_name_.size();
        name_size += it->t_name_.size();
        total_value += it->q_id_;
        total_value += it->q_begin_;
        total_value += it->q_end_;
        total_value += it->q_length_;
        total_value += it->t_id_;
        total_value += it->t_begin_;
        total_value += it->t_end_;
        total_value += it->t_length_;
        total_value += it->orientation_;
        total_value += it->error_;
        total_value += it->minmers_;
        total_value += it->matching_bases_;
        total_value += it->overlap_length_;
        total_value += it->mapping_quality_;
    }
}

class Alignment {
public:
    Alignment(const char* q_name, std::uint32_t q_name_length,
        std::uint32_t flag,
        const char* t_name, std::uint32_t t_name_length,
        std::uint32_t t_begin,
        std::uint32_t mapping_quality,
        const char* cigar, std::uint32_t cigar_length,
        const char* t_next_name, std::uint32_t t_next_name_length,
        std::uint32_t t_next_begin,
        std::uint32_t template_length,
        const char* sequence, std::uint32_t sequence_length,
        const char* quality, std::uint32_t quality_length)
            : q_name_(q_name, q_name_length),
            flag_(flag),
            t_name_(t_name, t_name_length),
            t_begin_(t_begin),
            mapping_quality_(mapping_quality),
            cigar_(cigar, cigar_length),
            t_next_name_(t_next_name, t_next_name_length),
            t_next_begin_(t_next_begin),
            template_length_(template_length),
            sequence_(sequence, sequence_length),
            quality_(quality, quality_length) {
    }

    ~Alignment() {}

    std::string q_name_;
    std::uint32_t flag_;
    std::string t_name_;
    std::uint32_t t_begin_;
    std::uint32_t mapping_quality_;
    std::string cigar_;
    std::string t_next_name_;
    std::uint32_t t_next_begin_;
    std::uint32_t template_length_;
    std::string sequence_;
    std::string quality_;
};

void alignments_summary(std::uint32_t& string_size, std::uint32_t& total_value,
    const std::vector<std::unique_ptr<Alignment>>& alignments) {

    string_size = 0;
    total_value = 0;
    for (const auto& it: alignments) {
        string_size += it->q_name_.size();
        string_size += it->t_name_.size();
        string_size += it->cigar_.size();
        string_size += it->t_next_name_.size();
        string_size += it->sequence_.size();
        string_size += it->quality_.size();
        total_value += it->flag_;
        total_value += it->t_begin_;
        total_value += it->mapping_quality_;
        total_value += it->t_next_begin_;
        total_value += it->template_length_;
    }
}

class BioparserFastaTest: public ::testing::Test {
public:
    void SetUp(const std::string& file_name) {
        parser = bioparser::createParser<bioparser::FastaParser, Read>(file_name);
    }

    void TearDown() {}

    std::unique_ptr<bioparser::Parser<Read>> parser;
};

class BioparserFastqTest: public ::testing::Test {
public:
    void SetUp(const std::string& file_name) {
        parser = bioparser::createParser<bioparser::FastqParser, Read>(file_name);
    }

    void TearDown() {}

    std::unique_ptr<bioparser::Parser<Read>> parser;
};

class BioparserMhapTest: public ::testing::Test {
public:
    void SetUp(const std::string& file_name) {
        parser = bioparser::createParser<bioparser::MhapParser, Overlap>(file_name);
    }

    void TearDown() {}

    std::unique_ptr<bioparser::Parser<Overlap>> parser;
};

class BioparserPafTest: public ::testing::Test {
public:
    void SetUp(const std::string& file_name) {
        parser = bioparser::createParser<bioparser::PafParser, Overlap>(file_name);
    }

    void TearDown() {}

    std::unique_ptr<bioparser::Parser<Overlap>> parser;
};

class BioparserSamTest: public ::testing::Test {
public:
    void SetUp(const std::string& file_name) {
        parser = bioparser::createParser<bioparser::SamParser, Alignment>(file_name);
    }

    void TearDown() {}

    std::unique_ptr<bioparser::Parser<Alignment>> parser;
};

TEST(BioparserTest, CreateParserError) {
    try {
        auto parser = bioparser::createParser<bioparser::FastaParser, Read>("");
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::createParser] error: "
            "unable to open file !");
    }
}

TEST_F(BioparserFastaTest, ParseWhole) {

    SetUp(bioparser_test_data_path + "sample.fasta");

    std::vector<std::unique_ptr<Read>> reads;
    parser->parse(reads, -1);

    std::uint32_t name_size = 0, sequence_size = 0, quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    EXPECT_EQ(14U, reads.size());
    EXPECT_EQ(65U, name_size);
    EXPECT_EQ(109117U, sequence_size);
    EXPECT_EQ(0U, quality_size);
}

TEST_F(BioparserFastaTest, ParseWholeWithoutTrimming) {

    SetUp(bioparser_test_data_path + "sample.fasta");

    std::vector<std::unique_ptr<Read>> reads;
    parser->parse(reads, -1, false);

    std::uint32_t name_size = 0, sequence_size = 0, quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    EXPECT_EQ(14U, reads.size());
    EXPECT_EQ(75U, name_size);
    EXPECT_EQ(109117U, sequence_size);
    EXPECT_EQ(0U, quality_size);
}

TEST_F(BioparserFastaTest, CompressedParseWhole) {

    SetUp(bioparser_test_data_path + "sample.fasta.gz");

    std::vector<std::unique_ptr<Read>> reads;
    parser->parse(reads, -1);

    std::uint32_t name_size = 0, sequence_size = 0, quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    EXPECT_EQ(14U, reads.size());
    EXPECT_EQ(65U, name_size);
    EXPECT_EQ(109117U, sequence_size);
    EXPECT_EQ(0U, quality_size);
}

TEST_F(BioparserFastaTest, CompressedParseWholeWithoutTrimming) {

    SetUp(bioparser_test_data_path + "sample.fasta.gz");

    std::vector<std::unique_ptr<Read>> reads;
    parser->parse(reads, -1, false);

    std::uint32_t name_size = 0, sequence_size = 0, quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    EXPECT_EQ(14U, reads.size());
    EXPECT_EQ(75U, name_size);
    EXPECT_EQ(109117U, sequence_size);
    EXPECT_EQ(0U, quality_size);
}

TEST_F(BioparserFastaTest, ParseInChunks) {

    SetUp(bioparser_test_data_path + "sample.fasta");

    std::uint32_t size_in_bytes = 64 * 1024;
    std::vector<std::unique_ptr<Read>> reads;
    while (parser->parse(reads, size_in_bytes)) {
    }

    std::uint32_t name_size = 0, sequence_size = 0, quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    EXPECT_EQ(14U, reads.size());
    EXPECT_EQ(65U, name_size);
    EXPECT_EQ(109117U, sequence_size);
    EXPECT_EQ(0U, quality_size);
}

TEST_F(BioparserFastaTest, CompressedParseInChunks) {

    SetUp(bioparser_test_data_path + "sample.fasta.gz");

    std::uint32_t size_in_bytes = 64 * 1024;
    std::vector<std::unique_ptr<Read>> reads;
    while (parser->parse(reads, size_in_bytes)) {
    }

    std::uint32_t name_size = 0, sequence_size = 0, quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    EXPECT_EQ(14U, reads.size());
    EXPECT_EQ(65U, name_size);
    EXPECT_EQ(109117U, sequence_size);
    EXPECT_EQ(0U, quality_size);
}

TEST_F(BioparserFastaTest, FormatError) {

    SetUp(bioparser_test_data_path + "sample.fastq");
    std::vector<std::unique_ptr<Read>> reads;

    try {
        parser->parse(reads, -1);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::FastaParser] error: "
            "invalid file format!");
    }
}

TEST_F(BioparserFastaTest, CompressedFormatError) {

    SetUp(bioparser_test_data_path + "sample.fastq.gz");
    std::vector<std::unique_ptr<Read>> reads;

    try {
        parser->parse(reads, -1);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::FastaParser] error: "
            "invalid file format!");
    }
}

TEST_F(BioparserFastaTest, ChunkSizeError) {

    SetUp(bioparser_test_data_path + "sample.fasta");

    std::uint32_t size_in_bytes = 10 * 1024;
    std::vector<std::unique_ptr<Read>> reads;

    try {
        parser->parse(reads, size_in_bytes);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::FastaParser] error: "
            "too small chunk size!");
    }
}

TEST_F(BioparserFastaTest, CompressedChunkSizeError) {

    SetUp(bioparser_test_data_path + "sample.fasta.gz");

    std::uint32_t size_in_bytes = 10 * 1024;
    std::vector<std::unique_ptr<Read>> reads;

    try {
        parser->parse(reads, size_in_bytes);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::FastaParser] error: "
            "too small chunk size!");
    }
}

TEST_F(BioparserFastaTest, ParseAndReset) {

    SetUp(bioparser_test_data_path + "sample.fasta");

    std::vector<std::unique_ptr<Read>> reads;
    parser->parse(reads, -1);

    std::uint32_t num_reads = reads.size(), name_size = 0, sequence_size = 0,
        quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    std::uint32_t size_in_bytes = 64 * 1024;
    reads.clear();
    parser->reset();
    while (parser->parse(reads, size_in_bytes)) {
    }

    std::uint32_t num_reads_new = reads.size(), name_size_new = 0,
        sequence_size_new = 0, quality_size_new = 0;
    reads_summary(name_size_new, sequence_size_new, quality_size_new, reads);

    EXPECT_EQ(num_reads_new, num_reads);
    EXPECT_EQ(name_size_new, name_size);
    EXPECT_EQ(sequence_size_new, sequence_size);
    EXPECT_EQ(quality_size_new, quality_size);
}

TEST_F(BioparserFastaTest, CompressedParseAndReset) {

    SetUp(bioparser_test_data_path + "sample.fasta.gz");

    std::vector<std::unique_ptr<Read>> reads;
    parser->parse(reads, -1);

    std::uint32_t num_reads = reads.size(), name_size = 0, sequence_size = 0,
        quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    std::uint32_t size_in_bytes = 64 * 1024;
    reads.clear();
    parser->reset();
    while (parser->parse(reads, size_in_bytes)) {
    }

    std::uint32_t num_reads_new = reads.size(), name_size_new = 0,
        sequence_size_new = 0, quality_size_new = 0;
    reads_summary(name_size_new, sequence_size_new, quality_size_new, reads);

    EXPECT_EQ(num_reads_new, num_reads);
    EXPECT_EQ(name_size_new, name_size);
    EXPECT_EQ(sequence_size_new, sequence_size);
    EXPECT_EQ(quality_size_new, quality_size);
}

TEST_F(BioparserFastqTest, ParseWhole) {

    SetUp(bioparser_test_data_path + "sample.fastq");

    std::vector<std::unique_ptr<Read>> reads;
    parser->parse(reads, -1);

    std::uint32_t name_size = 0, sequence_size = 0, quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    EXPECT_EQ(13U, reads.size());
    EXPECT_EQ(17U, name_size);
    EXPECT_EQ(108140U, sequence_size);
    EXPECT_EQ(108140U, quality_size);
}

TEST_F(BioparserFastqTest, CompressedParseWhole) {

    SetUp(bioparser_test_data_path + "sample.fastq.gz");

    std::vector<std::unique_ptr<Read>> reads;
    parser->parse(reads, -1);

    std::uint32_t name_size = 0, sequence_size = 0, quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    EXPECT_EQ(13U, reads.size());
    EXPECT_EQ(17U, name_size);
    EXPECT_EQ(108140U, sequence_size);
    EXPECT_EQ(108140U, quality_size);
}

TEST_F(BioparserFastqTest, ParseInChunks) {

    SetUp(bioparser_test_data_path + "sample.fastq");

    std::uint32_t size_in_bytes = 64 * 1024;
    std::vector<std::unique_ptr<Read>> reads;
    while (parser->parse(reads, size_in_bytes)) {
    }

    std::uint32_t name_size = 0, sequence_size = 0, quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    EXPECT_EQ(13U, reads.size());
    EXPECT_EQ(17U, name_size);
    EXPECT_EQ(108140U, sequence_size);
    EXPECT_EQ(108140U, quality_size);
}

TEST_F(BioparserFastqTest, CompressedParseInChunks) {

    SetUp(bioparser_test_data_path + "sample.fastq.gz");

    std::uint32_t size_in_bytes = 64 * 1024;
    std::vector<std::unique_ptr<Read>> reads;
    while (parser->parse(reads, size_in_bytes)) {
    }

    std::uint32_t name_size = 0, sequence_size = 0, quality_size = 0;
    reads_summary(name_size, sequence_size, quality_size, reads);

    EXPECT_EQ(13U, reads.size());
    EXPECT_EQ(17U, name_size);
    EXPECT_EQ(108140U, sequence_size);
    EXPECT_EQ(108140U, quality_size);
}

TEST_F(BioparserFastqTest, FormatError) {

    SetUp(bioparser_test_data_path + "sample.fasta");

    std::vector<std::unique_ptr<Read>> reads;

    try {
        parser->parse(reads, -1);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::FastqParser] error: "
            "invalid file format!");
    }
}

TEST_F(BioparserFastqTest, CompressedFormatError) {

    SetUp(bioparser_test_data_path + "sample.fasta.gz");

    std::vector<std::unique_ptr<Read>> reads;

    try {
        parser->parse(reads, -1);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::FastqParser] error: "
            "invalid file format!");
    }
}

TEST_F(BioparserFastqTest, ChunkSizeError) {

    SetUp(bioparser_test_data_path + "sample.fastq");

    std::uint32_t size_in_bytes = 10 * 1024;
    std::vector<std::unique_ptr<Read>> reads;

    try {
        parser->parse(reads, size_in_bytes);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::FastqParser] error: "
            "too small chunk size!");
    }
}

TEST_F(BioparserFastqTest, CompressedChunkSizeError) {

    SetUp(bioparser_test_data_path + "sample.fastq.gz");

    std::uint32_t size_in_bytes = 10 * 1024;
    std::vector<std::unique_ptr<Read>> reads;

    try {
        parser->parse(reads, size_in_bytes);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::FastqParser] error: "
            "too small chunk size!");
    }
}

TEST_F(BioparserMhapTest, ParseWhole) {

    SetUp(bioparser_test_data_path + "sample.mhap");

    std::vector<std::unique_ptr<Overlap>> overlaps;
    parser->parse(overlaps, -1);

    std::uint32_t name_size = 0, total_value = 0;
    overlaps_summary(name_size, total_value, overlaps);

    EXPECT_EQ(150U, overlaps.size());
    EXPECT_EQ(0U, name_size);
    EXPECT_EQ(7822873U, total_value);
}

TEST_F(BioparserMhapTest, CompressedParseWhole) {

    SetUp(bioparser_test_data_path + "sample.mhap.gz");

    std::vector<std::unique_ptr<Overlap>> overlaps;
    parser->parse(overlaps, -1);

    std::uint32_t name_size = 0, total_value = 0;
    overlaps_summary(name_size, total_value, overlaps);

    EXPECT_EQ(150U, overlaps.size());
    EXPECT_EQ(0U, name_size);
    EXPECT_EQ(7822873U, total_value);
}

TEST_F(BioparserMhapTest, ParseInChunks) {

    SetUp(bioparser_test_data_path + "sample.mhap");

    std::uint32_t size_in_bytes = 64 * 1024;
    std::vector<std::unique_ptr<Overlap>> overlaps;
    while (parser->parse(overlaps, size_in_bytes)) {
    }

    std::uint32_t name_size = 0, total_value = 0;
    overlaps_summary(name_size, total_value, overlaps);

    EXPECT_EQ(150U, overlaps.size());
    EXPECT_EQ(0U, name_size);
    EXPECT_EQ(7822873U, total_value);
}

TEST_F(BioparserMhapTest, CompressedParseInChunks) {

    SetUp(bioparser_test_data_path + "sample.mhap.gz");

    std::uint32_t size_in_bytes = 64 * 1024;
    std::vector<std::unique_ptr<Overlap>> overlaps;
    while (parser->parse(overlaps, size_in_bytes)) {
    }

    std::uint32_t name_size = 0, total_value = 0;
    overlaps_summary(name_size, total_value, overlaps);

    EXPECT_EQ(150U, overlaps.size());
    EXPECT_EQ(0U, name_size);
    EXPECT_EQ(7822873U, total_value);
}

TEST_F(BioparserMhapTest, FormatError) {

    SetUp(bioparser_test_data_path + "sample.paf");

    std::vector<std::unique_ptr<Overlap>> overlaps;

    try {
        parser->parse(overlaps, -1);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::MhapParser] error: "
            "invalid file format!");
    }
}

TEST_F(BioparserMhapTest, CompressedFormatError) {

    SetUp(bioparser_test_data_path + "sample.paf.gz");

    std::vector<std::unique_ptr<Overlap>> overlaps;

    try {
        parser->parse(overlaps, -1);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::MhapParser] error: "
            "invalid file format!");
    }
}

TEST_F(BioparserPafTest, ParseWhole) {

    SetUp(bioparser_test_data_path + "sample.paf");

    std::vector<std::unique_ptr<Overlap>> overlaps;
    parser->parse(overlaps, -1);

    std::uint32_t name_size = 0, total_value = 0;
    overlaps_summary(name_size, total_value, overlaps);

    EXPECT_EQ(500U, overlaps.size());
    EXPECT_EQ(96478U, name_size);
    EXPECT_EQ(18494208U, total_value);
}

TEST_F(BioparserPafTest, CompressedParseWhole) {

    SetUp(bioparser_test_data_path + "sample.paf.gz");

    std::vector<std::unique_ptr<Overlap>> overlaps;
    parser->parse(overlaps, -1);

    std::uint32_t name_size = 0, total_value = 0;
    overlaps_summary(name_size, total_value, overlaps);

    EXPECT_EQ(500U, overlaps.size());
    EXPECT_EQ(96478U, name_size);
    EXPECT_EQ(18494208U, total_value);
}

TEST_F(BioparserPafTest, ParseInChunks) {

    SetUp(bioparser_test_data_path + "sample.paf");

    std::uint32_t size_in_bytes = 64 * 1024;
    std::vector<std::unique_ptr<Overlap>> overlaps;
    while (parser->parse(overlaps, size_in_bytes)) {
    }

    std::uint32_t name_size = 0, total_value = 0;
    overlaps_summary(name_size, total_value, overlaps);

    EXPECT_EQ(500U, overlaps.size());
    EXPECT_EQ(96478U, name_size);
    EXPECT_EQ(18494208U, total_value);
}

TEST_F(BioparserPafTest, CompressedParseInChunks) {

    SetUp(bioparser_test_data_path + "sample.paf.gz");

    std::uint32_t size_in_bytes = 64 * 1024;
    std::vector<std::unique_ptr<Overlap>> overlaps;
    while (parser->parse(overlaps, size_in_bytes)) {
    }

    std::uint32_t name_size = 0, total_value = 0;
    overlaps_summary(name_size, total_value, overlaps);

    EXPECT_EQ(500U, overlaps.size());
    EXPECT_EQ(96478U, name_size);
    EXPECT_EQ(18494208U, total_value);
}

TEST_F(BioparserPafTest, FormatError) {

    SetUp(bioparser_test_data_path + "sample.mhap");

    std::vector<std::unique_ptr<Overlap>> overlaps;

    try {
        parser->parse(overlaps, -1);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::PafParser] error: "
            "invalid file format!");
    }
}

TEST_F(BioparserPafTest, CompressedFormatError) {

    SetUp(bioparser_test_data_path + "sample.mhap.gz");

    std::vector<std::unique_ptr<Overlap>> overlaps;

    try {
        parser->parse(overlaps, -1);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::PafParser] error: "
            "invalid file format!");
    }
}

TEST_F(BioparserSamTest, ParseWhole) {

    SetUp(bioparser_test_data_path + "sample.sam");

    std::vector<std::unique_ptr<Alignment>> alignments;
    parser->parse(alignments, -1);

    std::uint32_t string_size = 0, total_value = 0;
    alignments_summary(string_size, total_value, alignments);

    EXPECT_EQ(48U, alignments.size());
    EXPECT_EQ(795237U, string_size);
    EXPECT_EQ(639677U, total_value);
}

TEST_F(BioparserSamTest, CompressedParseWhole) {

    SetUp(bioparser_test_data_path + "sample.sam.gz");

    std::vector<std::unique_ptr<Alignment>> alignments;
    parser->parse(alignments, -1);

    std::uint32_t string_size = 0, total_value = 0;
    alignments_summary(string_size, total_value, alignments);

    EXPECT_EQ(48U, alignments.size());
    EXPECT_EQ(795237U, string_size);
    EXPECT_EQ(639677U, total_value);
}

TEST_F(BioparserSamTest, ParseInChunks) {

    SetUp(bioparser_test_data_path + "sample.sam");

    std::uint32_t size_in_bytes = 64 * 1024;
    std::vector<std::unique_ptr<Alignment>> alignments;
    while (parser->parse(alignments, size_in_bytes)) {
    }

    std::uint32_t string_size = 0, total_value = 0;
    alignments_summary(string_size, total_value, alignments);

    EXPECT_EQ(48U, alignments.size());
    EXPECT_EQ(795237U, string_size);
    EXPECT_EQ(639677U, total_value);
}

TEST_F(BioparserSamTest, CompressedParseInChunks) {

    SetUp(bioparser_test_data_path + "sample.sam.gz");

    std::uint32_t size_in_bytes = 64 * 1024;
    std::vector<std::unique_ptr<Alignment>> alignments;
    while (parser->parse(alignments, size_in_bytes)) {
    }

    std::uint32_t string_size = 0, total_value = 0;
    alignments_summary(string_size, total_value, alignments);

    EXPECT_EQ(48U, alignments.size());
    EXPECT_EQ(795237U, string_size);
    EXPECT_EQ(639677U, total_value);
}

TEST_F(BioparserSamTest, FormatError) {

    SetUp(bioparser_test_data_path + "sample.paf");

    std::vector<std::unique_ptr<Alignment>> alignments;

    try {
        parser->parse(alignments, -1);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::SamParser] error: "
            "invalid file format!");
    }
}

TEST_F(BioparserSamTest, CompressedFormatError) {

    SetUp(bioparser_test_data_path + "sample.paf.gz");

    std::vector<std::unique_ptr<Alignment>> alignments;

    try {
        parser->parse(alignments, -1);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[bioparser::SamParser] error: "
            "invalid file format!");
    }
}

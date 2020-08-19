/*!
 * @file sampler.cpp
 *
 * @brief Sampler class source file
 */

#include <random>

#include "sequence.hpp"
#include "sampler.hpp"

#include "bioparser/bioparser.hpp"

namespace rampler {

constexpr uint32_t kChunkSize = 1024 * 1024 * 1024; // ~ 1GB

std::unique_ptr<Sampler> createSampler(const std::string& sequences_path) {

    std::unique_ptr<bioparser::Parser<Sequence>> sparser = nullptr;

    std::string base_name = sequences_path.substr(sequences_path.rfind('/') + 1);
    base_name = base_name.substr(0, base_name.find('.'));
    std::string extension;

    auto is_suffix = [](const std::string& src, const std::string& suffix) -> bool {
        if (src.size() < suffix.size()) {
            return false;
        }
        return src.compare(src.size() - suffix.size(), suffix.size(), suffix) == 0;
    };

    if (is_suffix(sequences_path, ".fasta") || is_suffix(sequences_path, ".fa") ||
        is_suffix(sequences_path, ".fasta.gz") || is_suffix(sequences_path, ".fa.gz")) {
        sparser = bioparser::createParser<bioparser::FastaParser, Sequence>(
            sequences_path);
        extension = ".fasta";
    } else if (is_suffix(sequences_path, ".fastq") || is_suffix(sequences_path, ".fq") ||
        is_suffix(sequences_path, ".fastq.gz") || is_suffix(sequences_path, ".fq.gz")) {
        sparser = bioparser::createParser<bioparser::FastqParser, Sequence>(
            sequences_path);
        extension = ".fastq";
    } else {
        fprintf(stderr, "[rampler::createSampler] error: "
            "file %s has unsupported format extension (valid extensions: "
            ".fasta, .fasta.gz, .fa, .fa.gz, .fastq, .fastq.gz, .fq, .fq.gz)!\n",
            sequences_path.c_str());
        exit(1);
    }

    return std::unique_ptr<Sampler>(new Sampler(std::move(sparser), base_name,
        extension));
}

Sampler::Sampler(std::unique_ptr<bioparser::Parser<Sequence>> sparser,
    const std::string& base_name, const std::string& extension)
        : sparser_(std::move(sparser)), sequences_length_(0), base_name_(base_name),
        extension_(extension) {
}

Sampler::~Sampler() {
}

void Sampler::initialize() {

    if (sequences_length_ != 0) {
        fprintf(stderr, "[rampler::Sampler::initialize] warning: "
            "object already initialized!\n");
        return;
    }

    sparser_->reset();
    while (true) {
        std::vector<std::unique_ptr<Sequence>> sequences;
        auto status = sparser_->parse(sequences, kChunkSize);

        for (const auto& it: sequences) {
            sequences_length_ += it->data().size();
        }

        if (!status) {
            break;
        }
    }
}

void Sampler::subsample(const std::string& out_directory, uint32_t reference_length,
    uint32_t coverage) {

    if (coverage * reference_length > sequences_length_) {
        fprintf(stderr, "[rampler::Sampler::subsample] warning: "
            "insufficient data for coverage %u!\n", coverage);
        return;
    }

    std::random_device r;
    std::mt19937 generator(r());
    std::uniform_real_distribution<double> distribution(0.0, 1.0);

    double ratio = (coverage * reference_length) / static_cast<double>(
        sequences_length_);

    std::string out_path = out_directory + "/" + base_name_ + "_" +
        std::to_string(coverage) + "x" + extension_;
    auto out = fopen(out_path.c_str(), "w");
    if (out == nullptr) {
        fprintf(stderr, "rampler::Sampler::subsample] error: "
            "unable to create file %s!\n", out_path.c_str());
        exit(1);
    }

    sparser_->reset();
    while (true) {
        std::vector<std::unique_ptr<Sequence>> sequences;
        auto status = sparser_->parse(sequences, kChunkSize);

        for (const auto& it: sequences) {
            if (distribution(generator) < ratio) {
                if (it->quality().empty()) {
                    fprintf(out, ">%s\n%s\n", it->name().c_str(),
                        it->data().c_str());
                } else {
                    fprintf(out, "@%s\n%s\n+\n%s\n", it->name().c_str(),
                        it->data().c_str(), it->quality().c_str());
                }
            }
        }

        if (!status) {
            break;
        }
    }

    fclose(out);
}

void Sampler::split(const std::string& out_directory, uint32_t chunk_size) {

    if (chunk_size > sequences_length_) {
        fprintf(stderr, "[rampler::Sampler::split] warning: "
            "insufficient data for chunk size %u!\n", chunk_size);
        return;
    }

    uint32_t chunk_number = 0;

    sparser_->reset();
    while (true) {
        std::vector<std::unique_ptr<Sequence>> sequences;
        auto status = sparser_->parse(sequences, chunk_size);

        std::string out_path = out_directory + "/" + base_name_ + "_" +
            std::to_string(chunk_number) + extension_;
        auto out = fopen(out_path.c_str(), "w");
        if (out == nullptr) {
            fprintf(stderr, "rampler::Sampler::subsample] error: "
                "unable to create file %s!\n", out_path.c_str());
            exit(1);
        }

        for (const auto& it: sequences) {
            if (it->quality().empty()) {
                fprintf(out, ">%s\n%s\n", it->name().c_str(),
                    it->data().c_str());
            } else {
                fprintf(out, "@%s\n%s\n+\n%s\n", it->name().c_str(),
                    it->data().c_str(), it->quality().c_str());
            }
        }

        fclose(out);

        ++chunk_number;

        if (!status) {
            break;
        }
    }
}

}

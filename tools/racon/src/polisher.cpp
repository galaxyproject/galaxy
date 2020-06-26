/*!
 * @file polisher.cpp
 *
 * @brief Polisher class source file
 */

#include <algorithm>
#include <unordered_set>
#include <iostream>

#include "overlap.hpp"
#include "sequence.hpp"
#include "window.hpp"
#include "logger.hpp"
#include "polisher.hpp"
#ifdef CUDA_ENABLED
#include "cuda/cudapolisher.hpp"
#endif

#include "bioparser/bioparser.hpp"
#include "thread_pool/thread_pool.hpp"
#include "spoa/spoa.hpp"

namespace racon {

constexpr uint32_t kChunkSize = 1024 * 1024 * 1024; // ~ 1GB

template<class T>
uint64_t shrinkToFit(std::vector<std::unique_ptr<T>>& src, uint64_t begin) {

    uint64_t i = begin;
    for (uint64_t j = begin; i < src.size(); ++i) {
        if (src[i] != nullptr) {
            continue;
        }

        j = std::max(j, i);
        while (j < src.size() && src[j] == nullptr) {
            ++j;
        }

        if (j >= src.size()) {
            break;
        } else if (i != j) {
            src[i].swap(src[j]);
        }
    }
    uint64_t num_deletions = src.size() - i;
    if (i < src.size()) {
        src.resize(i);
    }
    return num_deletions;
}

std::unique_ptr<Polisher> createPolisher(const std::string& sequences_path,
    const std::string& overlaps_path, const std::string& target_path,
    PolisherType type, uint32_t window_length, double quality_threshold,
    double error_threshold, bool trim, int8_t match, int8_t mismatch, int8_t gap,
    uint32_t num_threads, uint32_t cudapoa_batches, bool cuda_banded_alignment,
    uint32_t cudaaligner_batches) {

    if (type != PolisherType::kC && type != PolisherType::kF) {
        fprintf(stderr, "[racon::createPolisher] error: invalid polisher type!\n");
        exit(1);
    }

    if (window_length == 0) {
        fprintf(stderr, "[racon::createPolisher] error: invalid window length!\n");
        exit(1);
    }

    std::unique_ptr<bioparser::Parser<Sequence>> sparser = nullptr,
        tparser = nullptr;
    std::unique_ptr<bioparser::Parser<Overlap>> oparser = nullptr;

    auto is_suffix = [](const std::string& src, const std::string& suffix) -> bool {
        if (src.size() < suffix.size()) {
            return false;
        }
        return src.compare(src.size() - suffix.size(), suffix.size(), suffix) == 0;
    };

    if (is_suffix(sequences_path, ".fasta") || is_suffix(sequences_path, ".fasta.gz") ||
        is_suffix(sequences_path, ".fna") || is_suffix(sequences_path, ".fna.gz") ||
        is_suffix(sequences_path, ".fa") || is_suffix(sequences_path, ".fa.gz")) {
        sparser = bioparser::createParser<bioparser::FastaParser, Sequence>(
            sequences_path);
    } else if (is_suffix(sequences_path, ".fastq") || is_suffix(sequences_path, ".fastq.gz") ||
        is_suffix(sequences_path, ".fq") || is_suffix(sequences_path, ".fq.gz")) {
        sparser = bioparser::createParser<bioparser::FastqParser, Sequence>(
            sequences_path);
    } else {
        fprintf(stderr, "[racon::createPolisher] error: "
            "file %s has unsupported format extension (valid extensions: "
            ".fasta, .fasta.gz, .fna, .fna.gz, .fa, .fa.gz, .fastq, .fastq.gz, "
            ".fq, .fq.gz)!\n",
            sequences_path.c_str());
        exit(1);
    }

    if (is_suffix(overlaps_path, ".mhap") || is_suffix(overlaps_path, ".mhap.gz")) {
        oparser = bioparser::createParser<bioparser::MhapParser, Overlap>(
            overlaps_path);
    } else if (is_suffix(overlaps_path, ".paf") || is_suffix(overlaps_path, ".paf.gz")) {
        oparser = bioparser::createParser<bioparser::PafParser, Overlap>(
            overlaps_path);
    } else if (is_suffix(overlaps_path, ".sam") || is_suffix(overlaps_path, ".sam.gz")) {
        oparser = bioparser::createParser<bioparser::SamParser, Overlap>(
            overlaps_path);
    } else {
        fprintf(stderr, "[racon::createPolisher] error: "
            "file %s has unsupported format extension (valid extensions: "
            ".mhap, .mhap.gz, .paf, .paf.gz, .sam, .sam.gz)!\n", overlaps_path.c_str());
        exit(1);
    }

    if (is_suffix(target_path, ".fasta") || is_suffix(target_path, ".fasta.gz") ||
        is_suffix(target_path, ".fna") || is_suffix(target_path, ".fna.gz") ||
        is_suffix(target_path, ".fa") || is_suffix(target_path, ".fa.gz")) {
        tparser = bioparser::createParser<bioparser::FastaParser, Sequence>(
            target_path);
    } else if (is_suffix(target_path, ".fastq") || is_suffix(target_path, ".fastq.gz") ||
        is_suffix(target_path, ".fq") || is_suffix(target_path, ".fq.gz")) {
        tparser = bioparser::createParser<bioparser::FastqParser, Sequence>(
            target_path);
    } else {
        fprintf(stderr, "[racon::createPolisher] error: "
            "file %s has unsupported format extension (valid extensions: "
            ".fasta, .fasta.gz, .fna, .fna.gz, .fa, .fa.gz, .fastq, .fastq.gz, "
            ".fq, .fq.gz)!\n",
            target_path.c_str());
        exit(1);
    }

    if (cudapoa_batches > 0 || cudaaligner_batches > 0)
    {
#ifdef CUDA_ENABLED
        // If CUDA is enabled, return an instance of the CUDAPolisher object.
        return std::unique_ptr<Polisher>(new CUDAPolisher(std::move(sparser),
                    std::move(oparser), std::move(tparser), type, window_length,
                    quality_threshold, error_threshold, trim, match, mismatch, gap,
                    num_threads, cudapoa_batches, cuda_banded_alignment, cudaaligner_batches));
#else
        fprintf(stderr, "[racon::createPolisher] error: "
                "Attemping to use CUDA when CUDA support is not available.\n"
                "Please check logic in %s:%s\n",
                __FILE__, __func__);
        exit(1);
#endif
    }
    else
    {
        (void) cuda_banded_alignment;
        return std::unique_ptr<Polisher>(new Polisher(std::move(sparser),
                    std::move(oparser), std::move(tparser), type, window_length,
                    quality_threshold, error_threshold, trim, match, mismatch, gap,
                    num_threads));
    }
}

Polisher::Polisher(std::unique_ptr<bioparser::Parser<Sequence>> sparser,
    std::unique_ptr<bioparser::Parser<Overlap>> oparser,
    std::unique_ptr<bioparser::Parser<Sequence>> tparser,
    PolisherType type, uint32_t window_length, double quality_threshold,
    double error_threshold, bool trim, int8_t match, int8_t mismatch, int8_t gap,
    uint32_t num_threads)
        : sparser_(std::move(sparser)), oparser_(std::move(oparser)),
        tparser_(std::move(tparser)), type_(type), quality_threshold_(
        quality_threshold), error_threshold_(error_threshold), trim_(trim),
        alignment_engines_(), sequences_(), dummy_quality_(window_length, '!'),
        window_length_(window_length), windows_(),
        thread_pool_(thread_pool::createThreadPool(num_threads)),
        thread_to_id_(), logger_(new Logger()) {

    uint32_t id = 0;
    for (const auto& it: thread_pool_->thread_identifiers()) {
        thread_to_id_[it] = id++;
    }

    for (uint32_t i = 0; i < num_threads; ++i) {
        alignment_engines_.emplace_back(spoa::createAlignmentEngine(
            spoa::AlignmentType::kNW, match, mismatch, gap));
        alignment_engines_.back()->prealloc(window_length_, 5);
    }
}

Polisher::~Polisher() {
    logger_->total("[racon::Polisher::] total =");
}

void Polisher::initialize() {

    if (!windows_.empty()) {
        fprintf(stderr, "[racon::Polisher::initialize] warning: "
            "object already initialized!\n");
        return;
    }

    logger_->log();

    tparser_->reset();
    tparser_->parse(sequences_, -1);

    uint64_t targets_size = sequences_.size();
    if (targets_size == 0) {
        fprintf(stderr, "[racon::Polisher::initialize] error: "
            "empty target sequences set!\n");
        exit(1);
    }

    std::unordered_map<std::string, uint64_t> name_to_id;
    std::unordered_map<uint64_t, uint64_t> id_to_id;
    for (uint64_t i = 0; i < targets_size; ++i) {
        name_to_id[sequences_[i]->name() + "t"] = i;
        id_to_id[i << 1 | 1] = i;
    }

    std::vector<bool> has_name(targets_size, true);
    std::vector<bool> has_data(targets_size, true);
    std::vector<bool> has_reverse_data(targets_size, false);

    logger_->log("[racon::Polisher::initialize] loaded target sequences");
    logger_->log();

    uint64_t sequences_size = 0, total_sequences_length = 0;

    sparser_->reset();
    while (true) {
        uint64_t l = sequences_.size();
        auto status = sparser_->parse(sequences_, kChunkSize);

        uint64_t n = 0;
        for (uint64_t i = l; i < sequences_.size(); ++i, ++sequences_size) {
            total_sequences_length += sequences_[i]->data().size();

            auto it = name_to_id.find(sequences_[i]->name() + "t");
            if (it != name_to_id.end()) {
                if (sequences_[i]->data().size() != sequences_[it->second]->data().size() ||
                    sequences_[i]->quality().size() != sequences_[it->second]->quality().size()) {

                    fprintf(stderr, "[racon::Polisher::initialize] error: "
                        "duplicate sequence %s with unequal data\n",
                        sequences_[i]->name().c_str());
                    exit(1);
                }

                name_to_id[sequences_[i]->name() + "q"] = it->second;
                id_to_id[sequences_size << 1 | 0] = it->second;

                sequences_[i].reset();
                ++n;
            } else {
                name_to_id[sequences_[i]->name() + "q"] = i - n;
                id_to_id[sequences_size << 1 | 0] = i - n;
            }
        }

        shrinkToFit(sequences_, l);

        if (!status) {
            break;
        }
    }

    if (sequences_size == 0) {
        fprintf(stderr, "[racon::Polisher::initialize] error: "
            "empty sequences set!\n");
        exit(1);
    }

    has_name.resize(sequences_.size(), false);
    has_data.resize(sequences_.size(), false);
    has_reverse_data.resize(sequences_.size(), false);

    WindowType window_type = static_cast<double>(total_sequences_length) /
        sequences_size <= 1000 ? WindowType::kNGS : WindowType::kTGS;

    logger_->log("[racon::Polisher::initialize] loaded sequences");
    logger_->log();

    std::vector<std::unique_ptr<Overlap>> overlaps;

    auto remove_invalid_overlaps = [&](uint64_t begin, uint64_t end) -> void {
        for (uint64_t i = begin; i < end; ++i) {
            if (overlaps[i] == nullptr) {
                continue;
            }
            if (overlaps[i]->error() > error_threshold_ ||
                overlaps[i]->q_id() == overlaps[i]->t_id()) {
                overlaps[i].reset();
                continue;
            }
            if (type_ == PolisherType::kC) {
                for (uint64_t j = i + 1; j < end; ++j) {
                    if (overlaps[j] == nullptr) {
                        continue;
                    }
                    if (overlaps[i]->length() > overlaps[j]->length()) {
                        overlaps[j].reset();
                    } else {
                        overlaps[i].reset();
                        break;
                    }
                }
            }
        }
    };

    oparser_->reset();
    uint64_t l = 0;
    while (true) {
        auto status = oparser_->parse(overlaps, kChunkSize);

        uint64_t c = l;
        for (uint64_t i = l; i < overlaps.size(); ++i) {
            overlaps[i]->transmute(sequences_, name_to_id, id_to_id);

            if (!overlaps[i]->is_valid()) {
                overlaps[i].reset();
                continue;
            }

            while (overlaps[c] == nullptr) {
                ++c;
            }
            if (overlaps[c]->q_id() != overlaps[i]->q_id()) {
                remove_invalid_overlaps(c, i);
                c = i;
            }
        }
        if (!status) {
            remove_invalid_overlaps(c, overlaps.size());
            c = overlaps.size();
        }

        for (uint64_t i = l; i < c; ++i) {
            if (overlaps[i] == nullptr) {
                continue;
            }

            if (overlaps[i]->strand()) {
                has_reverse_data[overlaps[i]->q_id()] = true;
            } else {
                has_data[overlaps[i]->q_id()] = true;
            }
        }

        uint64_t n = shrinkToFit(overlaps, l);
        l = c - n;

        if (!status) {
            break;
        }
    }

    std::unordered_map<std::string, uint64_t>().swap(name_to_id);
    std::unordered_map<uint64_t, uint64_t>().swap(id_to_id);

    if (overlaps.empty()) {
        fprintf(stderr, "[racon::Polisher::initialize] error: "
            "empty overlap set!\n");
        exit(1);
    }

    logger_->log("[racon::Polisher::initialize] loaded overlaps");
    logger_->log();

    std::vector<std::future<void>> thread_futures;
    for (uint64_t i = 0; i < sequences_.size(); ++i) {
        thread_futures.emplace_back(thread_pool_->submit(
            [&](uint64_t j) -> void {
                sequences_[j]->transmute(has_name[j], has_data[j], has_reverse_data[j]);
            }, i));
    }
    for (const auto& it: thread_futures) {
        it.wait();
    }

    find_overlap_breaking_points(overlaps);

    logger_->log();

    std::vector<uint64_t> id_to_first_window_id(targets_size + 1, 0);
    for (uint64_t i = 0; i < targets_size; ++i) {
        uint32_t k = 0;
        for (uint32_t j = 0; j < sequences_[i]->data().size(); j += window_length_, ++k) {

            uint32_t length = std::min(j + window_length_,
                static_cast<uint32_t>(sequences_[i]->data().size())) - j;

            windows_.emplace_back(createWindow(i, k, window_type,
                &(sequences_[i]->data()[j]), length,
                sequences_[i]->quality().empty() ? &(dummy_quality_[0]) :
                &(sequences_[i]->quality()[j]), length));
        }

        id_to_first_window_id[i + 1] = id_to_first_window_id[i] + k;
    }

    targets_coverages_.resize(targets_size, 0);

    for (uint64_t i = 0; i < overlaps.size(); ++i) {

        ++targets_coverages_[overlaps[i]->t_id()];

        const auto& sequence = sequences_[overlaps[i]->q_id()];
        const auto& breaking_points = overlaps[i]->breaking_points();

        for (uint32_t j = 0; j < breaking_points.size(); j += 2) {
            if (breaking_points[j + 1].second - breaking_points[j].second < 0.02 * window_length_) {
                continue;
            }

            if (!sequence->quality().empty() ||
                !sequence->reverse_quality().empty()) {

                const auto& quality = overlaps[i]->strand() ?
                    sequence->reverse_quality() : sequence->quality();
                double average_quality = 0;
                for (uint32_t k = breaking_points[j].second; k < breaking_points[j + 1].second; ++k) {
                    average_quality += static_cast<uint32_t>(quality[k]) - 33;
                }
                average_quality /= breaking_points[j + 1].second - breaking_points[j].second;

                if (average_quality < quality_threshold_) {
                    continue;
                }
            }

            uint64_t window_id = id_to_first_window_id[overlaps[i]->t_id()] +
                breaking_points[j].first / window_length_;
            uint32_t window_start = (breaking_points[j].first / window_length_) *
                window_length_;

            const char* data = overlaps[i]->strand() ?
                &(sequence->reverse_complement()[breaking_points[j].second]) :
                &(sequence->data()[breaking_points[j].second]);
            uint32_t data_length = breaking_points[j + 1].second -
                breaking_points[j].second;

            const char* quality = overlaps[i]->strand() ?
                (sequence->reverse_quality().empty() ?
                    nullptr : &(sequence->reverse_quality()[breaking_points[j].second]))
                :
                (sequence->quality().empty() ?
                    nullptr : &(sequence->quality()[breaking_points[j].second]));
            uint32_t quality_length = quality == nullptr ? 0 : data_length;

            windows_[window_id]->add_layer(data, data_length,
                quality, quality_length,
                breaking_points[j].first - window_start,
                breaking_points[j + 1].first - window_start - 1);
        }

        overlaps[i].reset();
    }

    logger_->log("[racon::Polisher::initialize] transformed data into windows");
}

void Polisher::find_overlap_breaking_points(std::vector<std::unique_ptr<Overlap>>& overlaps)
{
    std::vector<std::future<void>> thread_futures;
    for (uint64_t i = 0; i < overlaps.size(); ++i) {
        thread_futures.emplace_back(thread_pool_->submit(
            [&](uint64_t j) -> void {
                overlaps[j]->find_breaking_points(sequences_, window_length_);
            }, i));
    }

    uint32_t logger_step = thread_futures.size() / 20;
    for (uint64_t i = 0; i < thread_futures.size(); ++i) {
        thread_futures[i].wait();
        if (logger_step != 0 && (i + 1) % logger_step == 0 && (i + 1) / logger_step < 20) {
            logger_->bar("[racon::Polisher::initialize] aligning overlaps");
        }
    }
    if (logger_step != 0) {
        logger_->bar("[racon::Polisher::initialize] aligning overlaps");
    } else {
        logger_->log("[racon::Polisher::initialize] aligned overlaps");
    }
}

void Polisher::polish(std::vector<std::unique_ptr<Sequence>>& dst,
    bool drop_unpolished_sequences) {

    logger_->log();

    std::vector<std::future<bool>> thread_futures;
    for (uint64_t i = 0; i < windows_.size(); ++i) {
        thread_futures.emplace_back(thread_pool_->submit(
            [&](uint64_t j) -> bool {
                auto it = thread_to_id_.find(std::this_thread::get_id());
                if (it == thread_to_id_.end()) {
                    fprintf(stderr, "[racon::Polisher::polish] error: "
                        "thread identifier not present!\n");
                    exit(1);
                }
                return windows_[j]->generate_consensus(
                    alignment_engines_[it->second], trim_);
            }, i));
    }

    std::string polished_data = "";
    uint32_t num_polished_windows = 0;

    uint64_t logger_step = thread_futures.size() / 20;

    for (uint64_t i = 0; i < thread_futures.size(); ++i) {
        thread_futures[i].wait();

        num_polished_windows += thread_futures[i].get() == true ? 1 : 0;
        polished_data += windows_[i]->consensus();

        if (i == windows_.size() - 1 || windows_[i + 1]->rank() == 0) {
            double polished_ratio = num_polished_windows /
                static_cast<double>(windows_[i]->rank() + 1);

            if (!drop_unpolished_sequences || polished_ratio > 0) {
                std::string tags = type_ == PolisherType::kF ? "r" : "";
                tags += " LN:i:" + std::to_string(polished_data.size());
                tags += " RC:i:" + std::to_string(targets_coverages_[windows_[i]->id()]);
                tags += " XC:f:" + std::to_string(polished_ratio);
                dst.emplace_back(createSequence(sequences_[windows_[i]->id()]->name() +
                    tags, polished_data));
            }

            num_polished_windows = 0;
            polished_data.clear();
        }
        windows_[i].reset();

        if (logger_step != 0 && (i + 1) % logger_step == 0 && (i + 1) / logger_step < 20) {
            logger_->bar("[racon::Polisher::polish] generating consensus");
        }
    }

    if (logger_step != 0) {
        logger_->bar("[racon::Polisher::polish] generating consensus");
    } else {
        logger_->log("[racon::Polisher::polish] generated consensus");
    }

    std::vector<std::shared_ptr<Window>>().swap(windows_);
    std::vector<std::unique_ptr<Sequence>>().swap(sequences_);
}

}

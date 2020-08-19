/*!
 * @file polisher.hpp
 *
 * @brief Polisher class header file
 */

#pragma once

#include <stdlib.h>
#include <vector>
#include <memory>
#include <unordered_map>
#include <thread>

namespace bioparser {
    template<class T>
    class Parser;
}

namespace thread_pool {
    class ThreadPool;
}

namespace spoa {
    class AlignmentEngine;
}


namespace racon {

class Sequence;
class Overlap;
class Window;
class Logger;

enum class PolisherType {
    kC, // Contig polishing
    kF // Fragment error correction
};

class Polisher;
std::unique_ptr<Polisher> createPolisher(const std::string& sequences_path,
    const std::string& overlaps_path, const std::string& target_path,
    PolisherType type, uint32_t window_length, double quality_threshold,
    double error_threshold, bool trim, int8_t match, int8_t mismatch, int8_t gap,
    uint32_t num_threads, uint32_t cuda_batches = 0,
    bool cuda_banded_alignment = false, uint32_t cudaaligner_batches = 0);

class Polisher {
public:
    virtual ~Polisher();

    virtual void initialize();

    virtual void polish(std::vector<std::unique_ptr<Sequence>>& dst,
        bool drop_unpolished_sequences);

    friend std::unique_ptr<Polisher> createPolisher(const std::string& sequences_path,
        const std::string& overlaps_path, const std::string& target_path,
        PolisherType type, uint32_t window_length, double quality_threshold,
        double error_threshold, bool trim, int8_t match, int8_t mismatch, int8_t gap,
        uint32_t num_threads, uint32_t cuda_batches, bool cuda_banded_alignment,
        uint32_t cudaaligner_batches);

protected:
    Polisher(std::unique_ptr<bioparser::Parser<Sequence>> sparser,
        std::unique_ptr<bioparser::Parser<Overlap>> oparser,
        std::unique_ptr<bioparser::Parser<Sequence>> tparser,
        PolisherType type, uint32_t window_length, double quality_threshold,
        double error_threshold, bool trim, int8_t match, int8_t mismatch, int8_t gap,
        uint32_t num_threads);
    Polisher(const Polisher&) = delete;
    const Polisher& operator=(const Polisher&) = delete;
    virtual void find_overlap_breaking_points(std::vector<std::unique_ptr<Overlap>>& overlaps);

    std::unique_ptr<bioparser::Parser<Sequence>> sparser_;
    std::unique_ptr<bioparser::Parser<Overlap>> oparser_;
    std::unique_ptr<bioparser::Parser<Sequence>> tparser_;

    PolisherType type_;
    double quality_threshold_;
    double error_threshold_;
    bool trim_;
    std::vector<std::shared_ptr<spoa::AlignmentEngine>> alignment_engines_;

    std::vector<std::unique_ptr<Sequence>> sequences_;
    std::vector<uint32_t> targets_coverages_;
    std::string dummy_quality_;

    uint32_t window_length_;
    std::vector<std::shared_ptr<Window>> windows_;

    std::unique_ptr<thread_pool::ThreadPool> thread_pool_;
    std::unordered_map<std::thread::id, uint32_t> thread_to_id_;

    std::unique_ptr<Logger> logger_;
};

}

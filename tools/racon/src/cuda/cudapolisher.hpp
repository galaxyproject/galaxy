/*!
 * @file cudapolisher.hpp
 *
 * @brief CUDA Polisher class header file
 */

#pragma once

#include <mutex>

#include "polisher.hpp"
#include "cudabatch.hpp"
#include "cudaaligner.hpp"
#include "thread_pool/thread_pool.hpp"


namespace racon {

class CUDAPolisher : public Polisher {
public:
    ~CUDAPolisher();

    virtual void polish(std::vector<std::unique_ptr<Sequence>>& dst,
        bool drop_unpolished_sequences) override;

    friend std::unique_ptr<Polisher> createPolisher(const std::string& sequences_path,
        const std::string& overlaps_path, const std::string& target_path,
        PolisherType type, uint32_t window_length, double quality_threshold,
        double error_threshold, bool trim, int8_t match, int8_t mismatch, int8_t gap,
        uint32_t num_threads, uint32_t cudapoa_batches, bool cuda_banded_alignment,
        uint32_t cudaaligner_batches);

protected:
    CUDAPolisher(std::unique_ptr<bioparser::Parser<Sequence>> sparser,
        std::unique_ptr<bioparser::Parser<Overlap>> oparser,
        std::unique_ptr<bioparser::Parser<Sequence>> tparser,
        PolisherType type, uint32_t window_length, double quality_threshold,
        double error_threshold, bool trim, int8_t match, int8_t mismatch, int8_t gap,
        uint32_t num_threads, uint32_t cudapoa_batches, bool cuda_banded_alignment,
        uint32_t cudaaligner_batches);
    CUDAPolisher(const CUDAPolisher&) = delete;
    const CUDAPolisher& operator=(const CUDAPolisher&) = delete;
    virtual void find_overlap_breaking_points(std::vector<std::unique_ptr<Overlap>>& overlaps) override;

    static std::vector<uint32_t> calculate_batches_per_gpu(uint32_t cudapoa_batches, uint32_t gpus);

    // Vector of POA batches.
    std::vector<std::unique_ptr<CUDABatchProcessor>> batch_processors_;

    // Vector of aligner batches.
    std::vector<std::unique_ptr<CUDABatchAligner>> batch_aligners_;

    // Vector of bool indicating consensus generation status for each window.
    std::vector<bool> window_consensus_status_;

    // Number of batches for POA processing.
    uint32_t cudapoa_batches_;

    // Numbver of batches for Alignment processing.
    uint32_t cudaaligner_batches_;

    // Number of GPU devices to run with.
    int32_t num_devices_;

    // State transition scores.
    int8_t gap_;
    int8_t mismatch_;
    int8_t match_;

    // Use banded POA alignment
    bool cuda_banded_alignment_;
};

}

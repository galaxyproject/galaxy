/*!
 * @file cudapolisher.cpp
 *
 * @brief CUDA Polisher class source file
 */

#include <future>
#include <iostream>
#include <chrono>
#include <cuda_profiler_api.h>

#include "sequence.hpp"
#include "logger.hpp"
#include "cudapolisher.hpp"
#include <claragenomics/utils/cudautils.hpp>

#include "bioparser/bioparser.hpp"

namespace racon {

// The logger used by racon has a fixed size of 20 bins
// which is used for the progress bar updates. Hence all
// updates need to be broken into 20 bins.
const uint32_t RACON_LOGGER_BIN_SIZE = 20;

CUDAPolisher::CUDAPolisher(std::unique_ptr<bioparser::Parser<Sequence>> sparser,
    std::unique_ptr<bioparser::Parser<Overlap>> oparser,
    std::unique_ptr<bioparser::Parser<Sequence>> tparser,
    PolisherType type, uint32_t window_length, double quality_threshold,
    double error_threshold, bool trim, int8_t match, int8_t mismatch, int8_t gap,
    uint32_t num_threads, uint32_t cudapoa_batches, bool cuda_banded_alignment,
    uint32_t cudaaligner_batches)
        : Polisher(std::move(sparser), std::move(oparser), std::move(tparser),
                type, window_length, quality_threshold, error_threshold, trim,
                match, mismatch, gap, num_threads)
        , cudapoa_batches_(cudapoa_batches)
        , cudaaligner_batches_(cudaaligner_batches)
        , gap_(gap)
        , mismatch_(mismatch)
        , match_(match)
        , cuda_banded_alignment_(cuda_banded_alignment)
{
    claragenomics::cudapoa::Init();
    claragenomics::cudaaligner::Init();

    CGA_CU_CHECK_ERR(cudaGetDeviceCount(&num_devices_));

    if (num_devices_ < 1)
    {
        throw std::runtime_error("No GPU devices found.");
    }

    std::cerr << "Using " << num_devices_ << " GPU(s) to perform polishing" << std::endl;

    // Run dummy call on each device to initialize CUDA context.
    for(int32_t dev_id = 0; dev_id < num_devices_; dev_id++)
    {
        std::cerr << "Initialize device " << dev_id << std::endl;
        CGA_CU_CHECK_ERR(cudaSetDevice(dev_id));
        CGA_CU_CHECK_ERR(cudaFree(0));
    }

    std::cerr << "[CUDAPolisher] Constructed." << std::endl;
}

CUDAPolisher::~CUDAPolisher()
{
    cudaDeviceSynchronize();
    cudaProfilerStop();
}

std::vector<uint32_t> CUDAPolisher::calculate_batches_per_gpu(uint32_t batches, uint32_t gpus)
{
    // Bin batches into each GPU.
    std::vector<uint32_t> batches_per_gpu(gpus, batches / gpus);

    for(uint32_t i = 0; i < batches % gpus; ++i)
    {
        ++batches_per_gpu[i];
    }

    return batches_per_gpu;
}


void CUDAPolisher::find_overlap_breaking_points(std::vector<std::unique_ptr<Overlap>>& overlaps)
{
    if (cudaaligner_batches_ >= 1)
    {
        // TODO: Experimentally this is giving decent perf
        const uint32_t MAX_ALIGNMENTS = 200;

        logger_->log();
        std::mutex mutex_overlaps;
        uint32_t next_overlap_index = 0;

        // Lambda expression for filling up next batch of alignments.
        auto fill_next_batch = [&mutex_overlaps, &next_overlap_index, &overlaps, this](CUDABatchAligner* batch) -> std::pair<uint32_t, uint32_t> {
            batch->reset();

            // Use mutex to read the vector containing windows in a threadsafe manner.
            std::lock_guard<std::mutex> guard(mutex_overlaps);

            uint32_t initial_count = next_overlap_index;
            uint32_t count = overlaps.size();
            while(next_overlap_index < count)
            {
                if (batch->addOverlap(overlaps.at(next_overlap_index).get(), sequences_))
                {
                    next_overlap_index++;
                }
                else
                {
                    break;
                }
            }
            return {initial_count, next_overlap_index};
        };

        // Variables for keeping track of logger progress bar.
        uint32_t logger_step = overlaps.size() / RACON_LOGGER_BIN_SIZE;
        int32_t log_bar_idx = 0, log_bar_idx_prev = -1;
        uint32_t window_idx = 0;
        std::mutex mutex_log_bar_idx;

        // Lambda expression for processing a batch of alignments.
        auto process_batch = [&fill_next_batch, &logger_step, &log_bar_idx, &log_bar_idx_prev, &window_idx, &mutex_log_bar_idx, this](CUDABatchAligner* batch) -> void {
            while(true)
            {
                auto range = fill_next_batch(batch);
                if (batch->hasOverlaps())
                {
                    // Launch workload.
                    batch->alignAll();

                    // Generate CIGAR strings for successful alignments. The actual breaking points
                    // will be calculate by the overlap object.
                    batch->generate_cigar_strings();

                    // logging bar
                    {
                        std::lock_guard<std::mutex> guard(mutex_log_bar_idx);
                        window_idx += range.second - range.first;
                        log_bar_idx = window_idx / logger_step;
                        if (log_bar_idx == log_bar_idx_prev) {
                            continue;
                        }
                        else if (logger_step != 0 && log_bar_idx < static_cast<int32_t>(RACON_LOGGER_BIN_SIZE))
                        {
                            logger_->bar("[racon::CUDAPolisher::initialize] aligning overlaps");
                            log_bar_idx_prev = log_bar_idx;
                        }
                    }
                }
                else
                {
                    break;
                }
            }
        };

        // Bin batches into each GPU.
        std::vector<uint32_t> batches_per_gpu = calculate_batches_per_gpu(cudaaligner_batches_, num_devices_);

        for(int32_t device = 0; device < num_devices_; device++)
        {
            for(uint32_t batch = 0; batch < batches_per_gpu.at(device); batch++)
            {
                batch_aligners_.emplace_back(createCUDABatchAligner(15000, 15000, MAX_ALIGNMENTS, device));
            }
        }

        logger_->log("[racon::CUDAPolisher::initialize] allocated memory on GPUs for alignment");

        // Run batched alignment.
        std::vector<std::future<void>> thread_futures;
        for(auto& aligner : batch_aligners_)
        {
            thread_futures.emplace_back(
                    thread_pool_->submit(
                        process_batch,
                        aligner.get()
                        )
                    );
        }

        // Wait for threads to finish, and collect their results.
        for (const auto& future : thread_futures) {
            future.wait();
        }

        batch_aligners_.clear();
    }

    // This call runs the breaking point detection code for all alignments.
    // Any overlaps that couldn't be processed by the GPU are also handled here
    // by the CPU aligner.
    logger_->log();
    Polisher::find_overlap_breaking_points(overlaps);
}

void CUDAPolisher::polish(std::vector<std::unique_ptr<Sequence>>& dst,
    bool drop_unpolished_sequences)
{
    if (cudapoa_batches_ < 1)
    {
        Polisher::polish(dst, drop_unpolished_sequences);
    }
    else
    {
        // Creation and use of batches.
        const uint32_t MAX_DEPTH_PER_WINDOW = 200;

        // Bin batches into each GPU.
        std::vector<uint32_t> batches_per_gpu = calculate_batches_per_gpu(cudapoa_batches_, num_devices_);

        for(int32_t device = 0; device < num_devices_; device++)
        {
            size_t total = 0, free = 0;
            CGA_CU_CHECK_ERR(cudaSetDevice(device));
            CGA_CU_CHECK_ERR(cudaMemGetInfo(&free, &total));
            // Using 90% of available memory as heuristic since not all available memory can be used
            // due to fragmentation.
            size_t mem_per_batch = 0.9 * free/batches_per_gpu.at(device);
            for(uint32_t batch = 0; batch < batches_per_gpu.at(device); batch++)
            {
                batch_processors_.emplace_back(createCUDABatch(MAX_DEPTH_PER_WINDOW, device, mem_per_batch, gap_, mismatch_, match_, cuda_banded_alignment_));
            }
        }

        logger_->log("[racon::CUDAPolisher::polish] allocated memory on GPUs for polishing");

        // Mutex for accessing the vector of windows.
        std::mutex mutex_windows;

        // Initialize window consensus statuses.
        window_consensus_status_.resize(windows_.size(), false);

        // Index of next window to be added to a batch.
        uint32_t next_window_index = 0;

        // Lambda function for adding windows to batches.
        auto fill_next_batch = [&mutex_windows, &next_window_index, this](CUDABatchProcessor* batch) -> std::pair<uint32_t, uint32_t> {
            batch->reset();

            // Use mutex to read the vector containing windows in a threadsafe manner.
            std::lock_guard<std::mutex> guard(mutex_windows);

            // TODO: Reducing window wize by 10 for debugging.
            uint32_t initial_count = next_window_index;
            uint32_t count = windows_.size();
            while(next_window_index < count)
            {
                if (batch->addWindow(windows_.at(next_window_index)))
                {
                    next_window_index++;
                }
                else
                {
                    break;
                }
            }

            return {initial_count, next_window_index};
        };

        // Variables for keeping track of logger progress bar.
        uint32_t logger_step = windows_.size() / RACON_LOGGER_BIN_SIZE;
        int32_t log_bar_idx = 0, log_bar_idx_prev = -1;
        uint32_t window_idx = 0;
        std::mutex mutex_log_bar_idx;
        logger_->log();

        // Lambda function for processing each batch.
        auto process_batch = [&fill_next_batch, &logger_step, &log_bar_idx, &mutex_log_bar_idx, &window_idx, &log_bar_idx_prev, this](CUDABatchProcessor* batch) -> void {
            while(true)
            {
                std::pair<uint32_t, uint32_t> range = fill_next_batch(batch);
                if (batch->hasWindows())
                {
                    // Launch workload.
                    const std::vector<bool>& results = batch->generateConsensus();

                    // Check if the number of batches processed is same as the range of
                    // of windows that were added.
                    if (results.size() != (range.second - range.first))
                    {
                        throw std::runtime_error("Windows processed doesn't match \
                                range of windows passed to batch\n");
                    }

                    // Copy over the results from the batch into the per window
                    // result vector of the CUDAPolisher.
                    for(uint32_t i = 0; i < results.size(); i++)
                    {
                        window_consensus_status_.at(range.first + i) = results.at(i);
                    }

                    // logging bar
                    {
                        std::lock_guard<std::mutex> guard(mutex_log_bar_idx);
                        window_idx += results.size();
                        log_bar_idx = window_idx / logger_step;
                        if (log_bar_idx == log_bar_idx_prev) {
                            continue;
                        }
                        else if (logger_step != 0 && log_bar_idx < static_cast<int32_t>(RACON_LOGGER_BIN_SIZE))
                        {
                            while(log_bar_idx_prev <= log_bar_idx)
                            {
                                logger_->bar("[racon::CUDAPolisher::polish] generating consensus");
                                log_bar_idx_prev++;
                            }
                        }
                    }
                }
                else
                {
                    break;
                }
            }
        };

        // Process each of the batches in a separate thread.
        std::vector<std::future<void>> thread_futures;
        for(auto& batch_processor : batch_processors_)
        {
            thread_futures.emplace_back(
                    thread_pool_->submit(
                        process_batch,
                        batch_processor.get()
                        )
                    );
        }

        // Wait for threads to finish, and collect their results.
        for (const auto& future : thread_futures) {
            future.wait();
        }

        logger_->log("[racon::CUDAPolisher::polish] polished windows on GPU");

        // Start timing CPU time for failed windows on GPU
        logger_->log();
        // Process each failed windows in parallel on CPU
        std::vector<std::future<bool>> thread_failed_windows;
        for (uint64_t i = 0; i < windows_.size(); ++i) {
            if (window_consensus_status_.at(i) == false)
            {
                thread_failed_windows.emplace_back(thread_pool_->submit(
                            [&](uint64_t j) -> bool {
                            auto it = thread_to_id_.find(std::this_thread::get_id());
                            if (it == thread_to_id_.end()) {
                            fprintf(stderr, "[racon::CUDAPolisher::polish] error: "
                                    "thread identifier not present!\n");
                            exit(1);
                            }
                            return window_consensus_status_.at(j) = windows_[j]->generate_consensus(
                                    alignment_engines_[it->second], trim_);
                            }, i));
            }
        }

        // Wait for threads to finish, and collect their results.
        for (const auto& t : thread_failed_windows) {
            t.wait();
        }
        if (thread_failed_windows.size() > 0)
        {
            logger_->log("[racon::CUDAPolisher::polish] polished remaining windows on CPU");
            logger_->log();
        }

        // Collect results from all windows into final output.
        std::string polished_data = "";
        uint32_t num_polished_windows = 0;

        for (uint64_t i = 0; i < windows_.size(); ++i) {

            num_polished_windows += window_consensus_status_.at(i) == true ? 1 : 0;
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
        }

        logger_->log("[racon::CUDAPolisher::polish] generated consensus");

        // Clear POA processors.
        batch_processors_.clear();
    }
}

}

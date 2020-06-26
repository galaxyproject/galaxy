/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "common/utils.hpp"

#include <claragenomics/cudapoa/batch.hpp>
#include <claragenomics/utils/signed_integer_utils.hpp>

#include <future>
#include <numeric>

namespace claragenomics
{
namespace cudapoa
{

/// \class MultiBatch
/// Class encapsulating running multiple concurrent cudapoa Batch classes.
class MultiBatch
{
public:
    /// \brief Construct a multi batch processor
    ///
    /// \param num_batches Number of cudapoa batches
    /// \param filename Filename with window data
    MultiBatch(int32_t num_batches, const std::string& filename, int32_t total_windows = -1)
        : num_batches_(num_batches)
    {
        parse_window_data_file(windows_, filename, total_windows);

        assert(get_size(windows_) > 0);

        size_t total = 0, free = 0;
        cudaSetDevice(0);
        cudaMemGetInfo(&free, &total);
        size_t mem_per_batch = 0.9 * free / num_batches_;
        for (int32_t batch = 0; batch < num_batches_; batch++)
        {
            cudaStream_t stream;
            cudaStreamCreate(&stream);
            batches_.emplace_back(create_batch(200,
                                               0, stream, mem_per_batch,
                                               OutputType::consensus,
                                               -8, -6, 8, false));
        }
    }

    ~MultiBatch()
    {
        batches_.clear();
    }

    /// \brief Process the batches in concurrent fashion
    void process_batches()
    {
        // Reserve space
        consensus_.resize(get_size(windows_));
        coverages_.resize(get_size(windows_));

        // Mutex for accessing the vector of windows.
        std::mutex mutex_windows;

        // Index of next window to be added to a batch.
        int32_t next_window_index = 0;

        // Lambda function for adding windows to batches.
        auto fill_next_batch = [&mutex_windows, &next_window_index, this](Batch* batch) -> std::pair<int32_t, int32_t> {
            // Reset batch before adding fresh set of windows.
            batch->reset();

            // Use mutex to read the vector containing windows in a threadsafe manner.
            std::lock_guard<std::mutex> guard(mutex_windows);

            // TODO: Reducing window wize by 10 for debugging.
            int32_t initial_count = next_window_index;
            int32_t count         = get_size(windows_);
            while (next_window_index < count)
            {
                Group poa_group;
                const std::vector<std::string>& window = windows_[next_window_index];
                for (auto& seq : window)
                {
                    Entry e{};
                    e.seq     = seq.c_str();
                    e.weights = NULL;
                    e.length  = seq.length();
                    poa_group.push_back(e);
                }

                std::vector<StatusType> s;
                StatusType status = batch->add_poa_group(s, poa_group);
                if (status == StatusType::success)
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

        // Lambda function for processing each batch.
        auto process_batch = [&fill_next_batch, this](Batch* batch) -> void {
            while (true)
            {
                std::pair<int32_t, int32_t> range = fill_next_batch(batch);
                if (batch->get_total_poas() > 0)
                {
                    std::vector<std::string> consensus_temp;
                    std::vector<std::vector<uint16_t>> coverages_temp;
                    std::vector<claragenomics::cudapoa::StatusType> output_status;

                    // Launch workload.
                    batch->generate_poa();
                    batch->get_consensus(consensus_temp, coverages_temp, output_status);

                    // Check if the number of batches processed is same as the range of
                    // of windows that were added.
                    if (get_size(consensus_temp) != (range.second - range.first))
                    {
                        throw std::runtime_error("Consensus processed doesn't match \
                                range of windows passed to batch\n");
                    }
                    if (get_size(coverages_temp) != (range.second - range.first))
                    {
                        throw std::runtime_error("Coverages processed doesn't match \
                                range of windows passed to batch\n");
                    }
                    for (int32_t i = range.first; i < range.second; i++)
                    {
                        consensus_[i] = consensus_temp[i - range.first];
                        coverages_[i] = coverages_temp[i - range.first];
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
        for (auto& batch : batches_)
        {
            thread_futures.emplace_back(std::async(std::launch::async,
                                                   process_batch,
                                                   batch.get()));
        }

        // Wait for threads to finish, and collect their results.
        for (const auto& future : thread_futures)
        {
            future.wait();
        }
    }

    /// \brief Concatenate consensus of finished POA windows to generate
    ///        final assembly. The coverage values is also used to trim the
    ///        assembly based on average covarge across the window.
    std::string assembly()
    {
        std::string genome = "";
        for (int32_t w = 0; w < get_size(windows_); w++)
        {
            int32_t average_coverage = std::accumulate(coverages_[w].begin(),
                                                       coverages_[w].end(),
                                                       0) /
                                       get_size(coverages_[w]);
            int32_t begin = 0, end = consensus_[w].length() - 1;
            for (; begin < get_size(coverages_[w]); ++begin)
            {
                if (coverages_[w][begin] >= average_coverage)
                {
                    break;
                }
            }
            for (; end >= 0; --end)
            {
                if (coverages_[w][end] >= average_coverage)
                {
                    break;
                }
            }

            if (begin < end)
            {
                genome += consensus_[w].substr(begin, end - begin + 1);
            }
        }
        return genome;
    }

private:
    int32_t num_batches_;
    std::vector<std::unique_ptr<Batch>> batches_;
    std::vector<std::vector<std::string>> windows_;
    std::vector<std::string> consensus_;
    std::vector<std::vector<uint16_t>> coverages_;
};
} // namespace cudapoa
} // namespace claragenomics

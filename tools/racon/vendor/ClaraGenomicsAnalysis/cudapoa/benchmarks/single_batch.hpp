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

namespace claragenomics
{

namespace cudapoa
{
class SingleBatch
{

    /// \class SingleBatch
    /// Class encapsulating running single cudapoa Batch classes with varying batch size.
public:
    /// \brief Construct a single batch processor
    ///
    /// \param max_poas_per_batch Batch size
    /// \param filename Filename with window data
    SingleBatch(int32_t max_poas_per_batch, const std::string& filename, int32_t total_windows)
        : max_poas_per_batch_(max_poas_per_batch)
    {
        parse_window_data_file(windows_, filename, total_windows);

        assert(get_size(windows_) > 0);

        cudaStream_t stream;
        cudaStreamCreate(&stream);

        size_t total = 0, free = 0;
        cudaSetDevice(0);
        cudaMemGetInfo(&free, &total);
        size_t mem_per_batch = 0.9 * free;

        batch_ = create_batch(200, 0, stream, mem_per_batch, OutputType::consensus, -8, -6, 8, false);
    }

    ~SingleBatch()
    {
        batch_.reset();
    }

    /// \brief Add windows to the batch class
    void add_windows()
    {
        batch_->reset();

        int32_t total_windows = get_size(windows_);
        for (int32_t i = 0; i < max_poas_per_batch_; i++)
        {
            Group poa_group;
            const auto& window = windows_[i % total_windows];
            for (int32_t s = 0; s < get_size(window); s++)
            {
                Entry e{};
                e.seq     = window[s].c_str();
                e.weights = NULL;
                e.length  = window[s].length();
                poa_group.push_back(e);
            }
            std::vector<StatusType> error_status;
            batch_->add_poa_group(error_status, poa_group);
        }
    }

    /// \brief Process POA and generate consensus
    void process_consensus()
    {
        batch_->generate_poa();
        std::vector<std::string> consensus;
        std::vector<std::vector<uint16_t>> coverage;
        std::vector<claragenomics::cudapoa::StatusType> output_status;
        batch_->get_consensus(consensus, coverage, output_status);
    }

private:
    std::unique_ptr<Batch> batch_;
    std::vector<std::vector<std::string>> windows_;
    int32_t max_poas_per_batch_;
};
} // namespace cudapoa
} // namespace claragenomics

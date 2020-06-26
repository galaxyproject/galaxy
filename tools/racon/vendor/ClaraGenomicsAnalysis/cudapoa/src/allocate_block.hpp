/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#pragma once

#include "cudapoa_kernels.cuh"

#include <memory>
#include <vector>
#include <stdint.h>
#include <string>
#include <cuda_runtime_api.h>

namespace claragenomics
{

namespace cudapoa
{

class BatchBlock
{
public:
    BatchBlock(int32_t device_id_, size_t avail_mem, int32_t max_sequences_per_poa, int8_t output_mask, bool banded_alignment = false);
    ~BatchBlock();

    void get_output_details(OutputDetails** output_details_h_p, OutputDetails** output_details_d_p);

    void get_input_details(InputDetails** input_details_h_p, InputDetails** input_details_d_p);

    void get_alignment_details(AlignmentDetails** alignment_details_d_p);

    void get_graph_details(GraphDetails** graph_details_d_p, GraphDetails** graph_details_h_p);

    uint8_t* get_block_host();

    uint8_t* get_block_device();

    int32_t get_max_poas() const { return max_poas_; };

protected:
    // Returns amount of host and device memory needed to store metadata per POA entry.
    // The first two elements of the tuple are fixed host and device sizes that
    // don't vary based on POA count. The latter two are host and device
    // buffer sizes that scale with number of POA entries to process. These sizes do
    // not include the scoring matrix needs for POA processing.
    std::tuple<int64_t, int64_t, int64_t, int64_t> calculate_space_per_poa();

protected:
    // Maximum POAs to process in batch.
    int32_t max_poas_ = 0;

    // Maximum sequences per POA.
    int32_t max_sequences_per_poa_ = 0;

    // Use banded POA alignment
    bool banded_alignment_;

    // Pointer for block data on host and device
    uint8_t* block_data_h_;
    uint8_t* block_data_d_;

    // Accumulator for the memory size
    int64_t total_h_ = 0;
    int64_t total_d_ = 0;

    // Offset index for pointing a buffer to block memory
    int64_t offset_h_ = 0;
    int64_t offset_d_ = 0;

    int64_t input_size_                = 0;
    int64_t output_size_               = 0;
    int32_t matrix_sequence_dimension_ = 0;
    int32_t max_graph_dimension_       = 0;
    int32_t max_nodes_per_window_      = 0;
    int32_t device_id_;

    // Bit field for output type
    int8_t output_mask_;
};

} // namespace cudapoa

} // namespace claragenomics

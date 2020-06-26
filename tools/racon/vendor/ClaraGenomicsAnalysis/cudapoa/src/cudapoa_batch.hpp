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

#include <claragenomics/cudapoa/batch.hpp>

#include <memory>
#include <vector>
#include <stdint.h>
#include <string>
#include <iostream>
#include <cuda_runtime_api.h>

namespace claragenomics
{

namespace cudapoa
{

class WindowDetails;

class AlignmentDetails;

class GraphDetails;

class OutputDetails;

class InputDetails;

class BatchBlock;

/// \addtogroup cudapoa
/// \{

/// \class
/// Batched GPU CUDA POA object
class CudapoaBatch : public Batch
{
public:
    CudapoaBatch(int32_t max_sequences_per_poa, int32_t device_id, cudaStream_t stream, size_t max_mem, int8_t output_mask, int16_t gap_score = -8, int16_t mismatch_score = -6, int16_t match_score = 8, bool cuda_banded_alignment = false);
    ~CudapoaBatch();

    virtual StatusType add_poa_group(std::vector<StatusType>& per_seq_status,
                                     const Group& poa_group);

    // Get total number of partial order alignments in batch.
    int32_t get_total_poas() const;

    // Run partial order alignment algorithm over all POAs.
    void generate_poa();

    // Get the consensus for each POA.
    StatusType get_consensus(std::vector<std::string>& consensus,
                             std::vector<std::vector<uint16_t>>& coverage,
                             std::vector<claragenomics::cudapoa::StatusType>& output_status);

    // Get multiple sequence alignments for each POA
    StatusType get_msa(std::vector<std::vector<std::string>>& msa,
                       std::vector<StatusType>& output_status);

    void get_graphs(std::vector<DirectedGraph>& graphs,
                    std::vector<StatusType>& output_status);

    // Return batch ID.
    int32_t batch_id() const;

    // Reset batch. Must do before re-using batch.
    void reset();

protected:
    // Print debug message with batch specific formatting.
    void print_batch_debug_message(const std::string& message);

    // Allocate buffers for output details
    void initialize_output_details();

    // Allocate buffers for alignment details
    void initialize_alignment_details();

    // Allocate buffers for graph details
    void initialize_graph_details();

    // Allocate buffers for input details
    void initialize_input_details();

    // Log cudapoa kernel error
    void decode_cudapoa_kernel_error(claragenomics::cudapoa::StatusType error_type,
                                     std::vector<StatusType>& output_status);

    // Add new partial order alignment to batch.
    StatusType add_poa();

    // Add sequence to last partial order alignment.
    StatusType add_seq_to_poa(const char* seq, const int8_t* weights, int32_t seq_len);

    // Check if seq length can fit in available scoring matrix memory.
    bool reserve_buf(int32_t max_seq_length);

protected:
    // Maximum sequences per POA.
    int32_t max_sequences_per_poa_ = 0;

    // GPU Device ID
    int32_t device_id_ = 0;

    // CUDA stream for launching kernels.
    cudaStream_t stream_;

    // Bit field for output type
    int8_t output_mask_;

    // Gap, mismatch and match scores for NW dynamic programming loop.
    int16_t gap_score_;
    int16_t mismatch_score_;
    int16_t match_score_;

    // Host and device buffer for output data.
    OutputDetails* output_details_h_;
    OutputDetails* output_details_d_;

    // Host and device buffer pointer for input data.
    InputDetails* input_details_d_;
    InputDetails* input_details_h_;

    // Device buffer struct for alignment details
    AlignmentDetails* alignment_details_d_;

    // Device buffer struct for graph details
    GraphDetails* graph_details_d_;
    GraphDetails* graph_details_h_;

    // Static batch count used to generate batch IDs.
    static int32_t batches;

    // Batch ID.
    int32_t bid_ = 0;

    // Total POAs added.
    int32_t poa_count_ = 0;

    // Number of nucleotides already already inserted.
    int32_t num_nucleotides_copied_ = 0;

    // Global sequence index.
    int32_t global_sequence_idx_ = 0;

    // Remaining scores buffer memory available for use.
    size_t avail_scorebuf_mem_ = 0;

    // Temporary variable to compute the offset to scorebuf.
    size_t next_scores_offset_ = 0;

    // Use banded POA alignment
    bool banded_alignment_;

    // Pointer of a seperate class BatchBlock that implements details on calculating and allocating the memory for each batch
    std::unique_ptr<BatchBlock> batch_block_;

    // Maximum POAs to process in batch.
    int32_t max_poas_ = 0;
};

/// \}

} // namespace cudapoa

} // namespace claragenomics

/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

// Implementation file for CUDA POA kernels.

#include "cudapoa_kernels.cuh"
#include "cudapoa_nw.cu"
#include "cudapoa_nw_banded.cu"
#include "cudapoa_topsort.cu"
#include "cudapoa_add_alignment.cu"
#include "cudapoa_generate_consensus.cu"
#include "cudapoa_generate_msa.cu"

#include <claragenomics/utils/cudautils.hpp>

namespace claragenomics
{

namespace cudapoa
{

/**
 * @brief The main kernel that runs the partial order alignment
 *        algorithm.
 *
 * @param[out] consensus_d                Device buffer for generated consensus
 * @param[in] sequences_d                 Device buffer with sequences for all windows
 * @param[in] base_weights_d              Device buffer with base weights for all windows
 * @param[in] sequence_lengths_d          Device buffer sequence lengths
 * @param[in] window_details_d            Device buffer with structs 
 *                                        encapsulating sequence details per window
 * @param[in] total_window                Total number of windows to process
 * @param[in] scores                      Device scratch space that scores alignment matrix score
 * @param[in] alignment_graph_d           Device scratch space for backtrace alignment of graph
 * @param[in] alignment_read_d            Device scratch space for backtrace alignment of sequence
 * @param[in] nodes                       Device scratch space for storing unique nodes in graph
 * @param[in] incoming_edges              Device scratch space for storing incoming edges per node
 * @param[in] incoming_edges_count        Device scratch space for storing number of incoming edges per node
 * @param[in] outgoing_edges              Device scratch space for storing outgoing edges per node
 * @param[in] outgoing_edges_count        Device scratch space for storing number of outgoing edges per node
 * @param[in] incoming_edge_w             Device scratch space for storing weight of incoming edges
 * @param[in] outgoing_edge_w             Device scratch space for storing weight of outgoing edges
 * @param[in] sorted_poa                  Device scratch space for storing sorted graph
 * @param[in] node_id_to_pos              Device scratch space for mapping node ID to position in graph
 * @graph[in] node_alignments             Device scratch space for storing alignment nodes per node in graph
 * @param[in] node_alignment_count        Device scratch space for storing number of aligned nodes
 * @param[in] sorted_poa_local_edge_count Device scratch space for maintaining edge counts during topological sort
 * @param[in] node_marks_d_               Device scratch space for storing node marks when running spoa accurate top sort
 * @param[in] check_aligned_nodes_d_      Device scratch space for storing check for aligned nodes
 * @param[in] nodes_to_visit_d_           device scratch space for storing stack of nodes to be visited in topsort
 * @param[in] node_coverage_counts_d_     device scratch space for storing coverage of each node in graph.
 * @param[in] gap_score                   Score for inserting gap into alignment
 * @param[in] mismatch_score              Score for finding a mismatch in alignment
 * @param[in] match_score                 Score for finding a match in alignment
 */
template <int32_t TPB = 64, bool cuda_banded_alignment = false, bool msa = false>
__global__ void generatePOAKernel(uint8_t* consensus_d,
                                  uint8_t* sequences_d,
                                  int8_t* base_weights_d,
                                  uint16_t* sequence_lengths_d,
                                  claragenomics::cudapoa::WindowDetails* window_details_d,
                                  int32_t total_windows,
                                  int16_t* scores_d,
                                  int16_t* alignment_graph_d,
                                  int16_t* alignment_read_d,
                                  uint8_t* nodes_d,
                                  uint16_t* incoming_edges_d,
                                  uint16_t* incoming_edge_count_d,
                                  uint16_t* outgoing_edges_d,
                                  uint16_t* outgoing_edge_count_d,
                                  uint16_t* incoming_edge_w_d,
                                  uint16_t* outgoing_edge_w_d,
                                  uint16_t* sorted_poa_d,
                                  uint16_t* node_id_to_pos_d,
                                  uint16_t* node_alignments_d,
                                  uint16_t* node_alignment_count_d,
                                  uint16_t* sorted_poa_local_edge_count_d,
                                  uint8_t* node_marks_d_,
                                  bool* check_aligned_nodes_d_,
                                  uint16_t* nodes_to_visit_d_,
                                  uint16_t* node_coverage_counts_d_,
                                  int16_t gap_score,
                                  int16_t mismatch_score,
                                  int16_t match_score,
                                  uint32_t max_sequences_per_poa,
                                  uint16_t* sequence_begin_nodes_ids_d,
                                  uint16_t* outgoing_edges_coverage_d,
                                  uint16_t* outgoing_edges_coverage_count_d)
{
    // shared error indicator within a warp
    bool warp_error = false;

    int32_t nwindows_per_block = TPB / WARP_SIZE;
    int32_t warp_idx           = threadIdx.x / WARP_SIZE;
    int32_t lane_idx           = threadIdx.x % WARP_SIZE;
    int32_t window_idx         = blockIdx.x * nwindows_per_block + warp_idx;

    if (window_idx >= total_windows)
        return;

    // These are not being changed to int32_t to make use of larger range
    // without having to use 2 registers which would be needed for 64bit
    uint32_t max_nodes_per_window = cuda_banded_alignment ? CUDAPOA_MAX_NODES_PER_WINDOW_BANDED : CUDAPOA_MAX_NODES_PER_WINDOW;
    uint32_t max_graph_dimension  = cuda_banded_alignment ? CUDAPOA_MAX_MATRIX_GRAPH_DIMENSION_BANDED : CUDAPOA_MAX_MATRIX_GRAPH_DIMENSION;

    // Find the buffer offsets for each thread within the global memory buffers.
    uint8_t* nodes                        = &nodes_d[max_nodes_per_window * window_idx];
    uint16_t* incoming_edges              = &incoming_edges_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_EDGES];
    uint16_t* incoming_edge_count         = &incoming_edge_count_d[window_idx * max_nodes_per_window];
    uint16_t* outoing_edges               = &outgoing_edges_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_EDGES];
    uint16_t* outgoing_edge_count         = &outgoing_edge_count_d[window_idx * max_nodes_per_window];
    uint16_t* incoming_edge_weights       = &incoming_edge_w_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_EDGES];
    uint16_t* outgoing_edge_weights       = &outgoing_edge_w_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_EDGES];
    uint16_t* sorted_poa                  = &sorted_poa_d[window_idx * max_nodes_per_window];
    uint16_t* node_id_to_pos              = &node_id_to_pos_d[window_idx * max_nodes_per_window];
    uint16_t* node_alignments             = &node_alignments_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_ALIGNMENTS];
    uint16_t* node_alignment_count        = &node_alignment_count_d[window_idx * max_nodes_per_window];
    uint16_t* sorted_poa_local_edge_count = &sorted_poa_local_edge_count_d[window_idx * max_nodes_per_window];

    int32_t scores_width = window_details_d[window_idx].scores_width;
    size_t scores_offset = window_details_d[window_idx].scores_offset * max_graph_dimension;

    int16_t* scores = 0;
    if (cuda_banded_alignment)
        scores = &scores_d[max_graph_dimension * CUDAPOA_BANDED_MAX_MATRIX_SEQUENCE_DIMENSION * window_idx];
    else
        scores = &scores_d[scores_offset];

    int16_t* alignment_graph       = &alignment_graph_d[max_graph_dimension * window_idx];
    int16_t* alignment_read        = &alignment_read_d[max_graph_dimension * window_idx];
    uint16_t* node_coverage_counts = &node_coverage_counts_d_[max_nodes_per_window * window_idx];

#ifdef SPOA_ACCURATE
    uint8_t* node_marks       = &node_marks_d_[max_nodes_per_window * window_idx];
    bool* check_aligned_nodes = &check_aligned_nodes_d_[max_nodes_per_window * window_idx];
    uint16_t* nodes_to_visit  = &nodes_to_visit_d_[max_nodes_per_window * window_idx];
#endif

    uint16_t* sequence_lengths = &sequence_lengths_d[window_details_d[window_idx].seq_len_buffer_offset];

    uint32_t num_sequences = window_details_d[window_idx].num_seqs;
    uint8_t* sequence      = &sequences_d[window_details_d[window_idx].seq_starts];
    int8_t* base_weights   = &base_weights_d[window_details_d[window_idx].seq_starts];

    uint8_t* consensus = &consensus_d[window_idx * CUDAPOA_MAX_CONSENSUS_SIZE];

    uint16_t* sequence_begin_nodes_ids      = nullptr;
    uint16_t* outgoing_edges_coverage       = nullptr;
    uint16_t* outgoing_edges_coverage_count = nullptr;

    if (msa)
    {
        sequence_begin_nodes_ids      = &sequence_begin_nodes_ids_d[window_idx * max_sequences_per_poa];
        outgoing_edges_coverage       = &outgoing_edges_coverage_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_EDGES * max_sequences_per_poa];
        outgoing_edges_coverage_count = &outgoing_edges_coverage_count_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_EDGES];
    }

    if (lane_idx == 0)
    {
        // Create backbone for window based on first sequence in window.
        nodes[0]                                     = sequence[0];
        sorted_poa[0]                                = 0;
        incoming_edge_count[0]                       = 0;
        node_alignment_count[0]                      = 0;
        node_id_to_pos[0]                            = 0;
        outgoing_edge_count[sequence_lengths[0] - 1] = 0;
        incoming_edge_weights[0]                     = base_weights[0];
        node_coverage_counts[0]                      = 1;
        if (msa)
        {
            sequence_begin_nodes_ids[0] = 0;
        }

        //Build the rest of the graphs
        for (uint16_t nucleotide_idx = 1; nucleotide_idx < sequence_lengths[0]; nucleotide_idx++)
        {
            nodes[nucleotide_idx]                                          = sequence[nucleotide_idx];
            sorted_poa[nucleotide_idx]                                     = nucleotide_idx;
            outoing_edges[(nucleotide_idx - 1) * CUDAPOA_MAX_NODE_EDGES]   = nucleotide_idx;
            outgoing_edge_count[nucleotide_idx - 1]                        = 1;
            incoming_edges[nucleotide_idx * CUDAPOA_MAX_NODE_EDGES]        = nucleotide_idx - uint16_t(1);
            incoming_edge_weights[nucleotide_idx * CUDAPOA_MAX_NODE_EDGES] = base_weights[nucleotide_idx - 1] + base_weights[nucleotide_idx];
            incoming_edge_count[nucleotide_idx]                            = 1;
            node_alignment_count[nucleotide_idx]                           = 0;
            node_id_to_pos[nucleotide_idx]                                 = nucleotide_idx;
            node_coverage_counts[nucleotide_idx]                           = 1;
            if (msa)
            {
                outgoing_edges_coverage[(nucleotide_idx - 1) * CUDAPOA_MAX_NODE_EDGES * max_sequences_per_poa] = 0;
                outgoing_edges_coverage_count[(nucleotide_idx - 1) * CUDAPOA_MAX_NODE_EDGES]                   = 1;
            }
        }

        // Clear error code for window.
        consensus[0] = CUDAPOA_KERNEL_NOERROR_ENCOUNTERED;
    }

    __syncwarp();

    // Align each subsequent read, add alignment to graph, run topoligical sort.
    for (uint16_t s = 1; s < num_sequences; s++)
    {
        uint16_t seq_len = sequence_lengths[s];
        sequence += sequence_lengths[s - 1];     // increment the pointer so it is pointing to correct sequence data
        base_weights += sequence_lengths[s - 1]; // increment the pointer so it is pointing to correct sequence data

        if (lane_idx == 0)
        {
            if (sequence_lengths[0] >= CUDAPOA_MAX_NODES_PER_WINDOW)
            {
                consensus[0] = CUDAPOA_KERNEL_ERROR_ENCOUNTERED;
                consensus[1] = static_cast<uint8_t>(StatusType::node_count_exceeded_maximum_graph_size);
                warp_error   = true;
            }
        }

        warp_error = __shfl_sync(FULL_MASK, warp_error, 0);
        if (warp_error)
        {
            return;
        }

        // Run Needleman-Wunsch alignment between graph and new sequence.
        uint16_t alignment_length;

        if (cuda_banded_alignment)
        {
            alignment_length = runNeedlemanWunschBanded<uint8_t, uint16_t, int16_t>(nodes,
                                                                                    sorted_poa,
                                                                                    node_id_to_pos,
                                                                                    sequence_lengths[0],
                                                                                    incoming_edge_count,
                                                                                    incoming_edges,
                                                                                    outgoing_edge_count,
                                                                                    outoing_edges,
                                                                                    sequence,
                                                                                    seq_len,
                                                                                    scores,
                                                                                    alignment_graph,
                                                                                    alignment_read,
                                                                                    gap_score,
                                                                                    mismatch_score,
                                                                                    match_score);
        }
        else
        {
            alignment_length = runNeedlemanWunsch<uint8_t, uint16_t, int16_t>(nodes,
                                                                              sorted_poa,
                                                                              node_id_to_pos,
                                                                              sequence_lengths[0],
                                                                              incoming_edge_count,
                                                                              incoming_edges,
                                                                              outgoing_edge_count,
                                                                              outoing_edges,
                                                                              sequence,
                                                                              seq_len,
                                                                              scores,
                                                                              scores_width,
                                                                              alignment_graph,
                                                                              alignment_read,
                                                                              gap_score,
                                                                              mismatch_score,
                                                                              match_score);
        }

        __syncwarp();

        if (alignment_length == UINT16_MAX)
        {
            if (lane_idx == 0)
            {
                consensus[0] = CUDAPOA_KERNEL_ERROR_ENCOUNTERED;
                consensus[1] = static_cast<uint8_t>(StatusType::loop_count_exceeded_upper_bound);
            }
            return;
        }

        if (lane_idx == 0)
        {

            // Add alignment to graph.
            uint16_t new_node_count;
            uint8_t error_code = addAlignmentToGraph<msa>(new_node_count,
                                                          nodes, sequence_lengths[0],
                                                          node_alignments, node_alignment_count,
                                                          incoming_edges, incoming_edge_count,
                                                          outoing_edges, outgoing_edge_count,
                                                          incoming_edge_weights, outgoing_edge_weights,
                                                          alignment_length,
                                                          sorted_poa, alignment_graph,
                                                          sequence, alignment_read,
                                                          node_coverage_counts,
                                                          base_weights,
                                                          (sequence_begin_nodes_ids + s),
                                                          outgoing_edges_coverage,
                                                          outgoing_edges_coverage_count,
                                                          s,
                                                          max_sequences_per_poa);

            if (error_code != 0)
            {
                consensus[0] = CUDAPOA_KERNEL_ERROR_ENCOUNTERED;
                consensus[1] = error_code;
                warp_error   = true;
            }
            else
            {
                sequence_lengths[0] = new_node_count;
                // Run a topsort on the graph.
#ifdef SPOA_ACCURATE
                // Exactly matches racon CPU results
                raconTopologicalSortDeviceUtil(sorted_poa,
                                               node_id_to_pos,
                                               new_node_count,
                                               incoming_edge_count,
                                               incoming_edges,
                                               node_alignment_count,
                                               node_alignments,
                                               node_marks,
                                               check_aligned_nodes,
                                               nodes_to_visit,
                                               cuda_banded_alignment);
#else
                // Faster top sort
                topologicalSortDeviceUtil(sorted_poa,
                                          node_id_to_pos,
                                          new_node_count,
                                          incoming_edge_count,
                                          outoing_edges,
                                          outgoing_edge_count,
                                          sorted_poa_local_edge_count);
#endif
            }
        }

        __syncwarp();

        warp_error = __shfl_sync(FULL_MASK, warp_error, 0);
        if (warp_error)
        {
            return;
        }
    }
}

// Host function call for POA kernel.
void generatePOA(claragenomics::cudapoa::OutputDetails* output_details_d,
                 claragenomics::cudapoa::InputDetails* input_details_d,
                 int32_t total_windows,
                 cudaStream_t stream,
                 claragenomics::cudapoa::AlignmentDetails* alignment_details_d,
                 claragenomics::cudapoa::GraphDetails* graph_details_d,
                 int16_t gap_score,
                 int16_t mismatch_score,
                 int16_t match_score,
                 bool cuda_banded_alignment,
                 uint32_t max_sequences_per_poa,
                 int8_t output_mask)
{
    // unpack output details
    uint8_t* consensus_d                  = output_details_d->consensus;
    uint16_t* coverage_d                  = output_details_d->coverage;
    uint8_t* multiple_sequence_alignments = output_details_d->multiple_sequence_alignments;

    // unpack input details
    uint8_t* sequences_d               = input_details_d->sequences;
    int8_t* base_weights_d             = input_details_d->base_weights;
    uint16_t* sequence_lengths_d       = input_details_d->sequence_lengths;
    WindowDetails* window_details_d    = input_details_d->window_details;
    uint16_t* sequence_begin_nodes_ids = input_details_d->sequence_begin_nodes_ids;

    // unpack alignment details
    int16_t* scores          = alignment_details_d->scores;
    int16_t* alignment_graph = alignment_details_d->alignment_graph;
    int16_t* alignment_read  = alignment_details_d->alignment_read;
    // unpack graph details
    uint8_t* nodes                          = graph_details_d->nodes;
    uint16_t* node_alignments               = graph_details_d->node_alignments;
    uint16_t* node_alignment_count          = graph_details_d->node_alignment_count;
    uint16_t* incoming_edges                = graph_details_d->incoming_edges;
    uint16_t* incoming_edge_count           = graph_details_d->incoming_edge_count;
    uint16_t* outgoing_edges                = graph_details_d->outgoing_edges;
    uint16_t* outgoing_edge_count           = graph_details_d->outgoing_edge_count;
    uint16_t* incoming_edge_w               = graph_details_d->incoming_edge_weights;
    uint16_t* outgoing_edge_w               = graph_details_d->outgoing_edge_weights;
    uint16_t* sorted_poa                    = graph_details_d->sorted_poa;
    uint16_t* node_id_to_pos                = graph_details_d->sorted_poa_node_map;
    uint16_t* sorted_poa_local_edge_count   = graph_details_d->sorted_poa_local_edge_count;
    int32_t* consensus_scores               = graph_details_d->consensus_scores;
    int16_t* consensus_predecessors         = graph_details_d->consensus_predecessors;
    uint8_t* node_marks                     = graph_details_d->node_marks;
    bool* check_aligned_nodes               = graph_details_d->check_aligned_nodes;
    uint16_t* nodes_to_visit                = graph_details_d->nodes_to_visit;
    uint16_t* node_coverage_counts          = graph_details_d->node_coverage_counts;
    uint16_t* outgoing_edges_coverage       = graph_details_d->outgoing_edges_coverage;
    uint16_t* outgoing_edges_coverage_count = graph_details_d->outgoing_edges_coverage_count;
    int16_t* node_id_to_msa_pos             = graph_details_d->node_id_to_msa_pos;

    int32_t nwindows_per_block = CUDAPOA_THREADS_PER_BLOCK / WARP_SIZE;
    int32_t nblocks            = (total_windows + nwindows_per_block - 1) / nwindows_per_block;

    CGA_CU_CHECK_ERR(cudaDeviceSetCacheConfig(cudaFuncCachePreferL1));

    int32_t consensus_num_blocks = (total_windows / CUDAPOA_MAX_CONSENSUS_PER_BLOCK) + 1;
    if (cuda_banded_alignment)
    {
        if (output_mask & OutputType::consensus)
        {
            generatePOAKernel<CUDAPOA_BANDED_THREADS_PER_BLOCK, true, false>
                <<<total_windows, CUDAPOA_BANDED_THREADS_PER_BLOCK, 0, stream>>>(consensus_d,
                                                                                 sequences_d,
                                                                                 base_weights_d,
                                                                                 sequence_lengths_d,
                                                                                 window_details_d,
                                                                                 total_windows,
                                                                                 scores,
                                                                                 alignment_graph,
                                                                                 alignment_read,
                                                                                 nodes,
                                                                                 incoming_edges,
                                                                                 incoming_edge_count,
                                                                                 outgoing_edges,
                                                                                 outgoing_edge_count,
                                                                                 incoming_edge_w,
                                                                                 outgoing_edge_w,
                                                                                 sorted_poa,
                                                                                 node_id_to_pos,
                                                                                 node_alignments,
                                                                                 node_alignment_count,
                                                                                 sorted_poa_local_edge_count,
                                                                                 node_marks,
                                                                                 check_aligned_nodes,
                                                                                 nodes_to_visit,
                                                                                 node_coverage_counts,
                                                                                 gap_score,
                                                                                 mismatch_score,
                                                                                 match_score,
                                                                                 max_sequences_per_poa,
                                                                                 sequence_begin_nodes_ids,
                                                                                 outgoing_edges_coverage,
                                                                                 outgoing_edges_coverage_count);
            CGA_CU_CHECK_ERR(cudaPeekAtLastError());

            generateConsensusKernel<true>
                <<<consensus_num_blocks, CUDAPOA_MAX_CONSENSUS_PER_BLOCK, 0, stream>>>(consensus_d,
                                                                                       coverage_d,
                                                                                       sequence_lengths_d,
                                                                                       window_details_d,
                                                                                       total_windows,
                                                                                       nodes,
                                                                                       incoming_edges,
                                                                                       incoming_edge_count,
                                                                                       outgoing_edges,
                                                                                       outgoing_edge_count,
                                                                                       incoming_edge_w,
                                                                                       sorted_poa,
                                                                                       node_id_to_pos,
                                                                                       node_alignments,
                                                                                       node_alignment_count,
                                                                                       consensus_scores,
                                                                                       consensus_predecessors,
                                                                                       node_coverage_counts);
            CGA_CU_CHECK_ERR(cudaPeekAtLastError());
        }
        if (output_mask & OutputType::msa)
        {
            generatePOAKernel<CUDAPOA_BANDED_THREADS_PER_BLOCK, true, true>
                <<<total_windows, CUDAPOA_BANDED_THREADS_PER_BLOCK, 0, stream>>>(consensus_d,
                                                                                 sequences_d,
                                                                                 base_weights_d,
                                                                                 sequence_lengths_d,
                                                                                 window_details_d,
                                                                                 total_windows,
                                                                                 scores,
                                                                                 alignment_graph,
                                                                                 alignment_read,
                                                                                 nodes,
                                                                                 incoming_edges,
                                                                                 incoming_edge_count,
                                                                                 outgoing_edges,
                                                                                 outgoing_edge_count,
                                                                                 incoming_edge_w,
                                                                                 outgoing_edge_w,
                                                                                 sorted_poa,
                                                                                 node_id_to_pos,
                                                                                 node_alignments,
                                                                                 node_alignment_count,
                                                                                 sorted_poa_local_edge_count,
                                                                                 node_marks,
                                                                                 check_aligned_nodes,
                                                                                 nodes_to_visit,
                                                                                 node_coverage_counts,
                                                                                 gap_score,
                                                                                 mismatch_score,
                                                                                 match_score,
                                                                                 max_sequences_per_poa,
                                                                                 sequence_begin_nodes_ids,
                                                                                 outgoing_edges_coverage,
                                                                                 outgoing_edges_coverage_count);
            CGA_CU_CHECK_ERR(cudaPeekAtLastError());

            generateMSAKernel<true>
                <<<total_windows, max_sequences_per_poa, 0, stream>>>(nodes,
                                                                      consensus_d,
                                                                      window_details_d,
                                                                      incoming_edge_count,
                                                                      incoming_edges,
                                                                      outgoing_edge_count,
                                                                      outgoing_edges,
                                                                      outgoing_edges_coverage,
                                                                      outgoing_edges_coverage_count,
                                                                      node_id_to_msa_pos,
                                                                      sequence_begin_nodes_ids,
                                                                      multiple_sequence_alignments,
                                                                      sequence_lengths_d,
                                                                      sorted_poa,
                                                                      node_alignments,
                                                                      node_alignment_count,
                                                                      max_sequences_per_poa,
                                                                      node_id_to_pos,
                                                                      node_marks,
                                                                      check_aligned_nodes,
                                                                      nodes_to_visit);
            CGA_CU_CHECK_ERR(cudaPeekAtLastError());
        }
    }
    else
    {
        if (output_mask & OutputType::consensus)
        {
            generatePOAKernel<CUDAPOA_THREADS_PER_BLOCK, false, false>
                <<<nblocks, CUDAPOA_THREADS_PER_BLOCK, 0, stream>>>(consensus_d,
                                                                    sequences_d,
                                                                    base_weights_d,
                                                                    sequence_lengths_d,
                                                                    window_details_d,
                                                                    total_windows,
                                                                    scores,
                                                                    alignment_graph,
                                                                    alignment_read,
                                                                    nodes,
                                                                    incoming_edges,
                                                                    incoming_edge_count,
                                                                    outgoing_edges,
                                                                    outgoing_edge_count,
                                                                    incoming_edge_w,
                                                                    outgoing_edge_w,
                                                                    sorted_poa,
                                                                    node_id_to_pos,
                                                                    node_alignments,
                                                                    node_alignment_count,
                                                                    sorted_poa_local_edge_count,
                                                                    node_marks,
                                                                    check_aligned_nodes,
                                                                    nodes_to_visit,
                                                                    node_coverage_counts,
                                                                    gap_score,
                                                                    mismatch_score,
                                                                    match_score,
                                                                    max_sequences_per_poa,
                                                                    sequence_begin_nodes_ids,
                                                                    outgoing_edges_coverage,
                                                                    outgoing_edges_coverage_count);
            CGA_CU_CHECK_ERR(cudaPeekAtLastError());

            generateConsensusKernel<false>
                <<<consensus_num_blocks, CUDAPOA_MAX_CONSENSUS_PER_BLOCK, 0, stream>>>(consensus_d,
                                                                                       coverage_d,
                                                                                       sequence_lengths_d,
                                                                                       window_details_d,
                                                                                       total_windows,
                                                                                       nodes,
                                                                                       incoming_edges,
                                                                                       incoming_edge_count,
                                                                                       outgoing_edges,
                                                                                       outgoing_edge_count,
                                                                                       incoming_edge_w,
                                                                                       sorted_poa,
                                                                                       node_id_to_pos,
                                                                                       node_alignments,
                                                                                       node_alignment_count,
                                                                                       consensus_scores,
                                                                                       consensus_predecessors,
                                                                                       node_coverage_counts);
            CGA_CU_CHECK_ERR(cudaPeekAtLastError());
        }
        if (output_mask & OutputType::msa)
        {
            generatePOAKernel<CUDAPOA_THREADS_PER_BLOCK, false, true>
                <<<nblocks, CUDAPOA_THREADS_PER_BLOCK, 0, stream>>>(consensus_d,
                                                                    sequences_d,
                                                                    base_weights_d,
                                                                    sequence_lengths_d,
                                                                    window_details_d,
                                                                    total_windows,
                                                                    scores,
                                                                    alignment_graph,
                                                                    alignment_read,
                                                                    nodes,
                                                                    incoming_edges,
                                                                    incoming_edge_count,
                                                                    outgoing_edges,
                                                                    outgoing_edge_count,
                                                                    incoming_edge_w,
                                                                    outgoing_edge_w,
                                                                    sorted_poa,
                                                                    node_id_to_pos,
                                                                    node_alignments,
                                                                    node_alignment_count,
                                                                    sorted_poa_local_edge_count,
                                                                    node_marks,
                                                                    check_aligned_nodes,
                                                                    nodes_to_visit,
                                                                    node_coverage_counts,
                                                                    gap_score,
                                                                    mismatch_score,
                                                                    match_score,
                                                                    max_sequences_per_poa,
                                                                    sequence_begin_nodes_ids,
                                                                    outgoing_edges_coverage,
                                                                    outgoing_edges_coverage_count);
            CGA_CU_CHECK_ERR(cudaPeekAtLastError());

            generateMSAKernel<false>
                <<<total_windows, max_sequences_per_poa, 0, stream>>>(nodes,
                                                                      consensus_d,
                                                                      window_details_d,
                                                                      incoming_edge_count,
                                                                      incoming_edges,
                                                                      outgoing_edge_count,
                                                                      outgoing_edges,
                                                                      outgoing_edges_coverage,
                                                                      outgoing_edges_coverage_count,
                                                                      node_id_to_msa_pos,
                                                                      sequence_begin_nodes_ids,
                                                                      multiple_sequence_alignments,
                                                                      sequence_lengths_d,
                                                                      sorted_poa,
                                                                      node_alignments,
                                                                      node_alignment_count,
                                                                      max_sequences_per_poa,
                                                                      node_id_to_pos,
                                                                      node_marks,
                                                                      check_aligned_nodes,
                                                                      nodes_to_visit);
            CGA_CU_CHECK_ERR(cudaPeekAtLastError());
        }
    }
}

} // namespace cudapoa

} // namespace claragenomics

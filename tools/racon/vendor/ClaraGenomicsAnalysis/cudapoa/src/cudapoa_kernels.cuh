/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

// Header for for CUDA POA host kernel wrappers.

#pragma once

#include <claragenomics/cudapoa/cudapoa.hpp>

#include <stdint.h>
#include <cuda_runtime_api.h>
#include <stdio.h>
#include <string>
#include <vector>

// Maximum vnumber of edges per node.
#define CUDAPOA_MAX_NODE_EDGES 50

// Maximum number of nodes aligned to each other.
#define CUDAPOA_MAX_NODE_ALIGNMENTS 50

// Maximum number of nodes in a graph, 1 graph per window.
#define CUDAPOA_MAX_NODES_PER_WINDOW 3072
#define CUDAPOA_MAX_NODES_PER_WINDOW_BANDED 4096

// Maximum number of elements in a sequence.
#define CUDAPOA_MAX_SEQUENCE_SIZE 1024

// Maximum size of final consensus
#define CUDAPOA_MAX_CONSENSUS_SIZE 1024

// Maximum vertical dimension of scoring matrix, which stores graph.
// Adding 4 elements more to ensure a 4byte boundary alignment for
// any allocated buffer.
#define CUDAPOA_MAX_MATRIX_GRAPH_DIMENSION (CUDAPOA_MAX_NODES_PER_WINDOW + 4)
#define CUDAPOA_MAX_MATRIX_GRAPH_DIMENSION_BANDED (CUDAPOA_MAX_NODES_PER_WINDOW_BANDED + 4)

// Maximum horizontal dimension of scoring matrix, which stores sequences.
// Adding 4 elements more to ensure a 4byte boundary alignment for
// any allocated buffer.
#define CUDAPOA_MAX_MATRIX_SEQUENCE_DIMENSION (CUDAPOA_MAX_SEQUENCE_SIZE + 4)

// imensions for Banded alignment score matrix
#define WARP_SIZE 32
#define CELLS_PER_THREAD 4
#define CUDAPOA_BAND_WIDTH (CELLS_PER_THREAD * WARP_SIZE)
#define CUDAPOA_BANDED_MATRIX_RIGHT_PADDING (CELLS_PER_THREAD * 2)
#define CUDAPOA_BANDED_MAX_MATRIX_SEQUENCE_DIMENSION (CUDAPOA_BAND_WIDTH + CUDAPOA_BANDED_MATRIX_RIGHT_PADDING)

#define CUDAPOA_THREADS_PER_BLOCK 64
#define CUDAPOA_BANDED_THREADS_PER_BLOCK WARP_SIZE
#define CUDAPOA_MAX_CONSENSUS_PER_BLOCK 512

#define FULL_MASK 0xffffffff
#define CUDAPOA_KERNEL_ERROR_ENCOUNTERED UINT8_MAX
#define CUDAPOA_KERNEL_NOERROR_ENCOUNTERED 0

namespace claragenomics
{

namespace cudapoa
{

/**
 * @brief A struct to hold information about the sequences
 *        inside a window.
 */
typedef struct WindowDetails
{
    /// Number of sequences in the window.
    uint16_t num_seqs;
    /// Offset of first sequence length for specific window
    /// inside global sequence length buffer.
    int32_t seq_len_buffer_offset;
    /// Offset of first sequence content for specific window
    /// inside global sequences buffer.
    int32_t seq_starts;

    /// Offset to the scores buffer for specific window
    size_t scores_offset;

    /// Max column width of the score matrix required for specific window
    int32_t scores_width;
} WindowDetails;

typedef struct OutputDetails
{
    // Buffer pointer for storing consensus.
    uint8_t* consensus;
    // Buffer for coverage of consensus.
    uint16_t* coverage;
    // Buffer for multiple sequence alignments
    uint8_t* multiple_sequence_alignments;
} OutputDetails;

typedef struct InputDetails
{
    // Buffer pointer for input data.
    uint8_t* sequences;
    // Buffer pointer for weights of each base.
    int8_t* base_weights;
    // Buffer for sequence lengths.
    uint16_t* sequence_lengths;
    // Buffer pointers that hold Window Details struct.
    WindowDetails* window_details;
    // Buffer storing begining nodes for sequences
    uint16_t* sequence_begin_nodes_ids;

} InputDetails;

typedef struct AlignmentDetails
{
    // Device buffer for the scoring matrix for all windows.
    int16_t* scores;

    // preallocated size of scores buffer
    size_t scorebuf_alloc_size = 0;

    // Device buffers for alignment backtrace
    int16_t* alignment_graph;
    int16_t* alignment_read;
} AlignmentDetails;

typedef struct GraphDetails
{
    // Device buffer to store nodes of the graph. The node itself is the base
    // (A, T, C, G) and the id of the node is it's position in the buffer.
    uint8_t* nodes;

    // Device buffer to store the list of nodes aligned to a
    // specific node in the graph.
    uint16_t* node_alignments;
    uint16_t* node_alignment_count;

    // Device buffer to store incoming edges to a node.
    uint16_t* incoming_edges;
    uint16_t* incoming_edge_count;

    // Device buffer to store outgoing edges from a node.
    uint16_t* outgoing_edges;
    uint16_t* outgoing_edge_count;

    // Devices buffers to store incoming and outgoing edge weights.
    uint16_t* incoming_edge_weights;
    uint16_t* outgoing_edge_weights;

    // Device buffer to store the topologically sorted graph. Each element
    // of this buffer is an ID of the node.
    uint16_t* sorted_poa;

    // Device buffer that maintains a mapping between the node ID and its
    // position in the topologically sorted graph.
    uint16_t* sorted_poa_node_map;

    // Device buffer used during topological sort to store incoming
    // edge counts for nodes.
    uint16_t* sorted_poa_local_edge_count;

    // Device buffer to store scores calculated during traversal
    // of graph for consensus generation.
    int32_t* consensus_scores;

    // Device buffer to store the predecessors of nodes during
    // graph traversal.
    int16_t* consensus_predecessors;

    // Device buffer to store node marks when performing spoa accurate topsort.
    uint8_t* node_marks;

    // Device buffer to store check for aligned nodes.
    bool* check_aligned_nodes;

    // Device buffer to store stack for nodes to be visited.
    uint16_t* nodes_to_visit;

    // Device buffer for storing coverage of each node in graph.
    uint16_t* node_coverage_counts;

    uint16_t* outgoing_edges_coverage;
    uint16_t* outgoing_edges_coverage_count;
    int16_t* node_id_to_msa_pos;

} GraphDetails;

/**
 * @brief The host function which calls the kernel that runs the partial order alignment
 *        algorithm.
 *
 * @param[out] output_details_d           Struct that contains output buffers, including the following fields:
 *             consensus                  Device buffer for generated consensus
 *             coverage                   Device buffer for coverage of each base in consensus
 *
 * @param[in] input_details_d             Struct that contains input buffers, including the following fields:
 *            sequences                   Device buffer with sequences for all windows
 *            base_weight                 Device buffer with weights per base for all windows
 *            sequence_lengths            Device buffer sequence lengths
 *            window_details              Device buffer with structs encapsulating sequence details per window
 *
 * @param[in] total_window                Total number of windows to process
 * @param[in] stream                      Stream to run kernel on
 *
 * @param[in] alignment_details_d         Struct that contains alignment related buffers, including the following fields:
 *            scores                      Device scratch space that scores alignment matrix score
 *            alignment_graph             Device scratch space for backtrace alignment of graph
 *            alignment_read              Device scratch space for backtrace alignment of sequence
 *
 * @param[in] graph_details_d             Struct that contains graph related buffers, including the following fields:
 *            nodes                       Device scratch space for storing unique nodes in graph
 *            incoming_edges              Device scratch space for storing incoming edges per node
 *            incoming_edges_count        Device scratch space for storing number of incoming edges per node
 *            outgoing_edges              Device scratch space for storing outgoing edges per node
 *            outgoing_edges_count        Device scratch space for storing number of outgoing edges per node
 *            incoming_edge_w             Device scratch space for storing weight of incoming edges
 *            outgoing_edge_w             Device scratch space for storing weight of outgoing edges
 *            sorted_poa                  Device scratch space for storing sorted graph
 *            node_id_to_pos              Device scratch space for mapping node ID to position in graph
 *            node_alignments             Device scratch space for storing alignment nodes per node in graph
 *            node_alignment_count        Device scratch space for storing number of aligned nodes
 *            sorted_poa_local_edge_count Device scratch space for maintaining edge counts during topological sort
 *            consensus_scores            Device scratch space for storing score of each node while traversing graph during consensus
 *            consensus_predecessors      Device scratch space for storing predecessors of nodes while traversing graph during consensus
 *            node_marks                  Device scratch space for storing node marks when running spoa accurate top sort
 *            check_aligned_nodes         Device scratch space for storing check for aligned nodes
 *            nodes_to_visit              Device scratch space for storing stack of nodes to be visited in topsort
 *            node_coverage_counts        Device scratch space for storing coverage count for each node in graph
 *
 * @param[in] gap_score                   Score for inserting gap into alignment
 * @param[in] mismatch_score              Score for finding a mismatch in alignment
 * @param[in] match_score                 Score for finding a match in alignment
 * @param[in] banded_alignment            Use banded alignment
 */

void generatePOA(claragenomics::cudapoa::OutputDetails* output_details_d,
                 claragenomics::cudapoa::InputDetails* Input_details_d,
                 int32_t total_windows,
                 cudaStream_t stream,
                 claragenomics::cudapoa::AlignmentDetails* alignment_details_d,
                 claragenomics::cudapoa::GraphDetails* graph_details_d,
                 int16_t gap_score,
                 int16_t mismatch_score,
                 int16_t match_score,
                 bool banded_alignment,
                 uint32_t max_sequences_per_poa,
                 int8_t output_mask);

// host function that calls runTopSortKernel
void runTopSort(uint16_t* sorted_poa,
                uint16_t* sorted_poa_node_map,
                uint16_t node_count,
                uint16_t* incoming_edge_count,
                uint16_t* outgoing_edges,
                uint16_t* outgoing_edge_count,
                uint16_t* local_incoming_edge_count);

// Host function that calls the kernel
void addAlignment(uint8_t* nodes,
                  uint16_t* node_count,
                  uint16_t* node_alignments, uint16_t* node_alignment_count,
                  uint16_t* incoming_edges, uint16_t* incoming_edge_count,
                  uint16_t* outgoing_edges, uint16_t* outgoing_edge_count,
                  uint16_t* incoming_edge_w, uint16_t* outgoing_edge_w,
                  uint16_t* alignment_length,
                  uint16_t* graph,
                  int16_t* alignment_graph,
                  uint8_t* read,
                  int16_t* alignment_read,
                  uint16_t* node_coverage_counts,
                  int8_t* base_weights,
                  uint16_t* sequence_begin_nodes_ids,
                  uint16_t* outgoing_edges_coverage,
                  uint16_t* outgoing_edges_coverage_count,
                  uint16_t s,
                  uint32_t max_sequences_per_poa);

// Host function that calls the kernel
void runNW(uint8_t* nodes,
           uint16_t* graph,
           uint16_t* node_id_to_pos,
           uint16_t graph_count,
           uint16_t* incoming_edge_count,
           uint16_t* incoming_edges,
           uint16_t* outgoing_edge_count,
           uint16_t* outgoing_edges,
           uint8_t* read,
           uint16_t read_count,
           int16_t* scores,
           int32_t scores_width,
           int16_t* alignment_graph,
           int16_t* alignment_read,
           int16_t gap_score,
           int16_t mismatch_score,
           int16_t match_score,
           uint16_t* algined_nodes);

void generateConsensusTestHost(uint8_t* nodes,
                               uint16_t node_count,
                               uint16_t* graph,
                               uint16_t* node_id_to_pos,
                               uint16_t* incoming_edges,
                               uint16_t* incoming_edge_count,
                               uint16_t* outgoing_edges,
                               uint16_t* outgoing_edge_count,
                               uint16_t* incoming_edge_w,
                               int16_t* predecessors,
                               int32_t* scores,
                               uint8_t* consensus,
                               uint16_t* coverage,
                               uint16_t* node_coverage_counts,
                               uint16_t* node_alignments,
                               uint16_t* node_alignment_count);
} // namespace cudapoa

} // namespace claragenomics

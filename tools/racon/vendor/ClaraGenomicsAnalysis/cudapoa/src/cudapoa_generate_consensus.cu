/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "cudapoa_kernels.cuh"

#include <claragenomics/utils/cudautils.hpp>

#include <stdio.h>

namespace claragenomics
{

namespace cudapoa
{

__device__
    uint16_t
    branchCompletion(uint16_t max_score_id_pos,
                     uint8_t* nodes,
                     uint16_t node_count,
                     uint16_t* graph,
                     uint16_t* incoming_edges,
                     uint16_t* incoming_edge_count,
                     uint16_t* outgoing_edges,
                     uint16_t* outgoing_edge_count,
                     uint16_t* incoming_edge_w,
                     int32_t* scores,
                     int16_t* predecessors)
{
    uint16_t node_id = graph[max_score_id_pos];

    // Go through all the outgoing edges of the node, and for
    // each of the end nodes of the edges clear the scores
    // for all the _other_ nodes that had edges to that end node.
    uint16_t out_edges = outgoing_edge_count[node_id];
    for (uint16_t oe = 0; oe < out_edges; oe++)
    {
        uint16_t out_node_id       = outgoing_edges[node_id * CUDAPOA_MAX_NODE_EDGES + oe];
        uint16_t out_node_in_edges = incoming_edge_count[out_node_id];
        for (uint16_t ie = 0; ie < out_node_in_edges; ie++)
        {
            uint16_t id = incoming_edges[out_node_id * CUDAPOA_MAX_NODE_EDGES + ie];
            if (id != node_id)
            {
                scores[id] = -1;
            }
        }
    }

    int32_t max_score     = 0;
    uint16_t max_score_id = 0;
    // Run the same node weight traversal algorithm as always, to find the new
    // node with maximum weight.
    // We can start from the very next position in the graph rank because
    // the graph is topologically sorted and hence guarantees that successor of the current max
    // node will be processed again.
    for (uint16_t graph_pos = max_score_id_pos + 1; graph_pos < node_count; graph_pos++)
    {
        node_id = graph[graph_pos];

        predecessors[node_id] = -1;
        int32_t score_node_id = -1;

        uint16_t in_edges = incoming_edge_count[node_id];
        for (uint16_t e = 0; e < in_edges; e++)
        {
            uint16_t begin_node_id = incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES + e];
            if (scores[begin_node_id] == -1)
            {
                continue;
            }

            int32_t edge_w = static_cast<int32_t>(incoming_edge_w[node_id * CUDAPOA_MAX_NODE_EDGES + e]);
            if (score_node_id < edge_w ||
                (score_node_id == edge_w &&
                 scores[predecessors[node_id]] <= scores[begin_node_id]))
            {
                score_node_id         = edge_w;
                predecessors[node_id] = begin_node_id;
            }
        }

        if (predecessors[node_id] != -1)
        {
            score_node_id += scores[predecessors[node_id]];
        }

        if (max_score <= score_node_id)
        {
            max_score    = score_node_id;
            max_score_id = node_id;
        }
        //printf("max score %d, max score id %d, node id %d score %d\n", max_score, max_score_id, node_id, score_node_id);

        scores[node_id] = score_node_id;
    }

    return max_score_id;
}

/**
 * @brief Device function to generate consensus from a given graph.
 *        The input graph needs to be topologically sorted.
 *
 * @param[in] nodes                 Device buffer with unique nodes in graph
 * @param[in] node_count            Number of nodes in graph
 * @param[in] graph                 Device buffer with sorted graph
 * @param[in] node_id_to_pos        Device scratch space for mapping node ID to position in graph
 * @param[in] incoming_edges        Device buffer with incoming edges per node
 * @param[in] incoming_edges_count  Device buffer with number of incoming edges per node
 * @param[in] outgoing_edges        Device buffer with outgoing edges per node
 * @param[in] outgoing_edges_count  Device buffer with number of outgoing edges per node
 * @param[in] predecessors          Device buffer with predecessors of nodes while traversing graph during consensus
 * @param[in] scores                Device buffer with score of each node while traversing graph during consensus
 * @param[out] consensus            Device buffer for generated consensus
 * @param[out] coverate             Device buffer for coverage of each base in consensus
 * @param[out] node_coverage_counts Device buffer with coverage of each base in graph
 * @param[in] node_alignments       Device buffer with aligned nodes for each node in graph
 * @param[in] node_alignment)count  Device buffer with aligned nodes count for each node in graph
 */
__device__ void generateConsensus(uint8_t* nodes,
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
                                  uint16_t* node_alignment_count)
{
    // Initialize scores and predecessors to default value.
    for (uint16_t i = 0; i < node_count; i++)
    {
        predecessors[i] = -1;
        scores[i]       = -1;
    }

    uint16_t max_score_id = 0;
    int32_t max_score     = -1;

    for (uint16_t graph_pos = 0; graph_pos < node_count; graph_pos++)
    {
        uint16_t node_id  = graph[graph_pos];
        uint16_t in_edges = incoming_edge_count[node_id];

        int32_t score_node_id = scores[node_id];

        // For each node, go through it's incoming edges.
        // If the weight of any of the incoming edges is greater
        // than the score of the current node, or if the weight is equal
        // but the predecessors of the edge are heavier than the current node,
        // then update the score of the node to be the incoming edge weight.
        for (uint16_t e = 0; e < in_edges; e++)
        {
            int32_t edge_w         = static_cast<int32_t>(incoming_edge_w[node_id * CUDAPOA_MAX_NODE_EDGES + e]);
            uint16_t begin_node_id = incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES + e];
            if (score_node_id < edge_w ||
                (score_node_id == edge_w &&
                 scores[predecessors[node_id]] <= scores[begin_node_id]))
            {
                score_node_id         = edge_w;
                predecessors[node_id] = begin_node_id;
            }
        }

        // Then update the score of the node to be the sum
        // of the score of the predecessor and itself.
        if (predecessors[node_id] != -1)
        {
            score_node_id += scores[predecessors[node_id]];
        }

        // Keep track of the highest weighted node.
        if (max_score <= score_node_id)
        {
            max_score_id = node_id;
            max_score    = score_node_id;
        }
        //printf("max score %d, max score id %d, node id %d score %d\n", max_score, max_score_id, node_id, score_node_id);

        scores[node_id] = score_node_id;
    }

    // If the node with maximum score isn't a leaf of the graph
    // then run a special branch completion function.
    uint16_t loop_count = 0;
    if (outgoing_edge_count[max_score_id] != 0)
    {
        while (outgoing_edge_count[max_score_id] != 0 && loop_count < node_count)
        {
            max_score_id = branchCompletion(node_id_to_pos[max_score_id],
                                            nodes,
                                            node_count,
                                            graph,
                                            incoming_edges,
                                            incoming_edge_count,
                                            outgoing_edges,
                                            outgoing_edge_count,
                                            incoming_edge_w,
                                            scores,
                                            predecessors);
            loop_count++;
        }
    }

    if (loop_count >= node_count)
    {
        consensus[0] = CUDAPOA_KERNEL_ERROR_ENCOUNTERED;
        consensus[1] = static_cast<uint8_t>(StatusType::loop_count_exceeded_upper_bound);
        return;
    }

    // Use consensus_pos to track which position to put new element in. Clip this to the maximum
    // size of consensus so as not to overwrite other good data.
    uint16_t consensus_pos = 0;
    // Use consensus_count to track how many elements are in consensus. If more than the maximum
    // size, then consensus cannot be properly represented. So throw error.
    uint16_t consensus_count = 0;

    while (predecessors[max_score_id] != -1)
    {
        consensus[consensus_pos] = nodes[max_score_id];
        uint16_t cov             = node_coverage_counts[max_score_id];
        for (uint16_t a = 0; a < node_alignment_count[max_score_id]; a++)
        {
            cov += node_coverage_counts[node_alignments[max_score_id * CUDAPOA_MAX_NODE_ALIGNMENTS + a]];
        }
        coverage[consensus_pos] = cov;
        max_score_id            = predecessors[max_score_id];
        consensus_pos           = min(consensus_pos + 1, CUDAPOA_MAX_CONSENSUS_SIZE - 1);
        consensus_count++;
    }
    consensus[consensus_pos] = nodes[max_score_id];
    uint16_t cov             = node_coverage_counts[max_score_id];
    for (uint16_t a = 0; a < node_alignment_count[max_score_id]; a++)
    {
        cov += node_coverage_counts[node_alignments[max_score_id * CUDAPOA_MAX_NODE_ALIGNMENTS + a]];
    }
    coverage[consensus_pos] = cov;

    // Check consensus count against maximum size.
    if (consensus_count >= (CUDAPOA_MAX_CONSENSUS_SIZE - 1))
    {
        consensus[0] = CUDAPOA_KERNEL_ERROR_ENCOUNTERED;
        consensus[1] = static_cast<uint8_t>(StatusType::exceeded_maximum_sequence_size);
        return;
    }

    // Now we can increment consensus_pos without checking for upper bound because the max length
    // test above guarantees that consensus_pos <= (CUDAPOA_MAX_CONSENSUS_SIZE - 2).
    consensus_pos++;
    // Add EOL character at the end of the string.
    consensus[consensus_pos] = '\0';
}

template <bool cuda_banded_alignment = false>
__global__ void generateConsensusKernel(uint8_t* consensus_d,
                                        uint16_t* coverage_d,
                                        uint16_t* sequence_lengths_d,
                                        claragenomics::cudapoa::WindowDetails* window_details_d,
                                        int32_t total_windows,
                                        uint8_t* nodes_d,
                                        uint16_t* incoming_edges_d,
                                        uint16_t* incoming_edge_count_d,
                                        uint16_t* outgoing_edges_d,
                                        uint16_t* outgoing_edge_count_d,
                                        uint16_t* incoming_edge_w_d,
                                        uint16_t* sorted_poa_d,
                                        uint16_t* node_id_to_pos_d,
                                        uint16_t* node_alignments_d,
                                        uint16_t* node_alignment_count_d,
                                        int32_t* consensus_scores_d,
                                        int16_t* consensus_predecessors_d,
                                        uint16_t* node_coverage_counts_d_)
{
    //each thread will operate on a window
    int32_t window_idx = blockIdx.x * CUDAPOA_MAX_CONSENSUS_PER_BLOCK + threadIdx.x;

    if (window_idx >= total_windows)
        return;

    uint8_t* consensus = &consensus_d[window_idx * CUDAPOA_MAX_CONSENSUS_SIZE];

    if (consensus[0] == CUDAPOA_KERNEL_ERROR_ENCOUNTERED) //error during graph generation
        return;

    int32_t max_nodes_per_window = cuda_banded_alignment ? CUDAPOA_MAX_NODES_PER_WINDOW_BANDED : CUDAPOA_MAX_NODES_PER_WINDOW;

    // Find the buffer offsets for each thread within the global memory buffers.
    uint8_t* nodes                  = &nodes_d[max_nodes_per_window * window_idx];
    uint16_t* incoming_edges        = &incoming_edges_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_EDGES];
    uint16_t* incoming_edge_count   = &incoming_edge_count_d[window_idx * max_nodes_per_window];
    uint16_t* outoing_edges         = &outgoing_edges_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_EDGES];
    uint16_t* outgoing_edge_count   = &outgoing_edge_count_d[window_idx * max_nodes_per_window];
    uint16_t* incoming_edge_weights = &incoming_edge_w_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_EDGES];
    uint16_t* sorted_poa            = &sorted_poa_d[window_idx * max_nodes_per_window];
    uint16_t* node_id_to_pos        = &node_id_to_pos_d[window_idx * max_nodes_per_window];
    uint16_t* node_alignments       = &node_alignments_d[window_idx * max_nodes_per_window * CUDAPOA_MAX_NODE_ALIGNMENTS];
    uint16_t* node_alignment_count  = &node_alignment_count_d[window_idx * max_nodes_per_window];
    uint16_t* node_coverage_counts  = &node_coverage_counts_d_[max_nodes_per_window * window_idx];
    uint16_t* sequence_lengths      = &sequence_lengths_d[window_details_d[window_idx].seq_len_buffer_offset];

    //generate consensus
    uint16_t* coverage              = &coverage_d[window_idx * CUDAPOA_MAX_CONSENSUS_SIZE];
    int32_t* consensus_scores       = &consensus_scores_d[window_idx * max_nodes_per_window];
    int16_t* consensus_predecessors = &consensus_predecessors_d[window_idx * max_nodes_per_window];

    generateConsensus(nodes,
                      sequence_lengths[0],
                      sorted_poa,
                      node_id_to_pos,
                      incoming_edges,
                      incoming_edge_count,
                      outoing_edges,
                      outgoing_edge_count,
                      incoming_edge_weights,
                      consensus_predecessors,
                      consensus_scores,
                      consensus,
                      coverage,
                      node_coverage_counts,
                      node_alignments, node_alignment_count);
}

__global__ void generateConsensusTestKernel(uint8_t* nodes,
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
                                            uint16_t* node_alignment_count)
{
    generateConsensus(nodes,
                      node_count,
                      graph,
                      node_id_to_pos,
                      incoming_edges,
                      incoming_edge_count,
                      outgoing_edges,
                      outgoing_edge_count,
                      incoming_edge_w,
                      predecessors,
                      scores,
                      consensus,
                      coverage,
                      node_coverage_counts,
                      node_alignments,
                      node_alignment_count);
}

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
                               uint16_t* node_alignment_count)
{
    generateConsensusTestKernel<<<1, 1>>>(nodes,
                                          node_count,
                                          graph,
                                          node_id_to_pos,
                                          incoming_edges,
                                          incoming_edge_count,
                                          outgoing_edges,
                                          outgoing_edge_count,
                                          incoming_edge_w,
                                          predecessors,
                                          scores,
                                          consensus,
                                          coverage,
                                          node_coverage_counts,
                                          node_alignments,
                                          node_alignment_count);
    CGA_CU_CHECK_ERR(cudaPeekAtLastError());
}

} // namespace cudapoa

} // namespace claragenomics

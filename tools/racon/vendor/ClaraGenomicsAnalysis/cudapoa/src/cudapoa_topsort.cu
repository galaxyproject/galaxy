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

/**
 * @brief Device function for running topoligical sort on graph.
 *
 * @param[out] sorted_poa                Device buffer with sorted graph
 * @param[out] sorted_poa_node_map       Device scratch space for mapping node ID to position in graph
 * @param[in] node_count                 Number of nodes graph
 * @param[in] incoming_edge_count        Device buffer with number of incoming edges per node
 * @param[in] outgoing_edges             Device buffer with outgoing edges per node
 * @param[in] outgoing_edge_count        Device buffer with number of outgoing edges per node
 * @param[in] local_incoming_edge_count  Device scratch space for maintaining edge counts during topological sort
 */
__device__ void topologicalSortDeviceUtil(uint16_t* sorted_poa,
                                          uint16_t* sorted_poa_node_map,
                                          uint16_t node_count,
                                          uint16_t* incoming_edge_count,
                                          uint16_t* outgoing_edges,
                                          uint16_t* outgoing_edge_count,
                                          uint16_t* local_incoming_edge_count)
{
    //printf("Running top sort\n");
    // Clear the incoming edge count for each node.
    //__shared__ int16_t local_incoming_edge_count[CUDAPOA_MAX_NODES_PER_WINDOW];
    //memset(local_incoming_edge_count, -1, CUDAPOA_MAX_NODES_PER_WINDOW);
    uint16_t sorted_poa_position = 0;

    // Iterate through node IDs (since nodes are from 0
    // through node_count -1, a simple loop works) and fill
    // out the incoming edge count.
    for (uint16_t n = 0; n < node_count; n++)
    {
        local_incoming_edge_count[n] = incoming_edge_count[n];
        // If we find a node ID has 0 incoming edges, add it to sorted nodes list.
        if (local_incoming_edge_count[n] == 0)
        {
            sorted_poa_node_map[n]            = sorted_poa_position;
            sorted_poa[sorted_poa_position++] = n;
        }
    }

    // Loop through set of node IDs with no incoming edges,
    // then iterate through their children. For each child decrement their
    // incoming edge count. If incoming edge count of child == 0,
    // add its node ID to the sorted order list.
    for (uint16_t n = 0; n < sorted_poa_position; n++)
    {
        uint16_t node = sorted_poa[n];
        for (uint16_t edge = 0; edge < outgoing_edge_count[node]; edge++)
        {
            uint16_t out_node = outgoing_edges[node * CUDAPOA_MAX_NODE_EDGES + edge];
            //printf("%d\n", out_node);
            local_incoming_edge_count[out_node]--;
            if (local_incoming_edge_count[out_node] == 0)
            {
                sorted_poa_node_map[out_node]     = sorted_poa_position;
                sorted_poa[sorted_poa_position++] = out_node;
            }
        }
    }

    // sorted_poa will have final ordering of node IDs.
}

// Implementation of topological sort that matches the original
// racon source topological sort. This is helpful in ensuring the
// correctness of the GPU implementation. With this change,
// the GPU code exactly matches the SISD implementation of spoa.
__device__ void raconTopologicalSortDeviceUtil(uint16_t* sorted_poa,
                                               uint16_t* sorted_poa_node_map,
                                               uint16_t node_count,
                                               uint16_t* incoming_edge_count,
                                               uint16_t* incoming_edges,
                                               uint16_t* aligned_node_count,
                                               uint16_t* aligned_nodes,
                                               uint8_t* node_marks,
                                               bool* check_aligned_nodes,
                                               uint16_t* nodes_to_visit,
                                               bool banded_alignment)
{
    int16_t node_idx        = -1;
    uint16_t sorted_poa_idx = 0;

    uint16_t max_nodes_per_window = banded_alignment ? CUDAPOA_MAX_NODES_PER_WINDOW_BANDED : CUDAPOA_MAX_NODES_PER_WINDOW;
    for (uint16_t i = 0; i < max_nodes_per_window; i++)
    {
        node_marks[i]          = 0;
        check_aligned_nodes[i] = true;
    }

    for (uint16_t i = 0; i < node_count; i++)
    {
        if (node_marks[i] != 0)
        {
            continue;
        }

        node_idx++;
        nodes_to_visit[node_idx] = i;

        while (node_idx != -1)
        {
            uint16_t node_id = nodes_to_visit[node_idx];
            bool valid       = true;

            if (node_marks[node_id] != 2)
            {
                for (uint16_t e = 0; e < incoming_edge_count[node_id]; e++)
                {
                    uint16_t begin_node_id = incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES + e];
                    if (node_marks[begin_node_id] != 2)
                    {
                        node_idx++;
                        nodes_to_visit[node_idx] = begin_node_id;
                        valid                    = false;
                    }
                }

                if (check_aligned_nodes[node_id])
                {
                    for (uint16_t a = 0; a < aligned_node_count[node_id]; a++)
                    {
                        uint16_t aid = aligned_nodes[node_id * CUDAPOA_MAX_NODE_ALIGNMENTS + a];
                        if (node_marks[aid] != 2)
                        {
                            node_idx++;
                            nodes_to_visit[node_idx] = aid;
                            check_aligned_nodes[aid] = false;
                            valid                    = false;
                        }
                    }
                }

                if (valid)
                {
                    node_marks[node_id] = 2;
                    if (check_aligned_nodes[node_id])
                    {
                        sorted_poa[sorted_poa_idx]   = node_id;
                        sorted_poa_node_map[node_id] = sorted_poa_idx;
                        sorted_poa_idx++;
                        for (uint16_t a = 0; a < aligned_node_count[node_id]; a++)
                        {
                            uint16_t aid               = aligned_nodes[node_id * CUDAPOA_MAX_NODE_ALIGNMENTS + a];
                            sorted_poa[sorted_poa_idx] = aid;
                            sorted_poa_node_map[aid]   = sorted_poa_idx;
                            sorted_poa_idx++;
                        }
                    }
                }
                else
                {
                    node_marks[node_id] = 1;
                }
            }

            if (valid)
            {
                node_idx--;
            }
        }
    }
}

__global__ void runTopSortKernel(uint16_t* sorted_poa,
                                 uint16_t* sorted_poa_node_map,
                                 uint16_t node_count,
                                 uint16_t* incoming_edge_count,
                                 uint16_t* outgoing_edges,
                                 uint16_t* outgoing_edge_count,
                                 uint16_t* local_incoming_edge_count)
{
    //calls the topsort device function
    topologicalSortDeviceUtil(sorted_poa,
                              sorted_poa_node_map,
                              node_count,
                              incoming_edge_count,
                              outgoing_edges,
                              outgoing_edge_count,
                              local_incoming_edge_count);
}

void runTopSort(uint16_t* sorted_poa,
                uint16_t* sorted_poa_node_map,
                uint16_t node_count,
                uint16_t* incoming_edge_count,
                uint16_t* outgoing_edges,
                uint16_t* outgoing_edge_count,
                uint16_t* local_incoming_edge_count)
{
    // calls the topsort kernel on 1 thread
    runTopSortKernel<<<1, 1>>>(sorted_poa,
                               sorted_poa_node_map,
                               node_count,
                               incoming_edge_count,
                               outgoing_edges,
                               outgoing_edge_count,
                               local_incoming_edge_count);
    CGA_CU_CHECK_ERR(cudaPeekAtLastError());
}

} // namespace cudapoa

} // namespace claragenomics

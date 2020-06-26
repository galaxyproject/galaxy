/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "../src/cudapoa_kernels.cuh" //CUDAPOA_MAX_NODE_EDGES, CUDAPOA_MAX_NODE_ALIGNMENTS

#include <claragenomics/utils/signed_integer_utils.hpp> //get_size

#include <string>
#include <vector>
#include <stdint.h>

namespace claragenomics
{

namespace cudapoa
{

// alias for the 2d vector graph representation
typedef std::vector<std::vector<uint16_t>> Uint16Vec2D;
typedef std::vector<std::vector<std::vector<uint16_t>>> Uint16Vec3D;

class BasicGraph
{
public:
    BasicGraph(std::vector<uint8_t> nodes, Uint16Vec2D outgoing_edges, Uint16Vec2D node_alignments, std::vector<uint16_t> node_coverage_counts, Uint16Vec3D outgoing_edges_coverage = {})
        : nodes_(nodes)
        , outgoing_edges_(outgoing_edges)
        , node_alignments_(node_alignments)
        , node_coverage_counts_(node_coverage_counts)
        , outgoing_edges_coverage_(outgoing_edges_coverage)
    {
        graph_complete_ = true;
        node_count_     = get_size(nodes_);
    }

    BasicGraph(uint16_t* outgoing_edges, uint16_t* outgoing_edge_count, uint16_t node_count)
    {
        graph_complete_ = false;
        outgoing_edges_ = edges_to_graph(outgoing_edges, outgoing_edge_count, node_count);
    }

    BasicGraph(Uint16Vec2D outgoing_edges)
    {
        graph_complete_ = false;
        outgoing_edges_ = outgoing_edges;
        node_count_     = get_size(outgoing_edges);
    }

    BasicGraph(std::vector<uint8_t> nodes, Uint16Vec2D outgoing_edges)
        : BasicGraph(outgoing_edges)
    {
        nodes_ = nodes;
    }

    BasicGraph() = delete;

    //fill in the edge-related pointers based on stored graph
    void get_edges(uint16_t* incoming_edges, uint16_t* incoming_edge_count,
                   uint16_t* outgoing_edges, uint16_t* outgoing_edge_count) const
    {
        uint16_t out_node;
        for (int i = 0; i < node_count_; i++)
        {
            outgoing_edge_count[i] = get_size(outgoing_edges_[i]);
            for (int j = 0; j < get_size(outgoing_edges_[i]); j++)
            {
                out_node                                                          = outgoing_edges_[i][j];
                uint16_t in_edge_count                                            = incoming_edge_count[out_node];
                incoming_edge_count[out_node]                                     = in_edge_count + 1;
                incoming_edges[out_node * CUDAPOA_MAX_NODE_EDGES + in_edge_count] = i;
                outgoing_edges[i * CUDAPOA_MAX_NODE_EDGES + j]                    = out_node;
            }
        }
    }
    //fill in the nodes and node_count pointer
    void get_nodes(uint8_t* nodes, uint16_t* node_count) const
    {
        for (int i = 0; i < get_size(nodes_); i++)
        {
            nodes[i] = nodes_[i];
        }
        *node_count = node_count_;
    }
    //fill in the node_alignments and node_alignment_count pointers
    void get_node_alignments(uint16_t* node_alignments, uint16_t* node_alignment_count) const
    {
        uint16_t aligned_node;
        for (int i = 0; i < get_size(node_alignments_); i++)
        {
            for (int j = 0; j < get_size(node_alignments_[i]); j++)
            {
                aligned_node                                         = node_alignments_[i][j];
                node_alignments[i * CUDAPOA_MAX_NODE_ALIGNMENTS + j] = aligned_node;
                node_alignment_count[i]++;
            }
        }
    }
    //fill in node_coverage_counts pointer
    void get_node_coverage_counts(uint16_t* node_coverage_counts) const
    {
        for (int i = 0; i < get_size(node_coverage_counts_); i++)
        {
            node_coverage_counts[i] = node_coverage_counts_[i];
        }
    }

    // convert results from outgoing_edges to Uint16Vec2D graph
    Uint16Vec2D edges_to_graph(uint16_t* outgoing_edges, uint16_t* outgoing_edge_count, uint16_t node_count)
    {
        Uint16Vec2D graph(node_count);
        for (uint16_t i = 0; i < node_count; i++)
        {
            for (uint16_t j = 0; j < outgoing_edge_count[i]; j++)
            {
                graph[i].push_back(outgoing_edges[i * CUDAPOA_MAX_NODE_EDGES + j]);
            }
        }
        return graph;
    }

    void get_outgoing_edges_coverage(uint16_t* outgoing_edges_coverage, uint16_t* outgoing_edges_coverage_count, uint16_t num_sequences) const
    {
        if (outgoing_edges_coverage_.size() == 0)
            return;
        uint16_t out_node;
        for (int i = 0; i < outgoing_edges_coverage_.size(); i++) //from_node
        {
            for (int j = 0; j < (int)outgoing_edges_coverage_[i].size(); j++) //to_node
            {
                uint16_t edge_coverage_count                                  = outgoing_edges_coverage_[i][j].size();
                outgoing_edges_coverage_count[i * CUDAPOA_MAX_NODE_EDGES + j] = edge_coverage_count;
                for (int k = 0; k < edge_coverage_count; k++)
                {
                    outgoing_edges_coverage[i * CUDAPOA_MAX_NODE_EDGES * num_sequences + j * num_sequences + k] = outgoing_edges_coverage_[i][j][k];
                }
            }
        }
    }

    bool is_complete() const
    {
        return graph_complete_;
    }

    bool operator==(const BasicGraph& rhs) const
    {
        return this->outgoing_edges_ == rhs.outgoing_edges_;
    }

    const Uint16Vec2D& get_outgoing_edges() const { return outgoing_edges_; }

protected:
    bool graph_complete_;
    std::vector<uint8_t> nodes_;
    Uint16Vec2D outgoing_edges_; //this uniquely represents the graph structure; equality of BasicGraph is based on this member.
    Uint16Vec3D outgoing_edges_coverage_;
    Uint16Vec2D node_alignments_;
    std::vector<uint16_t> node_coverage_counts_;
    uint16_t node_count_;
};

} // namespace cudapoa

} // namespace claragenomics

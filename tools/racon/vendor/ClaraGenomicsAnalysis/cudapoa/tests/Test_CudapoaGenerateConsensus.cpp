/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "../src/cudapoa_kernels.cuh" //generateConsensusHost, CUDAPOA_MAX_NODE_EDGES, CUDAPOA_MAX_NODE_ALIGNMENTS
#include "sorted_graph.hpp"           //SortedGraph

#include <claragenomics/utils/cudautils.hpp>            //CGA_CU_CHECK_ERR
#include <claragenomics/utils/signed_integer_utils.hpp> //get_size

#include "gtest/gtest.h"

namespace claragenomics
{

namespace cudapoa
{

class BasicGenerateConsensus
{

public:
    BasicGenerateConsensus(std::vector<uint8_t> nodes, std::vector<uint16_t> sorted_graph, Uint16Vec2D node_alignments,
                           Uint16Vec2D outgoing_edges, std::vector<uint16_t> node_coverage_counts, Uint16Vec2D outgoing_edge_w)
        : graph_(nodes, sorted_graph, node_alignments, node_coverage_counts, outgoing_edges)
        , outgoing_edge_w_(outgoing_edge_w)
        , outgoing_edges_(outgoing_edges)
    {
    }

    void get_graph_buffers(uint8_t* nodes, uint16_t* node_count,
                           uint16_t* sorted_poa, uint16_t* node_id_to_pos,
                           uint16_t* incoming_edges, uint16_t* incoming_edge_count,
                           uint16_t* outgoing_edges, uint16_t* outgoing_edge_count,
                           uint16_t* incoming_edge_w, uint16_t* node_coverage_counts,
                           uint16_t* node_alignments, uint16_t* node_alignment_count) const
    {
        graph_.get_nodes(nodes, node_count);
        graph_.get_sorted_graph(sorted_poa);
        graph_.get_node_id_to_pos(node_id_to_pos);
        graph_.get_node_coverage_counts(node_coverage_counts);
        graph_.get_edges(incoming_edges, incoming_edge_count, outgoing_edges, outgoing_edge_count);
        graph_.get_node_alignments(node_alignments, node_alignment_count);
        get_incoming_edge_w(incoming_edge_w);
    }

    void get_incoming_edge_w(uint16_t* incoming_edge_w) const
    {
        auto outgoing_edges = graph_.get_outgoing_edges();
        for (int i = 0; i < get_size(outgoing_edges); i++)
        {
            for (int j = 0; j < get_size(outgoing_edges[i]); j++)
            {
                uint16_t to_node                                      = outgoing_edges[i][j];
                incoming_edge_w[to_node * CUDAPOA_MAX_NODE_EDGES + i] = outgoing_edge_w_[i][j];
            }
        }
    }

protected:
    SortedGraph graph_;
    Uint16Vec2D outgoing_edges_;
    Uint16Vec2D outgoing_edge_w_;
};

typedef std::pair<std::string, BasicGenerateConsensus> GenerateConsensusTestPair;
// create a vector of test cases
std::vector<GenerateConsensusTestPair> getGenerateConsensusTestCases()
{

    std::vector<GenerateConsensusTestPair> test_cases;

    /*
     *                  T
     *                 / \
     * graph      A — A   A
     *                 \ /
     *                  A
     */
    std::string ans_1 = "ATAA";
    BasicGenerateConsensus gc_1({'A', 'A', 'A', 'A', 'T'},    //nodes
                                {0, 1, 2, 4, 3},              //sorted_graph
                                {{}, {}, {4}, {}, {2}},       //node_alignments
                                {{1}, {2, 4}, {3}, {}, {3}},  //outgoing_edges
                                {2, 2, 1, 2, 1},              //node_coverage_counts
                                {{5}, {4, 3}, {2}, {}, {1}}); //outgoing_edge_w
    test_cases.emplace_back(std::move(ans_1), std::move(gc_1));

    /*
     * graph   A — T — C — G — A
     */
    std::string ans_2 = "AGCTA";
    BasicGenerateConsensus gc_2({'A', 'T', 'C', 'G', 'A'}, //nodes
                                {0, 1, 2, 3, 4},           //sorted_graph
                                {{}, {}, {}, {}, {}},      //node_alignments
                                {{1}, {2}, {3}, {4}, {}},  //outgoing_edges
                                {1, 1, 1, 1, 1},           //node_coverage_counts
                                {{4}, {3}, {2}, {1}, {}});
    test_cases.emplace_back(std::move(ans_2), std::move(gc_2));

    /*
     *                T
     *              /   \
     * graph      A — C — C — G
     *              \   /
     *                A
     */
    std::string ans_3 = "GCCA";
    BasicGenerateConsensus gc_3({'A', 'A', 'C', 'G', 'C', 'T'},       //nodes
                                {0, 1, 4, 5, 2, 3},                   //sorted_graph
                                {{}, {4, 5}, {}, {}, {1, 5}, {1, 4}}, //node_alignments
                                {{1, 4, 5}, {2}, {3}, {}, {2}, {2}},  //outgoing_edges
                                {3, 1, 3, 3, 1, 1},                   //node_coverage_counts
                                {{7, 6, 5}, {4}, {3}, {}, {2}, {1}});
    test_cases.emplace_back(std::move(ans_3), std::move(gc_3));

    /*
     * graph      A — T — T — G — A
     *             \_____________/
     */
    std::string ans_4 = "AGTTA";
    BasicGenerateConsensus gc_4({'A', 'T', 'T', 'G', 'A'},   //nodes
                                {0, 1, 2, 3, 4},             //sorted_graph
                                {{}, {}, {}, {}, {}},        //node_alignments
                                {{1, 4}, {2}, {3}, {4}, {}}, //outgoing_edges
                                {2, 1, 1, 1, 2},             //node_coverage_counts
                                {{5, 4}, {3}, {2}, {1}, {}});
    test_cases.emplace_back(std::move(ans_4), std::move(gc_4));

    /*
     *                T — G   
     *              /       \
     * graph      A — C — A — T — A
     *                  \   /
     *                    T
     */
    std::string ans_5 = "ATTCA";
    BasicGenerateConsensus gc_5({'A', 'T', 'G', 'T', 'A', 'C', 'A', 'T'},       //nodes
                                {0, 1, 5, 2, 6, 7, 3, 4},                       //sorted_graph
                                {{}, {5}, {6, 7}, {}, {}, {1}, {2, 7}, {2, 6}}, //node_alignments
                                {{1, 5}, {2}, {3}, {4}, {}, {6, 7}, {3}, {3}},  //outgoing_edges
                                {3, 1, 1, 3, 3, 2, 1, 1},                       //node_coverage_counts
                                {{9, 8}, {7}, {6}, {5}, {}, {4, 3}, {2}, {1}});

    test_cases.emplace_back(std::move(ans_5), std::move(gc_5));

    //add more test cases below

    return test_cases;
}

// host function for calling the kernel to test topsort device function.
std::string testGenerateConsensus(const BasicGenerateConsensus& obj)
{
    //declare device buffer
    uint8_t* nodes;
    uint16_t* node_count;
    uint16_t* graph;
    uint16_t* node_id_to_pos;
    uint16_t* incoming_edges;
    uint16_t* incoming_edge_count;
    uint16_t* outgoing_edges;
    uint16_t* outgoing_edge_count;
    uint16_t* incoming_edge_w;
    uint16_t* node_coverage_counts;
    uint16_t* node_alignments;
    uint16_t* node_alignment_count;

    //buffers that don't need initialization
    int16_t* predecessors;
    int32_t* scores;
    uint8_t* consensus;
    uint16_t* coverage;

    //allocate unified memory so they can be accessed by both host and device.
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&nodes, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint8_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&node_count, sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&graph, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&node_id_to_pos, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&incoming_edges, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&incoming_edge_count, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edges, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edge_count, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&incoming_edge_w, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&node_coverage_counts, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&node_alignments, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_ALIGNMENTS * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&node_alignment_count, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));

    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&predecessors, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(int16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&scores, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(int32_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&consensus, CUDAPOA_MAX_CONSENSUS_SIZE * sizeof(uint8_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&coverage, CUDAPOA_MAX_CONSENSUS_SIZE * sizeof(uint16_t)));

    //initialize all 'count' buffers
    memset((void**)incoming_edge_count, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));
    memset((void**)outgoing_edge_count, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));
    memset((void**)node_coverage_counts, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));
    memset((void**)node_alignment_count, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));

    //calculate edge counts on host
    obj.get_graph_buffers(nodes, node_count,
                          graph, node_id_to_pos,
                          incoming_edges, incoming_edge_count,
                          outgoing_edges, outgoing_edge_count,
                          incoming_edge_w, node_coverage_counts,
                          node_alignments, node_alignment_count);

    // call the host wrapper of topsort kernel
    generateConsensusTestHost(nodes,
                              *node_count,
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

    CGA_CU_CHECK_ERR(cudaDeviceSynchronize());

    //input and output buffers are the same ones in unified memory, so the results are updated in place
    //create and return a new BasicGraph object that encodes the resulting graph structure after adding the alignment
    std::string res((char*)consensus);

    CGA_CU_CHECK_ERR(cudaFree(nodes));
    CGA_CU_CHECK_ERR(cudaFree(node_count));
    CGA_CU_CHECK_ERR(cudaFree(graph));
    CGA_CU_CHECK_ERR(cudaFree(node_id_to_pos));
    CGA_CU_CHECK_ERR(cudaFree(incoming_edges));
    CGA_CU_CHECK_ERR(cudaFree(incoming_edge_count));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edges));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edge_count));
    CGA_CU_CHECK_ERR(cudaFree(incoming_edge_w));
    CGA_CU_CHECK_ERR(cudaFree(node_coverage_counts));
    CGA_CU_CHECK_ERR(cudaFree(node_alignments));
    CGA_CU_CHECK_ERR(cudaFree(node_alignment_count));
    CGA_CU_CHECK_ERR(cudaFree(predecessors));
    CGA_CU_CHECK_ERR(cudaFree(scores));
    CGA_CU_CHECK_ERR(cudaFree(consensus));
    CGA_CU_CHECK_ERR(cudaFree(coverage));

    return res;
}

using ::testing::TestWithParam;
using ::testing::ValuesIn;

class GenerateConsensusTest : public TestWithParam<GenerateConsensusTestPair>
{
public:
    void SetUp() {}

    std::string runGenerateConsensus(const BasicGenerateConsensus& obj)
    {
        return testGenerateConsensus(obj);
    }
};

TEST_P(GenerateConsensusTest, TestGenerateConsensuesCorrectness)
{
    const auto test_case = GetParam();
    EXPECT_EQ(test_case.first, runGenerateConsensus(test_case.second));
}

INSTANTIATE_TEST_SUITE_P(TestGenerateConsensus, GenerateConsensusTest, ValuesIn(getGenerateConsensusTestCases()));

} // namespace cudapoa

} // namespace claragenomics

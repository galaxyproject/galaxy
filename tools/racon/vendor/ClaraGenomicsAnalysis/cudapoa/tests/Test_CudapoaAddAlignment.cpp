/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "../src/cudapoa_kernels.cuh" //addAlignment, CUDAPOA_MAX_NODE_EDGES, CUDAPOA_MAX_NODE_ALIGNMENTS
#include "basic_graph.hpp"            //BasicGraph

#include <claragenomics/utils/cudautils.hpp>            //CGA_CU_CHECK_ERR
#include <claragenomics/utils/stringutils.hpp>          //array_to_string
#include <claragenomics/utils/signed_integer_utils.hpp> // get_size

#include "gtest/gtest.h"

namespace claragenomics
{

namespace cudapoa
{

class BasicAlignment
{
public:
    BasicAlignment(std::vector<uint8_t> nodes, Uint16Vec2D outgoing_edges,
                   Uint16Vec2D node_alignments, std::vector<uint16_t> node_coverage_counts,
                   std::vector<uint8_t> read, std::vector<int8_t> base_weights, std::vector<int16_t> alignment_graph, std::vector<int16_t> alignment_read)
        : graph(nodes, outgoing_edges, node_alignments, node_coverage_counts)
        , read_(read)
        , alignment_graph_(alignment_graph)
        , alignment_read_(alignment_read)
    {
        //do nothing for now
    }

    void get_alignments(int16_t* alignment_graph, int16_t* alignment_read, uint16_t* alignment_length) const
    {
        for (int i = 0; i < get_size(alignment_graph_); i++)
        {
            alignment_graph[i] = alignment_graph_[i];
            alignment_read[i]  = alignment_read_[i];
        }
        *alignment_length = get_size(alignment_graph_);
    }

    void get_read(uint8_t* read) const
    {
        for (int i = 0; i < get_size(read_); i++)
        {
            read[i] = read_[i];
        }
    }

    void get_base_weights(int8_t* base_weights) const
    {
        for (int i = 0; i < get_size(base_weights_); i++)
        {
            base_weights[i] = base_weights_[i];
        }
    }

    void get_graph_buffers(uint16_t* incoming_edges, uint16_t* incoming_edge_count,
                           uint16_t* outgoing_edges, uint16_t* outgoing_edge_count,
                           uint8_t* nodes, uint16_t* node_count,
                           uint16_t* node_alignments, uint16_t* node_alignment_count,
                           uint16_t* node_coverage_counts) const
    {
        if (!graph.is_complete())
        {
            throw "graph is incomplete; unable to fill the buffers.";
        }
        graph.get_edges(incoming_edges, incoming_edge_count, outgoing_edges, outgoing_edge_count);
        graph.get_nodes(nodes, node_count);
        graph.get_node_alignments(node_alignments, node_alignment_count);
        graph.get_node_coverage_counts(node_coverage_counts);
    }

    void get_alignment_buffers(int16_t* alignment_graph, int16_t* alignment_read, uint16_t* alignment_length,
                               uint8_t* read, int8_t* base_weights) const
    {
        get_alignments(alignment_graph, alignment_read, alignment_length);
        get_read(read);
        get_base_weights(base_weights);
    }

protected:
    BasicGraph graph;
    std::vector<uint8_t> read_;
    std::vector<int8_t> base_weights_;
    std::vector<int16_t> alignment_graph_;
    std::vector<int16_t> alignment_read_;
};

typedef std::pair<BasicGraph, BasicAlignment> AddAlginmentTestPair;
// create a vector of test cases
std::vector<AddAlginmentTestPair> getAddAlignmentTestCases()
{

    std::vector<AddAlginmentTestPair> test_cases;

    /*
     * read:            A   A   T   A
     * graph:           A — A — A — A
     * alignment graph: 0   1   2   3
     * alignment read:  0   1   2   3
     *                        T
     *                       / \
     * final graph      A — A   A
     *                       \ /
     *                        A
     */
    BasicGraph ans_1(Uint16Vec2D({{}, {0}, {1}, {2, 4}, {1}}));
    BasicAlignment ali_1({'A', 'A', 'A', 'A'}, //nodes
                         {{}, {0}, {1}, {2}},  //outgoing_edges
                         {{}, {}, {}, {}},     //node_alignments
                         {1, 1, 1, 1},         //node_coverage_counts
                         {'A', 'A', 'T', 'A'}, //read
                         {0, 0, 1, 2},         //base weights
                         {0, 1, 2, 3},         //alignment_graph
                         {0, 1, 2, 3});        //alignment_read
    test_cases.emplace_back(std::move(ans_1), std::move(ali_1));

    /*
     * read:            A   T   C   G   A
     * graph:           A — T — C — G
     * alignment graph: 0   1   2   3  -1
     * alignment read:  0   1   2   3   4
     *                        
     * final graph      A — T — C — G — A
     * 
     */
    BasicGraph ans_2(Uint16Vec2D({{}, {0}, {1}, {2}, {3}}));
    BasicAlignment ali_2({'A', 'T', 'C', 'G'},      //nodes
                         {{}, {0}, {1}, {2}},       //outgoing_edges
                         {{}, {}, {}, {}},          //node_alignments
                         {1, 1, 1, 1},              //node_coverage_counts
                         {'A', 'T', 'C', 'G', 'A'}, //read
                         {0, 1, 2, 3, 4},           //base weights
                         {0, 1, 2, 3, -1},          //alignment_graph
                         {0, 1, 2, 3, 4});          //alignment_read
    test_cases.emplace_back(std::move(ans_2), std::move(ali_2));

    /*
     * read:            A   T   C   G
     *                      A
     *                    /   \
     * graph:           A — C — C — G
     * alignment graph: 0   4   2   3
     * alignment read:  0   1   2   3
     *                      T
     *                    /   \
     * final graph      A — C — C — G
     *                    \   /
     *                      A
     */
    BasicGraph ans_3(Uint16Vec2D({{}, {0}, {1, 4, 5}, {2}, {0}, {0}}));
    BasicAlignment ali_3({'A', 'A', 'C', 'G', 'C'},   //nodes
                         {{}, {0}, {1, 4}, {2}, {0}}, //outgoing_edges
                         {{}, {}, {}, {}},            //node_alignments
                         {2, 1, 2, 2, 1},             //node_coverage_counts
                         {'A', 'T', 'C', 'G'},        //read
                         {0, 1, 1, 5},                //base weights
                         {0, 4, 2, 3},                //alignment_graph
                         {0, 1, 2, 3});               //alignment_read
    test_cases.emplace_back(std::move(ans_3), std::move(ali_3));

    /*
     * read:            A   A  
     * graph:           A — T — T — G — A
     * alignment graph: 0   1   2   3   4
     * alignment read:  0  -1  -1  -1   1
     *                        
     * final graph      A — T — T — G — A
     *                   \_____________/
     * 
     */
    BasicGraph ans_4(Uint16Vec2D({{}, {0}, {1}, {2}, {3, 0}}));
    BasicAlignment ali_4({'A', 'T', 'T', 'G', 'A'}, //nodes
                         {{}, {0}, {1}, {2}, {3}},  //outgoing_edges
                         {{}, {}, {}, {}},          //node_alignments
                         {1, 1, 1, 1, 1},           //node_coverage_counts
                         {'A', 'A'},                //read
                         {5, 1},                    //base weights
                         {0, 1, 2, 3, 4},           //alignment_graph
                         {0, -1, -1, -1, 1});       //alignment_read
    test_cases.emplace_back(std::move(ans_4), std::move(ali_4));

    /*
     * read:            A   C   T   T   A
     *                      T — G
     *                    /       \ 
     * graph:           A — C — A — T — A
     * alignment graph: 0   5   6   3   4
     * alignment read:  0   1   2   3   4
     *                      T — G   
     *                    /       \
     * final graph      A — C — A — T — A
     *                        \   /
     *                          T
     * 
     */
    BasicGraph ans_5(Uint16Vec2D({{}, {0}, {1}, {2, 6, 7}, {3}, {0}, {5}, {5}}));
    BasicAlignment ali_5({'A', 'T', 'G', 'T', 'A', 'C', 'A'},   //nodes
                         {{}, {0}, {1}, {2, 6}, {3}, {0}, {5}}, //outgoing_edges
                         {{}, {}, {}, {}},                      //node_alignments
                         {2, 1, 1, 2, 2, 1, 1},                 //node_coverage_counts
                         {'A', 'C', 'T', 'T', 'A'},             //read
                         {10, 9, 8, 7, 6},                      //base weights
                         {0, 5, 6, 3, 4},                       //alignment_graph
                         {0, 1, 2, 3, 4});                      //alignment_read
    test_cases.emplace_back(std::move(ans_5), std::move(ali_5));

    //add more test cases below

    return test_cases;
}

// host function for calling the kernel to test topsort device function.
BasicGraph testAddAlignment(const BasicAlignment& obj)
{
    //declare device buffer
    uint8_t* nodes;
    uint16_t* node_count;
    uint16_t* node_alignments;
    uint16_t* node_alignment_count;
    uint16_t* incoming_edges;
    uint16_t* incoming_edge_count;
    uint16_t* outgoing_edges;
    uint16_t* outgoing_edge_count;
    uint16_t* incoming_edge_w;
    uint16_t* outgoing_edge_w;
    uint16_t* alignment_length;
    uint16_t* graph;
    int16_t* alignment_graph;
    uint8_t* read;
    int8_t* base_weights;
    int16_t* alignment_read;
    uint16_t* node_coverage_counts;
    uint16_t* sequence_begin_nodes_ids;
    uint16_t* outgoing_edges_coverage;
    uint16_t* outgoing_edges_coverage_count;
    uint16_t s                     = 0;
    uint32_t max_sequences_per_poa = 100;

    //allocate unified memory so they can be accessed by both host and device.
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&nodes, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint8_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&node_count, sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&node_alignments, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_ALIGNMENTS * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&node_alignment_count, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&incoming_edges, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&incoming_edge_count, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edges, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edge_count, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&incoming_edge_w, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edge_w, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&alignment_length, sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&graph, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&alignment_graph, CUDAPOA_MAX_SEQUENCE_SIZE * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&read, CUDAPOA_MAX_SEQUENCE_SIZE * sizeof(uint8_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&base_weights, CUDAPOA_MAX_SEQUENCE_SIZE * sizeof(int8_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&alignment_read, CUDAPOA_MAX_SEQUENCE_SIZE * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&node_coverage_counts, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&sequence_begin_nodes_ids, max_sequences_per_poa * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edges_coverage, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * max_sequences_per_poa * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edges_coverage_count, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * sizeof(uint16_t)));

    //initialize all 'count' buffers
    memset((void**)node_alignment_count, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));
    memset((void**)incoming_edge_count, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));
    memset((void**)outgoing_edge_count, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));
    memset((void**)node_coverage_counts, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));

    //calculate edge counts on host
    //3 buffers are disregarded because they don't affect correctness -- incoming_edge_w, outgoing_edge_w, graph
    obj.get_graph_buffers(incoming_edges, incoming_edge_count, outgoing_edges, outgoing_edge_count,
                          nodes, node_count,
                          node_alignments, node_alignment_count,
                          node_coverage_counts);
    obj.get_alignment_buffers(alignment_graph, alignment_read, alignment_length, read, base_weights);

    // call the host wrapper of topsort kernel
    addAlignment(nodes,
                 node_count,
                 node_alignments, node_alignment_count,
                 incoming_edges, incoming_edge_count,
                 outgoing_edges, outgoing_edge_count,
                 incoming_edge_w, outgoing_edge_w,
                 alignment_length,
                 graph,
                 alignment_graph,
                 read,
                 alignment_read,
                 node_coverage_counts,
                 base_weights,
                 sequence_begin_nodes_ids,
                 outgoing_edges_coverage,
                 outgoing_edges_coverage_count,
                 s,
                 max_sequences_per_poa);

    CGA_CU_CHECK_ERR(cudaDeviceSynchronize());

    //input and output buffers are the same ones in unified memory, so the results are updated in place
    //create and return a new BasicGraph object that encodes the resulting graph structure after adding the alignment
    BasicGraph res(outgoing_edges, outgoing_edge_count, *node_count);

    CGA_CU_CHECK_ERR(cudaFree(nodes));
    CGA_CU_CHECK_ERR(cudaFree(node_count));
    CGA_CU_CHECK_ERR(cudaFree(node_alignments));
    CGA_CU_CHECK_ERR(cudaFree(node_alignment_count));
    CGA_CU_CHECK_ERR(cudaFree(incoming_edges));
    CGA_CU_CHECK_ERR(cudaFree(incoming_edge_count));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edges));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edge_count));
    CGA_CU_CHECK_ERR(cudaFree(incoming_edge_w));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edge_w));
    CGA_CU_CHECK_ERR(cudaFree(alignment_length));
    CGA_CU_CHECK_ERR(cudaFree(graph));
    CGA_CU_CHECK_ERR(cudaFree(alignment_graph));
    CGA_CU_CHECK_ERR(cudaFree(read));
    CGA_CU_CHECK_ERR(cudaFree(base_weights));
    CGA_CU_CHECK_ERR(cudaFree(alignment_read));
    CGA_CU_CHECK_ERR(cudaFree(node_coverage_counts));
    CGA_CU_CHECK_ERR(cudaFree(sequence_begin_nodes_ids));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edges_coverage));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edges_coverage_count));

    return res;
}

using ::testing::TestWithParam;
using ::testing::ValuesIn;

class AddAlignmentTest : public TestWithParam<AddAlginmentTestPair>
{
public:
    void SetUp() {}

    BasicGraph runAddAlignment(const BasicAlignment& ali)
    {
        return testAddAlignment(ali);
    }
};

TEST_P(AddAlignmentTest, TestAddAlignmentCorrectness)
{
    const auto test_case = GetParam();
    EXPECT_EQ(test_case.first, runAddAlignment(test_case.second));
}

INSTANTIATE_TEST_SUITE_P(TestAddAlginment, AddAlignmentTest, ValuesIn(getAddAlignmentTestCases()));

} // namespace cudapoa

} // namespace claragenomics

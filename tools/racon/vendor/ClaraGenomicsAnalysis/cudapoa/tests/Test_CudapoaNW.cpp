/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "../src/cudapoa_kernels.cuh" //runNW, CUDAPOA_*
#include "sorted_graph.hpp"           //SortedGraph

#include <claragenomics/utils/cudautils.hpp>            //CGA_CU_CHECK_ERR
#include <claragenomics/utils/stringutils.hpp>          //array_to_string
#include <claragenomics/utils/signed_integer_utils.hpp> //get_size

#include "gtest/gtest.h"

namespace claragenomics
{

namespace cudapoa
{

class BasicNW
{

public:
    const static int16_t gap_score_      = -8;
    const static int16_t mismatch_score_ = -6;
    const static int16_t match_score_    = 8;

public:
    BasicNW(std::vector<uint8_t> nodes, std::vector<uint16_t> sorted_graph, Uint16Vec2D outgoing_edges,
            std::vector<uint8_t> read)
        : graph_(nodes, sorted_graph, outgoing_edges)
        , read_(read)
    {
        // do nothing
    }

    BasicNW() = delete;

    void get_graph_buffers(uint16_t* incoming_edges, uint16_t* incoming_edge_count,
                           uint16_t* outgoing_edges, uint16_t* outgoing_edge_count,
                           uint8_t* nodes, uint16_t* node_count,
                           uint16_t* graph, uint16_t* node_id_to_pos) const
    {
        graph_.get_edges(incoming_edges, incoming_edge_count, outgoing_edges, outgoing_edge_count);
        graph_.get_nodes(nodes, node_count);
        graph_.get_sorted_graph(graph);
        graph_.get_node_id_to_pos(node_id_to_pos);
    }

    void get_read_buffers(uint8_t* read, uint16_t* read_count) const
    {
        for (int i = 0; i < get_size(read_); i++)
        {
            read[i] = read_[i];
        }
        *read_count = get_size(read_);
    }

protected:
    SortedGraph graph_;
    std::vector<uint8_t> read_;
};

typedef std::pair<std::string, std::string> NWAnswer;
typedef std::pair<NWAnswer, BasicNW> NWTestPair;
// create a vector of test cases
std::vector<NWTestPair> getNWTestCases()
{

    std::vector<NWTestPair> test_cases;

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

    NWAnswer ans_1("3,2,1,0", "3,2,1,0"); //alginment_graph & alignment_read are reversed
    BasicNW nw_1({'A', 'A', 'A', 'A'},    //nodes
                 {0, 1, 2, 3},            //sorted_graph
                 {{1}, {2}, {3}, {}},     //outgoing_edges
                 {'A', 'A', 'T', 'A'});   //read
    test_cases.emplace_back(std::move(ans_1), std::move(nw_1));

    /*
     * read:            A   T   C   G   A
     * graph:           A — T — C — G
     * alignment graph: 0   1   2   3  -1
     * alignment read:  0   1   2   3   4
     *                        
     * final graph      A — T — C — G — A
     * 
     */
    NWAnswer ans_2("-1,3,2,1,0", "4,3,2,1,0"); //alginment_graph & alignment_read are reversed
    BasicNW nw_2({'A', 'T', 'C', 'G'},         //nodes
                 {0, 1, 2, 3},                 //sorted_graph
                 {{1}, {2}, {3}, {}},          //outgoing_edges
                 {'A', 'T', 'C', 'G', 'A'});   //read

    test_cases.emplace_back(std::move(ans_2), std::move(nw_2));

    /*
     * read:            A   T   C   G
     *                      A
     *                    /   \
     * graph:           A — C — C — G
     * alignment graph: 0   1   2   3
     * alignment read:  0   1   2   3
     *                      T
     *                    /   \
     * final graph      A — C — C — G
     *                    \   /
     *                      A
     */
    NWAnswer ans_3("3,2,1,0", "3,2,1,0");     //alginment_graph & alignment_read are reversed
    BasicNW nw_3({'A', 'A', 'C', 'G', 'C'},   //nodes
                 {0, 4, 1, 2, 3},             //sorted_graph
                 {{1, 4}, {2}, {3}, {}, {2}}, //outgoing_edges
                 {'A', 'T', 'C', 'G'});       //read

    test_cases.emplace_back(std::move(ans_3), std::move(nw_3));

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
    NWAnswer ans_4("4,3,2,1,0", "1,-1,-1,-1,0"); //alginment_graph & alignment_read are reversed
    BasicNW nw_4({'A', 'T', 'T', 'G', 'A'},      //nodes
                 {0, 1, 2, 3, 4},                //sorted_graph
                 {{1}, {2}, {3}, {4}, {}},       //outgoing_edges
                 {'A', 'A'});                    //read
    test_cases.emplace_back(std::move(ans_4), std::move(nw_4));

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
    NWAnswer ans_5("4,3,6,5,0", "4,3,2,1,0");           //alignment_graph & alignment_read are reversed
    BasicNW nw_5({'A', 'T', 'G', 'T', 'A', 'C', 'A'},   //nodes
                 {0, 5, 1, 6, 2, 3, 4},                 //sorted_graph
                 {{1, 5}, {2}, {3}, {4}, {}, {6}, {3}}, //outgoing_edges
                 {'A', 'C', 'T', 'T', 'A'});            //read

    test_cases.emplace_back(std::move(ans_5), std::move(nw_5));

    //add more test cases below

    return test_cases;
}

// host function for calling the kernel to test topsort device function.
NWAnswer testNW(const BasicNW& obj)
{
    //declare device buffer
    uint8_t* nodes;
    uint16_t* graph;
    uint16_t* node_id_to_pos;
    uint16_t graph_count; //local
    uint16_t* incoming_edge_count;
    uint16_t* incoming_edges;
    uint16_t* outgoing_edge_count;
    uint16_t* outgoing_edges;
    uint8_t* read;
    uint16_t read_count; //local
    int16_t* scores;
    int16_t* alignment_graph;
    int16_t* alignment_read;
    int16_t gap_score;
    int16_t mismatch_score;
    int16_t match_score;
    uint16_t* aligned_nodes; //local; to store num of nodes aligned (length of alignment_graph and alignment_read)

    //allocate unified memory so they can be accessed by both host and device.
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&nodes, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint8_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&graph, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&node_id_to_pos, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&incoming_edges, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&incoming_edge_count, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edges, CUDAPOA_MAX_NODES_PER_WINDOW * CUDAPOA_MAX_NODE_EDGES * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edge_count, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&scores, CUDAPOA_MAX_MATRIX_GRAPH_DIMENSION * CUDAPOA_MAX_MATRIX_SEQUENCE_DIMENSION * sizeof(int16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&alignment_graph, CUDAPOA_MAX_MATRIX_GRAPH_DIMENSION * sizeof(int16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&read, CUDAPOA_MAX_SEQUENCE_SIZE * sizeof(uint8_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&alignment_read, CUDAPOA_MAX_MATRIX_GRAPH_DIMENSION * sizeof(int16_t)));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&aligned_nodes, sizeof(uint16_t)));

    //initialize all 'count' buffers
    memset((void**)incoming_edge_count, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));
    memset((void**)outgoing_edge_count, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));
    memset((void**)node_id_to_pos, 0, CUDAPOA_MAX_NODES_PER_WINDOW * sizeof(uint16_t));
    memset((void**)scores, 0, CUDAPOA_MAX_MATRIX_GRAPH_DIMENSION * CUDAPOA_MAX_MATRIX_SEQUENCE_DIMENSION * sizeof(int16_t));

    //calculate edge counts on host
    obj.get_graph_buffers(incoming_edges, incoming_edge_count,
                          outgoing_edges, outgoing_edge_count,
                          nodes, &graph_count,
                          graph, node_id_to_pos);
    obj.get_read_buffers(read, &read_count);
    gap_score      = BasicNW::gap_score_;
    mismatch_score = BasicNW::mismatch_score_;
    match_score    = BasicNW::match_score_;

    //call the host wrapper of nw kernel
    runNW(nodes,
          graph,
          node_id_to_pos,
          graph_count,
          incoming_edge_count,
          incoming_edges,
          outgoing_edge_count,
          outgoing_edges,
          read,
          read_count,
          scores,
          CUDAPOA_MAX_MATRIX_SEQUENCE_DIMENSION,
          alignment_graph,
          alignment_read,
          gap_score,
          mismatch_score,
          match_score,
          aligned_nodes);

    CGA_CU_CHECK_ERR(cudaDeviceSynchronize());

    //input and output buffers are the same ones in unified memory, so the results are updated in place
    //results are stored in alignment_graph and alignment_read; return string representation of those
    auto res = std::make_pair(claragenomics::stringutils::array_to_string<int16_t>(alignment_graph, *aligned_nodes, ","),
                              claragenomics::stringutils::array_to_string<int16_t>(alignment_read, *aligned_nodes, ","));

    CGA_CU_CHECK_ERR(cudaFree(nodes));
    CGA_CU_CHECK_ERR(cudaFree(graph));
    CGA_CU_CHECK_ERR(cudaFree(node_id_to_pos));
    CGA_CU_CHECK_ERR(cudaFree(incoming_edges));
    CGA_CU_CHECK_ERR(cudaFree(incoming_edge_count));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edges));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edge_count));
    CGA_CU_CHECK_ERR(cudaFree(scores));
    CGA_CU_CHECK_ERR(cudaFree(alignment_graph));
    CGA_CU_CHECK_ERR(cudaFree(read));
    CGA_CU_CHECK_ERR(cudaFree(alignment_read));
    CGA_CU_CHECK_ERR(cudaFree(aligned_nodes));

    return res;
}

using ::testing::TestWithParam;
using ::testing::ValuesIn;

class NWTest : public TestWithParam<NWTestPair>
{
public:
    void SetUp() {}

    NWAnswer runNWTest(const BasicNW& nw)
    {
        return testNW(nw);
    }
};

TEST_P(NWTest, TestNWCorrectness)
{
    const auto test_case = GetParam();
    EXPECT_EQ(test_case.first, runNWTest(test_case.second));
}

INSTANTIATE_TEST_SUITE_P(TestNW, NWTest, ValuesIn(getNWTestCases()));

} // namespace cudapoa

} // namespace claragenomics

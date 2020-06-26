/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "../src/cudapoa_kernels.cuh" //runTopSort

#include <claragenomics/cudapoa/batch.hpp>
#include <claragenomics/utils/cudautils.hpp>            //CGA_CU_CHECK_ERR
#include <claragenomics/utils/stringutils.hpp>          //array_to_string
#include <claragenomics/utils/signed_integer_utils.hpp> //get_size

#include "gtest/gtest.h"

namespace claragenomics
{

namespace cudapoa
{

// alias for the 2d vector graph representation
typedef std::vector<std::vector<uint16_t>> Uint16Vec2D;
// alias for a test case (answer, graph)
typedef std::pair<std::string, Uint16Vec2D> TopSortTestPair;

using ::testing::TestWithParam;
using ::testing::ValuesIn;

// create a vector of test cases
std::vector<TopSortTestPair> getTopSortTestCases()
{

    std::vector<TopSortTestPair> test_cases;

    Uint16Vec2D outgoing_edges_1 = {{}, {}, {3}, {1}, {0, 1}, {0, 2}};
    std::string answer_1         = "4-5-0-2-3-1";
    test_cases.emplace_back(answer_1, outgoing_edges_1);

    Uint16Vec2D outgoing_edges_2 = {{1, 3}, {2, 3}, {3, 4, 5}, {4, 5}, {5}, {}};
    std::string answer_2         = "0-1-2-3-4-5";
    test_cases.emplace_back(answer_2, outgoing_edges_2);

    Uint16Vec2D outgoing_edges_3 = {{}, {}, {3}, {1}, {0, 1, 7}, {0, 2}, {4}, {5}};
    std::string answer_3         = "6-4-7-5-0-2-3-1";
    test_cases.emplace_back(answer_3, outgoing_edges_3);

    //add more test cases below

    return test_cases;
}

// host function for calling the kernel to test topsort device function.
std::string testTopSortDeviceUtil(uint16_t node_count, std::vector<std::vector<uint16_t>> outgoing_edges_vec)
{
    //declare device buffer
    uint16_t* sorted_poa;
    uint16_t* sorted_poa_node_map;
    uint16_t* incoming_edge_count;
    uint16_t* outgoing_edges;
    uint16_t* outgoing_edge_count;
    uint16_t* local_incoming_edge_count;

    size_t graph_size = node_count * sizeof(uint16_t);

    //allocate unified memory so they can be accessed by both host and device.
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&sorted_poa, graph_size));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&sorted_poa_node_map, graph_size));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&incoming_edge_count, graph_size));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edges, graph_size * CUDAPOA_MAX_NODE_EDGES));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&outgoing_edge_count, graph_size));
    CGA_CU_CHECK_ERR(cudaMallocManaged((void**)&local_incoming_edge_count, graph_size));

    //initialize incoming_edge_count & local_incoming_edge_count
    memset((void**)incoming_edge_count, 0, graph_size);
    memset((void**)local_incoming_edge_count, 0, graph_size);

    //calculate edge counts on host

    uint16_t out_node;
    for (int i = 0; i < node_count; i++)
    {
        outgoing_edge_count[i] = get_size(outgoing_edges_vec[i]);
        for (int j = 0; j < get_size(outgoing_edges_vec[i]); j++)
        {
            out_node = outgoing_edges_vec[i][j];
            incoming_edge_count[out_node]++;
            local_incoming_edge_count[out_node]++;
            outgoing_edges[i * CUDAPOA_MAX_NODE_EDGES + j] = out_node;
        }
    }

    // call the host wrapper of topsort kernel
    runTopSort(sorted_poa,
               sorted_poa_node_map,
               node_count,
               incoming_edge_count,
               outgoing_edges,
               outgoing_edge_count,
               local_incoming_edge_count);

    CGA_CU_CHECK_ERR(cudaDeviceSynchronize());

    std::string res = claragenomics::stringutils::array_to_string<uint16_t>(sorted_poa, node_count);

    CGA_CU_CHECK_ERR(cudaFree(sorted_poa));
    CGA_CU_CHECK_ERR(cudaFree(sorted_poa_node_map));
    CGA_CU_CHECK_ERR(cudaFree(incoming_edge_count));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edges));
    CGA_CU_CHECK_ERR(cudaFree(outgoing_edge_count));
    CGA_CU_CHECK_ERR(cudaFree(local_incoming_edge_count));

    return res;
}

class TopSortDeviceUtilTest : public TestWithParam<TopSortTestPair>
{
public:
    void SetUp() {}

    std::string runTopSortDevice(Uint16Vec2D outgoing_edges)
    {
        return testTopSortDeviceUtil(get_size(outgoing_edges), outgoing_edges);
    }
};

TEST_P(TopSortDeviceUtilTest, TestTopSotCorrectness)
{
    const auto test_case = GetParam();
    EXPECT_EQ(test_case.first, runTopSortDevice(test_case.second));
}

INSTANTIATE_TEST_SUITE_P(TestTopSort, TopSortDeviceUtilTest, ValuesIn(getTopSortTestCases()));

} // namespace cudapoa

} // namespace claragenomics

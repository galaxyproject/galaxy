/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <claragenomics/utils/graph.hpp>

#include "gtest/gtest.h"

namespace claragenomics
{

TEST(GraphTest, DirectedGraph)
{
    DirectedGraph graph;

    // Sample graph
    //      3
    //      ^
    //      |
    // 1 -> 2 -> 5
    //      |    ^
    //      u    |
    //      4 ---|

    graph.add_edge(1, 2);
    graph.add_edge(2, 5);
    graph.add_edge(2, 3);
    graph.add_edge(2, 4);
    graph.add_edge(4, 5);

    const auto& adjacent_nodes_to_2 = graph.get_adjacent_nodes(2);
    EXPECT_NE(std::find(adjacent_nodes_to_2.begin(), adjacent_nodes_to_2.end(), 3), adjacent_nodes_to_2.end());
    EXPECT_NE(std::find(adjacent_nodes_to_2.begin(), adjacent_nodes_to_2.end(), 4), adjacent_nodes_to_2.end());
    EXPECT_NE(std::find(adjacent_nodes_to_2.begin(), adjacent_nodes_to_2.end(), 5), adjacent_nodes_to_2.end());
    EXPECT_EQ(std::find(adjacent_nodes_to_2.begin(), adjacent_nodes_to_2.end(), 1), adjacent_nodes_to_2.end());

    const auto& adjacent_nodes_to_3 = graph.get_adjacent_nodes(3);
    EXPECT_EQ(std::find(adjacent_nodes_to_3.begin(), adjacent_nodes_to_3.end(), 2), adjacent_nodes_to_3.end());
}

TEST(GraphTest, UndirectedGraph)
{
    UndirectedGraph graph;

    // Sample graph
    //      3
    //      |
    //      |
    // 1 -- 2 -- 5
    //      |    |
    //      |    |
    //      4 ---|

    graph.add_edge(1, 2);
    graph.add_edge(2, 5);
    graph.add_edge(2, 3);
    graph.add_edge(2, 4);
    graph.add_edge(4, 5);

    const auto& adjacent_nodes_to_2 = graph.get_adjacent_nodes(2);
    EXPECT_NE(std::find(adjacent_nodes_to_2.begin(), adjacent_nodes_to_2.end(), 3), adjacent_nodes_to_2.end());
    EXPECT_NE(std::find(adjacent_nodes_to_2.begin(), adjacent_nodes_to_2.end(), 4), adjacent_nodes_to_2.end());
    EXPECT_NE(std::find(adjacent_nodes_to_2.begin(), adjacent_nodes_to_2.end(), 5), adjacent_nodes_to_2.end());
    EXPECT_NE(std::find(adjacent_nodes_to_2.begin(), adjacent_nodes_to_2.end(), 1), adjacent_nodes_to_2.end());

    const auto& adjacent_nodes_to_3 = graph.get_adjacent_nodes(3);
    EXPECT_EQ(std::find(adjacent_nodes_to_3.begin(), adjacent_nodes_to_3.end(), 1), adjacent_nodes_to_3.end());
    EXPECT_NE(std::find(adjacent_nodes_to_3.begin(), adjacent_nodes_to_3.end(), 2), adjacent_nodes_to_3.end());
}

} // namespace claragenomics

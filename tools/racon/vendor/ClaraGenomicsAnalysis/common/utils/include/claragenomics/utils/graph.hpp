/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#pragma once

#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <cstdint>
#include <string>
#include <iostream>
#include <sstream>
#include <algorithm>

namespace claragenomics
{

/// \struct PairHash
/// Hash function for a pair
struct PairHash
{
public:
    /// \brief Operator overload to define hash function
    template <class T1, class T2>
    size_t operator()(const std::pair<T1, T2>& pair) const
    {
        size_t hash_1 = std::hash<T1>()(pair.first);
        size_t hash_2 = std::hash<T2>()(pair.second);
        return hash_1 ^ hash_2;
    }
};

/// \brief Object representing a generic graph structure
class Graph
{
public:
    /// Typedef for node ID
    using node_id_t = int32_t;
    /// Tpyedef for edge weight
    using edge_weight_t = int32_t;
    /// Typedef for edge
    using edge_t = std::pair<node_id_t, node_id_t>;

    /// \brief Get a list of adjacent nodes to a given node
    ///
    /// \param node Node for which adjacent nodes are requested
    /// \return Vector of adjacent node IDs
    const std::vector<node_id_t>& get_adjacent_nodes(node_id_t node) const
    {
        auto iter = adjacent_nodes_.find(node);
        if (iter != adjacent_nodes_.end())
        {
            return iter->second;
        }
        else
        {
            return Graph::empty_;
        }
    }

    /// \brief List all node IDs in the graph
    ///
    /// \return A vector of node IDs
    const std::vector<node_id_t> get_node_ids() const
    {
        std::vector<node_id_t> nodes;
        for (auto iter : adjacent_nodes_)
        {
            nodes.push_back(iter.first);
        }

        return nodes;
    }

    /// \brief Get a list of all edges in the graph
    ///
    /// \return A vector of edges
    const std::vector<std::pair<edge_t, edge_weight_t>> get_edges() const
    {
        return {begin(edges_), end(edges_)};
    }

    /// \brief Add string labels to a node ID
    ///
    /// \param node ID of node
    /// \param label Label to attach to that node ID
    void set_node_label(node_id_t node, const std::string& label)
    {
        node_labels_.insert({node, label});
    }

    /// \brief Get the label associated with a node
    ///
    /// \param node node ID for label query
    /// \return String label for associated node. Returns empty string if
    //          no label is associated or node ID doesn't exist.
    std::string get_node_label(node_id_t node) const
    {
        auto found_node = node_labels_.find(node);
        if (found_node != node_labels_.end())
        {
            return found_node->second;
        }
        else
        {
            return "";
        }
    }

protected:
    /// \brief Check if a directed edge exists in the grph
    ///
    /// \param edge A directed edge
    /// \return Boolean result of check
    bool directed_edge_exists(edge_t edge)
    {
        return edges_.find(edge) != edges_.end();
    }

    /// \brief Update the adjacent nodes based on edge information
    ///
    /// \param edge A directed edge
    void update_adject_nodes(edge_t edge)
    {
        auto find_node = adjacent_nodes_.find(edge.first);
        if (find_node == adjacent_nodes_.end())
        {
            adjacent_nodes_.insert({edge.first, {edge.second}});
        }
        else
        {
            find_node->second.push_back(edge.second);
        }
    }

    /// \brief Serialize node labels to dot format
    ///
    /// \param dot_str Output string stream to serialize labels to
    void node_labels_to_dot(std::ostringstream& dot_str) const
    {
        for (auto iter : node_labels_)
        {
            dot_str << iter.first << " [label=\"" << iter.second << "\"];\n";
        }
    }

    /// \brief Serialize edges to dot format
    ///
    /// \param dot_str Output string stream to serialize labels to
    /// \param node_separator DOT delimiter for edge description
    void edges_to_dot(std::ostringstream& dot_str, const std::string& node_separator) const
    {
        for (auto iter : edges_)
        {
            const edge_t& edge          = iter.first;
            const edge_weight_t& weight = iter.second;
            dot_str << edge.first << " " << node_separator << " " << edge.second;
            dot_str << " [label=\"" << weight << "\"];\n";
        }
    }

    /// List of adjacent nodes per node ID
    std::unordered_map<node_id_t, std::vector<node_id_t>> adjacent_nodes_;

    /// All edges in the graph
    std::unordered_map<edge_t, edge_weight_t, PairHash> edges_;

    /// Label per node
    std::unordered_map<node_id_t, std::string> node_labels_;

    /// An empty list representing no connectivity
    const std::vector<node_id_t> empty_;
};

/// \brief DirectedGraph Object representing a directed graph structure
class DirectedGraph : public Graph
{
public:
    /// Typedef for node ID
    using Graph::node_id_t;
    /// Tpyedef for edge weight
    using Graph::edge_weight_t;
    /// Typedef for edge
    using Graph::edge_t;

    /// \brief Add directed edges to graph.
    ///
    /// \param node_id_from Source node ID
    /// \param node_id_to Sink node ID
    /// \param weight Edge weight
    void add_edge(node_id_t node_id_from, node_id_t node_id_to, edge_weight_t weight = 0)
    {
        auto edge = edge_t(node_id_from, node_id_to);
        if (!directed_edge_exists(edge))
        {
            edges_.insert({edge, weight});
            update_adject_nodes(edge);
        }
    }

    /// \brief Serialize graph structure to dot format
    ///
    /// \return A string encoding the graph in dot format
    std::string serialize_to_dot() const
    {
        std::ostringstream dot_str;
        dot_str << "digraph g {\n";

        // Get nodel labels, if any.
        node_labels_to_dot(dot_str);

        // Get edges.
        edges_to_dot(dot_str, "->");

        dot_str << "}\n";
        return dot_str.str();
    }
};

/// \brief UndirectedGraph Object representing an undirected graph structure
class UndirectedGraph : public Graph
{
public:
    /// Typedef for node ID
    using Graph::node_id_t;
    /// Tpyedef for edge weight
    using Graph::edge_weight_t;
    /// Typedef for edge
    using Graph::edge_t;

    /// \brief Add undirected edges to graph.
    ///
    /// \param node_id_from Source node ID
    /// \param node_id_to Sink node ID
    /// \param weight Edge weight
    void add_edge(node_id_t node_id_from, node_id_t node_id_to, edge_weight_t weight = 0)
    {
        auto edge          = edge_t(node_id_from, node_id_to);
        auto edge_reversed = edge_t(node_id_to, node_id_from);
        if (!directed_edge_exists(edge) && !directed_edge_exists(edge_reversed))
        {
            edges_.insert({edge, weight});
            update_adject_nodes(edge);
            update_adject_nodes(edge_reversed);
        }
    }

    /// \brief Serialize graph structure to dot format
    ///
    /// \return A string encoding the graph in dot format
    std::string serialize_to_dot() const
    {
        std::ostringstream dot_str;
        dot_str << "graph g {\n";

        // Get nodel labels, if any.
        node_labels_to_dot(dot_str);

        // Get edges.
        edges_to_dot(dot_str, "--");

        dot_str << "}\n";
        return dot_str.str();
    }
};

} // namespace claragenomics

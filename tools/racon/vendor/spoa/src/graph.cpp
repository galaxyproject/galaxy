/*!
 * @file graph.cpp
 *
 * @brief Graph class source file
 */

#include <assert.h>
#include <algorithm>
#include <stack>
#include <fstream>

#include "spoa/graph.hpp"

namespace spoa {

constexpr std::uint32_t kMaxAlphabetSize = 256;

std::unique_ptr<Node> Graph::createNode(std::uint32_t id, std::uint32_t code) {
    return std::unique_ptr<Node>(new Node(id, code));
}

Node::Node(std::uint32_t id, std::uint32_t code)
        : id_(id), code_(code), in_edges_(), out_edges_(),
        aligned_nodes_ids_() {
}

Node::~Node() {
}

bool Node::successor(std::uint32_t& dst, std::uint32_t label) const {

    for (const auto& edge: out_edges_) {
        for (const auto& l: edge->sequence_labels_) {
            if (l == label) {
                dst = edge->end_node_id_;
                return true;
            }
        }
    }
    return false;
}

std::uint32_t Node::coverage() const {

    std::unordered_set<std::uint32_t> label_set;
    for (const auto& edge: in_edges_) {
        for (const auto& label: edge->sequence_labels_) {
            label_set.insert(label);
        }
    }
    for (const auto& edge: out_edges_) {
        for (const auto& label: edge->sequence_labels_) {
            label_set.insert(label);
        }
    }
    return label_set.size();
}

std::unique_ptr<Edge> Graph::createEdge(std::uint32_t begin_node_id,
    std::uint32_t end_node_id, std::uint32_t label, std::uint32_t weight) {

    return std::unique_ptr<Edge>(new Edge(begin_node_id, end_node_id, label,
        weight));
}

Edge::Edge(std::uint32_t begin_node_id, std::uint32_t end_node_id,
    std::uint32_t label, std::uint32_t weight)
        : begin_node_id_(begin_node_id), end_node_id_(end_node_id),
        sequence_labels_(1, label), total_weight_(weight) {
}

Edge::~Edge() {
}

void Edge::add_sequence(std::uint32_t label, std::uint32_t weight) {
    sequence_labels_.emplace_back(label);
    total_weight_ += weight;
}

std::unique_ptr<Graph> createGraph() {
    return std::unique_ptr<Graph>(new Graph());
}

Graph::Graph()
        : num_sequences_(0), num_codes_(0), coder_(kMaxAlphabetSize, -1),
        decoder_(kMaxAlphabetSize, -1), nodes_(), rank_to_node_id_(),
        sequences_begin_nodes_ids_(), consensus_() {
}

Graph::~Graph() {
}

std::uint32_t Graph::add_node(std::uint32_t code) {
    std::uint32_t node_id = nodes_.size();
    nodes_.emplace_back(createNode(node_id, code));
    return node_id;
}

void Graph::add_edge(std::uint32_t begin_node_id, std::uint32_t end_node_id,
    std::uint32_t weight) {

    assert(begin_node_id < nodes_.size() && end_node_id < nodes_.size());

    for (const auto& edge: nodes_[begin_node_id]->out_edges_) {
        if (edge->end_node_id_ == end_node_id) {
            edge->add_sequence(num_sequences_, weight);
            return;
        }
    }

    std::shared_ptr<Edge> edge = createEdge(begin_node_id, end_node_id,
        num_sequences_, weight);
    nodes_[begin_node_id]->out_edges_.emplace_back(edge);
    nodes_[end_node_id]->in_edges_.emplace_back(edge);
}

void Graph::add_alignment(const Alignment& alignment,
    const std::string& sequence, std::uint32_t weight) {

    add_alignment(alignment, sequence.c_str(), sequence.size(), weight);
}

void Graph::add_alignment(const Alignment& alignment, const char* sequence,
    std::uint32_t sequence_size, std::uint32_t weight) {

    std::vector<std::uint32_t> weights(sequence_size, weight);
    add_alignment(alignment, sequence, sequence_size, weights);
}

void Graph::add_alignment(const Alignment& alignment, const std::string& sequence,
    const std::string& quality) {

    add_alignment(alignment, sequence.c_str(), sequence.size(),
        quality.c_str(), quality.size());
}

void Graph::add_alignment(const Alignment& alignment, const char* sequence,
    std::uint32_t sequence_size, const char* quality,
    std::uint32_t quality_size) {

    std::vector<std::uint32_t> weights;
    for (std::uint32_t i = 0; i < quality_size; ++i) {
        weights.emplace_back(static_cast<std::uint32_t>(quality[i] - 33)); // PHRED quality
    }
    add_alignment(alignment, sequence, sequence_size, weights);
}

void Graph::add_alignment(const Alignment& alignment, const std::string& sequence,
    const std::vector<std::uint32_t>& weights) {

    add_alignment(alignment, sequence.c_str(), sequence.size(), weights);
}

void Graph::add_alignment(const Alignment& alignment, const char* sequence,
    std::uint32_t sequence_size, const std::vector<std::uint32_t>& weights) {

    if (sequence_size == 0) {
        return;
    }
    if (sequence_size != weights.size()) {
        throw std::invalid_argument("[spoa::Graph::add_alignment] error: "
            "sequence and weights are of unequal size!");
    }

    for (std::uint32_t i = 0; i < sequence_size; ++i) {
        auto c = sequence[i];
        if (coder_[c] == -1) {
            coder_[c] = num_codes_;
            decoder_[num_codes_] = c;
            ++num_codes_;
        }
    }

    if (alignment.empty()) { // no alignment
        std::int32_t begin_node_id = add_sequence(sequence, weights, 0,
            sequence_size);
        ++num_sequences_;
        sequences_begin_nodes_ids_.emplace_back(begin_node_id);

        topological_sort();
        return;
    }

    std::vector<std::uint32_t> valid_seq_ids;
    for (const auto& it: alignment) {
        if (it.second != -1) {
            valid_seq_ids.emplace_back(it.second);
        }
    }

    assert(valid_seq_ids.front() <= sequence_size);
    assert(valid_seq_ids.back() + 1 <= sequence_size);

    std::uint32_t tmp = nodes_.size();
    std::int32_t begin_node_id = add_sequence(sequence, weights, 0,
        valid_seq_ids.front());
    std::int32_t head_node_id = tmp == nodes_.size() ? -1 : nodes_.size() - 1;

    std::int32_t tail_node_id = add_sequence(sequence, weights,
        valid_seq_ids.back() + 1, sequence_size);

    std::int32_t new_node_id = -1;
    float prev_weight = head_node_id == -1 ?
        0 : weights[valid_seq_ids.front() - 1];

    for (std::uint32_t i = 0; i < alignment.size(); ++i) {
        if (alignment[i].second == -1) {
            continue;
        }

        char letter = sequence[alignment[i].second];
        if (alignment[i].first == -1) {
            new_node_id = add_node(coder_[letter]);

        } else {
            if (decoder_[nodes_[alignment[i].first]->code_] == letter) {
                new_node_id = alignment[i].first;

            } else {
                std::int32_t aligned_to_node_id = -1;
                for (const auto& aid: nodes_[alignment[i].first]->aligned_nodes_ids_) {
                    if (decoder_[nodes_[aid]->code_] == letter) {
                        aligned_to_node_id = aid;
                        break;
                    }
                }

                if (aligned_to_node_id == -1) {
                    new_node_id = add_node(coder_[letter]);

                    for (const auto& aid: nodes_[alignment[i].first]->aligned_nodes_ids_) {
                        nodes_[new_node_id]->aligned_nodes_ids_.emplace_back(aid);
                        nodes_[aid]->aligned_nodes_ids_.emplace_back(new_node_id);
                    }

                    nodes_[new_node_id]->aligned_nodes_ids_.emplace_back(
                        alignment[i].first);
                    nodes_[alignment[i].first]->aligned_nodes_ids_.emplace_back(
                        new_node_id);

                } else {
                    new_node_id = aligned_to_node_id;
                }
            }
        }

        if (begin_node_id == -1) {
            begin_node_id = new_node_id;
        }

        if (head_node_id != -1) {
            // both nodes contribute to edge weight
            add_edge(head_node_id, new_node_id,
                prev_weight + weights[alignment[i].second]);
        }

        head_node_id = new_node_id;
        prev_weight = weights[alignment[i].second];
    }

    if (tail_node_id != -1) {
        // both nodes contribute to edge weight
        add_edge(head_node_id, tail_node_id,
            prev_weight + weights[valid_seq_ids.back() + 1]);
    }

    ++num_sequences_;
    sequences_begin_nodes_ids_.emplace_back(begin_node_id);

    topological_sort();
}

std::int32_t Graph::add_sequence(const char* sequence,
    const std::vector<std::uint32_t>& weights, std::uint32_t begin,
    std::uint32_t end) {

    if (begin == end) {
        return -1;
    }

    std::int32_t first_node_id = add_node(coder_[sequence[begin]]);

    std::uint32_t node_id;
    for (std::uint32_t i = begin + 1; i < end; ++i) {
        node_id = add_node(coder_[sequence[i]]);
        // both nodes contribute to edge weight
        add_edge(node_id - 1, node_id, weights[i - 1] + weights[i]);
    }

    return first_node_id;
}

void Graph::topological_sort() {

    rank_to_node_id_.clear();

    // 0 - unmarked, 1 - temporarily marked, 2 - permanently marked
    std::vector<std::uint8_t> node_marks(nodes_.size(), 0);
    std::vector<bool> check_aligned_nodes(nodes_.size(), true);
    std::stack<std::uint32_t> nodes_to_visit;

    for (std::uint32_t i = 0; i < nodes_.size(); ++i) {
        if (node_marks[i] != 0) {
            continue;
        }

        nodes_to_visit.push(i);
        while (nodes_to_visit.size() != 0) {
            std::uint32_t node_id = nodes_to_visit.top();
            bool valid = true;

            if (node_marks[node_id] != 2) {
                for (const auto& edge: nodes_[node_id]->in_edges_) {
                    if (node_marks[edge->begin_node_id_] != 2) {
                        nodes_to_visit.push(edge->begin_node_id_);
                        valid = false;
                    }
                }

                if (check_aligned_nodes[node_id]) {
                    for (const auto& aid: nodes_[node_id]->aligned_nodes_ids_) {
                        if (node_marks[aid] != 2) {
                            nodes_to_visit.push(aid);
                            check_aligned_nodes[aid] = false;
                            valid = false;
                        }
                    }
                }

                assert((valid || node_marks[node_id] != 1) &&
                    "Graph is not a DAG!");

                if (valid) {
                    node_marks[node_id] = 2;
                    if (check_aligned_nodes[node_id]) {
                        rank_to_node_id_.push_back(node_id);
                        for (const auto& aid: nodes_[node_id]->aligned_nodes_ids_) {
                            rank_to_node_id_.emplace_back(aid);
                        }
                    }
                } else {
                    node_marks[node_id] = 1;
                }
            }

            if (valid) {
                nodes_to_visit.pop();
            }
        }
    }

    assert(is_topologically_sorted() == true);
}

bool Graph::is_topologically_sorted() const {
    assert(nodes_.size() == rank_to_node_id_.size());

    std::vector<bool> visited_nodes(nodes_.size(), false);
    for (std::uint32_t node_id: rank_to_node_id_) {
        for (const auto& edge: nodes_[node_id]->in_edges_) {
            if (visited_nodes[edge->begin_node_id_] == false) {
                return false;
            }
        }
        visited_nodes[node_id] = true;
    }

    return true;
}

std::uint32_t Graph::initialize_multiple_sequence_alignment(
    std::vector<std::uint32_t>& dst) const {

    dst.resize(nodes_.size(), 0);

    std::uint32_t msa_id = 0;
    for (std::uint32_t i = 0; i < nodes_.size(); ++i) {
        std::uint32_t node_id = rank_to_node_id_[i];

        dst[node_id] = msa_id;
        for (std::uint32_t j = 0; j < nodes_[node_id]->aligned_nodes_ids_.size(); ++j) {
            dst[rank_to_node_id_[++i]] = msa_id;
        }
        ++msa_id;
    }

    return msa_id;
}

void Graph::generate_multiple_sequence_alignment(std::vector<std::string>& dst,
    bool include_consensus) {

    // assign msa id to each node
    std::vector<std::uint32_t> node_id_to_msa_id;
    auto msa_length = initialize_multiple_sequence_alignment(node_id_to_msa_id);

    // extract sequences from graph and create msa strings (add indels(-) where
    // necessary)
    for (std::uint32_t i = 0; i < num_sequences_; ++i) {
        std::string alignment_str(msa_length, '-');
        std::uint32_t node_id = sequences_begin_nodes_ids_[i];

        while (true) {
            alignment_str[node_id_to_msa_id[node_id]] =
                decoder_[nodes_[node_id]->code_];

            if (!nodes_[node_id]->successor(node_id, i)) {
                break;
            }
        }

        dst.emplace_back(alignment_str);
    }

    if (include_consensus) {
        // do the same for consensus sequence
        traverse_heaviest_bundle();

        std::string alignment_str(msa_length, '-');
        for (const auto& node_id: consensus_) {
            alignment_str[node_id_to_msa_id[node_id]] =
                decoder_[nodes_[node_id]->code_];
        }
        dst.emplace_back(alignment_str);
    }
}

std::string Graph::generate_consensus() {

    traverse_heaviest_bundle();
    std::string consensus_str = "";
    for (const auto& node_id: consensus_) {
        consensus_str += decoder_[nodes_[node_id]->code_];
    }

    return consensus_str;
}

std::string Graph::generate_consensus(std::vector<std::uint32_t>& dst,
    bool verbose) {

    auto consensus_str = generate_consensus();

    dst.clear();
    if (verbose == false) {
        for (const auto& node_id: consensus_) {
            std::uint32_t total_coverage = nodes_[node_id]->coverage();
            for (const auto& aid: nodes_[node_id]->aligned_nodes_ids_) {
                total_coverage += nodes_[aid]->coverage();
            }
            dst.emplace_back(total_coverage);
        }
    } else {
        dst.resize((num_codes_ + 1) * consensus_.size(), 0);

        std::vector<std::uint32_t> node_id_to_msa_id;
        initialize_multiple_sequence_alignment(node_id_to_msa_id);

        for (std::uint32_t i = 0; i < num_sequences_; ++i) {
            auto node_id = sequences_begin_nodes_ids_[i];

            bool count_indels = false;
            std::uint32_t c = 0, l;
            while (true) {
                for (; c < consensus_.size() &&
                    node_id_to_msa_id[consensus_[c]] < node_id_to_msa_id[node_id]; ++c);
                if (c >= consensus_.size()) {
                    break;
                }

                if (node_id_to_msa_id[consensus_[c]] == node_id_to_msa_id[node_id]) {
                    if (count_indels) {
                        for (std::uint32_t j = l + 1; j < c; ++j) {
                            ++dst[num_codes_ * consensus_.size() + j];
                        }
                    }
                    count_indels = true;
                    l = c;

                    ++dst[nodes_[node_id]->code_ * consensus_.size() + c];
                }

                if (!nodes_[node_id]->successor(node_id, i)) {
                    break;
                }
            }
        }
    }

    return consensus_str;
}

void Graph::traverse_heaviest_bundle() {

    std::vector<std::int32_t> predecessors(nodes_.size(), -1);
    std::vector<std::int64_t> scores(nodes_.size(), -1);

    std::uint32_t max_score_id = 0;
    for (const auto& node_id: rank_to_node_id_) {
        for (const auto& edge: nodes_[node_id]->in_edges_) {
            if (scores[node_id] < edge->total_weight_ ||
                (scores[node_id] == edge->total_weight_ &&
                scores[predecessors[node_id]] <= scores[edge->begin_node_id_])) {

                scores[node_id] = edge->total_weight_;
                predecessors[node_id] = edge->begin_node_id_;
            }
        }

        if (predecessors[node_id] != -1) {
            scores[node_id] += scores[predecessors[node_id]];
        }

        if (scores[max_score_id] < scores[node_id]) {
            max_score_id = node_id;
        }
    }

    if (nodes_[max_score_id]->out_edges_.size() != 0) {

        std::vector<std::uint32_t> node_id_to_rank(nodes_.size(), 0);
        for (std::uint32_t i = 0; i < nodes_.size(); ++i) {
            node_id_to_rank[rank_to_node_id_[i]] = i;
        }

        while (nodes_[max_score_id]->out_edges_.size() != 0) {
            max_score_id = branch_completion(scores, predecessors,
                node_id_to_rank[max_score_id]);
        }
    }

    // traceback
    consensus_.clear();
    while (predecessors[max_score_id] != -1) {
        consensus_.emplace_back(max_score_id);
        max_score_id = predecessors[max_score_id];
    }
    consensus_.emplace_back(max_score_id);

    std::reverse(consensus_.begin(), consensus_.end());
}

std::uint32_t Graph::branch_completion(std::vector<std::int64_t>& scores,
    std::vector<std::int32_t>& predecessors, std::uint32_t rank) {

    std::uint32_t node_id = rank_to_node_id_[rank];
    for (const auto& edge: nodes_[node_id]->out_edges_) {
        for (const auto& o_edge: nodes_[edge->end_node_id_]->in_edges_) {
            if (o_edge->begin_node_id_ != node_id) {
                scores[o_edge->begin_node_id_] = -1;
            }
        }
    }

    std::int64_t max_score = 0;
    std::uint32_t max_score_id = 0;
    for (std::uint32_t i = rank + 1; i < rank_to_node_id_.size(); ++i) {

        std::uint32_t node_id = rank_to_node_id_[i];
        scores[node_id] = -1;
        predecessors[node_id] = -1;

        for (const auto& edge: nodes_[node_id]->in_edges_) {
            if (scores[edge->begin_node_id_] == -1) {
                continue;
            }

            if (scores[node_id] < edge->total_weight_ ||
                (scores[node_id] == edge->total_weight_ &&
                scores[predecessors[node_id]] <= scores[edge->begin_node_id_])) {

                scores[node_id] = edge->total_weight_;
                predecessors[node_id] = edge->begin_node_id_;
            }
        }

        if (predecessors[node_id] != -1) {
            scores[node_id] += scores[predecessors[node_id]];
        }

        if (max_score < scores[node_id]) {
            max_score = scores[node_id];
            max_score_id = node_id;
        }
    }

    return max_score_id;
}

// backtracing from right to left!
void Graph::extract_subgraph_nodes(std::vector<bool>& dst,
    std::uint32_t begin_node_id, std::uint32_t end_node_id) const {

    dst.resize(nodes_.size(), false);

    std::stack<std::uint32_t> nodes_to_visit;
    nodes_to_visit.push(begin_node_id);

    while (nodes_to_visit.size() != 0) {
        std::uint32_t node_id = nodes_to_visit.top();
        nodes_to_visit.pop();

        if (dst[node_id] == false && node_id >= end_node_id) {
            for (const auto& edge: nodes_[node_id]->in_edges_) {
                nodes_to_visit.push(edge->begin_node_id_);
            }
            for (const auto& aid: nodes_[node_id]->aligned_nodes_ids_) {
                nodes_to_visit.push(aid);
            }

            dst[node_id] = true;
        }
    }
}

std::unique_ptr<Graph> Graph::subgraph(std::uint32_t begin_node_id,
    std::uint32_t end_node_id,
    std::vector<std::int32_t>& subgraph_to_graph_mapping) const {

    std::vector<bool> is_subgraph_node;
    extract_subgraph_nodes(is_subgraph_node, end_node_id, begin_node_id);

    // init subgraph
    auto subgraph = std::unique_ptr<Graph>(new Graph());
    subgraph->num_sequences_ = num_sequences_;
    subgraph->num_codes_ = num_codes_;
    subgraph->coder_ = std::vector<std::int32_t>(coder_);
    subgraph->decoder_ = std::vector<std::int32_t>(decoder_);

    // create mapping from subgraph to graph and vice versa and add nodes to
    // subgraph
    subgraph_to_graph_mapping.resize(nodes_.size(), -1);
    std::vector<std::int32_t> graph_to_subgraph_mapping(nodes_.size(), -1);

    for (std::uint32_t i = 0; i < is_subgraph_node.size(); ++i) {
        if (is_subgraph_node[i] == false) {
            continue;
        }

        std::uint32_t subgraph_id = subgraph->add_node(nodes_[i]->code_);
        graph_to_subgraph_mapping[i] = subgraph_id;
        subgraph_to_graph_mapping[subgraph_id] = i;
    }

    // add edges and aligned nodes
    for (std::uint32_t i = 0; i < is_subgraph_node.size(); ++i) {
        if (is_subgraph_node[i] == false) {
            continue;
        }

        std::uint32_t subgraph_id = graph_to_subgraph_mapping[i];

        for (const auto& edge: nodes_[i]->in_edges_) {
            if (graph_to_subgraph_mapping[edge->begin_node_id_] == -1) {
                continue;
            }
            subgraph->add_edge(graph_to_subgraph_mapping[edge->begin_node_id_],
                subgraph_id, edge->total_weight_);
        }
        for (const auto& aid: nodes_[i]->aligned_nodes_ids_) {
            if (graph_to_subgraph_mapping[aid] == -1) {
                continue;
            }
            subgraph->nodes_[subgraph_id]->aligned_nodes_ids_.emplace_back(
                graph_to_subgraph_mapping[aid]);
        }
    }

    subgraph->topological_sort();

    return subgraph;
}

void Graph::update_alignment(Alignment& alignment,
    const std::vector<std::int32_t>& subgraph_to_graph_mapping) const {

    for (std::uint32_t i = 0; i < alignment.size(); ++i) {
        if (alignment[i].first != -1) {
            alignment[i].first = subgraph_to_graph_mapping[alignment[i].first];
        }
    }
}

void Graph::print_dot(const std::string& path) const {

    if (path.empty()) {
        return;
    }

    std::ofstream out(path);

    std::vector<std::int32_t> in_consensus(nodes_.size(), -1);
    std::int32_t rank = 0;
    for (const auto& id: consensus_) {
        in_consensus[id] = rank++;
    }

    out << "digraph " << num_sequences_ << " {" << std::endl;
    out << "    graph [rankdir=LR]" << std::endl;
    for (std::uint32_t i = 0; i < nodes_.size(); ++i) {
        out << "    " << i << " [label = \"" << i << " - ";
        out << static_cast<char>(decoder_[nodes_[i]->code_]) << "\"";
        if (in_consensus[i] != -1) {
            out << ", style=filled, fillcolor=goldenrod1";
        }
        out << "]" << std::endl;

        for (const auto& edge: nodes_[i]->out_edges_) {
            out << "    " << i << " -> " << edge->end_node_id_;
            out << " [label = \"" << edge->total_weight_ << "\"";
            if (in_consensus[i] + 1 == in_consensus[edge->end_node_id_]) {
                out << ", color=goldenrod1";
            }
            out << "]" << std::endl;
        }
        for (const auto& aid: nodes_[i]->aligned_nodes_ids_) {
            if (aid > i) {
                out << "    " << i << " -> " << aid;
                out << " [style = dotted, arrowhead = none]" << std::endl;
            }
        }
    }
    out << "}" << std::endl;

    out.close();
}

void Graph::clear() {
    std::fill(coder_.begin(), coder_.end(), -1);
    std::fill(decoder_.begin(), decoder_.end(), -1);
    nodes_.clear();
    rank_to_node_id_.clear();
    sequences_begin_nodes_ids_.clear();
    consensus_.clear();
}

}

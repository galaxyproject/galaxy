/*!
 * @file sisd_alignment_engine.cpp
 *
 * @brief SisdAlignmentEngine class source file
 */

#include <limits>
#include <algorithm>

#include "spoa/graph.hpp"
#include "sisd_alignment_engine.hpp"

namespace spoa {

constexpr std::int32_t kNegativeInfinity =
    std::numeric_limits<std::int32_t>::min() + 1024;

std::unique_ptr<AlignmentEngine> createSisdAlignmentEngine(AlignmentType type,
    AlignmentSubtype subtype, std::int8_t m, std::int8_t n, std::int8_t g,
    std::int8_t e, std::int8_t q, std::int8_t c) {

    return std::unique_ptr<AlignmentEngine>(new SisdAlignmentEngine(type,
        subtype, m, n, g, e, q, c));
}

struct SisdAlignmentEngine::Implementation {
    std::vector<std::uint32_t> node_id_to_rank;
    std::vector<std::int32_t> sequence_profile;
    std::vector<std::int32_t> M;
    std::int32_t* H;
    std::int32_t* F;
    std::int32_t* E;
    std::int32_t* O;
    std::int32_t* Q;

    Implementation()
            : node_id_to_rank(), sequence_profile(), M(), H(nullptr), F(nullptr),
            E(nullptr), O(nullptr), Q(nullptr) {
    }
};

SisdAlignmentEngine::SisdAlignmentEngine(AlignmentType type,
    AlignmentSubtype subtype, std::int8_t m, std::int8_t n, std::int8_t g,
    std::int8_t e, std::int8_t q, std::int8_t c)
        : AlignmentEngine(type, subtype, m, n, g, e, q, c),
        pimpl_(new Implementation()) {
}

SisdAlignmentEngine::~SisdAlignmentEngine() {
}

void SisdAlignmentEngine::prealloc(std::uint32_t max_sequence_size,
    std::uint32_t alphabet_size) {

    realloc(max_sequence_size, alphabet_size * max_sequence_size,
        alphabet_size);
}

void SisdAlignmentEngine::realloc(std::uint32_t matrix_width,
    std::uint32_t matrix_height, std::uint32_t num_codes) {

    if (pimpl_->node_id_to_rank.size() < matrix_height - 1) {
        pimpl_->node_id_to_rank.resize(matrix_height - 1, 0);
    }
    if (pimpl_->sequence_profile.size() < num_codes * matrix_width) {
        pimpl_->sequence_profile.resize(num_codes * matrix_width, 0);
    }
    if (subtype_ == AlignmentSubtype::kLinear) {
        if (pimpl_->M.size() < matrix_height * matrix_width) {
            pimpl_->M.resize(matrix_width * matrix_height, 0);
            pimpl_->H = pimpl_->M.data();
            pimpl_->F = nullptr;
            pimpl_->E = nullptr;
        }
    } else if (subtype_ == AlignmentSubtype::kAffine) {
        if (pimpl_->M.size() < 3 * matrix_height * matrix_width) {
            pimpl_->M.resize(3 * matrix_width * matrix_height, 0);
            pimpl_->H = pimpl_->M.data();
            pimpl_->F = pimpl_->H + matrix_width * matrix_height;
            pimpl_->E = pimpl_->F + matrix_width * matrix_height;
        }
    } else if (subtype_ == AlignmentSubtype::kConvex) {
        if (pimpl_->M.size() < 5 * matrix_height * matrix_width) {
            pimpl_->M.resize(5 * matrix_width * matrix_height, 0);
            pimpl_->H = pimpl_->M.data();
            pimpl_->F = pimpl_->H + matrix_width * matrix_height;
            pimpl_->E = pimpl_->F + matrix_width * matrix_height;
            pimpl_->O = pimpl_->E + matrix_width * matrix_height;
            pimpl_->Q = pimpl_->O + matrix_width * matrix_height;
        }
    }
}

void SisdAlignmentEngine::initialize(const char* sequence,
    std::uint32_t sequence_size, const std::unique_ptr<Graph>& graph) noexcept {

    std::uint32_t matrix_width = sequence_size + 1;
    std::uint32_t matrix_height = graph->nodes().size() + 1;

    for (std::uint32_t i = 0; i < graph->num_codes(); ++i) {
        char c = graph->decoder(i);
        pimpl_->sequence_profile[i * matrix_width] = 0;
        for (std::uint32_t j = 0; j < sequence_size; ++j) {
            pimpl_->sequence_profile[i * matrix_width + (j + 1)] =
                (c == sequence[j] ? m_ : n_);
        }
    }

    const auto& rank_to_node_id = graph->rank_to_node_id();

    for (std::uint32_t i = 0; i < rank_to_node_id.size(); ++i) {
        pimpl_->node_id_to_rank[rank_to_node_id[i]] = i;
    }

    // initialize secondary matrices
    switch (subtype_) {
        case AlignmentSubtype::kConvex:
            pimpl_->O[0] = 0;
            pimpl_->Q[0] = 0;
            for (std::uint32_t j = 1; j < matrix_width; ++j) {
                pimpl_->O[j] = kNegativeInfinity;
                pimpl_->Q[j] = q_ + (j - 1) * c_;
            }
            for (std::uint32_t i = 1; i < matrix_height; ++i) {
                const auto& edges =
                    graph->nodes()[rank_to_node_id[i - 1]]->in_edges();
                std::int32_t penalty = edges.empty() ? q_ - c_ : kNegativeInfinity;
                for (const auto& edge: edges) {
                    std::uint32_t pred_i = pimpl_->node_id_to_rank[
                        edge->begin_node_id()] + 1;
                    penalty = std::max(penalty,
                        pimpl_->O[pred_i * matrix_width]);
                }
                pimpl_->O[i * matrix_width] = penalty + c_;
                pimpl_->Q[i * matrix_width] = kNegativeInfinity;
            }
        case AlignmentSubtype::kAffine:
            pimpl_->F[0] = 0;
            pimpl_->E[0] = 0;
            for (std::uint32_t j = 1; j < matrix_width; ++j) {
                pimpl_->F[j] = kNegativeInfinity;
                pimpl_->E[j] = g_ + (j - 1) * e_;
            }
            for (std::uint32_t i = 1; i < matrix_height; ++i) {
                const auto& edges =
                    graph->nodes()[rank_to_node_id[i - 1]]->in_edges();
                std::int32_t penalty = edges.empty() ? g_ - e_ : kNegativeInfinity;
                for (const auto& edge: edges) {
                    std::uint32_t pred_i = pimpl_->node_id_to_rank[
                        edge->begin_node_id()] + 1;
                    penalty = std::max(penalty,
                        pimpl_->F[pred_i * matrix_width]);
                }
                pimpl_->F[i * matrix_width] = penalty + e_;
                pimpl_->E[i * matrix_width] = kNegativeInfinity;
            }
        case AlignmentSubtype::kLinear:
            pimpl_->H[0] = 0;
        default:
            break;
    }

    // initialize primary matrix
    switch (type_) {
        case AlignmentType::kSW:
            for (std::uint32_t j = 1; j < matrix_width; ++j) {
                pimpl_->H[j] = 0;
            }
            for (std::uint32_t i = 1; i < matrix_height; ++i) {
                pimpl_->H[i * matrix_width] = 0;
            }
            break;
        case AlignmentType::kNW:
            switch (subtype_) {
                case AlignmentSubtype::kConvex:
                    for (std::uint32_t j = 1; j < matrix_width; ++j) {
                        pimpl_->H[j] = std::max(pimpl_->Q[j], pimpl_->E[j]);
                    }
                    for (std::uint32_t i = 1; i < matrix_height; ++i) {
                        pimpl_->H[i * matrix_width] = std::max(
                            pimpl_->O[i * matrix_width],
                            pimpl_->F[i * matrix_width]);
                    }
                    break;
                case AlignmentSubtype::kAffine:
                    for (std::uint32_t j = 1; j < matrix_width; ++j) {
                        pimpl_->H[j] = pimpl_->E[j];
                    }
                    for (std::uint32_t i = 1; i < matrix_height; ++i) {
                        pimpl_->H[i * matrix_width] =
                            pimpl_->F[i * matrix_width];
                    }
                    break;
                case AlignmentSubtype::kLinear:
                    for (std::uint32_t j = 1; j < matrix_width; ++j) {
                        pimpl_->H[j] = j * g_;
                    }
                    for (std::uint32_t i = 1; i < matrix_height; ++i) {
                        const auto& edges =
                            graph->nodes()[rank_to_node_id[i - 1]]->in_edges();
                        std::int32_t penalty = edges.empty() ? 0 : kNegativeInfinity;
                        for (const auto& edge: edges) {
                            std::uint32_t pred_i = pimpl_->node_id_to_rank[
                                edge->begin_node_id()] + 1;
                            penalty = std::max(penalty,
                                pimpl_->H[pred_i * matrix_width]);
                        }
                        pimpl_->H[i * matrix_width] = penalty + g_;
                    }
                default:
                    break;
            }
            break;
        case AlignmentType::kOV:
            switch (subtype_) {
                case AlignmentSubtype::kConvex:
                    for (std::uint32_t j = 1; j < matrix_width; ++j) {
                        pimpl_->H[j] = std::max(pimpl_->Q[j], pimpl_->E[j]);
                    }
                    break;
                case AlignmentSubtype::kAffine:
                    for (std::uint32_t j = 1; j < matrix_width; ++j) {
                        pimpl_->H[j] = pimpl_->E[j];
                    }
                    break;
                case AlignmentSubtype::kLinear:
                    for (std::uint32_t j = 1; j < matrix_width; ++j) {
                        pimpl_->H[j] = j * g_;
                    }
                    break;
                default:
                    break;
            }
            for (std::uint32_t i = 1; i < matrix_height; ++i) {
                pimpl_->H[i * matrix_width] = 0;
            }
            break;
        default:
            break;
    }
}

Alignment SisdAlignmentEngine::align(const char* sequence,
    std::uint32_t sequence_size, const std::unique_ptr<Graph>& graph) noexcept {

    if (graph->nodes().empty() || sequence_size == 0) {
        return Alignment();
    }

    if (subtype_ == AlignmentSubtype::kLinear) {
        return linear(sequence, sequence_size, graph);
    } else if (subtype_ == AlignmentSubtype::kAffine) {
        return affine(sequence, sequence_size, graph);
    } else if (subtype_ == AlignmentSubtype::kConvex) {
        return convex(sequence, sequence_size, graph);
    }
    return Alignment();
}

Alignment SisdAlignmentEngine::linear(const char* sequence,
    std::uint32_t sequence_size, const std::unique_ptr<Graph>& graph) noexcept {

    std::uint32_t matrix_width = sequence_size + 1;
    std::uint32_t matrix_height = graph->nodes().size() + 1;
    const auto& rank_to_node_id = graph->rank_to_node_id();

    // realloc
    realloc(matrix_width, matrix_height, graph->num_codes());

    // initialize
    initialize(sequence, sequence_size, graph);

    std::int32_t max_score = type_ == AlignmentType::kSW ? 0 : kNegativeInfinity;
    std::int32_t max_i = -1;
    std::int32_t max_j = -1;
    auto update_max_score = [&max_score, &max_i, &max_j](std::int32_t* H_row,
        std::uint32_t i, std::uint32_t j) -> void {

        if (max_score < H_row[j]) {
            max_score = H_row[j];
            max_i = i;
            max_j = j;
        }
        return;
    };

    // alignment
    for (std::uint32_t node_id: rank_to_node_id) {
        const auto& node = graph->nodes()[node_id];
        const auto& char_profile =
            &(pimpl_->sequence_profile[node->code() * matrix_width]);

        std::uint32_t i = pimpl_->node_id_to_rank[node_id] + 1;

        std::int32_t* H_row = &(pimpl_->H[i * matrix_width]);

        std::uint32_t pred_i = node->in_edges().empty() ? 0 :
            pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

        std::int32_t* H_pred_row = &(pimpl_->H[pred_i * matrix_width]);

        for (std::uint32_t j = 1; j < matrix_width; ++j) {
            // update H
            H_row[j] = std::max(H_pred_row[j - 1] + char_profile[j],
                H_pred_row[j] + g_);
        }

        // check other predeccessors
        for (std::uint32_t p = 1; p < node->in_edges().size(); ++p) {
            pred_i = pimpl_->node_id_to_rank[node->in_edges()[p]->begin_node_id()] + 1;

            H_pred_row = &(pimpl_->H[pred_i * matrix_width]);

            for (std::uint32_t j = 1; j < matrix_width; ++j) {
                // update H
                H_row[j] = std::max(H_pred_row[j - 1] + char_profile[j],
                    std::max(H_row[j], H_pred_row[j] + g_));
            }
        }

        for (std::uint32_t j = 1; j < matrix_width; ++j) {
            // update H
            H_row[j] = std::max(H_row[j - 1] + g_, H_row[j]);

            if (type_ == AlignmentType::kSW) {
                H_row[j] = std::max(H_row[j], 0);
                update_max_score(H_row, i, j);

            } else if (type_ == AlignmentType::kNW &&
                (j == matrix_width - 1 && node->out_edges().empty())) {
                update_max_score(H_row, i, j);

            } else if (type_ == AlignmentType::kOV &&
                (node->out_edges().empty())) {
                update_max_score(H_row, i, j);
            }
        }
    }

    // backtrack
    Alignment alignment;

    std::uint32_t i = max_i;
    std::uint32_t j = max_j;

    auto sw_condition = [this, &i, &j, &matrix_width]() {
        return (pimpl_->H[i * matrix_width + j] == 0) ? false : true;
    };
    auto nw_condition = [&i, &j]() {
        return (i == 0 && j == 0) ? false : true;
    };
    auto ov_condition = [&i, &j]() {
        return (i == 0 || j == 0) ? false : true;
    };

    std::uint32_t prev_i = 0;
    std::uint32_t prev_j = 0;

    while ((type_ == AlignmentType::kSW && sw_condition()) ||
           (type_ == AlignmentType::kNW && nw_condition()) ||
           (type_ == AlignmentType::kOV && ov_condition())) {

        auto H_ij = pimpl_->H[i * matrix_width + j];
        bool predecessor_found = false;

        if (i != 0 && j != 0) {
            const auto& node = graph->nodes()[rank_to_node_id[i - 1]];
            std::int32_t match_cost =
                pimpl_->sequence_profile[node->code() * matrix_width + j];

            std::uint32_t pred_i = node->in_edges().empty() ? 0 :
                pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

            if (H_ij == pimpl_->H[pred_i * matrix_width + (j - 1)] + match_cost) {
                prev_i = pred_i;
                prev_j = j - 1;
                predecessor_found = true;
            } else {
                const auto& edges = node->in_edges();
                for (std::uint32_t p = 1; p < edges.size(); ++p) {
                    std::uint32_t pred_i =
                        pimpl_->node_id_to_rank[edges[p]->begin_node_id()] + 1;

                    if (H_ij == pimpl_->H[pred_i * matrix_width + (j - 1)] + match_cost) {
                        prev_i = pred_i;
                        prev_j = j - 1;
                        predecessor_found = true;
                        break;
                    }
                }
            }
        }

        if (!predecessor_found && i != 0) {
            const auto& node = graph->nodes()[rank_to_node_id[i - 1]];

            std::uint32_t pred_i = node->in_edges().empty() ? 0 :
                pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

            if (H_ij == pimpl_->H[pred_i * matrix_width + j] + g_) {
                prev_i = pred_i;
                prev_j = j;
                predecessor_found = true;
            } else {
                const auto& edges = node->in_edges();
                for (std::uint32_t p = 1; p < edges.size(); ++p) {
                    std::uint32_t pred_i =
                        pimpl_->node_id_to_rank[edges[p]->begin_node_id()] + 1;

                    if (H_ij == pimpl_->H[pred_i * matrix_width + j] + g_) {
                        prev_i = pred_i;
                        prev_j = j;
                        predecessor_found = true;
                        break;
                    }
                }
            }
        }

        if (!predecessor_found && H_ij == pimpl_->H[i * matrix_width + j - 1] + g_) {
            prev_i = i;
            prev_j = j - 1;
            predecessor_found = true;
        }

        alignment.emplace_back(i == prev_i ? -1 : rank_to_node_id[i - 1],
            j == prev_j ? -1 : j - 1);

        i = prev_i;
        j = prev_j;
    }

    std::reverse(alignment.begin(), alignment.end());
    return alignment;
}

Alignment SisdAlignmentEngine::affine(const char* sequence,
    std::uint32_t sequence_size, const std::unique_ptr<Graph>& graph) noexcept {

    std::uint32_t matrix_width = sequence_size + 1;
    std::uint32_t matrix_height = graph->nodes().size() + 1;
    const auto& rank_to_node_id = graph->rank_to_node_id();

    // realloc
    realloc(matrix_width, matrix_height, graph->num_codes());

    // initialize
    initialize(sequence, sequence_size, graph);

    std::int32_t max_score = type_ == AlignmentType::kSW ? 0 : kNegativeInfinity;
    std::int32_t max_i = -1;
    std::int32_t max_j = -1;
    auto update_max_score = [&max_score, &max_i, &max_j](std::int32_t* H_row,
        std::uint32_t i, std::uint32_t j) -> void {

        if (max_score < H_row[j]) {
            max_score = H_row[j];
            max_i = i;
            max_j = j;
        }
        return;
    };

    // alignment
    for (std::uint32_t node_id: rank_to_node_id) {
        const auto& node = graph->nodes()[node_id];
        const auto& char_profile =
            &(pimpl_->sequence_profile[node->code() * matrix_width]);

        std::uint32_t i = pimpl_->node_id_to_rank[node_id] + 1;

        std::int32_t* H_row = &(pimpl_->H[i * matrix_width]);
        std::int32_t* F_row = &(pimpl_->F[i * matrix_width]);

        std::uint32_t pred_i = node->in_edges().empty() ? 0 :
            pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

        std::int32_t* H_pred_row = &(pimpl_->H[pred_i * matrix_width]);
        std::int32_t* F_pred_row = &(pimpl_->F[pred_i * matrix_width]);

        for (std::uint32_t j = 1; j < matrix_width; ++j) {
            // update F
            F_row[j] = std::max(H_pred_row[j] + g_, F_pred_row[j] + e_);
            // update H
            H_row[j] = H_pred_row[j - 1] + char_profile[j];
        }

        // check other predeccessors
        for (std::uint32_t p = 1; p < node->in_edges().size(); ++p) {
            pred_i = pimpl_->node_id_to_rank[node->in_edges()[p]->begin_node_id()] + 1;

            H_pred_row = &(pimpl_->H[pred_i * matrix_width]);
            F_pred_row = &(pimpl_->F[pred_i * matrix_width]);

            for (std::uint32_t j = 1; j < matrix_width; ++j) {
                // update F
                F_row[j] = std::max(F_row[j], std::max(H_pred_row[j] + g_,
                    F_pred_row[j] + e_));
                // update H
                H_row[j] = std::max(H_row[j], H_pred_row[j - 1] + char_profile[j]);
            }
        }

        std::int32_t* E_row = &(pimpl_->E[i * matrix_width]);

        for (std::uint32_t j = 1; j < matrix_width; ++j) {
            // update E
            E_row[j] = std::max(H_row[j - 1] + g_, E_row[j - 1] + e_);
            // update H
            H_row[j] = std::max(H_row[j], std::max(F_row[j], E_row[j]));

            if (type_ == AlignmentType::kSW) {
                H_row[j] = std::max(H_row[j], 0);
                update_max_score(H_row, i, j);

            } else if (type_ == AlignmentType::kNW &&
                (j == matrix_width - 1 && node->out_edges().empty())) {
                update_max_score(H_row, i, j);

            } else if (type_ == AlignmentType::kOV &&
                (node->out_edges().empty())) {
                update_max_score(H_row, i, j);
            }
        }
    }

    // backtrack
    Alignment alignment;

    std::uint32_t i = max_i;
    std::uint32_t j = max_j;

    auto sw_condition = [this, &i, &j, &matrix_width]() {
        return (pimpl_->H[i * matrix_width + j] == 0) ? false : true;
    };
    auto nw_condition = [&i, &j]() {
        return (i == 0 && j == 0) ? false : true;
    };
    auto ov_condition = [&i, &j]() {
        return (i == 0 || j == 0) ? false : true;
    };

    std::uint32_t prev_i = 0;
    std::uint32_t prev_j = 0;

    while ((type_ == AlignmentType::kSW && sw_condition()) ||
           (type_ == AlignmentType::kNW && nw_condition()) ||
           (type_ == AlignmentType::kOV && ov_condition())) {

        auto H_ij = pimpl_->H[i * matrix_width + j];
        bool predecessor_found = false, extend_left = false, extend_up = false;

        if (i != 0 && j != 0) {
            const auto& node = graph->nodes()[rank_to_node_id[i - 1]];
            std::int32_t match_cost =
                pimpl_->sequence_profile[node->code() * matrix_width + j];

            std::uint32_t pred_i = node->in_edges().empty() ? 0 :
                pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

            if (H_ij == pimpl_->H[pred_i * matrix_width + (j - 1)] + match_cost) {
                prev_i = pred_i;
                prev_j = j - 1;
                predecessor_found = true;
            } else {
                const auto& edges = node->in_edges();
                for (std::uint32_t p = 1; p < edges.size(); ++p) {
                    pred_i = pimpl_->node_id_to_rank[edges[p]->begin_node_id()] + 1;

                    if (H_ij == pimpl_->H[pred_i * matrix_width + (j - 1)] + match_cost) {
                        prev_i = pred_i;
                        prev_j = j - 1;
                        predecessor_found = true;
                        break;
                    }
                }
            }
        }

        if (!predecessor_found && i != 0) {
            const auto& node = graph->nodes()[rank_to_node_id[i - 1]];

            std::uint32_t pred_i = node->in_edges().empty() ? 0 :
                pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

            if ((extend_up = H_ij == pimpl_->F[pred_i * matrix_width + j] + e_) ||
                             H_ij == pimpl_->H[pred_i * matrix_width + j] + g_) {
                prev_i = pred_i;
                prev_j = j;
                predecessor_found = true;
            } else {
                const auto& edges = node->in_edges();
                for (std::uint32_t p = 1; p < edges.size(); ++p) {
                    pred_i = pimpl_->node_id_to_rank[edges[p]->begin_node_id()] + 1;

                    if ((extend_up = H_ij == pimpl_->F[pred_i * matrix_width + j] + e_) ||
                                     H_ij == pimpl_->H[pred_i * matrix_width + j] + g_) {
                        prev_i = pred_i;
                        prev_j = j;
                        predecessor_found = true;
                        break;
                    }
                }
            }
        }

        if (!predecessor_found && j != 0) {
            if ((extend_left = H_ij == pimpl_->E[i * matrix_width + j - 1] + e_) ||
                               H_ij == pimpl_->H[i * matrix_width + j - 1] + g_) {
                prev_i = i;
                prev_j = j - 1;
                predecessor_found = true;
            }
        }

        alignment.emplace_back(i == prev_i ? -1 : rank_to_node_id[i - 1],
            j == prev_j ? -1 : j - 1);

        i = prev_i;
        j = prev_j;

        if (extend_left) {
            while (true) {
                alignment.emplace_back(-1, j - 1);
                --j;
                if (pimpl_->E[i * matrix_width + j] + e_ !=
                    pimpl_->E[i * matrix_width + j + 1]) {
                    break;
                }
            }
        } else if (extend_up) {
            while (true) {
                bool stop = false;
                prev_i = 0;
                for (const auto& it: graph->nodes()[rank_to_node_id[i - 1]]->in_edges()) {
                    std::uint32_t pred_i = pimpl_->node_id_to_rank[it->begin_node_id()] + 1;

                    if ((stop = pimpl_->F[i * matrix_width + j] == pimpl_->H[pred_i * matrix_width + j] + g_) ||
                                pimpl_->F[i * matrix_width + j] == pimpl_->F[pred_i * matrix_width + j] + e_) {
                        prev_i = pred_i;
                        break;
                    }
                }

                alignment.emplace_back(rank_to_node_id[i - 1], -1);
                i = prev_i;

                if (stop || i == 0) {
                    break;
                }
            }
        }
    }

    std::reverse(alignment.begin(), alignment.end());
    return alignment;
}

Alignment SisdAlignmentEngine::convex(const char* sequence,
    std::uint32_t sequence_size, const std::unique_ptr<Graph>& graph) noexcept {

    std::uint32_t matrix_width = sequence_size + 1;
    std::uint32_t matrix_height = graph->nodes().size() + 1;
    const auto& rank_to_node_id = graph->rank_to_node_id();

    // realloc
    realloc(matrix_width, matrix_height, graph->num_codes());

    // initialize
    initialize(sequence, sequence_size, graph);

    std::int32_t max_score = type_ == AlignmentType::kSW ? 0 : kNegativeInfinity;
    std::int32_t max_i = -1;
    std::int32_t max_j = -1;
    auto update_max_score = [&max_score, &max_i, &max_j](std::int32_t* H_row,
        std::uint32_t i, std::uint32_t j) -> void {

        if (max_score < H_row[j]) {
            max_score = H_row[j];
            max_i = i;
            max_j = j;
        }
        return;
    };

    // alignment
    for (std::uint32_t node_id: rank_to_node_id) {
        const auto& node = graph->nodes()[node_id];
        const auto& char_profile =
            &(pimpl_->sequence_profile[node->code() * matrix_width]);

        std::uint32_t i = pimpl_->node_id_to_rank[node_id] + 1;

        std::int32_t* H_row = &(pimpl_->H[i * matrix_width]);
        std::int32_t* F_row = &(pimpl_->F[i * matrix_width]);
        std::int32_t* O_row = &(pimpl_->O[i * matrix_width]);

        std::uint32_t pred_i = node->in_edges().empty() ? 0 :
            pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

        std::int32_t* H_pred_row = &(pimpl_->H[pred_i * matrix_width]);
        std::int32_t* F_pred_row = &(pimpl_->F[pred_i * matrix_width]);
        std::int32_t* O_pred_row = &(pimpl_->O[pred_i * matrix_width]);

        for (std::uint32_t j = 1; j < matrix_width; ++j) {
            // update F
            F_row[j] = std::max(H_pred_row[j] + g_, F_pred_row[j] + e_);
            // update O
            O_row[j] = std::max(H_pred_row[j] + q_, O_pred_row[j] + c_);
            // update H
            H_row[j] = H_pred_row[j - 1] + char_profile[j];
        }

        // check other predeccessors
        for (std::uint32_t p = 1; p < node->in_edges().size(); ++p) {
            pred_i = pimpl_->node_id_to_rank[node->in_edges()[p]->begin_node_id()] + 1;

            H_pred_row = &(pimpl_->H[pred_i * matrix_width]);
            F_pred_row = &(pimpl_->F[pred_i * matrix_width]);
            O_pred_row = &(pimpl_->O[pred_i * matrix_width]);

            for (std::uint32_t j = 1; j < matrix_width; ++j) {
                // update F
                F_row[j] = std::max(F_row[j], std::max(H_pred_row[j] + g_,
                    F_pred_row[j] + e_));
                // update O
                O_row[j] = std::max(O_row[j], std::max(H_pred_row[j] + q_,
                    O_pred_row[j] + c_));
                // update H
                H_row[j] = std::max(H_row[j], H_pred_row[j - 1] + char_profile[j]);
            }
        }

        std::int32_t* E_row = &(pimpl_->E[i * matrix_width]);
        std::int32_t* Q_row = &(pimpl_->Q[i * matrix_width]);

        for (std::uint32_t j = 1; j < matrix_width; ++j) {
            // update E
            E_row[j] = std::max(H_row[j - 1] + g_, E_row[j - 1] + e_);
            // update Q
            Q_row[j] = std::max(H_row[j - 1] + q_, Q_row[j - 1] + c_);
            // update H
            H_row[j] = std::max(H_row[j], std::max(
                std::max(F_row[j], E_row[j]),
                std::max(O_row[j], Q_row[j])));

            if (type_ == AlignmentType::kSW) {
                H_row[j] = std::max(H_row[j], 0);
                update_max_score(H_row, i, j);

            } else if (type_ == AlignmentType::kNW &&
                (j == matrix_width - 1 && node->out_edges().empty())) {
                update_max_score(H_row, i, j);

            } else if (type_ == AlignmentType::kOV &&
                (node->out_edges().empty())) {
                update_max_score(H_row, i, j);
            }
        }
    }

    // backtrack
    Alignment alignment;

    std::uint32_t i = max_i;
    std::uint32_t j = max_j;

    auto sw_condition = [this, &i, &j, &matrix_width]() {
        return (pimpl_->H[i * matrix_width + j] == 0) ? false : true;
    };
    auto nw_condition = [&i, &j]() {
        return (i == 0 && j == 0) ? false : true;
    };
    auto ov_condition = [&i, &j]() {
        return (i == 0 || j == 0) ? false : true;
    };

    std::uint32_t prev_i = 0;
    std::uint32_t prev_j = 0;

    while ((type_ == AlignmentType::kSW && sw_condition()) ||
           (type_ == AlignmentType::kNW && nw_condition()) ||
           (type_ == AlignmentType::kOV && ov_condition())) {

        auto H_ij = pimpl_->H[i * matrix_width + j];
        bool predecessor_found = false, extend_left = false, extend_up = false;

        if (i != 0 && j != 0) {
            const auto& node = graph->nodes()[rank_to_node_id[i - 1]];
            std::int32_t match_cost =
                pimpl_->sequence_profile[node->code() * matrix_width + j];

            std::uint32_t pred_i = node->in_edges().empty() ? 0 :
                pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

            if (H_ij == pimpl_->H[pred_i * matrix_width + (j - 1)] + match_cost) {
                prev_i = pred_i;
                prev_j = j - 1;
                predecessor_found = true;
            } else {
                const auto& edges = node->in_edges();
                for (std::uint32_t p = 1; p < edges.size(); ++p) {
                    pred_i = pimpl_->node_id_to_rank[edges[p]->begin_node_id()] + 1;

                    if (H_ij == pimpl_->H[pred_i * matrix_width + (j - 1)] + match_cost) {
                        prev_i = pred_i;
                        prev_j = j - 1;
                        predecessor_found = true;
                        break;
                    }
                }
            }
        }

        if (!predecessor_found && i != 0) {
            const auto& node = graph->nodes()[rank_to_node_id[i - 1]];

            std::uint32_t pred_i = node->in_edges().empty() ? 0 :
                pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

            if ((extend_up |= H_ij == pimpl_->F[pred_i * matrix_width + j] + e_) ||
                              H_ij == pimpl_->H[pred_i * matrix_width + j] + g_  ||
                (extend_up |= H_ij == pimpl_->O[pred_i * matrix_width + j] + c_) ||
                              H_ij == pimpl_->H[pred_i * matrix_width + j] + q_) {
                prev_i = pred_i;
                prev_j = j;
                predecessor_found = true;
            } else {
                const auto& edges = node->in_edges();
                for (std::uint32_t p = 1; p < edges.size(); ++p) {
                    pred_i = pimpl_->node_id_to_rank[edges[p]->begin_node_id()] + 1;

                    if ((extend_up |= H_ij == pimpl_->F[pred_i * matrix_width + j] + e_) ||
                                      H_ij == pimpl_->H[pred_i * matrix_width + j] + g_  ||
                        (extend_up |= H_ij == pimpl_->O[pred_i * matrix_width + j] + c_) ||
                                      H_ij == pimpl_->H[pred_i * matrix_width + j] + q_) {
                        prev_i = pred_i;
                        prev_j = j;
                        predecessor_found = true;
                        break;
                    }
                }
            }
        }

        if (!predecessor_found && j != 0) {
            if ((extend_left |= H_ij == pimpl_->E[i * matrix_width + j - 1] + e_) ||
                                H_ij == pimpl_->H[i * matrix_width + j - 1] + g_  ||
                (extend_left |= H_ij == pimpl_->Q[i * matrix_width + j - 1] + c_) ||
                                H_ij == pimpl_->H[i * matrix_width + j - 1] + q_) {
                prev_i = i;
                prev_j = j - 1;
                predecessor_found = true;
            }
        }

        alignment.emplace_back(i == prev_i ? -1 : rank_to_node_id[i - 1],
            j == prev_j ? -1 : j - 1);

        i = prev_i;
        j = prev_j;

        if (extend_left) {
            while (true) {
                alignment.emplace_back(-1, j - 1);
                --j;
                if (pimpl_->E[i * matrix_width + j] + e_ != pimpl_->E[i * matrix_width + j + 1] &&
                    pimpl_->Q[i * matrix_width + j] + c_ != pimpl_->Q[i * matrix_width + j + 1]) {
                    break;
                }
            }
        } else if (extend_up) {
            while (true) {
                bool stop = true;
                prev_i = 0;
                for (const auto& it: graph->nodes()[rank_to_node_id[i - 1]]->in_edges()) {
                    std::uint32_t pred_i = pimpl_->node_id_to_rank[it->begin_node_id()] + 1;

                    if (pimpl_->F[i * matrix_width + j] == pimpl_->F[pred_i * matrix_width + j] + e_ ||
                        pimpl_->O[i * matrix_width + j] == pimpl_->O[pred_i * matrix_width + j] + c_) {
                        prev_i = pred_i;
                        stop = false;
                        break;
                    }
                }
                if (stop == true) {
                    for (const auto& it: graph->nodes()[rank_to_node_id[i - 1]]->in_edges()) {
                        std::uint32_t pred_i = pimpl_->node_id_to_rank[it->begin_node_id()] + 1;

                        if (pimpl_->F[i * matrix_width + j] == pimpl_->H[pred_i * matrix_width + j] + g_ ||
                            pimpl_->O[i * matrix_width + j] == pimpl_->H[pred_i * matrix_width + j] + q_) {
                            prev_i = pred_i;
                            break;
                        }
                    }
                }

                alignment.emplace_back(rank_to_node_id[i - 1], -1);
                i = prev_i;

                if (stop || i == 0) {
                    break;
                }
            }
        }
    }

    std::reverse(alignment.begin(), alignment.end());
    return alignment;
}

}

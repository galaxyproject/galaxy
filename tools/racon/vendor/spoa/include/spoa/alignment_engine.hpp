/*!
 * @file alignment_engine.hpp
 *
 * @brief AlignmentEngine class header file
 */

#pragma once

#include <cstdint>
#include <string>
#include <memory>
#include <vector>
#include <utility>

namespace spoa {

enum class AlignmentType {
    kSW, // Smith Waterman
    kNW, // Needleman Wunsch
    kOV // Overlap
};

enum class AlignmentSubtype {
    kLinear,
    kAffine,
    kConvex
};

class Graph;
using Alignment = std::vector<std::pair<std::int32_t, std::int32_t>>;

class AlignmentEngine;
std::unique_ptr<AlignmentEngine> createAlignmentEngine(AlignmentType type,
    std::int8_t m, std::int8_t n, std::int8_t g);

std::unique_ptr<AlignmentEngine> createAlignmentEngine(AlignmentType type,
    std::int8_t m, std::int8_t n, std::int8_t g, std::int8_t e);

std::unique_ptr<AlignmentEngine> createAlignmentEngine(AlignmentType type,
    std::int8_t m, std::int8_t n, std::int8_t g, std::int8_t e,
    std::int8_t q, std::int8_t c);

class AlignmentEngine {
public:
    virtual ~AlignmentEngine() {}

    virtual void prealloc(std::uint32_t max_sequence_size,
        std::uint32_t alphabet_size) = 0;

    Alignment align(const std::string& sequence,
        const std::unique_ptr<Graph>& graph);

    virtual Alignment align(const char* sequence, std::uint32_t sequence_size,
        const std::unique_ptr<Graph>& graph) noexcept = 0;

protected:
    AlignmentEngine(AlignmentType type, AlignmentSubtype subtype, std::int8_t m,
        std::int8_t n, std::int8_t g, std::int8_t e, std::int8_t q,
        std::int8_t c);
    AlignmentEngine(const AlignmentEngine&) = delete;
    const AlignmentEngine& operator=(const AlignmentEngine&) = delete;

    AlignmentType type_;
    AlignmentSubtype subtype_;
    std::int8_t m_;
    std::int8_t n_;
    std::int8_t g_;
    std::int8_t e_;
    std::int8_t q_;
    std::int8_t c_;
};

}

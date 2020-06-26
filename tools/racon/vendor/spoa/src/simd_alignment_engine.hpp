/*!
 * @file simd_alignment_engine.hpp
 *
 * @brief SimdAlignmentEngine class header file
 */

#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "spoa/alignment_engine.hpp"

namespace spoa {

class Graph;

class SimdAlignmentEngine;
std::unique_ptr<AlignmentEngine> createSimdAlignmentEngine(AlignmentType type,
    AlignmentSubtype subtype, std::int8_t m, std::int8_t n, std::int8_t g,
    std::int8_t e, std::int8_t q, std::int8_t c);

class SimdAlignmentEngine: public AlignmentEngine {
public:
    ~SimdAlignmentEngine();

    void prealloc(std::uint32_t max_sequence_size,
        std::uint32_t alphabet_size) override;

    Alignment align(const char* sequence, std::uint32_t sequence_size,
        const std::unique_ptr<Graph>& graph) noexcept override;

    friend std::unique_ptr<AlignmentEngine> createSimdAlignmentEngine(
        AlignmentType type, AlignmentSubtype subtype, std::int8_t m,
        std::int8_t n, std::int8_t g, std::int8_t e, std::int8_t q,
        std::int8_t c);

private:
    SimdAlignmentEngine(AlignmentType type, AlignmentSubtype subtype,
        std::int8_t m, std::int8_t n, std::int8_t g, std::int8_t e,
        std::int8_t q, std::int8_t c);
    SimdAlignmentEngine(const SimdAlignmentEngine&) = delete;
    const SimdAlignmentEngine& operator=(const SimdAlignmentEngine&) = delete;

    template<typename T>
    Alignment linear(const char* sequence, std::uint32_t sequence_size,
        const std::unique_ptr<Graph>& graph) noexcept;

    template<typename T>
    Alignment affine(const char* sequence, std::uint32_t sequence_size,
        const std::unique_ptr<Graph>& graph) noexcept;

    template<typename T>
    Alignment convex(const char* sequence, std::uint32_t sequence_size,
        const std::unique_ptr<Graph>& graph) noexcept;

    void realloc(std::uint32_t matrix_width, std::uint32_t matrix_height,
        std::uint32_t num_codes);

    template<typename T>
    void initialize(const char* sequence, const std::unique_ptr<Graph>& graph,
        std::uint32_t normal_matrix_width, std::uint32_t matrix_width,
        std::uint32_t matrix_height) noexcept;

    struct Implementation;
    std::unique_ptr<Implementation> pimpl_;
};

}

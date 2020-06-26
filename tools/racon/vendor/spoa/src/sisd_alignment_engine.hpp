/*!
 * @file sisd_alignment_engine.hpp
 *
 * @brief SisdAlignmentEngine class header file
 */

#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "spoa/alignment_engine.hpp"

namespace spoa {

class Graph;

class SisdAlignmentEngine;
std::unique_ptr<AlignmentEngine> createSisdAlignmentEngine(AlignmentType type,
    AlignmentSubtype subtype, std::int8_t m, std::int8_t n, std::int8_t g,
    std::int8_t e, std::int8_t q, std::int8_t c);

class SisdAlignmentEngine: public AlignmentEngine {
public:
    ~SisdAlignmentEngine();

    void prealloc(std::uint32_t max_sequence_size,
        std::uint32_t alphabet_size) override;

    Alignment align(const char* sequence, std::uint32_t sequence_size,
        const std::unique_ptr<Graph>& graph) noexcept override;

    friend std::unique_ptr<AlignmentEngine> createSisdAlignmentEngine(
        AlignmentType type, AlignmentSubtype subtype, std::int8_t m,
        std::int8_t n, std::int8_t g, std::int8_t e, std::int8_t c,
        std::int8_t q);

private:
    SisdAlignmentEngine(AlignmentType type, AlignmentSubtype subtype,
        std::int8_t m, std::int8_t n, std::int8_t g, std::int8_t e,
        std::int8_t q, std::int8_t c);
    SisdAlignmentEngine(const SisdAlignmentEngine&) = delete;
    const SisdAlignmentEngine& operator=(const SisdAlignmentEngine&) = delete;

    Alignment linear(const char* sequence, std::uint32_t sequence_size,
        const std::unique_ptr<Graph>& graph) noexcept;

    Alignment affine(const char* sequence, std::uint32_t sequence_size,
        const std::unique_ptr<Graph>& graph) noexcept;

    Alignment convex(const char* sequence, std::uint32_t sequence_size,
        const std::unique_ptr<Graph>& graph) noexcept;

    void realloc(std::uint32_t matrix_width, std::uint32_t matrix_height,
        std::uint32_t num_codes);

    void initialize(const char* sequence, std::uint32_t sequence_size,
        const std::unique_ptr<Graph>& graph) noexcept;

    struct Implementation;
    std::unique_ptr<Implementation> pimpl_;
};

}

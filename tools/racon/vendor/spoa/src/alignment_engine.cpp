/*!
 * @file alignment_engine.cpp
 *
 * @brief AlignmentEngine class source file
 */

#include <limits>
#include <algorithm>
#include <exception>

#include "sisd_alignment_engine.hpp"
#include "simd_alignment_engine.hpp"
#include "spoa/alignment_engine.hpp"

namespace spoa {

std::unique_ptr<AlignmentEngine> createAlignmentEngine(AlignmentType type,
    std::int8_t m, std::int8_t n, std::int8_t g) {

    return createAlignmentEngine(type, m, n, g, g);
}

std::unique_ptr<AlignmentEngine> createAlignmentEngine(AlignmentType type,
    std::int8_t m, std::int8_t n, std::int8_t g, std::int8_t e) {

    return createAlignmentEngine(type, m, n, g, e, g, e);
}

std::unique_ptr<AlignmentEngine> createAlignmentEngine(AlignmentType type,
    std::int8_t m, std::int8_t n, std::int8_t g, std::int8_t e,
    std::int8_t q, std::int8_t c) {

    if (type != AlignmentType::kSW &&
        type != AlignmentType::kNW &&
        type != AlignmentType::kOV) {

        throw std::invalid_argument("[spoa::createAlignmentEngine] error: "
            "invalid alignment type!");
    }
    if (g > 0 || q > 0) {
        throw std::invalid_argument("[spoa::createAlignmentEngine] error: "
            "gap opening penalty must be non-positive!");
    }
    if (e > 0 || c > 0) {
        throw std::invalid_argument("[spoa::createAlignmentEngine] error: "
            "gap extension penalty must be non-positive!");
    }

    AlignmentSubtype subtype = g >= e ?
        AlignmentSubtype::kLinear : (g <= q || e >= c ?
        AlignmentSubtype::kAffine : AlignmentSubtype::kConvex);

    if (subtype == AlignmentSubtype::kLinear) {
        e = g;
    } else if (subtype == AlignmentSubtype::kAffine) {
        q = g;
        c = e;
    }

    auto alignment_engine = createSimdAlignmentEngine(type, subtype, m, n, g, e,
        q, c);

    if (alignment_engine == nullptr) {
        return createSisdAlignmentEngine(type, subtype, m, n, g, e, q, c);
    }

    return alignment_engine;
}

AlignmentEngine::AlignmentEngine(AlignmentType type, AlignmentSubtype subtype,
    std::int8_t m, std::int8_t n, std::int8_t g, std::int8_t e,
    std::int8_t q, std::int8_t c)
        : type_(type), subtype_(subtype), m_(m), n_(n), g_(g), e_(e), q_(q), c_(c) {
}

Alignment AlignmentEngine::align(const std::string& sequence,
    const std::unique_ptr<Graph>& graph) {

    return align(sequence.c_str(), sequence.size(), graph);
}

}

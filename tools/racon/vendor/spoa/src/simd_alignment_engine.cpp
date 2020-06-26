/*!
 * @file simd_alignment_engine.cpp
 *
 * @brief SimdAlignmentEngine class source file
 */

#include <iostream>
#include <algorithm>
#include <limits>

extern "C" {
    #include <immintrin.h> // AVX2 and lower
}

#include "spoa/graph.hpp"
#include "simd_alignment_engine.hpp"

namespace spoa {

// Taken from https://gcc.gnu.org/viewcvs/gcc?view=revision&revision=216149
inline void* align(std::size_t __align, std::size_t __size, void*& __ptr,
    std::size_t& __space) noexcept {

    const auto __intptr = reinterpret_cast<uintptr_t>(__ptr);
    const auto __aligned = (__intptr - 1u + __align) & -__align;
    const auto __diff = __aligned - __intptr;
    if ((__size + __diff) > __space)
        return nullptr;
    else {
        __space -= __diff;
        return __ptr = reinterpret_cast<void*>(__aligned);
    }
}

template<typename T>
T* allocateAlignedMemory(T** storage, std::uint32_t size, std::uint32_t alignment) {
    *storage = new T[size + alignment - 1];
    void* ptr = static_cast<void*>(*storage);
    std::size_t storage_size = (size + alignment - 1) * sizeof(T);
    return static_cast<T*>(align(alignment, size * sizeof(T), ptr, storage_size));
}

template<typename T>
struct InstructionSet;

#if defined(__AVX2__)

constexpr std::uint32_t kRegisterSize = 256;
using __mxxxi = __m256i;

inline __mxxxi _mmxxx_load_si(__mxxxi const* mem_addr) {
    return _mm256_load_si256(mem_addr);
}

inline void _mmxxx_store_si(__mxxxi* mem_addr, const __mxxxi& a) {
    _mm256_store_si256(mem_addr, a);
}

inline __mxxxi _mmxxx_or_si(const __mxxxi& a, const __mxxxi& b) {
    return _mm256_or_si256(a, b);
}

#define _mmxxx_slli_si(a, n) n < 16 ? \
    _mm256_alignr_epi8(a, _mm256_permute2x128_si256(a, a, \
        _MM_SHUFFLE(0, 0, 2, 0)), 16 - n) : \
    _mm256_permute2x128_si256(a, a, _MM_SHUFFLE(0, 0, 2, 0))

#define _mmxxx_srli_si(a, n) \
    _mm256_srli_si256(_mm256_permute2x128_si256(a, a, \
        _MM_SHUFFLE(2, 0, 0, 1)), n - 16)

template<>
struct InstructionSet<std::int16_t> {
    using type = std::int16_t;
    static constexpr std::uint32_t kNumVar = kRegisterSize / (8 * sizeof(type));
    static constexpr std::uint32_t kLogNumVar = 4;
    static constexpr std::uint32_t kLSS = 2; // Left Shift Size
    static constexpr std::uint32_t kRSS = 30; // Right Shift Size
    static inline __mxxxi _mmxxx_add_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm256_add_epi16(a, b);
    }
    static inline __mxxxi _mmxxx_sub_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm256_sub_epi16(a, b);
    }
    static inline __mxxxi _mmxxx_min_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm256_min_epi16(a, b);
    }
    static inline __mxxxi _mmxxx_max_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm256_max_epi16(a, b);
    }
    static inline __mxxxi _mmxxx_set1_epi(type a) {
        return _mm256_set1_epi16(a);
    }
    static inline void _mmxxx_prefix_max(__mxxxi& a, const __mxxxi* masks,
        const __mxxxi* penalties) {

        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[0], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[0]), 2)));
        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[1], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[1]), 4)));
        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[2], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[2]), 8)));
        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[3], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[3]), 16)));
    }
};

template<>
struct InstructionSet<std::int32_t> {
    using type = std::int32_t;
    static constexpr std::uint32_t kNumVar = kRegisterSize / (8 * sizeof(type));
    static constexpr std::uint32_t kLogNumVar = 3;
    static constexpr std::uint32_t kLSS = 4;
    static constexpr std::uint32_t kRSS = 28;
    static inline __mxxxi _mmxxx_add_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm256_add_epi32(a, b);
    }
    static inline __mxxxi _mmxxx_sub_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm256_sub_epi32(a, b);
    }
    static inline __mxxxi _mmxxx_min_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm256_min_epi32(a, b);
    }
    static inline __mxxxi _mmxxx_max_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm256_max_epi32(a, b);
    }
    static inline __mxxxi _mmxxx_set1_epi(type a) {
        return _mm256_set1_epi32(a);
    }
    static inline void _mmxxx_prefix_max(__mxxxi& a, const __mxxxi* masks,
        const __mxxxi* penalties) {

        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[0], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[0]), 4)));
        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[1], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[1]), 8)));
        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[2], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[2]), 16)));
    }
};

#elif defined(__SSE4_1__)

constexpr std::uint32_t kRegisterSize = 128;
using __mxxxi = __m128i;

inline __mxxxi _mmxxx_load_si(__mxxxi const* mem_addr) {
    return _mm_load_si128(mem_addr);
}

inline void _mmxxx_store_si(__mxxxi* mem_addr, const __mxxxi& a) {
    _mm_store_si128(mem_addr, a);
}

inline __mxxxi _mmxxx_or_si(const __mxxxi& a, const __mxxxi& b) {
    return _mm_or_si128(a, b);
}

#define _mmxxx_slli_si(a, n) \
    _mm_slli_si128(a, n)

#define _mmxxx_srli_si(a, n) \
    _mm_srli_si128(a, n)

template<>
struct InstructionSet<std::int16_t> {
    using type = std::int16_t;
    static constexpr std::uint32_t kNumVar = kRegisterSize / (8 * sizeof(type));
    static constexpr std::uint32_t kLogNumVar = 3;
    static constexpr std::uint32_t kLSS = 2;
    static constexpr std::uint32_t kRSS = 14;
    static inline __mxxxi _mmxxx_add_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm_add_epi16(a, b);
    }
    static inline __mxxxi _mmxxx_sub_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm_sub_epi16(a, b);
    }
    static inline __mxxxi _mmxxx_min_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm_min_epi16(a, b);
    }
    static inline __mxxxi _mmxxx_max_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm_max_epi16(a, b);
    }
    static inline __mxxxi _mmxxx_set1_epi(type a) {
        return _mm_set1_epi16(a);
    }
    static inline void _mmxxx_prefix_max(__mxxxi& a, const __mxxxi* masks,
        const __mxxxi* penalties) {

        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[0], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[0]), 2)));
        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[1], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[1]), 4)));
        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[2], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[2]), 8)));
    }
};

template<>
struct InstructionSet<std::int32_t> {
    using type = std::int32_t;
    static constexpr std::uint32_t kNumVar = kRegisterSize / (8 * sizeof(type));
    static constexpr std::uint32_t kLogNumVar = 2;
    static constexpr std::uint32_t kLSS = 4;
    static constexpr std::uint32_t kRSS = 12;
    static inline __mxxxi _mmxxx_add_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm_add_epi32(a, b);
    }
    static inline __mxxxi _mmxxx_sub_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm_sub_epi32(a, b);
    }
    static inline __mxxxi _mmxxx_min_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm_min_epi32(a, b);
    }
    static inline __mxxxi _mmxxx_max_epi(const __mxxxi& a, const __mxxxi& b) {
        return _mm_max_epi32(a, b);
    }
    static inline __mxxxi _mmxxx_set1_epi(type a) {
        return _mm_set1_epi32(a);
    }
    static inline void _mmxxx_prefix_max(__mxxxi& a, const __mxxxi* masks,
        const __mxxxi* penalties) {

        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[0], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[0]), 4)));
        a = _mmxxx_max_epi(a, _mmxxx_or_si(masks[1], _mmxxx_slli_si(
            _mmxxx_add_epi(a, penalties[1]), 8)));
    }
};

#endif

#if defined(__AVX2__) || defined(__SSE4_1__)

template<typename T>
void _mmxxx_print(const __mxxxi& a) {

    __attribute__((aligned(kRegisterSize / 8))) typename T::type
        unpacked[T::kNumVar];
    _mmxxx_store_si(reinterpret_cast<__mxxxi*>(unpacked), a);

    for (std::uint32_t i = 0; i < T::kNumVar; i++) {
        std::cout << unpacked[i] << " ";
    }
}

template<typename T>
typename T::type _mmxxx_max_value(const __mxxxi& a) {

    typename T::type max_score = 0;
    __attribute__((aligned(kRegisterSize / 8))) typename T::type
        unpacked[T::kNumVar];
    _mmxxx_store_si(reinterpret_cast<__mxxxi*>(unpacked), a);

    for (std::uint32_t i = 0; i < T::kNumVar; i++) {
        max_score = std::max(max_score, unpacked[i]);
    }

    return max_score;
}

template<typename T>
typename T::type _mmxxx_value_at(const __mxxxi& a, std::uint32_t i) {

    __attribute__((aligned(kRegisterSize / 8))) typename T::type
        unpacked[T::kNumVar];
    _mmxxx_store_si(reinterpret_cast<__mxxxi*>(unpacked), a);

    return unpacked[i];
}

template<typename T>
std::int32_t _mmxxx_index_of(const __mxxxi* row, std::uint32_t row_width,
    typename T::type value) {

    for (std::uint32_t i = 0; i < row_width; ++i) {
        __attribute__((aligned(kRegisterSize / 8))) typename T::type
            unpacked[T::kNumVar];
        _mmxxx_store_si(reinterpret_cast<__mxxxi*>(unpacked), row[i]);

        for (std::uint32_t j = 0; j < T::kNumVar; j++) {
            if (unpacked[j] == value) {
                return i * T::kNumVar + j;
            }
        }
    }

    return -1;
}

#endif

std::unique_ptr<AlignmentEngine> createSimdAlignmentEngine(AlignmentType type,
    AlignmentSubtype subtype, std::int8_t m, std::int8_t n, std::int8_t g,
    std::int8_t e, std::int8_t q, std::int8_t c) {

#if defined(__AVX2__) || defined(__SSE4_1__)

    return std::unique_ptr<AlignmentEngine>(new SimdAlignmentEngine(type,
        subtype, m, n, g, e, q, c));

#else

    return nullptr;

#endif
}

struct SimdAlignmentEngine::Implementation {

#if defined(__AVX2__) || defined(__SSE4_1__)

    std::vector<std::uint32_t> node_id_to_rank;

    std::unique_ptr<__mxxxi[]> sequence_profile_storage;
    std::uint32_t sequence_profile_size;
    __mxxxi* sequence_profile;

    std::vector<std::int32_t> first_column;
    std::unique_ptr<__mxxxi[]> M_storage;
    std::uint32_t M_size;
    __mxxxi* H;
    __mxxxi* F;
    __mxxxi* E;
    __mxxxi* O;
    __mxxxi* Q;

    std::unique_ptr<__mxxxi[]> masks_storage;
    std::uint32_t masks_size;
    __mxxxi* masks;

    std::unique_ptr<__mxxxi[]> penalties_storage;
    std::uint32_t penalties_size;
    __mxxxi* penalties;

    Implementation()
            : node_id_to_rank(), sequence_profile_storage(nullptr),
            sequence_profile_size(0), sequence_profile(nullptr), first_column(),
            M_storage(nullptr), M_size(0), H(nullptr), F(nullptr), E(nullptr),
            O(nullptr), Q(nullptr), masks_storage(nullptr), masks_size(0),
            masks(nullptr), penalties_storage(nullptr), penalties_size(0),
            penalties(nullptr) {
    }

#endif
};

SimdAlignmentEngine::SimdAlignmentEngine(AlignmentType type,
    AlignmentSubtype subtype, std::int8_t m, std::int8_t n, std::int8_t g,
    std::int8_t e, std::int8_t q, std::int8_t c)
        : AlignmentEngine(type, subtype, m, n, g, e, q, c),
        pimpl_(new Implementation()) {
}

SimdAlignmentEngine::~SimdAlignmentEngine() {
}

void SimdAlignmentEngine::prealloc(std::uint32_t max_sequence_size,
    std::uint32_t alphabet_size) {

#if defined(__AVX2__) || defined(__SSE4_1__)

    std::uint32_t longest_path = max_sequence_size * (alphabet_size + 1) + 1 +
        InstructionSet<std::int16_t>::kNumVar;

    std::uint32_t max_penalty = std::max(std::max(abs(m_), abs(n_)),
        std::max(abs(g_), abs(q_)));

    if (max_penalty * longest_path < std::numeric_limits<std::int16_t>::max()) {
        realloc((max_sequence_size / InstructionSet<std::int16_t>::kNumVar) + 1,
            alphabet_size * max_sequence_size, alphabet_size);
    } else {
        realloc((max_sequence_size / InstructionSet<std::int32_t>::kNumVar) + 1,
            alphabet_size * max_sequence_size, alphabet_size);
    }

#endif
}

void SimdAlignmentEngine::realloc(std::uint32_t matrix_width,
    std::uint32_t matrix_height, std::uint32_t num_codes) {

#if defined(__AVX2__) || defined(__SSE4_1__)

    if (pimpl_->node_id_to_rank.size() < matrix_height - 1) {
        pimpl_->node_id_to_rank.resize(matrix_height - 1, 0);
    }
    if (pimpl_->sequence_profile_size < num_codes * matrix_width) {
        __mxxxi* storage = nullptr;
        pimpl_->sequence_profile_size = num_codes * matrix_width;
        pimpl_->sequence_profile = allocateAlignedMemory(&storage,
            pimpl_->sequence_profile_size, kRegisterSize / 8);
        pimpl_->sequence_profile_storage.reset();
        pimpl_->sequence_profile_storage = std::unique_ptr<__mxxxi[]>(storage);
    }
    if (subtype_ == AlignmentSubtype::kLinear) {
        if (pimpl_->first_column.size() < matrix_height) {
            pimpl_->first_column.resize(matrix_height, 0);
        }
        if (pimpl_->M_size < matrix_height * matrix_width) {
            __mxxxi* storage = nullptr;
            pimpl_->M_size = matrix_height * matrix_width;
            pimpl_->H = allocateAlignedMemory(&storage, pimpl_->M_size,
                kRegisterSize / 8);
            pimpl_->M_storage.reset();
            pimpl_->M_storage = std::unique_ptr<__mxxxi[]>(storage);
        }
    } else if (subtype_ == AlignmentSubtype::kAffine) {
        if (pimpl_->first_column.size() < 2 * matrix_height) {
            pimpl_->first_column.resize(2 * matrix_height, 0);
        }
        if (pimpl_->M_size < 3 * matrix_height * matrix_width) {
            __mxxxi* storage = nullptr;
            pimpl_->M_size = 3 * matrix_height * matrix_width;
            pimpl_->H = allocateAlignedMemory(&storage, pimpl_->M_size,
                kRegisterSize / 8);
            pimpl_->F = pimpl_->H + matrix_height * matrix_width;
            pimpl_->E = pimpl_->F + matrix_height * matrix_width;
            pimpl_->M_storage.reset();
            pimpl_->M_storage = std::unique_ptr<__mxxxi[]>(storage);
        }
    } else if (subtype_ == AlignmentSubtype::kConvex) {
        if (pimpl_->first_column.size() < 3 * matrix_height) {
            pimpl_->first_column.resize(3 * matrix_height, 0);
        }
        if (pimpl_->M_size < 5 * matrix_height * matrix_width) {
            __mxxxi* storage = nullptr;
            pimpl_->M_size = 5 * matrix_height * matrix_width;
            pimpl_->H = allocateAlignedMemory(&storage, pimpl_->M_size,
                kRegisterSize / 8);
            pimpl_->F = pimpl_->H + matrix_height * matrix_width;
            pimpl_->E = pimpl_->F + matrix_height * matrix_width;
            pimpl_->O = pimpl_->E + matrix_height * matrix_width;
            pimpl_->Q = pimpl_->O + matrix_height * matrix_width;
            pimpl_->M_storage.reset();
            pimpl_->M_storage = std::unique_ptr<__mxxxi[]>(storage);
        }
    }
    if (pimpl_->masks_size < InstructionSet<std::int16_t>::kLogNumVar + 1) {
        __mxxxi* storage = nullptr;
        pimpl_->masks_size = InstructionSet<std::int16_t>::kLogNumVar + 1;
        pimpl_->masks = allocateAlignedMemory(&storage,
            pimpl_->masks_size, kRegisterSize / 8);
        pimpl_->masks_storage.reset();
        pimpl_->masks_storage = std::unique_ptr<__mxxxi[]>(storage);
    }
    if (pimpl_->penalties_size < 2 * InstructionSet<std::int16_t>::kLogNumVar) {
        __mxxxi* storage = nullptr;
        pimpl_->penalties_size = 2 * InstructionSet<std::int16_t>::kLogNumVar;
        pimpl_->penalties = allocateAlignedMemory(&storage,
            pimpl_->penalties_size, kRegisterSize / 8);
        pimpl_->penalties_storage.reset();
        pimpl_->penalties_storage = std::unique_ptr<__mxxxi[]>(storage);
    }

#endif
}

template<typename T>
void SimdAlignmentEngine::initialize(const char* sequence,
    const std::unique_ptr<Graph>& graph, std::uint32_t normal_matrix_width,
    std::uint32_t matrix_width, std::uint32_t matrix_height) noexcept {

#if defined(__AVX2__) || defined(__SSE4_1__)

    std::int32_t padding_penatly = -1 * std::max(std::max(abs(m_), abs(n_)),
        std::max(abs(g_), abs(q_)));

    __attribute__((aligned(kRegisterSize / 8))) typename T::type
        unpacked[T::kNumVar] = {};

    for (std::uint32_t i = 0; i < graph->num_codes(); ++i) {
        char c = graph->decoder(i);
        for (std::uint32_t j = 0; j < matrix_width; ++j) {
            for (std::uint32_t k = 0; k < T::kNumVar; ++k) {
                unpacked[k] = (j * T::kNumVar + k) < normal_matrix_width ?
                    (c == sequence[j * T::kNumVar + k] ? m_ : n_) :
                    padding_penatly;
            }
            pimpl_->sequence_profile[i * matrix_width + j] =
                _mmxxx_load_si(reinterpret_cast<const __mxxxi*>(unpacked));
        }
    }

    const auto& rank_to_node_id = graph->rank_to_node_id();

    for (std::uint32_t i = 0; i < rank_to_node_id.size(); ++i) {
        pimpl_->node_id_to_rank[rank_to_node_id[i]] = i;
    }

    typename T::type kNegativeInfinity =
        std::numeric_limits<typename T::type>::min() + 1024;

    __mxxxi negative_infinities = T::_mmxxx_set1_epi(kNegativeInfinity);
    __mxxxi zeroes = T::_mmxxx_set1_epi(0);

    // initialize secondary matrices
    switch (subtype_) {
        case AlignmentSubtype::kConvex:
            for (std::uint32_t j = 0; j < matrix_width; ++j) {
                pimpl_->O[j] = negative_infinities;
                pimpl_->Q[j] = T::_mmxxx_set1_epi(q_ + j * T::kNumVar * c_);

                __mxxxi c = T::_mmxxx_set1_epi(c_);
                for (std::uint32_t k = 1; k < T::kNumVar; ++k) {
                    c = _mmxxx_slli_si(c, T::kLSS);
                    pimpl_->Q[j] = T::_mmxxx_add_epi(pimpl_->Q[j], c);
                }
            }
            pimpl_->first_column[2 * matrix_height] = 0;
            for (std::uint32_t i = 1; i < matrix_height; ++i) {
                const auto& edges =
                    graph->nodes()[rank_to_node_id[i - 1]]->in_edges();
                std::int32_t penalty = edges.empty() ? q_ - c_ : kNegativeInfinity;
                for (const auto& edge: edges) {
                    std::uint32_t pred_i = pimpl_->node_id_to_rank[
                        edge->begin_node_id()] + 1;
                    penalty = std::max(penalty,
                        pimpl_->first_column[2 * matrix_height + pred_i]);
                }
                pimpl_->first_column[2 * matrix_height + i] = penalty + c_;
            }
        case AlignmentSubtype::kAffine:
            for (std::uint32_t j = 0; j < matrix_width; ++j) {
                pimpl_->F[j] = negative_infinities;
                pimpl_->E[j] = T::_mmxxx_set1_epi(g_ + j * T::kNumVar * e_);

                __mxxxi e = T::_mmxxx_set1_epi(e_);
                for (std::uint32_t k = 1; k < T::kNumVar; ++k) {
                    e = _mmxxx_slli_si(e, T::kLSS);
                    pimpl_->E[j] = T::_mmxxx_add_epi(pimpl_->E[j], e);
                }
            }
            pimpl_->first_column[matrix_height] = 0;
            for (std::uint32_t i = 1; i < matrix_height; ++i) {
                const auto& edges =
                    graph->nodes()[rank_to_node_id[i - 1]]->in_edges();
                std::int32_t penalty = edges.empty() ? g_ - e_ : kNegativeInfinity;
                for (const auto& edge: edges) {
                    std::uint32_t pred_i = pimpl_->node_id_to_rank[
                        edge->begin_node_id()] + 1;
                    penalty = std::max(penalty,
                        pimpl_->first_column[matrix_height + pred_i]);
                }
                pimpl_->first_column[matrix_height + i] = penalty + e_;
            }
        case AlignmentSubtype::kLinear:
        default:
            break;
    }

    // initialize primary matrix
    switch (type_) {
        case AlignmentType::kSW:
            for (std::uint32_t j = 0; j < matrix_width; ++j) {
                pimpl_->H[j] = zeroes;
            }
            for (std::uint32_t i = 0; i < matrix_height; ++i) {
                pimpl_->first_column[i] = 0;
            }
            break;
        case AlignmentType::kNW:
            switch (subtype_) {
                case AlignmentSubtype::kConvex:
                    for (std::uint32_t i = 0; i < matrix_height; ++i) {
                        pimpl_->first_column[i] = std::max(
                            pimpl_->first_column[matrix_height + i],
                            pimpl_->first_column[2 * matrix_height + i]);
                    }
                    for (std::uint32_t j = 0; j < matrix_width; ++j) {
                        pimpl_->H[j] = T::_mmxxx_max_epi(pimpl_->E[j],
                            pimpl_->Q[j]);
                    }
                    break;
                case AlignmentSubtype::kAffine:
                    for (std::uint32_t i = 0; i < matrix_height; ++i) {
                        pimpl_->first_column[i] =
                            pimpl_->first_column[matrix_height + i];
                    }
                    for (std::uint32_t j = 0; j < matrix_width; ++j) {
                        pimpl_->H[j] = pimpl_->E[j];
                    }
                    break;
                case AlignmentSubtype::kLinear:
                    pimpl_->first_column[0] = 0;
                    for (std::uint32_t i = 1; i < matrix_height; ++i) {
                        const auto& edges =
                            graph->nodes()[rank_to_node_id[i - 1]]->in_edges();
                        std::int32_t penalty = edges.empty() ? 0 : kNegativeInfinity;
                        for (const auto& edge: edges) {
                            std::uint32_t pred_i = pimpl_->node_id_to_rank[
                                edge->begin_node_id()] + 1;
                            penalty = std::max(penalty,
                                pimpl_->first_column[pred_i]);
                        }
                        pimpl_->first_column[i] = penalty + g_;
                    }
                    for (std::uint32_t j = 0; j < matrix_width; ++j) {
                        pimpl_->H[j] = T::_mmxxx_set1_epi(g_ + j * T::kNumVar * g_);
                        __mxxxi g = T::_mmxxx_set1_epi(g_);

                        for (std::uint32_t k = 1; k < T::kNumVar; ++k) {
                            g = _mmxxx_slli_si(g, T::kLSS);
                            pimpl_->H[j] = T::_mmxxx_add_epi(pimpl_->H[j], g);
                        }
                    }
                default:
                    break;
            }
            break;
        case AlignmentType::kOV:
            switch (subtype_) {
                case AlignmentSubtype::kConvex:
                    for (std::uint32_t j = 0; j < matrix_width; ++j) {
                        pimpl_->H[j] = T::_mmxxx_max_epi(pimpl_->E[j],
                            pimpl_->Q[j]);
                    }
                    break;
                case AlignmentSubtype::kAffine:
                    for (std::uint32_t j = 0; j < matrix_width; ++j) {
                        pimpl_->H[j] = pimpl_->E[j];
                    }
                    break;
                case AlignmentSubtype::kLinear:
                    for (std::uint32_t j = 0; j < matrix_width; ++j) {
                        pimpl_->H[j] = T::_mmxxx_set1_epi(g_ + j * T::kNumVar * g_);
                        __mxxxi g = T::_mmxxx_set1_epi(g_);

                        for (std::uint32_t k = 1; k < T::kNumVar; ++k) {
                            g = _mmxxx_slli_si(g, T::kLSS);
                            pimpl_->H[j] = T::_mmxxx_add_epi(pimpl_->H[j], g);
                        }
                    }
                    break;
                default:
                    break;
            }
            for (std::uint32_t i = 0; i < matrix_height; ++i) {
                pimpl_->first_column[i] = 0;
            }
            break;
        default:
            break;
    }

#endif
}

Alignment SimdAlignmentEngine::align(const char* sequence,
    std::uint32_t sequence_size, const std::unique_ptr<Graph>& graph) noexcept {

    if (graph->nodes().empty() || sequence_size == 0) {
        return Alignment();
    }

#if defined(__AVX2__) || defined(__SSE4_1__)

    std::uint32_t longest_path = graph->nodes().size() + 1 + sequence_size +
        InstructionSet<std::int16_t>::kNumVar;

    std::uint32_t max_penalty = std::max(std::max(abs(m_), abs(n_)), abs(g_));

    if (max_penalty * longest_path < std::numeric_limits<std::int16_t>::max()) {
        if (subtype_ == AlignmentSubtype::kLinear) {
            return linear<InstructionSet<std::int16_t>>(sequence, sequence_size, graph);
        } else if (subtype_ == AlignmentSubtype::kAffine) {
            return affine<InstructionSet<std::int16_t>>(sequence, sequence_size, graph);
        } else if (subtype_ == AlignmentSubtype::kConvex) {
            return convex<InstructionSet<std::int16_t>>(sequence, sequence_size, graph);
        }
    } else {
        if (subtype_ == AlignmentSubtype::kLinear) {
            return linear<InstructionSet<std::int32_t>>(sequence, sequence_size, graph);
        } else if (subtype_ == AlignmentSubtype::kAffine) {
            return affine<InstructionSet<std::int32_t>>(sequence, sequence_size, graph);
        } else if (subtype_ == AlignmentSubtype::kConvex) {
            return convex<InstructionSet<std::int32_t>>(sequence, sequence_size, graph);
        }
    }

    return Alignment();

#else

    return Alignment();

#endif
}

template<typename T>
Alignment SimdAlignmentEngine::linear(const char* sequence,
    std::uint32_t sequence_size, const std::unique_ptr<Graph>& graph) noexcept {

#if defined(__AVX2__) || defined(__SSE4_1__)

    std::uint32_t normal_matrix_width = sequence_size;
    std::uint32_t matrix_width = (sequence_size + (sequence_size % T::kNumVar == 0 ?
        0 : T::kNumVar - sequence_size % T::kNumVar)) / T::kNumVar;
    std::uint32_t matrix_height = graph->nodes().size() + 1;
    const auto& rank_to_node_id = graph->rank_to_node_id();

    // realloc
    realloc(matrix_width, matrix_height, graph->num_codes());

    // initialize
    initialize<T>(sequence, graph, normal_matrix_width, matrix_width,
        matrix_height);

    typename T::type kNegativeInfinity =
        std::numeric_limits<typename T::type>::min() + 1024;

    __attribute__((aligned(kRegisterSize / 8))) typename T::type
        unpacked[T::kNumVar] = {0};

    for (std::uint32_t i = 0, j = 0; i < T::kNumVar && j < T::kLogNumVar; ++i) {
        unpacked[i] = kNegativeInfinity;
        if ((i & (i + 1)) == 0) {
            pimpl_->masks[j++] =
                _mmxxx_load_si(reinterpret_cast<const __mxxxi*>(unpacked));
        }
    }
    pimpl_->masks[T::kLogNumVar] = _mmxxx_slli_si(T::_mmxxx_set1_epi(
        kNegativeInfinity), T::kLSS);

    pimpl_->penalties[0] = T::_mmxxx_set1_epi(g_);
    for (std::uint32_t i = 1; i < T::kLogNumVar; ++i) {
        pimpl_->penalties[i] = T::_mmxxx_add_epi(pimpl_->penalties[i - 1],
            pimpl_->penalties[i - 1]);
    }

    typename T::type max_score = type_ == AlignmentType::kSW ? 0 : kNegativeInfinity;
    std::int32_t max_i = -1;
    std::int32_t max_j = -1;
    std::uint32_t last_column_id = (normal_matrix_width - 1) % T::kNumVar;
    __mxxxi zeroes = T::_mmxxx_set1_epi(0);
    __mxxxi g = T::_mmxxx_set1_epi(g_);

    // alignment
    for (std::uint32_t node_id: rank_to_node_id) {
        const auto& node = graph->nodes()[node_id];
        __mxxxi* char_profile =
            &(pimpl_->sequence_profile[node->code() * matrix_width]);

        std::uint32_t i = pimpl_->node_id_to_rank[node_id] + 1;
        std::uint32_t pred_i = node->in_edges().empty() ? 0 :
            pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

        __mxxxi* H_row = &(pimpl_->H[i * matrix_width]);
        __mxxxi* H_pred_row = &(pimpl_->H[pred_i * matrix_width]);

        __mxxxi x = _mmxxx_srli_si(T::_mmxxx_set1_epi(pimpl_->first_column[pred_i]),
            T::kRSS);

        for (std::uint32_t j = 0; j < matrix_width; ++j) {
            // get diagonal
            __mxxxi t1 = _mmxxx_srli_si(H_pred_row[j], T::kRSS);
            H_row[j] = _mmxxx_or_si(_mmxxx_slli_si(H_pred_row[j], T::kLSS), x);
            x = t1;

            // update M
            H_row[j] = T::_mmxxx_max_epi(T::_mmxxx_add_epi(H_row[j],
                char_profile[j]), T::_mmxxx_add_epi(H_pred_row[j], g));
        }

        // check other predecessors
        for (std::uint32_t p = 1; p < node->in_edges().size(); ++p) {
            pred_i = pimpl_->node_id_to_rank[node->in_edges()[p]->begin_node_id()] + 1;

            H_pred_row = &(pimpl_->H[pred_i * matrix_width]);

            x = _mmxxx_srli_si(T::_mmxxx_set1_epi(pimpl_->first_column[pred_i]),
                T::kRSS);

            for (std::uint32_t j = 0; j < matrix_width; ++j) {
                // get diagonal
                __mxxxi t1 = _mmxxx_srli_si(H_pred_row[j], T::kRSS);
                __mxxxi m = _mmxxx_or_si(_mmxxx_slli_si(H_pred_row[j], T::kLSS), x);
                x = t1;

                // updage M
                H_row[j] = T::_mmxxx_max_epi(H_row[j], T::_mmxxx_max_epi(
                    T::_mmxxx_add_epi(m, char_profile[j]),
                    T::_mmxxx_add_epi(H_pred_row[j], g)));
            }
        }

        __mxxxi score = T::_mmxxx_set1_epi(kNegativeInfinity);
        x = _mmxxx_srli_si(T::_mmxxx_add_epi(T::_mmxxx_set1_epi(
            pimpl_->first_column[i]), g), T::kRSS);

        for (std::uint32_t j = 0; j < matrix_width; ++j) {

            // add last element of previous vector into this one
            H_row[j] = T::_mmxxx_max_epi(H_row[j], _mmxxx_or_si(x,
                pimpl_->masks[T::kLogNumVar]));

            T::_mmxxx_prefix_max(H_row[j], pimpl_->masks, pimpl_->penalties);

            x = _mmxxx_srli_si(T::_mmxxx_add_epi(H_row[j], g), T::kRSS);

            if (type_ == AlignmentType::kSW) {
                H_row[j] = T::_mmxxx_max_epi(H_row[j], zeroes);
            }
            score = T::_mmxxx_max_epi(score, H_row[j]);
        }

        if (type_ == AlignmentType::kSW) {
            std::int32_t max_row_score = _mmxxx_max_value<T>(score);
            if (max_score < max_row_score) {
                max_score = max_row_score;
                max_i = i;
            }

        } else if (type_ == AlignmentType::kOV) {
            if (node->out_edges().empty()) {
                std::int32_t max_row_score = _mmxxx_max_value<T>(score);
                if (max_score < max_row_score) {
                    max_score = max_row_score;
                    max_i = i;
                }
            }

        } else if (type_ == AlignmentType::kNW) {
            if (node->out_edges().empty()) {
                std::int32_t max_row_score = _mmxxx_value_at<T>(
                    H_row[matrix_width - 1], last_column_id);
                if (max_score < max_row_score) {
                    max_score = max_row_score;
                    max_i = i;
                }
            }
        }
    }

    if (max_i == -1 && max_j == -1) { // no alignment found
        return Alignment();
    }

    if (type_ == AlignmentType::kSW) {
        max_j = _mmxxx_index_of<T>(&(pimpl_->H[max_i * matrix_width]),
            matrix_width, max_score);

    } else if (type_ == AlignmentType::kOV) {
        if (graph->nodes()[rank_to_node_id[max_i - 1]]->out_edges().empty()) {
            max_j = _mmxxx_index_of<T>(&(pimpl_->H[max_i * matrix_width]),
                matrix_width, max_score);
        } else {
            max_j = normal_matrix_width - 1;
        }

    } else if (type_ == AlignmentType::kNW) {
        max_j = normal_matrix_width - 1;
    }

    // backtrack
    std::uint32_t max_num_predecessors = 1;
    for (std::uint32_t i = 0; i < (std::uint32_t) max_i; ++i) {
        max_num_predecessors = std::max(max_num_predecessors,
            (std::uint32_t) graph->nodes()[rank_to_node_id[i]]->in_edges().size());
    }

    typename T::type* backtrack_storage = nullptr;
    typename T::type* H = allocateAlignedMemory(&backtrack_storage,
        3 * T::kNumVar + 2 * T::kNumVar * max_num_predecessors, kRegisterSize / 8);
    typename T::type* H_pred = H + T::kNumVar;
    typename T::type* H_diag_pred = H_pred + T::kNumVar * max_num_predecessors;
    typename T::type* H_left_pred = H_diag_pred + T::kNumVar * max_num_predecessors;
    typename T::type* profile = H_left_pred + T::kNumVar;

    std::vector<std::uint32_t> predecessors;

    std::int32_t i = max_i;
    std::int32_t j = max_j;
    std::int32_t prev_i = 0, prev_j = 0;

    std::uint32_t j_div = j / T::kNumVar;
    std::uint32_t j_mod = j % T::kNumVar;

    bool load_next_segment = true;

    Alignment alignment;

    do {
        // check stop condition
        if (j == -1 || i == 0) {
            break;
        }

        const auto& node = graph->nodes()[rank_to_node_id[i - 1]];
        // load everything
        if (load_next_segment) {
            predecessors.clear();

            // load current cells
            _mmxxx_store_si(reinterpret_cast<__mxxxi*>(H),
                pimpl_->H[i * matrix_width + j_div]);

            // load predecessors cells
            if (node->in_edges().empty()) {
                predecessors.emplace_back(0);
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(H_pred),
                    pimpl_->H[j_div]);

            } else {
                std::uint32_t store_pos = 0;
                for (const auto& edge: node->in_edges()) {
                    predecessors.emplace_back(
                        pimpl_->node_id_to_rank[edge->begin_node_id()] + 1);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&H_pred[store_pos * T::kNumVar]),
                        pimpl_->H[predecessors.back() * matrix_width + j_div]);
                    ++store_pos;
                }
            }

            // load query profile cells
            _mmxxx_store_si(reinterpret_cast<__mxxxi*>(profile),
                pimpl_->sequence_profile[node->code() * matrix_width + j_div]);
        }

        // check stop condition
        if (type_ == AlignmentType::kSW && H[j_mod] == 0) {
            break;
        }

        if (j_mod == 0) {
            // border case
            if (j_div > 0) {
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(H_left_pred),
                    pimpl_->H[i * matrix_width + j_div - 1]);

                for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&H_diag_pred[p * T::kNumVar]),
                        pimpl_->H[predecessors[p] * matrix_width + (j_div - 1)]);
                }
            } else {
                H_left_pred[T::kNumVar - 1] = pimpl_->first_column[i];

                for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                    H_diag_pred[(p + 1) * T::kNumVar - 1] =
                        pimpl_->first_column[predecessors[p]];
                }
            }
        }

        // find best predecessor cell
        bool predecessor_found = false;

        if (i != 0) {
            for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                if ((j_mod == 0 && H[j_mod] ==
                        H_diag_pred[(p + 1) * T::kNumVar - 1] + profile[j_mod]) ||
                    (j_mod != 0 && H[j_mod] ==
                        H_pred[p * T::kNumVar + j_mod - 1] + profile[j_mod])) {

                    prev_i = predecessors[p];
                    prev_j = j - 1;
                    predecessor_found = true;
                    break;
                }
            }
        }

        if (!predecessor_found && i != 0) {
            for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                if (H[j_mod] == H_pred[p * T::kNumVar + j_mod] + g_) {
                    prev_i = predecessors[p];
                    prev_j = j;
                    predecessor_found = true;
                    break;
                }
            }
        }

        if (!predecessor_found) {
            if ((j_mod == 0 && H[j_mod] == H_left_pred[T::kNumVar - 1] + g_) ||
                (j_mod != 0 && H[j_mod] == H[j_mod - 1] + g_)) {
                prev_i = i;
                prev_j = j - 1;
                predecessor_found = true;
            }
        }

        alignment.emplace_back(i == prev_i ? -1 : rank_to_node_id[i - 1],
            j == prev_j ? -1 : j);

        // update for next round
        load_next_segment = (i == prev_i ? false : true) ||
            (j != prev_j && prev_j % T::kNumVar == T::kNumVar - 1 ? true : false);

        i = prev_i;
        j = prev_j;
        j_div = j / T::kNumVar;
        j_mod = j % T::kNumVar;

    } while (true);

    delete[] backtrack_storage;

    // update alignment for NW (backtrack stops on first row or column)
    if (type_ == AlignmentType::kNW) {
        while (i == 0 && j != -1) {
            alignment.emplace_back(-1, j);
            --j;
        }
        while (i != 0 && j == -1) {
            alignment.emplace_back(rank_to_node_id[i - 1], -1);

            const auto& node = graph->nodes()[rank_to_node_id[i - 1]];
            if (node->in_edges().empty()) {
                i = 0;
            } else {
                for (const auto& edge: node->in_edges()) {
                    std::uint32_t pred_i =
                        pimpl_->node_id_to_rank[edge->begin_node_id()] + 1;
                    if (pimpl_->first_column[i] ==
                        pimpl_->first_column[pred_i] + g_) {
                        i = pred_i;
                        break;
                    }
                }
            }
        }
    }

    std::reverse(alignment.begin(), alignment.end());
    return alignment;

#else

    return Alignment();

#endif
}

template<typename T>
Alignment SimdAlignmentEngine::affine(const char* sequence,
    std::uint32_t sequence_size, const std::unique_ptr<Graph>& graph) noexcept {

#if defined(__AVX2__) || defined(__SSE4_1__)

    std::uint32_t normal_matrix_width = sequence_size;
    std::uint32_t matrix_width = (sequence_size + (sequence_size % T::kNumVar == 0 ?
        0 : T::kNumVar - sequence_size % T::kNumVar)) / T::kNumVar;
    std::uint32_t matrix_height = graph->nodes().size() + 1;
    const auto& rank_to_node_id = graph->rank_to_node_id();

    // realloc
    realloc(matrix_width, matrix_height, graph->num_codes());

    // initialize
    initialize<T>(sequence, graph, normal_matrix_width, matrix_width,
        matrix_height);

    typename T::type kNegativeInfinity =
        std::numeric_limits<typename T::type>::min() + 1024;

    typename T::type max_score = type_ == AlignmentType::kSW ? 0 : kNegativeInfinity;
    std::int32_t max_i = -1;
    std::int32_t max_j = -1;
    std::uint32_t last_column_id = (normal_matrix_width - 1) % T::kNumVar;
    __mxxxi zeroes = T::_mmxxx_set1_epi(0);
    __mxxxi g = T::_mmxxx_set1_epi(g_ - e_);
    __mxxxi e = T::_mmxxx_set1_epi(e_);

    __attribute__((aligned(kRegisterSize / 8))) typename T::type
        unpacked[T::kNumVar] = {0};

    for (std::uint32_t i = 0, j = 0; i < T::kNumVar && j < T::kLogNumVar; ++i) {
        unpacked[i] = kNegativeInfinity;
        if ((i & (i + 1)) == 0) {
            pimpl_->masks[j++] =
                _mmxxx_load_si(reinterpret_cast<const __mxxxi*>(unpacked));
        }
    }
    pimpl_->masks[T::kLogNumVar] =
        _mmxxx_slli_si(T::_mmxxx_set1_epi(kNegativeInfinity), T::kLSS);

    pimpl_->penalties[0] = T::_mmxxx_set1_epi(e_);
    for (std::uint32_t i = 1; i < T::kLogNumVar; ++i) {
        pimpl_->penalties[i] = T::_mmxxx_add_epi(pimpl_->penalties[i - 1],
            pimpl_->penalties[i - 1]);
    }

    // alignment
    for (std::uint32_t node_id: rank_to_node_id) {
        const auto& node = graph->nodes()[node_id];
        __mxxxi* char_profile =
            &(pimpl_->sequence_profile[node->code() * matrix_width]);

        std::uint32_t i = pimpl_->node_id_to_rank[node_id] + 1;

        __mxxxi* H_row = &(pimpl_->H[i * matrix_width]);
        __mxxxi* F_row = &(pimpl_->F[i * matrix_width]);

        std::uint32_t pred_i = node->in_edges().empty() ? 0 :
            pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

        __mxxxi* H_pred_row = &(pimpl_->H[pred_i * matrix_width]);
        __mxxxi* F_pred_row = &(pimpl_->F[pred_i * matrix_width]);

        __mxxxi x = _mmxxx_srli_si(T::_mmxxx_set1_epi(
            pimpl_->first_column[pred_i]), T::kRSS);

        for (std::uint32_t j = 0; j < matrix_width; ++j) {
            // update F
            F_row[j] = T::_mmxxx_add_epi(T::_mmxxx_max_epi(T::_mmxxx_add_epi(
                H_pred_row[j], g), F_pred_row[j]), e);

            // update H
            H_row[j] = T::_mmxxx_add_epi(_mmxxx_or_si(_mmxxx_slli_si(
                H_pred_row[j], T::kLSS), x), char_profile[j]);
            x = _mmxxx_srli_si(H_pred_row[j], T::kRSS);
        }

        // check other predecessors
        for (std::uint32_t p = 1; p < node->in_edges().size(); ++p) {
            pred_i = pimpl_->node_id_to_rank[node->in_edges()[p]->begin_node_id()] + 1;

            H_pred_row = &(pimpl_->H[pred_i * matrix_width]);
            F_pred_row = &(pimpl_->F[pred_i * matrix_width]);

            x = _mmxxx_srli_si(T::_mmxxx_set1_epi(
                pimpl_->first_column[pred_i]), T::kRSS);

            for (std::uint32_t j = 0; j < matrix_width; ++j) {
                // update F
                F_row[j] = T::_mmxxx_max_epi(F_row[j], T::_mmxxx_add_epi(
                    T::_mmxxx_max_epi(T::_mmxxx_add_epi(H_pred_row[j], g),
                    F_pred_row[j]), e));

                // update H
                H_row[j] = T::_mmxxx_max_epi(H_row[j], T::_mmxxx_add_epi(
                    _mmxxx_or_si(_mmxxx_slli_si(H_pred_row[j], T::kLSS), x),
                    char_profile[j]));
                x = _mmxxx_srli_si(H_pred_row[j], T::kRSS);
            }
        }

        __mxxxi* E_row = &(pimpl_->E[i * matrix_width]);
        __mxxxi score = zeroes;
        x = T::_mmxxx_set1_epi(pimpl_->first_column[i]);

        for (std::uint32_t j = 0; j < matrix_width; ++j) {
            H_row[j] = T::_mmxxx_max_epi(H_row[j], F_row[j]);

            E_row[j] = T::_mmxxx_add_epi(T::_mmxxx_add_epi(_mmxxx_or_si(
                _mmxxx_slli_si(H_row[j], T::kLSS), _mmxxx_srli_si(x, T::kRSS)), g), e);

            T::_mmxxx_prefix_max(E_row[j], pimpl_->masks, pimpl_->penalties);

            H_row[j] = T::_mmxxx_max_epi(H_row[j], E_row[j]);
            x = T::_mmxxx_max_epi(H_row[j], T::_mmxxx_sub_epi(E_row[j], g));

            if (type_ == AlignmentType::kSW) {
                H_row[j] = T::_mmxxx_max_epi(H_row[j], zeroes);
            }
            score = T::_mmxxx_max_epi(score, H_row[j]);
        }

        if (type_ == AlignmentType::kSW) {
            std::int32_t max_row_score = _mmxxx_max_value<T>(score);
            if (max_score < max_row_score) {
                max_score = max_row_score;
                max_i = i;
            }

        } else if (type_ == AlignmentType::kOV) {
            if (node->out_edges().empty()) {
                std::int32_t max_row_score = _mmxxx_max_value<T>(score);
                if (max_score < max_row_score) {
                    max_score = max_row_score;
                    max_i = i;
                }
            }

        } else if (type_ == AlignmentType::kNW) {
            if (node->out_edges().empty()) {
                std::int32_t max_row_score = _mmxxx_value_at<T>(
                    H_row[matrix_width - 1], last_column_id);
                if (max_score < max_row_score) {
                    max_score = max_row_score;
                    max_i = i;
                }
            }
        }
    }

    if (max_i == -1 && max_j == -1) { // no alignment found
        return Alignment();
    }

    if (type_ == AlignmentType::kSW) {
        max_j = _mmxxx_index_of<T>(&(pimpl_->H[max_i * matrix_width]),
            matrix_width, max_score);

    } else if (type_ == AlignmentType::kOV) {
        if (graph->nodes()[rank_to_node_id[max_i - 1]]->out_edges().empty()) {
            max_j = _mmxxx_index_of<T>(&(pimpl_->H[max_i * matrix_width]),
                matrix_width, max_score);
        } else {
            max_j = normal_matrix_width - 1;
        }

    } else if (type_ == AlignmentType::kNW) {
        max_j = normal_matrix_width - 1;
    }

    // backtrack
    std::uint32_t max_num_predecessors = 0;
    for (std::uint32_t i = 0; i < (std::uint32_t) max_i; ++i) {
        max_num_predecessors = std::max(max_num_predecessors,
            (std::uint32_t) graph->nodes()[rank_to_node_id[i]]->in_edges().size());
    }

    typename T::type* backtrack_storage = nullptr;
    typename T::type* H = allocateAlignedMemory(&backtrack_storage,
        6 * T::kNumVar + 3 * T::kNumVar * max_num_predecessors, kRegisterSize / 8);
    typename T::type* H_pred = H + T::kNumVar;
    typename T::type* H_diag_pred = H_pred + T::kNumVar * max_num_predecessors;
    typename T::type* H_left = H_diag_pred + T::kNumVar * max_num_predecessors;
    typename T::type* F = H_left + T::kNumVar;
    typename T::type* F_pred = F + T::kNumVar;
    typename T::type* E = F_pred + T::kNumVar * max_num_predecessors;
    typename T::type* E_left = E + T::kNumVar;
    typename T::type* profile = E_left + T::kNumVar;

    std::vector<std::uint32_t> predecessors;

    std::int32_t i = max_i;
    std::int32_t j = max_j;
    std::int32_t prev_i = 0, prev_j = 0;

    std::uint32_t j_div = j / T::kNumVar;
    std::uint32_t j_mod = j % T::kNumVar;

    bool load_next_segment = true;

    Alignment alignment;

    do {
        // check stop condition
        if (j == -1 || i == 0) {
            break;
        }

        const auto& node = graph->nodes()[rank_to_node_id[i - 1]];
        // load everything
        if (load_next_segment) {
            predecessors.clear();

            // load current cells
            _mmxxx_store_si(reinterpret_cast<__mxxxi*>(H),
                pimpl_->H[i * matrix_width + j_div]);
            _mmxxx_store_si(reinterpret_cast<__mxxxi*>(E),
                pimpl_->E[i * matrix_width + j_div]);

            // load predecessors cells
            if (node->in_edges().empty()) {
                predecessors.emplace_back(0);
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(H_pred),
                    pimpl_->H[j_div]);
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(F_pred),
                    pimpl_->F[j_div]);

            } else {
                std::uint32_t store_pos = 0;
                for (const auto& edge: node->in_edges()) {
                    predecessors.emplace_back(
                        pimpl_->node_id_to_rank[edge->begin_node_id()] + 1);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&H_pred[store_pos * T::kNumVar]),
                        pimpl_->H[predecessors.back() * matrix_width + j_div]);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&F_pred[store_pos * T::kNumVar]),
                        pimpl_->F[predecessors.back() * matrix_width + j_div]);
                    ++store_pos;
                }
            }

            // load query profile cells
            _mmxxx_store_si(reinterpret_cast<__mxxxi*>(profile),
                pimpl_->sequence_profile[node->code() * matrix_width + j_div]);
        }

        // check stop condition
        if (type_ == AlignmentType::kSW && H[j_mod] == 0) {
            break;
        }

        if (j_mod == 0) {
            // border case
            if (j_div > 0) {
                for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&H_diag_pred[p * T::kNumVar]),
                        pimpl_->H[predecessors[p] * matrix_width + (j_div - 1)]);
                }
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(H_left),
                    pimpl_->H[i * matrix_width + j_div - 1]);
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(E_left),
                    pimpl_->E[i * matrix_width + j_div - 1]);
            } else {
                for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                    H_diag_pred[(p + 1) * T::kNumVar - 1] =
                        pimpl_->first_column[predecessors[p]];
                }
                H_left[T::kNumVar - 1] = pimpl_->first_column[i];
                E_left[T::kNumVar - 1] = pimpl_->first_column[i];
            }
        }

        // find best predecessor cell
        bool predecessor_found = false, extend_left = false, extend_up = false;

        if (i != 0) {
            for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                if ((j_mod == 0 && H[j_mod] == H_diag_pred[(p + 1) * T::kNumVar - 1] + profile[j_mod]) ||
                    (j_mod != 0 && H[j_mod] == H_pred[p * T::kNumVar + j_mod - 1] + profile[j_mod])) {
                    prev_i = predecessors[p];
                    prev_j = j - 1;
                    predecessor_found = true;
                    break;
                }
            }
        }

        if (!predecessor_found && i != 0) {
            for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                if ((extend_up = H[j_mod] == F_pred[p * T::kNumVar + j_mod] + e_) ||
                                 H[j_mod] == H_pred[p * T::kNumVar + j_mod] + g_) {
                    prev_i = predecessors[p];
                    prev_j = j;
                    predecessor_found = true;
                    break;
                }
            }
        }

        if (!predecessor_found) {
            if ((j_mod != 0 && ((extend_left = H[j_mod] == E[j_mod - 1] + e_) ||
                                               H[j_mod] == H[j_mod - 1] + g_)) ||
                (j_mod == 0 && ((extend_left = H[j_mod] == E_left[T::kNumVar - 1] + e_ ) ||
                                               H[j_mod] == H_left[T::kNumVar - 1] + g_))) {
                prev_i = i;
                prev_j = j - 1;
                predecessor_found = true;
            }
        }

        alignment.emplace_back(i == prev_i ? -1 : rank_to_node_id[i - 1],
            j == prev_j ? -1 : j);

        // update for next round
        load_next_segment = (i == prev_i ? false : true) ||
            (j != prev_j && prev_j % T::kNumVar == T::kNumVar - 1 ? true : false);

        i = prev_i;
        j = prev_j;
        j_div = j / T::kNumVar;
        j_mod = j % T::kNumVar;

        if (extend_left) {
            while (true) {
                // load
                if (j_mod == T::kNumVar - 1) {
                    _mmxxx_store_si(reinterpret_cast<__mxxxi*>(E),
                        pimpl_->E[i * matrix_width + j_div]);
                } else if (j_mod == 0) { // boarder case
                    if (j_div > 0) {
                        _mmxxx_store_si(reinterpret_cast<__mxxxi*>(E_left),
                            pimpl_->E[i * matrix_width + j_div - 1]);
                    }
                }

                alignment.emplace_back(-1, j);
                --j;
                j_div = j / T::kNumVar;
                j_mod = j % T::kNumVar;
                if (j == -1 ||
                    (j_mod != T::kNumVar - 1 && E[j_mod] + e_ != E[j_mod + 1]) ||
                    (j_mod == T::kNumVar - 1 && E_left[j_mod] + e_ != E[0])) {
                    break;
                }
            }
            load_next_segment = true;
        } else if (extend_up) {
            while (true) {
                // load
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(F),
                    pimpl_->F[i * matrix_width + j_div]);

                prev_i = 0;
                predecessors.clear();
                std::uint32_t store_pos = 0;
                for (const auto& it: graph->nodes()[rank_to_node_id[i - 1]]->in_edges()) {
                    predecessors.emplace_back(
                        pimpl_->node_id_to_rank[it->begin_node_id()] + 1);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&H_pred[store_pos * T::kNumVar]),
                        pimpl_->H[predecessors.back() * matrix_width + j_div]);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&F_pred[store_pos * T::kNumVar]),
                        pimpl_->F[predecessors.back() * matrix_width + j_div]);
                    ++store_pos;
                }

                bool stop = false;
                for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                    if ((stop = F[j_mod] == H_pred[p * T::kNumVar + j_mod] + g_) ||
                                F[j_mod] == F_pred[p * T::kNumVar + j_mod] + e_) {
                        prev_i = predecessors[p];
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

    } while (true);

    delete[] backtrack_storage;

    // update alignment for NW (backtrack stops on first row or column)
    if (type_ == AlignmentType::kNW) {
        while (i == 0 && j != -1) {
            alignment.emplace_back(-1, j);
            --j;
        }
        while (i != 0 && j == -1) {
            alignment.emplace_back(rank_to_node_id[i - 1], -1);

            const auto& node = graph->nodes()[rank_to_node_id[i - 1]];
            if (node->in_edges().empty()) {
                i = 0;
            } else {
                for (const auto& edge: node->in_edges()) {
                    std::uint32_t pred_i =
                        pimpl_->node_id_to_rank[edge->begin_node_id()] + 1;
                    if (pimpl_->first_column[i] ==
                        pimpl_->first_column[pred_i] + e_) {
                        i = pred_i;
                        break;
                    }
                }
            }
        }
    }

    std::reverse(alignment.begin(), alignment.end());
    return alignment;

#else

    return Alignment();

#endif
}

template<typename T>
Alignment SimdAlignmentEngine::convex(const char* sequence,
    std::uint32_t sequence_size, const std::unique_ptr<Graph>& graph) noexcept {

#if defined(__AVX2__) || defined(__SSE4_1__)

    std::uint32_t normal_matrix_width = sequence_size;
    std::uint32_t matrix_width = (sequence_size + (sequence_size % T::kNumVar == 0 ?
        0 : T::kNumVar - sequence_size % T::kNumVar)) / T::kNumVar;
    std::uint32_t matrix_height = graph->nodes().size() + 1;
    const auto& rank_to_node_id = graph->rank_to_node_id();

    // realloc
    realloc(matrix_width, matrix_height, graph->num_codes());

    // initialize
    initialize<T>(sequence, graph, normal_matrix_width, matrix_width,
        matrix_height);

    typename T::type kNegativeInfinity =
        std::numeric_limits<typename T::type>::min() + 1024;

    typename T::type max_score = type_ == AlignmentType::kSW ? 0 : kNegativeInfinity;
    std::int32_t max_i = -1;
    std::int32_t max_j = -1;
    std::uint32_t last_column_id = (normal_matrix_width - 1) % T::kNumVar;
    __mxxxi zeroes = T::_mmxxx_set1_epi(0);
    __mxxxi g = T::_mmxxx_set1_epi(g_ - e_);
    __mxxxi e = T::_mmxxx_set1_epi(e_);
    __mxxxi q = T::_mmxxx_set1_epi(q_ - c_);
    __mxxxi c = T::_mmxxx_set1_epi(c_);

    __attribute__((aligned(kRegisterSize / 8))) typename T::type
        unpacked[T::kNumVar] = {0};

    for (std::uint32_t i = 0, j = 0; i < T::kNumVar && j < T::kLogNumVar; ++i) {
        unpacked[i] = kNegativeInfinity;
        if ((i & (i + 1)) == 0) {
            pimpl_->masks[j++] =
                _mmxxx_load_si(reinterpret_cast<const __mxxxi*>(unpacked));
        }
    }
    pimpl_->masks[T::kLogNumVar] =
        _mmxxx_slli_si(T::_mmxxx_set1_epi(kNegativeInfinity), T::kLSS);

    pimpl_->penalties[0] = T::_mmxxx_set1_epi(e_);
    for (std::uint32_t i = 1; i < T::kLogNumVar; ++i) {
        pimpl_->penalties[i] = T::_mmxxx_add_epi(pimpl_->penalties[i - 1],
            pimpl_->penalties[i - 1]);
    }
    pimpl_->penalties[T::kLogNumVar] = T::_mmxxx_set1_epi(c_);
    for (std::uint32_t i = T::kLogNumVar + 1; i < 2 * T::kLogNumVar; ++i) {
        pimpl_->penalties[i] = T::_mmxxx_add_epi(pimpl_->penalties[i - 1],
            pimpl_->penalties[i - 1]);
    }

    // alignment
    for (std::uint32_t node_id: rank_to_node_id) {
        const auto& node = graph->nodes()[node_id];
        __mxxxi* char_profile =
            &(pimpl_->sequence_profile[node->code() * matrix_width]);

        std::uint32_t i = pimpl_->node_id_to_rank[node_id] + 1;

        __mxxxi* H_row = &(pimpl_->H[i * matrix_width]);
        __mxxxi* F_row = &(pimpl_->F[i * matrix_width]);
        __mxxxi* O_row = &(pimpl_->O[i * matrix_width]);

        std::uint32_t pred_i = node->in_edges().empty() ? 0 :
            pimpl_->node_id_to_rank[node->in_edges()[0]->begin_node_id()] + 1;

        __mxxxi* H_pred_row = &(pimpl_->H[pred_i * matrix_width]);
        __mxxxi* F_pred_row = &(pimpl_->F[pred_i * matrix_width]);
        __mxxxi* O_pred_row = &(pimpl_->O[pred_i * matrix_width]);

        __mxxxi x = _mmxxx_srli_si(T::_mmxxx_set1_epi(
            pimpl_->first_column[pred_i]), T::kRSS);

        for (std::uint32_t j = 0; j < matrix_width; ++j) {
            // update F
            F_row[j] = T::_mmxxx_add_epi(T::_mmxxx_max_epi(T::_mmxxx_add_epi(
                H_pred_row[j], g), F_pred_row[j]), e);

            // update O
            O_row[j] = T::_mmxxx_add_epi(T::_mmxxx_max_epi(T::_mmxxx_add_epi(
                H_pred_row[j], q), O_pred_row[j]), c);

            // update H
            H_row[j] = T::_mmxxx_add_epi(_mmxxx_or_si(_mmxxx_slli_si(
                H_pred_row[j], T::kLSS), x), char_profile[j]);
            x = _mmxxx_srli_si(H_pred_row[j], T::kRSS);
        }

        // check other predecessors
        for (std::uint32_t p = 1; p < node->in_edges().size(); ++p) {
            pred_i = pimpl_->node_id_to_rank[node->in_edges()[p]->begin_node_id()] + 1;

            H_pred_row = &(pimpl_->H[pred_i * matrix_width]);
            F_pred_row = &(pimpl_->F[pred_i * matrix_width]);
            O_pred_row = &(pimpl_->O[pred_i * matrix_width]);

            x = _mmxxx_srli_si(T::_mmxxx_set1_epi(
                pimpl_->first_column[pred_i]), T::kRSS);

            for (std::uint32_t j = 0; j < matrix_width; ++j) {
                // update F
                F_row[j] = T::_mmxxx_max_epi(F_row[j], T::_mmxxx_add_epi(
                    T::_mmxxx_max_epi(T::_mmxxx_add_epi(H_pred_row[j],
                    g), F_pred_row[j]), e));

                // update O
                O_row[j] = T::_mmxxx_max_epi(O_row[j], T::_mmxxx_add_epi(
                    T::_mmxxx_max_epi(T::_mmxxx_add_epi(H_pred_row[j],
                    q), O_pred_row[j]), c));

                // update H
                H_row[j] = T::_mmxxx_max_epi(H_row[j], T::_mmxxx_add_epi(
                    _mmxxx_or_si(_mmxxx_slli_si(H_pred_row[j], T::kLSS), x),
                    char_profile[j]));
                x = _mmxxx_srli_si(H_pred_row[j], T::kRSS);
            }
        }

        __mxxxi* E_row = &(pimpl_->E[i * matrix_width]);
        __mxxxi* Q_row = &(pimpl_->Q[i * matrix_width]);

        x = T::_mmxxx_set1_epi(pimpl_->first_column[i]);
        __mxxxi y = T::_mmxxx_set1_epi(pimpl_->first_column[i]);

        __mxxxi score = zeroes;

        for (std::uint32_t j = 0; j < matrix_width; ++j) {
            H_row[j] = T::_mmxxx_max_epi(H_row[j], T::_mmxxx_max_epi(F_row[j],
                O_row[j]));

            E_row[j] = T::_mmxxx_add_epi(T::_mmxxx_add_epi(_mmxxx_or_si(
                _mmxxx_slli_si(H_row[j], T::kLSS), _mmxxx_srli_si(x, T::kRSS)),
                g), e);

            T::_mmxxx_prefix_max(E_row[j], pimpl_->masks, pimpl_->penalties);

            Q_row[j] = T::_mmxxx_add_epi(T::_mmxxx_add_epi(_mmxxx_or_si(
                _mmxxx_slli_si(H_row[j], T::kLSS), _mmxxx_srli_si(y, T::kRSS)),
                q), c);

            T::_mmxxx_prefix_max(Q_row[j], pimpl_->masks,
                &pimpl_->penalties[T::kLogNumVar]);

            H_row[j] = T::_mmxxx_max_epi(H_row[j], T::_mmxxx_max_epi(E_row[j],
                Q_row[j]));

            x = T::_mmxxx_max_epi(H_row[j], T::_mmxxx_sub_epi(E_row[j], g));
            y = T::_mmxxx_max_epi(H_row[j], T::_mmxxx_sub_epi(Q_row[j], q));

            if (type_ == AlignmentType::kSW) {
                H_row[j] = T::_mmxxx_max_epi(H_row[j], zeroes);
            }
            score = T::_mmxxx_max_epi(score, H_row[j]);
        }

        if (type_ == AlignmentType::kSW) {
            std::int32_t max_row_score = _mmxxx_max_value<T>(score);
            if (max_score < max_row_score) {
                max_score = max_row_score;
                max_i = i;
            }

        } else if (type_ == AlignmentType::kOV) {
            if (node->out_edges().empty()) {
                std::int32_t max_row_score = _mmxxx_max_value<T>(score);
                if (max_score < max_row_score) {
                    max_score = max_row_score;
                    max_i = i;
                }
            }

        } else if (type_ == AlignmentType::kNW) {
            if (node->out_edges().empty()) {
                std::int32_t max_row_score = _mmxxx_value_at<T>(
                    H_row[matrix_width - 1], last_column_id);
                if (max_score < max_row_score) {
                    max_score = max_row_score;
                    max_i = i;
                }
            }
        }
    }

    if (max_i == -1 && max_j == -1) { // no alignment found
        return Alignment();
    }

    if (type_ == AlignmentType::kSW) {
        max_j = _mmxxx_index_of<T>(&(pimpl_->H[max_i * matrix_width]),
            matrix_width, max_score);

    } else if (type_ == AlignmentType::kOV) {
        if (graph->nodes()[rank_to_node_id[max_i - 1]]->out_edges().empty()) {
            max_j = _mmxxx_index_of<T>(&(pimpl_->H[max_i * matrix_width]),
                matrix_width, max_score);
        } else {
            max_j = normal_matrix_width - 1;
        }

    } else if (type_ == AlignmentType::kNW) {
        max_j = normal_matrix_width - 1;
    }

    // backtrack
    std::uint32_t max_num_predecessors = 0;
    for (std::uint32_t i = 0; i < (std::uint32_t) max_i; ++i) {
        max_num_predecessors = std::max(max_num_predecessors,
            (std::uint32_t) graph->nodes()[rank_to_node_id[i]]->in_edges().size());
    }

    typename T::type* backtrack_storage = nullptr;
    typename T::type* H = allocateAlignedMemory(&backtrack_storage,
        9 * T::kNumVar + 4 * T::kNumVar * max_num_predecessors, kRegisterSize / 8);
    typename T::type* H_pred = H + T::kNumVar;
    typename T::type* H_diag_pred = H_pred + T::kNumVar * max_num_predecessors;
    typename T::type* H_left = H_diag_pred + T::kNumVar * max_num_predecessors;
    typename T::type* F = H_left + T::kNumVar;
    typename T::type* F_pred = F + T::kNumVar;
    typename T::type* O = F_pred + T::kNumVar * max_num_predecessors;
    typename T::type* O_pred = O + T::kNumVar;
    typename T::type* E = O_pred + T::kNumVar * max_num_predecessors;
    typename T::type* E_left = E + T::kNumVar;
    typename T::type* Q = E_left + T::kNumVar;
    typename T::type* Q_left = Q + T::kNumVar;
    typename T::type* profile = Q_left + T::kNumVar;

    std::vector<std::uint32_t> predecessors;

    std::int32_t i = max_i;
    std::int32_t j = max_j;
    std::int32_t prev_i = 0, prev_j = 0;

    std::uint32_t j_div = j / T::kNumVar;
    std::uint32_t j_mod = j % T::kNumVar;

    bool load_next_segment = true;

    Alignment alignment;

    do {
        // check stop condition
        if (j == -1 || i == 0) {
            break;
        }

        const auto& node = graph->nodes()[rank_to_node_id[i - 1]];
        // load everything
        if (load_next_segment) {
            predecessors.clear();

            // load current cells
            _mmxxx_store_si(reinterpret_cast<__mxxxi*>(H),
                pimpl_->H[i * matrix_width + j_div]);
            _mmxxx_store_si(reinterpret_cast<__mxxxi*>(E),
                pimpl_->E[i * matrix_width + j_div]);
            _mmxxx_store_si(reinterpret_cast<__mxxxi*>(Q),
                pimpl_->Q[i * matrix_width + j_div]);

            // load predecessors cells
            if (node->in_edges().empty()) {
                predecessors.emplace_back(0);
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(H_pred),
                    pimpl_->H[j_div]);
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(F_pred),
                    pimpl_->F[j_div]);
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(O_pred),
                    pimpl_->O[j_div]);

            } else {
                std::uint32_t store_pos = 0;
                for (const auto& edge: node->in_edges()) {
                    predecessors.emplace_back(
                        pimpl_->node_id_to_rank[edge->begin_node_id()] + 1);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&H_pred[store_pos * T::kNumVar]),
                        pimpl_->H[predecessors.back() * matrix_width + j_div]);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&F_pred[store_pos * T::kNumVar]),
                        pimpl_->F[predecessors.back() * matrix_width + j_div]);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&O_pred[store_pos * T::kNumVar]),
                        pimpl_->O[predecessors.back() * matrix_width + j_div]);
                    ++store_pos;
                }
            }

            // load query profile cells
            _mmxxx_store_si(reinterpret_cast<__mxxxi*>(profile),
                pimpl_->sequence_profile[node->code() * matrix_width + j_div]);
        }

        // check stop condition
        if (type_ == AlignmentType::kSW && H[j_mod] == 0) {
            break;
        }

        if (j_mod == 0) {
            // border case
            if (j_div > 0) {
                for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&H_diag_pred[p * T::kNumVar]),
                        pimpl_->H[predecessors[p] * matrix_width + (j_div - 1)]);
                }
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(H_left),
                    pimpl_->H[i * matrix_width + j_div - 1]);
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(E_left),
                    pimpl_->E[i * matrix_width + j_div - 1]);
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(Q_left),
                    pimpl_->Q[i * matrix_width + j_div - 1]);
            } else {
                for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                    H_diag_pred[(p + 1) * T::kNumVar - 1] =
                        pimpl_->first_column[predecessors[p]];
                }
                H_left[T::kNumVar - 1] = pimpl_->first_column[i];
                E_left[T::kNumVar - 1] = pimpl_->first_column[i];
                Q_left[T::kNumVar - 1] = pimpl_->first_column[i];
            }
        }

        // find best predecessor cell
        bool predecessor_found = false, extend_left = false, extend_up = false;

        if (i != 0) {
            for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                if ((j_mod == 0 && H[j_mod] == H_diag_pred[(p + 1) * T::kNumVar - 1] + profile[j_mod]) ||
                    (j_mod != 0 && H[j_mod] == H_pred[p * T::kNumVar + j_mod - 1] + profile[j_mod])) {
                    prev_i = predecessors[p];
                    prev_j = j - 1;
                    predecessor_found = true;
                    break;
                }
            }
        }

        if (!predecessor_found && i != 0) {
            for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                if ((extend_up = H[j_mod] == F_pred[p * T::kNumVar + j_mod] + e_) ||
                                 H[j_mod] == H_pred[p * T::kNumVar + j_mod] + g_  ||
                    (extend_up = H[j_mod] == O_pred[p * T::kNumVar + j_mod] + c_) ||
                                 H[j_mod] == H_pred[p * T::kNumVar + j_mod] + q_) {
                    prev_i = predecessors[p];
                    prev_j = j;
                    predecessor_found = true;
                    break;
                }
            }
        }

        if (!predecessor_found) {
            if ((j_mod != 0 && ((extend_left = H[j_mod] == E[j_mod - 1] + e_)  ||
                                               H[j_mod] == H[j_mod - 1] + g_   ||
                                (extend_left = H[j_mod] == Q[j_mod - 1] + c_)  ||
                                               H[j_mod] == H[j_mod - 1] + q_)) ||
                (j_mod == 0 && ((extend_left = H[j_mod] == E_left[T::kNumVar - 1] + e_) ||
                                               H[j_mod] == H_left[T::kNumVar - 1] + g_  ||
                                (extend_left = H[j_mod] == Q_left[T::kNumVar - 1] + c_) ||
                                               H[j_mod] == H_left[T::kNumVar - 1] + q_))) {
                prev_i = i;
                prev_j = j - 1;
                predecessor_found = true;
            }
        }

        alignment.emplace_back(i == prev_i ? -1 : rank_to_node_id[i - 1],
            j == prev_j ? -1 : j);

        // update for next round
        load_next_segment = (i == prev_i ? false : true) ||
            (j != prev_j && prev_j % T::kNumVar == T::kNumVar - 1 ? true : false);

        i = prev_i;
        j = prev_j;
        j_div = j / T::kNumVar;
        j_mod = j % T::kNumVar;

        if (extend_left) {
            while (true) {
                // load
                if (j_mod == T::kNumVar - 1) {
                    _mmxxx_store_si(reinterpret_cast<__mxxxi*>(E),
                        pimpl_->E[i * matrix_width + j_div]);
                    _mmxxx_store_si(reinterpret_cast<__mxxxi*>(Q),
                        pimpl_->Q[i * matrix_width + j_div]);
                } else if (j_mod == 0) { // boarder case
                    if (j_div > 0) {
                        _mmxxx_store_si(reinterpret_cast<__mxxxi*>(E_left),
                            pimpl_->E[i * matrix_width + j_div - 1]);
                        _mmxxx_store_si(reinterpret_cast<__mxxxi*>(Q_left),
                            pimpl_->Q[i * matrix_width + j_div - 1]);
                    }
                }

                alignment.emplace_back(-1, j);
                --j;
                j_div = j / T::kNumVar;
                j_mod = j % T::kNumVar;
                if (j == -1 ||
                    (j_mod != T::kNumVar - 1 &&      E[j_mod] + e_ != E[j_mod + 1]) ||
                    (j_mod == T::kNumVar - 1 && E_left[j_mod] + e_ != E[0])         ||
                    (j_mod != T::kNumVar - 1 &&      Q[j_mod] + c_ != Q[j_mod + 1]) ||
                    (j_mod == T::kNumVar - 1 && Q_left[j_mod] + c_ != Q[0])) {
                    break;
                }
            }
            load_next_segment = true;
        } else if (extend_up) {
            while (true) {
                // load
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(F),
                    pimpl_->F[i * matrix_width + j_div]);
                _mmxxx_store_si(reinterpret_cast<__mxxxi*>(O),
                    pimpl_->O[i * matrix_width + j_div]);

                predecessors.clear();
                std::uint32_t store_pos = 0;
                for (const auto& it: graph->nodes()[rank_to_node_id[i - 1]]->in_edges()) {
                    predecessors.emplace_back(
                        pimpl_->node_id_to_rank[it->begin_node_id()] + 1);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&H_pred[store_pos * T::kNumVar]),
                        pimpl_->H[predecessors.back() * matrix_width + j_div]);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&F_pred[store_pos * T::kNumVar]),
                        pimpl_->F[predecessors.back() * matrix_width + j_div]);
                    _mmxxx_store_si(
                        reinterpret_cast<__mxxxi*>(&O_pred[store_pos * T::kNumVar]),
                        pimpl_->O[predecessors.back() * matrix_width + j_div]);
                    ++store_pos;
                }

                bool stop = true;
                prev_i = 0;
                for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                    if (F[j_mod] == F_pred[p * T::kNumVar + j_mod] + e_ ||
                        O[j_mod] == O_pred[p * T::kNumVar + j_mod] + c_) {
                        prev_i = predecessors[p];
                        stop = false;
                        break;
                    }
                }
                if (stop == true) {
                    for (std::uint32_t p = 0; p < predecessors.size(); ++p) {
                        if (F[j_mod] == H_pred[p * T::kNumVar + j_mod] + g_ ||
                            O[j_mod] == H_pred[p * T::kNumVar + j_mod] + q_) {
                            prev_i = predecessors[p];
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

    } while (true);

    delete[] backtrack_storage;

    // update alignment for NW (backtrack stops on first row or column)
    if (type_ == AlignmentType::kNW) {
        while (i == 0 && j != -1) {
            alignment.emplace_back(-1, j);
            --j;
        }
        while (i != 0 && j == -1) {
            alignment.emplace_back(rank_to_node_id[i - 1], -1);

            const auto& node = graph->nodes()[rank_to_node_id[i - 1]];
            if (node->in_edges().empty()) {
                i = 0;
            } else {
                for (const auto& edge: node->in_edges()) {
                    std::uint32_t pred_i =
                        pimpl_->node_id_to_rank[edge->begin_node_id()] + 1;
                    if (pimpl_->first_column[matrix_height + i]     == pimpl_->first_column[matrix_height + pred_i] + e_ ||
                        pimpl_->first_column[2 * matrix_height + i] == pimpl_->first_column[2 * matrix_height + pred_i] + c_ ) {
                        i = pred_i;
                        break;
                    }
                }
            }
        }
    }

    std::reverse(alignment.begin(), alignment.end());
    return alignment;
#else

    return Alignment();

#endif
}

}

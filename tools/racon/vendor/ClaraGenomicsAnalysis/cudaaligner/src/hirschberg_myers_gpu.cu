/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "hirschberg_myers_gpu.cuh"
#include <cassert>
#include "batched_device_matrices.cuh"
#include <claragenomics/cudaaligner/aligner.hpp>
#include <claragenomics/utils/cudautils.hpp>
#include <claragenomics/utils/mathutils.hpp>
#include <claragenomics/utils/limits.cuh>
#include <cstring>

namespace claragenomics
{

namespace cudaaligner
{

namespace hirschbergmyers
{

constexpr int32_t warp_size = 32;
constexpr int32_t word_size = sizeof(WordType) * CHAR_BIT;

inline __device__ WordType warp_leftshift_sync(uint32_t warp_mask, WordType v)
{
    const WordType x = __shfl_up_sync(warp_mask, v >> (word_size - 1), 1);
    v <<= 1;
    if (threadIdx.x != 0)
        v |= x;
    return v;
}

inline __device__ WordType warp_add_sync(uint32_t warp_mask, WordType a, WordType b)
{
    static_assert(sizeof(WordType) == 4, "This function assumes WordType to have 4 bytes.");
    static_assert(CHAR_BIT == 8, "This function assumes a char width of 8 bit.");
    const uint64_t ax = a;
    const uint64_t bx = b;
    uint64_t r        = ax + bx;
    uint32_t carry    = static_cast<uint32_t>(r >> 32);
    if (warp_mask == 1)
    {
        return static_cast<WordType>(r);
    }
    r &= 0xffff'ffffull;
    // TODO: I think due to the structure of the Myer blocks,
    // a carry cannot propagate over more than a single block.
    // I.e. a single carry propagation without the loop should be sufficient.
    while (__any_sync(warp_mask, carry))
    {
        uint32_t x = __shfl_up_sync(warp_mask, carry, 1);
        if (threadIdx.x != 0)
            r += x;
        carry = static_cast<uint32_t>(r >> 32);
        r &= 0xffff'ffffull;
    }
    return static_cast<WordType>(r);
}

__device__ int32_t myers_advance_block(uint32_t warp_mask, WordType highest_bit, WordType eq, WordType& pv, WordType& mv, int32_t carry_in)
{
    assert((pv & mv) == WordType(0));

    // Stage 1
    WordType xv = eq | mv;
    if (carry_in < 0)
        eq |= WordType(1);
    WordType xh = warp_add_sync(warp_mask, eq & pv, pv);
    xh          = (xh ^ pv) | eq;
    WordType ph = mv | (~(xh | pv));
    WordType mh = pv & xh;

    int32_t carry_out = ((ph & highest_bit) == WordType(0) ? 0 : 1) - ((mh & highest_bit) == WordType(0) ? 0 : 1);

    ph = warp_leftshift_sync(warp_mask, ph);
    mh = warp_leftshift_sync(warp_mask, mh);

    if (carry_in < 0)
        mh |= WordType(1);

    if (carry_in > 0)
        ph |= WordType(1);

    // Stage 2
    pv = mh | (~(xv | ph));
    mv = ph & xv;

    return carry_out;
}

inline __device__ int32_t get_myers_score(int32_t i, int32_t j, device_matrix_view<WordType> const& pv, device_matrix_view<WordType> const& mv, device_matrix_view<int32_t> const& score, WordType last_entry_mask)
{
    assert(i > 0); // row 0 is implicit, NW matrix is shifted by i -> i-1
    const int32_t word_idx = (i - 1) / word_size;
    const int32_t bit_idx  = (i - 1) % word_size;
    int32_t s              = score(word_idx, j);
    WordType mask          = (~WordType(1)) << bit_idx;
    if (word_idx == score.num_rows() - 1)
        mask &= last_entry_mask;
    s -= __popc(mask & pv(word_idx, j));
    s += __popc(mask & mv(word_idx, j));
    return s;
}

__device__ int32_t append_myers_backtrace(int8_t* path, device_matrix_view<WordType> const& pv, device_matrix_view<WordType> const& mv, device_matrix_view<int32_t> const& score, int32_t query_size)
{
    assert(threadIdx.x == 0);
    using nw_score_t = int32_t;
    assert(pv.num_rows() == score.num_rows());
    assert(mv.num_rows() == score.num_rows());
    assert(pv.num_cols() == score.num_cols());
    assert(mv.num_cols() == score.num_cols());
    assert(score.num_rows() == ceiling_divide(query_size, word_size));
    int32_t i = query_size;
    int32_t j = score.num_cols() - 1;

    const WordType last_entry_mask = query_size % word_size != 0 ? (WordType(1) << (query_size % word_size)) - 1 : ~WordType(0);

    nw_score_t myscore = score((i - 1) / word_size, j);
    int32_t pos        = 0;
    while (i > 0 && j > 0)
    {
        int8_t r               = 0;
        nw_score_t const above = i == 1 ? j : get_myers_score(i - 1, j, pv, mv, score, last_entry_mask);
        nw_score_t const diag  = i == 1 ? j - 1 : get_myers_score(i - 1, j - 1, pv, mv, score, last_entry_mask);
        nw_score_t const left  = get_myers_score(i, j - 1, pv, mv, score, last_entry_mask);
        if (left + 1 == myscore)
        {
            r       = static_cast<int8_t>(AlignmentState::insertion);
            myscore = left;
            --j;
        }
        else if (above + 1 == myscore)
        {
            r       = static_cast<int8_t>(AlignmentState::deletion);
            myscore = above;
            --i;
        }
        else
        {
            r       = (diag == myscore ? static_cast<int8_t>(AlignmentState::match) : static_cast<int8_t>(AlignmentState::mismatch));
            myscore = diag;
            --i;
            --j;
        }
        path[pos] = r;
        ++pos;
    }
    while (i > 0)
    {
        path[pos] = static_cast<int8_t>(AlignmentState::deletion);
        ++pos;
        --i;
    }
    while (j > 0)
    {
        path[pos] = static_cast<int8_t>(AlignmentState::insertion);
        ++pos;
        --j;
    }
    return pos;
}

inline __device__ void hirschberg_myers_fill_path_warp(int8_t*& path, int32_t* path_length, int32_t n, int8_t value)
{
    // TODO parallelize
    if (threadIdx.x == 0)
    {
        int8_t const* const path_end = path + n;
        while (path != path_end)
        {
            *path = value;
            ++path;
        }
        *path_length += n;
    }
}

__device__ WordType myers_generate_query_pattern(char x, char const* query, int32_t query_size, int32_t offset)
{
    // Sets a 1 bit at the position of every matching character
    assert(offset < query_size);
    const int32_t max_i = min(query_size - offset, word_size);
    WordType r          = 0;
    for (int32_t i = 0; i < max_i; ++i)
    {
        if (x == query[i + offset])
            r = r | (WordType(1) << i);
    }
    return r;
}

__device__ WordType myers_generate_query_pattern_reverse(char x, char const* query, int32_t query_size, int32_t offset)
{
    // Sets a 1 bit at the position of every matching character
    assert(offset < query_size);
    const int32_t max_i = min(query_size - offset, word_size);
    WordType r          = 0;
    // TODO make this a forward loop
    for (int32_t i = 0; i < max_i; ++i)
    {
        if (x == query[query_size - 1 - (i + offset)])
            r = r | (WordType(1) << i);
    }
    return r;
}

__device__ void myers_preprocess(device_matrix_view<WordType>& query_pattern, char const* query, int32_t query_size)
{
    const int32_t n_words = ceiling_divide(query_size, word_size);
    for (int32_t idx = threadIdx.x; idx < n_words; idx += warp_size)
    {
        // TODO query load is inefficient
        query_pattern(idx, 0) = myers_generate_query_pattern('A', query, query_size, idx * word_size);
        query_pattern(idx, 1) = myers_generate_query_pattern('C', query, query_size, idx * word_size);
        query_pattern(idx, 2) = myers_generate_query_pattern('T', query, query_size, idx * word_size);
        query_pattern(idx, 3) = myers_generate_query_pattern('G', query, query_size, idx * word_size);
        query_pattern(idx, 4) = myers_generate_query_pattern_reverse('A', query, query_size, idx * word_size);
        query_pattern(idx, 5) = myers_generate_query_pattern_reverse('C', query, query_size, idx * word_size);
        query_pattern(idx, 6) = myers_generate_query_pattern_reverse('T', query, query_size, idx * word_size);
        query_pattern(idx, 7) = myers_generate_query_pattern_reverse('G', query, query_size, idx * word_size);
    }
}

inline __device__ WordType get_query_pattern(device_matrix_view<WordType>& query_patterns, int32_t idx, int32_t query_begin_offset, char x, bool reverse)
{
    static_assert(std::is_unsigned<WordType>::value, "WordType has to be an unsigned type for well-defined >> operations.");
    const int32_t char_idx = [](char x) -> int32_t {
        int32_t r = x;
        return (r >> 1) & 0x3;
    }(x) + (reverse ? 4 : 0);

    // 4-bit word example:
    // query_patterns contains character match bit patterns "XXXX" for the full query string.
    // we want the bit pattern "yyyy" for a view of on the query string starting at eg. character 11:
    //       4    3    2     1      0 (pattern index)
    //    XXXX XXXX XXXX [XXXX] [XXXX]
    //     YYY Yyyy y
    //         1    0 (idx)
    //
    // query_begin_offset = 11
    // => idx_offset = 11/4 = 2, shift = 11%4 = 3

    const int32_t idx_offset = query_begin_offset / word_size;
    const int32_t shift      = query_begin_offset % word_size;

    WordType r = query_patterns(idx + idx_offset, char_idx);
    if (shift != 0)
    {
        r >>= shift;
        if (idx + idx_offset + 1 < query_patterns.num_rows())
        {
            r |= query_patterns(idx + idx_offset + 1, char_idx) << (word_size - shift);
        }
    }
    return r;
}

__device__ void
myers_compute_scores(
    device_matrix_view<WordType>& pv,
    device_matrix_view<WordType>& mv,
    device_matrix_view<int32_t>& score,
    device_matrix_view<WordType>& query_patterns,
    char const* target_begin,
    char const* target_end,
    char const* query_begin,
    char const* query_end,
    int32_t const pattern_idx_offset,
    bool full_score_matrix,
    bool reverse)
{
    assert(warpSize == warp_size);
    assert(threadIdx.x < warp_size);
    assert(blockIdx.x == 0);

    assert(query_end - query_begin > 0);
    assert(target_begin < target_end);

    const int32_t n_words     = ceiling_divide<int32_t>(query_end - query_begin, word_size);
    const int32_t target_size = target_end - target_begin;

    assert(pv.num_rows() == n_words);
    assert(mv.num_rows() == n_words);
    assert(score.num_rows() == full_score_matrix ? n_words : target_size + 1);
    assert(pv.num_cols() == full_score_matrix ? target_size + 1 : 1);
    assert(mv.num_cols() == full_score_matrix ? target_size + 1 : 1);
    assert(score.num_cols() == full_score_matrix ? target_size + 1 : 2);

    {
        for (int32_t idx = threadIdx.x; idx < n_words; idx += warp_size)
        {
            pv(idx, 0) = ~WordType(0);
            mv(idx, 0) = 0;
        }

        const int32_t query_size = query_end - query_begin;
        if (full_score_matrix)
        {
            for (int32_t idx = threadIdx.x; idx < n_words; idx += warp_size)
                score(idx, 0) = min((idx + 1) * word_size, query_size);
        }
        else
        {
            if (threadIdx.x == 0)
                score(0, reverse ? 1 : 0) = query_size;
            __syncwarp();
        }
    }

    for (int32_t t = 1; t <= target_size; ++t)
    {
        int32_t warp_carry = 0;
        if (threadIdx.x == 0)
            warp_carry = 1; // for global alignment the (implicit) first row has to be 0,1,2,3,... -> carry 1
        for (int32_t idx = threadIdx.x; idx < n_words; idx += warp_size)
        {
            const uint32_t warp_mask = idx / warp_size < n_words / warp_size ? 0xffff'ffffu : (1u << (n_words % warp_size)) - 1;

            WordType pv_local = pv(idx, full_score_matrix ? t - 1 : 0);
            WordType mv_local = mv(idx, full_score_matrix ? t - 1 : 0);
            // TODO these might be cached or only computed for the specific t at hand.
            const WordType highest_bit = WordType(1) << (idx == (n_words - 1) ? (query_end - query_begin) - (n_words - 1) * word_size - 1 : word_size - 1);

            const WordType eq = get_query_pattern(query_patterns, idx, pattern_idx_offset, target_begin[reverse ? target_size - t : t - 1], reverse);

            warp_carry = myers_advance_block(warp_mask, highest_bit, eq, pv_local, mv_local, warp_carry);
            if (full_score_matrix)
            {
                score(idx, t) = score(idx, t - 1) + warp_carry;
            }
            else
            {
                if (idx + 1 == n_words)
                    score(t, reverse ? 1 : 0) = score(t - 1, reverse ? 1 : 0) + warp_carry;
            }
            if (threadIdx.x == 0)
                warp_carry = 0;
            if (warp_mask == 0xffff'ffffu)
                warp_carry = __shfl_down_sync(0x8000'0001u, warp_carry, warp_size - 1);
            if (threadIdx.x != 0)
                warp_carry = 0;
            pv(idx, full_score_matrix ? t : 0) = pv_local;
            mv(idx, full_score_matrix ? t : 0) = mv_local;
        }
    }
}

__device__ void hirschberg_myers_compute_path(
    int8_t*& path,
    int32_t* path_length,
    batched_device_matrices<WordType>::device_interface* pvi,
    batched_device_matrices<WordType>::device_interface* mvi,
    batched_device_matrices<int32_t>::device_interface* scorei,
    device_matrix_view<WordType>& query_patterns,
    char const* target_begin,
    char const* target_end,
    char const* query_begin,
    char const* query_end,
    char const* query_begin_absolute,
    int32_t alignment_idx)
{
    assert(query_begin < query_end);
    const int32_t n_words             = ceiling_divide<int32_t>(query_end - query_begin, word_size);
    device_matrix_view<int32_t> score = scorei->get_matrix_view(alignment_idx, n_words, target_end - target_begin + 1);
    device_matrix_view<WordType> pv   = pvi->get_matrix_view(alignment_idx, n_words, target_end - target_begin + 1);
    device_matrix_view<WordType> mv   = mvi->get_matrix_view(alignment_idx, n_words, target_end - target_begin + 1);
    myers_compute_scores(pv, mv, score, query_patterns, target_begin, target_end, query_begin, query_end, query_begin - query_begin_absolute, true, false);
    __syncwarp();
    if (threadIdx.x == 0)
    {
        int32_t len = append_myers_backtrace(path, pv, mv, score, query_end - query_begin);
        path += len;
        *path_length += len;
    }
}

__device__ const char* hirschberg_myers_compute_target_mid_warp(
    batched_device_matrices<WordType>::device_interface* pvi,
    batched_device_matrices<WordType>::device_interface* mvi,
    batched_device_matrices<int32_t>::device_interface* scorei,
    device_matrix_view<WordType>& query_patterns,
    char const* target_begin,
    char const* target_end,
    char const* query_begin,
    char const* query_mid,
    char const* query_end,
    char const* query_begin_absolute,
    char const* query_end_absolute,
    int32_t alignment_idx)
{
    assert(query_begin <= query_mid);
    assert(query_mid < query_end);
    assert(target_begin < target_end);

    device_matrix_view<int32_t> score = scorei->get_matrix_view(alignment_idx, target_end - target_begin + 1, 2);

    if (query_begin < query_mid)
    {
        const int32_t n_words           = ceiling_divide<int32_t>(query_mid - query_begin, word_size);
        device_matrix_view<WordType> pv = pvi->get_matrix_view(alignment_idx, n_words, 2);
        device_matrix_view<WordType> mv = mvi->get_matrix_view(alignment_idx, n_words, 2);
        myers_compute_scores(pv, mv, score, query_patterns, target_begin, target_end, query_begin, query_mid, query_begin - query_begin_absolute, false, false);
    }
    else
    {
        const int32_t target_size = (target_end - target_begin);
        for (int32_t t = threadIdx.x; t <= target_size; t += warp_size)
        {
            score(t, 0) = t;
        }
        __syncwarp();
    }

    {
        const int32_t n_words           = ceiling_divide<int32_t>(query_end - query_mid, word_size);
        device_matrix_view<WordType> pv = pvi->get_matrix_view(alignment_idx, n_words, 2);
        device_matrix_view<WordType> mv = mvi->get_matrix_view(alignment_idx, n_words, 2);
        myers_compute_scores(pv, mv, score, query_patterns, target_begin, target_end, query_mid, query_end, query_end_absolute - query_end, false, true);
    }

    const int32_t target_size = (target_end - target_begin);
    int32_t midpoint          = 0;
    nw_score_t cur_min        = numeric_limits<nw_score_t>::max();
    for (int32_t t = threadIdx.x; t <= target_size; t += warp_size)
    {
        nw_score_t sum = score(t, 0) + score(target_size - t, 1);
        if (sum < cur_min)
        {
            cur_min  = sum;
            midpoint = t;
        }
    }
#pragma unroll
    for (int32_t i = 16; i > 0; i >>= 1)
    {
        const int32_t mv = __shfl_down_sync(0xffff'ffff, cur_min, i);
        const int32_t mp = __shfl_down_sync(0xffff'ffff, midpoint, i);
        if (mv < cur_min)
        {
            cur_min  = mv;
            midpoint = mp;
        }
    }
    __shfl_sync(0xffff'ffff, midpoint, 0);
    return target_begin + midpoint;
}

__device__ void hirschberg_myers_single_char_warp(int8_t*& path, int32_t* path_length, char query_char, char const* target_begin, char const* target_end)
{
    // TODO parallelize
    if (threadIdx.x == 0)
    {
        char const* t = target_end - 1;
        while (t >= target_begin)
        {
            if (*t == query_char)
            {
                *path = static_cast<int8_t>(AlignmentState::match);
                ++path;
                --t;
                break;
            }
            *path = static_cast<int8_t>(AlignmentState::insertion);
            ++path;
            --t;
        }
        if (*(path - 1) != static_cast<int8_t>(AlignmentState::match))
        {
            *(path - 1) = static_cast<int8_t>(AlignmentState::mismatch);
        }
        while (t >= target_begin)
        {
            *path = static_cast<int8_t>(AlignmentState::insertion);
            ++path;
            --t;
        }
        *path_length += target_end - target_begin;
    }
}

template <typename T>
class warp_shared_stack
{
public:
    __device__ warp_shared_stack(T* buffer_begin, T* buffer_end)
        : buffer_begin_(buffer_begin)
        , cur_end_(buffer_begin)
        , buffer_end_(buffer_end)
    {
        assert(buffer_begin_ < buffer_end_);
    }

    __device__ bool inline push(T const& t, unsigned warp_mask = 0xffff'ffff)
    {
        if (buffer_end_ - cur_end_ >= 1)
        {
            __syncwarp(warp_mask);
            if (threadIdx.x == 0)
            {
                *cur_end_ = t;
            }
            __syncwarp(warp_mask);
            ++cur_end_;
            return true;
        }
        else
        {
            if (threadIdx.x == 0)
            {
                printf("ERROR: stack full!");
            }
            return false;
        }
    }

    __device__ inline void pop()
    {
        assert(cur_end_ > buffer_begin_);
        if (cur_end_ - 1 >= buffer_begin_)
            --cur_end_;
    }

    __device__ inline T back() const
    {
        assert(cur_end_ - 1 >= buffer_begin_);
        return *(cur_end_ - 1);
    }

    __device__ inline bool empty() const
    {
        return buffer_begin_ == cur_end_;
    }

private:
    T* buffer_begin_;
    T* cur_end_;
    T* buffer_end_;
};

__device__ void hirschberg_myers(
    query_target_range* stack_buffer_begin,
    query_target_range* stack_buffer_end,
    int8_t*& path,
    int32_t* path_length,
    int32_t full_myers_threshold,
    batched_device_matrices<WordType>::device_interface* pvi,
    batched_device_matrices<WordType>::device_interface* mvi,
    batched_device_matrices<int32_t>::device_interface* scorei,
    device_matrix_view<WordType>& query_patterns,
    char const* target_begin_absolute,
    char const* target_end_absolute,
    char const* query_begin_absolute,
    char const* query_end_absolute,
    int32_t alignment_idx)
{
    assert(blockDim.x == warp_size);
    assert(blockDim.z == 1);
    assert(query_begin_absolute <= query_end_absolute);
    assert(target_begin_absolute <= target_end_absolute);

    warp_shared_stack<query_target_range> stack(stack_buffer_begin, stack_buffer_end);
    stack.push({query_begin_absolute, query_end_absolute, target_begin_absolute, target_end_absolute});

    assert(pvi->get_max_elements_per_matrix() == mvi->get_max_elements_per_matrix());
    assert(scorei->get_max_elements_per_matrix() >= pvi->get_max_elements_per_matrix());

    bool success   = true;
    int32_t length = 0;
    while (success && !stack.empty())
    {
        query_target_range e = stack.back();
        stack.pop();
        assert(e.query_begin <= e.query_end);
        assert(e.target_begin <= e.target_end);
        if (e.target_begin == e.target_end)
        {
            hirschberg_myers_fill_path_warp(path, &length, e.query_end - e.query_begin, static_cast<int8_t>(AlignmentState::deletion));
        }
        else if (e.query_begin == e.query_end)
        {
            hirschberg_myers_fill_path_warp(path, &length, e.target_end - e.target_begin, static_cast<int8_t>(AlignmentState::insertion));
        }
        else if (e.query_begin + 1 == e.query_end)
        {
            hirschberg_myers_single_char_warp(path, &length, *e.query_begin, e.target_begin, e.target_end);
        }
        else
        {
            if (e.query_end - e.query_begin < full_myers_threshold && e.query_end != e.query_begin)
            {
                const int32_t n_words = ceiling_divide<int32_t>(e.query_end - e.query_begin, word_size);
                if ((e.target_end - e.target_begin + 1) * n_words <= pvi->get_max_elements_per_matrix())
                {
                    hirschberg_myers_compute_path(path, &length, pvi, mvi, scorei, query_patterns, e.target_begin, e.target_end, e.query_begin, e.query_end, query_begin_absolute, alignment_idx);
                    continue;
                }
            }

            const char* query_mid  = e.query_begin + (e.query_end - e.query_begin) / 2;
            const char* target_mid = hirschberg_myers_compute_target_mid_warp(pvi, mvi, scorei, query_patterns, e.target_begin, e.target_end, e.query_begin, query_mid, e.query_end, query_begin_absolute, query_end_absolute, alignment_idx);
            success                = success && stack.push({e.query_begin, query_mid, e.target_begin, target_mid});
            success                = success && stack.push({query_mid, e.query_end, target_mid, e.target_end});
        }
    }
    if (!success)
        length = 0;
    if (threadIdx.x == 0)
        *path_length = length;
}

__global__ void hirschberg_myers_compute_alignment(
    query_target_range* stack_buffer_base,
    int32_t stack_buffer_size_per_alignment,
    int32_t full_myers_threshold,
    int8_t* paths_base,
    int32_t* path_lengths,
    int32_t max_path_length,
    batched_device_matrices<WordType>::device_interface* pvi,
    batched_device_matrices<WordType>::device_interface* mvi,
    batched_device_matrices<int32_t>::device_interface* scorei,
    batched_device_matrices<WordType>::device_interface* query_patternsi,
    char const* sequences_d, int32_t const* sequence_lengths_d,
    int32_t max_sequence_length,
    int32_t n_alignments)
{
    assert(blockDim.x == warp_size);
    assert(blockDim.z == 1);

    const int32_t alignment_idx = blockIdx.z;
    if (alignment_idx >= n_alignments)
        return;

    const char* const query_begin               = sequences_d + 2 * alignment_idx * max_sequence_length;
    const char* const target_begin              = sequences_d + (2 * alignment_idx + 1) * max_sequence_length;
    const char* const query_end                 = query_begin + sequence_lengths_d[2 * alignment_idx];
    const char* const target_end                = target_begin + sequence_lengths_d[2 * alignment_idx + 1];
    int8_t* path                                = paths_base + alignment_idx * max_path_length;
    query_target_range* stack_buffer_begin      = stack_buffer_base + alignment_idx * stack_buffer_size_per_alignment;
    device_matrix_view<WordType> query_patterns = query_patternsi->get_matrix_view(alignment_idx, ceiling_divide<int32_t>(query_end - query_begin, word_size), 8);
    myers_preprocess(query_patterns, query_begin, query_end - query_begin);
    hirschberg_myers(stack_buffer_begin, stack_buffer_begin + stack_buffer_size_per_alignment, path, path_lengths + alignment_idx, full_myers_threshold, pvi, mvi, scorei, query_patterns, target_begin, target_end, query_begin, query_end, alignment_idx);
}

} // namespace hirschbergmyers

void hirschberg_myers_gpu(device_buffer<hirschbergmyers::query_target_range>& stack_buffer,
                          int32_t stack_buffer_size_per_alignment,
                          int8_t* paths_d, int32_t* path_lengths_d, int32_t max_path_length,
                          char const* sequences_d,
                          int32_t const* sequence_lengths_d,
                          int32_t max_sequence_length,
                          int32_t n_alignments,
                          batched_device_matrices<hirschbergmyers::WordType>& pv,
                          batched_device_matrices<hirschbergmyers::WordType>& mv,
                          batched_device_matrices<int32_t>& score,
                          batched_device_matrices<hirschbergmyers::WordType>& query_patterns,
                          int32_t switch_to_myers_threshold,
                          cudaStream_t stream)
{
    using hirschbergmyers::warp_size;

    const dim3 threads(warp_size, 1, 1);
    const dim3 blocks(1, 1, ceiling_divide<int32_t>(n_alignments, threads.z));
    hirschbergmyers::hirschberg_myers_compute_alignment<<<blocks, threads, 0, stream>>>(stack_buffer.data(), stack_buffer_size_per_alignment, switch_to_myers_threshold, paths_d, path_lengths_d, max_path_length, pv.get_device_interface(), mv.get_device_interface(), score.get_device_interface(), query_patterns.get_device_interface(), sequences_d, sequence_lengths_d, max_sequence_length, n_alignments);
}

} // namespace cudaaligner
} // namespace claragenomics

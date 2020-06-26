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

#include "matrix_cpu.hpp"

#include <claragenomics/utils/mathutils.hpp>
#include <claragenomics/cudaaligner/cudaaligner.hpp>

#include <limits>
#include <cassert>
#include <tuple>
#include <algorithm>

namespace claragenomics
{

namespace cudaaligner
{

std::tuple<int, int> to_band_indices(int i, int j, int p)
{
    int const kd = (j - i + p) / 2;
    int const l  = (j + i);
    return std::make_tuple(kd, l);
}

std::tuple<int, int> to_matrix_indices(int kd, int l, int p)
{
    int const j = kd - (p + l) / 2 + l;
    int const i = l - j;
    return std::make_tuple(i, j);
}

int pos(int i, int j)
{
    return 1000 * i + j;
}

std::vector<int8_t> ukkonen_backtrace(matrix<int> const& scores, int n, int m, int p)
{
    // Using scoring schema from cudaaligner.hpp
    // Match = 0
    // Mismatch = 1
    // Insertion = 2
    // Deletion = 3

    using std::get;
    constexpr int max = std::numeric_limits<int>::max() - 1;
    std::vector<int8_t> res;

    int i = m - 1;
    int j = n - 1;

    int k, l;
    std::tie(k, l) = to_band_indices(i, j, p);
    int myscore    = scores(k, l);
    while (i > 0 && j > 0)
    {
        char r          = 0;
        std::tie(k, l)  = to_band_indices(i - 1, j, p);
        int const above = k < 0 || k >= scores.num_rows() || l < 0 || l >= scores.num_cols() ? max : scores(k, l);
        std::tie(k, l)  = to_band_indices(i - 1, j - 1, p);
        int const diag  = k < 0 || k >= scores.num_rows() || l < 0 || l >= scores.num_cols() ? max : scores(k, l);
        std::tie(k, l)  = to_band_indices(i, j - 1, p);
        int const left  = k < 0 || k >= scores.num_rows() || l < 0 || l >= scores.num_cols() ? max : scores(k, l);
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
        res.push_back(r);
    }
    while (i > 0)
    {
        res.push_back(static_cast<int8_t>(AlignmentState::deletion));
        --i;
    }
    while (j > 0)
    {
        res.push_back(static_cast<int8_t>(AlignmentState::insertion));
        --j;
    }
    std::reverse(res.begin(), res.end());
    return res;
}

void ukkonen_build_score_matrix_odd(matrix<int>& scores, char const* target, int n, char const* query, int m, int p, int l, int kdmax)
{
    constexpr int max = std::numeric_limits<int>::max() - 1;
    int const bw      = (1 + n - m + 2 * p + 1) / 2;
    for (int kd = 0; kd <= (kdmax - 1) / 2; ++kd)
    {
        int const lmin = abs(2 * kd + 1 - p);
        int const lmax = 2 * kd + 1 <= p ? 2 * (m - p + 2 * kd + 1) + lmin : (2 * std::min(m, n - (2 * kd + 1) + p) + lmin);
        if (lmin + 1 <= l && l < lmax)
        {
            int const rk    = kd;
            int const rl    = l;
            int const j     = kd - (p + l) / 2 + l;
            int const i     = l - j;
            int const diag  = rl - 2 < 0 ? max : scores(rk, rl - 2) + (query[i - 1] == target[j - 1] ? 0 : 1);
            int const left  = rl - 1 < 0 ? max : scores(rk, rl - 1) + 1;
            int const above = rl - 1 < 0 || rk + 1 >= bw ? max : scores(rk + 1, rl - 1) + 1;
            scores(rk, rl)  = min3(diag, left, above);
        }
    }
}
void ukkonen_build_score_matrix_even(matrix<int>& scores, char const* target, int n, char const* query, int m, int p, int l, int kdmax)
{
    constexpr int max = std::numeric_limits<int>::max() - 1;
    for (int kd = 0; kd <= kdmax / 2; ++kd)
    {
        int const lmin = abs(2 * kd - p);
        int const lmax = 2 * kd <= p ? 2 * (m - p + 2 * kd) + lmin : (2 * std::min(m, n - 2 * kd + p) + lmin);
        if (lmin + 1 <= l && l < lmax)
        {
            int const rk    = kd;
            int const rl    = l;
            int const j     = kd - (p + l) / 2 + l;
            int const i     = l - j;
            int const left  = rk - 1 < 0 || rl - 1 < 0 ? max : scores(rk - 1, rl - 1) + 1;
            int const diag  = rl - 2 < 0 ? max : scores(rk, rl - 2) + (query[i - 1] == target[j - 1] ? 0 : 1);
            int const above = rl - 1 < 0 ? max : scores(rk, rl - 1) + 1;
            scores(rk, rl)  = min3(left, diag, above);
        }
    }
}

matrix<int> ukkonen_build_score_matrix(std::string const& target, std::string const& query, int p)
{
    constexpr int max = std::numeric_limits<int>::max() - 1;
    assert(target.size() >= query.size());
    int const n = target.size() + 1;
    int const m = query.size() + 1;

    int const bw = (1 + n - m + 2 * p + 1) / 2;

    matrix<int> scores(bw, n + m, max);
    scores(0, 0) = 0;
    for (int i = 0; i <= p; ++i)
    {
        int k, l;
        std::tie(k, l) = to_band_indices(i, 0, p);
        scores(k, l)   = i;
    }
    for (int j = 0; j <= (n - m) + p; ++j)
    {
        int k, l;
        std::tie(k, l) = to_band_indices(0, j, p);
        scores(k, l)   = j;
    }

    // Transform to diagonal coordinates
    // (i,j) -> (k=j-i, l=(j+i)/2)
    // where
    // -p <= k <= (n-m)+p
    // abs(k)/2 <= l < (k <= 0 ? m+k : min(m,n-k)
    // shift by p: kd = (k + p)/2, (k + p)/2+1
    int const kdmax = (n - m) + 2 * p;
    for (int lx = 0; lx < n + m; ++lx)
    {
        if (p % 2 == 0)
        {
            ukkonen_build_score_matrix_even(scores, target.c_str(), n, query.c_str(), m, p, 2 * lx, kdmax);
            ukkonen_build_score_matrix_odd(scores, target.c_str(), n, query.c_str(), m, p, 2 * lx + 1, kdmax);
        }
        else
        {
            ukkonen_build_score_matrix_odd(scores, target.c_str(), n, query.c_str(), m, p, 2 * lx, kdmax);
            ukkonen_build_score_matrix_even(scores, target.c_str(), n, query.c_str(), m, p, 2 * lx + 1, kdmax);
        }
    }
    return scores;
}

matrix<int> ukkonen_build_score_matrix_old(std::string const& target, std::string const& query, int t)
{
    assert(target.size() >= query.size());
    int const n = target.size() + 1;
    int const m = query.size() + 1;

    int const p = (t - (n - m)) / 2;

    matrix<int> scores(m, n, 999);
    scores(0, 0) = 0;
    for (int i = 0; i < m; ++i)
        scores(i, 0) = i;
    for (int j = 0; j < n; ++j)
        scores(0, j) = j;

    // Transform to diagonal coordinates
    // (i,j) -> (k=j-i, l=(j+i)/2)
    // where
    // -p <= k <= (n-m)+p
    // abs(k)/2 <= l < (k <= 0 ? m+k : min(m,n-k)
    // shift by p: kd = k + p
    int const kdmax = (n - m) + 2 * p;
    for (int kd = 0; kd <= kdmax; ++kd)
    {
        int const lmin = abs(kd - p) / 2;
        int const lmax = kd <= p ? 2 * (m + kd - p) + lmin : (std::min(m, n - kd + p) + lmin);
        for (int l = lmin; l < lmax; ++l)
        {
            int const kfloor = (kd + p) / 2 - p; // = (k+2*p) - p; to round to -infty for -p <= k <= (n-m)+p
            int const i      = l - kfloor;
            int const j      = l + kd - p - kfloor;
            scores(i, j)     = min3(
                scores(i - 1, j) + 1,
                scores(i, j - 1) + 1,
                scores(i - 1, j - 1) + (query[i - 1] == target[j - 1] ? 0 : 1));
        }
    }
    return scores;
}

std::vector<int8_t> ukkonen_cpu(std::string const& target, std::string const& query, int const p)
{
    int const n        = target.size() + 1;
    int const m        = query.size() + 1;
    matrix<int> scores = ukkonen_build_score_matrix(target, query, p);
    std::vector<int8_t> result;
    result = ukkonen_backtrace(scores, n, m, p);
    return result;
}

} // namespace cudaaligner
} // namespace claragenomics

/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "needleman_wunsch_cpu.hpp"

#include <claragenomics/cudaaligner/cudaaligner.hpp>
#include <claragenomics/utils/mathutils.hpp>

#include <tuple>
#include <cassert>
#include <algorithm>

namespace claragenomics
{

namespace cudaaligner
{

int find_alignment_position(matrix<int> const& scores)
{
    int const last_i = scores.num_rows() - 1;
    int min_score    = std::numeric_limits<int>::max();
    int best_pos     = 0;
    for (int j = 0; j < scores.num_cols(); ++j)
    {
        if (scores(last_i, j) < min_score)
        {
            min_score = scores(last_i, j);
            best_pos  = j;
        }
    }
    return best_pos;
}

std::tuple<int, std::vector<int8_t>> needleman_wunsch_backtrace_old(matrix<int> const& scores)
{
    using std::get;
    std::tuple<int, std::vector<int8_t>> res;
    int best_pos = find_alignment_position(scores);
    //
    //    int i = 0;
    //    int j = 0;
    //    if(best_pos < 0)
    //    {
    //        i = -best_pos;
    //        j = scores.num_cols()-1;
    //    }
    //    else
    //    {
    //        i = scores.num_rows()-1;
    //        j = best_pos;
    //    }
    //
    int i       = scores.num_rows() - 1;
    int j       = scores.num_cols() - 1;
    get<0>(res) = best_pos;
    get<1>(res).reserve(std::max(scores.num_rows(), scores.num_cols()));
    int myscore = scores(i, j);
    while (i > 0 && j > 0)
    {
        int8_t r        = 0;
        int const above = scores(i - 1, j);
        int const diag  = scores(i - 1, j - 1);
        int const left  = scores(i, j - 1);
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
        get<1>(res).push_back(r);
    }
    while (i > 0)
    {
        get<1>(res).push_back(static_cast<int8_t>(AlignmentState::deletion));
        --i;
    }
    while (j > 0)
    {
        get<1>(res).push_back(static_cast<int8_t>(AlignmentState::insertion));
        --j;
    }
    reverse(get<1>(res).begin(), get<1>(res).end());
    return res;
}

matrix<int> needleman_wunsch_build_score_matrix_naive(std::string const& text, std::string const& query)
{
    int const text_size  = text.size() + 1;
    int const query_size = query.size() + 1;
    matrix<int> scores(query_size, text_size);

    for (int i = 0; i < query_size; ++i)
        scores(i, 0) = i;
    for (int j = 0; j < text_size; ++j)
        scores(0, j) = j;

    for (int j = 1; j < text_size; ++j)
        for (int i = 1; i < query_size; ++i)
        {
            scores(i, j) = min3(
                scores(i - 1, j) + 1,
                scores(i, j - 1) + 1,
                scores(i - 1, j - 1) + (query[i - 1] == text[j - 1] ? 0 : 1));
        }

    return scores;
}

matrix<int> needleman_wunsch_build_score_matrix_diagonal(std::string const& text, std::string const& query)
{
    int const query_size = query.size() + 1;
    int const text_size  = text.size() + 1;
    assert(query_size <= text_size);
    matrix<int> scores(query_size, text_size);

    for (int i = 0; i < query_size; ++i)
        scores(i, 0) = i;
    for (int j = 0; j < text_size; ++j)
        scores(0, j) = j;

    for (int k = 1; k < query_size; ++k)
    {
        int const jmax = std::min(k, text_size);
        for (int j = 1; j < jmax; ++j)
        {
            int const i  = k - j;
            scores(i, j) = min3(
                scores(i - 1, j) + 1,
                scores(i, j - 1) + 1,
                scores(i - 1, j - 1) + (query[i - 1] == text[j - 1] ? 0 : 1));
        }
    }

    for (int l = 1; l < text_size; ++l)
    {
        int const imax = std::min(text_size - l, query_size - 1);
        for (int k = 0; k < imax; ++k)
        {
            int const i  = query_size - k - 1;
            int const j  = l + k;
            scores(i, j) = min3(
                scores(i - 1, j) + 1,
                scores(i, j - 1) + 1,
                scores(i - 1, j - 1) + (query[i - 1] == text[j - 1] ? 0 : 1));
        }
    }
    return scores;
}

std::vector<int8_t> needleman_wunsch_cpu(std::string const& text, std::string const& query)
{
    matrix<int> scores = needleman_wunsch_build_score_matrix_naive(text, query);
    return std::get<1>(needleman_wunsch_backtrace_old(scores));
}

} // namespace cudaaligner
} // namespace claragenomics

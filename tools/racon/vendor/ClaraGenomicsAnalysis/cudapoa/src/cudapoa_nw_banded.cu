/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "cudapoa_kernels.cuh"
#include "cudastructs.cuh"

#include <claragenomics/utils/cudautils.hpp>

#include <stdio.h>

namespace claragenomics
{

namespace cudapoa
{

__device__ uint16_t get_band_start_for_row(uint16_t row_idx, float gradient, uint16_t band_width, uint16_t max_column)
{

    int16_t start_pos = uint16_t(row_idx * gradient) - band_width / 2;

    start_pos = max(start_pos, 0);

    int16_t end_pos = start_pos + band_width;

    if (end_pos > max_column)
    {
        start_pos = max_column - band_width + CELLS_PER_THREAD;
    };

    start_pos = max(start_pos, 0);

    start_pos = start_pos - (start_pos % CELLS_PER_THREAD);

    return uint16_t(start_pos);
}

__device__ int16_t* get_score_ptr(int16_t* scores, uint16_t row, uint16_t column, float gradient, uint16_t band_width, uint16_t max_column)
{

    uint16_t band_start = get_band_start_for_row(row, gradient, band_width, max_column);

    uint16_t col_idx;

    if (column == 0)
    {
        col_idx = band_start;
    }
    else
    {
        col_idx = column - band_start;
    }

    return &scores[(col_idx) + row * CUDAPOA_BANDED_MAX_MATRIX_SEQUENCE_DIMENSION];
};

__device__ void set_score(int16_t* scores, uint16_t row, uint16_t column, int16_t value, float gradient, uint16_t band_width, uint16_t max_column)
{
    uint16_t band_start = get_band_start_for_row(row, gradient, band_width, max_column);

    uint16_t col_idx;
    if (column == 0)
    {
        col_idx = band_start;
    }
    else
    {
        col_idx = column - band_start;
    }

    scores[col_idx + row * CUDAPOA_BANDED_MAX_MATRIX_SEQUENCE_DIMENSION] = value;
}

__device__ void initialize_band(int16_t* scores, uint16_t row, int16_t value, float gradient, uint16_t band_width, uint16_t max_column)
{
    int32_t lane_idx    = threadIdx.x % WARP_SIZE;
    uint16_t band_start = get_band_start_for_row(row, gradient, band_width, max_column);
    uint16_t band_end   = band_start + band_width;

    uint16_t initialization_offset = (band_start == 0) ? 1 : band_start;

    set_score(scores, row, initialization_offset, value, gradient, band_width, max_column);

    for (uint16_t j = lane_idx + band_end; j < band_end + CUDAPOA_BANDED_MATRIX_RIGHT_PADDING; j += WARP_SIZE)
    {
        set_score(scores, row, j, value, gradient, band_width, max_column);
    }
};

__device__ int16_t get_score(int16_t* scores, uint16_t row, uint16_t column, float gradient, uint16_t bandwidth, uint16_t max_column, int16_t out_of_band_score_offset)
{
    uint16_t band_start = get_band_start_for_row(row, gradient, bandwidth, max_column);
    uint16_t band_end   = band_start + bandwidth;

    if (((column > band_end) || (column < band_start)) && column != 0)
    {
        return SHRT_MIN + out_of_band_score_offset;
    }
    else
    {
        return *get_score_ptr(scores, row, column, gradient, bandwidth, max_column);
    }
}

template <typename ScoreT>
__device__ ScoreT4<ScoreT> get_scores(uint16_t read_pos,
                                      ScoreT* scores,
                                      uint16_t node,
                                      ScoreT gap_score,
                                      ScoreT4<ScoreT> char_profile,
                                      float gradient,
                                      uint16_t bandwidth,
                                      int16_t default_value,
                                      uint16_t max_column)
{

    // The load instructions typically load data in 4B or 8B chunks.
    // If data is 16b (2B), then a 4B load chunk is loaded into register
    // and the necessary bits are extracted before returning. This wastes cycles
    // as each read of 16b issues a separate load command.
    // Instead it is better to load a 4B or 8B chunk into a register
    // using a single load inst, and then extracting necessary part of
    // of the data using bit arithmatic. Also reduces register count.

    uint16_t band_start = get_band_start_for_row(node, gradient, bandwidth, max_column);

    uint16_t band_end = band_start + bandwidth + CELLS_PER_THREAD;

    if (((read_pos + 1 > band_end) || (read_pos + 1 < band_start)) && read_pos + 1 != 0)
    {
        return ScoreT4<ScoreT>{default_value, default_value, default_value, default_value};
    }
    else
    {
        ScoreT4<ScoreT>* pred_scores = (ScoreT4<ScoreT>*)get_score_ptr(scores, node, read_pos, gradient, bandwidth, max_column);

        // loads 8 consecutive bytes (4 shorts)
        ScoreT4<ScoreT> score4 = pred_scores[0];

        // need to load the next chunk of memory as well
        ScoreT4<ScoreT> score4_next = pred_scores[1];

        ScoreT4<int16_t> score;

        score.s0 = max(score4.s0 + char_profile.s0,
                       score4.s1 + gap_score);
        score.s1 = max(score4.s1 + char_profile.s1,
                       score4.s2 + gap_score);
        score.s2 = max(score4.s2 + char_profile.s2,
                       score4.s3 + gap_score);
        score.s3 = max(score4.s3 + char_profile.s3,
                       score4_next.s0 + gap_score);

        return score;
    }
}

template <typename SeqT,
          typename IndexT,
          typename ScoreT>
__device__
    uint16_t
    runNeedlemanWunschBanded(SeqT* nodes,
                             uint16_t* graph,
                             uint16_t* node_id_to_pos,
                             uint16_t graph_count,
                             uint16_t* incoming_edge_count,
                             uint16_t* incoming_edges,
                             uint16_t* outgoing_edge_count,
                             uint16_t* outgoing_edges,
                             SeqT* read,
                             uint16_t read_length,
                             ScoreT* scores,
                             int16_t* alignment_graph,
                             int16_t* alignment_read,
                             ScoreT gap_score,
                             ScoreT mismatch_score,
                             ScoreT match_score)
{
    const ScoreT min_score_abs = abs(min(min(gap_score, mismatch_score), match_score) - 1);
    int32_t lane_idx           = threadIdx.x % WARP_SIZE;

    //Calculate gradient for the scores matrix
    float gradient = float(read_length + 1) / float(graph_count + 1);

    uint16_t band_width = WARP_SIZE * CELLS_PER_THREAD;

    uint16_t max_column = read_length + 1;

    // Initialise the horizontal boundary of the score matrix
    for (IndexT j = lane_idx; j < CUDAPOA_BANDED_MAX_MATRIX_SEQUENCE_DIMENSION; j += WARP_SIZE)
    {
        set_score(scores, 0, j, j * gap_score, gradient, band_width, max_column);
    }

    // Initialise the vertical boundary of the score matrix
    if (lane_idx == 0)
    {
#ifdef NW_VERBOSE_PRINT
        printf("graph %d, read %d\n", graph_count, read_length);
#endif

        for (IndexT graph_pos = 0; graph_pos < graph_count; graph_pos++)
        {

            set_score(scores, 0, 0, 0, gradient, band_width, max_column);

            uint16_t node_id = graph[graph_pos];
            IndexT i         = graph_pos + 1;

            uint16_t pred_count = incoming_edge_count[node_id];
            if (pred_count == 0)
            {
                set_score(scores, i, 0, gap_score, gradient, band_width, max_column);
            }
            else
            {
                ScoreT penalty = SHRT_MIN;
                for (uint16_t p = 0; p < pred_count; p++)
                {
                    uint16_t pred_node_id        = incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES + p];
                    uint16_t pred_node_graph_pos = node_id_to_pos[pred_node_id] + 1;
                    penalty                      = max(penalty, get_score(scores, pred_node_graph_pos, 0, gradient, band_width, read_length + 1, min_score_abs));
                }
                set_score(scores, i, 0, penalty + gap_score, gradient, band_width, max_column);
            }
        }
    }

    __syncwarp();

    SeqT4<SeqT>* d_read4 = (SeqT4<SeqT>*)read;
    // compute vertical and diagonal values in parallel.
    for (uint16_t graph_pos = 0; graph_pos < graph_count; graph_pos++)
    {

        uint16_t node_id    = graph[graph_pos];
        uint16_t score_gIdx = graph_pos + 1;

        uint16_t band_start = get_band_start_for_row(score_gIdx, gradient, band_width, read_length + 1);

        initialize_band(scores, score_gIdx, SHRT_MIN + min_score_abs, gradient, band_width, read_length + 1);

        ScoreT first_element_prev_score = get_score(scores, score_gIdx, 0, gradient, band_width, read_length + 1, min_score_abs);

        uint16_t pred_count = incoming_edge_count[node_id];

        uint16_t pred_idx = (pred_count == 0 ? 0 : node_id_to_pos[incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES]] + 1);

        SeqT graph_base = nodes[node_id];

        uint16_t read_pos = lane_idx * CELLS_PER_THREAD + band_start;
        {
            IndexT rIdx       = read_pos / CELLS_PER_THREAD;
            SeqT4<SeqT> read4 = d_read4[rIdx];

            ScoreT4<ScoreT> char_profile;
            char_profile.s0 = (graph_base == read4.r0 ? match_score : mismatch_score);
            char_profile.s1 = (graph_base == read4.r1 ? match_score : mismatch_score);
            char_profile.s2 = (graph_base == read4.r2 ? match_score : mismatch_score);
            char_profile.s3 = (graph_base == read4.r3 ? match_score : mismatch_score);

            ScoreT4<ScoreT> score = get_scores(read_pos, scores, pred_idx, gap_score, char_profile, gradient, band_width, SHRT_MIN + min_score_abs, read_length + 1);

            // Perform same score updates as above, but for rest of predecessors.
            for (uint16_t p = 1; p < pred_count; p++)
            {
                int16_t pred_idx2         = node_id_to_pos[incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES + p]] + 1;
                ScoreT4<int16_t> scores_4 = get_scores(read_pos, scores, pred_idx2, gap_score, char_profile, gradient, band_width, SHRT_MIN + min_score_abs, read_length + 1);

                score.s0 = max(score.s0, scores_4.s0);
                score.s1 = max(score.s1, scores_4.s1);
                score.s2 = max(score.s2, scores_4.s2);
                score.s3 = max(score.s3, scores_4.s3);
            }

            // While there are changes to the horizontal score values, keep updating the matrix.
            // So loop will only run the number of time there are corrections in the matrix.
            // The any_sync warp primitive lets us easily check if any of the threads had an update.
            bool loop = true;

            while (__any_sync(FULL_MASK, loop))
            {

                // To increase instruction level parallelism, we compute the scores
                // in reverse order (score3 first, then score2, then score1, etc).
                // And then check if any of the scores had an update,
                // and if there's an update then we rerun the loop to capture the effects
                // of the change in the next loop.
                loop = false;

                // The shfl_up lets us grab a value from the lane below.
                ScoreT last_score = __shfl_up_sync(FULL_MASK, score.s3, 1);
                if (lane_idx == 0)
                {
                    last_score = first_element_prev_score;
                }

                ScoreT tscore = max(score.s2 + gap_score, score.s3);
                if (tscore > score.s3)
                {
                    score.s3 = tscore;
                    loop     = true;
                }

                tscore = max(score.s1 + gap_score, score.s2);
                if (tscore > score.s2)
                {
                    score.s2 = tscore;
                    loop     = true;
                }

                tscore = max(score.s0 + gap_score, score.s1);
                if (tscore > score.s1)
                {
                    score.s1 = tscore;
                    loop     = true;
                }

                tscore = max(last_score + gap_score, score.s0);
                if (tscore > score.s0)
                {
                    score.s0 = tscore;
                    loop     = true;
                }
            }

            // Copy over the last element score of the last lane into a register of first lane
            // which can be used to compute the first cell of the next warp.
            first_element_prev_score = __shfl_sync(FULL_MASK, score.s3, WARP_SIZE - 1);

            scores[score_gIdx * CUDAPOA_BANDED_MAX_MATRIX_SEQUENCE_DIMENSION + read_pos + 1 - band_start] = score.s0;
            scores[score_gIdx * CUDAPOA_BANDED_MAX_MATRIX_SEQUENCE_DIMENSION + read_pos + 2 - band_start] = score.s1;
            scores[score_gIdx * CUDAPOA_BANDED_MAX_MATRIX_SEQUENCE_DIMENSION + read_pos + 3 - band_start] = score.s2;
            scores[score_gIdx * CUDAPOA_BANDED_MAX_MATRIX_SEQUENCE_DIMENSION + read_pos + 4 - band_start] = score.s3;

            __syncwarp();
        }
    }

    uint16_t aligned_nodes = 0;
    if (lane_idx == 0)
    {
        // Find location of the maximum score in the matrix.
        IndexT i      = 0;
        IndexT j      = read_length;
        ScoreT mscore = SHRT_MIN;

        for (IndexT idx = 1; idx <= graph_count; idx++)
        {
            if (outgoing_edge_count[graph[idx - 1]] == 0)
            {
                ScoreT s = get_score(scores, idx, j, gradient, band_width, read_length + 1, min_score_abs);
                if (mscore < s)
                {
                    mscore = s;
                    i      = idx;
                }
            }
        }

        // Fill in backtrace
        IndexT prev_i = 0;
        IndexT prev_j = 0;

        int32_t loop_count = 0;
        while (!(i == 0 && j == 0) && loop_count < (read_length + graph_count + 2))
        {
            loop_count++;
            ScoreT scores_ij = get_score(scores, i, j, gradient, band_width, read_length + 1, min_score_abs);
            bool pred_found  = false;
            // Check if move is diagonal.
            if (i != 0 && j != 0)
            {

                uint16_t node_id  = graph[i - 1];
                ScoreT match_cost = (nodes[node_id] == read[j - 1] ? match_score : mismatch_score);

                uint16_t pred_count = incoming_edge_count[node_id];
                uint16_t pred_i     = (pred_count == 0 ? 0 : (node_id_to_pos[incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES]] + 1));

                if (scores_ij == (get_score(scores, pred_i, j - 1, gradient, band_width, read_length + 1, min_score_abs) + match_cost))
                {
                    prev_i     = pred_i;
                    prev_j     = j - 1;
                    pred_found = true;
                }

                if (!pred_found)
                {
                    for (uint16_t p = 1; p < pred_count; p++)
                    {
                        pred_i = (node_id_to_pos[incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES + p]] + 1);

                        if (scores_ij == (get_score(scores, pred_i, j - 1, gradient, band_width, read_length + 1, min_score_abs) + match_cost))
                        {
                            prev_i     = pred_i;
                            prev_j     = j - 1;
                            pred_found = true;
                            break;
                        }
                    }
                }
            }

            // Check if move is vertical.
            if (!pred_found && i != 0)
            {
                uint16_t node_id    = graph[i - 1];
                uint16_t pred_count = incoming_edge_count[node_id];
                uint16_t pred_i     = (pred_count == 0 ? 0 : node_id_to_pos[incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES]] + 1);

                if (scores_ij == get_score(scores, pred_i, j, gradient, band_width, read_length + 1, min_score_abs) + gap_score)
                {
                    prev_i     = pred_i;
                    prev_j     = j;
                    pred_found = true;
                }

                if (!pred_found)
                {
                    for (uint16_t p = 1; p < pred_count; p++)
                    {
                        pred_i = node_id_to_pos[incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES + p]] + 1;

                        if (scores_ij == get_score(scores, pred_i, j, gradient, band_width, read_length + 1, min_score_abs) + gap_score)
                        {
                            prev_i     = pred_i;
                            prev_j     = j;
                            pred_found = true;
                            break;
                        }
                    }
                }
            }

            // Check if move is horizontal.
            if (!pred_found && scores_ij == get_score(scores, i, j - 1, gradient, band_width, read_length + 1, min_score_abs) + gap_score)
            {
                prev_i     = i;
                prev_j     = j - 1;
                pred_found = true;
            }

            alignment_graph[aligned_nodes] = (i == prev_i ? -1 : graph[i - 1]);
            alignment_read[aligned_nodes]  = (j == prev_j ? -1 : j - 1);
            aligned_nodes++;

            i = prev_i;
            j = prev_j;
        }

        if (loop_count >= (read_length + graph_count + 2))
        {
            aligned_nodes = UINT16_MAX;
        }

#ifdef NW_VERBOSE_PRINT
        printf("aligned nodes %d\n", aligned_nodes);
#endif
    }
    aligned_nodes = __shfl_sync(FULL_MASK, aligned_nodes, 0);
    return aligned_nodes;
}

} // namespace cudapoa

} // namespace claragenomics

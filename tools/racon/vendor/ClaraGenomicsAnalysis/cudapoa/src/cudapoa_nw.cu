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

template <typename ScoreT>
__device__ __forceinline__
    ScoreT4<ScoreT>
    make_ScoreT4(ScoreT s0)
{
    ScoreT4<ScoreT> t;
    t.s0 = s0;
    t.s1 = s0;
    t.s2 = s0;
    t.s3 = s0;
    return t;
}

template <typename SeqT,
          typename IndexT,
          typename ScoreT>
__device__ __forceinline__
    ScoreT4<ScoreT>
    computeScore(IndexT rIdx,
                 SeqT4<SeqT> read4,
                 IndexT gIdx,
                 SeqT graph_base,
                 uint16_t pred_count,
                 IndexT pred_idx,
                 uint16_t* node_id_to_pos,
                 uint16_t* incoming_edges,
                 ScoreT* scores,
                 int32_t scores_width,
                 ScoreT gap_score,
                 ScoreT match_score,
                 ScoreT mismatch_score)
{

    ScoreT4<ScoreT> char_profile;
    char_profile.s0 = (graph_base == read4.r0 ? match_score : mismatch_score);
    char_profile.s1 = (graph_base == read4.r1 ? match_score : mismatch_score);
    char_profile.s2 = (graph_base == read4.r2 ? match_score : mismatch_score);
    char_profile.s3 = (graph_base == read4.r3 ? match_score : mismatch_score);

    // The load instructions typically load data in 4B or 8B chunks.
    // If data is 16b (2B), then a 4B load chunk is loaded into register
    // and the necessary bits are extracted before returning. This wastes cycles
    // as each read of 16b issues a separate load command.
    // Instead it is better to load a 4B or 8B chunk into a register
    // using a single load inst, and then extracting necessary part of
    // of the data using bit arithmatic. Also reduces register count.

    ScoreT4<ScoreT>* pred_scores = (ScoreT4<ScoreT>*)&scores[pred_idx * scores_width];

    // loads 8 consecutive bytes (4 shorts)
    ScoreT4<ScoreT> score4 = pred_scores[rIdx];

    // need to load the next chunk of memory as well
    ScoreT4<ScoreT> score4_next = pred_scores[rIdx + 1];

    ScoreT4<ScoreT> score;

    score.s0 = max(score4.s0 + char_profile.s0,
                   score4.s1 + gap_score);
    score.s1 = max(score4.s1 + char_profile.s1,
                   score4.s2 + gap_score);
    score.s2 = max(score4.s2 + char_profile.s2,
                   score4.s3 + gap_score);
    score.s3 = max(score4.s3 + char_profile.s3,
                   score4_next.s0 + gap_score);

    // Perform same score updates as above, but for rest of predecessors.
    for (IndexT p = 1; p < pred_count; p++)
    {
        int16_t pred_idx = node_id_to_pos[incoming_edges[gIdx * CUDAPOA_MAX_NODE_EDGES + p]] + 1;

        ScoreT4<ScoreT>* pred_scores = (ScoreT4<ScoreT>*)&scores[pred_idx * scores_width];

        // Reasoning for 8B preload same as above.
        ScoreT4<ScoreT> score4      = pred_scores[rIdx];
        ScoreT4<ScoreT> score4_next = pred_scores[rIdx + 1];

        score.s0 = max(score4.s0 + char_profile.s0,
                       max(score.s0, score4.s1 + gap_score));

        score.s1 = max(score4.s1 + char_profile.s1,
                       max(score.s1, score4.s2 + gap_score));

        score.s2 = max(score4.s2 + char_profile.s2,
                       max(score.s2, score4.s3 + gap_score));

        score.s3 = max(score4.s3 + char_profile.s3,
                       max(score.s3, score4_next.s0 + gap_score));
    }

    return score;
}

/**
 * @brief Device function for running Needleman-Wunsch dynamic programming loop.
 *
 * @param[in] nodes                Device buffer with unique nodes in graph
 * @param[in] graph                Device buffer with sorted graph
 * @param[in] node_id_to_pos       Device scratch space for mapping node ID to position in graph
 * @param[in] incoming_edge_count  Device buffer with number of incoming edges per node
 * @param[in] incoming_edges       Device buffer with incoming edges per node
 * @param[in] outgoing_edge_count  Device buffer with number of outgoing edges per node
 * @param[in] outgoing_edges       Device buffer with outgoing edges per node
 * @param[in] read                 Device buffer with sequence (read) to align
 * @param[in] read_count           Number of bases in read
 * @param[out] scores              Device scratch space that scores alignment matrix score
 * @param[out] alignment_graph     Device scratch space for backtrace alignment of graph
 * @param[out] alignment_read      Device scratch space for backtrace alignment of sequence
 * @param[in] gap_score            Score for inserting gap into alignment
 * @param[in] mismatch_score       Score for finding a mismatch in alignment
 * @param[in] match_score          Score for finding a match in alignment
 *
 * @return Number of nodes in final alignment.
 */
template <typename SeqT,
          typename IndexT,
          typename ScoreT,
          int32_t CPT = 4>
__device__
    uint16_t
    runNeedlemanWunsch(SeqT* nodes,
                       uint16_t* graph,
                       uint16_t* node_id_to_pos,
                       uint16_t graph_count,
                       uint16_t* incoming_edge_count,
                       uint16_t* incoming_edges,
                       uint16_t* outgoing_edge_count,
                       uint16_t* outgoing_edges,
                       SeqT* read,
                       uint16_t read_count,
                       ScoreT* scores,
                       int32_t scores_width,
                       int16_t* alignment_graph,
                       int16_t* alignment_read,
                       ScoreT gap_score,
                       ScoreT mismatch_score,
                       ScoreT match_score)
{

    static_assert(CPT == 4,
                  "implementation currently supports only 4 cells per thread");

    int32_t lane_idx = threadIdx.x % WARP_SIZE;

    // Init horizonal boundary conditions (read).
    for (IndexT j = lane_idx; j < read_count + 1; j += WARP_SIZE)
    {
        scores[j] = j * gap_score;
    }

    if (lane_idx == 0)
    {
#ifdef NW_VERBOSE_PRINT
        printf("graph %d, read %d\n", graph_count, read_count);
#endif

        // Init vertical boundary (graph).
        for (IndexT graph_pos = 0; graph_pos < graph_count; graph_pos++)
        {
            uint16_t node_id    = graph[graph_pos];
            uint16_t i          = graph_pos + 1;
            uint16_t pred_count = incoming_edge_count[node_id];
            if (pred_count == 0)
            {
                scores[i * scores_width] = gap_score;
            }
            else
            {
                ScoreT penalty = SHRT_MIN;
                for (uint16_t p = 0; p < pred_count; p++)
                {
                    uint16_t pred_node_id        = incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES + p];
                    uint16_t pred_node_graph_pos = node_id_to_pos[pred_node_id] + 1;
                    penalty                      = max(penalty, scores[pred_node_graph_pos * scores_width]);
                }
                scores[i * scores_width] = penalty + gap_score;
            }
        }
    }

    __syncwarp();

    // readpos_bound is the first multiple of (CPT * WARP_SIZE) that is larger than read_count.
    uint16_t readpos_bound = (((read_count - 1) / (WARP_SIZE * CPT)) + 1) * (WARP_SIZE * CPT);

    SeqT4<SeqT>* d_read4 = (SeqT4<SeqT>*)read;

    // Run DP loop for calculating scores. Process each row at a time, and
    // compute vertical and diagonal values in parallel.
    for (IndexT graph_pos = 0;
         graph_pos < graph_count;
         graph_pos++)
    {

        uint16_t node_id  = graph[graph_pos]; // node id for the graph node
        IndexT score_gIdx = graph_pos + 1;    // score matrix index for this graph node

        ScoreT first_element_prev_score = scores[score_gIdx * scores_width];

        uint16_t pred_count = incoming_edge_count[node_id];

        uint16_t pred_idx = (pred_count == 0 ? 0 : node_id_to_pos[incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES]] + 1);

        SeqT graph_base = nodes[node_id];

        // readpos_bound is the first tb boundary multiple beyond read_count. This is done
        // so all threads in the block enter the loop. The loop has syncwarp, so if
        // any of the threads don't enter, then it'll cause a lock in the system.
        for (IndexT read_pos = lane_idx * CPT;
             read_pos < readpos_bound;
             read_pos += WARP_SIZE * CPT)
        {

            IndexT rIdx = read_pos / CPT;

            // To avoid doing extra work, we clip the extra warps that go beyond the read count.
            // Warp clipping hasn't shown to help too much yet, but might if we increase the tb
            // size in the future.

            SeqT4<SeqT> read4 = d_read4[rIdx];

            ScoreT4<ScoreT> score = make_ScoreT4((ScoreT)SHRT_MAX);

            if (read_pos < read_count)
            {
                score = computeScore<SeqT, IndexT, ScoreT>(rIdx, read4,
                                                           node_id, graph_base,
                                                           pred_count, pred_idx,
                                                           node_id_to_pos, incoming_edges,
                                                           scores, scores_width,
                                                           gap_score, match_score, mismatch_score);
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

            // Index into score matrix.
            if (read_pos < read_count)
            {
                scores[score_gIdx * scores_width + read_pos + 1] = score.s0;
                scores[score_gIdx * scores_width + read_pos + 2] = score.s1;
                scores[score_gIdx * scores_width + read_pos + 3] = score.s2;
                scores[score_gIdx * scores_width + read_pos + 4] = score.s3;
            }
            __syncwarp();
        }
    }

    uint16_t aligned_nodes = 0;
    if (lane_idx == 0)
    {
        // Find location of the maximum score in the matrix.
        IndexT i      = 0;
        IndexT j      = read_count;
        ScoreT mscore = SHRT_MIN;

        for (IndexT idx = 1; idx <= graph_count; idx++)
        {
            if (outgoing_edge_count[graph[idx - 1]] == 0)
            {
                ScoreT s = scores[idx * scores_width + j];
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

        // Trace back from maximum score position to generate alignment.
        // Trace back is done by re-calculating the score at each cell
        // along the path to see which preceding cell the move could have
        // come from. This seems computaitonally more expensive, but doesn't
        // require storing any traceback buffer during alignment.
        int32_t loop_count = 0;
        while (!(i == 0 && j == 0) && loop_count < (read_count + graph_count + 2))
        {
            loop_count++;
            ScoreT scores_ij = scores[i * scores_width + j];
            bool pred_found  = false;

            // Check if move is diagonal.
            if (i != 0 && j != 0)
            {
                uint16_t node_id    = graph[i - 1];
                ScoreT match_cost   = (nodes[node_id] == read[j - 1] ? match_score : mismatch_score);
                uint16_t pred_count = incoming_edge_count[node_id];
                uint16_t pred_i     = (pred_count == 0 ? 0 : (node_id_to_pos[incoming_edges[node_id * CUDAPOA_MAX_NODE_EDGES]] + 1));

                if (scores_ij == (scores[pred_i * scores_width + (j - 1)] + match_cost))
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

                        if (scores_ij == (scores[pred_i * scores_width + (j - 1)] + match_cost))
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

                if (scores_ij == scores[pred_i * scores_width + j] + gap_score)
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

                        if (scores_ij == scores[pred_i * scores_width + j] + gap_score)
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
            if (!pred_found && scores_ij == scores[i * scores_width + (j - 1)] + gap_score)
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

        } // end of while
        if (loop_count >= (read_count + graph_count + 2))
        {
            aligned_nodes = UINT16_MAX;
        }

#ifdef NW_VERBOSE_PRINT
        printf("aligned nodes %d\n", aligned_nodes);
#endif
    }

    aligned_nodes = __shfl_sync(0xffffffff, aligned_nodes, 0);
    return aligned_nodes;
}

__global__ void runNeedlemanWunschKernel(uint8_t* nodes,
                                         uint16_t* graph,
                                         uint16_t* node_id_to_pos,
                                         uint16_t graph_count,
                                         uint16_t* incoming_edge_count,
                                         uint16_t* incoming_edges,
                                         uint16_t* outgoing_edge_count,
                                         uint16_t* outgoing_edges,
                                         uint8_t* read,
                                         uint16_t read_count,
                                         int16_t* scores,
                                         int32_t scores_width,
                                         int16_t* alignment_graph,
                                         int16_t* alignment_read,
                                         int16_t gap_score,
                                         int16_t mismatch_score,
                                         int16_t match_score,
                                         uint16_t* aligned_nodes)
{
    *aligned_nodes = runNeedlemanWunsch<uint8_t, uint16_t, int16_t>(nodes,
                                                                    graph,
                                                                    node_id_to_pos,
                                                                    graph_count,
                                                                    incoming_edge_count,
                                                                    incoming_edges,
                                                                    outgoing_edge_count,
                                                                    outgoing_edges,
                                                                    read,
                                                                    read_count,
                                                                    scores,
                                                                    scores_width,
                                                                    alignment_graph,
                                                                    alignment_read,
                                                                    gap_score,
                                                                    mismatch_score,
                                                                    match_score);
}

void runNW(uint8_t* nodes,
           uint16_t* graph,
           uint16_t* node_id_to_pos,
           uint16_t graph_count,
           uint16_t* incoming_edge_count,
           uint16_t* incoming_edges,
           uint16_t* outgoing_edge_count,
           uint16_t* outgoing_edges,
           uint8_t* read,
           uint16_t read_count,
           int16_t* scores,
           int32_t scores_width,
           int16_t* alignment_graph,
           int16_t* alignment_read,
           int16_t gap_score,
           int16_t mismatch_score,
           int16_t match_score,
           uint16_t* aligned_nodes)
{
    runNeedlemanWunschKernel<<<1, 64>>>(nodes,
                                        graph,
                                        node_id_to_pos,
                                        graph_count,
                                        incoming_edge_count,
                                        incoming_edges,
                                        outgoing_edge_count,
                                        outgoing_edges,
                                        read,
                                        read_count,
                                        scores,
                                        scores_width,
                                        alignment_graph,
                                        alignment_read,
                                        gap_score,
                                        mismatch_score,
                                        match_score,
                                        aligned_nodes);
    CGA_CU_CHECK_ERR(cudaPeekAtLastError());
}

} // namespace cudapoa

} // namespace claragenomics

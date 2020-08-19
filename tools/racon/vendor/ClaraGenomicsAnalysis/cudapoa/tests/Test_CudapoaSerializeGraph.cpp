/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <claragenomics/cudapoa/batch.hpp>
#include <claragenomics/utils/genomeutils.hpp>
#include <claragenomics/utils/graph.hpp>

#include "gtest/gtest.h"

namespace claragenomics
{

namespace cudapoa
{

using ::testing::TestWithParam;
using ::testing::ValuesIn;

class GraphTest : public ::testing::Test
{
public:
    void SetUp() {}

    void initialize(uint32_t max_sequences_per_poa,
                    uint32_t device_id     = 0,
                    cudaStream_t stream    = 0,
                    int8_t output_mask     = OutputType::msa,
                    int16_t gap_score      = -8,
                    int16_t mismatch_score = -6,
                    int16_t match_score    = 8,
                    bool banded_alignment  = false)
    {
        size_t total = 0, free = 0;
        cudaSetDevice(device_id);
        cudaMemGetInfo(&free, &total);
        size_t mem_per_batch = 0.9 * free;

        cudapoa_batch = claragenomics::cudapoa::create_batch(max_sequences_per_poa, device_id, stream, mem_per_batch, output_mask, gap_score, mismatch_score, match_score, banded_alignment);
    }

public:
    std::unique_ptr<claragenomics::cudapoa::Batch> cudapoa_batch;
};

TEST_F(GraphTest, CudapoaSerializeGraph)
{
    std::minstd_rand rng(1);
    int num_sequences    = 500;
    std::string backbone = claragenomics::genomeutils::generate_random_genome(50, rng);
    auto sequences       = claragenomics::genomeutils::generate_random_sequences(backbone, num_sequences, rng, 10, 5, 10);

    initialize(num_sequences);
    Group poa_group;
    std::vector<StatusType> status;
    std::vector<std::vector<int8_t>> weights;
    for (const auto& seq : sequences)
    {
        weights.push_back(std::vector<int8_t>(seq.length(), 1));
        Entry e{};
        e.seq     = seq.c_str();
        e.weights = weights.back().data();
        e.length  = seq.length();
        poa_group.push_back(e);
    }
    ASSERT_EQ(cudapoa_batch->add_poa_group(status, poa_group), StatusType::success);

    std::vector<DirectedGraph> cudapoa_graphs;
    std::vector<StatusType> output_status;

    cudapoa_batch->generate_poa();

    cudapoa_batch->get_graphs(cudapoa_graphs, output_status);
    std::cout << cudapoa_graphs[0].serialize_to_dot() << std::endl;
}

} // namespace cudapoa

} // namespace claragenomics

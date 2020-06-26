/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <claragenomics/cudaaligner/cudaaligner.hpp>
#include <claragenomics/cudaaligner/aligner.hpp>
#include <claragenomics/cudaaligner/alignment.hpp>
#include <claragenomics/utils/cudautils.hpp>
#include <claragenomics/utils/genomeutils.hpp>

#include <cuda_runtime_api.h>
#include <vector>
#include <string>
#include <stdexcept>
#include <iostream>
#include <random>

using namespace claragenomics;
using namespace claragenomics::genomeutils;
using namespace claragenomics::cudaaligner;

std::unique_ptr<Aligner> initialize_batch(int32_t max_query_size,
                                          int32_t max_target_size,
                                          int32_t max_alignments_per_batch)
{
    // Get device information.
    int32_t device_count = 0;
    CGA_CU_CHECK_ERR(cudaGetDeviceCount(&device_count));
    assert(device_count > 0);

    // Initialize internal logging framework.
    Init();

    // Initialize CUDA Aligner batch object for batched processing of alignments on the GPU.
    const int32_t device_id = 0;
    cudaStream_t stream     = 0;

    std::unique_ptr<Aligner> batch = create_aligner(max_query_size,
                                                    max_target_size,
                                                    max_alignments_per_batch,
                                                    AlignmentType::global_alignment,
                                                    stream,
                                                    device_id);

    return std::move(batch);
}

void generate_data(std::vector<std::pair<std::string, std::string>>& data,
                   int32_t max_query_size,
                   int32_t max_target_size,
                   int32_t num_examples)
{
    std::minstd_rand rng(1);
    for (int32_t i = 0; i < num_examples; i++)
    {
        data.emplace_back(std::make_pair(
            generate_random_genome(max_query_size, rng),
            generate_random_genome(max_target_size, rng)));
    }
}

int main(int argc, char** argv)
{
    // Process options
    int c      = 0;
    bool help  = false;
    bool print = false;

    while ((c = getopt(argc, argv, "hp")) != -1)
    {
        switch (c)
        {
        case 'p':
            print = true;
            break;
        case 'h':
            help = true;
            break;
        }
    }

    if (help)
    {
        std::cout << "CUDA Aligner API sample program. Runs pairwise alignment over a batch of randomly generated sequences." << std::endl;
        std::cout << "Usage:" << std::endl;
        std::cout << "./sample_cudaaligner [-p] [-h]" << std::endl;
        std::cout << "-p : Print the MSA or consensus output to stdout" << std::endl;
        std::cout << "-h : Print help message" << std::endl;
        std::exit(0);
    }

    const int32_t query_length  = 10000;
    const int32_t target_length = 15000;
    const uint32_t num_entries  = 1000;

    std::cout << "Running pairwise alignment for " << num_entries << " pairs..." << std::endl;

    // Initialize batch.
    std::unique_ptr<Aligner> batch = initialize_batch(query_length, target_length, 100);

    // Generate data.
    std::vector<std::pair<std::string, std::string>> data;
    generate_data(data, query_length, target_length, num_entries);
    assert(data.size() == num_entries);

    // Loop over all the alignment pairs, add them to the batch and process them.
    uint32_t data_id = 0;
    while (data_id != num_entries)
    {
        const std::string& query  = data[data_id].first;
        const std::string& target = data[data_id].second;

        // Add a pair to the batch, and check for status.
        StatusType status = batch->add_alignment(query.c_str(), query.length(), target.c_str(), target.length());
        if (status == exceeded_max_alignments || data_id == num_entries - 1)
        {
            // Launch alignment on the GPU. align_all is an async call.
            batch->align_all();
            // Synchronize all alignments.
            batch->sync_alignments();
            if (print)
            {
                const std::vector<std::shared_ptr<Alignment>>& alignments = batch->get_alignments();
                for (const auto& alignment : alignments)
                {
                    FormattedAlignment formatted = alignment->format_alignment();
                    std::cout << formatted.first << "\n"
                              << formatted.second << "\n"
                              << std::endl;
                }
            }
            // Reset batch to reuse memory for new alignments.
            batch->reset();
            std::cout << "Aligned till " << (data_id - 1) << "." << std::endl;
        }
        else if (status != success)
        {
            throw std::runtime_error("Experienced error type " + std::to_string(status));
        }

        // If alignment was add successfully, increment counter.
        if (status == success)
        {
            data_id++;
        }
    }

    return 0;
}

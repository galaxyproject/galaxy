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

#include <random>
#include <stdexcept>

namespace claragenomics
{

namespace genomeutils
{

inline std::string generate_random_genome(const int32_t length, std::minstd_rand& rng)
{
    const char alphabet[4] = {'A', 'C', 'G', 'T'};
    std::uniform_int_distribution<int32_t> random_index(0, 3);
    std::string genome = "";
    for (int32_t i = 0; i < length; i++)
    {
        genome += alphabet[random_index(rng)];
    }
    return genome;
}

inline std::vector<std::string> generate_random_sequences(std::string backbone,
                                                          int n,
                                                          std::minstd_rand& rng,
                                                          int num_mutations = 1,
                                                          int num_insertion = 1,
                                                          int num_deletions = 1)
{
    if (backbone.length() == 0)
        throw std::invalid_argument("backbone sequence shouldn't be empty.");
    if (backbone.length() < num_deletions)
        throw std::invalid_argument("num_deletions should be smaller than backbone's length.");

    std::vector<std::string> sequences(n, backbone);
    std::string bases = "ATCG";

    std::uniform_real_distribution<double> random_prob(0, 1);
    std::uniform_int_distribution<int> random_base_pos(0, bases.length() - 1);

    for (int i = 1; i < n; i++)
    {
        for (int j = 0; j < num_deletions; j++)
        {
            if (random_prob(rng) > 0.5)
            {
                int length = sequences[i].length();
                std::uniform_int_distribution<int> random_del_pos(0, length - 1);
                int del_pos = random_del_pos(rng);
                sequences[i].erase(del_pos, 1);
            }
        }

        for (int j = 0; j < num_insertion; j++)
        {
            if (random_prob(rng) > 0.5)
            {
                int length = sequences[i].length();
                std::uniform_int_distribution<int> random_ins_pos(0, length - 1);
                int ins_pos  = random_ins_pos(rng);
                int ins_base = random_base_pos(rng);

                sequences[i].insert(ins_pos, 1, bases[ins_base]);
            }
        }

        int length = sequences[i].length();
        std::uniform_int_distribution<int> random_mut_pos(0, length - 1);
        for (int j = 0; j < num_mutations; j++)
        {
            if (random_prob(rng) > 0.5)
            {
                int mut_pos           = random_mut_pos(rng);
                int swap_base         = random_base_pos(rng);
                sequences[i][mut_pos] = bases[swap_base];
            }
        }
    }

    return sequences;
}

} // namespace genomeutils

} // namespace claragenomics

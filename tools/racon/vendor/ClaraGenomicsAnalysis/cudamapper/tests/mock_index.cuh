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

#include "gmock/gmock.h"

#include "../src/index_gpu.cuh"
#include "../src/minimizer.hpp"
#include "cudamapper_file_location.hpp"

namespace claragenomics
{
namespace cudamapper
{

class MockIndex : public IndexGPU<Minimizer>
{
public:
    MockIndex()
        : IndexGPU(*claragenomics::io::create_fasta_parser(std::string(CUDAMAPPER_BENCHMARK_DATA_DIR) + "/gatt.fasta"),
                   0,
                   0,
                   0,
                   0,
                   true)
    {
    }

    MOCK_METHOD(const std::string&, read_id_to_read_name, (const read_id_t read_id), (const, override));
    MOCK_METHOD(const std::uint32_t&, read_id_to_read_length, (const read_id_t read_id), (const, override));
};

} // namespace cudamapper
} // namespace claragenomics

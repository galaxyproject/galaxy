/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "gtest/gtest.h"
#include "../src/minimizer.hpp"

namespace claragenomics
{
namespace cudamapper
{

void test_function(const std::uint64_t number_of_reads_to_add,
                   const std::uint64_t minimizer_size,
                   const std::uint64_t window_size,
                   const std::uint64_t read_id_of_first_read,
                   const std::vector<char>& merged_basepairs_h,
                   const std::vector<ArrayBlock>& read_id_to_basepairs_section_h,
                   const std::vector<representation_t>& expected_representations_h,
                   const std::vector<Minimizer::ReadidPositionDirection>& expected_rest_h,
                   const bool hash_minimizers)
{
    device_buffer<char> merged_basepairs_d(merged_basepairs_h.size());
    CGA_CU_CHECK_ERR(cudaMemcpy(merged_basepairs_d.data(),
                                merged_basepairs_h.data(),
                                merged_basepairs_h.size() * sizeof(char),
                                cudaMemcpyHostToDevice));

    device_buffer<ArrayBlock> read_id_to_basepairs_section_d(read_id_to_basepairs_section_h.size());
    CGA_CU_CHECK_ERR(cudaMemcpy(read_id_to_basepairs_section_d.data(),
                                read_id_to_basepairs_section_h.data(),
                                read_id_to_basepairs_section_h.size() * sizeof(ArrayBlock),
                                cudaMemcpyHostToDevice));

    auto sketch_elements = Minimizer::generate_sketch_elements(number_of_reads_to_add,
                                                               minimizer_size,
                                                               window_size,
                                                               read_id_of_first_read,
                                                               merged_basepairs_d,
                                                               read_id_to_basepairs_section_h,
                                                               read_id_to_basepairs_section_d,
                                                               hash_minimizers);

    device_buffer<representation_t> representations_d = std::move(sketch_elements.representations_d);
    std::vector<representation_t> representations_h(representations_d.size());
    CGA_CU_CHECK_ERR(cudaMemcpy(representations_h.data(),
                                representations_d.data(),
                                representations_d.size() * sizeof(representation_t),
                                cudaMemcpyDeviceToHost));

    device_buffer<Minimizer::ReadidPositionDirection> rest_d = std::move(sketch_elements.rest_d);
    std::vector<Minimizer::ReadidPositionDirection> rest_h(rest_d.size());
    CGA_CU_CHECK_ERR(cudaMemcpy(rest_h.data(),
                                rest_d.data(),
                                rest_d.size() * sizeof(Minimizer::ReadidPositionDirection),
                                cudaMemcpyDeviceToHost));

    ASSERT_EQ(expected_representations_h.size(), expected_rest_h.size());
    ASSERT_EQ(expected_representations_h.size(), representations_h.size());
    ASSERT_EQ(expected_rest_h.size(), rest_h.size());

    for (std::size_t i = 0; i < expected_representations_h.size(); ++i)
    {
        EXPECT_EQ(expected_representations_h[i], representations_h[i]) << "index: " << i;
        EXPECT_EQ(expected_rest_h[i].read_id_, rest_h[i].read_id_) << "index: " << i;
        EXPECT_EQ(expected_rest_h[i].position_in_read_, rest_h[i].position_in_read_) << "index: " << i;
        EXPECT_EQ(expected_rest_h[i].direction_, rest_h[i].direction_) << "index: " << i;
    }
}

TEST(TestCudamappperMinimizer, GATT_4_1)
{
    const std::uint64_t number_of_reads_to_add = 1;
    const std::uint64_t minimizer_size         = 4;
    const std::uint64_t window_size            = 1;
    const std::uint64_t read_id_of_first_read  = 0;

    const std::vector<char> merged_basepairs_h{'G', 'A', 'T', 'T'};

    std::vector<ArrayBlock> read_id_to_basepairs_section_h;
    read_id_to_basepairs_section_h.push_back({0, 4});

    std::vector<representation_t> expected_representations_h;
    expected_representations_h.push_back(0b00001101);
    std::vector<Minimizer::ReadidPositionDirection> expected_rest_h;
    expected_rest_h.push_back({0, 0, 1});

    test_function(number_of_reads_to_add,
                  minimizer_size,
                  window_size,
                  read_id_of_first_read,
                  merged_basepairs_h,
                  read_id_to_basepairs_section_h,
                  expected_representations_h,
                  expected_rest_h,
                  false);

    // Test with minimizer hashing enabled
    std::vector<representation_t> expected_representations_hashed_h;
    expected_representations_hashed_h.push_back(304626093);
    std::vector<Minimizer::ReadidPositionDirection> expected_rest_hashed_h;
    expected_rest_hashed_h.push_back({0, 0, 0});

    test_function(number_of_reads_to_add,
                  minimizer_size,
                  window_size,
                  read_id_of_first_read,
                  merged_basepairs_h,
                  read_id_to_basepairs_section_h,
                  expected_representations_hashed_h,
                  expected_rest_hashed_h,
                  true);
}

TEST(TestCudamappperMinimizer, GATT_2_3)
{
    // GATT

    // kmer representation: forward, reverse
    // GA: <20> 31
    // AT: <03> 03 // takes forward by default
    // TT: 33  <00>

    // front end minimizers: representation, position_in_read, direction, read_id
    // GA: 20 0 F 0

    // central minimizers
    // GAT: 03 1 F 0
    // ATT: 00 2 R 0

    // back end minimizers
    // TT: 00 2 R 0

    const std::uint64_t number_of_reads_to_add = 1;
    const std::uint64_t minimizer_size         = 2;
    const std::uint64_t window_size            = 3;
    const std::uint64_t read_id_of_first_read  = 0;

    const std::vector<char> merged_basepairs_h{'G', 'A', 'T', 'T'};

    std::vector<ArrayBlock> read_id_to_basepairs_section_h;
    read_id_to_basepairs_section_h.push_back({0, 4});

    std::vector<representation_t> expected_representations_h;
    expected_representations_h.push_back(0b1000);
    expected_representations_h.push_back(0b0011);
    expected_representations_h.push_back(0b0000);
    std::vector<Minimizer::ReadidPositionDirection> expected_rest_h;
    expected_rest_h.push_back({0, 0, 0});
    expected_rest_h.push_back({0, 1, 0});
    expected_rest_h.push_back({0, 2, 1});

    test_function(number_of_reads_to_add,
                  minimizer_size,
                  window_size,
                  read_id_of_first_read,
                  merged_basepairs_h,
                  read_id_to_basepairs_section_h,
                  expected_representations_h,
                  expected_rest_h,
                  false);

    // Test with minimizer hashing enabled
    std::vector<representation_t> expected_representations_hashed_h;
    expected_representations_hashed_h.push_back(1023180699);
    expected_representations_hashed_h.push_back(2797583197);
    expected_representations_hashed_h.push_back(3255840626);
    std::vector<Minimizer::ReadidPositionDirection> expected_rest_hashed_h;
    expected_rest_hashed_h.push_back({0, 0, 0});
    expected_rest_hashed_h.push_back({0, 1, 0});
    expected_rest_hashed_h.push_back({0, 2, 0});

    test_function(number_of_reads_to_add,
                  minimizer_size,
                  window_size,
                  read_id_of_first_read,
                  merged_basepairs_h,
                  read_id_to_basepairs_section_h,
                  expected_representations_hashed_h,
                  expected_rest_hashed_h,
                  true);
}

TEST(TestCudamappperMinimizer, CCCATACC_2_7)
{
    // CCCATACC

    // kmer representation: forward, reverse
    // CC: <11> 22
    // CC: <11> 22
    // CA: <10> 32
    // AT: <03> 03
    // TA: <30> 30
    // AC: <01> 23
    // CC: <11> 22

    // front end minimizers: representation, position_in_read, direction, read_id
    // CC     : 11 0 F 0
    // CCC    : 11 1 F 0
    // CCCA   : 10 2 F 0
    // CCCAT  : 03 3 F 0
    // CCCATA : 03 3 F 0
    // CCCATAC: 01 5 F 0

    // central minimizers
    // CCCATACC: 01 5 F 0

    // back end minimizers
    // CCATACC: 01 5 F 0
    // CATACC : 01 5 F 0
    // ATACC  : 01 5 F 0
    // TACC   : 01 5 F 0
    // ACC    : 01 5 F 0
    // CC     : 11 6 F 0

    const std::uint64_t number_of_reads_to_add = 1;
    const std::uint64_t minimizer_size         = 2;
    const std::uint64_t window_size            = 7;
    const std::uint64_t read_id_of_first_read  = 0;

    const std::vector<char> merged_basepairs_h{'C', 'C', 'C', 'A', 'T', 'A', 'C', 'C'};

    std::vector<ArrayBlock> read_id_to_basepairs_section_h;
    read_id_to_basepairs_section_h.push_back({0, 8});

    std::vector<representation_t> expected_representations_h;
    expected_representations_h.push_back(0b0101);
    expected_representations_h.push_back(0b0101);
    expected_representations_h.push_back(0b0100);
    expected_representations_h.push_back(0b0011);
    expected_representations_h.push_back(0b0001);
    expected_representations_h.push_back(0b0101);
    std::vector<Minimizer::ReadidPositionDirection> expected_rest_h;
    expected_rest_h.push_back({0, 0, 0});
    expected_rest_h.push_back({0, 1, 0});
    expected_rest_h.push_back({0, 2, 0});
    expected_rest_h.push_back({0, 3, 0});
    expected_rest_h.push_back({0, 5, 0});
    expected_rest_h.push_back({0, 6, 0});

    test_function(number_of_reads_to_add,
                  minimizer_size,
                  window_size,
                  read_id_of_first_read,
                  merged_basepairs_h,
                  read_id_to_basepairs_section_h,
                  expected_representations_h,
                  expected_rest_h,
                  false);

    // Test with minimizer hashing enabled
    std::vector<representation_t> expected_representations_hashed_h;
    expected_representations_hashed_h.push_back(2515151312);
    expected_representations_hashed_h.push_back(2515151312);
    expected_representations_hashed_h.push_back(1582582417);
    expected_representations_hashed_h.push_back(2515151312);

    std::vector<Minimizer::ReadidPositionDirection> expected_rest_hashed_h;
    expected_rest_hashed_h.push_back({0, 0, 0});
    expected_rest_hashed_h.push_back({0, 1, 0});
    expected_rest_hashed_h.push_back({0, 2, 0});
    expected_rest_hashed_h.push_back({0, 6, 0});

    test_function(number_of_reads_to_add,
                  minimizer_size,
                  window_size,
                  read_id_of_first_read,
                  merged_basepairs_h,
                  read_id_to_basepairs_section_h,
                  expected_representations_hashed_h,
                  expected_rest_hashed_h,
                  true);
}

TEST(TestCudamappperMinimizer, CATCAAG_AAGCTA_3_2)
{
    // ** CATCAAG **

    // kmer representation: forward, reverse
    // CAT:  103 <032>
    // ATC: <031> 203
    // TCA: <310> 320
    // CAA: <100> 332
    // AAG: <002> 133

    // front end minimizers: representation, position_in_read, direction, read_id
    // CAT: 032 0 R 0

    // central minimizers
    // CATC: 031 1 F 0
    // ATCA: 031 1 F 0
    // TCAA: 100 3 F 0
    // CAAG: 002 4 F 0

    // back end minimizers
    // AAG: 002 4 F 0

    // ** AAGCTA **

    // kmer representation: forward, reverse
    // AAG: <002> 133
    // AGC: <021> 213
    // GCT:  213 <021>
    // CTA: <130> 302

    // front end minimizers: representation, position_in_read, direction, read_id
    // AAG: 002 0 F 1

    // central minimizers
    // AAGC: 002 0 F 1
    // AGCT: 021 2 R 1 // only the last minimizer is saved
    // GCTA: 021 2 R 1

    // back end minimizers
    // CTA: 130 3 F 1

    // all minimizers: (032,0,R,0), (031,1,F,0), (100,3,F,0), (002,4,F,0), (002,0,F,1), (021,2,R,1), (130,3,F,1)

    const std::uint64_t number_of_reads_to_add = 2;
    const std::uint64_t minimizer_size         = 3;
    const std::uint64_t window_size            = 2;
    const std::uint64_t read_id_of_first_read  = 0;

    const std::vector<char> merged_basepairs_h{'C', 'A', 'T', 'C', 'A', 'A', 'G', 'A', 'A', 'G', 'C', 'T', 'A'};

    std::vector<ArrayBlock> read_id_to_basepairs_section_h;
    read_id_to_basepairs_section_h.push_back({0, 7});
    read_id_to_basepairs_section_h.push_back({7, 6});

    std::vector<representation_t> expected_representations_h;
    expected_representations_h.push_back(0b001110);
    expected_representations_h.push_back(0b001101);
    expected_representations_h.push_back(0b010000);
    expected_representations_h.push_back(0b000010);
    expected_representations_h.push_back(0b000010);
    expected_representations_h.push_back(0b001001);
    expected_representations_h.push_back(0b011100);
    std::vector<Minimizer::ReadidPositionDirection> expected_rest_h;
    expected_rest_h.push_back({0, 0, 1});
    expected_rest_h.push_back({0, 1, 0});
    expected_rest_h.push_back({0, 3, 0});
    expected_rest_h.push_back({0, 4, 0});
    expected_rest_h.push_back({1, 0, 0});
    expected_rest_h.push_back({1, 2, 1});
    expected_rest_h.push_back({1, 3, 0});

    test_function(number_of_reads_to_add,
                  minimizer_size,
                  window_size,
                  read_id_of_first_read,
                  merged_basepairs_h,
                  read_id_to_basepairs_section_h,
                  expected_representations_h,
                  expected_rest_h,
                  false);

    // Test with minimizer hashing enabled
    std::vector<representation_t> expected_representations_hashed_h;
    expected_representations_hashed_h.push_back(549100223);
    expected_representations_hashed_h.push_back(447855090);
    expected_representations_hashed_h.push_back(1279515286);
    expected_representations_hashed_h.push_back(1865025060);
    expected_representations_hashed_h.push_back(1865025060);
    expected_representations_hashed_h.push_back(4103259927);
    expected_representations_hashed_h.push_back(357458314);
    std::vector<Minimizer::ReadidPositionDirection> expected_rest_hashed_h;
    expected_rest_hashed_h.push_back({0, 0, 0});
    expected_rest_hashed_h.push_back({0, 1, 1});
    expected_rest_hashed_h.push_back({0, 2, 0});
    expected_rest_hashed_h.push_back({0, 4, 0});
    expected_rest_hashed_h.push_back({1, 0, 0});
    expected_rest_hashed_h.push_back({1, 2, 1});
    expected_rest_hashed_h.push_back({1, 3, 0});

    test_function(number_of_reads_to_add,
                  minimizer_size,
                  window_size,
                  read_id_of_first_read,
                  merged_basepairs_h,
                  read_id_to_basepairs_section_h,
                  expected_representations_hashed_h,
                  expected_rest_hashed_h,
                  true);
}

TEST(TestCudamappperMinimizer, CATCAAG_AAGCTA_3_2_read_id_offset_5)
{
    // ** CATCAAG **

    // kmer representation: forward, reverse
    // CAT:  103 <032>
    // ATC: <031> 203
    // TCA: <310> 320
    // CAA: <100> 332
    // AAG: <002> 133

    // front end minimizers: representation, position_in_read, direction, read_id
    // CAT: 032 0 R 0

    // central minimizers
    // CATC: 031 1 F 0
    // ATCA: 031 1 F 0
    // TCAA: 100 3 F 0
    // CAAG: 002 4 F 0

    // back end minimizers
    // AAG: 002 4 F 0

    // ** AAGCTA **

    // kmer representation: forward, reverse
    // AAG: <002> 133
    // AGC: <021> 213
    // GCT:  213 <021>
    // CTA: <130> 302

    // front end minimizers: representation, position_in_read, direction, read_id
    // AAG: 002 0 F 1

    // central minimizers
    // AAGC: 002 0 F 1
    // AGCT: 021 2 R 1 // only the last minimizer is saved
    // GCTA: 021 2 R 1

    // back end minimizers
    // CTA: 130 3 F 1

    // all minimizers: (032,0,R,0), (031,1,F,0), (100,3,F,0), (002,4,F,0), (002,0,F,1), (021,2,R,1), (130,3,F,1)

    const std::uint64_t number_of_reads_to_add = 2;
    const std::uint64_t minimizer_size         = 3;
    const std::uint64_t window_size            = 2;
    const std::uint64_t read_id_of_first_read  = 5;

    const std::vector<char> merged_basepairs_h{'C', 'A', 'T', 'C', 'A', 'A', 'G', 'A', 'A', 'G', 'C', 'T', 'A'};

    std::vector<ArrayBlock> read_id_to_basepairs_section_h;
    read_id_to_basepairs_section_h.push_back({0, 7});
    read_id_to_basepairs_section_h.push_back({7, 6});

    std::vector<representation_t> expected_representations_h;
    expected_representations_h.push_back(0b001110);
    expected_representations_h.push_back(0b001101);
    expected_representations_h.push_back(0b010000);
    expected_representations_h.push_back(0b000010);
    expected_representations_h.push_back(0b000010);
    expected_representations_h.push_back(0b001001);
    expected_representations_h.push_back(0b011100);
    std::vector<Minimizer::ReadidPositionDirection> expected_rest_h;
    expected_rest_h.push_back({5, 0, 1});
    expected_rest_h.push_back({5, 1, 0});
    expected_rest_h.push_back({5, 3, 0});
    expected_rest_h.push_back({5, 4, 0});
    expected_rest_h.push_back({6, 0, 0});
    expected_rest_h.push_back({6, 2, 1});
    expected_rest_h.push_back({6, 3, 0});

    test_function(number_of_reads_to_add,
                  minimizer_size,
                  window_size,
                  read_id_of_first_read,
                  merged_basepairs_h,
                  read_id_to_basepairs_section_h,
                  expected_representations_h,
                  expected_rest_h,
                  false);

    std::vector<representation_t> expected_representations_hashed_h;
    expected_representations_hashed_h.push_back(549100223);
    expected_representations_hashed_h.push_back(447855090);
    expected_representations_hashed_h.push_back(1279515286);
    expected_representations_hashed_h.push_back(1865025060);
    expected_representations_hashed_h.push_back(1865025060);
    expected_representations_hashed_h.push_back(4103259927);
    expected_representations_hashed_h.push_back(357458314);
    std::vector<Minimizer::ReadidPositionDirection> expected_rest_hashed_h;
    expected_rest_hashed_h.push_back({5, 0, 0});
    expected_rest_hashed_h.push_back({5, 1, 1});
    expected_rest_hashed_h.push_back({5, 2, 0});
    expected_rest_hashed_h.push_back({5, 4, 0});
    expected_rest_hashed_h.push_back({6, 0, 0});
    expected_rest_hashed_h.push_back({6, 2, 1});
    expected_rest_hashed_h.push_back({6, 3, 0});

    test_function(number_of_reads_to_add,
                  minimizer_size,
                  window_size,
                  read_id_of_first_read,
                  merged_basepairs_h,
                  read_id_to_basepairs_section_h,
                  expected_representations_hashed_h,
                  expected_rest_hashed_h,
                  true);
    // Test with minimizer hashing enabled
}
} // namespace cudamapper
} // namespace claragenomics

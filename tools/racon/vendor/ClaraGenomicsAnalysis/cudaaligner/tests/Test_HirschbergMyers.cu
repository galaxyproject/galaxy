/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "../src/hirschberg_myers_gpu.cu"
#include "../src/batched_device_matrices.cuh"
#include <claragenomics/utils/device_buffer.cuh>
#include <claragenomics/utils/signed_integer_utils.hpp>
#include <vector>
#include <gtest/gtest.h>

namespace claragenomics
{

namespace cudaaligner
{

using WordType = hirschbergmyers::WordType;

namespace test
{

__global__ void myers_preprocess_kernel(batched_device_matrices<WordType>::device_interface* batched_query_pattern, char const* query, int32_t query_size)
{
    CGA_CONSTEXPR int32_t word_size            = sizeof(WordType) * CHAR_BIT;
    const int32_t n_words                      = ceiling_divide<int32_t>(query_size, word_size);
    device_matrix_view<WordType> query_pattern = batched_query_pattern->get_matrix_view(0, n_words, 8);
    hirschbergmyers::myers_preprocess(query_pattern, query, query_size);
}

__global__ void myers_get_query_pattern_test_kernel(int32_t n_words, WordType* result, batched_device_matrices<WordType>::device_interface* batched_query_pattern, int32_t idx, char x, bool reverse)
{
    int const i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < 32)
    {
        device_matrix_view<WordType> patterns = batched_query_pattern->get_matrix_view(0, n_words, 8);
        result[i]                             = hirschbergmyers::get_query_pattern(patterns, idx, i, x, reverse);
    }
}

matrix<WordType> compute_myers_preprocess_matrix(std::string query_host)
{
    CGA_CONSTEXPR int32_t word_size = sizeof(WordType) * CHAR_BIT;
    cudaStream_t stream             = nullptr;
    const int32_t n_words           = ceiling_divide<int32_t>(query_host.size(), word_size);

    device_buffer<char> query(query_host.size());
    cudaMemcpy(query.data(), query_host.data(), sizeof(char) * query.size(), cudaMemcpyHostToDevice);

    batched_device_matrices<WordType> query_pattern(1, 8 * n_words, stream);
    myers_preprocess_kernel<<<1, 32>>>(query_pattern.get_device_interface(), query.data(), query.size());
    return query_pattern.get_matrix(0, n_words, 8, stream);
}

std::vector<WordType> myers_get_query_pattern_test(std::string query_host, int32_t idx, char x, bool reverse)
{
    CGA_CONSTEXPR int32_t word_size = sizeof(WordType) * CHAR_BIT;
    cudaStream_t stream             = nullptr;
    const int32_t n_words           = ceiling_divide<int32_t>(query_host.size(), word_size);
    device_buffer<char> query(query_host.size());
    cudaMemcpy(query.data(), query_host.data(), sizeof(char) * query.size(), cudaMemcpyHostToDevice);
    batched_device_matrices<WordType> query_pattern(1, 8 * n_words, stream);
    myers_preprocess_kernel<<<1, 32>>>(query_pattern.get_device_interface(), query.data(), query.size());

    device_buffer<WordType> result(32);
    myers_get_query_pattern_test_kernel<<<1, 32>>>(n_words, result.data(), query_pattern.get_device_interface(), idx, x, reverse);

    std::vector<WordType> result_host(result.size());
    cudaMemcpy(result_host.data(), result.data(), sizeof(WordType) * result.size(), cudaMemcpyDeviceToHost);
    return result_host;
}

} // namespace test

TEST(HirschbergMyers, myers_preprocess_test)
{
    CGA_CONSTEXPR int32_t word_size = sizeof(WordType) * CHAR_BIT;
    static_assert(word_size == 32, "This test assumes word_size = 32bit.");
    using test::compute_myers_preprocess_matrix;
    std::string query =
        "AACCGGTTACGTACGT"
        "AAACCCGGGTTTACGT"
        "AAACCCGGGTTTACG";
    matrix<WordType> patterns = compute_myers_preprocess_matrix(query);
    ASSERT_EQ(patterns.num_rows(), 2);
    ASSERT_EQ(patterns.num_cols(), 8);
    // A=0, C=1, T=2, G=3
    EXPECT_EQ(patterns(0, 0), 0b00010000000001110001000100000011u);
    EXPECT_EQ(patterns(0, 1), 0b00100000001110000010001000001100u);
    EXPECT_EQ(patterns(0, 2), 0b10001110000000001000100011000000u);
    EXPECT_EQ(patterns(0, 3), 0b01000001110000000100010000110000u);
    EXPECT_EQ(patterns(1, 0), 0b001000000000111u);
    EXPECT_EQ(patterns(1, 1), 0b010000000111000u);
    EXPECT_EQ(patterns(1, 2), 0b000111000000000u);
    EXPECT_EQ(patterns(1, 3), 0b100000111000000u);
    // reverse: A=4, C=5, T=6, G=7
    EXPECT_EQ(patterns(0, 4), 0b01110000000001000111000000000100u);
    EXPECT_EQ(patterns(0, 5), 0b00001110000000100000111000000010u);
    EXPECT_EQ(patterns(0, 6), 0b10000000001110001000000000111000u);
    EXPECT_EQ(patterns(0, 7), 0b00000001110000010000000111000001u);
    EXPECT_EQ(patterns(1, 4), 0b110000001000100u);
    EXPECT_EQ(patterns(1, 5), 0b001100000100010u);
    EXPECT_EQ(patterns(1, 6), 0b000000110001000u);
    EXPECT_EQ(patterns(1, 7), 0b000011000010001u);

    std::reverse(query.begin(), query.end());
    matrix<WordType> patterns_reversed = compute_myers_preprocess_matrix(query);
    ASSERT_EQ(patterns.num_rows(), 2);
    ASSERT_EQ(patterns.num_cols(), 8);
    EXPECT_EQ(patterns_reversed(0, 0), patterns(0, 4));
    EXPECT_EQ(patterns_reversed(1, 0), patterns(1, 4));
    EXPECT_EQ(patterns_reversed(0, 1), patterns(0, 5));
    EXPECT_EQ(patterns_reversed(1, 1), patterns(1, 5));
    EXPECT_EQ(patterns_reversed(0, 2), patterns(0, 6));
    EXPECT_EQ(patterns_reversed(1, 2), patterns(1, 6));
    EXPECT_EQ(patterns_reversed(0, 3), patterns(0, 7));
    EXPECT_EQ(patterns_reversed(1, 3), patterns(1, 7));
    EXPECT_EQ(patterns_reversed(0, 4), patterns(0, 0));
    EXPECT_EQ(patterns_reversed(1, 4), patterns(1, 0));
    EXPECT_EQ(patterns_reversed(0, 5), patterns(0, 1));
    EXPECT_EQ(patterns_reversed(1, 5), patterns(1, 1));
    EXPECT_EQ(patterns_reversed(0, 6), patterns(0, 2));
    EXPECT_EQ(patterns_reversed(1, 6), patterns(1, 2));
    EXPECT_EQ(patterns_reversed(0, 7), patterns(0, 3));
    EXPECT_EQ(patterns_reversed(1, 7), patterns(1, 3));
}

TEST(HirschbergMyers, myers_get_query_pattern)
{
    CGA_CONSTEXPR int32_t word_size = sizeof(WordType) * CHAR_BIT;
    static_assert(word_size == 32, "This test assumes word_size = 32bit.");
    using test::compute_myers_preprocess_matrix;
    using test::myers_get_query_pattern_test;
    std::string query =
        "AACCGGTTACGTACGT"
        "AAACCCGGGTTTACGT"
        "AAACCCGGGTTTACG";
    std::vector<WordType> patterns_0 = myers_get_query_pattern_test(query, 0, 'A', false);
    std::vector<WordType> patterns_1 = myers_get_query_pattern_test(query, 1, 'A', false);
    ASSERT_EQ(get_size(patterns_0), get_size(patterns_1));
    int32_t const n = get_size(patterns_0);
    for (int32_t i = 0; i < n; ++i)
    {
        std::string shifted_query  = std::string(query.begin() + i, query.end());
        matrix<WordType> shifted_p = compute_myers_preprocess_matrix(shifted_query);
        EXPECT_EQ(patterns_0[i], shifted_p(0, 0)) << "for shift:" << i << std::endl;
        if (get_size(shifted_query) > word_size)
        {
            ASSERT_EQ(shifted_p.num_rows(), 2);
            EXPECT_EQ(patterns_1[i], shifted_p(1, 0)) << "for shift:" << i << std::endl;
        }
        else
        {
            EXPECT_EQ(patterns_1[i], WordType(0)) << "for shift:" << i << std::endl;
        }
    }
}

TEST(HirschbergMyers, myers_get_query_pattern_reverse)
{
    CGA_CONSTEXPR int32_t word_size = sizeof(WordType) * CHAR_BIT;
    static_assert(word_size == 32, "This test assumes word_size = 32bit.");
    using test::compute_myers_preprocess_matrix;
    using test::myers_get_query_pattern_test;
    std::string query =
        "AACCGGTTACGTACGT"
        "AAACCCGGGTTTACGT"
        "AAACCCGGGTTTACG";
    std::vector<WordType> reverse_patterns_0 = myers_get_query_pattern_test(query, 0, 'A', true);
    std::vector<WordType> reverse_patterns_1 = myers_get_query_pattern_test(query, 1, 'A', true);
    int32_t const n                          = get_size(reverse_patterns_0);
    ASSERT_EQ(get_size(reverse_patterns_0), get_size(reverse_patterns_1));
    for (int32_t i = 0; i < n; ++i)
    {
        std::string shifted_end_query = std::string(query.begin(), query.end() - i);
        matrix<WordType> shifted_p    = compute_myers_preprocess_matrix(shifted_end_query);
        EXPECT_EQ(reverse_patterns_0[i], shifted_p(0, 4)) << "for shift:" << i << std::endl;
        if (get_size(shifted_end_query) > word_size)
        {
            ASSERT_EQ(shifted_p.num_rows(), 2);
            EXPECT_EQ(reverse_patterns_1[i], shifted_p(1, 4)) << "for shift:" << i << std::endl;
        }
        else
        {
            EXPECT_EQ(reverse_patterns_1[i], WordType(0)) << "for shift:" << i << std::endl;
        }
    }
}

} // namespace cudaaligner
} // namespace claragenomics

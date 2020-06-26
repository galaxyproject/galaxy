/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include "index_gpu.cuh"

namespace claragenomics
{
namespace cudamapper
{
namespace details
{
namespace index_gpu
{
void find_first_occurrences_of_representations(thrust::device_vector<representation_t>& unique_representations_d,
                                               thrust::device_vector<std::uint32_t>& first_occurrence_index_d,
                                               const thrust::device_vector<representation_t>& input_representations_d)
{
    // each element has value 1 if representation with the same index in representations_d has a different value than it's neighbour to the left, 0 otehrwise
    // underlying type is 32-bit because a scan operation will be performed on the array, so the elements should be capable of holding a number that is equal to
    // the total number of 1s in the array
    thrust::device_vector<std::uint32_t> new_value_mask_d(input_representations_d.size());

    // TODO: Currently maximum number of thread blocks is 2^31-1. This means we support representations of up to (2^31-1) * number_of_threads
    // With 256 that's (2^31-1)*2^8 ~= 2^39. If representation is 4-byte (we expect it to be 4 or 8) that's 2^39*2^2 = 2^41 = 2TB. We don't expect to hit this limit any time soon
    // The kernel can be modified to process several representation per thread to support arbitrary size
    std::uint32_t number_of_threads = 256; // arbitrary value
    std::uint32_t number_of_blocks  = (input_representations_d.size() - 1) / number_of_threads + 1;

    create_new_value_mask<<<number_of_blocks, number_of_threads>>>(input_representations_d.data().get(),
                                                                   input_representations_d.size(),
                                                                   new_value_mask_d.data().get());

    // do inclusive scan
    // for example for
    // 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20
    // 0  0  0  0 12 12 12 12 12 12 23 23 23 32 32 32 32 32 46 46 46
    // 1  0  0  0  1  0  0  0  0  0  1  0  0  1  0  0  0  0  1  0  0
    // gives
    // 1  1  1  1  2  2  2  2  2  2  3  3  3  4  4  4  4  4  5  5  5
    // meaning all elements with the same representation have the same value and those values are sorted in increasing order starting from 1
    thrust::device_vector<std::uint64_t> representation_index_mask_d(new_value_mask_d.size());
    thrust::inclusive_scan(thrust::device,
                           new_value_mask_d.begin(),
                           new_value_mask_d.end(),
                           representation_index_mask_d.begin());
    new_value_mask_d.clear();
    new_value_mask_d.shrink_to_fit();

    const std::uint64_t number_of_unique_representations = representation_index_mask_d.back(); // D2H copy

    first_occurrence_index_d.resize(number_of_unique_representations + 1); // <- +1 for the additional element
    first_occurrence_index_d.shrink_to_fit();
    unique_representations_d.resize(number_of_unique_representations);
    unique_representations_d.shrink_to_fit();

    find_first_occurrences_of_representations_kernel<<<number_of_blocks, number_of_threads>>>(representation_index_mask_d.data().get(),
                                                                                              input_representations_d.data().get(),
                                                                                              representation_index_mask_d.size(),
                                                                                              first_occurrence_index_d.data().get(),
                                                                                              unique_representations_d.data().get());
    // last element is the total number of elements in representations array
    first_occurrence_index_d.back() = input_representations_d.size(); // H2D copy
}

__global__ void create_new_value_mask(const representation_t* const representations_d,
                                      const std::size_t number_of_elements,
                                      std::uint32_t* const new_value_mask_d)
{
    std::uint64_t index = blockIdx.x * blockDim.x + threadIdx.x;

    if (index >= number_of_elements)
        return;

    if (index == 0)
    {
        new_value_mask_d[0] = 1;
    }
    else
    {
        if (representations_d[index] == representations_d[index - 1])
        {
            new_value_mask_d[index] = 0;
        }
        else
            new_value_mask_d[index] = 1;
    }
}

__global__ void find_first_occurrences_of_representations_kernel(const std::uint64_t* const representation_index_mask_d,
                                                                 const representation_t* const input_representations_d,
                                                                 const std::size_t number_of_input_elements,
                                                                 std::uint32_t* const starting_index_of_each_representation_d,
                                                                 representation_t* const unique_representations_d)
{
    // one thread per element of input_representations_d (i.e. sketch_element)
    std::uint64_t index = blockIdx.x * blockDim.x + threadIdx.x;

    if (index >= number_of_input_elements)
        return;

    if (index == 0)
    {
        starting_index_of_each_representation_d[0] = 0;
        unique_representations_d[0]                = input_representations_d[0];
    }
    else
    {
        // representation_index_mask_d gives a unique index to each representation, starting from 1, thus '-1'
        const auto representation_index_mask_for_this_index = representation_index_mask_d[index];
        if (representation_index_mask_for_this_index != representation_index_mask_d[index - 1])
        {
            // if new representation is not the same as its left neighbor
            // save the index at which that representation starts
            starting_index_of_each_representation_d[representation_index_mask_for_this_index - 1] = index;
            unique_representations_d[representation_index_mask_for_this_index - 1]                = input_representations_d[index];
        }
    }
}
} // namespace index_gpu
} // namespace details

} // namespace cudamapper
} // namespace claragenomics

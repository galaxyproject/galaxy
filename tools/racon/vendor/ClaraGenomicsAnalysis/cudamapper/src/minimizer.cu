/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <limits>
#include "minimizer.hpp"

namespace claragenomics
{
namespace cudamapper
{

Minimizer::Minimizer(representation_t representation, position_in_read_t position_in_read, DirectionOfRepresentation direction, read_id_t read_id)
    : representation_(representation)
    , position_in_read_(position_in_read)
    , direction_(direction)
    , read_id_(read_id)
{
}

representation_t Minimizer::representation() const
{
    return representation_;
}

position_in_read_t Minimizer::position_in_read() const
{
    return position_in_read_;
}

read_id_t Minimizer::read_id() const
{
    return read_id_;
}

/// \brief Apply a hash function to a representation
///
/// Because of the non-Poisson distribuition of DNA, some common sequences with common kmer-content (e.g long poly-A runs)
/// may be over-represented in sketches. By applying a hash function, kmers are mapped to representations over
/// a more uniform space. The hash function implemented here was developed by Thomas Wang and is described
/// [here](https://gist.github.com/badboy/6267743). A mask is applied to the output so that all representations are mapped
/// to a 32 bit space.
///
/// \param key the input representation
__device__ representation_t wang_hash64(representation_t key)
{
    uint64_t mask = (uint64_t(1) << 32) - 1;
    key           = (~key + (key << 21)) & mask;
    key           = key ^ key >> 24;
    key           = ((key + (key << 3)) + (key << 8)) & mask;
    key           = key ^ key >> 14;
    key           = ((key + (key << 2)) + (key << 4)) & mask;
    key           = key ^ key >> 28;
    key           = (key + (key << 31)) & mask;
    return key;
}

Minimizer::DirectionOfRepresentation Minimizer::direction() const
{
    return direction_;
}

/// \brief finds front end minimizers
///
/// Finds the minimizers of windows starting at position 0 and having window size range from 1 to window_size-1
///
/// \param minimizer_size kmer length
/// \param window_size number of kmers in one central minimizer window, kmers being shifted by one basepair each (for front end minimizers window size actually varies from 1 to window_size-1)
/// \param basepairs array of basepairs, first come basepairs for read 0, then read 1 and so on
/// \param read_id_to_basepairs_section index of the first basepair of every read (in basepairs array) and the number of basepairs in that read
/// \param window_minimizers_representation output array of representations of minimizers, grouped by reads
/// \param window_minimizers_direction output array of directions of minimizers, grouped by reads (0 - forward, 1 - reverse)
/// \param window_minimizers_position_in_read output array of positions in read of minimizers, grouped by reads
/// \param read_id_to_window_section index of first element dedicated to that read in output arrays and the number of dedicated elements (enough elements are allocated to each read to support cases where each window has a different minimizer, no need to check that condition)
/// \param read_id_to_minimizers_written how many minimizers have been written for this read already (initially zero)
__global__ void find_front_end_minimizers(const std::uint64_t minimizer_size,
                                          const std::uint64_t window_size,
                                          const char* const basepairs,
                                          const ArrayBlock* const read_id_to_basepairs_section,
                                          representation_t* const window_minimizers_representation,
                                          char* const window_minimizers_direction,
                                          position_in_read_t* const window_minimizers_position_in_read,
                                          const ArrayBlock* const read_id_to_windows_section,
                                          std::uint32_t* const read_id_to_minimizers_written,
                                          const bool hash_representations)
{
    // TODO: simplify this method similarly to find_back_end_minimizers

    if (1 == window_size)
    {
        // if 1 == window_size there are no end minimizer
        return;
    }

    const auto input_array_first_element = read_id_to_basepairs_section[blockIdx.x].first_element_;
    const auto output_arrays_offset      = read_id_to_windows_section[blockIdx.x].first_element_;

    // Dynamically allocating shared memory and assigning parts of it to different pointers
    // Everything is 8-byte alligned
    extern __shared__ std::uint64_t sm[];
    // TODO: not all arrays are needed at the same time -> reduce shared memory requirements by reusing parts of the memory
    // TODO: use sizeof to get the number of bytes
    std::uint32_t shared_memory_64_bit_elements_already_taken = 0;
    char* forward_basepair_hashes                             = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // blockDim.x elements
    shared_memory_64_bit_elements_already_taken += (blockDim.x + 7) / 8;

    char* reverse_basepair_hashes = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // blockDim.x elements
    shared_memory_64_bit_elements_already_taken += (blockDim.x + 7) / 8;

    representation_t* minimizers_representation = reinterpret_cast<representation_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // blockDim.x - (minimizer_size - 1) elements
    shared_memory_64_bit_elements_already_taken += blockDim.x - (minimizer_size - 1);

    char* minimizers_direction = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // blockDim.x - (minimizer_size - 1) elements; 0 - forward, 1 - reverse
    shared_memory_64_bit_elements_already_taken += (blockDim.x - (minimizer_size - 1) + 7) / 8;

    position_in_read_t* minimizers_position_in_read = reinterpret_cast<position_in_read_t*>(&sm[shared_memory_64_bit_elements_already_taken]);
    shared_memory_64_bit_elements_already_taken += (blockDim.x - (minimizer_size - 1) + 1) / 2;

    position_in_read_t* different_minimizer_than_neighbors = reinterpret_cast<position_in_read_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // blockDim.x - (minimizer_size - 1) elements; 0 - same, 1 - different
    shared_memory_64_bit_elements_already_taken += (blockDim.x - (minimizer_size - 1) + 1) / 2;

    representation_t* minimizer_representation_of_largest_window_from_previous_step = (&sm[shared_memory_64_bit_elements_already_taken]); // 1 element
    shared_memory_64_bit_elements_already_taken += 1;

    position_in_read_t* minimizer_position_in_read_of_largest_window_from_previous_step = reinterpret_cast<position_in_read_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // 1 element
    shared_memory_64_bit_elements_already_taken += (1 + 1) / 2;

    // local index = index in section of the output array dedicated to this read
    position_in_read_t* local_index_to_write_next_minimizer_to = reinterpret_cast<position_in_read_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // 1 element
    shared_memory_64_bit_elements_already_taken += (1 + 1) / 2;

    // TODO: Move to constant memory
    char* forward_to_reverse_complement = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // 8 elements

    if (0 == threadIdx.x)
    {
        forward_to_reverse_complement[0b000] = 0b0000;
        forward_to_reverse_complement[0b001] = 0b0100; // A -> T (0b1 -> 0b10100)
        forward_to_reverse_complement[0b010] = 0b0000;
        forward_to_reverse_complement[0b011] = 0b0111; // C -> G (0b11 -> 0b111)
        forward_to_reverse_complement[0b100] = 0b0001; // T -> A (0b10100 -> 0b1)
        forward_to_reverse_complement[0b101] = 0b0000;
        forward_to_reverse_complement[0b110] = 0b0000;
        forward_to_reverse_complement[0b111] = 0b0011; // G -> C (0b111 -> 0b11)
    }
    __syncthreads();

    // Each thread loads one basepair, making it blockDim.x basepairs. Each kmer has minimizer_size elements
    // Number of windows is equal to the number of kmers for end minimizer
    // This means a total of blockDim.x - (minimizer_size - 1) kmer can be processed in one block, where each kmer is shifted by one one basepair compared to the previous kmer
    // For blockDim.x = 6 and minimizer_size = 3 there are 6 - (3 - 1) = 4  kmers
    // 0 1 2
    //   1 2 3
    //     2 3 4
    //       3 4 5
    // If more minimizers have to be processed a new step is needed, in this case meaning
    //         4 5 6
    //           5 6 7
    //             6 7 8
    //               7 8 9
    // This means that a number of basepairs is loaded twice, but this a tradeoff for less complex code
    const std::uint16_t windows_per_loop_step = blockDim.x - (minimizer_size - 1);

    *minimizer_representation_of_largest_window_from_previous_step   = 0;
    *minimizer_position_in_read_of_largest_window_from_previous_step = 0;
    *local_index_to_write_next_minimizer_to                          = 0;

    for (std::uint32_t first_element_in_step = 0; first_element_in_step < window_size - 1; first_element_in_step += windows_per_loop_step)
    {

        // load basepairs into shared memory and calculate the lexical ordering hash
        if (first_element_in_step + threadIdx.x < window_size - 1 + minimizer_size - 1)
        { // window_size - 1 + minimizer_size - 1 -> total number of basepairs needed for all front minimizers
            const char bp                        = basepairs[input_array_first_element + first_element_in_step + threadIdx.x];
            forward_basepair_hashes[threadIdx.x] = 0b11 & (bp >> 2 ^ bp >> 1);
            reverse_basepair_hashes[threadIdx.x] = 0b11 & (forward_to_reverse_complement[0b111 & bp] >> 2 ^ forward_to_reverse_complement[0b111 & bp] >> 1);
        }
        __syncthreads();

        // First front end window covers only one minimizer (the one starting at positon 0), second minimizers starting at 0 and 1 and so one until the window which covers window_size-1 minimizers
        // For window_size = 7 and minimize_size = 3 this means:
        // window 0: 0 1 2                  (0 1 2)
        // window 1: 0 1 2 3                (0 1 2; 1 2 3)
        // widnow 2: 0 1 2 3 4              (0 1 2; 1 2 3; 2 3 4)
        // window 3: 0 1 2 3 4 5            (0 1 2; 1 2 3; 2 3 4; 3 4 5)
        // window 4: 0 1 2 3 4 5 6          (0 1 2; 1 2 3; 2 3 4; 3 4 5; 4 5 6)
        // window 5: 0 1 2 3 4 5 6 7        (0 1 2; 1 2 3; 2 3 4; 3 4 5; 4 5 6; 5 6 7)
        // If window_size > windows_per_loop_step the other windows have to be processed in other loop steps
        // For example, for blockDim.x = 6, minimizer_size = 3 (=> windows_per_loop_step = 4) and window_size = 7:
        // step 0 (first_element_in_step = 0):
        // window 0: 0 1 2                  (0 1 2)
        // window 1: 0 1 2 3                (0 1 2; 1 2 3)
        // widnow 2: 0 1 2 3 4              (0 1 2; 1 2 3; 2 3 4)
        // window 3: 0 1 2 3 4 5            (0 1 2; 1 2 3; 2 3 4; 3 4 5)
        // step 1 (first_element_in_step = 4):
        // window 4: 0 1 2 3 4 5 6          (take results for window 3 and add: 4 5 6)
        // window 5: 0 1 2 3 4 5 6 7        (take results for window 3 and add: 4 5 6; 5 6 7)
        // This means that a thread has a window assigned to it when thraedIdx.x < minimizers_per_loop (for all loops other than the last one) and
        // when first_element_in_step + threadIdx.x < window_size - 1
        const bool thread_assigned_to_a_window = first_element_in_step + threadIdx.x < window_size - 1 && threadIdx.x < windows_per_loop_step;

        // calculate minimizer for each kmer in front end windows
        if (thread_assigned_to_a_window)
        { // largest front minimizer window starts at basepar 0 and goes up to window_size -1
            representation_t forward_representation = 0;
            representation_t reverse_representation = 0;
            // TODO: It's not necessary to fully build both representations in order to determine which one is smaller. In most cases there is going to be a difference already at the first element
            for (std::uint16_t i = 0; i < minimizer_size; ++i)
            {
                forward_representation |= forward_basepair_hashes[threadIdx.x + i] << 2 * (minimizer_size - i - 1);
                reverse_representation |= reverse_basepair_hashes[threadIdx.x + i] << 2 * i;
            }

            if (hash_representations)
            {
                forward_representation = wang_hash64(forward_representation);
                reverse_representation = wang_hash64(reverse_representation);
            }

            if (forward_representation <= reverse_representation)
            {
                minimizers_representation[threadIdx.x] = forward_representation;
                minimizers_direction[threadIdx.x]      = 0;
            }
            else
            {
                minimizers_representation[threadIdx.x] = reverse_representation;
                minimizers_direction[threadIdx.x]      = 1;
            }
        }
        __syncthreads();

        representation_t window_minimizer_representation     = 0;
        position_in_read_t window_minimizer_position_in_read = 0;
        // calculate minimizer for each window
        // Start by the value of the first minimizer and iteratively compare it with the other minimizers in the window
        // If first_element_in_step != 0 there is no need to go through all minimizers in the window. One can take the minimizer of window first_element_in_step-1
        // as the current window would check exaclty the same minimizers before checking minimizer first_element_in_step
        if (thread_assigned_to_a_window)
        {
            if (first_element_in_step != 0)
            {
                window_minimizer_representation   = *minimizer_representation_of_largest_window_from_previous_step;
                window_minimizer_position_in_read = *minimizer_position_in_read_of_largest_window_from_previous_step;
                if (minimizers_representation[0] <= window_minimizer_representation)
                {
                    window_minimizer_representation   = minimizers_representation[0];
                    window_minimizer_position_in_read = first_element_in_step;
                }
            }
            else
            {
                window_minimizer_representation   = minimizers_representation[0];
                window_minimizer_position_in_read = 0;
            }
            // All threads have to wait for the largest block to finish. Probably no better solution without big restructuring
            // If there are several minimizers with the same representation only save the latest one (thus <=), others will be covered by smaller windows
            for (std::uint16_t i = 1; i <= threadIdx.x; ++i)
            {
                if (minimizers_representation[i] <= window_minimizer_representation)
                {
                    window_minimizer_representation   = minimizers_representation[i];
                    window_minimizer_position_in_read = first_element_in_step + i;
                }
            }
            minimizers_position_in_read[threadIdx.x] = window_minimizer_position_in_read;
        }
        __syncthreads();

        // only write first occurence of each minimizer to the output array
        // Hash of the last kmer in a window can be a minimizer only if it is smaller or equal than the minimizer of the previous window
        // That means that the minimizer of the current window should only be written if it is different than the one of the previous window
        // Otherwise it it the same minimizer and there is no need write to the the output array
        // Imagine that hash representation of windows are are follows (the number in the parentheses marks the position of the last occurance of the minimizer with that representation):
        // 8, 89, 898, 8987, 89878, 898785, 8987856, 89878562
        // Minimizers of these windows are
        // 8(0) 8(0) 8(2) 7(3) 7(3) 5(5) 5(5) 2(7)
        // If we use 1 to indicate the first occurence of minimizer and 0 for repretition we get
        // 1 0 1 1 0 1 0 1
        // If we do an an inclusive scan on this array we get the indices to which the unique minimizers should be written to (plus one)
        // 1 1 2 3 3 4 4 5
        // From this it's clear that only the windows whose value is larger than the one of its neighbor should write its minimizer and it should write to the element with the index of value-1
        if (first_element_in_step + threadIdx.x < window_size - 1 && threadIdx.x < windows_per_loop_step)
        {
            if (0 == first_element_in_step && 0 == threadIdx.x)
            {
                // minimizer of first window is unique for sure as it has no left neighbor
                different_minimizer_than_neighbors[0] = 1;
            }
            else
            {
                representation_t neighbors_minimizers_position_in_read = 0;
                // find left neighbor's window minimizer's position in read
                if (0 == threadIdx.x)
                {
                    neighbors_minimizers_position_in_read = *minimizer_position_in_read_of_largest_window_from_previous_step;
                }
                else
                {
                    // TODO: consider using warp shuffle instead of shared memory
                    neighbors_minimizers_position_in_read = minimizers_position_in_read[threadIdx.x - 1];
                }
                // check if it's the same minimizer
                if (neighbors_minimizers_position_in_read == minimizers_position_in_read[threadIdx.x])
                {
                    different_minimizer_than_neighbors[threadIdx.x] = 0;
                }
                else
                {
                    different_minimizer_than_neighbors[threadIdx.x] = 1;
                }
            }
        }
        __syncthreads();

        // if there are more loop steps to follow write the value and position of minimizer of the largest window
        if (first_element_in_step + windows_per_loop_step < window_size - 1 && threadIdx.x == windows_per_loop_step - 1)
        {
            *minimizer_representation_of_largest_window_from_previous_step   = window_minimizer_representation;
            *minimizer_position_in_read_of_largest_window_from_previous_step = window_minimizer_position_in_read;
        }
        // no need to sync, these two values are not used before the next sync

        // perform inclusive scan
        // different_minimizer_than_neighbors changes meaning an becomes more like "output_array_index_to_write_the_value_plus_one"
        // TODO: implement it using warp shuffle or use CUB
        if (0 == threadIdx.x)
        {
            std::uint16_t i = 0;
            different_minimizer_than_neighbors[i] += *local_index_to_write_next_minimizer_to;
            for (i = 1; i < blockDim.x - (minimizer_size - 1); ++i)
            {
                different_minimizer_than_neighbors[i] += different_minimizer_than_neighbors[i - 1];
            }
        }
        __syncthreads();

        // now save minimizers to output array
        if (first_element_in_step + threadIdx.x < window_size - 1 && threadIdx.x < windows_per_loop_step)
        {
            const std::uint32_t neighbors_write_index = 0 == threadIdx.x ? *local_index_to_write_next_minimizer_to : different_minimizer_than_neighbors[threadIdx.x - 1];
            if (neighbors_write_index < different_minimizer_than_neighbors[threadIdx.x])
            {
                const std::uint64_t output_index                 = output_arrays_offset + different_minimizer_than_neighbors[threadIdx.x] - 1;
                window_minimizers_representation[output_index]   = minimizers_representation[minimizers_position_in_read[threadIdx.x] - first_element_in_step];
                window_minimizers_direction[output_index]        = minimizers_direction[minimizers_position_in_read[threadIdx.x] - first_element_in_step];
                window_minimizers_position_in_read[output_index] = minimizers_position_in_read[threadIdx.x];
            }
        }
        __syncthreads();

        // index (plus one) to which the last window minimizer was written is the number of all unique front end window minimizers
        if (first_element_in_step + threadIdx.x == window_size - 1 - 1)
        {
            // "plus one" is already included in different_minimizer_than_neighbors as it was created by an inclusive scan
            read_id_to_minimizers_written[blockIdx.x] = different_minimizer_than_neighbors[threadIdx.x];
        }

        // if there are more loop steps to follow write the output array index of last minimizer in this loop step
        if (first_element_in_step + windows_per_loop_step <= window_size - 1 && threadIdx.x == windows_per_loop_step - 1)
        {
            *local_index_to_write_next_minimizer_to = different_minimizer_than_neighbors[threadIdx.x];
        }
    }
}

/// \brief finds central minimizers
///
/// Finds the minimizers of windows of size window_size starting at position 0 and moving by one basepair at a time
///
/// \param minimizer_size kmer length
/// \param window_size number of kmers in one window, kmers being shifted by one one basepair each
/// \param basepairs array of basepairs, first come basepairs for read 0, then read 1 and so on
/// \param read_id_to_basepairs_section index of the first basepair of every read (in basepairs array) and the number of basepairs in that read
/// \param window_minimizers_representation output array of representations of minimizers, grouped by reads
/// \param window_minimizers_direction output array of directions of minimizers, grouped by reads (0 - forward, 1 - reverse)
/// \param window_minimizers_position_in_read output array of positions in read of minimizers, grouped by reads
/// \param read_id_to_window_section index of first element dedicated to that read in output arrays and the number of dedicated elements (enough elements are allocated to each read to support cases where each window has a different minimizer, no need to check that condition)
/// \param read_id_to_minimizers_written how many minimizers have been written for this read already (initially number of front end minimizers)
__global__ void find_central_minimizers(const std::uint64_t minimizer_size,
                                        const std::uint64_t window_size,
                                        const std::uint32_t basepairs_per_thread,
                                        const char* const basepairs,
                                        const ArrayBlock* const read_id_to_basepairs_section,
                                        representation_t* const window_minimizers_representation,
                                        char* const window_minimizers_direction,
                                        position_in_read_t* const window_minimizers_position_in_read,
                                        const ArrayBlock* const read_id_to_windows_section,
                                        std::uint32_t* const read_id_to_minimizers_written,
                                        const bool hash_representations)
{
    // See find_front_end_minimizers for more details about the algorithm

    const std::uint64_t index_of_first_element_to_process_global = read_id_to_basepairs_section[blockIdx.x].first_element_;
    // Index of the element to which the first central minimizer of this read should be written. Index refers to the positions withing the whole array dedicated to all reads
    const std::uint64_t output_index_to_write_the_first_minimizer_global = read_id_to_windows_section[blockIdx.x].first_element_ + read_id_to_minimizers_written[blockIdx.x];
    const std::uint32_t basepairs_in_read                                = read_id_to_basepairs_section[blockIdx.x].block_size_;
    const std::uint32_t kmers_in_read                                    = basepairs_in_read - (minimizer_size - 1);
    const std::uint32_t windows_in_read                                  = kmers_in_read - (window_size - 1);
    const std::uint16_t basepairs_per_loop_step                          = blockDim.x * basepairs_per_thread;
    const std::uint16_t kmers_per_loop_step                              = basepairs_per_loop_step - (minimizer_size - 1);
    const std::uint16_t windows_per_loop_step                            = kmers_per_loop_step - (window_size - 1);

    // Dynamically allocating shared memory and assigning parts of it to different pointers
    // Everything is 8-byte alligned
    extern __shared__ std::uint64_t sm[];
    // TODO: not all arrays are needed at the same time -> reduce shared memory requirements by reusing parts of the memory
    // TODO: use sizeof to get the number of bytes
    std::uint32_t shared_memory_64_bit_elements_already_taken = 0;
    char* forward_basepair_hashes                             = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // basepairs_per_loop_step elements
    shared_memory_64_bit_elements_already_taken += (basepairs_per_loop_step + 7) / 8;

    char* reverse_basepair_hashes = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // basepairs_per_loop_step elements
    shared_memory_64_bit_elements_already_taken += (basepairs_per_loop_step + 7) / 8;

    representation_t* minimizers_representation = reinterpret_cast<representation_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // kmers_loop_step elements
    shared_memory_64_bit_elements_already_taken += kmers_per_loop_step;

    char* minimizers_direction = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // windows_per_loop_step elements; 0 - forward, 1 - reverse
    shared_memory_64_bit_elements_already_taken += (windows_per_loop_step + 7) / 8;

    position_in_read_t* minimizers_position_in_read = reinterpret_cast<position_in_read_t*>(&sm[shared_memory_64_bit_elements_already_taken]);
    shared_memory_64_bit_elements_already_taken += (windows_per_loop_step + 1) / 2;

    position_in_read_t* different_minimizer_than_neighbors = reinterpret_cast<position_in_read_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // windows_per_loop_step elements; 0 - same, 1 - different
    shared_memory_64_bit_elements_already_taken += (windows_per_loop_step + 1) / 2;

    position_in_read_t* minimizer_position_in_read_of_largest_window_from_previous_step = reinterpret_cast<position_in_read_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // 1 element
    shared_memory_64_bit_elements_already_taken += (1 + 1) / 2;

    position_in_read_t* local_index_to_write_next_minimizer_to = reinterpret_cast<position_in_read_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // 1 element
    shared_memory_64_bit_elements_already_taken += (1 + 1) / 2;

    // TODO: Move to constant memory
    char* forward_to_reverse_complement = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // 8 elements

    if (0 == threadIdx.x)
    {
        forward_to_reverse_complement[0b000] = 0b0000;
        forward_to_reverse_complement[0b001] = 0b0100; // A -> T (0b1 -> 0b10100)
        forward_to_reverse_complement[0b010] = 0b0000;
        forward_to_reverse_complement[0b011] = 0b0111; // C -> G (0b11 -> 0b111)
        forward_to_reverse_complement[0b100] = 0b0001; // T -> A (0b10100 -> 0b1)
        forward_to_reverse_complement[0b101] = 0b0000;
        forward_to_reverse_complement[0b110] = 0b0000;
        forward_to_reverse_complement[0b111] = 0b0011; // G -> C (0b111 -> 0b11)
    }
    __syncthreads();

    // if there are front minimizers take them into account
    if (0 != read_id_to_minimizers_written[blockIdx.x])
    {
        *minimizer_position_in_read_of_largest_window_from_previous_step = window_minimizers_position_in_read[output_index_to_write_the_first_minimizer_global - 1];
        *local_index_to_write_next_minimizer_to                          = read_id_to_minimizers_written[blockIdx.x];
    }
    else
    {
        *minimizer_position_in_read_of_largest_window_from_previous_step = 0; // N/A
        *local_index_to_write_next_minimizer_to                          = 0;
    }

    for (std::uint32_t first_element_in_step = 0; first_element_in_step < windows_in_read; first_element_in_step += windows_per_loop_step)
    {
        // load basepairs into shared memory and calculate the lexical ordering hash
        for (std::uint32_t basepair_index = threadIdx.x; basepair_index < basepairs_per_loop_step && first_element_in_step + basepair_index < basepairs_in_read; basepair_index += blockDim.x)
        {
            const char bp                           = basepairs[index_of_first_element_to_process_global + first_element_in_step + basepair_index];
            forward_basepair_hashes[basepair_index] = 0b11 & (bp >> 2 ^ bp >> 1);
            reverse_basepair_hashes[basepair_index] = 0b11 & (forward_to_reverse_complement[0b111 & bp] >> 2 ^ forward_to_reverse_complement[0b111 & bp] >> 1);
        }
        __syncthreads();

        // calculate kmer minimizers
        for (std::uint32_t kmer_index = threadIdx.x; kmer_index < kmers_per_loop_step && first_element_in_step + kmer_index < kmers_in_read; kmer_index += blockDim.x)
        {
            representation_t forward_representation = 0;
            representation_t reverse_representation = 0;
            // TODO: It's not necessary to fully build both representations in order to determine which one is smaller. In most cases there is going to be a difference already at the first element
            for (std::uint16_t i = 0; i < minimizer_size; ++i)
            {
                forward_representation |= forward_basepair_hashes[kmer_index + i] << 2 * (minimizer_size - i - 1);
                reverse_representation |= reverse_basepair_hashes[kmer_index + i] << 2 * i;
            }

            if (hash_representations)
            {
                forward_representation = wang_hash64(forward_representation);
                reverse_representation = wang_hash64(reverse_representation);
            }
            if (forward_representation <= reverse_representation)
            {
                minimizers_representation[kmer_index] = forward_representation;
                minimizers_direction[kmer_index]      = 0;
            }
            else
            {
                minimizers_representation[kmer_index] = reverse_representation;
                minimizers_direction[kmer_index]      = 1;
            }
        }
        __syncthreads();

        position_in_read_t window_minimizer_position_in_read = 0;
        // find window minimizer
        for (std::uint32_t window_index = threadIdx.x; window_index < windows_per_loop_step && first_element_in_step + window_index < windows_in_read; window_index += blockDim.x)
        {
            // assume that the minimizer of the first kmer in step is the window minimizer
            representation_t window_minimizer_representation = minimizers_representation[window_index];
            window_minimizer_position_in_read                = first_element_in_step + window_index;
            // now check the minimizers of all other windows
            for (std::uint16_t i = 1; i < window_size; ++i)
            {
                if (minimizers_representation[window_index + i] <= window_minimizer_representation)
                {
                    window_minimizer_representation   = minimizers_representation[window_index + i];
                    window_minimizer_position_in_read = first_element_in_step + window_index + i;
                }
            }
            minimizers_position_in_read[window_index] = window_minimizer_position_in_read;
        }
        __syncthreads();

        // check if the window to the left has a the same minimizer
        for (std::uint32_t window_index = threadIdx.x; window_index < windows_per_loop_step && first_element_in_step + window_index < windows_in_read; window_index += blockDim.x)
        {
            // if this is the first window in read and there were no front end minimizers than this is the first occurence of this minimizer
            if (0 == first_element_in_step + window_index && 0 == read_id_to_minimizers_written[blockIdx.x])
            {
                different_minimizer_than_neighbors[0] = 1;
            }
            else
            {
                representation_t neighbors_minimizers_position_in_read = 0;
                // find left neighbor's window minimizer's position in read
                if (0 == window_index)
                {
                    neighbors_minimizers_position_in_read = *minimizer_position_in_read_of_largest_window_from_previous_step;
                }
                else
                {
                    // TODO: consider using warp shuffle instead of shared memory
                    neighbors_minimizers_position_in_read = minimizers_position_in_read[window_index - 1];
                }
                // check if it's the same minimizer
                if (neighbors_minimizers_position_in_read == minimizers_position_in_read[window_index])
                {
                    different_minimizer_than_neighbors[window_index] = 0;
                }
                else
                {
                    different_minimizer_than_neighbors[window_index] = 1;
                }
            }
        }
        __syncthreads();

        // if there are more loop steps to follow write the position of minimizer of the last window
        // "windows_per_loop_step % blockDim.x - 1" determines the thread which processes the last window
        if (first_element_in_step + windows_per_loop_step < windows_in_read && threadIdx.x == windows_per_loop_step % blockDim.x - 1)
        {
            *minimizer_position_in_read_of_largest_window_from_previous_step = window_minimizer_position_in_read;
        }

        // perform inclusive scan
        // different_minimizer_than_neighbors changes meaning an becomes more like "output_array_index_to_write_the_value_plus_one"
        // TODO: implement it using warp shuffle or use CUB
        if (0 == threadIdx.x)
        {
            std::uint16_t i = 0;
            different_minimizer_than_neighbors[i] += *local_index_to_write_next_minimizer_to;
            for (i = 1; i < windows_per_loop_step && first_element_in_step + i < windows_in_read; ++i)
            {
                different_minimizer_than_neighbors[i] += different_minimizer_than_neighbors[i - 1];
            }
        }
        __syncthreads();

        // now save minimizers to output array
        for (std::uint32_t window_index = threadIdx.x; window_index < windows_per_loop_step && first_element_in_step + window_index < windows_in_read; window_index += blockDim.x)
        {
            // if first_element_in_loop == 0 and window_index == 0 then *local_index_to_write_next_minimizer_to is set to 0 before entering the loop
            const std::uint32_t neighbors_write_index = 0 == window_index ? *local_index_to_write_next_minimizer_to : different_minimizer_than_neighbors[window_index - 1];
            if (neighbors_write_index < different_minimizer_than_neighbors[window_index])
            {
                // output array offset added in inclusive sum
                const auto output_index                          = read_id_to_windows_section[blockIdx.x].first_element_ + different_minimizer_than_neighbors[window_index] - 1;
                window_minimizers_representation[output_index]   = minimizers_representation[minimizers_position_in_read[window_index] - first_element_in_step];
                window_minimizers_direction[output_index]        = minimizers_direction[minimizers_position_in_read[window_index] - first_element_in_step];
                window_minimizers_position_in_read[output_index] = minimizers_position_in_read[window_index];
            }
        }
        __syncthreads();

        // increase the number of written minimizers by the number of central minimizers
        // the value is increased by the write index of the last window in read
        if (first_element_in_step + windows_per_loop_step >= windows_in_read && 0 == threadIdx.x)
        {                                                                                                                                // only do it when there is not going to be new loop step
            read_id_to_minimizers_written[blockIdx.x] = different_minimizer_than_neighbors[windows_in_read - first_element_in_step - 1]; // write the index of the last window
        }

        // if there are more loop steps to follow write the output array index of the last minimizer in this loop step
        if (first_element_in_step + windows_per_loop_step < windows_in_read && 0 == threadIdx.x)
        {
            *local_index_to_write_next_minimizer_to = different_minimizer_than_neighbors[windows_per_loop_step - 1]; // index of last written minimizer + 1
        }
    }
}

/// \brief finds back end minimizers
///
/// Finds the minimizers of windows ending end the last basepair and having window size range from 1 to window_size-1
///
/// \param minimizer_size kmer length
/// \param window_size number of kmers in one central minimizer window, kmers being shifted by one basepair each (for back end minimizers window size actually varies from 1 to window_size-1)
/// \param basepairs array of basepairs, first come basepairs for read 0, then read 1 and so on
/// \param read_id_to_basepairs_section index of the first basepair of every read (in basepairs array) and the number of basepairs in that read
/// \param window_minimizers_representation output array of representations of minimizers, grouped by reads
/// \param window_minimizers_direction output array of directions of minimizers, grouped by reads (0 - forward, 1 - reverse)
/// \param window_minimizers_position_in_read output array of positions in read of minimizers, grouped by reads
/// \param read_id_to_window_section index of first element dedicated to that read in output arrays and the number of dedicated elements (enough elements are allocated to each read to support cases where each window has a different minimizer, no need to check that condition)
/// \param read_id_to_minimizers_written how many minimizers have been written for this read already (initially number of front end and central minimizers)
__global__ void find_back_end_minimizers(const std::uint64_t minimizer_size,
                                         const std::uint64_t window_size,
                                         const char* const basepairs,
                                         const ArrayBlock* const read_id_to_basepairs_section,
                                         representation_t* const window_minimizers_representation,
                                         char* const window_minimizers_direction,
                                         position_in_read_t* const window_minimizers_position_in_read,
                                         const ArrayBlock* const read_id_to_windows_section,
                                         std::uint32_t* const read_id_to_minimizers_written,
                                         const bool hash_representations)
{
    // See find_front_end_minimizers for more details about the algorithm

    if (1 == window_size)
    {
        // if 1 == window_size there are no end minimizer
        return;
    }

    // Index of first basepair which belongs to the largest back end minimizers. Index of that basepair within the read
    const auto index_of_first_element_to_process_local = read_id_to_basepairs_section[blockIdx.x].block_size_ - (window_size - 1 + minimizer_size - 1);
    // Index of first basepair which belongs to the largest back end minimizers. Index of that basepair within the whole array of basepairs for all reads
    const auto index_of_first_element_to_process_global = read_id_to_basepairs_section[blockIdx.x].first_element_ + index_of_first_element_to_process_local;
    // Index of the element to which the first back end minimizer of this read should be written. Index refers to the positions withing the section dedicate to this read
    const auto output_index_to_write_the_first_minimizer_local = read_id_to_minimizers_written[blockIdx.x];
    // Index of the element to which the first back end minimizer of this read should be written. Index refers to the positions withing the whole array dedicated to all reads
    const auto output_index_to_write_the_first_minimizer_global = read_id_to_windows_section[blockIdx.x].first_element_ + output_index_to_write_the_first_minimizer_local;

    // Dynamically allocating shared memory and assigning parts of it to different pointers
    // Everything is 8-byte alligned
    extern __shared__ std::uint64_t sm[];
    // TODO: not all arrays are needed at the same time -> reduce shared memory requirements by reusing parts of the memory
    // TODO: use sizeof to get the number of bytes
    std::uint32_t shared_memory_64_bit_elements_already_taken = 0;
    char* forward_basepair_hashes                             = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // basepairs_to_process elements
    shared_memory_64_bit_elements_already_taken += (window_size - 1 + minimizer_size - 1 + 7) / 8;

    char* reverse_basepair_hashes = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // basepairs_to_process elements
    shared_memory_64_bit_elements_already_taken += (window_size - 1 + minimizer_size - 1 + 7) / 8;

    representation_t* minimizers_representation = reinterpret_cast<representation_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // kmers_to_process elements
    shared_memory_64_bit_elements_already_taken += window_size - 1;

    char* minimizers_direction = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // kmers_to_process elements; 0 - forward, 1 - reverse
    shared_memory_64_bit_elements_already_taken += (window_size - 1 + 7) / 8;

    position_in_read_t* minimizers_position_in_read = reinterpret_cast<position_in_read_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // windows_to_process elements
    shared_memory_64_bit_elements_already_taken += (window_size - 1 + 1) / 2;

    position_in_read_t* different_minimizer_than_neighbors = reinterpret_cast<position_in_read_t*>(&sm[shared_memory_64_bit_elements_already_taken]); // windows_to_process elements; 0 - same, 1 - different
    shared_memory_64_bit_elements_already_taken += (window_size - 1 + 1) / 2;

    // TODO: Move to constant memory
    char* forward_to_reverse_complement = reinterpret_cast<char*>(&sm[shared_memory_64_bit_elements_already_taken]); // 8 elements

    if (0 == threadIdx.x)
    {
        forward_to_reverse_complement[0b000] = 0b0000;
        forward_to_reverse_complement[0b001] = 0b0100; // A -> T (0b1 -> 0b10100)
        forward_to_reverse_complement[0b010] = 0b0000;
        forward_to_reverse_complement[0b011] = 0b0111; // C -> G (0b11 -> 0b111)
        forward_to_reverse_complement[0b100] = 0b0001; // T -> A (0b10100 -> 0b1)
        forward_to_reverse_complement[0b101] = 0b0000;
        forward_to_reverse_complement[0b110] = 0b0000;
        forward_to_reverse_complement[0b111] = 0b0011; // G -> C (0b111 -> 0b11)
    }
    __syncthreads();

    // There are only window_size-1 back end windows. window_size usually has the value of a few dozens
    // Having windows_size so large that it does not fit the shared memory is unlikely
    // If that happens implement this method similarly to find_central_minimizers

    // load basepairs into shared memory and calculate the lexical ordering hash
    for (std::uint16_t basepair_index = threadIdx.x; basepair_index < window_size - 1 + minimizer_size - 1; basepair_index += blockDim.x)
    {
        const char bp                           = basepairs[index_of_first_element_to_process_global + basepair_index];
        forward_basepair_hashes[basepair_index] = 0b11 & (bp >> 2 ^ bp >> 1);
        reverse_basepair_hashes[basepair_index] = 0b11 & (forward_to_reverse_complement[0b111 & bp] >> 2 ^ forward_to_reverse_complement[0b111 & bp] >> 1);
    }
    __syncthreads();

    // calculate kmer minimizers
    // For back end minimizers the number of kmers is the same as the number of windows
    for (std::uint16_t kmer_index = threadIdx.x; kmer_index < window_size - 1; kmer_index += blockDim.x)
    {
        representation_t forward_representation = 0;
        representation_t reverse_representation = 0;
        // TODO: It's not necessary to fully build both representations in order to determine which one is smaller. In most cases there is going to be a difference already at the first element
        for (std::uint16_t i = 0; i < minimizer_size; ++i)
        {
            forward_representation |= forward_basepair_hashes[kmer_index + i] << 2 * (minimizer_size - i - 1);
            reverse_representation |= reverse_basepair_hashes[kmer_index + i] << 2 * i;
        }

        if (hash_representations)
        {
            forward_representation = wang_hash64(forward_representation);
            reverse_representation = wang_hash64(reverse_representation);
        }
        if (forward_representation <= reverse_representation)
        {
            minimizers_representation[kmer_index] = forward_representation;
            minimizers_direction[kmer_index]      = 0;
        }
        else
        {
            minimizers_representation[kmer_index] = reverse_representation;
            minimizers_direction[kmer_index]      = 1;
        }
    }
    __syncthreads();

    // find window minimizer
    for (std::uint16_t window_index = threadIdx.x; window_index < window_size - 1; window_index += blockDim.x)
    {
        // assume that the first kmer in the window is the minimizer
        representation_t window_minimizer_representation     = minimizers_representation[window_index];
        position_in_read_t window_minimizer_position_in_read = index_of_first_element_to_process_local + window_index;
        // now check other kmers in the window (note that this the back end minimizer, so not all windows have the same length)
        for (std::uint16_t i = 1; window_index + i < window_size - 1; ++i)
        {
            if (minimizers_representation[window_index + i] <= window_minimizer_representation)
            {
                window_minimizer_representation   = minimizers_representation[window_index + i];
                window_minimizer_position_in_read = index_of_first_element_to_process_local + window_index + i;
            }
        }
        minimizers_position_in_read[window_index] = window_minimizer_position_in_read;
    }
    __syncthreads();

    // check if the window to the left has a the same minimizer
    for (std::uint16_t window_index = threadIdx.x; window_index < window_size - 1; window_index += blockDim.x)
    {
        representation_t neighbors_minimizers_position_in_read = 0;
        // find left neighbor's window minimizer's position in read
        if (0 == window_index)
        {
            // if this is the first window take the position of the minimizer of the last central minimizer
            neighbors_minimizers_position_in_read = window_minimizers_position_in_read[output_index_to_write_the_first_minimizer_global - 1];
        }
        else
        {
            // TODO: consider using warp shuffle instead of shared memory
            neighbors_minimizers_position_in_read = minimizers_position_in_read[window_index - 1];
        }
        // check if it's the same minimizer
        if (neighbors_minimizers_position_in_read == minimizers_position_in_read[window_index])
        {
            different_minimizer_than_neighbors[window_index] = 0;
        }
        else
        {
            different_minimizer_than_neighbors[window_index] = 1;
        }
    }
    __syncthreads();

    // perform inclusive scan
    // different_minimizer_than_neighbors changes meaning an becomes more like "output_array_index_to_write_the_value_plus_one"
    // TODO: implement it using warp shuffle or use CUB
    if (0 == threadIdx.x)
    {
        // read_id_to_minimizers_written[blockIdx.x] is the index of the last written plus one
        different_minimizer_than_neighbors[0] += output_index_to_write_the_first_minimizer_local;
        for (std::uint16_t i = 1; i < window_size - 1; ++i)
        {
            different_minimizer_than_neighbors[i] += different_minimizer_than_neighbors[i - 1];
        }
    }
    __syncthreads();

    // now save minimizers to output array
    for (std::uint16_t window_index = threadIdx.x; window_index < window_size - 1; window_index += blockDim.x)
    {
        // different_minimizer_than_neighbors contians an inclusive scan, i.e. it's index_to_write_to + 1
        const std::uint32_t neighbors_write_index = 0 == window_index ? output_index_to_write_the_first_minimizer_local : different_minimizer_than_neighbors[window_index - 1];
        if (neighbors_write_index < different_minimizer_than_neighbors[window_index])
        {
            // to get the actual index to write to do -1 to different_minimizer_than_neighbors
            const auto output_index = read_id_to_windows_section[blockIdx.x].first_element_ + different_minimizer_than_neighbors[window_index] - 1;
            // substract index_of_first_element_to_process_local to get the index in shared memory
            window_minimizers_representation[output_index]   = minimizers_representation[minimizers_position_in_read[window_index] - index_of_first_element_to_process_local];
            window_minimizers_direction[output_index]        = minimizers_direction[minimizers_position_in_read[window_index] - index_of_first_element_to_process_local];
            window_minimizers_position_in_read[output_index] = minimizers_position_in_read[window_index];
        }
    }
    __syncthreads();

    // save the write index of the last written minimizer
    if (0 == threadIdx.x)
    {
        read_id_to_minimizers_written[blockIdx.x] = different_minimizer_than_neighbors[window_size - 1 - 1];
    }
}

/// \brief packs minimizers of different reads together
///
/// window_minimizers_representation, window_minimizers_position_in_read and window_minimizers_direction all allocate one element for each window in the read.
/// Many windows share the same minimizer and each minimizer is written only once, meaning many elements do not contain minimizers.
/// This function creates new arrays where such elements do not exist.
/// Note that in the input arrays all minimizers of one read are written consecutively, i.e. [read 0 minimizers], [read 0 junk], [read 1 minimizers], [read 1 junk], [read 2 minimizers]...
///
/// \param window_minimizers_representation array of representations of minimizers, grouped by reads
/// \param window_minimizers_position_in_read array of positions in read of minimizers, grouped by reads
/// \param window_minimizers_direction array of directions of minimizers, grouped by reads (0 - forward, 1 - reverse)
/// \param read_id_to_windows_section index of first element dedicated to that read in input arrays and the number of dedicated elements
/// \param representations_compressed array of representations of minimizers, grouped by reads, without invalid elements between the reads
/// \param rest_compressed array of read_ids, positions_in_read and directions of reads, grouped by reads, without invalid elements between the reads
/// \param read_id_to_compressed_minimizers index of first element dedicated to that read in input arrays and the number of dedicated elements
__global__ void compress_minimizers(const representation_t* const window_minimizers_representation,
                                    const position_in_read_t* const window_minimizers_position_in_read,
                                    const char* const window_minimizers_direction,
                                    const ArrayBlock* const read_id_to_windows_section,
                                    representation_t* const representations_compressed,
                                    Minimizer::ReadidPositionDirection* const rest_compressed,
                                    const ArrayBlock* const read_id_to_compressed_minimizers,
                                    std::uint32_t offset)
{
    const auto& first_input_minimizer  = read_id_to_windows_section[blockIdx.x].first_element_;
    const auto& first_output_minimizer = read_id_to_compressed_minimizers[blockIdx.x].first_element_;
    const auto& number_of_minimizers   = read_id_to_compressed_minimizers[blockIdx.x].block_size_;

    for (std::uint32_t i = threadIdx.x; i < number_of_minimizers; i += blockDim.x)
    {
        representations_compressed[first_output_minimizer + i]        = window_minimizers_representation[first_input_minimizer + i];
        rest_compressed[first_output_minimizer + i].read_id_          = blockIdx.x + offset;
        rest_compressed[first_output_minimizer + i].position_in_read_ = window_minimizers_position_in_read[first_input_minimizer + i];
        rest_compressed[first_output_minimizer + i].direction_        = window_minimizers_direction[first_input_minimizer + i];
    }
}

Minimizer::GeneratedSketchElements Minimizer::generate_sketch_elements(const std::uint64_t number_of_reads_to_add,
                                                                       const std::uint64_t minimizer_size,
                                                                       const std::uint64_t window_size,
                                                                       const std::uint64_t read_id_of_first_read,
                                                                       const device_buffer<char>& merged_basepairs_d,
                                                                       const std::vector<ArrayBlock>& read_id_to_basepairs_section_h,
                                                                       const device_buffer<ArrayBlock>& read_id_to_basepairs_section_d,
                                                                       const bool hash_representations)
{
    // for each read find the maximum number of minimizers (one per window), determine their section in the minimizer arrays and allocate the arrays
    std::uint64_t total_windows = 0;
    std::vector<ArrayBlock> read_id_to_windows_section_h(number_of_reads_to_add, {0, 0});
    for (read_id_t read_id = 0; read_id < number_of_reads_to_add; ++read_id)
    {
        read_id_to_windows_section_h[read_id].first_element_ = total_windows;
        std::uint32_t windows                                = window_size - 1;                                  // front end minimizers
        windows += read_id_to_basepairs_section_h[read_id].block_size_ - (minimizer_size + window_size - 1) + 1; // central minimizers
        windows += window_size - 1;
        read_id_to_windows_section_h[read_id].block_size_ = windows;
        total_windows += windows;
    }

    CGA_LOG_INFO("Allocating {} bytes for read_id_to_windows_section_d", read_id_to_windows_section_h.size() * sizeof(decltype(read_id_to_windows_section_h)::value_type));
    device_buffer<decltype(read_id_to_windows_section_h)::value_type> read_id_to_windows_section_d(read_id_to_windows_section_h.size());
    CGA_CU_CHECK_ERR(cudaMemcpy(read_id_to_windows_section_d.data(),
                                read_id_to_windows_section_h.data(),
                                read_id_to_windows_section_h.size() * sizeof(decltype(read_id_to_windows_section_h)::value_type),
                                cudaMemcpyHostToDevice));

    CGA_LOG_INFO("Allocating {} bytes for window_minimizers_representation_d", total_windows * sizeof(representation_t));
    device_buffer<representation_t> window_minimizers_representation_d(total_windows);
    CGA_LOG_INFO("Allocating {} bytes for window_minimizers_direction_d", total_windows * sizeof(char));
    device_buffer<char> window_minimizers_direction_d(total_windows);
    CGA_LOG_INFO("Allocating {} bytes for window_minimizers_position_in_read_d", total_windows * sizeof(position_in_read_t));
    device_buffer<position_in_read_t> window_minimizers_position_in_read_d(total_windows);
    CGA_LOG_INFO("Allocating {} bytes for read_id_to_minimizers_written_d", number_of_reads_to_add * sizeof(std::uint32_t));
    device_buffer<std::uint32_t> read_id_to_minimizers_written_d(number_of_reads_to_add);
    // initially there are no minimizers written to the output arrays
    CGA_CU_CHECK_ERR(cudaMemset(read_id_to_minimizers_written_d.data(), 0, number_of_reads_to_add * sizeof(std::uint32_t)));

    // *** front end minimizers ***
    std::uint32_t num_of_basepairs_for_front_minimizers = (window_size - 1) + minimizer_size - 1;
    std::uint32_t num_of_threads                        = std::min(num_of_basepairs_for_front_minimizers, 64u);
    // largest window in end minimizers has the size of window_size-1, meaning it covers window_size-1 + minimizer_size - 1 basepairs
    const std::uint32_t basepairs_for_end_minimizers = (window_size - 1 + minimizer_size - 1);
    const std::uint32_t kmers_for_end_minimizers     = window_size - 1; // for end minimizers number of kmers is the as the number of windows because the last window has only one kmer
    const std::uint32_t windows_for_end_minimizers   = window_size - 1;
    // determine total ammount for shared memory needed (see kernel for clarification)
    // shared memeory is alligned to 8 bytes, so for 1-byte variables (x+7)/8 values are allocate (for 10 1-byte elements (10+7)/8=17/8=2 8-byte elements are allocated, instead of 10/1=1 which would be wrong)
    // the final number of allocated 8-byte values is multiplied by 8 at the end in order to get number of bytes needed
    std::uint32_t shared_memory_for_kernel = 0;
    shared_memory_for_kernel += (basepairs_for_end_minimizers + 7) / 8; // forward basepairs (char)
    shared_memory_for_kernel += (basepairs_for_end_minimizers + 7) / 8; // reverse basepairs (char)
    shared_memory_for_kernel += (kmers_for_end_minimizers);             // representations of minimizers (representation_t)
    shared_memory_for_kernel += (windows_for_end_minimizers + 7) / 8;   // directions of representations of minimizers (char)
    shared_memory_for_kernel += (windows_for_end_minimizers + 1) / 2;   // position_in_read of minimizers (position_in_read_t)
    shared_memory_for_kernel += (windows_for_end_minimizers + 1) / 2;   // does the window have a different minimizer than its left neighbor (position_in_read_t)
    shared_memory_for_kernel += 1;                                      // representation from previous step
    shared_memory_for_kernel += (1 + 1) / 2;                            // position from previous step (char)
    shared_memory_for_kernel += (1 + 1) / 2;                            // inclusive sum from previous step (position_in_read_t)
    shared_memory_for_kernel += 8 / 8;                                  // forward -> reverse complement conversion (char)

    shared_memory_for_kernel *= 8; // before it the number of 8-byte values, now get the number of bytes

    CGA_LOG_INFO("Launching find_front_end_minimizers with {} bytes of shared memory", shared_memory_for_kernel);
    find_front_end_minimizers<<<number_of_reads_to_add, num_of_threads, shared_memory_for_kernel>>>(minimizer_size,
                                                                                                    window_size,
                                                                                                    merged_basepairs_d.data(),
                                                                                                    read_id_to_basepairs_section_d.data(),
                                                                                                    window_minimizers_representation_d.data(),
                                                                                                    window_minimizers_direction_d.data(),
                                                                                                    window_minimizers_position_in_read_d.data(),
                                                                                                    read_id_to_windows_section_d.data(),
                                                                                                    read_id_to_minimizers_written_d.data(),
                                                                                                    hash_representations);
    CGA_CU_CHECK_ERR(cudaDeviceSynchronize());

    // *** central minimizers ***
    const std::uint32_t basepairs_per_thread    = 8;  // arbitrary, tradeoff between the number of thread blocks that can be scheduled simultaneously and the number of basepairs which have to be loaded multiple times beacuse only basepairs_per_thread*num_of_threads-(window_size_ + minimizer_size_ - 1) + 1 can be processed at once, i.e. window_size+minimizer_size-2 basepairs have to be loaded again
    num_of_threads                              = 64; // arbitrary
    const std::uint32_t basepairs_in_loop_step  = num_of_threads * basepairs_per_thread;
    const std::uint32_t minimizers_in_loop_step = basepairs_in_loop_step - minimizer_size + 1;
    const std::uint32_t windows_in_loop_step    = minimizers_in_loop_step - window_size + 1;
    //const std::uint32_t windows_in_loop_step = num_of_threads*basepairs_per_thread - (window_size + minimizer_size - 1) + 1;
    shared_memory_for_kernel = 0;
    shared_memory_for_kernel += (basepairs_in_loop_step + 7) / 8; // forward basepairs (char)
    shared_memory_for_kernel += (basepairs_in_loop_step + 7) / 8; // reverse basepairs (char)
    shared_memory_for_kernel += minimizers_in_loop_step;          // representations of minimizers (representation_t)
    shared_memory_for_kernel += (windows_in_loop_step + 7) / 8;   // directions of representations of minimizers (char)
    shared_memory_for_kernel += (windows_in_loop_step + 1) / 2;   // position_in_read of minimizers (position_in_read_t)
    shared_memory_for_kernel += (windows_in_loop_step + 1) / 2;   // does the window have a different minimizer than its left neighbor
    shared_memory_for_kernel += (1 + 1) / 2;                      // position from previous step (char)
    shared_memory_for_kernel += (1 + 1) / 2;                      // inclusive sum from previous step (position_in_read_t)
    shared_memory_for_kernel += 8 / 8;                            // forward -> reverse complement conversion (char)

    shared_memory_for_kernel *= 8; // before it the number of 8-byte values, now get the number of bytes

    CGA_LOG_INFO("Launching find_central_minimizers with {} bytes of shared memory", shared_memory_for_kernel);
    find_central_minimizers<<<number_of_reads_to_add, num_of_threads, shared_memory_for_kernel>>>(minimizer_size,
                                                                                                  window_size,
                                                                                                  basepairs_per_thread,
                                                                                                  merged_basepairs_d.data(),
                                                                                                  read_id_to_basepairs_section_d.data(),
                                                                                                  window_minimizers_representation_d.data(),
                                                                                                  window_minimizers_direction_d.data(),
                                                                                                  window_minimizers_position_in_read_d.data(),
                                                                                                  read_id_to_windows_section_d.data(),
                                                                                                  read_id_to_minimizers_written_d.data(),
                                                                                                  hash_representations);
    CGA_CU_CHECK_ERR(cudaDeviceSynchronize());

    // *** back end minimizers ***
    num_of_threads = 64;
    // largest window should fit shared memory
    shared_memory_for_kernel = 0;
    shared_memory_for_kernel += (basepairs_for_end_minimizers + 7) / 8; // forward basepairs (char)
    shared_memory_for_kernel += (basepairs_for_end_minimizers + 7) / 8; // reverse basepairs (char)
    shared_memory_for_kernel += kmers_for_end_minimizers;               // representations of minimizers (representation_t)
    shared_memory_for_kernel += (kmers_for_end_minimizers + 7) / 8;     // directions of representations of minimizers (char)
    shared_memory_for_kernel += (windows_for_end_minimizers + 1) / 2;   // position_in_read of minimizers (position_in_read_t)
    shared_memory_for_kernel += (windows_for_end_minimizers + 1) / 2;   // does the window have a different minimizer than its left neighbor
    shared_memory_for_kernel += 8 / 8;                                  // forward -> reverse complement conversion (char)

    shared_memory_for_kernel *= 8; // before it the number of 8-byte values, now get the number of bytes

    CGA_LOG_INFO("Launching find_back_end_minimizers with {} bytes of shared memory", shared_memory_for_kernel);
    find_back_end_minimizers<<<number_of_reads_to_add, num_of_threads, shared_memory_for_kernel>>>(minimizer_size,
                                                                                                   window_size,
                                                                                                   merged_basepairs_d.data(),
                                                                                                   read_id_to_basepairs_section_d.data(),
                                                                                                   window_minimizers_representation_d.data(),
                                                                                                   window_minimizers_direction_d.data(),
                                                                                                   window_minimizers_position_in_read_d.data(),
                                                                                                   read_id_to_windows_section_d.data(),
                                                                                                   read_id_to_minimizers_written_d.data(),
                                                                                                   hash_representations);
    CGA_CU_CHECK_ERR(cudaDeviceSynchronize());

    std::vector<std::uint32_t> read_id_to_minimizers_written_h(number_of_reads_to_add);

    CGA_CU_CHECK_ERR(cudaMemcpy(read_id_to_minimizers_written_h.data(),
                                read_id_to_minimizers_written_d.data(),
                                read_id_to_minimizers_written_h.size() * sizeof(decltype(read_id_to_minimizers_written_h)::value_type),
                                cudaMemcpyDeviceToHost));
    CGA_LOG_INFO("Deallocating {} bytes from read_id_to_minimizers_written_d", read_id_to_minimizers_written_d.size() * sizeof(decltype(read_id_to_minimizers_written_d)::value_type));
    read_id_to_minimizers_written_d.free();

    // *** remove unused elemets from the window minimizers arrays ***
    // In window_minimizers_representation_d and other arrays enough space was allocated to support cases where each window has a different minimizers. In reality many neighboring windows share the same mininizer
    // As a result there are areas of meaningless data between minimizers belonging to different reads (space_allocated_for_all_possible_minimizers_of_a_read - space_needed_for_the_actuall_minimizers)
    // At this point all mininizer are put together (compressed) so that the last minimizer of one read is next to the first minimizer of another read
    // Data is organized in two arrays in order to support usage of thrust::stable_sort_by_key. One contains representations (key) and the other the rest (values)
    std::vector<ArrayBlock> read_id_to_compressed_minimizers_h(number_of_reads_to_add, {0, 0});
    std::uint64_t total_minimizers = 0;
    for (std::size_t read_id = 0; read_id < read_id_to_minimizers_written_h.size(); ++read_id)
    {
        read_id_to_compressed_minimizers_h[read_id].first_element_ = total_minimizers;
        read_id_to_compressed_minimizers_h[read_id].block_size_    = read_id_to_minimizers_written_h[read_id];
        total_minimizers += read_id_to_minimizers_written_h[read_id];
    }

    CGA_LOG_INFO("Allocating {} bytes for read_id_to_compressed_minimizers_d", read_id_to_compressed_minimizers_h.size() * sizeof(decltype(read_id_to_compressed_minimizers_h)::value_type));
    device_buffer<decltype(read_id_to_compressed_minimizers_h)::value_type> read_id_to_compressed_minimizers_d(read_id_to_compressed_minimizers_h.size());
    CGA_CU_CHECK_ERR(cudaMemcpy(read_id_to_compressed_minimizers_d.data(),
                                read_id_to_compressed_minimizers_h.data(),
                                read_id_to_compressed_minimizers_h.size() * sizeof(decltype(read_id_to_compressed_minimizers_h)::value_type),
                                cudaMemcpyHostToDevice));

    CGA_LOG_INFO("Allocating {} bytes for representations_compressed_d", total_minimizers * sizeof(representation_t));
    device_buffer<representation_t> representations_compressed_d(total_minimizers);
    // rest = position_in_read, direction and read_id
    CGA_LOG_INFO("Allocating {} bytes for rest_compressed_d", total_minimizers * sizeof(ReadidPositionDirection));
    device_buffer<ReadidPositionDirection> rest_compressed_d(total_minimizers);

    CGA_LOG_INFO("Launching compress_minimizers with {} bytes of shared memory", 0);
    compress_minimizers<<<number_of_reads_to_add, 128>>>(window_minimizers_representation_d.data(),
                                                         window_minimizers_position_in_read_d.data(),
                                                         window_minimizers_direction_d.data(),
                                                         read_id_to_windows_section_d.data(),
                                                         representations_compressed_d.data(),
                                                         rest_compressed_d.data(),
                                                         read_id_to_compressed_minimizers_d.data(),
                                                         read_id_of_first_read);
    CGA_CU_CHECK_ERR(cudaDeviceSynchronize());

    // free these arrays as they are not needed anymore
    CGA_LOG_INFO("Deallocating {} bytes from window_minimizers_representation_d", window_minimizers_representation_d.size() * sizeof(decltype(window_minimizers_representation_d)::value_type));
    window_minimizers_representation_d.free();
    CGA_LOG_INFO("Deallocating {} bytes from window_minimizers_direction_d", window_minimizers_direction_d.size() * sizeof(decltype(window_minimizers_direction_d)::value_type));
    window_minimizers_direction_d.free();
    CGA_LOG_INFO("Deallocating {} bytes from window_minimizers_position_in_read_d", window_minimizers_position_in_read_d.size() * sizeof(decltype(window_minimizers_position_in_read_d)::value_type));
    window_minimizers_position_in_read_d.free();
    CGA_LOG_INFO("Deallocating {} bytes from read_id_to_compressed_minimizers_d", read_id_to_compressed_minimizers_d.size() * sizeof(decltype(read_id_to_compressed_minimizers_d)::value_type));
    read_id_to_compressed_minimizers_d.free();
    CGA_LOG_INFO("Deallocating {} bytes from read_id_to_windows_section_d", read_id_to_windows_section_d.size() * sizeof(decltype(read_id_to_windows_section_d)::value_type));
    read_id_to_windows_section_d.free();

    return {std::move(representations_compressed_d),
            std::move(rest_compressed_d)};
}

} // namespace cudamapper
} // namespace claragenomics

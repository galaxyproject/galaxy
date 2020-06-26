/*
* Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
*
* NVIDIA CORPORATION and its licensors retain all intellectual property
* and proprietary rights in and to this software, related documentation
* and any modifications thereto.  Any use, reproduction, disclosure or
* distribution of this software and related documentation without an express
* license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

#include <chrono>
#include <getopt.h>
#include <iostream>
#include <string>
#include <deque>
#include <mutex>
#include <future>
#include <thread>
#include <atomic>

#include <claragenomics/logging/logging.hpp>
#include <claragenomics/io/fasta_parser.hpp>
#include <claragenomics/utils/cudautils.hpp>

#include <claragenomics/cudamapper/index.hpp>
#include <claragenomics/cudamapper/matcher.hpp>
#include <claragenomics/cudamapper/overlapper.hpp>
#include "overlapper_triggered.hpp"

static struct option options[] = {
    {"window-size", required_argument, 0, 'w'},
    {"kmer-size", required_argument, 0, 'k'},
    {"index-size", required_argument, 0, 'i'},
    {"target-index-size", required_argument, 0, 't'},
    {"help", no_argument, 0, 'h'},
};

void help(int32_t exit_code);

int main(int argc, char* argv[])
{
    claragenomics::logging::Init();

    uint32_t k               = 15;
    uint32_t w               = 15;
    size_t index_size        = 10000;
    size_t target_index_size = 10000;
    std::string optstring    = "t:i:k:w:h";
    uint32_t argument;
    while ((argument = getopt_long(argc, argv, optstring.c_str(), options, nullptr)) != -1)
    {
        switch (argument)
        {
        case 'k':
            k = atoi(optarg);
            break;
        case 'w':
            w = atoi(optarg);
            break;
        case 'i':
            index_size = atoi(optarg);
            break;
        case 't':
            target_index_size = atoi(optarg);
            break;
        case 'h':
            help(0);
        default:
            exit(1);
        }
    }

    if (k > claragenomics::cudamapper::Index::maximum_kmer_size())
    {
        std::cerr << "kmer of size " << k << " is not allowed, maximum k = " << claragenomics::cudamapper::Index::maximum_kmer_size() << std::endl;
        exit(1);
    }

    // Check remaining argument count.
    if ((argc - optind) < 2)
    {
        std::cerr << "Invalid inputs. Please refer to the help function." << std::endl;
        help(1);
    }

    std::string query_filepath  = std::string(argv[optind++]);
    std::string target_filepath = std::string(argv[optind++]);

    bool all_to_all = false;
    if (query_filepath == target_filepath)
    {
        all_to_all        = true;
        target_index_size = index_size;
        std::cerr << "NOTE - Since query and target files are same, activating all_to_all mode. Query index size used for both files." << std::endl;
    }

    std::unique_ptr<claragenomics::io::FastaParser> query_parser = claragenomics::io::create_fasta_parser(query_filepath);
    int32_t queries                                              = query_parser->get_num_seqences();

    std::unique_ptr<claragenomics::io::FastaParser> target_parser = claragenomics::io::create_fasta_parser(target_filepath);
    int32_t targets                                               = target_parser->get_num_seqences();

    std::cerr << "Query " << query_filepath << " index " << queries << std::endl;
    std::cerr << "Target " << target_filepath << " index " << targets << std::endl;

    // Data structure for holding overlaps to be written out
    std::mutex overlaps_writer_mtx;
    std::deque<std::vector<claragenomics::cudamapper::Overlap>> overlaps_to_write;

    // Function for adding new overlaps to writer
    auto add_overlaps_to_write_queue = [&overlaps_to_write, &overlaps_writer_mtx](claragenomics::cudamapper::Overlapper& overlapper,
                                                                                  thrust::device_vector<claragenomics::cudamapper::Anchor>& anchors,
                                                                                  const claragenomics::cudamapper::Index& index_query,
                                                                                  const claragenomics::cudamapper::Index& index_target) {
        CGA_NVTX_RANGE(profiler, "add_overlaps_to_write_queue");
        overlaps_writer_mtx.lock();
        overlaps_to_write.push_back(std::vector<claragenomics::cudamapper::Overlap>());
        overlapper.get_overlaps(overlaps_to_write.back(), anchors, index_query, index_target);
        if (0 == overlaps_to_write.back().size())
        {
            overlaps_to_write.pop_back();
        }
        overlaps_writer_mtx.unlock();
    };

    // Start async thread for writing out PAF
    auto overlaps_writer_func = [&overlaps_to_write, &overlaps_writer_mtx]() {
        while (true)
        {
            bool done = false;
            overlaps_writer_mtx.lock();
            if (!overlaps_to_write.empty())
            {
                CGA_NVTX_RANGE(profile, "overlaps_writer");
                std::vector<claragenomics::cudamapper::Overlap>& overlaps = overlaps_to_write.front();
                // An empty overlap vector indicates end of processing.
                if (overlaps.size() > 0)
                {
                    claragenomics::cudamapper::Overlapper::print_paf(overlaps);
                    overlaps_to_write.pop_front();
                    overlaps_to_write.shrink_to_fit();
                }
                else
                {
                    done = true;
                }
            }
            overlaps_writer_mtx.unlock();
            if (done)
            {
                break;
            }
            std::this_thread::yield();
        }
    };
    std::future<void> overlap_result(std::async(std::launch::async, overlaps_writer_func));

    claragenomics::cudamapper::OverlapperTriggered overlapper;

    // Track overall time
    std::chrono::milliseconds index_time      = std::chrono::duration_values<std::chrono::milliseconds>::zero();
    std::chrono::milliseconds matcher_time    = std::chrono::duration_values<std::chrono::milliseconds>::zero();
    std::chrono::milliseconds overlapper_time = std::chrono::duration_values<std::chrono::milliseconds>::zero();

    for (std::int32_t query_start_index = 0; query_start_index < queries; query_start_index += index_size)
    { // outer loop over query
        std::int32_t query_end_index = std::min(query_start_index + index_size, static_cast<size_t>(queries));

        std::cerr << "Query range: " << query_start_index << " - " << query_end_index - 1 << std::endl;

        std::unique_ptr<claragenomics::cudamapper::Index> query_index(nullptr);
        std::unique_ptr<claragenomics::cudamapper::Index> target_index(nullptr);
        std::unique_ptr<claragenomics::cudamapper::Matcher> matcher(nullptr);

        {
            CGA_NVTX_RANGE(profiler, "generate_query_index");
            auto start_time = std::chrono::high_resolution_clock::now();
            query_index     = claragenomics::cudamapper::Index::create_index(*query_parser,
                                                                         query_start_index,
                                                                         query_end_index,
                                                                         k,
                                                                         w);
            index_time += std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time);
            std::cerr << "Query index generation time: " << std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time).count() << "ms" << std::endl;
        }

        std::int32_t target_start_index = 0;
        // If all_to_all mode, then we can optimzie by starting the target sequences from the same index as
        // query because all indices before the current query index are guaranteed to have been processed in
        // a2a mapping.
        if (all_to_all)
        {
            target_start_index = query_start_index;
        }
        for (; target_start_index < targets; target_start_index += target_index_size)
        {
            std::int32_t target_end_index = std::min(target_start_index + target_index_size, static_cast<size_t>(targets));

            std::cerr << "Target range: " << target_start_index << " - " << target_end_index - 1 << std::endl;

            {
                CGA_NVTX_RANGE(profiler, "generate_target_index");
                auto start_time = std::chrono::high_resolution_clock::now();
                target_index    = claragenomics::cudamapper::Index::create_index(*target_parser,
                                                                              target_start_index,
                                                                              target_end_index,
                                                                              k,
                                                                              w);
                index_time += std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time);
                std::cerr << "Target index generation time: " << std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time).count() << "ms" << std::endl;
            }
            {
                CGA_NVTX_RANGE(profiler, "generate_matcher");
                auto start_time = std::chrono::high_resolution_clock::now();
                matcher         = claragenomics::cudamapper::Matcher::create_matcher(*query_index,
                                                                             *target_index);
                matcher_time += std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time);
                std::cerr << "Matcher generation time: " << std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time).count() << "ms" << std::endl;
            }
            {
                CGA_NVTX_RANGE(profiler, "generate_overlaps");
                auto start_time = std::chrono::high_resolution_clock::now();
                add_overlaps_to_write_queue(overlapper, matcher->anchors(), *query_index, *target_index);
                overlapper_time += std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time);
                std::cerr << "Overlapper time: " << std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time).count() << "ms" << std::endl;
            }
        }
    }

    // Insert empty overlap vector to denote end of processing.
    // The lambda function for adding overlaps to queue ensures that no empty
    // overlaps are added to the queue so as not to confuse it with the
    // empty overlap inserted to indicate end of processing.
    auto start_time = std::chrono::high_resolution_clock::now();
    overlaps_writer_mtx.lock();
    overlaps_to_write.push_back(std::vector<claragenomics::cudamapper::Overlap>());
    overlaps_writer_mtx.unlock();
    auto paf_time = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::high_resolution_clock::now() - start_time);

    std::cerr << "\n\n"
              << std::endl;
    std::cerr << "Index execution time: " << index_time.count() << "ms" << std::endl;
    std::cerr << "Matcher execution time: " << matcher_time.count() << "ms" << std::endl;
    std::cerr << "Overlap detection execution time: " << overlapper_time.count() << "ms" << std::endl;
    std::cerr << "PAF detection execution time: " << paf_time.count() << "ms" << std::endl;

    // Sync overlap writer threads.
    overlap_result.get();

    return 0;
}

void help(int32_t exit_code = 0)
{
    std::cerr <<
        R"(Usage: cudamapper [options ...] <query_sequences> <target_sequences>
     <sequences>
        Input file in FASTA/FASTQ format (can be compressed with gzip)
        containing sequences used for all-to-all overlapping
     options:
        -k, --kmer-size
            length of kmer to use for minimizers [15] (Max=)"
              << claragenomics::cudamapper::Index::maximum_kmer_size() << ")"
              << R"(
        -w, --window-size
            length of window to use for minimizers [15])"
              << R"(
        -i, --index-size
            length of batch size used for query [10000])"
              << R"(
        -t --target-index-size
            length of batch sized used for target [10000])"
              << std::endl;

    exit(exit_code);
}

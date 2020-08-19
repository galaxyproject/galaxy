#include <getopt.h>

#include <cstdint>
#include <string>
#include <iostream>
#include <exception>

#include "sequence.hpp"

#include "spoa/spoa.hpp"
#include "bioparser/bioparser.hpp"

static const std::string version = "v3.0.1";

static struct option options[] = {
    {"algorithm", required_argument, nullptr, 'l'},
    {"result", required_argument, nullptr, 'r'},
    {"dot", required_argument, nullptr, 'd'},
    {"version", no_argument, nullptr, 'v'},
    {"help", no_argument, nullptr, 'h'},
    {nullptr, 0, nullptr, 0}
};

void help();

int main(int argc, char** argv) {

    std::int8_t m = 5;
    std::int8_t n = -4;
    std::int8_t g = -8;
    std::int8_t e = -6;
    std::int8_t q = -10;
    std::int8_t c = -4;

    std::uint8_t algorithm = 0;
    std::uint8_t result = 0;

    std::string dot_path = "";

    char opt;
    while ((opt = getopt_long(argc, argv, "m:n:g:e:q:c:l:r:d:h", options, nullptr)) != -1) {
        switch (opt) {
            case 'm': m = atoi(optarg); break;
            case 'n': n = atoi(optarg); break;
            case 'g': g = atoi(optarg); break;
            case 'e': e = atoi(optarg); break;
            case 'q': q = atoi(optarg); break;
            case 'c': c = atoi(optarg); break;
            case 'l': algorithm = atoi(optarg); break;
            case 'r': result = atoi(optarg); break;
            case 'd': dot_path = optarg; break;
            case 'v': std::cout << version << std::endl; return 0;
            case 'h': help(); return 0;
            default: return 1;
        }
    }

    if (optind >= argc) {
        std::cerr << "[spoa::] error: missing input file!" << std::endl;
        help();
        return 1;
    }

    std::string sequences_path = argv[optind];

    auto is_suffix = [](const std::string& src, const std::string& suffix) -> bool {
        if (src.size() < suffix.size()) {
            return false;
        }
        return src.compare(src.size() - suffix.size(), suffix.size(), suffix) == 0;
    };

    std::unique_ptr<bioparser::Parser<spoa::Sequence>> sparser = nullptr;

    if (is_suffix(sequences_path, ".fasta") || is_suffix(sequences_path, ".fa") ||
        is_suffix(sequences_path, ".fasta.gz") || is_suffix(sequences_path, ".fa.gz")) {
        sparser = bioparser::createParser<bioparser::FastaParser, spoa::Sequence>(
            sequences_path);
    } else if (is_suffix(sequences_path, ".fastq") || is_suffix(sequences_path, ".fq") ||
        is_suffix(sequences_path, ".fastq.gz") || is_suffix(sequences_path, ".fq.gz")) {
        sparser = bioparser::createParser<bioparser::FastqParser, spoa::Sequence>(
            sequences_path);
    } else {
        std::cerr << "[spoa::] error: file " << sequences_path <<
            " has unsupported format extension (valid extensions: .fasta, "
            ".fasta.gz, .fa, .fa.gz, .fastq, .fastq.gz, .fq, .fq.gz)!" <<
            std::endl;
        return 1;
    }

    std::unique_ptr<spoa::AlignmentEngine> alignment_engine;
    try {
        alignment_engine = spoa::createAlignmentEngine(
            static_cast<spoa::AlignmentType>(algorithm), m, n, g, e, q, c);
    } catch(std::invalid_argument& exception) {
        std::cerr << exception.what() << std::endl;
        return 1;
    }

    auto graph = spoa::createGraph();

    std::vector<std::unique_ptr<spoa::Sequence>> sequences;
    sparser->parse(sequences, -1);

    std::size_t max_sequence_size = 0;
    for (const auto& it: sequences) {
        max_sequence_size = std::max(max_sequence_size, it->data().size());
    }
    alignment_engine->prealloc(max_sequence_size, 4);

    for (const auto& it: sequences) {
        auto alignment = alignment_engine->align(it->data(), graph);
        try {
            graph->add_alignment(alignment, it->data(), it->quality());
        } catch(std::invalid_argument& exception) {
            std::cerr << exception.what() << std::endl;
            return 1;
        }
    }

    if (result == 0 || result == 2) {
        std::string consensus = graph->generate_consensus();
        std::cout << "Consensus (" << consensus.size() << ")" << std::endl;
        std::cout << consensus << std::endl;
    }

    if (result == 1 || result == 2) {
        std::vector<std::string> msa;
        graph->generate_multiple_sequence_alignment(msa);
        std::cout << "Multiple sequence alignment" << std::endl;
        for (const auto& it: msa) {
            std::cout << it << std::endl;
        }
    }

    graph->print_dot(dot_path);

    return 0;
}

void help() {
    std::cout <<
        "usage: spoa [options ...] <sequences>\n"
        "\n"
        "    <sequences>\n"
        "        input file in FASTA/FASTQ format (can be compressed with gzip)\n"
        "        containing sequences\n"
        "\n"
        "    options:\n"
        "        -m <int>\n"
        "            default: 5\n"
        "            score for matching bases\n"
        "        -n <int>\n"
        "            default: -4\n"
        "            score for mismatching bases\n"
        "        -g <int>\n"
        "            default: -8\n"
        "            gap opening penalty (must be non-positive)\n"
        "        -e <int>\n"
        "            default: -6\n"
        "            gap extension penalty (must be non-positive)\n"
        "        -q <int>\n"
        "            default: -10\n"
        "            gap opening penalty of the second affine function\n"
        "            (must be non-positive)\n"
        "        -c <int>\n"
        "            default: -4\n"
        "            gap extension penalty of the second affine function\n"
        "            (must be non-positive)\n"
        "        -l, --algorithm <int>\n"
        "            default: 0\n"
        "            alignment mode:\n"
        "                0 - local (Smith-Waterman)\n"
        "                1 - global (Needleman-Wunsch)\n"
        "                2 - semi-global\n"
        "        -r, --result <int>\n"
        "            default: 0\n"
        "            result mode:\n"
        "                0 - consensus\n"
        "                1 - multiple sequence alignment\n"
        "                2 - 0 & 1\n"
        "        -d, --dot <file>\n"
        "            output file for the final POA graph in DOT format\n"
        "        --version\n"
        "            prints the version number\n"
        "        -h, --help\n"
        "            prints the usage\n"
        "\n"
        "    gap mode:\n"
        "        linear if g >= e\n"
        "        affine if g <= q or e >= c\n"
        "        convex otherwise (default)\n";
}

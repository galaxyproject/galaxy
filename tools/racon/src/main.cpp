#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <getopt.h>

#include <string>
#include <vector>

#include "sequence.hpp"
#include "polisher.hpp"
#ifdef CUDA_ENABLED
#include "cuda/cudapolisher.hpp"
#endif

#ifndef RACON_VERSION
#error "Undefined version for Racon. Please pass version using -DRACON_VERSION macro."
#endif

static const char* version = RACON_VERSION;
static const int32_t CUDAALIGNER_INPUT_CODE = 10000;

static struct option options[] = {
    {"include-unpolished", no_argument, 0, 'u'},
    {"fragment-correction", no_argument, 0, 'f'},
    {"window-length", required_argument, 0, 'w'},
    {"quality-threshold", required_argument, 0, 'q'},
    {"error-threshold", required_argument, 0, 'e'},
    {"no-trimming", no_argument, 0, 'T'},
    {"match", required_argument, 0, 'm'},
    {"mismatch", required_argument, 0, 'x'},
    {"gap", required_argument, 0, 'g'},
    {"threads", required_argument, 0, 't'},
    {"version", no_argument, 0, 'v'},
    {"help", no_argument, 0, 'h'},
#ifdef CUDA_ENABLED
    {"cudapoa-batches", optional_argument, 0, 'c'},
    {"cuda-banded-alignment", no_argument, 0, 'b'},
    {"cudaaligner-batches", required_argument, 0, CUDAALIGNER_INPUT_CODE},
#endif
    {0, 0, 0, 0}
};

void help();

int main(int argc, char** argv) {

    std::vector<std::string> input_paths;

    uint32_t window_length = 500;
    double quality_threshold = 10.0;
    double error_threshold = 0.3;
    bool trim = true;

    int8_t match = 3;
    int8_t mismatch = -5;
    int8_t gap = -4;
    uint32_t type = 0;

    bool drop_unpolished_sequences = true;
    uint32_t num_threads = 1;

    uint32_t cudapoa_batches = 0;
    uint32_t cudaaligner_batches = 0;
    bool cuda_banded_alignment = false;

    std::string optstring = "ufw:q:e:m:x:g:t:h";
#ifdef CUDA_ENABLED
    optstring += "bc::";
#endif

    int32_t argument;
    while ((argument = getopt_long(argc, argv, optstring.c_str(), options, nullptr)) != -1) {
        switch (argument) {
            case 'u':
                drop_unpolished_sequences = false;
                break;
            case 'f':
                type = 1;
                break;
            case 'w':
                window_length = atoi(optarg);
                break;
            case 'q':
                quality_threshold = atof(optarg);
                break;
            case 'e':
                error_threshold = atof(optarg);
                break;
            case 'T':
                trim = false;
                break;
            case 'm':
                match = atoi(optarg);
                break;
            case 'x':
                mismatch = atoi(optarg);
                break;
            case 'g':
                gap = atoi(optarg);
                break;
            case 't':
                num_threads = atoi(optarg);
                break;
            case 'v':
                printf("%s\n", version);
                exit(0);
            case 'h':
                help();
                exit(0);
#ifdef CUDA_ENABLED
            case 'c':
                //if option c encountered, cudapoa_batches initialized with a default value of 1.
                cudapoa_batches = 1;
                // next text entry is not an option, assuming it's the arg for option 'c'
                if (optarg == NULL && argv[optind] != NULL
                    && argv[optind][0] != '-') {
                    cudapoa_batches = atoi(argv[optind++]);
                }
                // optional argument provided in the ususal way
                if (optarg != NULL) {
                    cudapoa_batches = atoi(optarg);
                }
                break;
            case 'b':
                cuda_banded_alignment = true;
                break;
            case CUDAALIGNER_INPUT_CODE: // cudaaligner-batches
                cudaaligner_batches = atoi(optarg);
                break;
#endif
            default:
                exit(1);
        }
    }

    for (int32_t i = optind; i < argc; ++i) {
        input_paths.emplace_back(argv[i]);
    }

    if (input_paths.size() < 3) {
        fprintf(stderr, "[racon::] error: missing input file(s)!\n");
        help();
        exit(1);
    }

    auto polisher = racon::createPolisher(input_paths[0], input_paths[1],
        input_paths[2], type == 0 ? racon::PolisherType::kC :
        racon::PolisherType::kF, window_length, quality_threshold,
        error_threshold, trim, match, mismatch, gap, num_threads,
        cudapoa_batches, cuda_banded_alignment, cudaaligner_batches);

    polisher->initialize();

    std::vector<std::unique_ptr<racon::Sequence>> polished_sequences;
    polisher->polish(polished_sequences, drop_unpolished_sequences);

    for (const auto& it: polished_sequences) {
        fprintf(stdout, ">%s\n%s\n", it->name().c_str(), it->data().c_str());
    }

    return 0;
}

void help() {
    printf(
        "usage: racon [options ...] <sequences> <overlaps> <target sequences>\n"
        "\n"
        "    <sequences>\n"
        "        input file in FASTA/FASTQ format (can be compressed with gzip)\n"
        "        containing sequences used for correction\n"
        "    <overlaps>\n"
        "        input file in MHAP/PAF/SAM format (can be compressed with gzip)\n"
        "        containing overlaps between sequences and target sequences\n"
        "    <target sequences>\n"
        "        input file in FASTA/FASTQ format (can be compressed with gzip)\n"
        "        containing sequences which will be corrected\n"
        "\n"
        "    options:\n"
        "        -u, --include-unpolished\n"
        "            output unpolished target sequences\n"
        "        -f, --fragment-correction\n"
        "            perform fragment correction instead of contig polishing\n"
        "            (overlaps file should contain dual/self overlaps!)\n"
        "        -w, --window-length <int>\n"
        "            default: 500\n"
        "            size of window on which POA is performed\n"
        "        -q, --quality-threshold <float>\n"
        "            default: 10.0\n"
        "            threshold for average base quality of windows used in POA\n"
        "        -e, --error-threshold <float>\n"
        "            default: 0.3\n"
        "            maximum allowed error rate used for filtering overlaps\n"
        "        --no-trimming\n"
        "            disables consensus trimming at window ends\n"
        "        -m, --match <int>\n"
        "            default: 3\n"
        "            score for matching bases\n"
        "        -x, --mismatch <int>\n"
        "            default: -5\n"
        "            score for mismatching bases\n"
        "        -g, --gap <int>\n"
        "            default: -4\n"
        "            gap penalty (must be negative)\n"
        "        -t, --threads <int>\n"
        "            default: 1\n"
        "            number of threads\n"
        "        --version\n"
        "            prints the version number\n"
        "        -h, --help\n"
        "            prints the usage\n"
#ifdef CUDA_ENABLED
        "        -c, --cudapoa-batches\n"
        "            default: 1\n"
        "            number of batches for CUDA accelerated polishing\n"
        "        -b, --cuda-banded-alignment\n"
        "            use banding approximation for alignment on GPU\n"
        "        --cudaaligner-batches\n"
        "            Number of batches for CUDA accelerated alignment\n"

#endif
    );
}

# Bioparser

[![Latest GitHub release](https://img.shields.io/github/release/rvaser/bioparser.svg)](https://github.com/rvaser/bioparser/releases/latest)
[![Build status for gcc/clang](https://travis-ci.org/rvaser/bioparser.svg?branch=master)](https://travis-ci.org/rvaser/bioparser)

Bioparser is a c++ implementation of parsers for several bioinformatics formats. It consists of only one header file containing template parsers for FASTA, FASTQ, MHAP, PAF and SAM format. It also supports compressed files with gzip.

## Dependencies
1. gcc 4.8+ or clang 3.4+
2. (optional) cmake 3.2+

## Installation
To build Bioparser unit tests run the following commands:

```bash
git clone --recursive https://github.com/rvaser/bioparser.git bioparser
cd bioparser
mkdir build
cd build
cmake -Dbioparser_build_tests=ON -DCMAKE_BUILD_TYPE=Release ..
make
```

After installation, an executable named `bioparser_test` will be created in `build/bin`.

## Usage

If you would like to add bioparser to your project, add the following commands to your CMakeLists.txt file: `add_subdirectory(vendor/bioparser EXCLUDE_FROM_ALL)` and `target_link_libraries(your_exe bioparser)`. If you are not using cmake, include the header `bioparser.hpp` to your project and install zlib on your machine.

For details on how to use the parsers in your code, please look at the examples bellow:

*Note:* Bioparser by default trims sequence headers to the first white space. To disable this behavior pass `false` to the last argument of member functions `bioparser::Parser:parse`.

```cpp
// define a class for sequences in FASTA format
class Example1 {
public:
    // required signature for the constructor
    Example1(
        const char* name, std::uint32_t name_length,
        const char* sequence, std::uint32_t sequence_length) {
        // your implementation
    }
};

std::vector<std::unique_ptr<Example1>> fasta_objects;
auto fasta_parser = bioparser::createParser<bioparser::FastaParser, Example1>(path_to_file);
// read the whole file
fasta_parser->parse(fasta_objects, -1);

// define a class for sequences in FASTQ format
class Example2 {
public:
    // required signature for the constructor
    Example2(
        const char* name, std::uint32_t name_length,
        const char* sequence, std::uint32_t sequence_length,
        const char* quality, std::uint32_t quality_length) {
        // your implementation
    }
};

std::vector<std::unique_ptr<Example2>> fastq_objects;
auto fastq_parser = bioparser::createParser<bioparser::FastqParser, Example2>(path_to_file2);
// read a predefined size of bytes
std::uint64_t size_in_bytes = 500 * 1024 * 1024; // 500 MB
while (true) {
    auto status = fastq_parser->parse(fastq_objects, size_in_bytes);
    // do some work with objects
    if (status == false) {
        break;
    }
}

// define a class for overlaps in MHAP format
class Example3 {
public:
    // required signature for the constructor
    Example3(
        std::uint64_t a_id,
        std::uint64_t b_id,
        double eq_bases_perc,
        std::uint32_t minmers,
        std::uint32_t a_rc,
        std::uint32_t a_begin,
        std::uint32_t a_end,
        std::uint32_t a_length,
        std::uint32_t b_rc,
        std::uint32_t b_begin,
        std::uint32_t b_end,
        std::uint32_t b_length) {
        // your implementation
    }
};

std::vector<std::unique_ptr<Example3>> mhap_objects;
auto mhap_parser = bioparser::createParser<bioparser::MhapParser, Example3>(path_to_file3);
mhap_parser->parse(mhap_objects, -1);

// define a class for overlaps in PAF format or add a constructor to existing overlap class
Example3::Example3(
    const char* q_name, std::uint32_t q_name_length,
    std::uint32_t q_length,
    std::uint32_t q_begin,
    std::uint32_t q_end,
    char orientation,
    const char* t_name, std::uint32_t t_name_length,
    std::uint32_t t_length,
    std::uint32_t t_begin,
    std::uint32_t t_end,
    std::uint32_t matching_bases,
    std::uint32_t overlap_length,
    std::uint32_t mapping_quality) {
    // your implementation
}

std::vector<std::unique_ptr<ExampleClass3>> paf_objects;
auto paf_parser = bioparser::createParser<bioparser::PafParser, ExampleClass3>(path_to_file4);
paf_parser->parse(paf_objects, -1);

// define a class for alignments in SAM format
class Example4 {
public:
    // required signature for the constructor
    Example4(
        const char* q_name, std::uint32_t q_name_length,
        std::uint32_t flag,
        const char* t_name, std::uint32_t t_name_length,
        std::uint32_t t_begin,
        std::uint32_t mapping_quality,
        const char* cigar, std::uint32_t cigar_length,
        const char* t_next_name, std::uint32_t t_next_name_length,
        std::uint32_t t_next_begin,
        std::uint32_t template_length,
        const char* sequence, std::uint32_t sequence_length,
        const char* quality, std::uint32_t quality_length) {
        // your implementation
    }
};

std::vector<std::unique_ptr<Example4>> sam_objects;
auto sam_parser = bioparser::createParser<bioparser::SamParser, Example4>(path_to_file5);
sam_parser->parse(sam_objects, -1);
```
If your class has a **private** constructor with the required signature, format your classes in the following way:

```cpp
class Example1 {
public:
    friend bioparser::FastaParser<Example1>;
private:
    Example1(...) {
        ...
    }
};

class Example2 {
public:
    friend bioparser::FastqParser<Example2>;
private:
    Example2(...) {
        ...
    }
};

class Example3 {
public:
    friend bioparser::MhapParser<Example3>;
    friend bioparser::PafParser<Example3>;
private:
    Example3(...) {
        ...
    }
};

class Example4 {
public:
    friend bioparser::SamParser<Example4>;
private:
    Example4(...) {
        ...
    }
};
```

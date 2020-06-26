# Rampler

[![Latest GitHub release](https://img.shields.io/github/release/rvaser/rampler.svg)](https://github.com/rvaser/rampler/releases/latest)
[![Build status for c++/clang++](https://travis-ci.org/rvaser/rampler.svg?branch=master)](https://travis-ci.org/rvaser/rampler)

Standalone module for sampling genomic sequences. It supports two modes, random subsampling of sequencer data to a desired depth (given the reference length) and file splitting to desired size in bytes.

Rampler takes as first input argument a file in FASTA/FASTQ format which can be compressed with gzip. The rest of input parameters depend on the mode of operation. The output is stored into a file(s) which is in the same format as the input file but uncompressed.

## Dependencies
1. gcc 4.8+ or clang 3.4+
2. cmake 3.2+

## Installation
To install Rampler run the following commands:

```bash
git clone --recursive https://github.com/rvaser/rampler.git rampler
cd rampler
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make
```

After successful installation, an executable named `rampler` will appear in `build/bin`.

Optionally, you can run `sudo make install` to install rampler executable to your machine.

***Note***: if you omitted `--recursive` from `git clone`, run `git submodule update --init --recursive` before proceeding with compilation.

## Usage
Usage of rampler is as following:

    usage: rampler [options ...] <mode>

    <mode>
        subsample <sequences> <reference length> <coverage> [<coverage> ...]

            <sequences>
                input file in FASTA/FASTQ format (can be compressed with gzip)
                containing sequences to be subsampled
            <reference length>
                integer denoting length of the reference genome (or
                assembly) from which the sequences originate
            <coverage>
                integer denoting desired coverage of the subsampled
                sequences

        split <sequences> <chunk size>

            <sequences>
                input file in FASTA/FASTQ format (can be compressed with gzip)
                containing sequences which will be split into smaller chunks
            <chunk size>
                integer denoting the desired chunk size in bytes

    options:
        -o, --out-directory
            default: current directory
            path in which sampled files will be created
        --version
            prints the version number
        -h, --help
            prints out the help

## Contact information

For additional information, help and bug reports please send an email to one of the following: robert.vaser@fer.hr

## Acknowledgment

This work has been supported in part by Croatian Science Foundation under the project UIP-11-2013-7353.

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

#include "claragenomics/io/fasta_parser.hpp"

#include <string>

extern "C" {
#include <htslib/faidx.h>
}

namespace claragenomics
{
namespace io
{

class FastaParserHTS : public FastaParser
{
public:
    FastaParserHTS(const std::string& fasta_file);
    ~FastaParserHTS();

    int32_t get_num_seqences() const;

    FastaSequence get_sequence_by_id(int32_t i) const;

    FastaSequence get_sequence_by_name(const std::string&) const;

private:
    faidx_t* fasta_index_;
    int32_t num_seqequences_;
};

} // namespace io
} // namespace claragenomics

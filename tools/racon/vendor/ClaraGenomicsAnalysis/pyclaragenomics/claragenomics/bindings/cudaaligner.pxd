#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

# cython: profile=False
# distutils: language = c++
# cython: embedsignature = True
# cython: language_level = 3

from libcpp.pair cimport pair
from libcpp.string cimport string
from libcpp.vector cimport vector
from libc.stdint cimport int32_t
from libcpp.memory cimport unique_ptr, shared_ptr

from claragenomics.bindings.cuda_runtime_api cimport _Stream

# This file declared public structs and API calls
# from the ClaraGenomicsAnalysis `cudaaligner` module.

# Declare structs and APIs from cudaaligner.hpp
cdef extern from "claragenomics/cudaaligner/cudaaligner.hpp" namespace "claragenomics::cudaaligner":
    cdef enum StatusType:
        success = 0,
        uninitialized
        exceeded_max_alignments
        exceeded_max_length
        exceeded_max_alignment_difference
        generic_error

    cdef enum AlignmentType:
        global_alignment = 0
        unset

    cdef enum AlignmentState:
        match = 0
        mismatch
        insertion # Absent in query, present in target
        deletion # Present in query, absent in target

    cdef StatusType Init()

# Declare structs and APIs from alignment.hpp
cdef extern from "claragenomics/cudaaligner/alignment.hpp" namespace "claragenomics::cudaaligner":
    ctypedef pair[string, string] FormattedAlignment

    cdef cppclass Alignment:
        string get_query_sequence() except +
        string get_target_sequence() except +
        string convert_to_cigar() except +
        AlignmentType get_alignment_type() except +
        StatusType get_status() except +
        vector[AlignmentState] get_alignment() except +
        FormattedAlignment format_alignment() except +

# Declare structs and APIs from aligner.hpp
cdef extern from "claragenomics/cudaaligner/aligner.hpp" namespace "claragenomics::cudaaligner":
    cdef cppclass Aligner:
        StatusType align_all() except +
        StatusType sync_alignments() except +
        StatusType add_alignment(const char*, int32_t, const char*, int32_t) except +
        vector[shared_ptr[Alignment]] get_alignments() except +
        void reset() except +

    unique_ptr[Aligner] create_aligner(int32_t, int32_t, int32_t, AlignmentType, _Stream, int32_t)

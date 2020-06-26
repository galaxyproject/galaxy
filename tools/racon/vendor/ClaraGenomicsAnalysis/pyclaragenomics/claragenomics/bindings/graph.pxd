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
from libc.stdint cimport int32_t
from libcpp.vector cimport vector

# This file declares public structs and API calls 
# from the ClaraGenomicsAnalysis `graph` utility class.

# Declare structs and APIs from graph.hpp.
cdef extern from "claragenomics/utils/graph.hpp" namespace "claragenomics":
    cdef cppclass Graph:
        ctypedef int32_t node_id_t 
        ctypedef int32_t edge_weight_t 
        ctypedef pair[node_id_t, node_id_t] edge_t

    cdef cppclass DirectedGraph(Graph):
        vector[node_id_t]& get_adjacent_nodes(node_id_t) except +
        vector[node_id_t] get_node_ids() except +
        vector[pair[edge_t, edge_weight_t]] get_edges() except +
        void set_node_label(node_id_t, const string&) except +
        string get_node_label(node_id_t) except +
        void add_edge(node_id_t, node_id_t, edge_weight_t) except +
        string serialize_to_dot() except +

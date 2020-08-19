#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

# distutils: language = c++

from cython.operator cimport dereference as deref
from libc.stdint cimport uint16_t
from libcpp.memory cimport unique_ptr
from libcpp.pair cimport pair
from libcpp.string cimport string
from libcpp.vector cimport vector
import networkx as nx

from claragenomics.bindings import cuda
from claragenomics.bindings cimport cudapoa


def status_to_str(status):
    """
    Convert status to their string representations.
    """
    if status == success:
        return "success"
    elif status == exceeded_maximum_poas:
        return "exceeded_maximum_poas"
    elif status == exceeded_maximum_sequence_size:
        return "exceeded_maximum_sequence_size"
    elif status == exceeded_maximum_sequences_per_poa:
        return "exceeded_maximum_sequences_per_poa"
    elif status == exceeded_batch_size:
        return "exceeded_batch_size"
    elif status == node_count_exceeded_maximum_graph_size:
        return "node_count_exceeded_maximum_graph_size"
    elif status == edge_count_exceeded_maximum_graph_size:
        return "edge_count_exceeded_maximum_graph_size"
    elif status == seq_len_exceeded_maximum_nodes_per_window:
        return "seq_len_exceeded_maximum_nodes_per_window"
    elif status == loop_count_exceeded_upper_bound:
        return "loop_count_exceeded_upper_bound"
    elif status == output_type_unavailable:
        return "output_type_unavailable"
    elif status == generic_error:
        return "generic_error"
    else:
        raise RuntimeError("Unknown error status : " + status)

cdef class CudaPoaBatch:
    """
    Python API for CUDA-accelerated partial order alignment algorithm.
    """
    cdef unique_ptr[cudapoa.Batch] batch

    def __cinit__(
            self,
            max_sequences_per_poa,
            gpu_mem,
            device_id=0,
            stream=None,
            output_type="consensus",
            gap_score=-8,
            mismatch_score=-6,
            match_score=8,
            cuda_banded_alignment=False,
            *args,
            **kwargs):
        """
        Construct a CUDAPOA Batch object to run CUDA-accelerated
        partial order alignment across all windows in the batch.

        Args:
            max_sequences_per_poa : Maximum number of sequences per POA
            stream : CudaStream to use for GPU execution
            device_id : ID of GPU device to use
            output_mask : Types of outputs to generate (consensus, msa)
            gap_score : Penalty for gaps
            mismatch_score : Penalty for mismatches
            match_score : Reward for match
            cuda_banded_alignment : Run POA using banded alignment
        """
        cdef size_t st
        cdef _Stream temp_stream
        if (stream is None):
            temp_stream = NULL
        elif (not isinstance(stream, cuda.CudaStream)):
            raise RuntimeError("Type for stream option must be CudaStream")
        else:
            st = stream.stream
            temp_stream = <_Stream>st

        cdef int8_t output_mask
        if (output_type == "consensus"):
            output_mask = consensus
        elif (output_type == "msa"):
            output_mask = msa
        else:
            raise RuntimeError("Unknown output_type provided. Must be consensus/msa.")

        self.batch = cudapoa.create_batch(
                max_sequences_per_poa,
                device_id,
                temp_stream,
                gpu_mem,
                output_mask,
                gap_score,
                mismatch_score,
                match_score,
                cuda_banded_alignment)

    def __init__(
            self,
            max_sequences_per_poa,
            gpu_mem,
            device_id=0,
            stream=None,
            output_mask=consensus,
            gap_score=-8,
            mismatch_score=-6,
            match_score=8,
            cuda_banded_alignment=False,
            *args,
            **kwargs):
        """
        Dummy implementation of __init__ function to allow
        for Python subclassing.
        """
        pass

    def add_poa_group(self, poa):
        """
        Set the POA groups to run alignment on.

        Args:
            poas : List of POA groups. Each group is a list of
                   sequences.
                   e.g. [["ACTG", "ATCG"], <--- Group 1
                         ["GCTA", "GACT", "ACGTC"] <--- Group 2
                        ]
                   Throws exception if error is encountered while
                   adding POA groups.
        """
        if (not isinstance(poa, list)):
            poas = [poa]
        if (len(poa) < 1):
            raise RuntimeError("At least one sequence must be present in POA group")
        cdef char* c_string
        cdef cudapoa.Group poa_group
        cdef cudapoa.Entry entry
        cdef vector[cudapoa.StatusType] seq_status
        byte_list = [] # To store byte array of POA sequences
        for seq in poa:
            byte_list.append(seq.encode('utf-8'))
            c_string = byte_list[-1]
            entry.seq = c_string
            entry.weights = NULL
            entry.length = len(seq)
            poa_group.push_back(entry)
        status = deref(self.batch).add_poa_group(seq_status, poa_group)
        if status != success and status != exceeded_maximum_poas:
            raise RuntimeError("Could not add POA group: Error code " + status_to_str(status))
        return (status, seq_status)

    @property
    def total_poas(self):
        """
        Get total number of POA groups added to batch.

        Returns:
            Number of POA groups added to batch.
        """
        return deref(self.batch).get_total_poas()

    @property
    def batch_id(self):
        """
        Get the batch ID of the cudapoa Batch object.

        Returns:
            Batch ID.
        """
        return deref(self.batch).batch_id()

    def generate_poa(self):
        """
        Run asynchronous partial order alignment on all POA groups
        in batch.
        """
        deref(self.batch).generate_poa()

    def get_msa(self):
        """
        Get the multi-sequence alignment for each POA group.

        Returns:
            A tuple where
            - first element is a list with MSAs for each POA group, with each MSA
            represented as a list of alignments.
            - second element is status of MSA generation for each group
        """
        cdef vector[vector[string]] msa
        cdef vector[cudapoa.StatusType] status
        error = deref(self.batch).get_msa(msa, status)
        if error == output_type_unavailable:
            raise RuntimeError("Output type not requested during batch initialization")
        return (msa, status)

    def get_consensus(self):
        """
        Get the consensus for each POA group.

        Returns:
            A tuple where
            - first element is list with consensus string for each group
            - second element is a list of per base coverages for each consensus
            - third element is status of consensus generation for each group
        """
        cdef vector[string] consensus
        cdef vector[vector[uint16_t]] coverage
        cdef vector[cudapoa.StatusType] status
        error = deref(self.batch).get_consensus(consensus, coverage, status)
        if error == output_type_unavailable:
            raise RuntimeError("Output type not requested during batch initialization")
        decoded_consensus = [c.decode('utf-8') for c in consensus]
        return (decoded_consensus, coverage, status)

    def get_graphs(self):
        """
        Get the POA graph for each POA group.

        Returns:
            A tuple where
            - first element is a networkx graph for each POA group
            - second element is status of MSA generation for each group
        """
        cdef vector[DirectedGraph] graphs
        cdef vector[cudapoa.StatusType] status
        cdef vector[pair[DirectedGraph.edge_t, DirectedGraph.edge_weight_t]] edges
        cdef DirectedGraph* graph
        cdef DirectedGraph.edge_t edge
        cdef DirectedGraph.edge_weight_t weight

        # Get the graphs from batch object.
        deref(self.batch).get_graphs(graphs, status)

        nx_digraphs = []
        for g in range(graphs.size()):
            graph = &graphs[g]
            edges = deref(graph).get_edges()
            nx_digraph = nx.DiGraph()
            for e in range(edges.size()):
                edge = edges[e].first
                weight = edges[e].second
                nx_digraph.add_edge(edge.first,
                                    edge.second,
                                    weight=weight)
            attributes = {}
            for n in nx_digraph.nodes:
                attributes[n] = {'label' : deref(graph).get_node_label(n).decode('utf-8')}
            nx.set_node_attributes(nx_digraph, attributes)
            nx_digraphs.append(nx_digraph)
        return (nx_digraphs, status)

    def reset(self):
        """
        Reset the batch object. Involves deleting all windows previously
        assigned to batch object.
        """
        deref(self.batch).reset()

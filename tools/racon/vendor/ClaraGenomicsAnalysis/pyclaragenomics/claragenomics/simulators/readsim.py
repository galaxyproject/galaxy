#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""Classes to simulate reads from a known reference, mimicking sequencing errors"""
import abc
import gzip
import random


from sortedcollections import SortedList

from . import NUCLEOTIDES
from ..io import pafio


def generate_overlaps(seqs, gzip_compressed=True):
    """
    Return a list of overlaps

    Args:
      seqs: list of Seq objects (4-tuple (read_id, sequence, reference_start, reference_end)
      gzip_compressed (bool): True if sequence field in seqs tuples is compressed

    Returns: list of overlap objects. Overlaps are named tuples with the follwing fields:
        * query_sequence_name
        * query_sequence_length
        * query_start
        * query_end
        * relative_strand
        * target_sequence_name
        * target_sequence_length
        * target_start
        * target_end
        * num_residue_matches
        * alignment_block_length
        * mapping_quality
    """

    def startsort(read): return read[2]
    overlaps = []
    sorted_seqs = SortedList(seqs, key=startsort)
    # reads are now sorted by their start position
    for query_index, query in enumerate(sorted_seqs):
        query_name = query[0]

        if gzip_compressed:
            query_seq_len = len(str(gzip.decompress(query[1]), "utf-8"))
        else:
            query_seq_len = len(query[1])

        query_reference_start = query[2]
        query_reference_end = query[3]
        for target_index, target in enumerate(sorted_seqs[query_index+1:]):
            target_reference_start = target[2]
            target_reference_end = target[3]
            if query_reference_end > target_reference_start:  # overlap found
                # Calculate the overlap coordinates:
                if gzip_compressed:
                    target_seq_len = len(str(gzip.decompress(target[1]), "utf-8"))
                else:
                    target_seq_len = len(target[1])

                query_start = target_reference_start - query_reference_start
                target_start = 0

                if target_reference_end > query_reference_end:
                    query_end = query_seq_len
                    target_end = query_reference_end - target_reference_start
                else:
                    target_end = target_seq_len
                    query_end = query_start + target_seq_len

                target_name = target[0]
                overlap = pafio.Overlap(query_sequence_name=query_name,
                                        query_sequence_length=query_seq_len,
                                        query_start=query_start,
                                        query_end=query_end,
                                        relative_strand="+",  # temporary
                                        target_sequence_name=target_name,
                                        target_sequence_length=target_seq_len,
                                        target_start=target_start,
                                        target_end=target_end,
                                        num_residue_matches=1,
                                        alignment_block_length=-1,
                                        mapping_quality=255)
                overlaps.append(overlap)
    return(overlaps)


class ReadSimulator:
    @abc.abstractmethod
    def generate_read(self, reference, median_length, error_rate):
        pass


class NoisyReadSimulator(ReadSimulator):
    """Simulate sequencing errors in reads"""

    def __init__(self):
        pass

    def _add_snv_errors(self, read, error_rate):
        """Randomly introduce SNV errors

        Args:
          read (str): The nucleotide string
          error_rate (int): the ratio of bases which will be converted to SNVs

        Returns: The read (string) with SNVs introduced
        """
        noisy_bases = []
        for r in read:
            rand = random.uniform(0, 1)
            if rand > error_rate:
                noisy_bases.append(r)
            else:
                candidate_bases = NUCLEOTIDES ^ set((r,))
                new_base = random.choice(tuple(candidate_bases))
                noisy_bases.append(new_base)
        return "".join(noisy_bases)

    def _add_deletion_errors(self, read, error_rate):
        """Randomly introduce SNV errors

        Args:
          read (str): The nucleotide string
          error_rate (int): the ratio of bases which will be deleted

        Returns: The read (string) with deletions introduced
        """
        noisy_bases = []
        for r in read:
            rand = random.uniform(0, 1)
            if rand > error_rate:
                noisy_bases.append(r)
        return "".join(noisy_bases)

    def _add_insertion_errors(self, read, error_rate):
        """Randomly introduce SNV errors

        Args:
          read (str): The nucleotide string
          error_rate (int): the ratio of bases which will be reference insertions in the read

        Returns: The read (string) with insertions introduced
        """
        noisy_bases = []
        for r in read:
            rand = random.uniform(0, 1)
            if rand > error_rate:
                noisy_bases.append(r)
            else:
                new_base = random.choice(tuple(NUCLEOTIDES))
                noisy_bases.append(r)
                noisy_bases.append(new_base)
        return "".join(noisy_bases)

    def _add_homopolymer_clipping(self, read, homopolymer_survival_length, clip_rate):
        """Randomly reduce homopolymer length

        Args:
          read (str): The nucleotide string
          homopolymer_survival_length: Homopolymers with this length will not be clipped
          clip_rate: bases above this length in a homopolymer will be removed with this probability

        Returns: The read (string) with clipped homopolymers
        """
        homopolymer_len = 1
        prev_base = read[0]
        noisy_bases = [prev_base]
        for r in read[1:]:
            if r == prev_base:
                homopolymer_len += 1
                if homopolymer_len > homopolymer_survival_length:
                    if random.uniform(0, 1) > clip_rate:
                        noisy_bases.append(r)
                else:
                    noisy_bases.append(r)
            else:
                prev_base = r
                homopolymer_len = 1
                noisy_bases.append(r)

        return "".join(noisy_bases)

    def generate_read(self, reference,
                      median_length,
                      snv_error_rate=2.5e-2,
                      insertion_error_rate=1.25e-2,
                      deletion_error_rate=1.25e-2,
                      homopolymer_survival_length=4,
                      homopolymer_clip_rate=0.5):
        """Generate reads

        Args:
          reference (str): The reference nucleotides from which the read is generated
          median_length (int): Median length of generated read
          snv_error_rate (int): the ratio of bases which will be converted to SNVs
          insertion_error_rate (int): the ratio of bases which will be reference insertions in the read
          deletion_error_rate (int): the ratio of bases from the reference which will be deleted
          homopolymer_survival_length: Homopolymers with this length will not be clipped
          homopolyumer_clip_rate: bases above this length in a homopolymer will be removed with this probability

        Returns: A read randomly generated from the reference, with noise applied
        """

        reference_length = len(reference)
        pos = random.randint(0, reference_length - 1)

        def clamp(x):
            return max(0, min(x, reference_length - 1))

        start = clamp(pos - median_length // 2)
        end = clamp(pos + median_length // 2) + median_length % 2
        substring = reference[start: end]

        substring = self._add_snv_errors(substring, snv_error_rate)

        substring = self._add_insertion_errors(substring, insertion_error_rate)

        substring = self._add_deletion_errors(substring, deletion_error_rate)

        read = self._add_homopolymer_clipping(substring,
                                              homopolymer_survival_length=homopolymer_survival_length,
                                              clip_rate=homopolymer_clip_rate)

        return read, start, end

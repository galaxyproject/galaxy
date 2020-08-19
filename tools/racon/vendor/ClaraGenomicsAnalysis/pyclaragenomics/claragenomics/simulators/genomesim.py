#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

"""Classes to simulate genomes"""
import abc
import functools
import multiprocessing
import random

import numpy as np
from tqdm import tqdm

from claragenomics.simulators import NUCLEOTIDES


class GenomeSimulator(abc.ABC):
    """Base class for genome simulators"""
    @abc.abstractmethod
    def build_reference(self):
        pass


class PoissonGenomeSimulator(GenomeSimulator):
    """Simulates genome with poisson process"""

    def __init__(self):
        pass

    def build_reference(self, reference_length):
        """Simulates genome with poisson process

        Args:
          reference_length: The desired genome length

        Returns:
          String corresponding to reference genome. Each character is a
          nucleotide radnomly selected from a uniform, flat distribution.
        """
        reference_length = int(reference_length)
        return ''.join(random.choice(tuple(NUCLEOTIDES)) for x in range(reference_length))


class MarkovGenomeSimulator(GenomeSimulator):
    """Simulates genome with a Markovian process"""

    def __init__(self):
        pass

    def _build_reference_section_worker(self, section_idx_and_length, transitions):
        """Simulates section of genome with a Markovian process
        Args:
          section_idx_and_length (int, int):  tuple consisting of section id and section length
          transitions: dict of dict with all transition probabilities
            e.g {'A': {'A':0.1,'C':0.3',...}, 'C':{'A':0.3,...}...}
          num_threads: number of threads to use when computing reference

        Returns:
          String corresponding to reference genome. Each character is a
          nucleotide radnomly selected from a uniform, flat distribution.
        """
        section_idx, section_length = section_idx_and_length
        np.random.seed(section_idx)
        reference_length = int(section_length)
        prev_base = np.random.choice(list(NUCLEOTIDES))
        ref_bases = [prev_base]
        for _ in range(reference_length - 1):
            next_base_choices = list(zip(*transitions[prev_base].items()))
            next_base_candidates = next_base_choices[0]
            next_base_pd = np.array(next_base_choices[1])
            next_base_pd = next_base_pd / next_base_pd.sum()
            prev_base = np.random.choice(next_base_candidates, 1, p=next_base_pd)[0]
            ref_bases.append(prev_base)
        return "".join(ref_bases)

    def build_reference(self, reference_length, transitions, num_threads=None):
        """Simulates genome with a Markovian process
        Args:
          reference_length (int): The desired genome length
          transitions: dict of dict with all transition probabilities
            e.g {'A': {'A':0.1,'C':0.3',...}, 'C':{'A':0.3,...}...}
          num_threads: number of threads to use when computing reference

        Returns:
          String corresponding to reference genome. Each character is a
          nucleotide radnomly selected from a uniform, flat distribution.
        """

        num_cpus = multiprocessing.cpu_count()

        if num_threads is None:
            num_threads = num_cpus

        # For very short reference do single-threaded
        if reference_length <= num_cpus:
            num_threads = 1

        if reference_length // num_threads > 100:
            num_sections = num_threads * 10
        else:
            num_sections = num_threads

        quotient, remainder = divmod(reference_length, num_sections)
        section_lengths = [quotient + int(i < remainder) for i in range(num_sections)]

        idxs_and_lengths = [(i, section_lengths[i]) for i in range(len(section_lengths))]

        ref_builder = functools.partial(self._build_reference_section_worker, transitions=transitions)

        pool = multiprocessing.Pool(num_threads)
        print('Simulating genome:')
        sections = tqdm(pool.imap(ref_builder, idxs_and_lengths), total=len(idxs_and_lengths))
        return "".join(sections)

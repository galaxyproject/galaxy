#
# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import pytest

from claragenomics.simulators import readsim
from claragenomics.simulators import genomesim
from claragenomics import simulators


num_reads_data = [
    (1, 100000, 1, 100),
    (20, 2000, 20, 100),
    pytest.param(1, 10, 1, 100, marks=pytest.mark.xfail(reason="Reads longer than reference")),
]


@pytest.mark.cpu
@pytest.mark.parametrize("num_reads, reference_length, num_reads_expected, read_median_length", num_reads_data)
def test_noisy_generator_number(num_reads, reference_length, num_reads_expected, read_median_length):
    """ Test generated length for Markovian genome simulator is correct"""

    genome_simulator = genomesim.MarkovGenomeSimulator()
    reference_string = genome_simulator.build_reference(reference_length,
                                                        transitions=simulators.HIGH_GC_HOMOPOLYMERIC_TRANSITIONS)
    read_generator = readsim.NoisyReadSimulator()
    num_reads_generated = 0
    for _ in range(num_reads):
        read_generator.generate_read(reference_string, read_median_length)
        num_reads_generated += 1

    assert(num_reads_generated == num_reads_expected)

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

test_reads = [
    ((("read_0",
      "AACGTCA",
       100,
       900),
     ("read_1",
      "AACGTCA",
      100,
      900)), 1),
    ((("read_0",
      "AACGTCA",
       100,
       900),
     ("read_1",
      "AACGTCA",
      1000,
      9000)), 0),
    ((("read_1",
      "AACGTCA",
       100,
       900),
     ("read_0",
      "AACGTCA",
      100,
      900)), 1),
    ((("read_1",
      "AACGTCA",
       100,
       900),
     ("read_0",
      "AACGTCA",
      100,
      900)), 1),
    ((("read_1",
      "AACGTCA",
       100,
       900),
      ("read_2",
      "AACGTCA",
       100,
       900),
     ("read_3",
      "AACGTCA",
      100,
      900)), 3),
]


@pytest.mark.parametrize("reads, expected_overlaps", test_reads)
def test_generates_overlaps(reads, expected_overlaps):
    """ Test that the number of overlaps detected is correct"""
    overlaps = readsim.generate_overlaps(reads, gzip_compressed=False)
    assert(len(overlaps) == expected_overlaps)

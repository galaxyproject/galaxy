from galaxy.datatypes.tabular import (
    GSuite
)
from .util import get_input_files


def test_gtrack_sniff():
    gsuite = GSuite()

    with get_input_files('Example_1.gsuite', 'Example_2.gsuite', 'Example_3.gsuite') as input_files:
        for input in input_files:
            assert gsuite.sniff(input) is True

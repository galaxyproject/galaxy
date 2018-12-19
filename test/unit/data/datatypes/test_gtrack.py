from galaxy.datatypes.interval import (
    GTrack
)
from .util import get_input_files


def test_gtrack_sniff():
    gtrack = GTrack()

    with get_input_files('Example_1.gtrack') as input:
        assert gtrack.sniff(input[0]) is False

    with get_input_files('Example_2.gtrack', 'Example_3.gtrack', 'Example_bed_direct.gtrack',
                         'Example_mean_sd_weights.gtrack') as input_files:
        for input in input_files:
            assert gtrack.sniff(input) is True

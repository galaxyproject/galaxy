from galaxy.datatypes.text import (
    Castep,
    FormattedDensity,
    Param,
)
from .util import get_input_files


def test_castep():
    castep = Castep()
    with get_input_files("Si.castep", "Si.param", "Si.den_fmt") as input_files:
        assert castep.sniff(input_files[0])
        assert not castep.sniff(input_files[1])
        assert not castep.sniff(input_files[2])


def test_param():
    param = Param()
    with get_input_files("Si.castep", "Si.param", "Si.den_fmt") as input_files:
        assert not param.sniff(input_files[0])
        assert param.sniff(input_files[1])
        assert not param.sniff(input_files[2])


def test_den_fmt():
    formattedDensity = FormattedDensity()
    with get_input_files("Si.castep", "Si.param", "Si.den_fmt") as input_files:
        assert not formattedDensity.sniff(input_files[0])
        assert not formattedDensity.sniff(input_files[1])
        assert formattedDensity.sniff(input_files[2])

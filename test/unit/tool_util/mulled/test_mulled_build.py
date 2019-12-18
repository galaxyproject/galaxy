import pytest

from galaxy.tool_util.deps.mulled.mulled_build import (
    any_target_requires_extended_base,
    build_target,
)
from ..util import external_dependency_management


@pytest.mark.parametrize("target,requires_extended", [
    ('maker', True),
    ('samtools', False)
])
@external_dependency_management
def test_any_target_requires_extended_base(target, requires_extended):
    target = build_target(target)
    assert any_target_requires_extended_base([target]) == requires_extended

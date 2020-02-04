import pytest

from galaxy.tool_util.deps.mulled.mulled_build import (
    base_image_for_targets,
    build_target,
    DEFAULT_BASE_IMAGE,
    DEFAULT_EXTENDED_BASE_IMAGE,
)
from ..util import external_dependency_management


@pytest.mark.parametrize("target,version,base_image", [
    ('maker', None, DEFAULT_EXTENDED_BASE_IMAGE),
    ('qiime', '1.9.1', DEFAULT_EXTENDED_BASE_IMAGE),
    ('samtools', None, DEFAULT_BASE_IMAGE),
])
@external_dependency_management
def test_base_image_for_targets(target, version, base_image):
    target = build_target(target, version=version)
    assert base_image_for_targets([target]) == base_image

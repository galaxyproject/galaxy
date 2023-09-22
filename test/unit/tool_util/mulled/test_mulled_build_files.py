import tempfile

import pytest
import yaml

from galaxy.tool_util.deps.mulled.mulled_build import target_str_to_targets
from galaxy.tool_util.deps.mulled.mulled_build_files import (
    FALLBACK_LINE_TUPLE,
    generate_targets,
)

TESTCASES = yaml.safe_load(
    r"""
- test_legacy_files_package_only:
    content: samtools
    equals:
      base_image: null
      image_build: null
      name_override: null
      targets: samtools
- test_legacy_files_package_image_build:
    content: "samtools\t10"
    equals:
      base_image: null
      image_build: '10'
      name_override: null
      targets: samtools
- test_legacy_files_package_image_build_name_override:
    content: "samtools\t10\timage_name"
    equals:
      base_image: null
      image_build: '10'
      name_override: image_name
      targets: samtools
- test_files_package_image_build_name_override_base_image_with_header:
    content: "#targets\timage_build\tname_override\tbase_image\nsamtools\t10\timage_name\textended_image"
    equals:
      base_image: extended_image
      image_build: '10'
      name_override: image_name
      targets: samtools
- test_files_package_image_build_base_image_with_header:
    content: "#targets\timage_build\tbase_image\nsamtools\t10\textended_image"
    equals:
      base_image: extended_image
      image_build: '10'
      name_override: null
      targets: samtools
- test_files_package_image_build_name_override_base_image_with_header_reordered:
    content: "#base_image\ttargets\timage_build\tname_override\nextended_image\tsamtools\t10\timage_name"
    equals:
      base_image: extended_image
      image_build: '10'
      name_override: image_name
      targets: samtools
"""
)
TEST_IDS = [next(iter(k.keys())) for k in TESTCASES]


@pytest.mark.parametrize(
    "content, equals", [(d[k]["content"], d[k]["equals"]) for k, d in zip(TEST_IDS, TESTCASES)], ids=TEST_IDS
)
def test_generate_targets(content, equals):
    equals["targets"] = target_str_to_targets(equals["targets"])
    equals = FALLBACK_LINE_TUPLE(**equals)
    with tempfile.NamedTemporaryFile(mode="w") as tmpfile:
        tmpfile.write(content)
        tmpfile.flush()
        generated_target = next(generate_targets(tmpfile.name))
    assert generated_target.targets == equals.targets
    assert generated_target.image_build == equals.image_build
    assert generated_target.name_override == equals.name_override
    assert generated_target.base_image == equals.base_image

import tempfile

import pytest
import yaml

from galaxy.tool_util.deps.mulled.mulled_build import target_str_to_targets
from galaxy.tool_util.deps.mulled.mulled_build_files import (
    FALLBACK_LINE_TUPLE,
    generate_targets,
    generate_targets_from_file,
    str_from_target,
)
from galaxy.tool_util.deps.mulled.util import build_target

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
TESTCASES = {k: v for t in TESTCASES for k, v in t.items()}
for key in TESTCASES:
    TESTCASES[key]["equals"]["targets"] = target_str_to_targets(TESTCASES[key]["equals"]["targets"])


@pytest.mark.parametrize(
    "content, equals",
    [(test_case["content"], test_case["equals"]) for _, test_case in TESTCASES.items()],
    ids=TESTCASES.keys(),
)
def test_generate_targets(content, equals):
    equals = FALLBACK_LINE_TUPLE(**equals)
    with tempfile.NamedTemporaryFile(mode="w") as tmpfile:
        tmpfile.write(content)
        tmpfile.flush()
        generated_target = next(generate_targets(tmpfile.name))
    assert generated_target.targets == equals.targets
    assert generated_target.image_build == equals.image_build
    assert generated_target.name_override == equals.name_override
    assert generated_target.base_image == equals.base_image


@pytest.mark.parametrize(
    "content, equals",
    [(test_case["content"], test_case["equals"]) for _, test_case in TESTCASES.items()],
    ids=TESTCASES.keys(),
)
def test_generate_targets_from_file(content, equals):
    equals = FALLBACK_LINE_TUPLE(**equals)
    with tempfile.NamedTemporaryFile(mode="w") as tmpfile:
        tmpfile.write(content)
        tmpfile.flush()
        generated_target = next(generate_targets_from_file(tmpfile.name))
    assert generated_target.targets == equals.targets
    assert generated_target.image_build == equals.image_build
    assert generated_target.name_override == equals.name_override
    assert generated_target.base_image == equals.base_image


def test_str_from_target():
    target_str = "atarget"
    assert target_str == str_from_target(build_target(target_str))

    version = "0.1"
    target_str_versioned = f"{target_str}={version}"
    assert target_str_versioned == str_from_target(build_target(target_str, version))

    build = "2"
    target_str_version_build = f"{target_str}={version}--{build}"
    assert target_str_version_build == str_from_target(build_target(target_str, version, build))

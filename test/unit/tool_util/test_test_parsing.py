import yaml

from galaxy.tool_util.parser.yaml import to_test_assert_list

# Legacy style
ASSERT_THAT_LIST = yaml.safe_load(
    """
- that: "has_text"
  text: "Number of input reads |\t1051466"
- that: "has_text"
  text: "Uniquely mapped reads number |\t871202"
"""
)
# New list of assertion style
ASSERT_LIST = yaml.safe_load(
    """
- has_text:
    text: "Number of input reads |\t1051466"
- has_text:
    text: "Uniquely mapped reads number |\t871202"
"""
)
# Singleton assertion
SIMPLE_ASSERT = {"has_text": {"text": "Number of input reads |\t1051466"}}


def test_assert_that_list_to_test_assert_list():
    to_test_assert_list(ASSERT_THAT_LIST)


def test_assert_list_to_test_assert_list():
    to_test_assert_list(ASSERT_LIST)


def test_simple_assert_to_test_assert_list():
    to_test_assert_list(SIMPLE_ASSERT)


def test_assert_legacy_same_as_new_list_style():
    assert to_test_assert_list(ASSERT_THAT_LIST) == to_test_assert_list(ASSERT_THAT_LIST)

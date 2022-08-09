import pytest

from galaxy.util.bool_expressions import (
    BooleanExpressionEvaluator,
    DEFAULT_TOKEN_FORMAT,
    TokenContainedEvaluator,
)

# Defines the allowed characters that form a valid token.
# Tokens that don't match this format will raise a ParseException
TOKEN_FORMAT = DEFAULT_TOKEN_FORMAT

# The set of tokens that will be evaluated to True using the TokenContainedEvaluator the rest
# of the *valid tokens* (those that match the TOKEN_FORMAT) will be evaluated to False.
TOKENS_THAT_ARE_TRUE = {"T1", "token_2", "valid quoted str"}

VALID_EXPRESSIONS_TESTS = [
    ("T1", True),
    ("token_2", True),
    ("T3", False),
    ("valid_token", False),
    ("not T3", True),
    ("NOT token_2", False),
    ("T1 and not T3", True),
    ("NOT T1 AND token_2", False),
    ("not T3 or (T3 AND token_2)", True),
    ("T1 and (T3 OR token_2)", True),
    ("(T3 OR T1) and not (T3 OR valid_token)", True),
    ("'some quoted str' and T1", False),
    ("'valid quoted str' and T1", True),
]

INVALID_EXPRESSIONS_TESTS = [
    "",
    "23 45",
    "invalid expression",
    "T1 and and T2",
    "T1 not and T3",
    "(T1 and T3",
    "T1 or T3)",
    "T1 and or T2",
]


@pytest.fixture(scope="module")
def contained_evaluator() -> BooleanExpressionEvaluator:
    """Boolean expression evaluator using the TokenContainedEvaluator.

    All the tokens in TOKENS_THAT_ARE_TRUE will be evaluated to True and
    any other token to False."""
    token_evaluator = TokenContainedEvaluator(TOKENS_THAT_ARE_TRUE)
    evaluator = BooleanExpressionEvaluator(token_evaluator, TOKEN_FORMAT)
    return evaluator


@pytest.mark.parametrize("expr, expected", VALID_EXPRESSIONS_TESTS)
def test_expression_evaluates_as_expected(expr: str, expected: bool, contained_evaluator: BooleanExpressionEvaluator):
    actual = contained_evaluator.evaluate_expression(expr)
    assert actual == expected


@pytest.mark.parametrize("expr", INVALID_EXPRESSIONS_TESTS)
def test_invalid_expression_raises_exception(expr: str, contained_evaluator: BooleanExpressionEvaluator):
    with pytest.raises(Exception):
        contained_evaluator.evaluate_expression(expr)


@pytest.mark.parametrize("expr, _", VALID_EXPRESSIONS_TESTS)
def test_is_valid_expression_return_true_when_valid(expr: str, _: bool):
    result = BooleanExpressionEvaluator.is_valid_expression(expr)
    assert result is True


@pytest.mark.parametrize("expr", INVALID_EXPRESSIONS_TESTS)
def test_is_valid_expression_return_false_when_invalid(expr: str):
    result = BooleanExpressionEvaluator.is_valid_expression(expr)
    assert result is False

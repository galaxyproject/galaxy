"""Simple boolean expression parser and evaluator using pyparsing.

Based on the example: https://github.com/pyparsing/pyparsing/blob/master/examples/simpleBool.py
"""

import logging
from typing import (
    Callable,
    Iterable,
    Optional,
    Set,
)

from pyparsing import (
    alphanums,
    CaselessKeyword,
    infixNotation,
    Keyword,
    opAssoc,
    ParseException,
    ParserElement,
    QuotedString,
    Word,
)

log = logging.getLogger(__name__)

ParserElement.enablePackrat()

# Defines the allowed characters that form a valid token.
# Tokens that don't match this format will raise an exception when found.
DEFAULT_TOKEN_FORMAT = f"{alphanums}_-@."

TRUE = Keyword("True")
FALSE = Keyword("False")
NOT_OP = CaselessKeyword("not")
AND_OP = CaselessKeyword("and")
OR_OP = CaselessKeyword("or")
QUOTED_STRING = QuotedString("'")


class TokenEvaluator:
    """Interface to evaluate a token and determine its boolean value."""

    def evaluate(self, token: str) -> bool:
        """Returns the boolean representation of the given token according to some custom logic."""
        raise NotImplementedError


class BoolOperand:
    """Represents a boolean operand that has a label and a value.

    The value is determined by a custom TokenEvaluator."""

    evaluator: TokenEvaluator

    def __init__(self, token):
        self.label = token[0]
        self.value = self.evaluator.evaluate(token[0])

    def __bool__(self):
        return self.value

    def __str__(self):
        return self.label

    __repr__ = __str__


class BoolBinaryOperation:
    """Base representation of a boolean binary operation."""

    reprsymbol: str
    evalop: Callable[[Iterable[object]], bool]

    def __init__(self, token):
        self.args = token[0][0::2]

    def __str__(self):
        sep = f" {self.reprsymbol} "
        return f"({sep.join(map(str, self.args))})"

    def __bool__(self):
        return self.evalop(bool(a) for a in self.args)  # type: ignore[misc,call-arg]

    __nonzero__ = __bool__


class BoolAnd(BoolBinaryOperation):
    """Represents the `AND` boolean operation."""

    reprsymbol = "&"
    evalop = all


class BoolOr(BoolBinaryOperation):
    """Represents the `OR` boolean operation."""

    reprsymbol = "|"
    evalop = any


class BoolNot:
    """Represents the `NOT` boolean operation."""

    def __init__(self, token):
        self.arg = token[0][1]

    def __bool__(self):
        v = bool(self.arg)
        return not v

    def __str__(self):
        return f"~{self.arg}"

    __repr__ = __str__


class BooleanExpressionEvaluator:
    """Boolean logic parser that can evaluate an expression using a particular TokenEvaluator.

    Supports AND, OR and NOT operator including parentheses to override operator precedences.

    You can pass in different TokenEvaluator implementations to customize how the tokens (or variables) are
    converted to a boolean value when evaluating the expression."""

    def __init__(self, evaluator: TokenEvaluator, token_format: Optional[str] = None) -> None:
        """Initializes the expression evaluator.

        :param evaluator: The custom TokenEvaluator used to transform any token into a boolean.
        :type evaluator:  TokenEvaluator

        :param token_format: A string of all allowed characters used to form a valid token, defaults to None.
                             The default value (None) will use DEFAULT_TOKEN_FORMAT which means the allowed characters are ``[A-Za-z0-9_-@.]``.
        :type token_format:  Optional[str]
        """
        action = BoolOperand
        action.evaluator = evaluator
        boolOperand = TRUE | FALSE | QUOTED_STRING | Word(token_format or DEFAULT_TOKEN_FORMAT)
        boolOperand.setParseAction(action)
        self.boolExpr: ParserElement = infixNotation(
            boolOperand,
            [
                (NOT_OP, 1, opAssoc.RIGHT, BoolNot),
                (AND_OP, 2, opAssoc.LEFT, BoolAnd),
                (OR_OP, 2, opAssoc.LEFT, BoolOr),
            ],
        )

    def evaluate_expression(self, expr: str) -> bool:
        """Given an expression it gets evaluated to True or False using boolean logic."""
        try:
            res = self.boolExpr.parseString(expr, parseAll=True)[0]
            return bool(res)
        except ParseException as e:
            log.error(f"BooleanExpressionEvaluator unable to evaluate expression => {expr}", exc_info=e)
            raise e

    @classmethod
    def is_valid_expression(cls, expr: str) -> bool:
        """Tries to evaluate the given boolean expression and returns True if it is valid or
        False if it has syntax or gramatical errors."""
        try:
            evaluator = BooleanExpressionEvaluator(ValidationOnlyTokenEvaluator())
            evaluator.evaluate_expression(expr)
            return True
        except ParseException:
            return False


class TokenContainedEvaluator(TokenEvaluator):
    """Implements the TokenEvaluator interface to determine if a token is contained
    in a particular list of tokens."""

    def __init__(self, tokens: Set[str]) -> None:
        """Initializes the token evaluator with the set of tokens that will evaluate to `True`.

        :param tokens: The list of tokens that should be evaluated to True.
        :type tokens: List[str]
        """
        self.tokens = tokens or set()

    def evaluate(self, token: str) -> bool:
        return token in self.tokens


class ValidationOnlyTokenEvaluator(TokenEvaluator):
    """Simple TokenEvaluator that always evaluates to True for valid tokens.

    This is only useful for validation purposes, do NOT use it for real expression evaluations."""

    def evaluate(self, token: str) -> bool:
        return True

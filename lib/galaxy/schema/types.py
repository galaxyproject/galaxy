from datetime import datetime

from pydantic.datetime_parse import parse_datetime
from typing_extensions import Literal

# Relative URLs cannot be validated with AnyUrl, they need a scheme.
# Making them an alias of `str` for now
RelativeUrl = str

LatestLiteral = Literal["latest"]


class OffsetNaiveDatetime(datetime):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        v = parse_datetime(v)
        return v.replace(tzinfo=None) - v.utcoffset() if v.tzinfo else v

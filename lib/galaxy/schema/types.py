from datetime import datetime

from pydantic import ValidationInfo
from pydantic.functional_validators import AfterValidator
from typing_extensions import (
    Annotated,
    Literal,
)

# Relative URLs cannot be validated with AnyUrl, they need a scheme.
# Making them an alias of `str` for now
RelativeUrl = str

# TODO: we may want to add a custom validator for this and for RelativeUrl
AbsoluteOrRelativeUrl = RelativeUrl

LatestLiteral = Literal["latest"]


def strip_tzinfo(v: datetime, info: ValidationInfo) -> datetime:
    return v.replace(tzinfo=None) - v.utcoffset() if v.tzinfo else v


OffsetNaiveDatetime = Annotated[datetime, AfterValidator(strip_tzinfo)]

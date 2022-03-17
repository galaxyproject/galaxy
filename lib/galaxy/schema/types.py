from typing_extensions import Literal

# Relative URLs cannot be validated with AnyUrl, they need a scheme.
# Making them an alias of `str` for now
RelativeUrl = str

LatestLiteral = Literal["latest"]

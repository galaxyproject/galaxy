from typing import (
    Dict,
    List,
    Optional,
    Union,
)

SerializationParams = Dict[str, Optional[Union[str, List]]]

# Relative URLs cannot be validated with AnyUrl, they need a scheme.
# Making them an alias of `str` for now
RelativeUrl = str

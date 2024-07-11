from typing import (
    Any,
    cast,
    Optional,
    Union,
)


def validate_explicit_conditional_test_value(test_parameter_name: str, value: Any) -> Optional[Union[str, bool]]:
    if value is not None and not isinstance(value, (str, bool)):
        raise Exception(f"Invalid conditional test value ({value}) for parameter ({test_parameter_name})")
    return cast(Optional[Union[str, bool]], value)

from typing import (
    Any,
    TYPE_CHECKING,
)

if TYPE_CHECKING:

    class HasDynamicProperties:
        def __getattr__(self, property: str) -> Any:
            return object()

else:
    HasDynamicProperties = object

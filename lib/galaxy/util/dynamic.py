from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:

    class HasDynamicProperties:
        def __getattr__(self, property: str) -> Any:
            return object()

else:
    HasDynamicProperties = object

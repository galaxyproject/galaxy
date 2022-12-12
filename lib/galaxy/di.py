"""Dependency injection framework for Galaxy-type apps."""
from typing import (
    Optional,
    Type,
    TypeVar,
)

from lagom import Container as LagomContainer
from lagom.exceptions import UnresolvableType

T = TypeVar("T")


class Container(LagomContainer):
    """Abstraction around lagom to provide a dependency injection context.

    Abstractions used by Galaxy should come through this interface so we can swap
    out the backend as needed. For instance https://punq.readthedocs.io/en/latest/
    containers look very nice and would allow us to also inject by name (e.g. for
    config variables for instance).
    """

    def _register_singleton(self, dep_type: Type[T], instance: Optional[T] = None) -> T:
        if instance is None:
            # create an instance from the context and register it as a singleton
            instance = self[dep_type]
        self[dep_type] = instance
        return self[dep_type]

    def _register_abstract_singleton(
        self, abstract_type: Type[T], concrete_type: Type[T], instance: Optional[T] = None
    ) -> T:
        self[abstract_type] = instance if instance is not None else concrete_type
        return self[abstract_type]

    def resolve_or_none(self, dep_type: Type[T]) -> Optional[T]:
        """Resolve the dependent type or just return None.

        If resolution is impossible assume caller has a backup plan for
        constructing the desired object. Used to construct controllers that
        may or may not be resolvable (some have upgraded but legacy framework still
        works).
        """
        try:
            return self[dep_type]
        except UnresolvableType:
            return None

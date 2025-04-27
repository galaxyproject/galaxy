"""
Accessible models can be read and copied but not modified or deleted.

Owned models can be modified and deleted.
"""

import abc
from typing import (
    Any,
    Generic,
    Optional,
    Type,
    TypeVar,
)

from galaxy import (
    exceptions,
    model,
)

U = TypeVar("U", bound=model._HasTable)


class AccessibleManagerMixin(Generic[U]):
    """
    A security interface to check if a User can read/view an item's.

    This can also be thought of as 'read but not modify' privileges.
    """

    # declare what we are using from base ModelManager
    model_class: Type[U]

    @abc.abstractmethod
    def by_id(self, id: int) -> U: ...

    # don't want to override by_id since consumers will also want to fetch w/o any security checks
    def is_accessible(self, item: U, user: Optional[model.User], **kwargs: Any) -> bool:
        """
        Return True if the item accessible to user.
        """
        # override in subclasses
        raise exceptions.NotImplemented("Abstract interface Method")

    def get_accessible(self, id: int, user: Optional[model.User], **kwargs: Any) -> U:
        """
        Return the item with the given id if it's accessible to user,
        otherwise raise an error.

        :raises exceptions.ItemAccessibilityException:
        """
        item = self.by_id(id)
        return self.error_unless_accessible(item, user, **kwargs)

    def error_unless_accessible(self, item: U, user: Optional[model.User], **kwargs: Any) -> U:
        """
        Raise an error if the item is NOT accessible to user, otherwise return the item.

        :raises exceptions.ItemAccessibilityException:
        """
        if self.is_accessible(item, user, **kwargs):
            return item
        raise exceptions.ItemAccessibilityException(f"{self.model_class.__name__} is not accessible by user")


class OwnableManagerMixin(Generic[U]):
    """
    A security interface to check if a User is an item's owner.

    Some resources are associated with the User that created or imported them
    and these Users can be considered the models' owner.

    This can also be thought of as write/edit privileges.
    """

    # declare what we are using from base ModelManager
    model_class: Type[U]

    @abc.abstractmethod
    def by_id(self, id: int) -> U: ...

    def is_owner(self, item: U, user: Optional[model.User], **kwargs: Any) -> bool:
        """
        Return True if user owns the item.
        """
        # override in subclasses
        raise exceptions.NotImplemented("Abstract interface Method")

    def get_owned(self, id: int, user: Optional[model.User], **kwargs: Any) -> U:
        """
        Return the item with the given id if owned by the user,
        otherwise raise an error.

        :raises exceptions.ItemOwnershipException:
        """
        item = self.by_id(id)
        return self.error_unless_owner(item, user, **kwargs)

    def error_unless_owner(self, item: U, user: Optional[model.User], **kwargs: Any) -> U:
        """
        Raise an error if the item is NOT owned by user, otherwise return the item.

        :raises exceptions.ItemAccessibilityException:
        """
        if self.is_owner(item, user, **kwargs):
            return item
        raise exceptions.ItemOwnershipException(f"{self.model_class.__name__} is not owned by user")

    def get_mutable(self, id: int, user: Optional[model.User], **kwargs: Any) -> U:
        """
        Return the item with the given id if the user can mutate it,
        otherwise raise an error. The user must be the owner of the item.

        :raises exceptions.ItemOwnershipException:
        """
        item = self.get_owned(id, user, **kwargs)
        self.error_unless_mutable(item)
        return item

    def error_unless_mutable(self, item: U) -> None:
        """
        Raise an error if the item is NOT mutable.

        Items purged or archived are considered immutable.

        :raises exceptions.ItemImmutableException:
        """
        if getattr(item, "purged", False) or getattr(item, "archived", False):
            raise exceptions.ItemImmutableException(f"{self.model_class.__name__} is immutable")

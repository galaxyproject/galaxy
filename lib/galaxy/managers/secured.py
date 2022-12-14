"""
Accessible models can be read and copied but not modified or deleted.

Owned models can be modified and deleted.
"""
from typing import (
    Any,
    Optional,
    Type,
    TYPE_CHECKING,
)

from galaxy import (
    exceptions,
    model,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Query


class AccessibleManagerMixin:
    """
    A security interface to check if a User can read/view an item's.

    This can also be thought of as 'read but not modify' privileges.
    """

    # declare what we are using from base ModelManager
    model_class: Type[Any]

    def by_id(self, id: int):
        ...

    # don't want to override by_id since consumers will also want to fetch w/o any security checks
    def is_accessible(self, item: "Query", user: model.User, **kwargs: Any) -> bool:
        """
        Return True if the item accessible to user.
        """
        # override in subclasses
        raise exceptions.NotImplemented("Abstract interface Method")

    def get_accessible(self, id: int, user: model.User, **kwargs: Any) -> "Query":
        """
        Return the item with the given id if it's accessible to user,
        otherwise raise an error.

        :raises exceptions.ItemAccessibilityException:
        """
        item = self.by_id(id)
        return self.error_unless_accessible(item, user, **kwargs)

    def error_unless_accessible(self, item: "Query", user, **kwargs):
        """
        Raise an error if the item is NOT accessible to user, otherwise return the item.

        :raises exceptions.ItemAccessibilityException:
        """
        if self.is_accessible(item, user, **kwargs):
            return item
        raise exceptions.ItemAccessibilityException(f"{self.model_class.__name__} is not accessible by user")

    # TODO:?? are these even useful?
    def list_accessible(self, user, **kwargs):
        """
        Return a list of items accessible to the user, raising an error if ANY
        are inaccessible.

        :raises exceptions.ItemAccessibilityException:
        """
        raise exceptions.NotImplemented("Abstract interface Method")
        # NOTE: this will be a large, inefficient list if filters are not passed in kwargs
        # items = ModelManager.list( self, trans, **kwargs )
        # return [ self.error_unless_accessible( trans, item, user ) for item in items ]

    def filter_accessible(self, user, **kwargs):
        """
        Return a list of items accessible to the user.
        """
        raise exceptions.NotImplemented("Abstract interface Method")
        # NOTE: this will be a large, inefficient list if filters are not  passed in kwargs
        # items = ModelManager.list( self, trans, **kwargs )
        # return filter( lambda item: self.is_accessible( trans, item, user ), items )


class OwnableManagerMixin:
    """
    A security interface to check if a User is an item's owner.

    Some resources are associated with the User that created or imported them
    and these Users can be considered the models' owner.

    This can also be thought of as write/edit privileges.
    """

    # declare what we are using from base ModelManager
    model_class: Type[Any]

    def by_id(self, id: int):
        ...

    def is_owner(self, item: model.Base, user: Optional[model.User], **kwargs: Any) -> bool:
        """
        Return True if user owns the item.
        """
        # override in subclasses
        raise exceptions.NotImplemented("Abstract interface Method")

    def get_owned(self, id: int, user: Optional[model.User], **kwargs: Any) -> Any:
        """
        Return the item with the given id if owned by the user,
        otherwise raise an error.

        :raises exceptions.ItemOwnershipException:
        """
        item = self.by_id(id)
        return self.error_unless_owner(item, user, **kwargs)

    def error_unless_owner(self, item, user: Optional[model.User], **kwargs: Any):
        """
        Raise an error if the item is NOT owned by user, otherwise return the item.

        :raises exceptions.ItemAccessibilityException:
        """
        if self.is_owner(item, user, **kwargs):
            return item
        raise exceptions.ItemOwnershipException(f"{self.model_class.__name__} is not owned by user")

    def list_owned(self, user, **kwargs):
        """
        Return a list of items owned by the user, raising an error if ANY
        are not.

        :raises exceptions.ItemAccessibilityException:
        """
        raise exceptions.NotImplemented("Abstract interface Method")
        # just alias to by_user (easier/same thing)
        # return self.by_user( trans, user, **kwargs )

    def filter_owned(self, user, **kwargs):
        """
        Return a list of items owned by the user.
        """
        # just alias to list_owned
        return self.list_owned(user, **kwargs)
